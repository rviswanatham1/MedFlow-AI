"""
Deterioration Prediction Agent

Predicts the probability and nature of clinical deterioration within a
30–60 minute window. Uses a deterministic weighted scoring model
combining vitals, symptoms, ESI level, and patient history.

No LLM used — purely rule-based for speed, reliability, and explainability.
"""

import math
from datetime import datetime
from typing import Optional, Dict, Any, List, Literal

try:
    import pandas as pd
    _PANDAS_AVAILABLE = True
except ImportError:
    _PANDAS_AVAILABLE = False

from pydantic import BaseModel, Field


# ============================================================================
# RISK FACTOR DICTIONARIES
# ============================================================================

# Maps symptom strings to their deterioration risk contribution (0.0–0.25)
HIGH_RISK_SYMPTOMS: Dict[str, float] = {
    "chest pain": 0.15,
    "chest pressure": 0.15,
    "chest tightness": 0.12,
    "shortness of breath": 0.14,
    "syncope": 0.18,
    "altered mental status": 0.20,
    "confusion": 0.18,
    "seizure": 0.20,
    "thunderclap headache": 0.18,
    "unilateral arm weakness": 0.17,
    "unilateral leg weakness": 0.17,
    "facial droop": 0.17,
    "aphasia": 0.17,
    "dysarthria": 0.14,
    "active bleeding": 0.18,
    "hemoptysis": 0.16,
    "hematemesis": 0.18,
    "hematochezia": 0.14,
    "abdominal pain": 0.08,
    "fever": 0.06,
    "rigors": 0.10,
    "dizziness": 0.06,
    "palpitations": 0.08,
    "diaphoresis": 0.10,
}

# Maps condition name patterns to deterioration risk contribution (0.0–0.10)
HIGH_RISK_CONDITIONS: Dict[str, float] = {
    "coronary artery disease": 0.08,
    "ischemic heart disease": 0.08,
    "heart failure": 0.08,
    "congestive heart failure": 0.08,
    "myocardial infarction": 0.07,
    "atrial fibrillation": 0.06,
    "copd": 0.06,
    "chronic obstructive pulmonary disease": 0.06,
    "asthma": 0.04,
    "diabetes mellitus": 0.04,
    "type 1 diabetes": 0.05,
    "type 2 diabetes": 0.04,
    "chronic kidney disease": 0.04,
    "renal failure": 0.06,
    "liver cirrhosis": 0.06,
    "immunosuppression": 0.07,
    "cancer": 0.06,
    "stroke": 0.07,
    "cerebrovascular disease": 0.07,
    "pulmonary embolism": 0.08,
    "aortic stenosis": 0.07,
    "hypertension": 0.03,
}


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class DeteriorationInput(BaseModel):
    patient_id: str
    vitals: Dict[str, Any] = Field(default_factory=dict)
    ews_score: int = Field(default=0)
    symptoms: List[str] = Field(default_factory=list)
    esi_level: int = Field(default=3, description="ESI level 1-5")
    patient_age: int = Field(default=40)
    active_conditions: List[str] = Field(default_factory=list)
    arrival_time: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="ISO 8601 arrival timestamp"
    )


class DeteriorationPrediction(BaseModel):
    patient_id: str
    risk_score: float = Field(description="0.0-1.0 probability of deterioration in 30-60 min")
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(
        description="LOW <0.25 | MEDIUM 0.25-0.50 | HIGH 0.50-0.75 | CRITICAL >0.75"
    )
    time_window: str = Field(default="30-60 minutes")
    risk_factors: List[str] = Field(description="Factors that contributed to the score")
    predicted_trajectory: Literal["STABLE", "WORSENING", "RAPID_DETERIORATION"] = Field(
        description="STABLE <0.25 | WORSENING 0.25-0.60 | RAPID_DETERIORATION >0.60"
    )
    confidence: float = Field(description="0.0-1.0 prediction confidence based on data completeness")
    recommended_reassessment_minutes: int = Field(
        description="15 if CRITICAL/HIGH, 30 if MEDIUM, 60 if LOW"
    )
    score_components: Dict[str, float] = Field(
        description="Breakdown of score contributions by component"
    )
    predicted_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# ============================================================================
