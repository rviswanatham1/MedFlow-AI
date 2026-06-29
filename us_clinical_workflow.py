"""
US Hospital Emergency Department — Multi-Agent Clinical Triage Workflow

Architecture:
- Agent 1: Clinical Reasoning Agent (ESI triage assessment)
- Agent 2: Clinical Safety & Verification Agent
- LangGraph orchestration

ESI (Emergency Severity Index) 5-level system. Output is a patient assignment
to the appropriate ED care area.
"""

from typing import TypedDict, Literal, List, Optional, Dict, Any
from datetime import datetime
import json
import pandas as pd

try:
    from langgraph.graph import StateGraph, END
except ImportError:
    raise ImportError("Please install langgraph: pip install langgraph>=0.0.40")

try:
    from langchain_core.prompts import PromptTemplate
    from langchain_core.output_parsers import JsonOutputParser
    from pydantic import BaseModel, Field
except ImportError:
    raise ImportError("Please install langchain-core")

from llm_provider import get_llm

from us_triage_agent import (
    load_data,
    get_patients_df,
    get_history_df,
    get_encounters_df,
    get_last_5_encounters,
    calculate_ews_score,
)


# ============================================================================
# STATE SCHEMA
# ============================================================================

class ClinicalWorkflowState(TypedDict):
    """State managed by LangGraph workflow"""

    # Input
    patient_id: str
    symptoms: str
    vitals: Dict[str, Any]

    # Intermediate results
    ews_result: Dict[str, Any]
    patient_data: Dict[str, Any]

    # Agent 1 Output
    clinical_reasoning_output: Dict[str, Any]

    # Agent 2 Output
    safety_verification_output: Dict[str, Any]

    # Final Decision
    final_decision: Dict[str, Any]

    # LLM provider config (passed from orchestrator)
    model_name: str
    base_url: str
    provider: str
    api_key: Optional[str]

    # Metadata
    workflow_complete: bool
    error: Optional[str]
    short_circuit_emergency: bool


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class ClinicalReasoningOutput(BaseModel):
    """Output from Clinical Reasoning Agent (Agent 1)"""

    triage_decision: Literal["RESUSCITATION", "EMERGENT", "URGENT", "LESS_URGENT", "NON_URGENT"] = Field(
        description="ESI triage level decision"
    )
    clinical_reasoning: str = Field(
        description="Step-by-step clinical reasoning"
    )
    identified_high_acuity_flags: List[str] = Field(
        description="High-acuity flags or critical symptoms identified"
    )
    risk_factors: List[str] = Field(
        description="Risk factors identified (age, comorbidities, medications, etc.)"
    )
    confidence_level: Literal["HIGH", "MEDIUM", "LOW"] = Field(
        description="Confidence level in the assessment"
    )
    patient_assignment: str = Field(
        description="Specific ED care area assignment (e.g., 'Resuscitation Bay', 'Acute Care Zone', 'Fast Track')"
    )


class SafetyVerificationOutput(BaseModel):
    """Output from Safety & Verification Agent (Agent 2)"""

    final_decision: Literal["RESUSCITATION", "EMERGENT", "URGENT", "LESS_URGENT", "NON_URGENT"] = Field(
        description="Final validated ESI triage decision"
    )
    escalation_required: bool = Field(
        description="Whether escalation to a higher acuity area is required"
    )
    escalation_reason: str = Field(
        description="Reason for escalation if required"
    )
    safety_validation: str = Field(
        description="Safety validation explanation"
    )
    physician_notification_required: bool = Field(
        description="Whether immediate physician notification is required"
    )
    validation_notes: str = Field(
        description="Additional validation notes"
    )


# ============================================================================
# US ED HIGH-ACUITY FLAG CRITERIA
# ============================================================================

US_ED_HIGH_ACUITY_FLAGS = {
    "cardiovascular": [
        "chest pain",
        "crushing chest pain",
        "chest pain radiating",
        "cardiac arrest",
        "unstable angina",
        "myocardial infarction",
        "aortic dissection",
    ],
    "neurological": [
        "sudden weakness",
        "facial droop",
        "speech difficulties",
        "stroke symptoms",
        "seizure",
        "loss of consciousness",
        "thunderclap headache",
        "meningism",
        "altered mental status",
    ],
    "respiratory": [
        "severe breathing difficulty",
        "stridor",
        "respiratory arrest",
        "severe dyspnea",
        "hemoptysis",
        "unable to speak in sentences",
        "respiratory failure",
    ],
    "abdominal": [
        "peritonism",
        "severe abdominal pain",
        "gastrointestinal bleeding",
        "acute abdomen",
        "hematemesis",
        "hematochezia",
        "ectopic pregnancy",
    ],
    "infection": [
        "sepsis",
        "meningitis signs",
        "severe infection",
        "immunocompromised with fever",
        "non-blanching rash",
        "petechiae",
    ],
    "trauma": [
        "severe bleeding",
        "major trauma",
        "penetrating injury",
        "head injury with loss of consciousness",
        "uncontrolled hemorrhage",
    ],
    "metabolic": [
        "diabetic ketoacidosis",
        "severe hypoglycemia",
        "hyperglycemic emergency",
        "hypertensive emergency",
    ],
    "mental_health": [
        "active suicidal ideation",
        "psychotic episode",
        "severe self-harm risk",
    ],
}


