"""
Triage Orchestrator — Real-Time AI Triage Intelligence System

End-to-end LangGraph workflow for incoming patients:

  Voice Intake → Clinical Triage → Diagnostics → Deterioration Prediction
      → Queue Update → Nurse Feedback Adjustment → Final TriageResult

Handles both walk-in patients and 911/ambulance arrivals.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import TypedDict, Optional, Dict, Any, List

try:
    from langgraph.graph import StateGraph, END
except ImportError:
    raise ImportError("Please install langgraph: pip install langgraph>=0.0.40")

# Local agents
from voice_intake_agent import process_voice_intake, VoiceIntakeResult
from us_triage_agent import load_data, get_patients_df, get_history_df, calculate_ews_score, get_last_5_encounters
from us_clinical_workflow import run_clinical_workflow
from diagnostics_agent import DiagnosticsInput, run_diagnostics_agent
from deterioration_agent import DeteriorationInput, predict_deterioration
from queue_agent import add_or_update_patient, QueueUpdateResult
from nurse_feedback_agent import get_adjusted_esi
from sepsis_screener import screen_for_sepsis
from specialist_agent import SpecialistInput, assign_specialist


# ============================================================================
# ESI MAPPING
# ============================================================================

ESI_DECISION_MAP = {
    "RESUSCITATION": 1,
    "EMERGENT": 2,
    "URGENT": 3,
    "LESS_URGENT": 4,
    "NON_URGENT": 5,
}


# ============================================================================
# STATE SCHEMA
# ============================================================================

class TriageWorkflowState(TypedDict):
    # --- Input ---
    patient_id: str
    transcript: str
    voice_metadata: Optional[Dict[str, Any]]
    vitals: Dict[str, Any]
    arrival_mode: str   # "walk_in" | "911" | "ambulance"

    # --- Stage 1: Voice Intake ---
    voice_intake_result: Optional[Dict[str, Any]]

    # --- Sepsis Screen (pre-LLM) ---
    sepsis_result: Optional[Dict[str, Any]]

    # --- Stage 2: Clinical Triage ---
    symptoms_text: str
    triage_workflow_state: Optional[Dict[str, Any]]
    final_triage_decision: Optional[Dict[str, Any]]
    esi_level: Optional[int]

    # --- Stage 3: Diagnostics ---
    diagnostics_output: Optional[Dict[str, Any]]

    # --- Stage 4: Deterioration ---
    deterioration_prediction: Optional[Dict[str, Any]]

    # --- Stage 5: Queue Update ---
    queue_result: Optional[Dict[str, Any]]

    # --- Post-processing ---
    adjusted_esi_level: Optional[int]
    adjustment_rationale: Optional[str]
    pre_arrival_note: Optional[str]

    # --- Stage 6: Specialist Assignment ---
    specialist_assignment: Optional[Dict[str, Any]]

    # --- Final Output ---
    triage_result: Optional[Dict[str, Any]]

    # --- Metadata ---
    workflow_complete: bool
    error: Optional[str]
    started_at: str
    completed_at: Optional[str]
    model_name: str
    base_url: str
    provider: str
    api_key: Optional[str]


# ============================================================================
# PRE-ARRIVAL NOTES (deterministic lookup by ESI level)
# ============================================================================

PRE_ARRIVAL_NOTES: Dict[int, str] = {
    1: "ACTIVATE RESUS/TRAUMA TEAM NOW. Prepare airway equipment, crash cart, and defibrillator. All hands to resuscitation bay.",
    2: "Alert attending physician and bedside nurse for immediate evaluation. Have IV access, monitoring, and crash cart accessible.",
    3: "Assign general treatment room, notify charge nurse. Initiate standard vitals monitoring on arrival.",
    4: "Route to Fast Track area. Standard intake procedures — no immediate resource pre-positioning required.",
    5: "Direct to waiting area for routine evaluation. No resource preparation needed.",
}


# ============================================================================
# WORKFLOW NODES
# ============================================================================

def sepsis_screen_node(state: TriageWorkflowState) -> TriageWorkflowState:
    """
    Stage 0 (pre-LLM): qSOFA sepsis screening.
    Deterministic, <1ms. Flags sepsis concern for downstream injection.
    """
    try:
        result = screen_for_sepsis(state["patient_id"], state["vitals"])
        state["sepsis_result"] = result.dict()
    except Exception as e:
        state["sepsis_result"] = None
        state["error"] = state.get("error") or f"[Sepsis screen warning] {str(e)}"
    return state


def voice_intake_node(state: TriageWorkflowState) -> TriageWorkflowState:
    """
    Stage 1: Process patient voice/text input.
    Scores voice quality, extracts symptoms, computes urgency modifier.
    """
    try:
        result: VoiceIntakeResult = process_voice_intake(
            patient_id=state["patient_id"],
            transcript=state["transcript"],
            metadata=state.get("voice_metadata"),
        )
        state["voice_intake_result"] = result.dict()

        # Build symptoms text for triage (use extracted symptoms if available,
        # fall back to raw transcript)
        if result.extracted_symptoms:
            base_symptoms = ", ".join(result.extracted_symptoms)
        else:
            base_symptoms = state["transcript"]

        # Append duration/severity context if extracted
        extras = []
        if result.symptom_duration:
            extras.append(f"for {result.symptom_duration}")
        if result.symptom_severity_self_reported:
            extras.append(f"severity {result.symptom_severity_self_reported}")
        if extras:
            base_symptoms += f" ({', '.join(extras)})"

        state["symptoms_text"] = base_symptoms

    except Exception as e:
        state["voice_intake_result"] = None
        state["symptoms_text"] = state["transcript"]
        state["error"] = state.get("error") or f"[Voice intake warning] {str(e)}"

    # Inject sepsis context if qSOFA positive (must run after symptoms_text is built)
    sepsis = state.get("sepsis_result") or {}
    if sepsis.get("sepsis_concern") and sepsis.get("sepsis_injection_text"):
        state["symptoms_text"] = sepsis["sepsis_injection_text"] + state["symptoms_text"]

    return state


def triage_node(state: TriageWorkflowState) -> TriageWorkflowState:
    """
    Stage 2: Run clinical triage workflow (ESI assignment).
    Uses us_clinical_workflow.run_clinical_workflow — includes:
      - Short-circuit high-acuity flag detection
      - Agent 1: Clinical Reasoning
      - Agent 2: Safety Verification
      - Finalize patient assignment
    """
    try:
        triage_state = run_clinical_workflow(
            patient_id=state["patient_id"],
            symptoms=state["symptoms_text"],
            vitals=state["vitals"],
            model_name=state["model_name"],
            base_url=state["base_url"],
            provider=state.get("provider", "ollama"),
            api_key=state.get("api_key"),
        )

        state["triage_workflow_state"] = dict(triage_state)
        final_decision = triage_state.get("final_decision", {})
        state["final_triage_decision"] = final_decision

        # Derive integer ESI level from decision string
        decision_str = final_decision.get("triage_decision", "URGENT")
        state["esi_level"] = ESI_DECISION_MAP.get(decision_str, 3)

        # Propagate triage errors as warnings (don't abort pipeline)
        if triage_error := triage_state.get("error"):
            state["error"] = state.get("error") or f"[Triage warning] {triage_error}"

    except Exception as e:
        # Fail-safe defaults
        state["final_triage_decision"] = {
            "triage_decision": "URGENT",
            "patient_assignment": "General ED Treatment Room — manual review required",
            "clinical_reasoning": f"Triage agent error: {str(e)}",
            "escalation_required": True,
            "physician_notification_required": True,
        }
        state["esi_level"] = 3
        state["error"] = state.get("error") or f"[Triage error] {str(e)}"

    return state


def diagnostics_node(state: TriageWorkflowState) -> TriageWorkflowState:
    """
    Stage 3: Generate clinical diagnostic workup plan.
    """
    try:
        patients_df = get_patients_df()
        history_df = get_history_df()

        patient_row = patients_df[patients_df["patient_id"] == state["patient_id"]].iloc[0]
        import pandas as pd
        dob = pd.to_datetime(patient_row["dob"])
        patient_age = (datetime.now() - dob).days // 365

        # Get active conditions
        patient_history = history_df[history_df["patient_id"] == state["patient_id"]]
        active_conditions = []
        for _, h_row in patient_history.iterrows():
            if h_row.get("is_active", 1):
                active_conditions.append(h_row["condition_name"])

        voice_result = state.get("voice_intake_result") or {}
        extracted_symptoms = voice_result.get("extracted_symptoms", [])
        if not extracted_symptoms:
            extracted_symptoms = [state["symptoms_text"]]

        final_decision = state.get("final_triage_decision", {})
        ews_result = state.get("triage_workflow_state", {}).get("ews_result", {})

        diag_input = DiagnosticsInput(
            patient_id=state["patient_id"],
            symptoms=extracted_symptoms,
            esi_level=state.get("esi_level", 3),
            triage_decision=final_decision.get("triage_decision", "URGENT"),
            patient_age=patient_age,
            patient_gender=patient_row.get("gender", "Unknown"),
            active_conditions=active_conditions,
            vitals=state["vitals"],
            ews_score=ews_result.get("total_score", 0),
            clinical_reasoning_summary=final_decision.get("clinical_reasoning", ""),
        )

        result = run_diagnostics_agent(
            diag_input,
            model_name=state["model_name"],
            base_url=state["base_url"],
            provider=state.get("provider", "ollama"),
            api_key=state.get("api_key"),
        )
        state["diagnostics_output"] = result.dict()

    except Exception as e:
        state["diagnostics_output"] = {
            "patient_id": state["patient_id"],
            "primary_differential": ["Manual assessment required"],
            "secondary_differential": [],
            "immediate_interventions": ["Physician assessment"],
            "labs_ordered": [],
            "imaging": [],
            "monitoring": [],
            "clinical_rationale": f"Diagnostics agent error: {str(e)}",
            "urgency_flag": state.get("esi_level", 3) <= 2,
            "generated_at": datetime.now().isoformat(),
        }
        state["error"] = state.get("error") or f"[Diagnostics warning] {str(e)}"

    return state


def deterioration_node(state: TriageWorkflowState) -> TriageWorkflowState:
    """
    Stage 4: Predict 30-60 minute clinical deterioration risk.
    """
    try:
        patients_df = get_patients_df()
        history_df = get_history_df()

        import pandas as pd
        patient_row = patients_df[patients_df["patient_id"] == state["patient_id"]].iloc[0]
        dob = pd.to_datetime(patient_row["dob"])
        patient_age = (datetime.now() - dob).days // 365

        patient_history = history_df[history_df["patient_id"] == state["patient_id"]]
        active_conditions = [
            h_row["condition_name"]
            for _, h_row in patient_history.iterrows()
            if h_row.get("is_active", 1)
        ]

        voice_result = state.get("voice_intake_result") or {}
        extracted_symptoms = voice_result.get("extracted_symptoms", [])
        ews_result = state.get("triage_workflow_state", {}).get("ews_result", {})

        det_input = DeteriorationInput(
            patient_id=state["patient_id"],
            vitals=state["vitals"],
            ews_score=ews_result.get("total_score", 0),
            symptoms=extracted_symptoms,
            esi_level=state.get("esi_level", 3),
            patient_age=patient_age,
            active_conditions=active_conditions,
            arrival_time=state["started_at"],
        )

        past_enc = get_last_5_encounters(state["patient_id"])
        prediction = predict_deterioration(det_input, past_encounters_df=past_enc)
        state["deterioration_prediction"] = prediction.dict()

    except Exception as e:
        state["deterioration_prediction"] = {
            "patient_id": state["patient_id"],
            "risk_score": 0.5,
            "risk_level": "MEDIUM",
            "time_window": "30-60 minutes",
            "risk_factors": [f"Deterioration prediction error: {str(e)}"],
            "predicted_trajectory": "WORSENING",
            "confidence": 0.0,
            "recommended_reassessment_minutes": 30,
            "score_components": {},
            "predicted_at": datetime.now().isoformat(),
        }
        state["error"] = state.get("error") or f"[Deterioration warning] {str(e)}"

    return state


def queue_update_node(state: TriageWorkflowState) -> TriageWorkflowState:
    """
    Stage 5: Add patient to queue and re-prioritise all waiting patients.
    """
    try:
        patients_df = get_patients_df()
        patient_row = patients_df[patients_df["patient_id"] == state["patient_id"]].iloc[0]

        det = state.get("deterioration_prediction") or {}
        final_decision = state.get("final_triage_decision") or {}

        entry_data = {
            "patient_id": state["patient_id"],
            "patient_name": patient_row.get("name", "Unknown"),
            "esi_level": state.get("esi_level", 3),
            "triage_decision": final_decision.get("triage_decision", "URGENT"),
            "deterioration_risk": det.get("risk_score", 0.0),
            "deterioration_level": det.get("risk_level", "LOW"),
            "predicted_trajectory": det.get("predicted_trajectory", "STABLE"),
            "arrival_time": state["started_at"],
            "patient_assignment": final_decision.get("patient_assignment", ""),
        }

        queue_result: QueueUpdateResult = add_or_update_patient(entry_data)
        state["queue_result"] = queue_result.dict()

    except Exception as e:
        state["queue_result"] = None
        state["error"] = state.get("error") or f"[Queue warning] {str(e)}"

    return state


def specialist_node(state: TriageWorkflowState) -> TriageWorkflowState:
    """
    Stage 6: Assign a medical specialist based on the triage and diagnostics output.
    """
    try:
        diagnostics = state.get("diagnostics_output") or {}
        final_decision = state.get("final_triage_decision") or {}
        voice_result = state.get("voice_intake_result") or {}
        sepsis = state.get("sepsis_result") or {}

        patients_df = get_patients_df()
        patient_row = patients_df[patients_df["patient_id"] == state["patient_id"]].iloc[0]
        import pandas as pd
        dob = pd.to_datetime(patient_row["dob"])
        patient_age = (datetime.now() - dob).days // 365

        inp = SpecialistInput(
            patient_id=state["patient_id"],
            esi_level=state.get("esi_level", 3),
            triage_decision=final_decision.get("triage_decision", "URGENT"),
            primary_differential=diagnostics.get("primary_differential", []),
            secondary_differential=diagnostics.get("secondary_differential", []),
            clinical_reasoning=final_decision.get("clinical_reasoning", ""),
            extracted_symptoms=voice_result.get("extracted_symptoms", [state.get("symptoms_text", "")]),
            patient_age=patient_age,
            patient_gender=patient_row.get("gender"),
            vitals=state.get("vitals", {}),
            sepsis_concern=sepsis.get("sepsis_concern", False),
            labs_ordered=diagnostics.get("labs_ordered", []),
            imaging=diagnostics.get("imaging", []),
        )

        assignment = assign_specialist(
            inp,
            provider=state.get("provider", "ollama"),
            model_name=state.get("model_name", "deepseek-r1:8b"),
            api_key=state.get("api_key"),
            base_url=state.get("base_url", "http://localhost:11434"),
        )
        state["specialist_assignment"] = assignment.dict()

    except Exception as e:
        state["specialist_assignment"] = {
            "patient_id": state["patient_id"],
            "primary_specialist": "Emergency Medicine Physician",
            "department": "Emergency Department",
            "reason": "Specialist assignment unavailable — managed by EM team.",
            "secondary_specialist": None,
            "urgency_for_specialist": "WITHIN_1H",
            "handoff_instructions": "Standard ED workup in progress.",
            "estimated_disposition": "OBSERVE",
            "error": str(e),
        }

    return state


def finalize_node(state: TriageWorkflowState) -> TriageWorkflowState:
    """
    Stage 7: Apply nurse feedback adjustment, assemble final TriageResult.
    """
    try:
        # Apply nurse correction weights
        voice_result = state.get("voice_intake_result") or {}
        extracted_symptoms = voice_result.get("extracted_symptoms", [])
        esi_level = state.get("esi_level", 3)

        adjusted_esi, adjustment_rationale = get_adjusted_esi(esi_level, extracted_symptoms)
        state["adjusted_esi_level"] = adjusted_esi
        state["adjustment_rationale"] = adjustment_rationale

        # Pre-arrival team prep note (only for 911 / ambulance arrivals)
        if state.get("arrival_mode") in ("911", "ambulance"):
            state["pre_arrival_note"] = PRE_ARRIVAL_NOTES.get(adjusted_esi, PRE_ARRIVAL_NOTES[3])
        else:
            state["pre_arrival_note"] = None

        # Pull all components together
        final_decision = state.get("final_triage_decision") or {}
        det = state.get("deterioration_prediction") or {}
        diagnostics = state.get("diagnostics_output") or {}
        queue = state.get("queue_result") or {}
        new_entry = queue.get("new_entry") or {}

        patients_df = get_patients_df()
        patient_row = patients_df[patients_df["patient_id"] == state["patient_id"]].iloc[0]

        completed_at = datetime.now().isoformat()
        started_at = state.get("started_at", completed_at)
        try:
            processing_secs = (
                datetime.fromisoformat(completed_at) - datetime.fromisoformat(started_at)
            ).total_seconds()
        except Exception:
            processing_secs = 0.0

        state["triage_result"] = {
            # Patient identity
            "patient_id": state["patient_id"],
            "patient_name": patient_row.get("name", "Unknown"),
            "arrival_mode": state.get("arrival_mode", "walk_in"),
            # ESI assignment
            "final_esi_level": adjusted_esi,
            "original_esi_level": esi_level,
            "triage_decision": final_decision.get("triage_decision", "URGENT"),
            "patient_assignment": final_decision.get("patient_assignment", "General ED Treatment Room"),
            "adjusted_esi_rationale": adjustment_rationale,
            # Voice quality
            "voice_quality_score": voice_result.get("voice_quality_score", 0.0),
            "urgency_modifier": voice_result.get("urgency_modifier", 0.0),
            "extracted_symptoms": extracted_symptoms,
            "symptom_duration": voice_result.get("symptom_duration"),
            "symptom_severity_self_reported": voice_result.get("symptom_severity_self_reported"),
            # Clinical reasoning
            "clinical_reasoning": final_decision.get("clinical_reasoning", ""),
            "escalation_required": final_decision.get("escalation_required", False),
            "physician_notification_required": final_decision.get("physician_notification_required", False),
            "safety_validation": final_decision.get("safety_validation", ""),
            # Diagnostics plan
            "diagnostics": {
                "primary_differential": diagnostics.get("primary_differential", []),
                "secondary_differential": diagnostics.get("secondary_differential", []),
                "immediate_interventions": diagnostics.get("immediate_interventions", []),
                "labs_ordered": diagnostics.get("labs_ordered", []),
                "imaging": diagnostics.get("imaging", []),
                "monitoring": diagnostics.get("monitoring", []),
                "clinical_rationale": diagnostics.get("clinical_rationale", ""),
                "soap_note": diagnostics.get("soap_note"),
                "icd10_codes": diagnostics.get("icd10_codes", []),
                "cpt_codes": diagnostics.get("cpt_codes", []),
            },
            # Deterioration prediction
            "deterioration": {
                "risk_score": det.get("risk_score", 0.0),
                "risk_level": det.get("risk_level", "LOW"),
                "predicted_trajectory": det.get("predicted_trajectory", "STABLE"),
                "time_window": det.get("time_window", "30-60 minutes"),
                "risk_factors": det.get("risk_factors", []),
                "recommended_reassessment_minutes": det.get("recommended_reassessment_minutes", 60),
                "confidence": det.get("confidence", 0.0),
            },
            # Queue
            "queue_position": new_entry.get("queue_position", 0),
            "priority_score": new_entry.get("priority_score", 0.0),
            "priority_rationale": new_entry.get("priority_rationale", ""),
            # Specialist assignment
            "specialist_assignment": state.get("specialist_assignment"),
            # Metadata
            "processing_time_seconds": round(processing_secs, 2),
            "completed_at": completed_at,
            # Improvements
            "sepsis_result": state.get("sepsis_result"),
            "pre_arrival_note": state.get("pre_arrival_note"),
        }

        state["completed_at"] = completed_at
        state["workflow_complete"] = True

    except Exception as e:
        state["triage_result"] = {
            "patient_id": state["patient_id"],
            "error": str(e),
            "triage_decision": "URGENT",
            "patient_assignment": "Manual triage review required",
            "final_esi_level": state.get("esi_level", 3),
        }
        state["workflow_complete"] = True
        state["error"] = state.get("error") or f"[Finalize error] {str(e)}"

    return state


# ============================================================================
# LANGGRAPH WORKFLOW
# ============================================================================

def create_triage_orchestrator():
    """Build and compile the full triage LangGraph workflow."""
    workflow = StateGraph(TriageWorkflowState)

    workflow.add_node("sepsis_screen", sepsis_screen_node)
    workflow.add_node("voice_intake", voice_intake_node)
    workflow.add_node("triage", triage_node)
    workflow.add_node("diagnostics", diagnostics_node)
    workflow.add_node("deterioration", deterioration_node)
    workflow.add_node("queue_update", queue_update_node)
    workflow.add_node("specialist", specialist_node)
    workflow.add_node("finalize", finalize_node)

    workflow.set_entry_point("sepsis_screen")
    workflow.add_edge("sepsis_screen", "voice_intake")
    workflow.add_edge("voice_intake", "triage")
    workflow.add_edge("triage", "diagnostics")
    workflow.add_edge("diagnostics", "deterioration")
    workflow.add_edge("deterioration", "queue_update")
    workflow.add_edge("queue_update", "specialist")
    workflow.add_edge("specialist", "finalize")
    workflow.add_edge("finalize", END)

    return workflow.compile()


# ============================================================================
# MAIN PUBLIC ENTRY POINT
# ============================================================================

def run_triage_pipeline(
    patient_id: str,
    transcript: str,
    vitals: Dict[str, Any],
    voice_metadata: Optional[Dict[str, Any]] = None,
    arrival_mode: str = "walk_in",
    model_name: str = "deepseek-r1:8b",
    base_url: str = "http://localhost:11434",
    provider: str = "ollama",
    api_key: Optional[str] = None,
    ensure_data_loaded: bool = True,
) -> Dict[str, Any]:
    """
    Run the complete real-time AI triage pipeline for an incoming patient.

    Args:
        patient_id: Patient identifier (must exist in patient_demographics.csv)
        transcript: Patient's spoken/typed symptom description
        vitals: Vital signs dict with keys: temperature, heart_rate,
                respiratory_rate, blood_pressure, oxygen_sat, consciousness
        voice_metadata: Optional STT metadata (confidence_scores, audio_quality, etc.)
        arrival_mode: "walk_in" | "911" | "ambulance"
        model_name: Model name (Ollama tag or Gemini model ID)
        base_url: Ollama base URL (ignored for Gemini)
        provider: "ollama" | "gemini"
        api_key: Google API key (required when provider="gemini")
        ensure_data_loaded: If True, calls load_data() if DataFrames not loaded yet

    Returns:
        Complete TriageResult dict with ESI assignment, patient assignment,
        diagnostics plan, deterioration prediction, specialist assignment, and queue position.
    """
    if ensure_data_loaded:
        patients_df = get_patients_df()
        if patients_df is None:
            load_data()

    orchestrator = create_triage_orchestrator()

    initial_state: TriageWorkflowState = {
        "patient_id": patient_id,
        "transcript": transcript,
        "voice_metadata": voice_metadata,
        "vitals": vitals,
        "arrival_mode": arrival_mode,
        "sepsis_result": None,
        "voice_intake_result": None,
        "symptoms_text": "",
        "triage_workflow_state": None,
        "final_triage_decision": None,
        "esi_level": None,
        "diagnostics_output": None,
        "deterioration_prediction": None,
        "queue_result": None,
        "specialist_assignment": None,
        "adjusted_esi_level": None,
        "adjustment_rationale": None,
        "pre_arrival_note": None,
        "triage_result": None,
        "workflow_complete": False,
        "error": None,
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "model_name": model_name,
        "base_url": base_url,
        "provider": provider,
        "api_key": api_key,
    }

    try:
        final_state = orchestrator.invoke(initial_state)
        return final_state.get("triage_result") or _error_result(patient_id, "No triage result produced")
    except Exception as e:
        import traceback
        return _error_result(patient_id, f"{str(e)}\n{traceback.format_exc()}")


def _error_result(patient_id: str, error_msg: str) -> Dict[str, Any]:
    """Return a safe fallback TriageResult when the pipeline fails completely."""
    return {
        "patient_id": patient_id,
        "error": error_msg,
        "triage_decision": "URGENT",
        "final_esi_level": 3,
        "patient_assignment": "General ED Treatment Room — manual review required",
        "physician_notification_required": True,
        "escalation_required": True,
        "completed_at": datetime.now().isoformat(),
    }


# ============================================================================
# CLI DEMO
# ============================================================================

def _print_triage_result(result: Dict[str, Any]) -> None:
    """Pretty-print a TriageResult to terminal."""
    sep = "=" * 70
    print(sep)
    print(f"  TRIAGE RESULT — Patient {result.get('patient_id', 'N/A')}")
    print(sep)

    print(f"\n  Arrival Mode   : {result.get('arrival_mode', 'N/A')}")
    print(f"  ESI Level      : {result.get('final_esi_level', 'N/A')} "
          f"(original: {result.get('original_esi_level', 'N/A')})")
    print(f"  Decision       : {result.get('triage_decision', 'N/A')}")
    print(f"  Assignment     : {result.get('patient_assignment', 'N/A')}")
    print(f"  Queue Position : #{result.get('queue_position', 'N/A')} "
          f"(score: {result.get('priority_score', 0):.1f})")

    if result.get("adjusted_esi_rationale"):
        print(f"\n  ESI Adjustment : {result['adjusted_esi_rationale']}")

    vqs = result.get("voice_quality_score", 0)
    um = result.get("urgency_modifier", 0)
    print(f"\n  Voice Quality  : {vqs:.1f}/10  "
          f"(urgency modifier: {um:+.2f})")
    symptoms = result.get("extracted_symptoms", [])
    print(f"  Symptoms       : {', '.join(symptoms) if symptoms else 'N/A'}")
    if result.get("symptom_duration"):
        print(f"  Duration       : {result['symptom_duration']}")

    det = result.get("deterioration", {})
    print(f"\n  Deterioration Risk  : {det.get('risk_level', 'N/A')} "
          f"({det.get('risk_score', 0):.0%}) — "
          f"{det.get('predicted_trajectory', 'N/A')}")
    print(f"  Reassess in    : {det.get('recommended_reassessment_minutes', 'N/A')} minutes")

    diag = result.get("diagnostics", {})
    if diag.get("primary_differential"):
        print(f"\n  Primary Differential:")
        for d in diag["primary_differential"]:
            print(f"    • {d}")
    if diag.get("immediate_interventions"):
        print(f"\n  Immediate Interventions:")
        for iv in diag["immediate_interventions"][:3]:
            print(f"    ▶ {iv}")

    if result.get("physician_notification_required"):
        print("\n  ⚠️  PHYSICIAN NOTIFICATION REQUIRED")
    if result.get("escalation_required"):
        print("  ⚠️  ESCALATION REQUIRED")

    print(f"\n  Processing time: {result.get('processing_time_seconds', 0):.1f}s")
    print(sep + "\n")


if __name__ == "__main__":
    import json

    # Load patient data
    load_data()

    # ── Test Case 1: High-acuity chest pain (ESI 2, should short-circuit) ──
    print("\n[Test 1] Chest Pain — ESI 2 expected")
    result1 = run_triage_pipeline(
        patient_id="P00001",
        transcript=(
            "I have crushing chest pain that started about 30 minutes ago. "
            "It's radiating to my left arm. I'm sweating a lot. "
            "Worst pain of my life, 9 out of 10."
        ),
        vitals={
            "temperature": 37.0,
            "heart_rate": 110,
            "respiratory_rate": 22,
            "blood_pressure": "145/90",
            "oxygen_sat": 95,
            "consciousness": "ALERT",
            "on_oxygen": False,
        },
        arrival_mode="911",
    )
    _print_triage_result(result1)

    # ── Test Case 2: Minor complaint (ESI 4-5 expected) ──
    print("[Test 2] Minor Cough — ESI 4-5 expected")
    result2 = run_triage_pipeline(
        patient_id="P00002",
        transcript="I've had a mild dry cough for 2 days. No fever. Feeling okay otherwise.",
        vitals={
            "temperature": 37.1,
            "heart_rate": 78,
            "respiratory_rate": 16,
            "blood_pressure": "118/76",
            "oxygen_sat": 99,
            "consciousness": "ALERT",
            "on_oxygen": False,
        },
        arrival_mode="walk_in",
    )
    _print_triage_result(result2)