# SCORING COMPONENT FUNCTIONS
# ============================================================================

def _compute_vitals_component(
    vitals: Dict[str, Any], ews_score: int
) -> tuple[float, List[str]]:
    """
    Vitals-based deterioration risk.
    Contribution: 0.0–0.40
    """
    factors: List[str] = []
    score = 0.0

    # Base from EWS (normalised to 0–0.30)
    if ews_score > 0:
        ews_contribution = min(0.30, ews_score / 15.0 * 0.30)
        score += ews_contribution
        factors.append(f"EWS score {ews_score} (+{ews_contribution:.2f})")

    # Critical vital sign increments
    spo2 = vitals.get("oxygen_sat")
    if spo2 is not None:
        if spo2 < 90:
            score += 0.08
            factors.append(f"Critical SpO2 {spo2}% (+0.08)")
        elif spo2 < 93:
            score += 0.05
            factors.append(f"Low SpO2 {spo2}% (+0.05)")

    bp_str = vitals.get("blood_pressure", "")
    if bp_str and bp_str != "Not recorded":
        try:
            systolic = int(str(bp_str).split('/')[0].strip())
            if systolic < 90:
                score += 0.08
                factors.append(f"Hypotension systolic {systolic} mmHg (+0.08)")
            elif systolic < 100:
                score += 0.04
                factors.append(f"Borderline hypotension systolic {systolic} mmHg (+0.04)")
            elif systolic > 200:
                score += 0.05
                factors.append(f"Hypertensive crisis systolic {systolic} mmHg (+0.05)")
        except (ValueError, IndexError):
            pass

    hr = vitals.get("heart_rate")
    if hr is not None:
        if hr > 130 or hr < 40:
            score += 0.05
            factors.append(f"Critical heart rate {hr} bpm (+0.05)")
        elif hr > 110:
            score += 0.03
            factors.append(f"Tachycardia {hr} bpm (+0.03)")

    rr = vitals.get("respiratory_rate")
    if rr is not None:
        if rr > 25 or rr < 8:
            score += 0.05
            factors.append(f"Critical respiratory rate {rr}/min (+0.05)")
        elif rr > 20:
            score += 0.03
            factors.append(f"Tachypnea {rr}/min (+0.03)")

    consciousness = str(vitals.get("consciousness", "ALERT")).upper()
    if consciousness != "ALERT":
        score += 0.08
        factors.append(f"Altered consciousness: {consciousness} (+0.08)")

    return min(0.40, score), factors


def _compute_symptom_component(
    symptoms: List[str],
) -> tuple[float, List[str]]:
    """
    Symptom-based deterioration risk.
    Contribution: 0.0–0.25
    """
    factors: List[str] = []
    score = 0.0

    symptoms_lower = [s.lower() for s in symptoms]

    for symptom in symptoms_lower:
        for key, weight in HIGH_RISK_SYMPTOMS.items():
            if key in symptom or symptom in key:
                score += weight
                factors.append(f"Symptom '{key}' (+{weight:.2f})")
                break  # avoid double-counting same symptom

    return min(0.25, score), factors


def _compute_history_component(
    active_conditions: List[str], patient_age: int
) -> tuple[float, List[str]]:
    """
    Medical history and age-based risk.
    Contribution: 0.0–0.20
    """
    factors: List[str] = []
    score = 0.0

    conditions_lower = [c.lower() for c in active_conditions]

    for condition_lower in conditions_lower:
        for key, weight in HIGH_RISK_CONDITIONS.items():
            if key in condition_lower:
                score += weight
                factors.append(f"History: {key} (+{weight:.2f})")
                break

    # Age risk increments
    if patient_age >= 85:
        score += 0.08
        factors.append(f"Age {patient_age} (≥85) (+0.08)")
    elif patient_age >= 75:
        score += 0.05
        factors.append(f"Age {patient_age} (≥75) (+0.05)")
    elif patient_age >= 65:
        score += 0.03
        factors.append(f"Age {patient_age} (≥65) (+0.03)")
    elif patient_age < 2:
        score += 0.05
        factors.append(f"Age {patient_age} (infant, <2 years) (+0.05)")

    return min(0.20, score), factors


