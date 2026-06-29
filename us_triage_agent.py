"""
US Hospital ED Triage Agent - DeepSeek Reasoning with Chain-of-Thought

Uses DeepSeek reasoning model for structured clinical assessment following
US Emergency Severity Index (ESI) triage protocols.

Single-stage approach: DeepSeek performs full assessment with structured reasoning.
"""

import json
import os
from typing import Optional, Dict, Any, List
from datetime import datetime

import pandas as pd
import argparse

# Handle LangChain imports
try:
    from langchain_classic.agents import AgentExecutor, create_openai_tools_agent
    from langchain_classic.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain_classic.tools import tool
except ImportError:
    try:
        from langchain.agents import AgentExecutor, create_openai_tools_agent
        from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
        from langchain.tools import tool
    except ImportError:
        raise ImportError("Please install langchain-classic: pip install langchain-classic")

try:
    from langchain_ollama import ChatOllama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    raise ImportError("Please install langchain-ollama: pip install langchain-ollama")


# ============================================================================
# DATA ACCESS
# ============================================================================

_patients_df: Optional[pd.DataFrame] = None
_history_df: Optional[pd.DataFrame] = None
_encounters_df: Optional[pd.DataFrame] = None
_rules_df: Optional[pd.DataFrame] = None


def load_data(
    patients_path: str = "patient_demographics.csv",
    history_path: str = "past_medical_history.csv",
    encounters_path: str = "clinical_encounters.csv",
    rules_path: str = "triage_rules.csv",
):
    """Load CSV files into memory."""
    global _patients_df, _history_df, _encounters_df, _rules_df

    if not os.path.exists(patients_path):
        raise FileNotFoundError(f"Patient demographics file not found: {patients_path}")

    _patients_df = pd.read_csv(patients_path)
    _history_df = pd.read_csv(history_path) if os.path.exists(history_path) else pd.DataFrame()
    _encounters_df = pd.read_csv(encounters_path) if os.path.exists(encounters_path) else pd.DataFrame()
    _rules_df = pd.read_csv(rules_path) if os.path.exists(rules_path) else pd.DataFrame()

    print(f"✓ Loaded data: {len(_patients_df)} patients, {len(_history_df)} history records, "
          f"{len(_encounters_df)} encounters, {len(_rules_df)} rules")


def get_patients_df():
    return _patients_df

def get_history_df():
    return _history_df

def get_encounters_df():
    return _encounters_df

def get_rules_df():
    return _rules_df


# ============================================================================
# EARLY WARNING SCORE (EWS) CALCULATOR
# ============================================================================

