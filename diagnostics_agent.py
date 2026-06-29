"""
Diagnostics Plan Agent

Given a patient's symptoms, ESI level, vitals, and history, generates a
structured clinical diagnostic workup plan using DeepSeek via Ollama.

Produces: differential diagnoses, immediate interventions, labs, imaging,
monitoring requirements, and clinical rationale.
"""

import json
from datetime import datetime
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field

try:
    from langchain_core.output_parsers import JsonOutputParser
except ImportError:
    raise ImportError("Please install langchain-core")

from llm_provider import get_llm
from soap_fallback import build_fallback_soap, needs_fallback


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class DiagnosticsInput(BaseModel):
    patient_id: str
    symptoms: List[str] = Field(description="Extracted symptom list")
    esi_level: int = Field(description="ESI triage level 1-5")
    triage_decision: str = Field(description="e.g. EMERGENT, URGENT")
    patient_age: int
    patient_gender: str
    active_conditions: List[str] = Field(default_factory=list)
    vitals: Dict[str, Any] = Field(default_factory=dict)
    ews_score: int = Field(default=0)
    clinical_reasoning_summary: str = Field(default="")


class SOAPNote(BaseModel):
    subjective: str = Field(
        description="S - Patient's perspective: chief complaint, symptom narrative, duration, pain level, relevant history as reported by the patient."
    )
    objective: str = Field(
        description="O - Measurable facts: vital signs summary, physical exam findings, relevant lab/imaging results available at time of triage."
    )
    assessment: str = Field(
        description="A - Medical diagnosis: clinician's analysis of the data, working diagnosis or differential diagnoses with reasoning."
    )
    plan: str = Field(
        description="P - Next steps: prescriptions, ordered tests, lifestyle advice, specialist referrals, and follow-up instructions."
    )


class ICD10Code(BaseModel):
    code: str = Field(description="ICD-10-CM code e.g. I21.9")
    description: str = Field(description="Human-readable description of the code")
    type: str = Field(description="'primary' for working diagnosis, 'secondary' for comorbidities or rule-outs")


class CPTCode(BaseModel):
    code: str = Field(description="CPT procedure code e.g. 99285")
    description: str = Field(description="Human-readable description of the procedure/service")
    category: str = Field(description="'evaluation', 'lab', 'imaging', or 'procedure'")


class DiagnosticsOutput(BaseModel):
    patient_id: str = Field(description="Patient identifier")
    primary_differential: List[str] = Field(
        description="Top 3-5 most likely diagnoses, most probable first"
    )
    secondary_differential: List[str] = Field(
        description="2-3 must-not-miss diagnoses to rule out"
    )
    immediate_interventions: List[str] = Field(
        description="Time-critical interventions ordered by priority"
    )
    labs_ordered: List[str] = Field(
        description="Specific lab tests to order"
    )
    imaging: List[str] = Field(
        description="Imaging studies to order"
    )
    monitoring: List[str] = Field(
        description="Ongoing monitoring requirements"
    )
    clinical_rationale: str = Field(
        description="Narrative explaining differential and workup choices given ESI and context"
    )
    urgency_flag: bool = Field(
        description="True if ESI 1 or 2 — triggers time annotations on interventions"
    )
    soap_note: Optional[SOAPNote] = Field(
        default=None,
        description="Structured SOAP note for this patient encounter"
    )
    icd10_codes: List[ICD10Code] = Field(
        default_factory=list,
        description="ICD-10-CM codes for the working diagnosis and relevant comorbidities"
    )
    cpt_codes: List[CPTCode] = Field(
        default_factory=list,
        description="CPT codes for ordered procedures, labs, imaging, and evaluation services"
    )
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# ============================================================================
# PROMPT BUILDER
# ============================================================================

