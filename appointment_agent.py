"""
Appointment Recommendation Agent
==================================
Takes the output from the Diagnostics Agent (DiagnosticsOutput) plus the
overall triage result and produces a structured list of follow-up appointments
the patient needs to book after their ED visit.

Each appointment includes:
  - Specialty / appointment type
  - Urgency tier  (URGENT_24H | SOON_1WK | ROUTINE_1MO | ELECTIVE)
  - Timeframe     (plain English: "within 24 hours", "within 1 week", etc.)
  - Reason        (why this appointment is needed)
  - Prep notes    (what to bring / what to fast / etc.)
  - Booking hints (how to get the appointment — GP referral, self-refer, etc.)

Works fully offline — no LLM required. Uses a clinical knowledge base of
condition → specialist mappings, then enriches with lab/imaging follow-ups
derived directly from the diagnostics plan.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class AppointmentItem(BaseModel):
    specialty: str = Field(description="Specialty or appointment type")
    appointment_type: str = Field(description="e.g. 'Cardiology follow-up', 'Echocardiogram'")
    urgency: str = Field(description="URGENT_24H | SOON_1WK | ROUTINE_1MO | ELECTIVE")
    timeframe: str = Field(description="Plain-English timeframe: 'within 24 hours' etc.")
    reason: str = Field(description="Clinical reason this appointment is needed")
    prep_notes: List[str] = Field(default_factory=list, description="Preparation instructions")
    booking_hints: str = Field(description="How to book: GP referral, self-refer, etc.")
    triggered_by: str = Field(description="Which diagnosis/finding triggered this")


class AppointmentPlan(BaseModel):
    patient_id: str
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    esi_level: int
    appointments: List[AppointmentItem]
    urgent_count: int
    soon_count: int
    routine_count: int
    elective_count: int
    summary: str = Field(description="One-paragraph plain-English summary for the patient")
    discharge_instructions: List[str] = Field(
        description="Key instructions before the patient leaves the ED"
    )
    red_flags: List[str] = Field(
        description="Return-to-ED warning signs to watch for at home"
    )
    error: Optional[str] = None


# ============================================================================
# CLINICAL KNOWLEDGE BASE
# Condition/keyword → list of appointment dicts
# ============================================================================

_URGENCY_TIMEFRAMES = {
    "URGENT_24H":  "within 24 hours",
    "SOON_1WK":    "within 1 week",
    "ROUTINE_1MO": "within 1 month",
    "ELECTIVE":    "at your convenience (within 3 months)",
}

# Maps lowercase keywords found in diagnosis strings → appointment templates
_CONDITION_APPOINTMENTS: List[Dict[str, Any]] = [

    # ── CARDIOVASCULAR ───────────────────────────────────────────────────────
    {
        "keywords": ["acs", "acute coronary", "nstemi", "stemi", "unstable angina", "myocardial"],
        "specialty": "Cardiology",
        "appointment_type": "Cardiology follow-up (post-ACS)",
        "urgency": "URGENT_24H",
        "reason": "Post-ACS patients require urgent cardiology review to plan PCI/CABG, optimise antiplatelet therapy, and assess for arrhythmia or re-infarction.",
        "prep_notes": ["Bring all discharge medications", "Do not stop any cardiac medications without cardiologist approval", "Fast 4 hours if stress test or procedure likely"],
        "booking_hints": "Hospital cardiology clinic will usually arrange this before discharge. If not, call your cardiologist directly or go to nearest ED if symptoms recur.",
    },
    {
        "keywords": ["acs", "acute coronary", "nstemi", "stemi", "chest pain", "angina", "myocardial"],
        "specialty": "Cardiology",
        "appointment_type": "Echocardiogram",
        "urgency": "SOON_1WK",
        "reason": "Echocardiogram needed to assess left ventricular function and wall motion abnormalities following cardiac event.",
        "prep_notes": ["No special preparation required", "Wear comfortable, loose-fitting clothing"],
        "booking_hints": "Request referral from your cardiologist or primary care physician. Most hospitals offer outpatient echo within 1 week for urgent cases.",
    },
    {
        "keywords": ["aortic dissection", "dissection"],
        "specialty": "Cardiothoracic Surgery",
        "appointment_type": "Cardiothoracic surgery urgent review",
        "urgency": "URGENT_24H",
        "reason": "Aortic dissection requires urgent surgical assessment to determine need for operative repair.",
        "prep_notes": ["Strict blood pressure control until review", "Avoid strenuous activity"],
        "booking_hints": "This referral should be arranged by the ED before discharge. Do not leave without a confirmed appointment.",
    },
    {
        "keywords": ["heart failure", "cardiac failure", "pulmonary edema", "pulmonary oedema"],
        "specialty": "Cardiology",
        "appointment_type": "Heart failure clinic follow-up",
        "urgency": "SOON_1WK",
        "reason": "Heart failure patients need early outpatient review to titrate diuretics, ACE inhibitors, and beta-blockers.",
        "prep_notes": ["Weigh yourself daily — return to ED if weight increases >2kg in 2 days", "Bring list of all current medications", "Low-sodium diet"],
        "booking_hints": "Ask ED or your GP for a referral to the heart failure clinic. Many hospitals have rapid-access HF clinics.",
    },
    {
        "keywords": ["arrhythmia", "atrial fibrillation", "af ", "afib", "svt", "tachycardia", "palpitation"],
        "specialty": "Cardiology / Electrophysiology",
        "appointment_type": "Cardiology arrhythmia review",
        "urgency": "SOON_1WK",
        "reason": "Cardiac rhythm abnormality requires outpatient Holter monitoring and electrophysiology assessment.",
        "prep_notes": ["Keep a symptom diary noting when palpitations occur", "Avoid caffeine and alcohol", "Bring any previous ECG reports"],
        "booking_hints": "GP referral to cardiology outpatient clinic. Request Holter monitor if symptoms are intermittent.",
    },
    {
        "keywords": ["hypertension", "hypertensive", "high blood pressure"],
        "specialty": "Primary Care / Internal Medicine",
        "appointment_type": "Blood pressure review and medication management",
        "urgency": "SOON_1WK",
        "reason": "Uncontrolled or newly diagnosed hypertension needs medication review and target organ damage screening.",
        "prep_notes": ["Monitor blood pressure at home twice daily", "Reduce salt and alcohol intake", "Bring a log of your home BP readings"],
        "booking_hints": "Book with your primary care physician (PCP). Many pharmacies offer free BP monitoring.",
    },

    # ── PULMONARY ────────────────────────────────────────────────────────────
    {
        "keywords": ["pulmonary embolism", "pe ", "dvt", "deep vein thrombosis", "clot"],
        "specialty": "Hematology / Pulmonology",
        "appointment_type": "Anticoagulation clinic and PE follow-up",
        "urgency": "URGENT_24H",
        "reason": "Anticoagulation monitoring and clot burden reassessment essential within 24 hours of PE/DVT diagnosis.",
        "prep_notes": ["Take anticoagulant exactly as prescribed — do not skip doses", "Avoid NSAIDs and aspirin unless advised", "Watch for signs of bleeding"],
        "booking_hints": "Anticoagulation clinic referral should be arranged before ED discharge. Bring discharge paperwork to every appointment.",
    },
    {
        "keywords": ["pneumonia", "pneumothorax", "pleural effusion", "respiratory failure"],
        "specialty": "Pulmonology / Respiratory Medicine",
        "appointment_type": "Pulmonology follow-up",
        "urgency": "SOON_1WK",
        "reason": "Follow-up imaging and clinical review needed to confirm resolution and detect complications.",
        "prep_notes": ["Complete full antibiotic course if prescribed", "Repeat chest X-ray as instructed", "Avoid smoking"],
        "booking_hints": "GP or ED referral to pulmonology outpatient clinic.",
    },
    {
        "keywords": ["asthma", "copd", "chronic obstructive"],
        "specialty": "Pulmonology / Respiratory Medicine",
        "appointment_type": "Respiratory disease management review",
        "urgency": "ROUTINE_1MO",
        "reason": "Optimise inhaler technique, step up/down therapy, and assess for further exacerbation risk.",
        "prep_notes": ["Bring all inhalers to the appointment", "Note frequency of rescue inhaler use", "Track peak flow readings if possible"],
        "booking_hints": "Book through your PCP or request a pulmonology outpatient referral.",
    },

    # ── NEUROLOGICAL ─────────────────────────────────────────────────────────
    {
        "keywords": ["stroke", "tia", "transient ischemic", "cerebrovascular", "cva"],
        "specialty": "Neurology",
        "appointment_type": "Neurology stroke/TIA follow-up",
        "urgency": "URGENT_24H",
        "reason": "Post-TIA/stroke patients have high early re-stroke risk. Rapid neurology review, antiplatelet therapy optimisation, and carotid imaging are required.",
        "prep_notes": ["Do not drive until cleared by a physician", "Take antiplatelet/anticoagulant medication as prescribed", "Monitor for new weakness, speech problems, or vision changes — return to ED immediately if these occur"],
        "booking_hints": "Stroke clinic referral should be arranged from the ED. Many centres have same-day TIA clinics.",
    },
    {
        "keywords": ["seizure", "epilepsy", "convulsion"],
        "specialty": "Neurology",
        "appointment_type": "Neurology seizure review",
        "urgency": "SOON_1WK",
        "reason": "New or breakthrough seizure requires EEG, medication review, and driving restriction assessment.",
        "prep_notes": ["Do not drive until cleared by a neurologist (legal requirement in most states)", "Avoid heights, swimming alone, or operating heavy machinery", "Keep a seizure diary"],
        "booking_hints": "Ask ED for urgent neurology outpatient referral. First seizure clinics are often available within days.",
    },
    {
        "keywords": ["headache", "migraine", "intracranial"],
        "specialty": "Neurology",
        "appointment_type": "Neurology headache clinic",
        "urgency": "ROUTINE_1MO",
        "reason": "Recurrent or first severe headache requires neurological assessment and imaging review.",
        "prep_notes": ["Keep a headache diary (frequency, severity, triggers, duration)", "Note any associated vision changes or neurological symptoms"],
        "booking_hints": "GP referral to neurology outpatient clinic. Request MRI head if not already performed.",
    },

    # ── GASTROINTESTINAL ─────────────────────────────────────────────────────
    {
        "keywords": ["gi bleed", "gastrointestinal bleed", "upper gi", "lower gi", "hematemesis", "melena", "rectal bleed"],
        "specialty": "Gastroenterology",
        "appointment_type": "Urgent gastroenterology / endoscopy",
        "urgency": "URGENT_24H",
        "reason": "GI bleeding source must be confirmed and treated endoscopically within 24 hours to prevent rebleeding.",
        "prep_notes": ["Clear liquid diet until scope performed", "Do not take NSAIDs or blood thinners until reviewed", "Monitor for dizziness or black stools — return to ED immediately"],
        "booking_hints": "GI team will typically arrange inpatient endoscopy. If discharged, call gastroenterology directly for urgent outpatient scope.",
    },
    {
        "keywords": ["appendicitis", "cholecystitis", "pancreatitis", "bowel obstruction", "diverticulitis", "hernia"],
        "specialty": "General Surgery",
        "appointment_type": "General surgery follow-up",
        "urgency": "SOON_1WK",
        "reason": "Post-acute abdominal pathology requires surgical review to assess for elective repair or further management.",
        "prep_notes": ["Low-fat diet following pancreatitis or cholecystitis", "Return to ED immediately if pain worsens or you develop fever"],
        "booking_hints": "ED referral to general surgery outpatient clinic. Surgery coordinator can expedite.",
    },
    {
        "keywords": ["peptic ulcer", "gerd", "gastroesophageal", "esophageal"],
        "specialty": "Gastroenterology",
        "appointment_type": "Gastroenterology outpatient review",
        "urgency": "ROUTINE_1MO",
        "reason": "H. pylori testing, endoscopy, and acid suppression therapy optimisation.",
        "prep_notes": ["Take PPI as prescribed", "Avoid NSAIDs, alcohol, and spicy food", "Eat smaller, more frequent meals"],
        "booking_hints": "GP referral to gastroenterology. Consider H. pylori breath test before the appointment.",
    },

    # ── RENAL / UROLOGICAL ───────────────────────────────────────────────────
    {
        "keywords": ["kidney", "renal failure", "aki", "acute kidney", "ckd", "chronic kidney"],
        "specialty": "Nephrology",
        "appointment_type": "Nephrology renal function review",
        "urgency": "SOON_1WK",
        "reason": "Creatinine, electrolytes, and urine protein must be re-checked and causative medications reviewed.",
        "prep_notes": ["Increase fluid intake unless told otherwise", "Avoid NSAIDs and contrast dye", "Check potassium-raising supplements"],
        "booking_hints": "GP or ED referral to nephrology outpatient. Labs should be repeated within 48–72 hours.",
    },
    {
        "keywords": ["urinary tract infection", "uti", "pyelonephritis", "kidney infection"],
        "specialty": "Urology / Primary Care",
        "appointment_type": "Urine culture follow-up",
        "urgency": "SOON_1WK",
        "reason": "Confirm antibiotic sensitivity once culture results are available and ensure full resolution.",
        "prep_notes": ["Complete full antibiotic course", "Increase fluid intake", "Return if fever or loin pain returns"],
        "booking_hints": "Book with your PCP to review culture results. No specialist referral usually needed.",
    },

    # ── ENDOCRINE ────────────────────────────────────────────────────────────
    {
        "keywords": ["diabetes", "diabetic", "hyperglycemia", "dka", "hypoglycemia", "insulin"],
        "specialty": "Endocrinology / Diabetes Clinic",
        "appointment_type": "Diabetes management review",
        "urgency": "SOON_1WK",
        "reason": "Insulin or oral hypoglycaemic dose adjustment and HbA1c target review following acute episode.",
        "prep_notes": ["Monitor blood glucose at least 4× daily", "Carry fast-acting sugar at all times", "Bring glucose log and medication list"],
        "booking_hints": "Book urgent review with your endocrinologist or diabetes nurse educator. Most clinics have same-week slots for acute cases.",
    },
    {
        "keywords": ["thyroid", "hypothyroid", "hyperthyroid", "thyrotoxicosis"],
        "specialty": "Endocrinology",
        "appointment_type": "Thyroid function review",
        "urgency": "SOON_1WK",
        "reason": "TSH/T4 levels and medication dosing need optimisation.",
        "prep_notes": ["Take thyroid medication on an empty stomach", "Bring list of supplements (calcium and iron can interfere)"],
        "booking_hints": "GP referral to endocrinology outpatient clinic.",
    },

    # ── ORTHOPAEDIC / MSK ────────────────────────────────────────────────────
    {
        "keywords": ["fracture", "broken bone", "dislocation", "orthopaedic", "orthopedic"],
        "specialty": "Orthopaedics",
        "appointment_type": "Fracture clinic / orthopaedic review",
        "urgency": "URGENT_24H",
        "reason": "Fracture management, cast check, and surgical planning if operative fixation required.",
        "prep_notes": ["Keep the injured area elevated", "Do not weight-bear unless instructed", "Do not get the cast wet", "Return to ED if fingers/toes become numb, blue, or cold"],
        "booking_hints": "Fracture clinic is typically booked by the ED. Call the orthopaedic department if no appointment is given before discharge.",
    },
    {
        "keywords": ["sprain", "ligament", "tendon", "muscle tear", "msk", "musculoskeletal"],
        "specialty": "Orthopaedics / Sports Medicine / Physiotherapy",
        "appointment_type": "Physiotherapy and orthopaedic outpatient review",
        "urgency": "SOON_1WK",
        "reason": "MRI / ultrasound and physiotherapy assessment to guide rehabilitation and rule out structural damage.",
        "prep_notes": ["RICE: Rest, Ice, Compress, Elevate", "Take prescribed pain relief", "Avoid returning to sport until cleared"],
        "booking_hints": "GP referral to physiotherapy or orthopaedics outpatient. Self-referral to physio is possible in most areas.",
    },
    {
        "keywords": ["back pain", "spinal", "disc", "sciatica", "lumbar"],
        "specialty": "Orthopaedics / Pain Management / Physiotherapy",
        "appointment_type": "Spinal / back pain outpatient review",
        "urgency": "ROUTINE_1MO",
        "reason": "MRI spine and physiotherapy assessment to guide conservative vs. surgical management.",
        "prep_notes": ["Keep active with gentle walking", "Avoid bed rest for more than 1–2 days", "Heat packs may help"],
        "booking_hints": "GP referral to orthopaedics or pain management. Physiotherapy self-referral is usually available.",
    },

    # ── MENTAL HEALTH ────────────────────────────────────────────────────────
    {
        "keywords": ["overdose", "self-harm", "suicid", "psychiatric", "mental health crisis"],
        "specialty": "Psychiatry / Mental Health",
        "appointment_type": "Urgent psychiatric follow-up",
        "urgency": "URGENT_24H",
        "reason": "Mental health crisis assessment and safety planning must be completed within 24 hours of discharge.",
        "prep_notes": ["Do not be alone in the first 24 hours", "Remove access to means of self-harm from the home", "Crisis helpline: 988 Suicide and Crisis Lifeline"],
        "booking_hints": "Psychiatric liaison team should arrange follow-up before ED discharge. Crisis teams can also provide same-day home visits.",
    },

    # ── INFECTIOUS DISEASE ───────────────────────────────────────────────────
    {
        "keywords": ["sepsis", "septic", "bacteremia", "meningitis", "endocarditis"],
        "specialty": "Infectious Disease",
        "appointment_type": "Infectious disease follow-up and culture review",
        "urgency": "URGENT_24H",
        "reason": "Blood culture sensitivities must be reviewed to confirm appropriate antibiotic therapy and duration.",
        "prep_notes": ["Complete full antibiotic course — do not stop early", "Monitor temperature twice daily", "Return to ED if fever returns or you feel worse"],
        "booking_hints": "ID team typically reviews inpatients directly. Outpatient: request referral from ED or PCP.",
    },

    # ── OPHTHALMOLOGY ────────────────────────────────────────────────────────
    {
        "keywords": ["eye", "vision", "retinal", "glaucoma", "ocular"],
        "specialty": "Ophthalmology",
        "appointment_type": "Ophthalmology urgent review",
        "urgency": "URGENT_24H",
        "reason": "Acute visual symptoms risk permanent vision loss without urgent specialist assessment.",
        "prep_notes": ["Do not rub the eye", "Avoid driving if vision is impaired", "Bring glasses and contact lens case"],
        "booking_hints": "Most eye hospitals have urgent walk-in clinics. Call ahead to confirm.",
    },

    # ── PRIMARY CARE CATCH-ALL ───────────────────────────────────────────────
    {
        "keywords": ["_pcp_followup_"],  # always added for ESI 3–5
        "specialty": "Primary Care Physician (PCP)",
        "appointment_type": "Post-ED primary care follow-up",
        "urgency": "SOON_1WK",
        "reason": "General follow-up to review ED findings, update medications, and arrange any outstanding investigations.",
        "prep_notes": ["Bring all ED discharge paperwork", "Bring a current medication list", "Write down any questions you have"],
        "booking_hints": "Call your PCP's office the next business day to schedule a follow-up visit. Mention you were recently in the ED.",
    },
]


# ============================================================================
# RED FLAG LIBRARY  (condition → warning signs to return to ED)
# ============================================================================

_RED_FLAGS_BY_KEYWORD: Dict[str, List[str]] = {
    "cardiac|acs|chest pain|heart": [
        "Return to ED immediately if chest pain returns or worsens",
        "Sudden shortness of breath at rest",
        "Fainting or near-fainting",
        "Irregular or very fast heartbeat",
    ],
    "stroke|tia|neurological|seizure": [
        "Any new or returning weakness, numbness, or paralysis",
        "Sudden speech difficulty or confusion",
        "Sudden severe headache unlike any before",
        "Vision changes or loss",
    ],
    "sepsis|infection|fever": [
        "Temperature above 38.5°C / 101.3°F",
        "Confusion or altered consciousness",
        "Rash that spreads rapidly",
        "Unable to keep fluids down",
    ],
    "fracture|ortho|injury": [
        "Fingers or toes below the cast become numb, blue, or very cold",
        "Sudden increase in pain despite medication",
        "Signs of wound infection: redness spreading, pus, warm skin",
    ],
    "respiratory|breathing|asthma|copd|pe": [
        "Difficulty breathing or breathlessness at rest",
        "Coughing up blood",
        "Oxygen saturation below 94% on home pulse oximeter",
    ],
    "abdominal|gi|bowel": [
        "Sudden severe abdominal pain",
        "Vomiting blood or passing black/tarry stools",
        "Rigid or board-like abdomen",
    ],
}

_UNIVERSAL_RED_FLAGS = [
    "Sudden deterioration in your condition",
    "If you are unable to take prescribed medications",
    "Any new symptom that concerns you",
]

_DISCHARGE_INSTRUCTIONS_BASE = [
    "Take all prescribed medications as directed — do not stop unless advised by a doctor",
    "Attend all follow-up appointments listed in this plan",
    "Rest for 24 hours following your ED visit — avoid strenuous activity",
    "Ensure someone can drive you home and stay with you tonight if you were given sedating medication",
    "If you were given a prescription, fill it today",
]


# ============================================================================
# MATCHING LOGIC
# ============================================================================

def _normalise(text: str) -> str:
    return text.lower().strip()


def _text_matches_keywords(text: str, keywords: List[str]) -> bool:
    t = _normalise(text)
    for kw in keywords:
        if kw in t:
            return True
    return False


def _get_red_flags(all_text: str) -> List[str]:
    flags = list(_UNIVERSAL_RED_FLAGS)
    for pattern, flag_list in _RED_FLAGS_BY_KEYWORD.items():
        if any(re.search(kw, all_text, re.IGNORECASE) for kw in pattern.split("|")):
            flags.extend(flag_list)
    return list(dict.fromkeys(flags))  # deduplicate preserving order


def _build_discharge_instructions(esi_level: int, appointments: List[AppointmentItem]) -> List[str]:
    instructions = list(_DISCHARGE_INSTRUCTIONS_BASE)
    if esi_level <= 2:
        instructions.insert(0, "⚠ You were triaged as HIGH PRIORITY — please follow all discharge instructions carefully")
    urgent_appts = [a for a in appointments if a.urgency == "URGENT_24H"]
    if urgent_appts:
        appt_names = ", ".join(a.appointment_type for a in urgent_appts[:3])
        instructions.append(f"Book within 24 hours: {appt_names}")
    instructions.append("Keep this report with you and bring it to all follow-up appointments")
    return instructions


def _build_summary(
    patient_id: str,
    esi_level: int,
    appointments: List[AppointmentItem],
    diagnosis_primary: List[str],
) -> str:
    urgents  = [a for a in appointments if a.urgency == "URGENT_24H"]
    soons    = [a for a in appointments if a.urgency == "SOON_1WK"]
    routines = [a for a in appointments if a.urgency in ("ROUTINE_1MO", "ELECTIVE")]

    lines = []
    if diagnosis_primary:
        lines.append(f"Based on your assessment, your primary concerns are: {', '.join(diagnosis_primary[:3])}.")

    if urgents:
        lines.append(
            f"You need to book {len(urgents)} appointment(s) within 24 hours: "
            + ", ".join(a.appointment_type for a in urgents) + "."
        )
    if soons:
        lines.append(
            f"Within the next week, please arrange: "
            + ", ".join(a.appointment_type for a in soons) + "."
        )
    if routines:
        lines.append(
            f"Within the next month: "
            + ", ".join(a.appointment_type for a in routines) + "."
        )
    lines.append(
        "Bring all ED discharge paperwork and your medication list to every appointment. "
        "If your symptoms worsen before any appointment, return to the Emergency Department immediately."
    )
    return " ".join(lines)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def generate_appointment_plan(
    patient_id: str,
    diagnostics: Dict[str, Any],
    esi_level: int = 3,
    triage_decision: str = "",
    patient_name: str = "",
) -> AppointmentPlan:
    """
    Generate a follow-up appointment plan from a diagnostics output dict.

    Args:
        patient_id   : patient identifier
        diagnostics  : DiagnosticsOutput dict (or .model_dump())
        esi_level    : final ESI level from triage
        triage_decision : e.g. "EMERGENT", "URGENT"
        patient_name : optional name for personalisation

    Returns:
        AppointmentPlan
    """
    if not diagnostics:
        return AppointmentPlan(
            patient_id=patient_id,
            esi_level=esi_level,
            appointments=[],
            urgent_count=0, soon_count=0, routine_count=0, elective_count=0,
            summary="No diagnostics data available to generate appointment plan.",
            discharge_instructions=list(_DISCHARGE_INSTRUCTIONS_BASE),
            red_flags=list(_UNIVERSAL_RED_FLAGS),
            error="No diagnostics provided",
        )

    # Build a combined text blob for matching
    primary_diff  = diagnostics.get("primary_differential") or []
    secondary_diff = diagnostics.get("secondary_differential") or []
    interventions = diagnostics.get("immediate_interventions") or []
    labs          = diagnostics.get("labs_ordered") or []
    imaging       = diagnostics.get("imaging") or []
    rationale     = diagnostics.get("clinical_rationale") or ""

    all_diag_text = " ".join(primary_diff + secondary_diff + interventions + labs + imaging + [rationale]).lower()

    # ── Match appointments ────────────────────────────────────────────────────
    appointments: List[AppointmentItem] = []
    seen_types: set = set()

    for template in _CONDITION_APPOINTMENTS:
        keywords = template["keywords"]

        # Special PCP catch-all: add for ESI 3-5 always
        if keywords == ["_pcp_followup_"]:
            if esi_level >= 3 and "pcp_followup" not in seen_types:
                seen_types.add("pcp_followup")
                appointments.append(AppointmentItem(
                    specialty=template["specialty"],
                    appointment_type=template["appointment_type"],
                    urgency=template["urgency"],
                    timeframe=_URGENCY_TIMEFRAMES[template["urgency"]],
                    reason=template["reason"],
                    prep_notes=template.get("prep_notes", []),
                    booking_hints=template["booking_hints"],
                    triggered_by="General post-ED follow-up",
                ))
            continue

        if _text_matches_keywords(all_diag_text, keywords):
            key = template["appointment_type"]
            if key in seen_types:
                continue
            seen_types.add(key)

            # Escalate urgency for high ESI
            urgency = template["urgency"]
            if esi_level <= 2 and urgency == "SOON_1WK":
                urgency = "URGENT_24H"
            elif esi_level <= 2 and urgency == "ROUTINE_1MO":
                urgency = "SOON_1WK"

            # Find which diagnosis triggered it
            triggered = next(
                (d for d in primary_diff + secondary_diff
                 if any(kw in d.lower() for kw in keywords)),
                keywords[0].replace("_", " ").title(),
            )

            appointments.append(AppointmentItem(
                specialty=template["specialty"],
                appointment_type=template["appointment_type"],
                urgency=urgency,
                timeframe=_URGENCY_TIMEFRAMES[urgency],
                reason=template["reason"],
                prep_notes=template.get("prep_notes", []),
                booking_hints=template["booking_hints"],
                triggered_by=triggered,
            ))

    # ── Add lab/imaging follow-ups ────────────────────────────────────────────
    if any("troponin" in l.lower() for l in labs):
        if "Troponin serial" not in seen_types:
            seen_types.add("Troponin serial")
            appointments.append(AppointmentItem(
                specialty="Cardiology / Primary Care",
                appointment_type="Serial troponin recheck",
                urgency="URGENT_24H",
                timeframe=_URGENCY_TIMEFRAMES["URGENT_24H"],
                reason="Serial troponin levels (3h and 6h) needed to confirm or rule out myocardial injury.",
                prep_notes=["Do not eat within 2 hours of blood draw"],
                booking_hints="Return to ED or attend lab as instructed on discharge paperwork.",
                triggered_by="Labs: troponin ordered",
            ))

    if any("culture" in l.lower() for l in labs):
        if "Culture result review" not in seen_types:
            seen_types.add("Culture result review")
            appointments.append(AppointmentItem(
                specialty="Primary Care / Infectious Disease",
                appointment_type="Culture result review",
                urgency="SOON_1WK",
                timeframe=_URGENCY_TIMEFRAMES["SOON_1WK"],
                reason="Blood/urine/wound culture sensitivity results need review to confirm correct antibiotic selection.",
                prep_notes=["Complete antibiotic course in the meantime"],
                booking_hints="Your PCP will receive culture results. Book a follow-up call in 2–3 days.",
                triggered_by="Labs: culture ordered",
            ))

    if any("mri" in i.lower() or "ct" in i.lower() for i in imaging):
        if "Imaging result review" not in seen_types:
            seen_types.add("Imaging result review")
            appointments.append(AppointmentItem(
                specialty="Radiology / Referring Specialist",
                appointment_type="Imaging results review",
                urgency="SOON_1WK",
                timeframe=_URGENCY_TIMEFRAMES["SOON_1WK"],
                reason="Formal radiology report for CT/MRI scan must be reviewed with the referring specialist.",
                prep_notes=["Request a copy of the report for your own records"],
                booking_hints="Your ED physician or specialist will follow up on results. Call if you have not heard back within 5 days.",
                triggered_by="Imaging ordered during ED visit",
            ))

    # ── Sort by urgency priority ──────────────────────────────────────────────
    urgency_order = {"URGENT_24H": 0, "SOON_1WK": 1, "ROUTINE_1MO": 2, "ELECTIVE": 3}
    appointments.sort(key=lambda a: urgency_order.get(a.urgency, 4))

    # ── Counts ────────────────────────────────────────────────────────────────
    urgent_count  = sum(1 for a in appointments if a.urgency == "URGENT_24H")
    soon_count    = sum(1 for a in appointments if a.urgency == "SOON_1WK")
    routine_count = sum(1 for a in appointments if a.urgency == "ROUTINE_1MO")
    elective_count = sum(1 for a in appointments if a.urgency == "ELECTIVE")

    red_flags = _get_red_flags(all_diag_text)
    discharge_instructions = _build_discharge_instructions(esi_level, appointments)
    summary = _build_summary(patient_id, esi_level, appointments, primary_diff)

    return AppointmentPlan(
        patient_id=patient_id,
        esi_level=esi_level,
        appointments=appointments,
        urgent_count=urgent_count,
        soon_count=soon_count,
        routine_count=routine_count,
        elective_count=elective_count,
        summary=summary,
        discharge_instructions=discharge_instructions,
        red_flags=red_flags,
    )


# ============================================================================
# CLI DEMO
# ============================================================================

if __name__ == "__main__":
    _sample_diag = {
        "primary_differential": ["Acute Coronary Syndrome — NSTEMI", "Unstable Angina", "Pulmonary Embolism"],
        "secondary_differential": ["Aortic Dissection", "Hypertensive Emergency"],
        "immediate_interventions": ["12-lead ECG", "Aspirin 325mg", "IV access"],
        "labs_ordered": ["Troponin I (serial)", "BMP", "CBC", "Blood culture"],
        "imaging": ["Chest X-ray", "CT angiography"],
        "clinical_rationale": "Classic ACS presentation in a patient with known coronary artery disease.",
    }

    plan = generate_appointment_plan(
        patient_id="P00001",
        diagnostics=_sample_diag,
        esi_level=2,
        patient_name="Alice Thompson",
    )

    print(f"\nAppointment Plan — {plan.patient_id}")
    print(f"Total: {len(plan.appointments)}  |  Urgent 24h: {plan.urgent_count}  "
          f"|  Soon 1wk: {plan.soon_count}  |  Routine: {plan.routine_count}")
    print(f"\nSummary:\n  {plan.summary}")
    print("\nAppointments:")
    for a in plan.appointments:
        print(f"  [{a.urgency}] {a.appointment_type} ({a.specialty})")
        print(f"    Reason: {a.reason[:80]}")
        print(f"    Book:   {a.booking_hints[:80]}")
    print("\nDischarge Instructions:")
    for d in plan.discharge_instructions:
        print(f"  • {d}")
    print("\nReturn to ED if:")
    for r in plan.red_flags[:5]:
        print(f"  ⚠ {r}")