# ============================================================================
# US ED CLINICAL KNOWLEDGE BASE
# ============================================================================

US_ED_CLINICAL_KNOWLEDGE_BASE = """
US EMERGENCY DEPARTMENT TRIAGE — ESI (EMERGENCY SEVERITY INDEX) FRAMEWORK

=== ESI TRIAGE LEVELS & PATIENT ASSIGNMENT ===

1. RESUSCITATION (ESI Level 1)
   - Immediate life-saving intervention required
   - Assignment: RESUSCITATION BAY (immediate physician and nursing response)
   - Examples: Cardiac arrest, respiratory failure, unconscious patient,
     uncontrolled hemorrhage, active seizure

2. EMERGENT (ESI Level 2)
   - High-risk situation, severe pain/distress, or vital sign danger zone
   - Assignment: ACUTE CARE / HIGH-ACUITY ZONE (provider <10 minutes)
   - Examples: Chest pain (ACS concern), stroke symptoms, sepsis,
     altered mental status, severe allergic reaction

3. URGENT (ESI Level 3)
   - Requires ≥2 ED resources; stable vitals but complex presentation
   - Assignment: GENERAL ED TREATMENT ROOM (provider <30-60 minutes)
   - Examples: Moderate abdominal pain, closed head injury, moderate dyspnea,
     significant pain requiring workup

4. LESS_URGENT (ESI Level 4)
   - Requires 1 ED resource; non-urgent
   - Assignment: FAST TRACK / URGENT CARE AREA (provider <2 hours)
   - Examples: Minor lacerations, UTI, minor fractures, mild pain

5. NON_URGENT (ESI Level 5)
   - No ED resources anticipated; minor complaint
   - Assignment: FAST TRACK or redirect to Urgent Care / PCP
   - Examples: Minor rash, cold symptoms, prescription refill question

=== HIGH-ACUITY FLAGS (Require RESUSCITATION or EMERGENT assignment) ===

CARDIOVASCULAR: Chest pain, ACS symptoms, cardiac arrest, aortic dissection
NEUROLOGICAL: Stroke/TIA (FAST), seizure, altered mental status, thunderclap headache
RESPIRATORY: Respiratory failure, stridor, severe dyspnea, hemoptysis
ABDOMINAL: Peritonitis, GI hemorrhage, ruptured ectopic pregnancy
INFECTIOUS: Sepsis criteria, meningitis, immunocompromised with fever
TRAUMA: Uncontrolled hemorrhage, major trauma, penetrating injury, head injury with LOC
METABOLIC: DKA, severe hypoglycemia, hypertensive emergency
MENTAL HEALTH: Active suicidal ideation, acute psychosis, immediate self-harm risk

=== RISK MODIFIERS ===

AGE: Elderly (>65) or pediatric (<2 years) → increased vulnerability
COMORBIDITIES: CAD, CHF, COPD, DM, CKD, cirrhosis, immunosuppression, pregnancy, anticoagulation
MEDICATIONS: Anticoagulants (bleeding risk), beta-blockers (mask tachycardia), immunosuppressants

=== SAFETY PRINCIPLES ===

1. When in doubt, assign to higher acuity area (safety-first)
2. High-acuity flags always require RESUSCITATION or EMERGENT assignment
3. NON_URGENT only if: no high-acuity flags, no significant risk modifiers,
   clearly minor self-limiting complaint, explicit safety justification
4. Low-confidence assessments require physician notification
5. Never under-triage — the cost of over-triage is manageable; under-triage is dangerous
"""


# ============================================================================
# AGENT 1: CLINICAL REASONING AGENT
# ============================================================================

def create_clinical_reasoning_agent(
    model_name: str = "llama3.1:8b",
    base_url: str = "http://localhost:11434",
    provider: str = "ollama",
    api_key: Optional[str] = None,
):
    """Create Clinical Reasoning Agent (Agent 1)"""
    llm = get_llm(provider=provider, model_name=model_name, api_key=api_key, base_url=base_url)
    parser = JsonOutputParser(pydantic_object=ClinicalReasoningOutput)
    return llm, parser