_DIAGNOSTICS_KNOWLEDGE = """
US EMERGENCY DEPARTMENT — DIAGNOSTIC WORKUP REFERENCE

COMMON WORKUP BY PRESENTATION:

Chest pain:
  Immediate: 12-lead ECG within 10 min, IV access x2, troponin, BMP, CBC, CXR
  Rule out: ACS (STEMI/NSTEMI), aortic dissection, PE, tension pneumothorax

Shortness of breath:
  Immediate: ABG or VBG, BNP, D-dimer, chest X-ray, spirometry if stable
  Rule out: PE, CHF exacerbation, pneumothorax, severe asthma, COPD exacerbation

Stroke symptoms (FAST):
  Immediate: Non-contrast CT head, CBC, BMP, PT/INR, glucose fingerstick, EKG
  Rule out: Ischemic stroke, hemorrhagic stroke, TIA, hypoglycemia mimicking stroke

Altered mental status:
  Immediate: Glucose, BMP, CBC, LFTs, ammonia, lactate, UA, blood cultures, CT head
  Rule out: Infection/sepsis, metabolic encephalopathy, stroke, drug toxicity, DKA

Abdominal pain:
  Immediate: BMP, CBC, lipase, LFTs, UA, urine pregnancy test (females <50)
  Imaging: CT abdomen/pelvis with contrast
  Rule out: Appendicitis, bowel obstruction, ectopic pregnancy, AAA, mesenteric ischemia

Sepsis / Fever:
  Immediate: Blood cultures x2, CBC, BMP, lactate, UA/urine culture, CXR
  Interventions: IV access x2, aggressive fluid resuscitation, broad-spectrum antibiotics

Trauma:
  Immediate: Primary survey (ABCDE), IV access x2, FAST exam, trauma labs (CBC, BMP, coags, type & screen)
  Imaging: Pan-CT if high mechanism, selective imaging if stable
"""


def _build_diagnostics_prompt(input_data: DiagnosticsInput, format_instructions: str) -> str:
    symptoms_str = ", ".join(input_data.symptoms) if input_data.symptoms else "Not specified"
    conditions_str = (
        ", ".join(input_data.active_conditions)
        if input_data.active_conditions
        else "None on record"
    )

    vitals = input_data.vitals
    vitals_str = (
        f"Temp: {vitals.get('temperature', 'NR')}°C | "
        f"HR: {vitals.get('heart_rate', 'NR')} bpm | "
        f"RR: {vitals.get('respiratory_rate', 'NR')} /min | "
        f"BP: {vitals.get('blood_pressure', 'NR')} | "
        f"SpO2: {vitals.get('oxygen_sat', 'NR')}% | "
        f"Mental status: {vitals.get('consciousness', 'ALERT')}"
    )

    urgency_note = ""
    if input_data.esi_level <= 2:
        urgency_note = "\n⚠️  ESI 1-2: All interventions must include timing (e.g., 'within 10 minutes')."

    return f"""{_DIAGNOSTICS_KNOWLEDGE}

You are an attending emergency physician at a US Level I Trauma Center.
A patient has been triaged and you must generate a complete clinical diagnostic workup plan including a SOAP note and billing codes.{urgency_note}

=== PATIENT CONTEXT ===
Patient ID: {input_data.patient_id}
Age: {input_data.patient_age} years | Gender: {input_data.patient_gender}
ESI Level: {input_data.esi_level} ({input_data.triage_decision})
EWS Score: {input_data.ews_score}

=== PRESENTING SYMPTOMS ===
{symptoms_str}

=== VITAL SIGNS ===
{vitals_str}

=== ACTIVE MEDICAL HISTORY ===
{conditions_str}

=== TRIAGE REASONING ===
{input_data.clinical_reasoning_summary or "Not provided"}

=== YOUR TASK ===
Generate a complete, ESI-appropriate diagnostic workup plan with SOAP note and billing codes.

Rules:
1. primary_differential: 3-5 entries, most likely first
2. secondary_differential: 2-3 must-not-miss diagnoses
3. immediate_interventions: ordered by clinical priority; if ESI 1-2, include timing
4. Do NOT order unnecessary tests for ESI 4-5 minor presentations
5. clinical_rationale must explain WHY this differential and workup given THESE specific symptoms and history

6. soap_note: Write a structured SOAP note:
   - subjective: Patient's own words — chief complaint, symptom description, duration, pain level (e.g. "Patient presents with crushing chest pain 9/10 radiating to left arm, onset 30 min ago...")
   - objective: Hard data — vitals, physical exam findings, any immediate test results available
   - assessment: Your clinical analysis — working diagnosis and differential reasoning
   - plan: All ordered interventions, labs, imaging, meds, referrals, and follow-up instructions

7. icd10_codes: Provide 2-5 ICD-10-CM codes:
   - One "primary" code for the working/most-likely diagnosis
   - "secondary" codes for active comorbidities or must-rule-out conditions
   Example: {{"code": "I21.9", "description": "Acute myocardial infarction, unspecified", "type": "primary"}}

8. cpt_codes: Provide relevant CPT codes for the ordered services:
   - Include E&M code (e.g. 99285 for high-complexity ED visit)
   - Lab codes (e.g. 80053 comprehensive metabolic panel)
   - Imaging codes (e.g. 71046 chest X-ray 2 views)
   - Procedure codes as applicable
   Example: {{"code": "99285", "description": "ED visit high complexity", "category": "evaluation"}}

{format_instructions}

Output ONLY valid JSON. No text before or after."""