def _compute_esi_component(esi_level: int) -> tuple[float, List[str]]:
    """
    Base risk contribution from ESI acuity level.
    Higher acuity (lower ESI number) → higher base deterioration risk.
    """
    esi_weights = {1: 0.15, 2: 0.12, 3: 0.08, 4: 0.03, 5: 0.01}
    contribution = esi_weights.get(esi_level, 0.08)
    return contribution, [f"ESI level {esi_level} (+{contribution:.2f})"]


def _compute_confidence(vitals: Dict[str, Any], symptoms: List[str]) -> float:
    """
    Confidence in prediction based on data completeness.
    """
    vital_fields = [
        "temperature", "heart_rate", "respiratory_rate",
        "oxygen_sat", "blood_pressure", "consciousness",
    ]
    present = sum(
        1 for f in vital_fields
        if vitals.get(f) is not None and vitals.get(f) != "Not recorded"
    )
    vitals_completeness = present / len(vital_fields)

    symptom_bonus = 0.2 if symptoms else 0.0

    return round(min(1.0, vitals_completeness * 0.80 + symptom_bonus), 2)


# ============================================================================
# VITAL TREND ANALYSIS
# ============================================================================

def _compute_trend_component(
    current_vitals: Dict[str, Any],
    past_encounters_df: Any = None,
) -> tuple[float, List[str]]:
    """
    Compare current vitals against the most recent past encounter.
    Worsening trends across ≥2 available vitals contribute +0.12.
    Contribution: 0.0–0.12
    """
    if past_encounters_df is None or not _PANDAS_AVAILABLE:
        return 0.0, []

    try:
        if hasattr(past_encounters_df, 'empty') and past_encounters_df.empty:
            return 0.0, []
        if len(past_encounters_df) == 0:
            return 0.0, []
    except Exception:
        return 0.0, []

    try:
        last = past_encounters_df.iloc[0]
    except (IndexError, Exception):
        return 0.0, []

    worsening: List[str] = []

    # Heart rate trend (available in clinical_encounters.csv)
    cur_hr = current_vitals.get("heart_rate")
    try:
        prev_hr = float(last["heart_rate"]) if pd.notna(last.get("heart_rate")) else None
    except Exception:
        prev_hr = None
    if cur_hr is not None and prev_hr is not None:
        delta = float(cur_hr) - prev_hr
        if delta >= 15:
            worsening.append(f"HR increased {delta:+.0f} bpm vs last encounter")

    # Respiratory rate trend (if column exists)
    cur_rr = current_vitals.get("respiratory_rate")
    prev_rr = None
    if "respiratory_rate" in last.index if hasattr(last, 'index') else False:
        try:
            val = last.get("respiratory_rate") if hasattr(last, 'get') else None
            if val is not None and pd.notna(val):
                prev_rr = float(val)
        except Exception:
            pass
    if cur_rr is not None and prev_rr is not None:
        delta = float(cur_rr) - prev_rr
        if delta >= 4:
            worsening.append(f"RR increased {delta:+.0f}/min vs last encounter")

    # SpO2 trend (if column exists)
    cur_spo2 = current_vitals.get("oxygen_sat")
    prev_spo2 = None
    for col in ("oxygen_sat", "spo2", "oxygen_saturation"):
        try:
            val = last.get(col) if hasattr(last, 'get') else None
            if val is not None and pd.notna(val):
                prev_spo2 = float(val)
                break
        except Exception:
            pass
    if cur_spo2 is not None and prev_spo2 is not None:
        delta = float(cur_spo2) - prev_spo2
        if delta <= -3:
            worsening.append(f"SpO2 decreased {delta:.0f}% vs last encounter")

    if len(worsening) >= 2:
        factor = "Worsening vital trend vs last encounter: " + "; ".join(worsening) + " (+0.12)"
        return 0.12, [factor]

    if len(worsening) == 1:
        return 0.0, [f"Single vital worsening (threshold not met): {worsening[0]}"]

    return 0.0, []