def create_clinical_reasoning_prompt() -> PromptTemplate:
    """Prompt template for Clinical Reasoning Agent.

    Clinical knowledge base is placed at the top to enable KV prefix caching in Ollama,
    so only patient-specific tokens are processed on repeat queries.
    """

    template = """{clinical_knowledge}

You are an experienced US Emergency Department triage nurse at a Level I Trauma Center with 15+ years of experience.
Perform a SYSTEMATIC and THOROUGH clinical assessment following ESI protocols.

=== CRITICAL INSTRUCTIONS ===

1. Perform step-by-step clinical reasoning
2. Take symptoms EXACTLY as described — do not add or assume
3. Check ALL high-acuity flag categories systematically
4. Identify ALL risk factors (age, comorbidities, medications, pregnancy, etc.)
5. Never assume safety — explicitly justify your assignment decision
6. If uncertain, state LOW confidence

=== EWS (PRE-CALCULATED) ===
{ews_context}

=== PATIENT INFORMATION ===
Patient ID: {patient_id}
Name: {patient_name}
Age: {age} years
Gender: {gender}

=== ACTIVE MEDICAL HISTORY ===
{medical_history}

=== CURRENT PRESENTATION ===
**PRESENTING SYMPTOMS:** {symptoms}

**VITAL SIGNS:**
Temperature: {temperature}°C
Heart Rate: {heart_rate} bpm
Respiratory Rate: {respiratory_rate} /min
Blood Pressure: {blood_pressure}
Oxygen Saturation: {oxygen_sat}%

=== PAST ENCOUNTERS (Last 5) ===
{past_encounters}

=== SYSTEMATIC ASSESSMENT REQUIRED ===

STEP 1 — SYMPTOM ANALYSIS:
- What are the EXACT symptoms?
- Duration and progression?
- Severity?
- Associated symptoms?

STEP 2 — HIGH-ACUITY FLAG CHECK:
Systematically check ALL categories:
- Cardiovascular: chest pain, ACS, aortic dissection
- Neurological: stroke/TIA (FAST), seizure, altered mental status, thunderclap headache
- Respiratory: respiratory failure, stridor, severe dyspnea
- Abdominal: peritonitis, GI hemorrhage, ectopic pregnancy
- Infectious: sepsis, meningitis, immunocompromised with fever
- Trauma: uncontrolled hemorrhage, major trauma, penetrating injury
- Metabolic: DKA, hypoglycemia, hypertensive emergency
- Mental health: suicidal ideation, acute psychosis

STEP 3 — RISK FACTOR IDENTIFICATION:
- Age-related risks
- Comorbidities and their impact
- Medications and implications
- Pregnancy status (if applicable)

STEP 4 — EWS INTERPRETATION:
- Does EWS match the clinical picture?
- Do symptoms override EWS urgency?

STEP 5 — ESI TRIAGE DECISION:
- RESUSCITATION: Immediate life-saving intervention required
- EMERGENT: High-risk / severe symptoms / vital sign danger zone
- URGENT: Stable but needs ≥2 resources
- LESS_URGENT: Needs 1 resource
- NON_URGENT: No resources anticipated — minor complaint

STEP 6 — PATIENT ASSIGNMENT:
State the specific ED care area:
- Resuscitation Bay (ESI 1)
- Acute Care / High-Acuity Zone (ESI 2)
- General ED Treatment Room (ESI 3)
- Fast Track (ESI 4)
- Fast Track or redirect to Urgent Care / PCP (ESI 5)

STEP 7 — CONFIDENCE ASSESSMENT:
- HIGH: Clear presentation, sufficient information
- MEDIUM: Some uncertainty but sufficient for decision
- LOW: Significant uncertainty, missing information, complex case

=== CRITICAL REMINDERS ===

1. Any high-acuity flag → RESUSCITATION or EMERGENT (no exceptions)
2. NON_URGENT only when: no flags, no significant risk factors, clearly minor
3. LOW confidence → physician notification required
4. Never under-triage

{format_instructions}

**Output MUST be valid JSON only. No additional text before or after.**"""

    return PromptTemplate(
        template=template,
        input_variables=[
            "clinical_knowledge", "ews_context", "patient_id", "patient_name", "age", "gender",
            "medical_history", "symptoms", "temperature", "heart_rate", "respiratory_rate",
            "blood_pressure", "oxygen_sat", "past_encounters", "format_instructions"
        ]
    )


