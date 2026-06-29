"""
Specialist Assignment Agent

Given a completed triage result, assigns the case to the most appropriate
medical specialist or department using an LLM (Gemini or DeepSeek/Ollama).
Falls back to keyword-based assignment if the LLM is unavailable.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from llm_provider import get_llm


# ============================================================================
# DATA MODELS
# ============================================================================

class SpecialistInput(BaseModel):
    patient_id: str
    esi_level: int
    triage_decision: str
    primary_differential: List[str] = Field(default_factory=list)
    secondary_differential: List[str] = Field(default_factory=list)
    clinical_reasoning: str = ""
    extracted_symptoms: List[str] = Field(default_factory=list)
    patient_age: Optional[int] = None
    patient_gender: Optional[str] = None
    vitals: Dict[str, Any] = Field(default_factory=dict)
    sepsis_concern: bool = False
    labs_ordered: List[str] = Field(default_factory=list)
    imaging: List[str] = Field(default_factory=list)


class SpecialistAssignment(BaseModel):
    patient_id: str
    primary_specialist: str = Field(
        description="Primary specialist type, e.g. 'Cardiologist', 'Neurologist'"
    )
    department: str = Field(
        description="Target department or unit, e.g. 'Cardiac Care Unit', 'Medical ICU'"
    )
    reason: str = Field(
        description="Clinical justification for this specialist selection"
    )
    secondary_specialist: Optional[str] = Field(
        default=None,
        description="Secondary specialist if multi-system involvement"
    )
    urgency_for_specialist: str = Field(
        description="IMMEDIATE | WITHIN_1H | WITHIN_4H | ROUTINE"
    )
    handoff_instructions: str = Field(
        description="Key clinical points for the specialist handoff"
    )
    estimated_disposition: str = Field(
        description="ADMIT | OBSERVE | DISCHARGE"
    )
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    error: Optional[str] = None


# ============================================================================
# KEYWORD-BASED FALLBACK
# ============================================================================

_SPECIALIST_RULES: List[Dict[str, Any]] = [
    {
        "keywords": ["chest pain", "acs", "nstemi", "stemi", "myocardial", "cardiac", "arrhythmia",
                     "heart failure", "angina", "troponin", "coronary", "palpitation", "afib",
                     "atrial fibrillation", "ventricular", "cardiogenic"],
        "specialist": "Cardiologist",
        "department": "Cardiac Care Unit",
        "disposition": "ADMIT",
    },
    {
        "keywords": ["stroke", "tia", "transient ischemic", "focal neurological", "seizure",
                     "altered mental", "confusion", "meningitis", "encephalitis",
                     "intracranial", "subarachnoid", "subdural", "epidural hematoma"],
        "specialist": "Neurologist",
        "department": "Neurology / Neurocritical Care",
        "disposition": "ADMIT",
    },
    {
        "keywords": ["respiratory distress", "copd", "asthma", "pneumonia", "pulmonary embolism",
                     "pe", "pneumothorax", "pleural effusion", "hemoptysis", "bronchitis",
                     "respiratory failure", "hypoxia"],
        "specialist": "Pulmonologist",
        "department": "Respiratory Medicine",
        "disposition": "ADMIT",
    },
    {
        "keywords": ["abdominal pain", "gi bleed", "gastrointestinal bleed", "pancreatitis",
                     "appendicitis", "diverticulitis", "bowel obstruction", "cholecystitis",
                     "hepatitis", "cirrhosis", "peptic ulcer", "crohn", "colitis",
                     "nausea vomiting", "melena", "hematochezia"],
        "specialist": "Gastroenterologist",
        "department": "Gastroenterology / General Medicine",
        "disposition": "OBSERVE",
    },
    {
        "keywords": ["fracture", "dislocation", "joint pain", "musculoskeletal", "orthopedic",
                     "tendon", "ligament", "bone", "hip", "knee", "shoulder",
                     "spinal cord", "back pain", "neck pain"],
        "specialist": "Orthopedist",
        "department": "Orthopedics",
        "disposition": "OBSERVE",
    },
    {
        "keywords": ["aortic dissection", "aortic aneurysm", "peripheral vascular",
                     "limb ischemia", "deep vein thrombosis", "dvt", "vascular"],
        "specialist": "Vascular Surgeon",
        "department": "Vascular Surgery",
        "disposition": "ADMIT",
    },
    {
        "keywords": ["trauma", "blunt trauma", "penetrating", "laceration", "hemorrhage",
                     "polytrauma", "internal bleeding"],
        "specialist": "Trauma Surgeon",
        "department": "Trauma Surgery / Surgical ICU",
        "disposition": "ADMIT",
    },
    {
        "keywords": ["sepsis", "bacteremia", "endocarditis", "osteomyelitis",
                     "hiv", "opportunistic infection"],
        "specialist": "Infectious Disease Specialist",
        "department": "Infectious Disease / Medical Unit",
        "disposition": "ADMIT",
    },
    {
        "keywords": ["renal failure", "acute kidney", "hyperkalemia", "hyponatremia",
                     "electrolyte", "metabolic acidosis", "dialysis"],
        "specialist": "Nephrologist",
        "department": "Nephrology / Renal Unit",
        "disposition": "ADMIT",
    },
    {
        "keywords": ["diabetic ketoacidosis", "dka", "hyperglycemia", "hypoglycemia",
                     "thyroid storm", "addisonian crisis", "endocrine"],
        "specialist": "Endocrinologist",
        "department": "Endocrinology / General Medicine",
        "disposition": "ADMIT",
    },
    {
        "keywords": ["renal colic", "kidney stone", "urinary retention", "urological",
                     "hematuria", "prostate"],
        "specialist": "Urologist",
        "department": "Urology",
        "disposition": "OBSERVE",
    },
    {
        "keywords": ["overdose", "poisoning", "toxic", "toxicology", "substance",
                     "alcohol withdrawal", "drug ingestion"],
        "specialist": "Toxicologist",
        "department": "Toxicology / Emergency Medicine",
        "disposition": "OBSERVE",
    },
    {
        "keywords": ["psychiatric", "suicidal", "psychosis", "schizophrenia",
                     "bipolar", "anxiety", "panic", "depression", "self-harm"],
        "specialist": "Psychiatrist",
        "department": "Psychiatric Emergency Services",
        "disposition": "OBSERVE",
    },
    {
        "keywords": ["obstetric", "pregnancy", "eclampsia", "preeclampsia",
                     "ectopic", "placenta", "labour", "miscarriage", "gynecological"],
        "specialist": "Obstetrician / Gynecologist",
        "department": "OB/GYN Unit",
        "disposition": "ADMIT",
    },
    {
        "keywords": ["oncology", "cancer", "tumor", "leukemia", "lymphoma",
                     "neutropenic fever", "chemotherapy"],
        "specialist": "Oncologist",
        "department": "Oncology / Hematology",
        "disposition": "ADMIT",
    },
]

_URGENCY_BY_ESI = {
    1: "IMMEDIATE",
    2: "IMMEDIATE",
    3: "WITHIN_1H",
    4: "WITHIN_4H",
    5: "ROUTINE",
}


def _keyword_fallback(inp: SpecialistInput) -> SpecialistAssignment:
    """Deterministic fallback: keyword matching against all clinical text."""
    combined_text = " ".join(
        inp.primary_differential + inp.secondary_differential +
        inp.extracted_symptoms + [inp.clinical_reasoning]
    ).lower()

    matched_rule: Optional[Dict[str, Any]] = None
    for rule in _SPECIALIST_RULES:
        if any(kw in combined_text for kw in rule["keywords"]):
            matched_rule = rule
            break

    urgency = _URGENCY_BY_ESI.get(inp.esi_level, "WITHIN_1H")

    if matched_rule:
        disposition = matched_rule["disposition"]
        if inp.esi_level <= 2 and disposition == "OBSERVE":
            disposition = "ADMIT"
        return SpecialistAssignment(
            patient_id=inp.patient_id,
            primary_specialist=matched_rule["specialist"],
            department=matched_rule["department"],
            reason=(
                f"Clinical presentation consistent with {inp.primary_differential[0] if inp.primary_differential else 'undifferentiated illness'}. "
                f"Keyword match triggered {matched_rule['specialist']} referral."
            ),
            urgency_for_specialist=urgency,
            handoff_instructions=(
                f"ESI {inp.esi_level} — {inp.triage_decision}. "
                f"Primary differential: {', '.join(inp.primary_differential[:3])}. "
                "Please review triage notes and diagnostics plan."
            ),
            estimated_disposition=disposition,
        )
    else:
        return SpecialistAssignment(
            patient_id=inp.patient_id,
            primary_specialist="Emergency Medicine Physician",
            department="Emergency Department",
            reason="Presentation does not match a single-specialty pattern; managed by EM team.",
            urgency_for_specialist=urgency,
            handoff_instructions=(
                f"ESI {inp.esi_level}. Symptoms: {', '.join(inp.extracted_symptoms[:5])}. "
                "General EM assessment and workup ongoing."
            ),
            estimated_disposition="OBSERVE" if inp.esi_level <= 3 else "DISCHARGE",
        )


# ============================================================================
# LLM PROMPT
# ============================================================================

_SPECIALIST_SYSTEM_PROMPT = """You are a senior Emergency Department attending physician.
Your role is to assign the most appropriate medical specialist(s) for each patient based on their triage information.