# ============================================================================
# MAIN PREDICTION FUNCTION
# ============================================================================

def predict_deterioration(
    input_data: DeteriorationInput,
    past_encounters_df: Any = None,
) -> DeteriorationPrediction:
    """
    Predict clinical deterioration risk over the next 30-60 minutes.

    Args:
        input_data: DeteriorationInput with patient vitals, symptoms, history

    Returns:
        DeteriorationPrediction with risk score, level, trajectory, and rationale
    """
    vitals_score, vitals_factors = _compute_vitals_component(
        input_data.vitals, input_data.ews_score
    )
    symptom_score, symptom_factors = _compute_symptom_component(input_data.symptoms)
    history_score, history_factors = _compute_history_component(
        input_data.active_conditions, input_data.patient_age
    )
    esi_score, esi_factors = _compute_esi_component(input_data.esi_level)
    trend_score, trend_factors = _compute_trend_component(
        input_data.vitals, past_encounters_df
    )

    total_score = min(1.0, vitals_score + symptom_score + history_score + esi_score + trend_score)
    total_score = round(total_score, 3)

    all_factors = vitals_factors + symptom_factors + history_factors + esi_factors + trend_factors

    # Risk level classification
    if total_score < 0.25:
        risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "LOW"
    elif total_score < 0.50:
        risk_level = "MEDIUM"
    elif total_score < 0.75:
        risk_level = "HIGH"
    else:
        risk_level = "CRITICAL"

    # Trajectory
    if total_score < 0.25:
        trajectory: Literal["STABLE", "WORSENING", "RAPID_DETERIORATION"] = "STABLE"
    elif total_score <= 0.60:
        trajectory = "WORSENING"
    else:
        trajectory = "RAPID_DETERIORATION"

    # Reassessment interval
    reassessment = {
        "LOW": 60,
        "MEDIUM": 30,
        "HIGH": 15,
        "CRITICAL": 15,
    }[risk_level]

    confidence = _compute_confidence(input_data.vitals, input_data.symptoms)

    return DeteriorationPrediction(
        patient_id=input_data.patient_id,
        risk_score=total_score,
        risk_level=risk_level,
        time_window="30-60 minutes",
        risk_factors=[f for f in all_factors if f],
        predicted_trajectory=trajectory,
        confidence=confidence,
        recommended_reassessment_minutes=reassessment,
        score_components={
            "vitals_component": round(vitals_score, 3),
            "symptom_component": round(symptom_score, 3),
            "history_component": round(history_score, 3),
            "esi_component": round(esi_score, 3),
            "trend_component": round(trend_score, 3),
        },
    )


# ============================================================================
# CLI DEMO
# ============================================================================

if __name__ == "__main__":
    test_input = DeteriorationInput(
        patient_id="P00001",
        vitals={
            "temperature": 38.5,
            "heart_rate": 118,
            "respiratory_rate": 24,
            "blood_pressure": "95/60",
            "oxygen_sat": 91,
            "consciousness": "ALERT",
        },
        ews_score=7,
        symptoms=["chest pain", "shortness of breath", "diaphoresis"],
        esi_level=2,
        patient_age=67,
        active_conditions=["Coronary artery disease", "Type 2 diabetes mellitus"],
    )

    prediction = predict_deterioration(test_input)
    print(f"Patient: {prediction.patient_id}")
    print(f"Risk Score: {prediction.risk_score:.3f}")
    print(f"Risk Level: {prediction.risk_level}")
    print(f"Trajectory: {prediction.predicted_trajectory}")
    print(f"Confidence: {prediction.confidence:.2f}")
    print(f"Reassess in: {prediction.recommended_reassessment_minutes} minutes")
    print(f"\nRisk Factors:")
    for f in prediction.risk_factors:
        print(f"  • {f}")
    print(f"\nScore Components: {prediction.score_components}")