def run_clinical_reasoning_node(state: ClinicalWorkflowState) -> ClinicalWorkflowState:
    """Node: Run Clinical Reasoning Agent (Agent 1)"""

    try:
        if state.get("error"):
            return state

        if state.get("short_circuit_emergency", False):
            return state

        patients_df = get_patients_df()
        history_df = get_history_df()

        patient_row = patients_df[patients_df["patient_id"] == state["patient_id"]].iloc[0]
        dob = pd.to_datetime(patient_row["dob"])
        age = (datetime.now() - dob).days // 365

        patient_history = history_df[history_df["patient_id"] == state["patient_id"]]
        history_list = []
        for _, h_row in patient_history.iterrows():
            if h_row.get("is_active", 1):
                history_list.append(f"- {h_row['condition_name']} (SNOMED: {h_row['snomed_code']})")
        history_text = "\n".join(history_list) if history_list else "No active medical conditions on record"

        past_encounters_df = get_last_5_encounters(state["patient_id"])
        if not past_encounters_df.empty:
            encounters_text = ""
            for _, enc in past_encounters_df.head(5).iterrows():
                encounters_text += (
                    f"\n- {enc['timestamp']}: {enc['symptoms_text']} "
                    f"(Temp: {enc.get('temp_celsius', 'N/A')}°C, HR: {enc.get('heart_rate', 'N/A')}bpm)"
                )
        else:
            encounters_text = "No previous encounters on record"

        ews_result = state["ews_result"]
        ews_text = (
            f"\nEWS Score: {ews_result['total_score']} points\n"
            f"Risk Level: {ews_result['risk_level']}\n"
            f"Action Required: {ews_result['action_required']}\n"
            f"ESI Level (from vitals): {ews_result.get('esi_level', 'N/A')}\n\n"
            "Note: Symptoms and high-acuity flags can override EWS-based urgency.\n"
        )

        llm, parser = create_clinical_reasoning_agent(
            model_name=state.get("model_name", "llama3.1:8b"),
            base_url=state.get("base_url", "http://localhost:11434"),
            provider=state.get("provider", "ollama"),
            api_key=state.get("api_key"),
        )
        prompt_template = create_clinical_reasoning_prompt()

        formatted_prompt = prompt_template.format(
            clinical_knowledge=US_ED_CLINICAL_KNOWLEDGE_BASE,
            ews_context=ews_text,
            patient_id=state["patient_id"],
            patient_name=patient_row["name"],
            age=age,
            gender=patient_row["gender"],
            medical_history=history_text,
            symptoms=state["symptoms"],
            temperature=state["vitals"].get("temperature", "Not recorded"),
            heart_rate=state["vitals"].get("heart_rate", "Not recorded"),
            respiratory_rate=state["vitals"].get("respiratory_rate", "Not recorded"),
            blood_pressure=state["vitals"].get("blood_pressure", "Not recorded"),
            oxygen_sat=state["vitals"].get("oxygen_sat", "Not recorded"),
            past_encounters=encounters_text,
            format_instructions=parser.get_format_instructions()
        )

        response = llm.invoke(formatted_prompt)
        response_text = response.content if hasattr(response, 'content') else str(response)

        try:
            json_str = _extract_json(response_text)
            if json_str:
                result_dict = json.loads(json_str)
                clinical_reasoning_output = ClinicalReasoningOutput(**result_dict)
                state["clinical_reasoning_output"] = clinical_reasoning_output.dict()
            else:
                raise ValueError("No JSON found in response")
        except Exception as e:
            state["clinical_reasoning_output"] = {
                "triage_decision": "UNKNOWN",
                "clinical_reasoning": f"Error parsing agent response: {str(e)}. Raw: {response_text[:500]}",
                "identified_high_acuity_flags": [],
                "risk_factors": [],
                "confidence_level": "LOW",
                "patient_assignment": "Manual triage review required"
            }
            state["error"] = f"Error parsing clinical reasoning output: {str(e)}"
            state["workflow_complete"] = True
            return state

        state["error"] = ""

    except Exception as e:
        state["clinical_reasoning_output"] = {
            "triage_decision": "UNKNOWN",
            "clinical_reasoning": f"Error in clinical reasoning node: {str(e)}",
            "identified_high_acuity_flags": [],
            "risk_factors": [],
            "confidence_level": "LOW",
            "patient_assignment": "Manual triage review required"
        }
        state["error"] = f"Error in clinical reasoning node: {str(e)}"
        state["workflow_complete"] = True

    return state


# ============================================================================
# AGENT 2: CLINICAL SAFETY & VERIFICATION AGENT
# ============================================================================

def create_safety_verification_agent(
    model_name: str = "deepseek-r1:8b",
    base_url: str = "http://localhost:11434",
    provider: str = "ollama",
    api_key: Optional[str] = None,
):
    """Create Safety & Verification Agent (Agent 2)"""
    llm = get_llm(provider=provider, model_name=model_name, api_key=api_key, base_url=base_url)
    parser = JsonOutputParser(pydantic_object=SafetyVerificationOutput)
    return llm, parser


