"""
ED Demand Forecasting Agent
============================
Uses Facebook Prophet to forecast Emergency Department patient arrival volume
at three granularities:

  • Hourly   — next 48 hours  (staffing shifts)
  • Daily    — next 30 days   (resource planning)
  • Weekly   — next 12 weeks  (capacity planning)

Input  : clinical_encounters.csv  (encounter_id, patient_id, timestamp, …)
         Optional: triage_audit_log.csv for ESI-level demand breakdown

Prophet captures:
  - Weekly seasonality  (Mon–Sun patterns in ED arrivals)
  - Daily seasonality   (hour-of-day patterns)
  - Yearly seasonality  (seasonal illness trends)
  - US public holidays  (demand spikes on holidays)
  - Changepoints        (automatic trend shifts)

Output : DemandForecast  Pydantic model with forecast DataFrame + insights
"""

from __future__ import annotations

import os
import warnings
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Literal

import pandas as pd
import numpy as np
from pydantic import BaseModel, Field

warnings.filterwarnings("ignore")  # suppress Prophet/Stan verbosity

try:
    from prophet import Prophet
    from prophet.diagnostics import cross_validation, performance_metrics
    _PROPHET_AVAILABLE = True
except ImportError:
    _PROPHET_AVAILABLE = False


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class ForecastPoint(BaseModel):
    ds: str              # ISO timestamp
    yhat: float          # predicted arrivals
    yhat_lower: float    # 80% CI lower
    yhat_upper: float    # 80% CI upper
    trend: float
    weekly: Optional[float] = None
    daily: Optional[float] = None
    yearly: Optional[float] = None


class PeakWindow(BaseModel):
    start: str
    end: str
    predicted_arrivals: float
    severity: str        # LOW | MEDIUM | HIGH | CRITICAL
    recommendation: str


class StaffingRecommendation(BaseModel):
    period: str
    predicted_volume: float
    recommended_nurses: int
    recommended_physicians: int
    recommended_beds: int
    notes: str


class DemandForecast(BaseModel):
    granularity: str              # hourly | daily | weekly
    generated_at: str
    horizon_label: str            # "Next 48 hours" etc.
    forecast_points: List[ForecastPoint]
    peak_windows: List[PeakWindow]
    staffing_recommendations: List[StaffingRecommendation]
    model_metrics: Dict[str, Any]
    insights: List[str]
    baseline_daily_avg: float
    baseline_hourly_avg: float
    error: Optional[str] = None


# ============================================================================
# DATA LOADING & AGGREGATION
# ============================================================================

_DATA_PATH = os.path.join(os.path.dirname(__file__), "clinical_encounters.csv")
_AUDIT_PATH = os.path.join(os.path.dirname(__file__), "triage_audit_log.csv")


def _load_encounter_series(csv_path: str = _DATA_PATH) -> pd.DataFrame:
    """
    Load clinical_encounters.csv and return a clean time-series DataFrame
    with columns [ds, y] where y = arrival count per period.
    """
    df = pd.read_csv(csv_path, parse_dates=["timestamp"])
    df = df.dropna(subset=["timestamp"])
    df = df.rename(columns={"timestamp": "ds"})
    df["ds"] = pd.to_datetime(df["ds"], utc=False, errors="coerce")
    df = df.dropna(subset=["ds"])
    return df


def _aggregate_for_granularity(
    df: pd.DataFrame,
    granularity: Literal["hourly", "daily", "weekly"],
) -> pd.DataFrame:
    """Resample to the requested granularity and return Prophet-ready df."""
    if granularity == "hourly":
        freq = "h"
    elif granularity == "daily":
        freq = "D"
    else:
        freq = "W"

    counts = (
        df.set_index("ds")
        .resample(freq)
        .size()
        .reset_index()
        .rename(columns={0: "y"})
    )

    # Fill gaps with 0 (ED was open but no arrivals logged)
    counts["y"] = counts["y"].fillna(0).clip(lower=0)

    # Drop future timestamps
    counts = counts[counts["ds"] <= pd.Timestamp.now()]

    return counts


# ============================================================================
# PROPHET MODELLING
# ============================================================================

def _has_enough_yearly_history(df: pd.DataFrame, min_years: float = 1.8) -> bool:
    """Return True only if the training data spans enough time for yearly seasonality."""
    if df.empty:
        return False
    span_days = (df["ds"].max() - df["ds"].min()).days
    return span_days >= min_years * 365