def calculate_ews_score(
    temperature: Optional[float] = None,
    heart_rate: Optional[int] = None,
    respiratory_rate: Optional[int] = None,
    oxygen_sat: Optional[float] = None,
    blood_pressure: Optional[str] = None,
    consciousness: str = "ALERT",
    on_oxygen: bool = False,
) -> Dict[str, Any]:
    """
    Calculate Early Warning Score (EWS) from vital signs.
    Returns dict with total_score, breakdown, and ESI-aligned interpretation.
    """
    score = 0
    breakdown = {}

    # Temperature
    if temperature is not None:
        if temperature <= 35.0:
            temp_score = 3
            temp_desc = "Critical - Severe hypothermia"
        elif temperature <= 36.0:
            temp_score = 1
            temp_desc = "Low - Mild hypothermia"
        elif temperature <= 38.0:
            temp_score = 0
            temp_desc = "Normal (afebrile)"
        elif temperature <= 39.0:
            temp_score = 1
            temp_desc = "Elevated - Low-grade fever"
        else:
            temp_score = 2
            temp_desc = "High - Significant fever"
        score += temp_score
        breakdown["temperature"] = {"value": temperature, "score": temp_score, "description": temp_desc}
    else:
        breakdown["temperature"] = {"value": "Not recorded", "score": 0, "description": "Not recorded"}

    # Heart Rate
    if heart_rate is not None:
        if heart_rate <= 40:
            hr_score = 3
            hr_desc = "Critical - Severe bradycardia"
        elif heart_rate <= 50:
            hr_score = 1
            hr_desc = "Low - Bradycardia"
        elif heart_rate <= 90:
            hr_score = 0
            hr_desc = "Normal"
        elif heart_rate <= 110:
            hr_score = 1
            hr_desc = "Elevated - Mild tachycardia"
        elif heart_rate <= 130:
            hr_score = 2
            hr_desc = "High - Tachycardia"
        else:
            hr_score = 3
            hr_desc = "Critical - Severe tachycardia"
        score += hr_score
        breakdown["heart_rate"] = {"value": heart_rate, "score": hr_score, "description": hr_desc}
    else:
        breakdown["heart_rate"] = {"value": "Not recorded", "score": 0, "description": "Not recorded"}

    # Respiratory Rate
    if respiratory_rate is not None:
        if respiratory_rate <= 8:
            rr_score = 3
            rr_desc = "Critical - Severe bradypnea"
        elif respiratory_rate <= 11:
            rr_score = 1
            rr_desc = "Low - Below normal"
        elif respiratory_rate <= 20:
            rr_score = 0
            rr_desc = "Normal range"
        elif respiratory_rate <= 24:
            rr_score = 2
            rr_desc = "Elevated - Tachypnea"
        else:
            rr_score = 3
            rr_desc = "Critical - Severe tachypnea"
        score += rr_score
        breakdown["respiratory_rate"] = {"value": respiratory_rate, "score": rr_score, "description": rr_desc}
    else:
        breakdown["respiratory_rate"] = {"value": "Not recorded", "score": 0, "description": "Not recorded"}

    # Oxygen Saturation
    if oxygen_sat is not None:
        if oxygen_sat <= 91:
            spo2_score = 3
            spo2_desc = "Critical - Severe hypoxia"
        elif oxygen_sat <= 93:
            spo2_score = 2
            spo2_desc = "Low - Hypoxia"
        elif oxygen_sat <= 95:
            spo2_score = 1
            spo2_desc = "Borderline"
        else:
            spo2_score = 0
            spo2_desc = "Normal"
        score += spo2_score
        breakdown["oxygen_sat"] = {"value": oxygen_sat, "score": spo2_score, "description": spo2_desc}
    else:
        breakdown["oxygen_sat"] = {"value": "Not recorded", "score": 0, "description": "Not recorded"}

    # Blood Pressure (systolic)
    if blood_pressure and blood_pressure != "Not recorded":
        try:
            systolic = int(blood_pressure.split('/')[0].strip())
            if systolic <= 90:
                bp_score = 3
                bp_desc = "Critical - Hypotension / Shock"
            elif systolic <= 100:
                bp_score = 2
                bp_desc = "Low - Borderline hypotension"
            elif systolic <= 110:
                bp_score = 1
                bp_desc = "Low-normal"
            elif systolic <= 219:
                bp_score = 0
                bp_desc = "Normal range"
            else:
                bp_score = 3
                bp_desc = "Critical - Hypertensive emergency"
            score += bp_score
            breakdown["blood_pressure"] = {"value": blood_pressure, "score": bp_score, "description": bp_desc}
        except Exception:
            breakdown["blood_pressure"] = {"value": blood_pressure, "score": 0, "description": "Invalid format"}
    else:
        breakdown["blood_pressure"] = {"value": "Not recorded", "score": 0, "description": "Not recorded"}

    # Consciousness (AVPU)
    if consciousness.upper() == "ALERT":
        cons_score = 0
        cons_desc = "Alert and oriented"
    else:
        cons_score = 3
        cons_desc = "Altered mental status / reduced consciousness"
    score += cons_score
    breakdown["consciousness"] = {"value": consciousness, "score": cons_score, "description": cons_desc}

    # Supplemental oxygen
    oxygen_score = 2 if on_oxygen else 0
    score += oxygen_score
    breakdown["supplemental_oxygen"] = {
        "value": "Yes" if on_oxygen else "No",
        "score": oxygen_score,
        "description": "On supplemental oxygen" if on_oxygen else "Room air",
    }

    # ESI-aligned urgency interpretation
    if score == 0:
        risk_level = "Low"
        action_required = "Routine monitoring"
        urgency = "NON_URGENT"
        esi_level = 5
    elif score <= 4:
        risk_level = "Low-Medium"
        action_required = "Standard clinical evaluation"
        urgency = "LESS_URGENT"
        esi_level = 4
    elif score <= 6:
        risk_level = "Medium"
        action_required = "Urgent clinical evaluation within 1 hour"
        urgency = "URGENT"
        esi_level = 3
    else:
        risk_level = "High"
        action_required = "Immediate emergency assessment. Consider critical care. Continuous monitoring."
        urgency = "EMERGENT"
        esi_level = 2

    return {
        "total_score": score,
        "breakdown": breakdown,
        "risk_level": risk_level,
        "action_required": action_required,
        "urgency": urgency,
        "esi_level": esi_level,
    }