SPECIALIST OPTIONS (use the exact names):
- Emergency Medicine Physician (undifferentiated / multi-system / minor)
- Cardiologist (cardiac, ACS, arrhythmia, heart failure)
- Neurologist (stroke, TIA, seizure, altered consciousness)
- Pulmonologist (respiratory failure, COPD, asthma, PE, pneumonia)
- Gastroenterologist (GI bleed, pancreatitis, abdominal pain, hepatic)
- General Surgeon (appendicitis, bowel obstruction, hernia, cholecystitis)
- Orthopedist (fractures, dislocations, musculoskeletal)
- Vascular Surgeon (aortic dissection, limb ischemia, DVT)
- Trauma Surgeon (polytrauma, penetrating injury, haemorrhage)
- Infectious Disease Specialist (sepsis, endocarditis, complex infections)
- Nephrologist (acute renal failure, electrolyte emergencies, dialysis)
- Endocrinologist (DKA, thyroid storm, adrenal crisis)
- Urologist (renal colic, retention, haematuria)
- Toxicologist (overdose, poisoning, withdrawal)
- Psychiatrist (psychiatric emergency, suicidal ideation, psychosis)
- Obstetrician / Gynecologist (obstetric emergencies, gynaecological)
- Oncologist (oncologic emergency, neutropenic fever)
- General Physician / Internist (general medical admission, unclear aetiology)