def _build_prophet(granularity: str, train_df: pd.DataFrame = None) -> "Prophet":
    """Configure Prophet with ED-appropriate seasonality settings.

    Key decisions:
    - yearly_seasonality is DISABLED unless we have ≥1.8 years of history.
      With only one year of data the model confuses a recent volume drop with a
      real seasonal dip, causing January forecasts to be unrealistically low.
    - seasonality_mode='multiplicative' handles proportional swings better for
      count data (e.g. 20% more arrivals on Mondays rather than +1.5 flat).
    - floor=0 / cap set from data prevents negative or absurd predictions.
    """
    use_yearly = _has_enough_yearly_history(train_df) if train_df is not None else False

    if granularity == "hourly":
        model = Prophet(
            changepoint_prior_scale=0.05,
            seasonality_prior_scale=10,
            holidays_prior_scale=10,
            seasonality_mode="multiplicative",
            daily_seasonality=True,
            weekly_seasonality=True,
            yearly_seasonality=False,   # hourly spans rarely cover 2+ years
            interval_width=0.80,
        )
    elif granularity == "daily":
        model = Prophet(
            changepoint_prior_scale=0.1,
            seasonality_prior_scale=10,
            holidays_prior_scale=10,
            seasonality_mode="multiplicative",
            daily_seasonality=False,
            weekly_seasonality=True,
            yearly_seasonality=use_yearly,
            interval_width=0.80,
        )
    else:  # weekly
        model = Prophet(
            changepoint_prior_scale=0.15,
            seasonality_prior_scale=5,
            holidays_prior_scale=5,
            seasonality_mode="multiplicative",
            daily_seasonality=False,
            weekly_seasonality=False,
            yearly_seasonality=use_yearly,
            interval_width=0.80,
        )

    # US public holidays — ED sees volume spikes on these days
    model.add_country_holidays(country_name="US")
    return model


def _forecast_periods(granularity: str) -> int:
    return {"hourly": 48, "daily": 30, "weekly": 12}[granularity]


def _freq_str(granularity: str) -> str:
    return {"hourly": "h", "daily": "D", "weekly": "W"}[granularity]


# ============================================================================
# PEAK & STAFFING ANALYSIS
# ============================================================================

_STAFFING_RATIOS = {
    # patients/hour: (nurses, physicians, beds)
    "LOW":      (2,  1,  4),
    "MEDIUM":   (4,  2,  8),
    "HIGH":     (6,  3, 12),
    "CRITICAL": (8,  4, 16),
}


def _severity_from_volume(volume: float, p25: float, p75: float, p95: float) -> str:
    if volume >= p95:
        return "CRITICAL"
    if volume >= p75:
        return "HIGH"
    if volume >= p25:
        return "MEDIUM"
    return "LOW"


def _detect_peaks(
    forecast_df: pd.DataFrame,
    granularity: str,
    baseline_avg: float,
) -> List[PeakWindow]:
    """Find contiguous windows where yhat > 1.25× baseline."""
    p25 = forecast_df["yhat"].quantile(0.25)
    p75 = forecast_df["yhat"].quantile(0.75)
    p95 = forecast_df["yhat"].quantile(0.95)
    threshold = max(baseline_avg * 1.25, p75)

    peaks = []
    in_peak = False
    peak_start = None
    peak_vals = []

    for _, row in forecast_df.iterrows():
        if row["yhat"] >= threshold:
            if not in_peak:
                in_peak = True
                peak_start = row["ds"]
                peak_vals = []
            peak_vals.append(row["yhat"])
        else:
            if in_peak:
                avg_vol = float(np.mean(peak_vals))
                sev = _severity_from_volume(avg_vol, p25, p75, p95)
                n, ph, beds = _STAFFING_RATIOS[sev]
                peaks.append(PeakWindow(
                    start=str(peak_start)[:16],
                    end=str(row["ds"])[:16],
                    predicted_arrivals=round(avg_vol, 1),
                    severity=sev,
                    recommendation=(
                        f"Surge expected — consider {n} nurses, {ph} physicians, {beds} beds on standby."
                    ),
                ))
                in_peak = False
                peak_vals = []

    return peaks[:10]  # top 10 peaks