# Keep alias for backward compatibility with workflow imports
calculate_news2_score = calculate_ews_score


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_last_5_encounters(patient_id: str) -> pd.DataFrame:
    """Get the last 5 encounters for a patient, sorted by timestamp (most recent first)."""
    if _encounters_df is None or _encounters_df.empty:
        return pd.DataFrame()

    patient_encounters = _encounters_df[_encounters_df["patient_id"] == patient_id].copy()
    if patient_encounters.empty:
        return pd.DataFrame()

    patient_encounters["timestamp"] = pd.to_datetime(patient_encounters["timestamp"])
    patient_encounters = patient_encounters.sort_values("timestamp", ascending=False).head(5)

    return patient_encounters


def get_patient_data_for_assessment(
    patient_id: str,
    symptoms: str,
    vitals: Dict[str, Any],
    include_past_encounters: bool = True,
) -> str:
    """Format patient data as a string for the clinical reasoning agent."""
    if _patients_df is None:
        raise ValueError("Patient data not loaded. Call load_data() first.")

    patient = _patients_df[_patients_df["patient_id"] == patient_id]
    if patient.empty:
        raise ValueError(f"Patient {patient_id} not found")

    row = patient.iloc[0]
    dob = pd.to_datetime(row["dob"])
    age = (datetime.now() - dob).days // 365

    conditions = []
    if _history_df is not None and not _history_df.empty:
        history = _history_df[_history_df["patient_id"] == patient_id]
        for _, h_row in history.iterrows():
            conditions.append({
                "condition_name": h_row["condition_name"],
                "snomed_code": h_row["snomed_code"],
                "history_flag": h_row.get("history_flag", ""),
                "is_active": bool(h_row.get("is_active", 1)),
            })

    report = f"""
=== PATIENT INFORMATION ===
Patient ID: {row['patient_id']}
Name: {row['name']}
Age: {age} years
Gender: {row['gender']}
Date of Birth: {row['dob']}
ZIP Code: {row.get('postcode', 'N/A')}
Ethnicity: {row['ethnicity_code']}

=== ACTIVE MEDICAL HISTORY ===
"""
    active_conditions = [c for c in conditions if c.get("is_active")]
    if active_conditions:
        for cond in active_conditions:
            report += f"- {cond.get('condition_name', 'N/A')} (SNOMED: {cond.get('snomed_code', 'N/A')}, Flag: {cond.get('history_flag', 'N/A')})\n"
    else:
        report += "No active medical conditions on record.\n"

    if include_past_encounters:
        past_encounters = get_last_5_encounters(patient_id)
        if not past_encounters.empty:
            report += "\n=== PAST ENCOUNTERS (Last 5) ===\n"
            for _, enc in past_encounters.iterrows():
                report += f"- {enc['timestamp']}: {enc['symptoms_text']} (Temp: {enc['temp_celsius']}°C, HR: {enc['heart_rate']}bpm)\n"
        else:
            report += "\n=== PAST ENCOUNTERS ===\nNo previous encounters on record.\n"

    report += f"""
=== CURRENT PRESENTATION ===
**PRESENTING SYMPTOMS:** {symptoms}

**VITAL SIGNS:**
Temperature: {vitals.get('temperature', 'Not recorded')}°C
Heart Rate: {vitals.get('heart_rate', 'Not recorded')} bpm
Respiratory Rate: {vitals.get('respiratory_rate', 'Not recorded')} /min
Blood Pressure: {vitals.get('blood_pressure', 'Not recorded')}
Oxygen Saturation: {vitals.get('oxygen_sat', 'Not recorded')}%
Consciousness (AVPU): {vitals.get('consciousness', 'ALERT')}
"""

    return report