URGENCY LEVELS:
- IMMEDIATE: Specialist at bedside now (ESI 1-2 critical)
- WITHIN_1H: Specialist consult within 1 hour (ESI 2-3 high)
- WITHIN_4H: Specialist available within 4 hours (ESI 3-4)
- ROUTINE: Next available specialist (ESI 4-5)

DISPOSITION OPTIONS: ADMIT | OBSERVE | DISCHARGE

Respond ONLY with valid JSON matching this schema:
{
  "primary_specialist": "<specialist type>",
  "department": "<department or unit name>",
  "reason": "<1-2 sentence clinical justification>",
  "secondary_specialist": "<second specialist or null>",
  "urgency_for_specialist": "<IMMEDIATE|WITHIN_1H|WITHIN_4H|ROUTINE>",
  "handoff_instructions": "<key clinical points for specialist handoff, max 2 sentences>",
  "estimated_disposition": "<ADMIT|OBSERVE|DISCHARGE>"
}"""


def _build_specialist_prompt(inp: SpecialistInput) -> str:
    age_str = f"{inp.patient_age} years old" if inp.patient_age else "age unknown"
    gender_str = inp.patient_gender or "unknown"
    vitals_parts = []
    for k, v in (inp.vitals or {}).items():
        vitals_parts.append(f"{k.replace('_', ' ').title()}: {v}")
    vitals_str = ", ".join(vitals_parts) if vitals_parts else "Not provided"

    return f"""{_SPECIALIST_SYSTEM_PROMPT}

--- PATIENT TRIAGE DATA ---
Patient ID     : {inp.patient_id}
Age / Gender   : {age_str} / {gender_str}
ESI Level      : {inp.esi_level} / 5
Triage Decision: {inp.triage_decision}
Sepsis Concern : {"YES — qSOFA positive" if inp.sepsis_concern else "No"}

Vitals: {vitals_str}

Symptoms: {", ".join(inp.extracted_symptoms) or "Not specified"}

Primary Differential:
{chr(10).join(f"  {i+1}. {d}" for i, d in enumerate(inp.primary_differential))}

Secondary / Must-Not-Miss:
{chr(10).join(f"  - {d}" for d in inp.secondary_differential) or "  None"}

Clinical Reasoning Summary:
{inp.clinical_reasoning or "Not provided"}

Labs Ordered: {", ".join(inp.labs_ordered) or "None"}
Imaging: {", ".join(inp.imaging) or "None"}

Assign the most appropriate specialist. Output ONLY valid JSON."""


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def assign_specialist(
    inp: SpecialistInput,
    provider: str = "ollama",
    model_name: str = "deepseek-r1:8b",
    api_key: Optional[str] = None,
    base_url: str = "http://localhost:11434",
) -> SpecialistAssignment:
    """
    Assign a medical specialist to the patient using LLM reasoning.

    Falls back to keyword-based assignment if LLM call fails.
    """
    try:
        llm = get_llm(
            provider=provider,
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=0.1,
        )
        prompt = _build_specialist_prompt(inp)
        response = llm.invoke(prompt)
        response_text = response.content if hasattr(response, "content") else str(response)

        # Extract JSON from response
        json_str = _extract_json(response_text)
        if not json_str:
            return _keyword_fallback(inp)

        data = json.loads(json_str)
        data["patient_id"] = inp.patient_id
        data.setdefault("secondary_specialist", None)

        return SpecialistAssignment(**data)

    except Exception as e:
        result = _keyword_fallback(inp)
        result.error = f"LLM specialist assignment failed ({e}); used keyword fallback."
        return result


def _extract_json(text: str) -> Optional[str]:
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        if end > start:
            return text[start:end].strip()
    if "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        if end > start:
            return text[start:end].strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        raw = text[start:end]
        raw = re.sub(r",(\s*[}\]])", r"\1", raw)
        return raw
    return None