# ============================================================================
# MAIN AGENT FUNCTION
# ============================================================================

def _extract_json(text: str) -> Optional[str]:
    import re
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
        json_str = text[start:end]
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        return json_str
    return None


def _fallback_output(
    patient_id: str,
    error_msg: str,
    input_data: Optional["DiagnosticsInput"] = None,
) -> DiagnosticsOutput:
    soap_note = None
    icd10_codes: list = []
    cpt_codes: list = []

    if input_data:
        try:
            symptoms_str = ", ".join(input_data.symptoms) if input_data.symptoms else ""
            soap_note, icd10_codes, cpt_codes = build_fallback_soap(
                symptoms          = symptoms_str,
                patient_age       = input_data.patient_age,
                patient_gender    = input_data.patient_gender,
                active_conditions = input_data.active_conditions,
                vitals            = input_data.vitals or {},
                pain_level        = 5,
            )
        except Exception:
            pass

    return DiagnosticsOutput(
        patient_id=patient_id,
        primary_differential=["Clinical assessment required"],
        secondary_differential=["Manual physician review needed"],
        immediate_interventions=["Physician assessment — LLM diagnostics unavailable"],
        labs_ordered=["Order per physician assessment"],
        imaging=["Order per physician assessment"],
        monitoring=["Continuous monitoring per physician order"],
        clinical_rationale=f"LLM unavailable: {error_msg}. Keyword-based fallback applied.",
        urgency_flag=False,
        soap_note=soap_note,
        icd10_codes=icd10_codes,
        cpt_codes=cpt_codes,
    )