# ============================================================================
# US ED CLINICAL KNOWLEDGE BASE
# ============================================================================

US_ED_CLINICAL_KNOWLEDGE = """
US EMERGENCY DEPARTMENT TRIAGE PROTOCOLS - ESI (EMERGENCY SEVERITY INDEX) FRAMEWORK

=== ABCDE PRIMARY SURVEY ===
Perform immediately on arrival to identify life threats:

A - AIRWAY:
  - Can the patient speak in full sentences? (Airway patent)
  - Stridor, choking, difficulty swallowing? (Airway compromise)
  - Unconscious patient? (Airway at risk — immediate intervention)

B - BREATHING:
  - Respiratory rate: Normal 12-20/min
  - Oxygen saturation: Normal >95% on room air
  - Signs: Use of accessory muscles, cyanosis, wheeze, paradoxical breathing
  - CRITICAL FLAGS: RR >25 or <10, SpO2 <90%, severe dyspnea

C - CIRCULATION:
  - Heart rate: Normal 60-100 bpm
  - Blood pressure: Systolic >90 mmHg
  - Capillary refill <2 seconds
  - Signs: Pallor, diaphoresis, cold/mottled extremities
  - CRITICAL FLAGS: HR >130 or <40, systolic BP <90 (shock), signs of hemorrhage

D - DISABILITY (Neurological):
  - AVPU: Alert / Voice / Pain / Unresponsive
  - Glasgow Coma Scale (GCS) if indicated
  - Pupil reactions, focal deficits
  - Point-of-care glucose
  - CRITICAL FLAGS: Altered mental status, new focal neurological deficits, seizures

E - EXPOSURE:
  - Temperature: Normal 36.5-37.5°C (97.7-99.5°F)
  - Rashes, wounds, bleeding, signs of trauma or abuse

=== HIGH-ACUITY PRESENTATIONS (Require Immediate or Emergent Assignment) ===

CARDIOVASCULAR:
- Chest pain with radiation to jaw/arm/back (ACS)
- Chest pain with diaphoresis, nausea, dyspnea
- Sudden severe tearing chest/back pain (aortic dissection)
- Syncope with exertion or cardiac history
- Palpitations with hemodynamic instability

NEUROLOGICAL:
- Sudden unilateral weakness, facial droop, speech deficits (FAST — stroke)
- Sudden severe "thunderclap" headache (subarachnoid hemorrhage)
- New confusion or acute altered mental status
- Seizure — first-time, prolonged, or post-ictal concern
- Sudden vision loss or diplopia

RESPIRATORY:
- Severe dyspnea unable to complete sentences
- Stridor (airway obstruction — immediate)
- Silent chest in asthma (life-threatening)
- Hemoptysis (blood in sputum)
- RR >25/min or SpO2 <90%

ABDOMINAL:
- Severe abdominal pain with peritoneal signs (guarding, rigidity, rebound)
- Abdominal pain with hypotension or syncope (AAA, ectopic pregnancy)
- Hematemesis or hematochezia (GI hemorrhage)
- Signs of ectopic pregnancy in females of reproductive age

INFECTION / SEPSIS:
- Non-blanching petechial/purpuric rash (meningococcemia)
- Fever with organ dysfunction (sepsis criteria: HR >100, RR >22, altered mentation, systolic <100)
- Immunocompromised patient with fever (absolute neutrophil count concern)

METABOLIC:
- Blood glucose <60 mg/dL (hypoglycemia)
- Blood glucose >400 mg/dL with ketones (DKA)
- Altered mental status + diabetic history (DKA / HHS)

=== ESI TRIAGE LEVELS & PATIENT ASSIGNMENT ===

ESI LEVEL 1 — IMMEDIATE RESUSCITATION:
- Requires immediate life-saving intervention
- Conditions: Cardiac arrest, respiratory failure, unconscious, uncontrolled hemorrhage, seizure
- Assignment: RESUSCITATION BAY — immediate physician and nurse at bedside
- Time to provider: Immediate (0 minutes)

ESI LEVEL 2 — EMERGENT:
- High-risk situation; severe pain/distress; vital sign danger zone
- Conditions: Chest pain (ACS concern), stroke symptoms, sepsis, altered mental status, severe allergic reaction
- Assignment: ACUTE CARE / HIGH-ACUITY ZONE — seen within 10 minutes
- Time to provider: <10 minutes

ESI LEVEL 3 — URGENT:
- Requires ≥2 ED resources (labs, imaging, IV medications, procedures)
- Stable vitals but complex presentation
- Conditions: Moderate abdominal pain, closed head injury, moderate dyspnea, moderate pain
- Assignment: GENERAL ED TREATMENT ROOM — seen within 30-60 minutes
- Time to provider: <30 minutes

ESI LEVEL 4 — LESS URGENT:
- Requires 1 ED resource
- Conditions: Minor lacerations, UTI, minor fractures, mild pain, stable chronic condition exacerbation
- Assignment: FAST TRACK / URGENT CARE AREA — seen within 1-2 hours
- Time to provider: <2 hours

ESI LEVEL 5 — NON-URGENT:
- No ED resources anticipated; minor complaint
- Conditions: Minor rash, prescription refill concern, simple wound check, cold symptoms
- Assignment: FAST TRACK / DISCHARGE WAITING AREA or redirect to primary care / urgent care clinic
- Time to provider: As capacity allows (>2 hours) or redirected
"""