def create_safety_verification_prompt() -> PromptTemplate:
    """Prompt template for Safety & Verification Agent (Agent 2)"""

    template = """{clinical_knowledge}

You are a senior US ED charge nurse and clinical safety officer. Your role is to independently
re-evaluate Agent 1's triage assessment with a SAFETY-FIRST, anti-under-triage bias.

=== SAFETY MANDATE ===
When in doubt, assign to a HIGHER acuity area. Your job is to catch missed high-acuity flags
and prevent under-triage. Under-triage is more dangerous than over-triage.

=== AGENT 1'S ASSESSMENT ===

**Triage Decision:** {triage_decision}
**Clinical Reasoning:** {clinical_reasoning}
**Identified High-Acuity Flags:** {identified_high_acuity_flags}
**Risk Factors:** {risk_factors}
**Confidence Level:** {confidence_level}
**Patient Assignment:** {patient_assignment}

=== ORIGINAL PATIENT INFORMATION ===

**Symptoms:** {symptoms}

**Vitals:**
Temperature: {temperature}°C
Heart Rate: {heart_rate} bpm
Respiratory Rate: {respiratory_rate} /min
Blood Pressure: {blood_pressure}
Oxygen Saturation: {oxygen_sat}%

**Medical History:** {medical_history}
**EWS Score:** {ews_score} ({ews_risk_level})

=== YOUR VERIFICATION TASK ===

STEP 1 — HIGH-ACUITY FLAG VERIFICATION:
- Did Agent 1 miss any high-acuity flags?
- If ANY high-acuity flag is present → must be RESUSCITATION or EMERGENT

STEP 2 — UNDER-TRIAGE CHECK:
- Is the assignment appropriate for the acuity?
- Could this presentation be more serious?

STEP 3 — NON-URGENT SAFETY CHECK:
If Agent 1 assigns NON_URGENT or LESS_URGENT:
- Are there any high-acuity flags? → Escalate
- Are there significant risk factors? → Escalate to URGENT minimum

STEP 4 — PHYSICIAN NOTIFICATION CHECK:
- If confidence is LOW → physician notification required
- Complex or ambiguous presentation → physician notification required

STEP 5 — FINAL VALIDATED ASSIGNMENT:
Override Agent 1 if necessary. State final patient assignment clearly.

=== REQUIRED JSON OUTPUT ===

Respond with ONLY valid JSON containing ALL fields:

{{
  "final_decision": "RESUSCITATION" | "EMERGENT" | "URGENT" | "LESS_URGENT" | "NON_URGENT",
  "escalation_required": true | false,
  "escalation_reason": "Explain escalation reason (or empty string if not needed)",
  "safety_validation": "Explain your safety validation reasoning",
  "physician_notification_required": true | false,
  "validation_notes": "Additional validation notes"
}}

Rules:
1. Output ONLY the JSON object — no text before or after
2. All 6 fields MUST be present
3. Boolean values: lowercase true or false
4. No trailing commas

JSON OUTPUT:"""

    return PromptTemplate(
        template=template,
        input_variables=[
            "clinical_knowledge", "triage_decision", "clinical_reasoning",
            "identified_high_acuity_flags", "risk_factors", "confidence_level",
            "patient_assignment", "symptoms", "temperature", "heart_rate",
            "respiratory_rate", "blood_pressure", "oxygen_sat", "medical_history",
            "ews_score", "ews_risk_level", "format_instructions"
        ]
    )


def check_hardcoded_high_acuity_flags(symptoms: str) -> List[str]:
    """Hard-coded high-acuity flag detection — safety net before LLM calls."""
    symptoms_lower = symptoms.lower()
    detected_flags = []
    for category, flags in US_ED_HIGH_ACUITY_FLAGS.items():
        for flag in flags:
            if flag.lower() in symptoms_lower:
                detected_flags.append(f"{category}: {flag}")
    return detected_flags