def _build_staffing(
    forecast_df: pd.DataFrame,
    granularity: str,
    p25: float,
    p75: float,
    p95: float,
) -> List[StaffingRecommendation]:
    """Generate per-period staffing recommendations."""
    recs = []

    if granularity == "hourly":
        # Group by shift: 07-15, 15-23, 23-07
        def shift(h):
            if 7 <= h < 15:
                return "Day (07:00–15:00)"
            if 15 <= h < 23:
                return "Evening (15:00–23:00)"
            return "Night (23:00–07:00)"

        forecast_df = forecast_df.copy()
        forecast_df["shift"] = forecast_df["ds"].dt.hour.apply(shift)
        for sh, grp in forecast_df.groupby("shift"):
            vol = grp["yhat"].mean()
            sev = _severity_from_volume(vol, p25, p75, p95)
            n, ph, beds = _STAFFING_RATIOS[sev]
            recs.append(StaffingRecommendation(
                period=sh, predicted_volume=round(vol, 1),
                recommended_nurses=n, recommended_physicians=ph,
                recommended_beds=beds,
                notes=f"Average {vol:.1f} arrivals/hr — {sev} load",
            ))
    elif granularity == "daily":
        # Group by week
        forecast_df = forecast_df.copy()
        forecast_df["week"] = forecast_df["ds"].dt.to_period("W").astype(str)
        for wk, grp in forecast_df.groupby("week"):
            vol = grp["yhat"].sum()
            daily_avg = grp["yhat"].mean()
            sev = _severity_from_volume(daily_avg, p25, p75, p95)
            n, ph, beds = _STAFFING_RATIOS[sev]
            recs.append(StaffingRecommendation(
                period=f"Week of {wk}", predicted_volume=round(vol, 1),
                recommended_nurses=n, recommended_physicians=ph,
                recommended_beds=beds,
                notes=f"~{daily_avg:.0f} arrivals/day avg — {sev} weekly load",
            ))
    else:  # weekly
        for _, row in forecast_df.head(12).iterrows():
            vol = row["yhat"]
            sev = _severity_from_volume(vol, p25, p75, p95)
            n, ph, beds = _STAFFING_RATIOS[sev]
            recs.append(StaffingRecommendation(
                period=str(row["ds"])[:10],
                predicted_volume=round(vol, 1),
                recommended_nurses=n, recommended_physicians=ph,
                recommended_beds=beds,
                notes=f"{sev} load week — {vol:.0f} projected arrivals",
            ))

    return recs


# ============================================================================
# INSIGHTS GENERATION
# ============================================================================

def _generate_insights(
    forecast_df: pd.DataFrame,
    train_df: pd.DataFrame,
    granularity: str,
    peaks: List[PeakWindow],
    baseline_avg: float,
) -> List[str]:
    insights = []

    max_row = forecast_df.loc[forecast_df["yhat"].idxmax()]
    min_row = forecast_df.loc[forecast_df["yhat"].idxmin()]

    if granularity == "hourly":
        insights.append(
            f"Peak hour forecast: {max_row['yhat']:.1f} arrivals at "
            f"{str(max_row['ds'])[11:16]} on {str(max_row['ds'])[:10]}."
        )
        insights.append(
            f"Quietest hour: {min_row['yhat']:.1f} arrivals at "
            f"{str(min_row['ds'])[11:16]} on {str(min_row['ds'])[:10]}."
        )
    else:
        insights.append(
            f"Highest volume forecast: {max_row['yhat']:.0f} arrivals on {str(max_row['ds'])[:10]}."
        )
        insights.append(
            f"Lowest volume forecast: {min_row['yhat']:.0f} arrivals on {str(min_row['ds'])[:10]}."
        )

    if peaks:
        insights.append(
            f"{len(peaks)} surge window(s) detected exceeding 125% of baseline. "
            f"Earliest: {peaks[0].start}."
        )

    overall_trend = forecast_df["trend"].iloc[-1] - forecast_df["trend"].iloc[0]
    if overall_trend > baseline_avg * 0.05:
        insights.append(
            f"Upward trend detected (+{overall_trend:.1f} arrivals over forecast horizon). "
            "Consider capacity expansion planning."
        )
    elif overall_trend < -baseline_avg * 0.05:
        insights.append(
            f"Downward trend detected ({overall_trend:.1f} arrivals over forecast horizon)."
        )

    # Day-of-week pattern from training data
    train_df = train_df.copy()
    train_df["dow"] = train_df["ds"].dt.day_name()
    dow_avg = train_df.groupby("dow")["y"].mean()
    if not dow_avg.empty:
        busiest_day = dow_avg.idxmax()
        quietest_day = dow_avg.idxmin()
        insights.append(
            f"Historically busiest day: {busiest_day} "
            f"(avg {dow_avg[busiest_day]:.1f} arrivals). "
            f"Quietest: {quietest_day} (avg {dow_avg[quietest_day]:.1f})."
        )

    return insights


