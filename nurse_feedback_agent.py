"""
Nurse Feedback Agent — Human-in-the-Loop Learning System

Nurses can override AI-assigned ESI levels with a reason.
The system accumulates corrections in nurse_corrections.json,
derives per-symptom-category adjustment weights from correction history,
and applies learned bias to future ESI assignments.

This introduces an adaptive, nurse-supervised learning loop without
requiring model retraining — purely statistical weight adjustment.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from pydantic import BaseModel, Field


DEFAULT_CORRECTIONS_PATH = "nurse_corrections.json"

# Minimum corrections per category before weights are applied
MIN_CORRECTIONS_FOR_ADJUSTMENT = 3

# Minimum mean delta magnitude to trigger an ESI change
ADJUSTMENT_THRESHOLD = 0.50

# Symptom category mappings (mirrors US_ED_HIGH_ACUITY_FLAGS structure)
_CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "cardiovascular": [
        "chest pain", "chest tightness", "chest pressure", "palpitations",
        "cardiac arrest", "aortic dissection", "myocardial infarction",
    ],
    "neurological": [
        "seizure", "stroke", "facial droop", "aphasia", "dysarthria",
        "altered mental status", "confusion", "thunderclap headache",
        "loss of consciousness", "syncope", "weakness",
    ],
    "respiratory": [
        "shortness of breath", "stridor", "wheezing", "hemoptysis",
        "respiratory failure", "cough",
    ],
    "abdominal": [
        "abdominal pain", "hematemesis", "hematochezia", "melena",
        "vomiting", "nausea", "diarrhea",
    ],
    "infectious": [
        "fever", "sepsis", "chills", "rigors", "rash",
    ],
    "trauma": [
        "active bleeding", "laceration", "trauma", "fall injury",
        "burn injury", "contusion",
    ],
    "metabolic": [
        "hypoglycemia", "diabetic", "edema", "dizziness",
    ],
    "mental_health": [
        "suicidal", "psychosis", "self-harm", "agitation",
    ],
}


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class NurseCorrection(BaseModel):
    correction_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    ai_esi_level: int = Field(description="ESI level assigned by AI (1-5)")
    nurse_esi_level: int = Field(description="ESI level assigned by nurse after override (1-5)")
    correction_delta: int = Field(
        description="nurse_esi_level - ai_esi_level. Negative = nurse upgraded urgency."
    )
    symptom_category: str = Field(description="Inferred symptom category of this case")
    symptoms: List[str] = Field(default_factory=list)
    nurse_id: str = Field(default="UNKNOWN")
    reason: str = Field(default="")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class AdjustmentWeights(BaseModel):
    weights: Dict[str, float] = Field(
        description="Mean correction delta per symptom category"
    )
    sample_counts: Dict[str, int] = Field(
        description="Number of corrections per category"
    )
    computed_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class FeedbackResult(BaseModel):
    correction_id: str
    accepted: bool
    updated_weights: AdjustmentWeights
    message: str


class CorrectionSummary(BaseModel):
    total_corrections: int
    corrections_by_category: Dict[str, int]
    mean_delta_by_category: Dict[str, float]
    most_upgraded_category: Optional[str] = Field(
        description="Category where AI was most often too low (nurse upgraded urgency)"
    )
    most_downgraded_category: Optional[str] = Field(
        description="Category where AI was most often too high (nurse downgraded urgency)"
    )
    overall_mean_delta: float
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# ============================================================================
# PERSISTENCE HELPERS
# ============================================================================

def load_corrections(path: str = DEFAULT_CORRECTIONS_PATH) -> List[NurseCorrection]:
    """Load corrections from JSON file. Returns empty list if file missing."""
    corrections_path = Path(path)
    if not corrections_path.exists():
        return []
    try:
        with open(corrections_path, "r") as f:
            data = json.load(f)
        return [NurseCorrection(**item) for item in data]
    except Exception:
        return []


def save_corrections(
    corrections: List[NurseCorrection],
    path: str = DEFAULT_CORRECTIONS_PATH,
) -> None:
    """Serialize corrections list to JSON file."""
    with open(path, "w") as f:
        json.dump(
            [c.dict() for c in corrections],
            f,
            indent=2,
            default=str,
        )


# ============================================================================
# CATEGORY INFERENCE
# ============================================================================

def _infer_symptom_category(symptoms: List[str]) -> str:
    """
    Infer the primary clinical category from symptom list.
    Returns 'general' if no category matches.
    """
    symptoms_lower = [s.lower() for s in symptoms]
    category_scores: Dict[str, int] = {}

    for category, keywords in _CATEGORY_KEYWORDS.items():
        hits = sum(
            1 for kw in keywords
            for sym in symptoms_lower
            if kw in sym or sym in kw
        )
        if hits > 0:
            category_scores[category] = hits

    if not category_scores:
        return "general"

    return max(category_scores, key=lambda c: category_scores[c])


# ============================================================================
# WEIGHT COMPUTATION
# ============================================================================

def compute_adjustment_weights(
    corrections: List[NurseCorrection],
) -> AdjustmentWeights:
    """
    Compute mean correction delta per symptom category.
    A negative mean delta means nurses typically upgrade urgency (lower ESI number)
    for that category — AI is under-triaging those cases.
    """
    category_deltas: Dict[str, List[int]] = {}

    for correction in corrections:
        cat = correction.symptom_category
        category_deltas.setdefault(cat, []).append(correction.correction_delta)

    weights: Dict[str, float] = {}
    sample_counts: Dict[str, int] = {}

    for cat, deltas in category_deltas.items():
        weights[cat] = round(sum(deltas) / len(deltas), 3)
        sample_counts[cat] = len(deltas)

    return AdjustmentWeights(
        weights=weights,
        sample_counts=sample_counts,
    )


# ============================================================================
# PUBLIC API
# ============================================================================

def submit_correction(
    patient_id: str,
    ai_esi_level: int,
    nurse_esi_level: int,
    symptoms: List[str],
    nurse_id: str,
    reason: str,
    path: str = DEFAULT_CORRECTIONS_PATH,
) -> FeedbackResult:
    """
    Record a nurse override of the AI triage decision.

    Args:
        patient_id: Patient being overridden
        ai_esi_level: ESI level assigned by AI (1-5)
        nurse_esi_level: ESI level assigned by nurse (1-5)
        symptoms: Patient symptom list (for category inference)
        nurse_id: Nurse identifier
        reason: Clinical reason for override
        path: Path to corrections JSON file

    Returns:
        FeedbackResult with correction_id and updated weights
    """
    # Clamp ESI levels
    ai_esi = max(1, min(5, ai_esi_level))
    nurse_esi = max(1, min(5, nurse_esi_level))

    category = _infer_symptom_category(symptoms)

    correction = NurseCorrection(
        patient_id=patient_id,
        ai_esi_level=ai_esi,
        nurse_esi_level=nurse_esi,
        correction_delta=nurse_esi - ai_esi,
        symptom_category=category,
        symptoms=symptoms,
        nurse_id=nurse_id,
        reason=reason,
    )

    corrections = load_corrections(path)
    corrections.append(correction)
    save_corrections(corrections, path)

    updated_weights = compute_adjustment_weights(corrections)

    direction = ""
    if correction.correction_delta < 0:
        direction = f"Upgraded urgency: ESI {ai_esi} → ESI {nurse_esi} (more urgent)"
    elif correction.correction_delta > 0:
        direction = f"Downgraded urgency: ESI {ai_esi} → ESI {nurse_esi} (less urgent)"
    else:
        direction = "No ESI change recorded"

    return FeedbackResult(
        correction_id=correction.correction_id,
        accepted=True,
        updated_weights=updated_weights,
        message=(
            f"Correction recorded (ID: {correction.correction_id}). "
            f"Category: {category}. {direction}. "
            f"Total corrections in category: {updated_weights.sample_counts.get(category, 1)}."
        ),
    )


def get_adjusted_esi(
    esi_level: int,
    symptoms: List[str],
    path: str = DEFAULT_CORRECTIONS_PATH,
) -> Tuple[int, str]:
    """
    Apply learned nurse correction weights to an AI-assigned ESI level.

    Returns:
        (adjusted_esi_level: int, rationale: str)
    """
    corrections = load_corrections(path)

    if not corrections:
        return esi_level, "No nurse corrections on record — no adjustment applied."

    weights = compute_adjustment_weights(corrections)
    category = _infer_symptom_category(symptoms)
    n = weights.sample_counts.get(category, 0)

    if n < MIN_CORRECTIONS_FOR_ADJUSTMENT:
        return (
            esi_level,
            f"Insufficient correction history for category '{category}' "
            f"(n={n}, minimum={MIN_CORRECTIONS_FOR_ADJUSTMENT}) — no adjustment applied.",
        )

    mean_delta = weights.weights.get(category, 0.0)

    if abs(mean_delta) < ADJUSTMENT_THRESHOLD:
        return (
            esi_level,
            f"Category '{category}' mean correction delta {mean_delta:+.2f} "
            f"below threshold ±{ADJUSTMENT_THRESHOLD} — no adjustment applied.",
        )

    # Apply rounded adjustment (negative delta = nurses upgraded = lower ESI)
    adjustment = round(mean_delta)  # round to nearest integer
    adjusted = max(1, min(5, esi_level + adjustment))

    direction = "upgraded (more urgent)" if adjustment < 0 else "downgraded (less urgent)"
    rationale = (
        f"Nurse corrections for '{category}' presentations average "
        f"{mean_delta:+.2f} ESI points (n={n} corrections) — "
        f"{direction}: ESI {esi_level} → ESI {adjusted}."
    )

    return adjusted, rationale


def get_correction_summary(path: str = DEFAULT_CORRECTIONS_PATH) -> CorrectionSummary:
    """Return statistical summary of all nurse corrections."""
    corrections = load_corrections(path)

    if not corrections:
        return CorrectionSummary(
            total_corrections=0,
            corrections_by_category={},
            mean_delta_by_category={},
            most_upgraded_category=None,
            most_downgraded_category=None,
            overall_mean_delta=0.0,
        )

    weights = compute_adjustment_weights(corrections)
    by_category = dict(weights.sample_counts)

    overall_delta = sum(c.correction_delta for c in corrections) / len(corrections)

    # Most upgraded = most negative mean delta (AI was too low, nurses bumped up urgency)
    most_upgraded = None
    most_downgraded = None

    if weights.weights:
        most_upgraded = min(weights.weights, key=lambda k: weights.weights[k])
        most_downgraded = max(weights.weights, key=lambda k: weights.weights[k])
        # Only report if meaningful
        if weights.weights[most_upgraded] >= 0:
            most_upgraded = None
        if weights.weights[most_downgraded] <= 0:
            most_downgraded = None

    return CorrectionSummary(
        total_corrections=len(corrections),
        corrections_by_category=by_category,
        mean_delta_by_category={k: round(v, 3) for k, v in weights.weights.items()},
        most_upgraded_category=most_upgraded,
        most_downgraded_category=most_downgraded,
        overall_mean_delta=round(overall_delta, 3),
    )


# ============================================================================
# CLI DEMO
# ============================================================================

if __name__ == "__main__":
    # Demo: simulate 5 nurse corrections for cardiovascular cases
    test_corrections = [
        ("P00001", 3, 2, ["chest pain", "diaphoresis"], "N001", "Patient more distressed than AI scored"),
        ("P00002", 3, 2, ["chest tightness", "palpitations"], "N002", "Cardiac history warrants higher priority"),
        ("P00003", 3, 2, ["chest pain", "shortness of breath"], "N001", "Elevated troponin risk"),
        ("P00004", 4, 4, ["abdominal pain"], "N003", "Agreed with AI assessment"),
        ("P00005", 4, 3, ["abdominal pain", "fever"], "N001", "Signs of peritonitis on exam"),
    ]

    print("Submitting nurse corrections...")
    for pid, ai_esi, nurse_esi, symptoms, nurse_id, reason in test_corrections:
        result = submit_correction(pid, ai_esi, nurse_esi, symptoms, nurse_id, reason)
        print(f"  {result.message}")

    print("\n--- Testing get_adjusted_esi ---")
    # Should apply cardiovascular weight (3 corrections, mean delta ~ -1.0)
    new_esi, rationale = get_adjusted_esi(3, ["chest pain", "diaphoresis"])
    print(f"Original ESI: 3 → Adjusted ESI: {new_esi}")
    print(f"Rationale: {rationale}")

    print("\n--- Correction Summary ---")
    summary = get_correction_summary()
    print(f"Total corrections: {summary.total_corrections}")
    print(f"By category: {summary.corrections_by_category}")
    print(f"Mean delta by category: {summary.mean_delta_by_category}")
    print(f"Most upgraded category: {summary.most_upgraded_category}")
    print(f"Overall mean delta: {summary.overall_mean_delta}")