def run_safety_verification_node(state: ClinicalWorkflowState) -> ClinicalWorkflowState:
    """Node: Run Safety & Verification Agent (Agent 2)"""

    try:
        if state.get("error"):
            return state

        if state.get("short_circuit_emergency", False):
            return state

        clinical_output = state["clinical_reasoning_output"]

        patients_df = get_patients_df()
        history_df = get_history_df()

        patient_row = patients_df[patients_df["patient_id"] == state["patient_id"]].iloc[0]

        patient_history = history_df[history_df["patient_id"] == state["patient_id"]]
        history_list = []
        for _, h_row in patient_history.iterrows():
            if h_row.get("is_active", 1):
                history_list.append(f"- {h_row['condition_name']}")
        history_text = "\n".join(history_list) if history_list else "No active medical conditions"

        flags_text = (
            "\n".join([f"- {flag}" for flag in clinical_output.get("identified_high_acuity_flags", [])])
            or "None identified"
        )
        risk_factors_text = (
            "\n".join([f"- {factor}" for factor in clinical_output.get("risk_factors", [])])
            or "None identified"
        )

        llm, parser = create_safety_verification_agent(
            model_name=state.get("model_name", "deepseek-r1:8b"),
            base_url=state.get("base_url", "http://localhost:11434"),
            provider=state.get("provider", "ollama"),
            api_key=state.get("api_key"),
        )
        prompt_template = create_safety_verification_prompt()

        ews_result = state["ews_result"]

        formatted_prompt = prompt_template.format(
            clinical_knowledge=US_ED_CLINICAL_KNOWLEDGE_BASE,
            triage_decision=clinical_output.get("triage_decision", "UNKNOWN"),
            clinical_reasoning=clinical_output.get("clinical_reasoning", ""),
            identified_high_acuity_flags=flags_text,
            risk_factors=risk_factors_text,
            confidence_level=clinical_output.get("confidence_level", "UNKNOWN"),
            patient_assignment=clinical_output.get("patient_assignment", ""),
            symptoms=state["symptoms"],
            temperature=state["vitals"].get("temperature", "Not recorded"),
            heart_rate=state["vitals"].get("heart_rate", "Not recorded"),
            respiratory_rate=state["vitals"].get("respiratory_rate", "Not recorded"),
            blood_pressure=state["vitals"].get("blood_pressure", "Not recorded"),
            oxygen_sat=state["vitals"].get("oxygen_sat", "Not recorded"),
            medical_history=history_text,
            ews_score=ews_result.get("total_score", 0),
            ews_risk_level=ews_result.get("risk_level", "Unknown"),
            format_instructions=parser.get_format_instructions()
        )

        response = llm.invoke(formatted_prompt)
        response_text = response.content if hasattr(response, 'content') else str(response)

        try:
            json_str = _extract_json(response_text)
            if json_str:
                result_dict = json.loads(json_str)
                result_dict.setdefault("safety_validation", result_dict.get("escalation_reason", "Safety validation completed"))
                result_dict.setdefault("validation_notes", "Assessment completed")
                result_dict.setdefault("final_decision", "UNKNOWN")
                result_dict.setdefault("escalation_required", True)
                result_dict.setdefault("physician_notification_required", False)
                safety_output = SafetyVerificationOutput(**result_dict)
                state["safety_verification_output"] = safety_output.dict()
            else:
                raise ValueError("No JSON found in response")

        except json.JSONDecodeError as e:
            result_dict = _extract_fields_from_text(response_text)
            state["safety_verification_output"] = {
                "final_decision": result_dict.get("final_decision", "UNKNOWN"),
                "escalation_required": True,
                "escalation_reason": f"JSON parsing error: {str(e)}. Manual review required.",
                "safety_validation": "Error parsing response. Manual verification needed.",
                "physician_notification_required": True,
                "validation_notes": f"Raw response excerpt: {response_text[:300]}"
            }
            state["error"] = f"JSON parsing error in safety verification: {str(e)}"

        except Exception as e:
            state["safety_verification_output"] = {
                "final_decision": "UNKNOWN",
                "escalation_required": True,
                "escalation_reason": f"Error: {str(e)}. Manual review required.",
                "safety_validation": f"Error during safety verification: {str(e)}",
                "physician_notification_required": True,
                "validation_notes": f"Error: {str(e)}"
            }
            state["error"] = f"Error parsing safety verification output: {str(e)}"

        state["workflow_complete"] = False

    except Exception as e:
        state["safety_verification_output"] = {
            "final_decision": "UNKNOWN",
            "escalation_required": True,
            "escalation_reason": f"Error in safety verification node: {str(e)}. Manual review required.",
            "safety_validation": f"Error: {str(e)}",
            "physician_notification_required": True,
            "validation_notes": f"Error in safety verification node: {str(e)}"
        }
        state["error"] = f"Error in safety verification node: {str(e)}"
        state["workflow_complete"] = True

    return state


# ============================================================================
# JSON HELPERS
# ============================================================================

def _extract_json(text: str) -> Optional[str]:
    """Extract JSON object from text."""
    import re

    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        if end > start:
            return text[start:end].strip()
    elif "```" in text:
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


def _extract_fields_from_text(text: str) -> dict:
    """Fallback: extract fields manually from malformed JSON/text."""
    import re

    result = {}

    decision_match = re.search(r'"final_decision"\s*:\s*"([^"]+)"', text, re.IGNORECASE)
    if decision_match:
        result["final_decision"] = decision_match.group(1)
    else:
        if "RESUSCITATION" in text.upper():
            result["final_decision"] = "RESUSCITATION"
        elif "EMERGENT" in text.upper():
            result["final_decision"] = "EMERGENT"
        elif "URGENT" in text.upper():
            result["final_decision"] = "URGENT"
        elif "LESS_URGENT" in text.upper():
            result["final_decision"] = "LESS_URGENT"
        else:
            result["final_decision"] = "UNKNOWN"

    escalation_match = re.search(r'"escalation_required"\s*:\s*(true|false)', text, re.IGNORECASE)
    result["escalation_required"] = (
        escalation_match.group(1).lower() == "true" if escalation_match else True
    )

    reason_match = re.search(r'"escalation_reason"\s*:\s*"([^"]+)"', text, re.IGNORECASE)
    result["escalation_reason"] = (
        reason_match.group(1) if reason_match else "Unable to parse escalation reason"
    )

    physician_match = re.search(r'"physician_notification_required"\s*:\s*(true|false)', text, re.IGNORECASE)
    result["physician_notification_required"] = (
        physician_match.group(1).lower() == "true" if physician_match else True
    )

    result["reasoning"] = text[:500]
    return result


# ============================================================================
# WORKFLOW NODES
# ============================================================================