# ============================================================================
# CROSS-VALIDATION METRICS (optional, skipped if < 60 data points)
# ============================================================================

def _safe_cv_metrics(model: "Prophet", train_df: pd.DataFrame, granularity: str) -> Dict[str, Any]:
    """Run Prophet cross-validation and return MAE/RMSE/MAPE if enough data."""
    try:
        n = len(train_df)
        if n < 60:
            return {"note": f"Insufficient history ({n} points) for cross-validation. Need ≥60."}

        horizon_map = {"hourly": "24 hours", "daily": "7 days", "weekly": "4 weeks"}
        initial_map = {"hourly": "168 hours", "daily": "90 days", "weekly": "26 weeks"}
        period_map  = {"hourly": "12 hours", "daily": "14 days", "weekly": "8 weeks"}

        cv_df = cross_validation(
            model,
            initial=initial_map[granularity],
            period=period_map[granularity],
            horizon=horizon_map[granularity],
            disable_tqdm=True,
        )
        pm = performance_metrics(cv_df, rolling_window=1)
        return {
            "mae": round(float(pm["mae"].mean()), 3),
            "rmse": round(float(pm["rmse"].mean()), 3),
            "mape": round(float(pm["mape"].mean()), 4),
            "cv_folds": len(pm),
        }
    except Exception as e:
        return {"note": f"CV skipped: {e}"}


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def run_demand_forecast(
    granularity: Literal["hourly", "daily", "weekly"] = "daily",
    csv_path: str = _DATA_PATH,
    run_cv: bool = False,
) -> DemandForecast:
    """
    Fit Prophet on historical ED encounter data and forecast future demand.

    Args:
        granularity : "hourly" | "daily" | "weekly"
        csv_path    : path to clinical_encounters.csv (or equivalent)
        run_cv      : whether to run cross-validation (slow, ~30s extra)

    Returns:
        DemandForecast
    """
    if not _PROPHET_AVAILABLE:
        return DemandForecast(
            granularity=granularity, generated_at=datetime.now().isoformat(),
            horizon_label="", forecast_points=[], peak_windows=[],
            staffing_recommendations=[], model_metrics={}, insights=[],
            baseline_daily_avg=0, baseline_hourly_avg=0,
            error="prophet not installed. Run: pip install prophet",
        )

    try:
        raw_df = _load_encounter_series(csv_path)
        train_df = _aggregate_for_granularity(raw_df, granularity)

        if len(train_df) < 10:
            return DemandForecast(
                granularity=granularity, generated_at=datetime.now().isoformat(),
                horizon_label="", forecast_points=[], peak_windows=[],
                staffing_recommendations=[], model_metrics={}, insights=[],
                baseline_daily_avg=0, baseline_hourly_avg=0,
                error=f"Not enough historical data ({len(train_df)} rows). Need ≥10.",
            )

        # Fit — pass train_df so the builder can check history length
        model = _build_prophet(granularity, train_df=train_df)

        # Add logistic floor/cap so Prophet never predicts below 0 or above
        # 3× the historical max (prevents exploding upper-CI extrapolations).
        # Only needed for logistic growth; we use 'linear' here but we clip
        # the output instead (simpler and equally effective).
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model.fit(train_df)

        # Forecast
        periods = _forecast_periods(granularity)
        future = model.make_future_dataframe(periods=periods, freq=_freq_str(granularity))
        forecast = model.predict(future)

        # Only the future portion
        cutoff = train_df["ds"].max()
        future_fc = forecast[forecast["ds"] > cutoff].copy()

        # Baselines
        baseline_daily_avg = float(
            _aggregate_for_granularity(raw_df, "daily")["y"].mean()
        )
        baseline_hourly_avg = float(
            _aggregate_for_granularity(raw_df, "hourly")["y"].mean()
        )
        baseline_avg = {"hourly": baseline_hourly_avg, "daily": baseline_daily_avg,
                        "weekly": baseline_daily_avg * 7}[granularity]

        # Clamp: floor = p5 of training data (realistic minimum), ceil = 3× historical max.
        # This prevents negative CIs and absurd upper-bound extrapolations.
        data_floor = max(0.0, float(train_df["y"].quantile(0.05)))
        data_ceil  = float(train_df["y"].max()) * 3.0
        for col in ["yhat", "yhat_lower", "yhat_upper"]:
            future_fc[col] = future_fc[col].clip(lower=data_floor, upper=data_ceil)

        # Forecast points
        component_cols = [c for c in ["trend", "weekly", "daily", "yearly"] if c in future_fc.columns]
        fp_list = []
        for _, row in future_fc.iterrows():
            fp_list.append(ForecastPoint(
                ds=str(row["ds"])[:19],
                yhat=round(float(row["yhat"]), 2),
                yhat_lower=round(float(row["yhat_lower"]), 2),
                yhat_upper=round(float(row["yhat_upper"]), 2),
                trend=round(float(row.get("trend", 0)), 2),
                weekly=round(float(row["weekly"]), 4) if "weekly" in row.index else None,
                daily=round(float(row["daily"]), 4) if "daily" in row.index else None,
                yearly=round(float(row["yearly"]), 4) if "yearly" in row.index else None,
            ))

        # Peaks
        p25 = float(future_fc["yhat"].quantile(0.25))
        p75 = float(future_fc["yhat"].quantile(0.75))
        p95 = float(future_fc["yhat"].quantile(0.95))
        peaks = _detect_peaks(future_fc, granularity, baseline_avg)

        # Staffing
        staffing = _build_staffing(future_fc, granularity, p25, p75, p95)

        # Metrics
        metrics = {"mae_train": None}
        if run_cv:
            metrics = _safe_cv_metrics(model, train_df, granularity)
        else:
            # Simple in-sample MAE on last 20% of training data
            hist = forecast[forecast["ds"] <= cutoff].merge(train_df, on="ds", how="inner")
            if not hist.empty:
                mae = float(np.abs(hist["yhat"] - hist["y"]).mean())
                metrics = {"mae_train": round(mae, 3), "n_train": len(train_df)}

        # Insights
        insights = _generate_insights(future_fc, train_df, granularity, peaks, baseline_avg)

        # Data quality warnings
        span_days = (train_df["ds"].max() - train_df["ds"].min()).days
        if span_days < 365 * 1.8:
            insights.insert(0,
                f"⚠ Data quality note: only {span_days} days of history available. "
                "Yearly seasonality disabled — need ≥2 years for reliable seasonal patterns. "
                "Weekly patterns are still modelled correctly."
            )

        horizon_labels = {
            "hourly": "Next 48 hours",
            "daily": "Next 30 days",
            "weekly": "Next 12 weeks",
        }

        return DemandForecast(
            granularity=granularity,
            generated_at=datetime.now().isoformat(),
            horizon_label=horizon_labels[granularity],
            forecast_points=fp_list,
            peak_windows=peaks,
            staffing_recommendations=staffing,
            model_metrics=metrics,
            insights=insights,
            baseline_daily_avg=round(baseline_daily_avg, 2),
            baseline_hourly_avg=round(baseline_hourly_avg, 2),
        )

    except Exception as e:
        import traceback
        return DemandForecast(
            granularity=granularity, generated_at=datetime.now().isoformat(),
            horizon_label="", forecast_points=[], peak_windows=[],
            staffing_recommendations=[], model_metrics={}, insights=[],
            baseline_daily_avg=0, baseline_hourly_avg=0,
            error=f"{e}\n{traceback.format_exc()}",
        )