# ============================================================================
# CLINICAL REASONING AGENT PROMPT
# ============================================================================

CLINICAL_REASONING_PROMPT = """You are an experienced US Emergency Department (ED) triage nurse with 15+ years of experience at a Level I Trauma Center. You perform SYSTEMATIC and THOROUGH triage assessments following ESI (Emergency Severity Index) protocols.

{clinical_knowledge}

=== YOUR TASK ===
Perform a comprehensive clinical assessment for the incoming patient and determine their ESI triage level and ED care area assignment.

=== CRITICAL INSTRUCTION ===
The Early Warning Score (EWS) has been PRE-CALCULATED from vital signs. Use it as physiological context, but:
- Presenting symptoms and HIGH-ACUITY FLAGS can override EWS
- A patient with ACS or stroke symptoms needs immediate care even with low EWS
- High EWS with non-specific symptoms still demands urgent assessment for physiological instability
- Balance EWS against clinical presentation for your final assignment

=== EWS (PRE-CALCULATED) ===
{ews_context}

=== PATIENT INFORMATION ===
{patient_data}

=== SYSTEMATIC ASSESSMENT ===

Work through EACH step and document your reasoning:

STEP 1 — SYMPTOM-DRIVEN ASSESSMENT:
- What do these EXACT symptoms suggest? (cardiac, neuro, respiratory, abdominal, infectious, trauma?)
- Are any HIGH-ACUITY FLAGS explicitly present?
- What is the WORST CASE scenario for this presentation?
- Does this require immediate life-saving intervention?

STEP 2 — ABCDE PRIMARY SURVEY:
Assess life threats from the reported symptoms and available vitals:
- A: Airway patency
- B: Breathing adequacy
- C: Circulation / hemodynamic stability
- D: Neurological status / mental status
- E: Exposure findings (temperature, rash, injury)

STEP 3 — HIGH-ACUITY FLAG ANALYSIS:
Systematically check ALL categories:
- Cardiovascular (ACS, aortic dissection, arrhythmia)
- Neurological (stroke/TIA, seizure, altered mental status, thunderclap headache)
- Respiratory (respiratory failure, tension pneumothorax, severe asthma)
- Abdominal (peritonitis, GI hemorrhage, ectopic rupture)
- Infectious (sepsis, meningitis, necrotizing fasciitis)
- Metabolic (hypoglycemia, DKA, hypertensive emergency)

STEP 4 — VITAL SIGNS INTERPRETATION:
- Does the EWS reflect the clinical picture?
- Are there concerning vital sign trends?
- Is the patient hemodynamically stable?

STEP 5 — HISTORY SYNTHESIS:
- Do comorbidities amplify risk? (CAD, COPD, DM, immunosuppression, anticoagulation)
- Do past ED encounters suggest a deteriorating pattern?
- Does age increase vulnerability?

STEP 6 — DIFFERENTIAL DIAGNOSIS:
- Most likely diagnosis based on presenting symptoms
- Must-not-miss dangerous diagnoses
- Alternative diagnoses to consider

STEP 7 — RISK STRATIFICATION (1-10):
Combine all factors: symptom severity + EWS + age + comorbidities + encounter patterns

STEP 8 — FINAL ESI ASSIGNMENT:
1. Life-threatening intervention needed now → ESI 1 (Resuscitation Bay)
2. High-risk / severe pain / vital sign danger zone → ESI 2 (Acute Care)
3. Stable but needs ≥2 resources → ESI 3 (General ED Treatment Room)
4. Needs 1 resource, non-urgent → ESI 4 (Fast Track)
5. No resources anticipated → ESI 5 (Fast Track / Redirect to PCP)

**REQUIRED JSON OUTPUT (output ONLY this, no other text):**
{{
  "esi_level": 3,
  "is_high_acuity": false,
  "ews_score": 2,
  "clinical_assessment": "Detailed step-by-step reasoning through each assessment step",
  "risk_factors": ["risk factor 1", "risk factor 2"],
  "patient_assignment": "Care area assignment — be specific: Resuscitation Bay / Acute Care / General ED Treatment Room / Fast Track / Redirect to Urgent Care or PCP",
  "thought_process": [
    "Step 1: Symptom assessment",
    "Step 2: ABCDE primary survey",
    "Step 3: High-acuity flag analysis",
    "Step 4: Vital signs interpretation",
    "Step 5: History synthesis",
    "Step 6: Differential diagnosis",
    "Step 7: Risk stratification",
    "Step 8: ESI level and assignment decision"
  ]
}}

**IMPORTANT:**
- Start with {{ and end with }}
- No text, explanations, or markdown outside the JSON
- patient_assignment must clearly state the specific ED care area"""