def short_circuit_emergency_node(state: ClinicalWorkflowState) -> ClinicalWorkflowState:
    """
    Short-Circuit Node: Check for hardcoded high-acuity flags immediately.
    If flags are detected, skip LLM calls and assign to RESUSCITATION BAY.
    Reduces latency from ~30s to <100ms for critical presentations.
    """
    try:
        if state.get("error"):
            return state

        flags = check_hardcoded_high_acuity_flags(state["symptoms"])

        if flags:
            state["short_circuit_emergency"] = True
            state["safety_verification_output"] = {
                "final_decision": "RESUSCITATION",
                "escalation_required": True,
                "escalation_reason": (
                    f"Automated high-acuity detection: {', '.join(flags)}. "
                    "Immediate assignment to Resuscitation Bay."
                ),
                "safety_validation": (
                    "Short-circuit node detected critical flags. "
                    "Immediate Resuscitation Bay assignment without LLM processing."
                ),
                "physician_notification_required": True,
                "validation_notes": (
                    f"System detected flags: {', '.join(flags)}. "
                    "Emergency assignment applied."
                )
            }
            state["clinical_reasoning_output"] = {
                "triage_decision": "RESUSCITATION",
                "clinical_reasoning": (
                    f"Short-circuit detection: High-acuity flags identified — {', '.join(flags)}. "
                    "Immediate resuscitation care required."
                ),
                "identified_high_acuity_flags": flags,
                "risk_factors": ["High-acuity symptoms detected"],
                "confidence_level": "HIGH",
                "patient_assignment": "Resuscitation Bay — immediate physician and nursing response"
            }
        else:
            state["short_circuit_emergency"] = False

        state["error"] = ""

    except Exception as e:
        state["error"] = f"Error in short-circuit node: {str(e)}"
        state["workflow_complete"] = True

    return state


def should_short_circuit(state: ClinicalWorkflowState) -> str:
    """Conditional router: skip LLM processing if high-acuity flags detected."""
    if state.get("short_circuit_emergency", False):
        return "short_circuit"
    return "continue"


def prepare_data_node(state: ClinicalWorkflowState) -> ClinicalWorkflowState:
    """Node: Prepare patient data and calculate EWS"""

    try:
        if state.get("error"):
            return state

        vitals = state.get("vitals", {})
        ews_result = calculate_ews_score(
            temperature=vitals.get("temperature") if vitals else None,
            heart_rate=vitals.get("heart_rate") if vitals else None,
            respiratory_rate=vitals.get("respiratory_rate") if vitals else None,
            oxygen_sat=vitals.get("oxygen_sat") if vitals else None,
            blood_pressure=vitals.get("blood_pressure") if vitals else None,
            consciousness=vitals.get("consciousness", "ALERT") if vitals else "ALERT",
            on_oxygen=vitals.get("on_oxygen", False) if vitals else False,
        )

        patients_df = get_patients_df()
        if patients_df is None:
            raise ValueError("Patient data not loaded.")

        patient_filtered = patients_df[patients_df["patient_id"] == state["patient_id"]]
        if patient_filtered.empty:
            raise ValueError(f"Patient {state['patient_id']} not found in database.")

        patient_row = patient_filtered.iloc[0]
        dob = pd.to_datetime(patient_row["dob"])
        age = (datetime.now() - dob).days // 365

        state["ews_result"] = ews_result
        state["patient_data"] = {
            "patient_id": state["patient_id"],
            "name": patient_row["name"],
            "age": age,
            "gender": patient_row["gender"],
            "dob": patient_row["dob"],
        }
        state["error"] = ""

    except Exception as e:
        state["error"] = f"Error preparing data: {str(e)}"
        state["workflow_complete"] = True

    return state


def finalize_decision_node(state: ClinicalWorkflowState) -> ClinicalWorkflowState:
    """Node: Finalize patient assignment from safety verification output."""

    try:
        if state.get("error"):
            state["workflow_complete"] = True
            return state

        safety_output = state["safety_verification_output"]
        clinical_output = state["clinical_reasoning_output"]

        # Map final ESI decision to patient assignment string
        assignment_map = {
            "RESUSCITATION": "Resuscitation Bay — immediate physician and nursing response",
            "EMERGENT": "Acute Care / High-Acuity Zone — provider within 10 minutes",
            "URGENT": "General ED Treatment Room — provider within 30-60 minutes",
            "LESS_URGENT": "Fast Track — provider within 1-2 hours",
            "NON_URGENT": "Fast Track or redirect to Urgent Care / Primary Care Physician",
        }

        decision = safety_output.get("final_decision", "UNKNOWN")
        patient_assignment = assignment_map.get(
            decision,
            clinical_output.get("patient_assignment", "Manual triage review required")
        )

        state["final_decision"] = {
            "triage_decision": decision,
            "patient_assignment": patient_assignment,
            "escalation_required": safety_output.get("escalation_required", False),
            "escalation_reason": safety_output.get("escalation_reason", ""),
            "physician_notification_required": safety_output.get("physician_notification_required", False),
            "safety_validation": safety_output.get("safety_validation", ""),
            "clinical_reasoning": clinical_output.get("clinical_reasoning", ""),
            "original_decision": clinical_output.get("triage_decision"),
            "validation_notes": safety_output.get("validation_notes", ""),
        }

        state["workflow_complete"] = True
        state["error"] = ""

    except Exception as e:
        state["error"] = f"Error finalizing decision: {str(e)}"
        state["workflow_complete"] = True

    return state