def run_diagnostics_agent(
    input_data: DiagnosticsInput,
    model_name: str = "deepseek-r1:8b",
    base_url: str = "http://localhost:11434",
    provider: str = "ollama",
    api_key: Optional[str] = None,
) -> DiagnosticsOutput:
    """
    Generate a clinical diagnostic workup plan using the configured LLM.

    Args:
        input_data: DiagnosticsInput with patient context
        model_name: Model name (Ollama tag or Gemini model ID)
        base_url: Ollama base URL (ignored for Gemini)
        provider: "ollama" | "gemini"
        api_key: Google API key (required for Gemini)

    Returns:
        DiagnosticsOutput with differential, workup, and rationale
    """
    try:
        llm = get_llm(provider=provider, model_name=model_name, api_key=api_key, base_url=base_url)
        parser = JsonOutputParser(pydantic_object=DiagnosticsOutput)
        format_instructions = parser.get_format_instructions()

        prompt = _build_diagnostics_prompt(input_data, format_instructions)
        response = llm.invoke(prompt)
        response_text = response.content if hasattr(response, 'content') else str(response)

        json_str = _extract_json(response_text)
        if not json_str:
            return _fallback_output(input_data.patient_id, "No JSON in LLM response", input_data)

        result_dict = json.loads(json_str)
        result_dict["patient_id"] = input_data.patient_id
        result_dict["urgency_flag"] = input_data.esi_level <= 2
        result_dict.setdefault("generated_at", datetime.now().isoformat())
        result_dict.setdefault("soap_note", None)
        result_dict.setdefault("icd10_codes", [])
        result_dict.setdefault("cpt_codes", [])

        # ── Fallback: if LLM didn't produce SOAP/codes, generate from keywords ──
        if needs_fallback(result_dict):
            symptoms_str = ", ".join(input_data.symptoms) if input_data.symptoms else ""
            vitals = {k: v for k, v in (input_data.vitals or {}).items()}
            fb_soap, fb_icd10, fb_cpt = build_fallback_soap(
                symptoms       = symptoms_str,
                patient_age    = input_data.patient_age,
                patient_gender = input_data.patient_gender,
                active_conditions = input_data.active_conditions,
                vitals         = vitals,
                pain_level     = 5,
            )
            if not result_dict.get("soap_note") or not any(result_dict["soap_note"].values()):
                result_dict["soap_note"] = fb_soap
            if not result_dict["icd10_codes"]:
                result_dict["icd10_codes"] = fb_icd10
            if not result_dict["cpt_codes"]:
                result_dict["cpt_codes"] = fb_cpt

        return DiagnosticsOutput(**result_dict)

    except json.JSONDecodeError as e:
        return _fallback_output(input_data.patient_id, f"JSON decode error: {str(e)}", input_data)
    except Exception as e:
        return _fallback_output(input_data.patient_id, str(e), input_data)


def format_diagnostics_for_display(output: DiagnosticsOutput) -> str:
    """Format DiagnosticsOutput as human-readable text for nursing station display."""
    lines = [
        f"DIAGNOSTIC PLAN — Patient {output.patient_id}",
        f"Generated: {output.generated_at}",
        f"{'⚠️  URGENT WORKUP' if output.urgency_flag else 'Standard workup'}",
        "",
        "PRIMARY DIFFERENTIAL:",
    ]
    for i, d in enumerate(output.primary_differential, 1):
        lines.append(f"  {i}. {d}")

    lines += ["", "RULE OUT (MUST-NOT-MISS):"]
    for d in output.secondary_differential:
        lines.append(f"  • {d}")

    lines += ["", "IMMEDIATE INTERVENTIONS:"]
    for iv in output.immediate_interventions:
        lines.append(f"  ▶ {iv}")

    lines += ["", "LABS:"]
    for lab in output.labs_ordered:
        lines.append(f"  • {lab}")

    if output.imaging:
        lines += ["", "IMAGING:"]
        for img in output.imaging:
            lines.append(f"  • {img}")

    if output.monitoring:
        lines += ["", "MONITORING:"]
        for m in output.monitoring:
            lines.append(f"  • {m}")

    lines += ["", "CLINICAL RATIONALE:", output.clinical_rationale]

    return "\n".join(lines)


# ============================================================================
# CLI DEMO
# ============================================================================

if __name__ == "__main__":
    demo_input = DiagnosticsInput(
        patient_id="P00001",
        symptoms=["chest pain", "chest pressure", "diaphoresis", "shortness of breath"],
        esi_level=2,
        triage_decision="EMERGENT",
        patient_age=58,
        patient_gender="Male",
        active_conditions=["Type 2 diabetes mellitus", "Hypertension", "Dyslipidemia"],
        vitals={
            "temperature": 37.1,
            "heart_rate": 105,
            "respiratory_rate": 22,
            "blood_pressure": "150/95",
            "oxygen_sat": 95,
            "consciousness": "ALERT",
        },
        ews_score=4,
        clinical_reasoning_summary="High-risk ACS presentation with cardiac history and hemodynamic concern.",
    )

    print("Running diagnostics agent...")
    result = run_diagnostics_agent(demo_input)
    print(format_diagnostics_for_display(result))