# ============================================================================
# FORMATTING AGENT PROMPT
# ============================================================================

FORMATTING_AGENT_PROMPT = """You are a US ED clinical communication specialist. Format the triage assessment output for clear presentation to ED staff.

**CRITICAL: Output ONLY valid JSON. No text before or after.**

**Input:** A triage assessment JSON from the clinical reasoning agent.

**Your Task:**
1. Review the assessment
2. Format for clear display to ED charge nurse and attending physician
3. Enhance clinical rationale readability
4. Ensure patient_assignment clearly states the ED care area and urgency

**REQUIRED JSON OUTPUT:**
{{
  "esi_level": 3,
  "is_high_acuity": false,
  "ews_score": 2,
  "clinical_rationale": "Clear, readable explanation: which symptoms drove the decision, how history affects assessment, why this ESI level was chosen, specific factors that determined the patient assignment.",
  "patient_assignment": "Specific assignment — must state: Resuscitation Bay (ESI 1) / Acute Care Zone (ESI 2) / General ED Treatment Room (ESI 3) / Fast Track (ESI 4) / Fast Track or Redirect to PCP (ESI 5)",
  "thought_process": ["Step 1: Life-threat check", "Step 2: EWS scoring", "Step 3: Risk context evaluation"]
}}

**IMPORTANT:** Start with {{ and end with }}. No text outside the JSON."""


# ============================================================================
# TWO-STAGE AGENT SYSTEM
# ============================================================================