# ============================================================================
# CLI DEMO
# ============================================================================

if __name__ == "__main__":
    import sys, json

    gran = sys.argv[1] if len(sys.argv) > 1 else "daily"
    print(f"Running {gran} demand forecast…")
    result = run_demand_forecast(granularity=gran)

    if result.error:
        print(f"Error: {result.error}")
        sys.exit(1)

    print(f"\nHorizon     : {result.horizon_label}")
    print(f"Baseline    : {result.baseline_daily_avg:.1f} arrivals/day avg")
    print(f"Forecast pts: {len(result.forecast_points)}")
    print(f"Peak windows: {len(result.peak_windows)}")
    print(f"Metrics     : {result.model_metrics}")
    print("\nInsights:")
    for ins in result.insights:
        print(f"  • {ins}")
    if result.peak_windows:
        print("\nSurge Windows:")
        for p in result.peak_windows:
            print(f"  [{p.severity}] {p.start} → {p.end}  avg {p.predicted_arrivals} arrivals  |  {p.recommendation}")
    print("\nStaffing Recommendations:")
    for s in result.staffing_recommendations[:5]:
        print(f"  {s.period}: {s.predicted_volume:.0f} arrivals → "
              f"{s.recommended_nurses}N / {s.recommended_physicians}MD / {s.recommended_beds} beds")
