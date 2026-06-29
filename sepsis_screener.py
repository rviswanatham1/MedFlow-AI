"""
Sepsis Screener — qSOFA Early Warning

Fast, deterministic 3-point qSOFA screen. Runs before any LLM call.
Positive result (≥2) injects sepsis context into the triage pipeline.

qSOFA criteria (Seymour 2016 / Singer 2016 Sepsis-3):
  1. Respiratory Rate ≥ 22/min
  2. Altered mentation (not fully ALERT on AVPU)
  3. Systolic BP ≤ 100 mmHg
"""

from datetime import datetime
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class SepsisScreenResult(BaseModel):
    patient_id: str
    qsofa_score: int = Field(description="qSOFA score 0-3")
    qsofa_components: Dict[str, bool] = Field(
        description="Which qSOFA criteria were positive"
    )
    sepsis_concern: bool = Field(description="True if qSOFA ≥ 2")
    recommendation: str
    fever_detected: bool = Field(description="Temperature >38.3°C or <36.0°C")
    hypoxia_detected: bool = Field(description="SpO2 < 94%")
    sepsis_injection_text: str = Field(
        description="Text to prepend to symptoms_text if sepsis_concern is True"
    )
    screened_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# ============================================================================
# SCREEN FUNCTION
# ============================================================================

def screen_for_sepsis(
    patient_id: str,
    vitals: Dict[str, Any],
) -> SepsisScreenResult:
    """
    Run qSOFA sepsis screening on patient vitals.

    Args:
        patient_id: Patient identifier
        vitals: Standard vitals dict (temperature, heart_rate, respiratory_rate,
                blood_pressure, oxygen_sat, consciousness)

    Returns:
        SepsisScreenResult with qSOFA score and clinical recommendation
    """
    components: Dict[str, bool] = {
        "tachypnea_rr_ge_22": False,
        "hypotension_sbp_le_100": False,
        "altered_mentation": False,
    }
    qsofa = 0

    # Criterion 1: Respiratory Rate ≥ 22/min
    rr = vitals.get("respiratory_rate")
    if rr is not None:
        try:
            if int(rr) >= 22:
                components["tachypnea_rr_ge_22"] = True
                qsofa += 1
        except (ValueError, TypeError):
            pass

    # Criterion 2: Systolic BP ≤ 100 mmHg
    bp = vitals.get("blood_pressure", "")
    if bp and bp not in ("Not recorded", ""):
        try:
            systolic = int(str(bp).split('/')[0].strip())
            if systolic <= 100:
                components["hypotension_sbp_le_100"] = True
                qsofa += 1
        except (ValueError, IndexError):
            pass

    # Criterion 3: Altered mentation
    consciousness = str(vitals.get("consciousness", "ALERT")).upper()
    if consciousness != "ALERT":
        components["altered_mentation"] = True
        qsofa += 1

    # Supplementary flags (not part of qSOFA but clinically relevant)
    temp = vitals.get("temperature")
    fever_detected = False
    if temp is not None:
        try:
            t = float(temp)
            fever_detected = t > 38.3 or t < 36.0
        except (ValueError, TypeError):
            pass

    spo2 = vitals.get("oxygen_sat")
    hypoxia_detected = False
    if spo2 is not None:
        try:
            hypoxia_detected = float(spo2) < 94.0
        except (ValueError, TypeError):
            pass

    # Recommendation text
    if qsofa >= 2:
        active = [k for k, v in components.items() if v]
        components_desc = ", ".join(active).replace("_", " ")
        recommendation = (
            f"qSOFA POSITIVE ({qsofa}/3: {components_desc}). "
            "INITIATE SEPSIS PROTOCOL: blood cultures ×2, serum lactate, CBC, BMP, CXR. "
            "IV access ×2 — aggressive fluid resuscitation. "
            "Notify attending physician IMMEDIATELY. Early broad-spectrum antibiotics."
        )
    elif qsofa == 1:
        recommendation = (
            "qSOFA 1/3 — borderline. Monitor closely and reassess in 15 minutes. "
            "If clinical suspicion persists, consider sepsis workup."
        )
    else:
        recommendation = "qSOFA 0/3 — low immediate sepsis concern from vital signs alone."

    # Injection text prepended to symptoms_text when sepsis_concern is True
    if qsofa >= 2:
        injection = (
            f"[SEPSIS ALERT — qSOFA {qsofa}/3 POSITIVE: "
            + ", ".join(k for k, v in components.items() if v).replace("_", " ")
            + "] "
        )
    else:
        injection = ""

    return SepsisScreenResult(
        patient_id=patient_id,
        qsofa_score=qsofa,
        qsofa_components=components,
        sepsis_concern=qsofa >= 2,
        recommendation=recommendation,
        fever_detected=fever_detected,
        hypoxia_detected=hypoxia_detected,
        sepsis_injection_text=injection,
    )


# ============================================================================
# CLI DEMO
# ============================================================================

if __name__ == "__main__":
    test_cases = [
        ("P00001", {"respiratory_rate": 24, "blood_pressure": "95/60", "consciousness": "VOICE",
                    "temperature": 38.8, "oxygen_sat": 93}),
        ("P00002", {"respiratory_rate": 16, "blood_pressure": "118/76", "consciousness": "ALERT",
                    "temperature": 37.1, "oxygen_sat": 98}),
        ("P00003", {"respiratory_rate": 23, "blood_pressure": "98/62", "consciousness": "ALERT",
                    "temperature": 39.1, "oxygen_sat": 91}),
    ]

    for pid, vitals in test_cases:
        result = screen_for_sepsis(pid, vitals)
        print(f"\nPatient {pid}:")
        print(f"  qSOFA: {result.qsofa_score}/3  |  Sepsis concern: {result.sepsis_concern}")
        print(f"  Components: {result.qsofa_components}")
        print(f"  Fever: {result.fever_detected}  |  Hypoxia: {result.hypoxia_detected}")
        print(f"  Recommendation: {result.recommendation}")