def triage_patient(
    patient_id: str,
    symptoms: str,
    vitals: Dict[str, Any],
    deepseek_model: str = "deepseek-r1:8b",
    base_url: str = "http://localhost:11434",
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Run US ED triage assessment using DeepSeek reasoning agent.

    Args:
        patient_id: Patient ID
        symptoms: Presenting symptoms (text)
        vitals: Dict with temperature, heart_rate, respiratory_rate, blood_pressure,
                oxygen_sat, consciousness, on_oxygen
        deepseek_model: DeepSeek Ollama model name
        base_url: Ollama base URL
        verbose: Enable verbose logging

    Returns:
        Dict with:
        - esi_level (1-5)
        - is_high_acuity
        - ews_score
        - clinical_rationale
        - patient_assignment  (specific ED care area)
        - thought_process
        - chain_of_thought
        - ews_result
    """
    try:
        from agent1 import ClinicalReasoningAgent
    except ImportError:
        raise ImportError("ClinicalReasoningAgent not available. Ensure agent1.py is present.")

    # Calculate EWS
    ews_result = calculate_ews_score(
        temperature=vitals.get('temperature'),
        heart_rate=vitals.get('heart_rate'),
        respiratory_rate=vitals.get('respiratory_rate'),
        oxygen_sat=vitals.get('oxygen_sat'),
        blood_pressure=vitals.get('blood_pressure'),
        consciousness=vitals.get('consciousness', 'ALERT'),
        on_oxygen=vitals.get('on_oxygen', False),
    )

    if verbose:
        print(f"🧠 DeepSeek reasoning agent analyzing patient {patient_id}...")

    patients_df = get_patients_df()
    history_df = get_history_df()

    patient_row = patients_df[patients_df["patient_id"] == patient_id].iloc[0]
    dob = pd.to_datetime(patient_row["dob"])
    age = (datetime.now() - dob).days // 365

    patient_history = history_df[history_df["patient_id"] == patient_id]
    history_list = []
    for _, h_row in patient_history.iterrows():
        if h_row.get("is_active", 1):
            history_list.append(f"{h_row['condition_name']} (SNOMED: {h_row['snomed_code']})")

    past_encounters = get_last_5_encounters(patient_id)

    patient_data = {
        'patient_id': patient_id,
        'name': patient_row['name'],
        'age': age,
        'gender': patient_row['gender'],
        'dob': patient_row['dob'],
    }

    vitals_dict = {
        'temperature': vitals.get('temperature'),
        'heart_rate': vitals.get('heart_rate'),
        'respiratory_rate': vitals.get('respiratory_rate'),
        'blood_pressure': vitals.get('blood_pressure', 'Not recorded'),
        'oxygen_sat': vitals.get('oxygen_sat'),
    }

    agent = ClinicalReasoningAgent(model_name=deepseek_model)

    reasoning_output, chain_of_thought = agent.assess_patient(
        patient_data=patient_data,
        symptoms=symptoms,
        vitals=vitals_dict,
        medical_history=history_list,
        past_encounters=past_encounters,
        additional_notes="",
        news2_result=ews_result,
    )

    # Map severity category to ESI level
    esi_map = {
        "RESUSCITATION": 1,
        "EMERGENCY": 2,
        "URGENT": 3,
        "STANDARD": 4,
        "NON-URGENT": 5,
    }
    esi_level = esi_map.get(reasoning_output.severity_category, 3)

    # Build patient assignment string from ESI level
    assignment_map = {
        1: "Resuscitation Bay — immediate physician and nursing response",
        2: "Acute Care / High-Acuity Zone — provider within 10 minutes",
        3: "General ED Treatment Room — provider within 30-60 minutes",
        4: "Fast Track — provider within 1-2 hours",
        5: "Fast Track or redirect to Urgent Care / Primary Care Physician",
    }

    result = {
        "esi_level": esi_level,
        "is_high_acuity": reasoning_output.red_flag_analysis.red_flags_present,
        "ews_score": ews_result["total_score"],
        "clinical_rationale": reasoning_output.clinical_reasoning_summary,
        "patient_assignment": assignment_map.get(esi_level, reasoning_output.recommended_pathway),
        "thought_process": list(reasoning_output.thought_process) if hasattr(reasoning_output, 'thought_process') else [],
        "chain_of_thought": chain_of_thought,
        "full_reasoning": reasoning_output.dict() if hasattr(reasoning_output, 'dict') else {},
        "ews_result": ews_result,
    }

    return result


# ============================================================================
# FALLBACK PARSING FUNCTIONS
# ============================================================================

def extract_ews_from_vitals(temp: float, hr: int) -> int:
    """Calculate EWS from temperature and heart rate only."""
    score = 0
    if temp > 39.1 or temp < 35.0:
        score += 3
    elif 38.1 <= temp <= 39.0:
        score += 2
    elif 35.1 <= temp <= 36.0:
        score += 1
    if hr > 130 or hr < 40:
        score += 3
    elif 111 <= hr <= 130:
        score += 2
    elif 91 <= hr <= 110:
        score += 1
    elif 41 <= hr <= 50:
        score += 1
    return score


def extract_data_from_text(text: str) -> Dict[str, Any]:
    """Fallback: extract structured data from natural language agent output."""
    import re

    result = {}

    esi_match = re.search(r'ESI.*?(\d)', text, re.IGNORECASE)
    if esi_match:
        try:
            level = int(esi_match.group(1))
            if 1 <= level <= 5:
                result["esi_level"] = level
        except Exception:
            pass

    ews_match = re.search(r'EWS.*?(\d+)', text, re.IGNORECASE)
    if ews_match:
        try:
            result["ews_score"] = int(ews_match.group(1))
        except Exception:
            pass

    high_acuity_keywords = ["high acuity", "life-threat", "emergency", "critical", "immediate"]
    result["is_high_acuity"] = any(kw in text.lower() for kw in high_acuity_keywords)

    result["clinical_rationale"] = text[:1000] if len(text) > 1000 else text

    if "resuscitation" in text.lower() or "cardiac arrest" in text.lower():
        result["patient_assignment"] = "Resuscitation Bay — immediate response"
    elif "emergency" in text.lower() or "acute care" in text.lower():
        result["patient_assignment"] = "Acute Care / High-Acuity Zone"
    elif "urgent" in text.lower():
        result["patient_assignment"] = "General ED Treatment Room"
    elif "fast track" in text.lower():
        result["patient_assignment"] = "Fast Track"
    else:
        result["patient_assignment"] = "Fast Track or redirect to Primary Care"

    thought_process = []
    for line in text.split('\n'):
        if line.strip().startswith(('*', '-', '•', '1.', '2.', '3.')):
            thought_process.append(line.strip())
    result["thought_process"] = thought_process if thought_process else ["Assessment completed"]

    result.setdefault("esi_level", 3)
    result.setdefault("ews_score", 0)

    return result


# ============================================================================
# MAIN CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="US ED Triage Agent — DeepSeek Reasoning")
    parser.add_argument("--patient_id", type=str, required=True, help="Patient ID (e.g., P00001)")
    parser.add_argument("--symptoms", type=str, required=True, help="Presenting symptoms")
    parser.add_argument("--temperature", type=float, help="Temperature in Celsius")
    parser.add_argument("--heart_rate", type=int, help="Heart rate in bpm")
    parser.add_argument("--deepseek_model", type=str, default="deepseek-r1:8b", help="DeepSeek model name")
    parser.add_argument("--base_url", type=str, default="http://localhost:11434", help="Ollama base URL")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    print("Loading clinical data...")
    load_data()

    vitals = {
        "temperature": args.temperature,
        "heart_rate": args.heart_rate,
        "respiratory_rate": None,
        "blood_pressure": None,
        "oxygen_sat": None,
        "consciousness": "ALERT",
        "on_oxygen": False,
    }

    print(f"\n{'='*60}")
    print(f"INCOMING PATIENT: {args.patient_id}")
    print(f"PRESENTING SYMPTOMS: {args.symptoms}")
    print(f"{'='*60}\n")

    result = triage_patient(
        args.patient_id,
        args.symptoms,
        vitals,
        deepseek_model=args.deepseek_model,
        base_url=args.base_url,
        verbose=args.verbose,
    )

    print("\n" + "=" * 60)
    print("TRIAGE RESULT:")
    print("=" * 60)
    print(json.dumps(result, indent=2))
    print("=" * 60)


if __name__ == "__main__":
    main()