# ============================================================================
# LANGGRAPH WORKFLOW
# ============================================================================

def create_clinical_workflow():
    """Create LangGraph workflow with short-circuit high-acuity routing."""

    workflow = StateGraph(ClinicalWorkflowState)

    workflow.add_node("short_circuit_check", short_circuit_emergency_node)
    workflow.add_node("prepare_data", prepare_data_node)
    workflow.add_node("clinical_reasoning", run_clinical_reasoning_node)
    workflow.add_node("safety_verification", run_safety_verification_node)
    workflow.add_node("finalize_decision", finalize_decision_node)

    workflow.set_entry_point("short_circuit_check")

    workflow.add_conditional_edges(
        "short_circuit_check",
        should_short_circuit,
        {
            "short_circuit": "finalize_decision",
            "continue": "prepare_data",
        }
    )

    workflow.add_edge("prepare_data", "clinical_reasoning")
    workflow.add_edge("clinical_reasoning", "safety_verification")
    workflow.add_edge("safety_verification", "finalize_decision")
    workflow.add_edge("finalize_decision", END)

    return workflow.compile()


# ============================================================================
# WORKFLOW RUNNER
# ============================================================================

def run_clinical_workflow(
    patient_id: str,
    symptoms: str,
    vitals: Dict[str, Any],
    model_name: str = "deepseek-r1:8b",
    base_url: str = "http://localhost:11434",
    provider: str = "ollama",
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run the complete US ED clinical triage workflow.

    Args:
        patient_id: Patient ID
        symptoms: Presenting symptoms
        vitals: Vital signs dict
        model_name: Model name (Ollama tag or Gemini model ID)
        base_url: Ollama base URL (ignored for Gemini)
        provider: "ollama" | "gemini"
        api_key: Google API key (required for Gemini)

    Returns:
        Complete workflow result including patient_assignment in final_decision
    """
    workflow = create_clinical_workflow()

    initial_state = {
        "patient_id": patient_id,
        "symptoms": symptoms,
        "vitals": vitals,
        "ews_result": {},
        "patient_data": {},
        "clinical_reasoning_output": {},
        "safety_verification_output": {},
        "final_decision": {},
        "model_name": model_name,
        "base_url": base_url,
        "provider": provider,
        "api_key": api_key,
        "workflow_complete": False,
        "error": None,
        "short_circuit_emergency": False,
    }

    try:
        final_state = workflow.invoke(initial_state)

        final_state.setdefault("clinical_reasoning_output", {})
        final_state.setdefault("safety_verification_output", {})
        final_state.setdefault("final_decision", {})

        return final_state

    except Exception as e:
        import traceback
        return {
            **initial_state,
            "error": f"Workflow error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}",
            "workflow_complete": True,
            "clinical_reasoning_output": {},
            "safety_verification_output": {},
            "final_decision": {},
        }


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("Testing US ED Clinical Triage Workflow")
    print("=" * 60)

    load_data()

    test_vitals = {
        "temperature": 37.2,
        "heart_rate": 85,
        "respiratory_rate": 18,
        "blood_pressure": "120/80",
        "oxygen_sat": 98,
        "consciousness": "ALERT",
        "on_oxygen": False,
    }

    # Test 1: Chest pain (should be RESUSCITATION or EMERGENT)
    print("\n1. Testing Chest Pain Presentation")
    result = run_clinical_workflow(
        patient_id="P00001",
        symptoms="Crushing chest pain radiating to left arm, started 30 minutes ago",
        vitals=test_vitals,
    )
    fd = result.get('final_decision', {})
    print(f"Triage Decision: {fd.get('triage_decision', 'N/A')}")
    print(f"Patient Assignment: {fd.get('patient_assignment', 'N/A')}")
    print(f"Escalation Required: {fd.get('escalation_required', False)}")
    print(f"Physician Notification: {fd.get('physician_notification_required', False)}")

    # Test 2: Minor cough (should be LESS_URGENT or NON_URGENT)
    print("\n2. Testing Minor Cough Presentation")
    result2 = run_clinical_workflow(
        patient_id="P00001",
        symptoms="Mild dry cough for 2 days, no other symptoms",
        vitals=test_vitals,
    )
    fd2 = result2.get('final_decision', {})
    print(f"Triage Decision: {fd2.get('triage_decision', 'N/A')}")
    print(f"Patient Assignment: {fd2.get('patient_assignment', 'N/A')}")
    print(f"Escalation Required: {fd2.get('escalation_required', False)}")
