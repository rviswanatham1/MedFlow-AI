"""
ED Triage AI — Streamlit Testing UI

Run:  streamlit run app.py
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional

import pandas as pd
import numpy as np
import streamlit as st

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="ED Triage AI",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# CSS OVERRIDES
# ============================================================================

st.markdown("""
<style>
.esi-badge {
    display: inline-block;
    padding: 6px 18px;
    border-radius: 8px;
    font-size: 1.6em;
    font-weight: bold;
    color: white;
    margin-bottom: 10px;
}
.risk-bar-label { font-size: 0.85em; color: #555; margin-bottom: 2px; }
.section-header { font-size: 1.1em; font-weight: 600; margin-top: 10px; }
.alert-box {
    padding: 10px 14px;
    border-radius: 6px;
    margin: 6px 0;
    font-weight: 500;
}
.alert-critical { background: #ffebee; border-left: 4px solid #c62828; color: #b71c1c; }
.alert-high     { background: #fff3e0; border-left: 4px solid #e65100; color: #bf360c; }
.alert-info     { background: #e3f2fd; border-left: 4px solid #1565c0; color: #0d47a1; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# ESI COLORS
# ============================================================================

ESI_COLORS = {1: "#c62828", 2: "#e65100", 3: "#f9a825", 4: "#1565c0", 5: "#2e7d32"}
ESI_LABELS = {
    1: "IMMEDIATE RESUSCITATION",
    2: "EMERGENT",
    3: "URGENT",
    4: "LESS URGENT",
    5: "NON-URGENT",
}
RISK_COLORS = {"LOW": "#2e7d32", "MEDIUM": "#f57f17", "HIGH": "#e65100", "CRITICAL": "#c62828"}

# ============================================================================
# LAZY IMPORTS & DATA LOADING
# ============================================================================

@st.cache_resource(show_spinner="Loading patient database...")
def _load_pipeline():
    """Import heavy modules and load CSVs once per session."""
    from us_triage_agent import load_data, get_patients_df
    load_data()
    return get_patients_df()

def _get_patient_ids() -> list:
    try:
        df = _load_pipeline()
        return df["patient_id"].dropna().tolist() if df is not None else []
    except Exception:
        return [f"P{str(i).zfill(5)}" for i in range(1, 21)]

# ============================================================================
# MOCK DATA (Demo Mode — no Ollama required)
# ============================================================================

MOCK_RESULT: Dict[str, Any] = {
    "patient_id": "P00001",
    "patient_name": "Alice Thompson",
    "arrival_mode": "911",
    "final_esi_level": 2,
    "original_esi_level": 3,
    "triage_decision": "EMERGENT",
    "patient_assignment": "Acute Care / High-Acuity Zone — provider within 10 minutes",
    "adjusted_esi_rationale": (
        "Nurse corrections for cardiovascular presentations average -1.0 ESI points "
        "(n=5 corrections) — upgraded: ESI 3 → ESI 2."
    ),
    "voice_quality_score": 4.2,
    "urgency_modifier": -0.55,
    "extracted_symptoms": ["chest pain", "chest pressure", "diaphoresis", "shortness of breath"],
    "symptom_duration": "30 minutes",
    "symptom_severity_self_reported": "9/10",
    "clinical_reasoning": (
        "58-year-old male with acute-onset crushing chest pain radiating to left arm, "
        "diaphoresis, and shortness of breath for 30 minutes. History of coronary artery disease "
        "and diabetes. EWS score 4. Presentation highly consistent with ACS (STEMI/NSTEMI). "
        "Immediate 12-lead ECG and troponin indicated. Haemodynamically borderline."
    ),
    "escalation_required": True,
    "physician_notification_required": True,
    "safety_validation": "Agent 2 confirmed ESI 2. Red flags verified: ACS presentation.",
    "queue_position": 1,
    "priority_score": 112.4,
    "priority_rationale": "ESI 2 (+80), Deterioration 72% (+21.6), Wait 2min (+0.8) = 112.4",
    "processing_time_seconds": 18.3,
    "completed_at": datetime.now().isoformat(),
    "sepsis_result": {
        "patient_id": "P00001",
        "qsofa_score": 0,
        "qsofa_components": {"tachypnea_rr_ge_22": False, "hypotension_sbp_le_100": False, "altered_mentation": False},
        "sepsis_concern": False,
        "recommendation": "qSOFA 0/3 — low immediate sepsis concern.",
        "fever_detected": False,
        "hypoxia_detected": False,
        "sepsis_injection_text": "",
    },
    "pre_arrival_note": (
        "Alert attending physician and bedside nurse for immediate evaluation. "
        "Have IV access, monitoring, and crash cart accessible."
    ),
    "diagnostics": {
        "primary_differential": [
            "Acute Coronary Syndrome — NSTEMI",
            "Acute Coronary Syndrome — STEMI",
            "Unstable Angina",
            "Aortic Dissection",
            "Pulmonary Embolism",
        ],
        "secondary_differential": [
            "Hypertensive Emergency",
            "Severe GERD / Esophageal Spasm",
        ],
        "immediate_interventions": [
            "12-lead ECG within 10 minutes of arrival",
            "IV access × 2 large-bore",
            "Aspirin 325 mg PO (unless contraindicated)",
            "Sublingual nitroglycerin (if SBP > 90)",
            "Continuous cardiac monitoring + pulse oximetry",
        ],
        "labs_ordered": [
            "Troponin I (serial at 0h and 3h)",
            "BMP (electrolytes, renal function, glucose)",
            "CBC with differential",
            "PT/INR and aPTT",
            "BNP",
            "Lipid panel",
        ],
        "imaging": [
            "Portable chest X-ray",
            "CT angiography chest if aortic dissection not excluded",
        ],
        "monitoring": [
            "Continuous 12-lead cardiac monitoring",
            "SpO2 Q15min",
            "BP Q15min",
            "Telemetry",
        ],
        "clinical_rationale": (
            "ACS is the must-not-miss diagnosis given the classic symptom triad "
            "(crushing chest pain, radiation, diaphoresis) in a patient with known CAD and DM. "
            "Serial troponins and ECG are first-line. CT angiography is held pending initial workup."
        ),
    },
    "deterioration": {
        "risk_score": 0.72,
        "risk_level": "HIGH",
        "predicted_trajectory": "RAPID_DETERIORATION",
        "time_window": "30-60 minutes",
        "risk_factors": [
            "EWS score 4 (+0.08)",
            "Tachycardia 110 bpm (+0.03)",
            "Symptom 'chest pain' (+0.15)",
            "Symptom 'diaphoresis' (+0.10)",
            "History: coronary artery disease (+0.08)",
            "Age 58 (no additional age penalty)",
            "ESI level 2 (+0.12)",
        ],
        "recommended_reassessment_minutes": 15,
        "confidence": 0.83,
    },
    "specialist_assignment": {
        "patient_id": "P00001",
        "primary_specialist": "Cardiologist",
        "department": "Cardiac Care Unit (CCU)",
        "reason": (
            "Classic ACS presentation (crushing chest pain, diaphoresis, radiation) in a patient "
            "with known coronary artery disease requires immediate cardiology consultation for "
            "catheterization lab evaluation and STEMI protocol activation."
        ),
        "secondary_specialist": "Intensivist / Critical Care",
        "urgency_for_specialist": "IMMEDIATE",
        "handoff_instructions": (
            "Activate STEMI protocol. 12-lead ECG and serial troponins already ordered. "
            "Patient hemodynamically borderline — crash cart at bedside."
        ),
        "estimated_disposition": "ADMIT",
        "error": None,
    },
}

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.image("https://img.icons8.com/color/96/hospital.png", width=60)
    st.title("ED Triage AI")
    st.caption("Real-Time Triage Intelligence System")
    st.divider()

    demo_mode = st.toggle("Demo Mode (no Ollama needed)", value=True)

    # Clear stale results when mode switches so other tabs don't show demo data in LLM mode
    prev_mode = st.session_state.get("_prev_demo_mode", demo_mode)
    if prev_mode != demo_mode:
        st.session_state.pop("last_result", None)
        st.session_state.pop("appt_plan", None)
    st.session_state["_prev_demo_mode"] = demo_mode

    if demo_mode:
        st.info("Demo Mode ON — returns mock data. Toggle off to use live AI pipeline.")

    st.divider()
    with st.expander("Model Configuration", expanded=not demo_mode):
        provider = st.radio(
            "LLM Provider",
            options=["ollama", "gemini"],
            format_func=lambda x: "🤖 DeepSeek / Ollama" if x == "ollama" else "✨ Google Gemini",
            horizontal=True,
            key="llm_provider",
        )
        if provider == "gemini":
            gemini_model = st.selectbox(
                "Gemini Model",
                ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp"],
                key="gemini_model",
            )
            gemini_api_key = st.text_input(
                "Google API Key",
                type="password",
                placeholder="AIza...",
                key="gemini_api_key",
            )
            model_name = gemini_model
            base_url = ""
            api_key = gemini_api_key or None
        else:
            model_name = st.text_input("Ollama Model", value="deepseek-r1:8b")
            base_url = st.text_input("Ollama Base URL", value="http://localhost:11434")
            api_key = None

    st.divider()
    st.caption("System Status")
    if demo_mode:
        st.success("Demo Mode")
    elif provider == "gemini":
        if api_key:
            st.success("Gemini: API key provided")
        else:
            st.warning("Gemini: API key required")
    else:
        try:
            import requests
            r = requests.get(f"{base_url}/api/tags", timeout=2)
            if r.status_code == 200:
                st.success("Ollama: Connected")
            else:
                st.error("Ollama: Not responding")
        except Exception:
            st.error("Ollama: Unreachable")

# ============================================================================
# MAIN TABS
# ============================================================================

# ============================================================================
# RESULT RENDERER (defined before tabs so all tabs can call it)
# ============================================================================

def _render_triage_result(result: Dict[str, Any]):
    """Render a TriageResult dict in the results panel."""
    esi = result.get("final_esi_level", 3)
    color = ESI_COLORS.get(esi, "#757575")
    label = ESI_LABELS.get(esi, "UNKNOWN")

    st.markdown(
        f'<div class="esi-badge" style="background:{color}">'
        f'ESI {esi} — {label}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(f"**📍 Assignment:** {result.get('patient_assignment', 'N/A')}")

    sepsis = result.get("sepsis_result") or {}
    if sepsis.get("sepsis_concern"):
        qscore = sepsis.get("qsofa_score", 0)
        active = [k.replace("_", " ") for k, v in sepsis.get("qsofa_components", {}).items() if v]
        st.markdown(
            f'<div class="alert-box alert-critical">⚠️ SEPSIS ALERT — '
            f'qSOFA {qscore}/3: {", ".join(active)}<br>'
            f'{sepsis.get("recommendation", "")}</div>',
            unsafe_allow_html=True,
        )

    pre_note = result.get("pre_arrival_note")
    if pre_note:
        st.markdown(
            f'<div class="alert-box alert-high">🚨 PRE-ARRIVAL: {pre_note}</div>',
            unsafe_allow_html=True,
        )

    det = result.get("deterioration") or {}
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("ESI Level", f"{esi} / 5",
              delta=f"orig {result.get('original_esi_level', esi)}" if result.get('original_esi_level') != esi else None,
              delta_color="inverse")
    m2.metric("Queue Position", f"#{result.get('queue_position', '—')}")
    m3.metric("Deterioration", det.get("risk_level", "—"))
    m4.metric("Reassess In", f"{det.get('recommended_reassessment_minutes', '—')} min")

    vqs = result.get("voice_quality_score", 0)
    um = result.get("urgency_modifier", 0)
    vc1, vc2 = st.columns(2)
    with vc1:
        st.caption("Voice Quality (10 = clear & calm)")
        st.progress(float(vqs) / 10.0, text=f"{vqs:.1f}/10")
    with vc2:
        st.caption("Urgency Modifier from Voice")
        norm = (float(um) + 1.0) / 2.0
        direction = "MORE urgent" if um < -0.1 else ("LESS urgent" if um > 0.1 else "Neutral")
        st.progress(norm, text=f"{um:+.2f} ({direction})")

    risk_score = float(det.get("risk_score", 0.0))
    risk_level = det.get("risk_level", "LOW")
    trajectory = det.get("predicted_trajectory", "STABLE")
    rcolor = RISK_COLORS.get(risk_level, "#757575")
    st.markdown(
        f'<div class="risk-bar-label">Deterioration Risk — '
        f'<b style="color:{rcolor}">{risk_level} — {trajectory}</b></div>',
        unsafe_allow_html=True,
    )
    st.progress(risk_score, text=f"{risk_score:.0%} in {det.get('time_window', '30-60 min')}")

    st.divider()

    symptoms = result.get("extracted_symptoms") or []
    if symptoms:
        st.markdown("**Extracted Symptoms:** " + " · ".join(f"`{s}`" for s in symptoms))
    if result.get("symptom_duration"):
        st.caption(f"Duration: {result['symptom_duration']}")
    if result.get("symptom_severity_self_reported"):
        st.caption(f"Self-reported severity: {result['symptom_severity_self_reported']}")

    adj = result.get("adjusted_esi_rationale", "")
    if adj and "no adjustment" not in adj.lower() and "insufficient" not in adj.lower():
        st.info(f"📚 Nurse Learning Adjustment: {adj}")

    st.caption(
        f"Priority score: {result.get('priority_score', 0):.1f} — "
        f"{result.get('priority_rationale', '')}"
    )
    st.divider()

    with st.expander("🩺 Clinical Reasoning & Safety Validation"):
        st.markdown(result.get("clinical_reasoning", "Not available"))
        sv = result.get("safety_validation", "")
        if sv:
            st.caption(f"Safety: {sv}")
        if result.get("physician_notification_required"):
            st.error("⚠️ Physician notification required")
        if result.get("escalation_required"):
            st.warning("⚠️ Escalation flagged")

    diag = result.get("diagnostics") or {}
    with st.expander("🔬 Diagnostics Plan"):
        dc1, dc2, dc3 = st.columns(3)
        with dc1:
            st.markdown("**Primary Differential**")
            for i, d in enumerate(diag.get("primary_differential", []), 1):
                st.markdown(f"{i}. {d}")
            st.markdown("**Must-Not-Miss**")
            for d in diag.get("secondary_differential", []):
                st.markdown(f"• {d}")
        with dc2:
            st.markdown("**Interventions**")
            for iv in diag.get("immediate_interventions", []):
                st.markdown(f"▶ {iv}")
            st.markdown("**Labs**")
            for lab in diag.get("labs_ordered", []):
                st.markdown(f"• {lab}")
        with dc3:
            st.markdown("**Imaging**")
            for img in diag.get("imaging", []):
                st.markdown(f"• {img}")
            st.markdown("**Monitoring**")
            for m in diag.get("monitoring", []):
                st.markdown(f"• {m}")
        if diag.get("clinical_rationale"):
            st.caption(diag["clinical_rationale"])

    with st.expander("📉 Deterioration Risk Factors"):
        for f in det.get("risk_factors", []):
            st.markdown(f"• {f}")
        components = det.get("score_components") or {}
        if components:
            comp_df = pd.DataFrame(
                [{"Component": k.replace("_", " ").title(), "Score": v}
                 for k, v in components.items()]
            )
            st.dataframe(comp_df, hide_index=True, use_container_width=True)

    specialist = result.get("specialist_assignment") or {}
    if specialist and specialist.get("primary_specialist"):
        urgency_colors = {
            "IMMEDIATE":    ("#ffebee", "#c62828"),
            "WITHIN_1H":    ("#fff3e0", "#e65100"),
            "WITHIN_4H":    ("#fffde7", "#f9a825"),
            "ROUTINE":      ("#e8f5e9", "#2e7d32"),
        }
        urgency = specialist.get("urgency_for_specialist", "WITHIN_1H")
        bg, border = urgency_colors.get(urgency, ("#f5f5f5", "#757575"))
        disposition_icon = {"ADMIT": "🏥", "OBSERVE": "👁️", "DISCHARGE": "🚪"}.get(
            specialist.get("estimated_disposition", ""), "📋"
        )
        with st.expander(
            f"👨‍⚕️ Specialist Assignment — {specialist.get('primary_specialist', '—')}",
            expanded=True,
        ):
            st.markdown(
                f"""<div style="background:{bg};border-left:4px solid {border};
                border-radius:6px;padding:10px 14px;margin-bottom:8px;">
                <b style="font-size:1.1em">{specialist.get("primary_specialist","—")}</b>
                &nbsp;·&nbsp;
                <span style="color:#555">{specialist.get("department","—")}</span>
                &nbsp;&nbsp;
                <span style="background:{border};color:white;padding:2px 8px;border-radius:12px;font-size:0.8em">
                {urgency.replace("_"," ")}
                </span>
                </div>""",
                unsafe_allow_html=True,
            )
            sc1, sc2 = st.columns(2)
            with sc1:
                st.markdown(f"**Clinical Reason:** {specialist.get('reason','—')}")
                if specialist.get("secondary_specialist"):
                    st.markdown(f"**Also consult:** {specialist['secondary_specialist']}")
            with sc2:
                st.markdown(
                    f"**Disposition:** {disposition_icon} {specialist.get('estimated_disposition','—')}"
                )
                st.markdown(
                    f"**Handoff Instructions:** {specialist.get('handoff_instructions','—')}"
                )
            if specialist.get("error"):
                st.caption(f"ℹ️ {specialist['error']}")

    img_data = result.get("image_analysis")
    if img_data:
        analyses_list = img_data.get("analyses") or []
        if analyses_list:
            with st.expander(f"📸 Image Analysis ({len(analyses_list)} image(s)) — {img_data.get('combined_severity','').upper()}"):
                for a in analyses_list:
                    sev = a.get("severity_assessment", "")
                    sev_color = {"minor": "green", "moderate": "orange", "severe": "red", "critical": "red"}.get(sev, "gray")
                    st.markdown(
                        f"**Image {a.get('image_index')}:** {a.get('injury_type')} — "
                        f":{sev_color}[{sev}] | Confidence: {a.get('confidence')} | Quality: {a.get('image_quality')}"
                    )
                    obs = a.get("clinical_observations") or []
                    if obs:
                        st.caption("Findings: " + "; ".join(obs[:4]))
                    flags = a.get("concerning_features") or []
                    if flags:
                        st.warning("⚠️ " + "; ".join(flags))
                    ivs = a.get("recommended_interventions") or []
                    if ivs:
                        st.caption("Interventions: " + "; ".join(ivs[:3]))
                    esi_imp = a.get("esi_impact", 0)
                    if esi_imp != 0:
                        st.caption(f"ESI impact: {esi_imp:+d} — {a.get('esi_impact_reason','')}")
                st.caption(
                    f"Combined ESI impact: {img_data.get('combined_esi_impact',0):+d} | "
                    f"Overall severity: {img_data.get('combined_severity','')}"
                )

    with st.expander("🔍 Raw JSON"):
        st.json(result)

    st.caption(
        f"⏱ Processed in {result.get('processing_time_seconds', 0):.1f}s  |  "
        f"{result.get('completed_at', '')[:19]}"
    )


# ============================================================================
# TABS
# ============================================================================

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🏥  Patient Intake",
    "📋  Live Queue Board",
    "👩‍⚕️  Nurse Override",
    "📊  Learning Analytics",
    "📄  Patient Report",
    "📈  Demand Forecast",
    "📅  Appointments",
])

# ============================================================================
# TAB 1 — PATIENT INTAKE
# ============================================================================

with tab1:
    col_form, col_result = st.columns([4, 6], gap="large")

    with col_form:
        st.subheader("New Patient Arrival")

        patient_ids = _get_patient_ids()
        patient_id = st.selectbox("Patient ID", patient_ids, index=0)

        # ── VOICE AUDIO INPUT ─────────────────────────────────────────────
        with st.expander("🎙️ Upload Voice Symptoms (optional)", expanded=False):
            st.caption("Upload an audio recording of the patient describing their symptoms. Supported: WAV, MP3, M4A, OGG, FLAC.")
            audio_file = st.file_uploader(
                "Select audio file",
                type=["wav", "mp3", "m4a", "ogg", "flac", "webm"],
                key="voice_audio_upload",
            )

            if audio_file is not None:
                st.audio(audio_file)
                va1, va2 = st.columns([1, 1])
                with va1:
                    whisper_model = st.selectbox(
                        "Whisper model",
                        ["tiny", "base", "small"],
                        index=1,
                        help="tiny=fastest, small=most accurate",
                    )
                with va2:
                    st.write("")
                    transcribe_btn = st.button("📝 Transcribe Audio", use_container_width=True)

                if transcribe_btn:
                    with st.spinner("Transcribing with Whisper..."):
                        try:
                            from voice_transcription_agent import transcribe_audio
                            audio_bytes = audio_file.read()
                            txn_result = transcribe_audio(
                                audio_bytes=audio_bytes,
                                filename=audio_file.name,
                                model_size=whisper_model,
                            )
                            if txn_result.error:
                                st.error(f"Transcription failed: {txn_result.error}")
                            else:
                                st.session_state["voice_transcript"] = txn_result.transcript
                                conf_color = {"HIGH": "green", "MEDIUM": "orange", "LOW": "red"}.get(
                                    txn_result.confidence, "gray"
                                )
                                st.success(
                                    f"Transcribed — Confidence: :{conf_color}[{txn_result.confidence}]"
                                    + (f" | {txn_result.duration_seconds:.1f}s" if txn_result.duration_seconds else "")
                                )
                                st.rerun()
                        except Exception as ex:
                            st.error(f"Transcription error: {ex}")

        voice_default = st.session_state.get("voice_transcript", "")
        transcript = st.text_area(
            "Symptom Transcript (patient's own words)",
            value=voice_default,
            placeholder=(
                "e.g. 'I've had crushing chest pain for about 30 minutes. "
                "It's going down my left arm. I'm sweating badly. "
                "Worst pain ever, maybe 9 out of 10.'"
            ),
            height=120,
        )

        # ── IMAGE UPLOAD ───────────────────────────────────────────────────
        with st.expander("📸 Upload Injury Photos (optional)", expanded=False):
            st.caption("Upload photographs of visible injuries (lacerations, burns, bruises, swelling, etc.).")
            uploaded_files = st.file_uploader(
                "Select injury images",
                type=["jpg", "jpeg", "png", "webp"],
                accept_multiple_files=True,
                key="injury_images",
            )

            if uploaded_files:
                img_cols = st.columns(min(len(uploaded_files), 4))
                for i, uf in enumerate(uploaded_files):
                    with img_cols[i % 4]:
                        st.image(uf, caption=uf.name, use_container_width=True)

                analyze_imgs_btn = st.button("🔬 Analyze Images", use_container_width=True)

                if analyze_imgs_btn:
                    with st.spinner("Analyzing images with Claude Vision..."):
                        try:
                            from image_analysis_agent import analyze_images
                            images_input = [(uf.read(), uf.name) for uf in uploaded_files]
                            # reset file pointers for re-read safety
                            for uf in uploaded_files:
                                uf.seek(0)
                            images_input = [(uf.read(), uf.name) for uf in uploaded_files]

                            img_result = analyze_images(
                                patient_id=patient_id,
                                images=images_input,
                                patient_context=transcript,
                            )
                            st.session_state["image_analysis"] = img_result
                            if img_result.error:
                                st.error(f"Image analysis error: {img_result.error}")
                            else:
                                st.success(
                                    f"Analyzed {img_result.num_images} image(s) — "
                                    f"Severity: **{img_result.combined_severity}** | "
                                    f"ESI impact: **{img_result.combined_esi_impact:+d}**"
                                )
                        except Exception as ex:
                            st.error(f"Image analysis error: {ex}")

            # Show prior analysis results if present
            img_analysis = st.session_state.get("image_analysis")
            if img_analysis and not img_analysis.error:
                st.divider()
                st.markdown(f"**Image Analysis — {img_analysis.combined_severity.upper()} severity**")
                for a in img_analysis.analyses:
                    sev_color = {"minor": "green", "moderate": "orange", "severe": "red", "critical": "red"}.get(
                        a.severity_assessment, "gray"
                    )
                    st.markdown(
                        f"**Image {a.image_index}:** {a.injury_type} — "
                        f":{sev_color}[{a.severity_assessment}] | "
                        f"Confidence: {a.confidence} | Quality: {a.image_quality}"
                    )
                    if a.clinical_observations:
                        st.caption("Findings: " + "; ".join(a.clinical_observations[:3]))
                    if a.concerning_features:
                        st.warning("⚠️ " + "; ".join(a.concerning_features))
                    if a.recommended_interventions:
                        st.caption("Interventions: " + "; ".join(a.recommended_interventions[:3]))
                    if a.esi_impact != 0:
                        st.caption(f"ESI impact: {a.esi_impact:+d} — {a.esi_impact_reason}")

        arrival_mode = st.radio(
            "Arrival Mode",
            ["walk_in", "911", "ambulance"],
            horizontal=True,
            format_func=lambda x: {"walk_in": "🚶 Walk-in", "911": "🚨 911 Call", "ambulance": "🚑 Ambulance"}[x],
        )

        with st.expander("Vital Signs", expanded=True):
            vc1, vc2 = st.columns(2)
            with vc1:
                hr = st.slider("Heart Rate (bpm)", 20, 220, 80)
                rr = st.slider("Respiratory Rate (/min)", 4, 50, 16)
                temp = st.slider("Temperature (°C)", 34.0, 42.0, 37.0, step=0.1)
            with vc2:
                spo2 = st.slider("SpO2 (%)", 60, 100, 98)
                bp = st.text_input("Blood Pressure", value="120/80", placeholder="120/80")
                consciousness = st.selectbox(
                    "Consciousness (AVPU)",
                    ["ALERT", "VOICE", "PAIN", "UNRESPONSIVE"],
                )

        run_btn = st.button("🚀 Run Triage", type="primary", use_container_width=True)

    # ── RESULTS PANEL ──────────────────────────────────────────────────────

    with col_result:
        if run_btn:
            if not transcript.strip():
                st.warning("Please enter a symptom transcript.")
                st.stop()

            vitals = {
                "heart_rate": hr,
                "respiratory_rate": rr,
                "temperature": temp,
                "oxygen_sat": spo2,
                "blood_pressure": bp,
                "consciousness": consciousness,
                "on_oxygen": False,
            }

            # Prepend image analysis injection text to transcript if available
            enriched_transcript = transcript
            img_analysis = st.session_state.get("image_analysis")
            if img_analysis and not img_analysis.error and img_analysis.symptoms_injection:
                enriched_transcript = img_analysis.symptoms_injection + transcript

            if demo_mode:
                result = dict(MOCK_RESULT)
                result["patient_id"] = patient_id
                if img_analysis and not img_analysis.error:
                    result["image_analysis"] = img_analysis.model_dump()
                st.session_state["last_result"] = result
            else:
                with st.spinner("Running triage pipeline... (30-60s with LLM)"):
                    try:
                        from triage_orchestrator import run_triage_pipeline
                        result = run_triage_pipeline(
                            patient_id=patient_id,
                            transcript=enriched_transcript,
                            vitals=vitals,
                            arrival_mode=arrival_mode,
                            model_name=model_name,
                            base_url=base_url,
                            provider=provider,
                            api_key=api_key,
                        )
                        st.session_state["last_result"] = result
                    except Exception as e:
                        st.error(f"Pipeline error: {e}")
                        st.stop()

        result = st.session_state.get("last_result")
        if not result:
            st.info("Fill in the form and click **Run Triage** to see results.")
        else:
            _render_triage_result(result)


# ============================================================================
# TAB 2 — LIVE QUEUE BOARD
# ============================================================================

with tab2:
    st.subheader("Live Patient Queue")

    if st.button("🔄 Refresh Queue", key="refresh_queue"):
        st.rerun()

    try:
        from queue_agent import get_current_queue, get_queue_summary

        queue = get_current_queue()
        summary = get_queue_summary()

        # Summary metrics
        qm1, qm2, qm3, qm4, qm5 = st.columns(5)
        qm1.metric("Total Patients", summary.total_patients)
        qm2.metric("🔴 Critical (ESI 1-2)", summary.critical_count)
        qm3.metric("🟠 High Risk", summary.high_risk_count)
        qm4.metric("Avg Wait", f"{summary.avg_wait_minutes:.0f} min")
        qm5.metric("Top Priority", summary.top_priority_patient or "—")

        st.divider()

        if not queue:
            st.info("Queue is empty. Run a triage to add patients.")
        else:
            rows = []
            for e in queue:
                esi_c = ESI_COLORS.get(e.esi_level, "#757575")
                rows.append({
                    "#": e.queue_position,
                    "Patient ID": e.patient_id,
                    "Name": e.patient_name,
                    "ESI": e.esi_level,
                    "Decision": e.triage_decision,
                    "Det. Risk": e.deterioration_level,
                    "Det. Score": f"{e.deterioration_risk:.0%}",
                    "Trajectory": e.predicted_trajectory,
                    "Wait (min)": f"{e.wait_minutes:.0f}",
                    "Priority": f"{e.priority_score:.1f}",
                    "Assignment": e.patient_assignment[:40],
                })

            df = pd.DataFrame(rows)

            def _color_esi(val):
                colors = {1: "#ffcdd2", 2: "#ffe0b2", 3: "#fff9c4", 4: "#bbdefb", 5: "#c8e6c9"}
                return f"background-color: {colors.get(int(val), 'white')}"

            styled = df.style.applymap(_color_esi, subset=["ESI"])
            st.dataframe(styled, hide_index=True, use_container_width=True)

            # Remove patient button
            st.divider()
            st.caption("Remove discharged / admitted patient")
            rc1, rc2 = st.columns([3, 1])
            with rc1:
                rem_id = st.selectbox("Patient to remove", [e.patient_id for e in queue], key="rem_sel")
            with rc2:
                st.write("")
                if st.button("Remove", key="remove_btn"):
                    from queue_agent import remove_patient
                    if remove_patient(rem_id):
                        st.success(f"{rem_id} removed from queue.")
                        st.rerun()

    except Exception as e:
        st.error(f"Queue error: {e}")

# ============================================================================
# TAB 3 — NURSE OVERRIDE
# ============================================================================

with tab3:
    st.subheader("Submit ESI Correction")
    st.caption(
        "Record a nurse override when the AI ESI level doesn't match clinical judgment. "
        "Corrections are stored and used to improve future ESI assignments."
    )

    with st.form("nurse_override_form"):
        nc1, nc2 = st.columns(2)
        with nc1:
            override_patient_id = st.text_input("Patient ID", placeholder="P00001")
            override_nurse_id = st.text_input("Nurse ID", placeholder="N001")
            ai_esi = st.number_input("AI Assigned ESI", min_value=1, max_value=5, value=3)
        with nc2:
            nurse_esi = st.number_input("Corrected ESI Level", min_value=1, max_value=5, value=2)
            override_reason = st.text_area("Reason for Override", height=80,
                                           placeholder="e.g. Patient appeared more distressed than AI scored")
            override_symptoms = st.text_input(
                "Symptoms (comma-separated)",
                placeholder="chest pain, diaphoresis, shortness of breath"
            )

        submitted = st.form_submit_button("✅ Submit Correction", use_container_width=True)

    if submitted:
        if not override_patient_id or not override_nurse_id:
            st.warning("Patient ID and Nurse ID are required.")
        else:
            try:
                from nurse_feedback_agent import submit_correction
                symptoms_list = [s.strip() for s in override_symptoms.split(",") if s.strip()]
                fb = submit_correction(
                    patient_id=override_patient_id,
                    ai_esi_level=int(ai_esi),
                    nurse_esi_level=int(nurse_esi),
                    symptoms=symptoms_list,
                    nurse_id=override_nurse_id,
                    reason=override_reason,
                )
                direction = nurse_esi - ai_esi
                if direction < 0:
                    st.success(f"✅ Correction submitted — upgraded urgency from ESI {ai_esi} → {nurse_esi}")
                elif direction > 0:
                    st.info(f"✅ Correction submitted — downgraded from ESI {ai_esi} → {nurse_esi}")
                else:
                    st.success("✅ Correction submitted (no ESI change recorded)")
                with st.expander("Correction Details"):
                    st.write(f"**Correction ID:** `{fb.correction_id}`")
                    st.write(fb.message)
            except Exception as e:
                st.error(f"Submission failed: {e}")

    st.divider()
    st.subheader("Recent Corrections")
    try:
        from nurse_feedback_agent import load_corrections
        corrections = load_corrections()
        if corrections:
            recent = sorted(corrections, key=lambda c: c.timestamp, reverse=True)[:10]
            corr_rows = [
                {
                    "Timestamp": c.timestamp[:16],
                    "Patient": c.patient_id,
                    "Nurse": c.nurse_id,
                    "AI ESI": c.ai_esi_level,
                    "Nurse ESI": c.nurse_esi_level,
                    "Delta": f"{c.correction_delta:+d}",
                    "Category": c.symptom_category,
                    "Reason": c.reason[:50],
                }
                for c in recent
            ]
            st.dataframe(pd.DataFrame(corr_rows), hide_index=True, use_container_width=True)
        else:
            st.info("No corrections recorded yet.")
    except Exception as e:
        st.error(f"Could not load corrections: {e}")

# ============================================================================
# TAB 4 — LEARNING ANALYTICS
# ============================================================================

with tab4:
    st.subheader("Nurse Correction Analytics")
    st.caption("How nurse corrections are shaping future AI triage decisions.")

    if st.button("🔄 Refresh Analytics", key="refresh_analytics"):
        st.rerun()

    try:
        from nurse_feedback_agent import get_correction_summary, load_corrections

        summary = get_correction_summary()

        if summary.total_corrections == 0:
            st.info("No nurse corrections recorded yet. Submit corrections in the 'Nurse Override' tab.")
        else:
            # Top metrics
            am1, am2, am3, am4 = st.columns(4)
            am1.metric("Total Corrections", summary.total_corrections)
            upgrades = sum(1 for c in load_corrections() if c.correction_delta < 0)
            downgrades = sum(1 for c in load_corrections() if c.correction_delta > 0)
            am2.metric("🔺 Urgency Upgrades", upgrades, help="Nurse assigned MORE urgent ESI than AI")
            am3.metric("🔻 Urgency Downgrades", downgrades, help="Nurse assigned LESS urgent ESI than AI")
            am4.metric("Overall Mean Delta", f"{summary.overall_mean_delta:+.2f}", help="Negative = AI typically under-triages")

            st.divider()
            ac1, ac2 = st.columns(2)

            with ac1:
                st.markdown("**Corrections by Category**")
                if summary.corrections_by_category:
                    cat_df = pd.DataFrame(
                        [{"Category": k, "Count": v}
                         for k, v in sorted(summary.corrections_by_category.items(), key=lambda x: -x[1])]
                    )
                    st.bar_chart(cat_df.set_index("Category"), use_container_width=True)

            with ac2:
                st.markdown("**Mean ESI Delta by Category**")
                st.caption("Negative = AI under-triages those cases (nurses upgrade urgency)")
                if summary.mean_delta_by_category:
                    delta_df = pd.DataFrame(
                        [{"Category": k, "Mean Delta": v}
                         for k, v in sorted(summary.mean_delta_by_category.items(), key=lambda x: x[1])]
                    )
                    st.bar_chart(delta_df.set_index("Category"), use_container_width=True)

            st.divider()
            col_info1, col_info2 = st.columns(2)
            with col_info1:
                if summary.most_upgraded_category:
                    st.warning(
                        f"📈 AI most often under-triages: **{summary.most_upgraded_category}** "
                        f"(mean delta {summary.mean_delta_by_category.get(summary.most_upgraded_category, 0):+.2f})"
                    )
            with col_info2:
                if summary.most_downgraded_category:
                    st.info(
                        f"📉 AI most often over-triages: **{summary.most_downgraded_category}** "
                        f"(mean delta {summary.mean_delta_by_category.get(summary.most_downgraded_category, 0):+.2f})"
                    )

            # Full corrections table
            with st.expander("View All Corrections"):
                corrections = load_corrections()
                all_rows = [
                    {
                        "Timestamp": c.timestamp[:16],
                        "Patient": c.patient_id,
                        "Nurse": c.nurse_id,
                        "AI ESI": c.ai_esi_level,
                        "Nurse ESI": c.nurse_esi_level,
                        "Delta": f"{c.correction_delta:+d}",
                        "Category": c.symptom_category,
                        "Symptoms": ", ".join(c.symptoms[:3]),
                        "Reason": c.reason[:60],
                    }
                    for c in sorted(corrections, key=lambda c: c.timestamp, reverse=True)
                ]
                st.dataframe(pd.DataFrame(all_rows), hide_index=True, use_container_width=True)

    except Exception as e:
        st.error(f"Analytics error: {e}")

# ============================================================================
# TAB 5 — PATIENT REPORT
# ============================================================================

def _build_appointment_pdf(appt_plan: Any, triage_result: Dict[str, Any]) -> bytes:
    """Build a patient-friendly appointment plan PDF using ReportLab."""
    import io as _io
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

    buf = _io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            leftMargin=0.75*inch, rightMargin=0.75*inch,
                            topMargin=0.75*inch, bottomMargin=0.75*inch,
                            title=f"Appointments — {appt_plan.patient_id}")

    base = getSampleStyleSheet()
    H1   = ParagraphStyle("H1",   parent=base["Heading1"], fontSize=17, textColor=colors.HexColor("#1a237e"), spaceAfter=4)
    H2   = ParagraphStyle("H2",   parent=base["Heading2"], fontSize=13, textColor=colors.HexColor("#1a237e"), spaceBefore=14, spaceAfter=4)
    BODY = ParagraphStyle("BODY", parent=base["Normal"],   fontSize=9,  leading=14)
    SMALL= ParagraphStyle("SMALL",parent=base["Normal"],   fontSize=8,  leading=12, textColor=colors.HexColor("#555"))
    BOLD = ParagraphStyle("BOLD", parent=base["Normal"],   fontSize=9,  leading=14, fontName="Helvetica-Bold")
    BULL = ParagraphStyle("BULL", parent=base["Normal"],   fontSize=9,  leading=14, leftIndent=14)
    WARN = ParagraphStyle("WARN", parent=base["Normal"],   fontSize=9,  leading=13,
                           backColor=colors.HexColor("#ffebee"), textColor=colors.HexColor("#b71c1c"),
                           borderPad=5, borderColor=colors.HexColor("#c62828"), borderWidth=1)

    URGENCY_COLORS = {
        "URGENT_24H":  ("#c62828", "#ffebee"),
        "SOON_1WK":    ("#e65100", "#fff3e0"),
        "ROUTINE_1MO": ("#f9a825", "#fffde7"),
        "ELECTIVE":    ("#2e7d32", "#e8f5e9"),
    }
    URGENCY_LABELS = {
        "URGENT_24H": "WITHIN 24 HOURS",
        "SOON_1WK":   "WITHIN 1 WEEK",
        "ROUTINE_1MO":"WITHIN 1 MONTH",
        "ELECTIVE":   "AT YOUR CONVENIENCE",
    }

    from datetime import datetime as _dt
    now = _dt.now().strftime("%B %d, %Y  %H:%M")

    story = []
    story.append(Paragraph("Follow-Up Appointment Plan", H1))
    story.append(Paragraph(
        f"Patient: {appt_plan.patient_id}  |  "
        f"ESI Level: {appt_plan.esi_level}  |  Generated: {now}", SMALL))
    story.append(Spacer(1, 8))

    # Summary box
    story.append(Paragraph(appt_plan.summary, ParagraphStyle(
        "SUM", parent=base["Normal"], fontSize=9, leading=14,
        backColor=colors.HexColor("#e3f2fd"), borderPad=8,
        borderColor=colors.HexColor("#1565c0"), borderWidth=1,
    )))
    story.append(Spacer(1, 10))

    # Counts table
    counts_tbl = Table([[
        Paragraph(f"<b>{appt_plan.urgent_count}</b><br/>Within 24 hrs", BODY),
        Paragraph(f"<b>{appt_plan.soon_count}</b><br/>Within 1 week", BODY),
        Paragraph(f"<b>{appt_plan.routine_count}</b><br/>Within 1 month", BODY),
        Paragraph(f"<b>{len(appt_plan.appointments)}</b><br/>Total", BODY),
    ]], colWidths=[1.5*inch]*4)
    counts_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(0,0), colors.HexColor("#ffebee")),
        ("BACKGROUND", (1,0),(1,0), colors.HexColor("#fff3e0")),
        ("BACKGROUND", (2,0),(2,0), colors.HexColor("#fffde7")),
        ("BACKGROUND", (3,0),(3,0), colors.HexColor("#e8f5e9")),
        ("ALIGN", (0,0),(-1,-1), "CENTER"),
        ("GRID", (0,0),(-1,-1), 0.4, colors.HexColor("#cccccc")),
        ("TOPPADDING", (0,0),(-1,-1), 8),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
    ]))
    story.append(counts_tbl)

    # Appointments
    story.append(Paragraph("Your Appointments", H2))
    current_tier = None
    for appt in appt_plan.appointments:
        border_c, bg_c = URGENCY_COLORS.get(appt.urgency, ("#9e9e9e", "#fafafa"))
        tier_label = URGENCY_LABELS.get(appt.urgency, appt.urgency)
        if appt.urgency != current_tier:
            current_tier = appt.urgency
            story.append(Spacer(1, 6))
            hdr = Table([[Paragraph(f"● {tier_label}", ParagraphStyle(
                "TH", fontSize=10, fontName="Helvetica-Bold",
                textColor=colors.HexColor(border_c)))]],
                colWidths=[6.5*inch])
            hdr.setStyle(TableStyle([
                ("BACKGROUND", (0,0),(-1,-1), colors.HexColor(bg_c)),
                ("TOPPADDING", (0,0),(-1,-1), 5),
                ("BOTTOMPADDING", (0,0),(-1,-1), 5),
                ("LEFTPADDING", (0,0),(-1,-1), 8),
            ]))
            story.append(hdr)

        rows = [
            [Paragraph("Appointment", SMALL), Paragraph(appt.appointment_type, BOLD)],
            [Paragraph("Specialty",    SMALL), Paragraph(appt.specialty, BODY)],
            [Paragraph("Why",          SMALL), Paragraph(appt.reason, BODY)],
            [Paragraph("How to book",  SMALL), Paragraph(appt.booking_hints, BODY)],
        ]
        if appt.prep_notes:
            rows.append([Paragraph("Preparation", SMALL),
                         Paragraph(" • ".join(appt.prep_notes), BODY)])

        tbl = Table(rows, colWidths=[1.1*inch, 5.4*inch])
        tbl.setStyle(TableStyle([
            ("FONTSIZE", (0,0),(-1,-1), 8),
            ("VALIGN",   (0,0),(-1,-1), "TOP"),
            ("TOPPADDING",(0,0),(-1,-1), 3),
            ("BOTTOMPADDING",(0,0),(-1,-1), 3),
            ("LEFTPADDING",(0,0),(-1,-1), 6),
            ("BACKGROUND",(0,0),(0,-1), colors.HexColor("#f5f5f5")),
            ("GRID",(0,0),(-1,-1), 0.3, colors.HexColor("#e0e0e0")),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 4))

    # Discharge instructions
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#bdbdbd"), spaceBefore=10))
    story.append(Paragraph("Before You Leave the ED", H2))
    for d in appt_plan.discharge_instructions:
        story.append(Paragraph(f"• {d}", BULL))

    # Red flags
    story.append(Paragraph("Return to the ED Immediately If:", H2))
    for r in appt_plan.red_flags:
        story.append(Paragraph(f"⚠ {r}", WARN))
        story.append(Spacer(1, 2))

    # Footer
    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#bdbdbd")))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"ED Triage AI — Clinical Decision Support  |  "
        f"AI-generated. All decisions must be made by a licensed healthcare provider.  |  {now}", SMALL))

    doc.build(story)
    buf.seek(0)
    return buf.read()


def _build_report_pdf(result: Dict[str, Any]) -> bytes:
    """Build a PDF patient report using ReportLab and return raw bytes."""
    import io as _io
    from datetime import datetime as _dt
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, KeepTogether,
    )
    from reportlab.lib.enums import TA_LEFT, TA_CENTER

    buf = _io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title=f"Triage Report — {result.get('patient_id','')}",
    )

    base = getSampleStyleSheet()
    H1 = ParagraphStyle("H1", parent=base["Heading1"], fontSize=16, textColor=colors.HexColor("#1a237e"), spaceAfter=4)
    H2 = ParagraphStyle("H2", parent=base["Heading2"], fontSize=12, textColor=colors.HexColor("#1a237e"), spaceBefore=14, spaceAfter=4)
    H3 = ParagraphStyle("H3", parent=base["Heading3"], fontSize=10, textColor=colors.HexColor("#333333"), spaceBefore=8, spaceAfter=2)
    BODY = ParagraphStyle("BODY", parent=base["Normal"], fontSize=9, leading=14)
    SMALL = ParagraphStyle("SMALL", parent=base["Normal"], fontSize=8, leading=12, textColor=colors.HexColor("#555555"))
    BULLET = ParagraphStyle("BULLET", parent=base["Normal"], fontSize=9, leading=14, leftIndent=14, bulletIndent=4)
    ALERT_RED = ParagraphStyle("ALERT_RED", parent=base["Normal"], fontSize=9, leading=13,
                                backColor=colors.HexColor("#ffebee"), textColor=colors.HexColor("#b71c1c"),
                                borderPad=6, borderColor=colors.HexColor("#c62828"), borderWidth=1, borderRadius=4)
    ALERT_ORG = ParagraphStyle("ALERT_ORG", parent=base["Normal"], fontSize=9, leading=13,
                                backColor=colors.HexColor("#fff3e0"), textColor=colors.HexColor("#bf360c"),
                                borderPad=6, borderColor=colors.HexColor("#e65100"), borderWidth=1, borderRadius=4)
    ITALIC = ParagraphStyle("ITALIC", parent=base["Normal"], fontSize=9, leading=13,
                             textColor=colors.HexColor("#444"), fontName="Helvetica-Oblique",
                             backColor=colors.HexColor("#f5f5f5"), borderPad=6, leftIndent=8)

    esi = result.get("final_esi_level", 3)
    esi_label = ESI_LABELS.get(esi, "UNKNOWN")
    esi_hex = ESI_COLORS.get(esi, "#757575")
    det = result.get("deterioration") or {}
    diag = result.get("diagnostics") or {}
    sepsis = result.get("sepsis_result") or {}
    img = result.get("image_analysis") or {}
    now = _dt.now().strftime("%B %d, %Y  %H:%M")

    def _tbl_style(header_color="#e8eaf6"):
        return TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_color)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1a237e")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ])

    def _kv_tbl(rows, col_widths=None):
        style = TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ])
        return Table([[Paragraph(str(k), SMALL), Paragraph(str(v), BODY)] for k, v in rows],
                     colWidths=col_widths or [1.5 * inch, 5.0 * inch], style=style)

    story = []

    # ── HEADER ────────────────────────────────────────────────────────────────
    story.append(Paragraph("Emergency Department — Patient Triage Report", H1))
    story.append(Paragraph(
        f"Generated: {now}  |  "
        f"Triage completed: {result.get('completed_at','')[:16].replace('T','  ')}  |  "
        f"Processing: {result.get('processing_time_seconds',0):.1f}s",
        SMALL,
    ))
    story.append(Spacer(1, 6))

    # Patient info table
    story.append(_kv_tbl([
        ("Patient ID", result.get("patient_id", "—")),
        ("Patient Name", result.get("patient_name", "—")),
        ("Arrival Mode", str(result.get("arrival_mode", "—")).replace("_", " ").title()),
        ("Queue Position", f"#{result.get('queue_position','—')}"),
    ]))
    story.append(Spacer(1, 10))

    # ESI Banner
    esi_tbl = Table(
        [[Paragraph(f"ESI {esi} — {esi_label}", ParagraphStyle(
            "ESI", fontSize=14, fontName="Helvetica-Bold", textColor=colors.white, alignment=TA_CENTER
        ))]],
        colWidths=[6.5 * inch],
    )
    esi_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(esi_hex)),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("ROUNDEDCORNERS", [6]),
    ]))
    story.append(esi_tbl)
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"<b>Patient Assignment:</b> {result.get('patient_assignment','—')}", BODY))

    adj = result.get("adjusted_esi_rationale", "")
    if adj and "no adjustment" not in adj.lower() and "insufficient" not in adj.lower():
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"Nurse Learning Adjustment: {adj}", ITALIC))

    # Alerts
    if sepsis.get("sepsis_concern"):
        active = [k.replace("_", " ") for k, v in sepsis.get("qsofa_components", {}).items() if v]
        story.append(Spacer(1, 6))
        story.append(Paragraph(
            f"SEPSIS ALERT — qSOFA {sepsis.get('qsofa_score',0)}/3  |  "
            f"Criteria: {', '.join(active) or 'N/A'}  |  {sepsis.get('recommendation','')}",
            ALERT_RED,
        ))

    pre_note = result.get("pre_arrival_note", "")
    if pre_note:
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"Pre-Arrival Note: {pre_note}", ALERT_ORG))

    # ── SYMPTOM SUMMARY ───────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#c5cae9"), spaceAfter=4, spaceBefore=10))
    story.append(Paragraph("Symptom Summary", H2))
    symptoms = result.get("extracted_symptoms") or []
    vqs = result.get("voice_quality_score")
    um = result.get("urgency_modifier", 0)
    sym_rows = [
        ("Extracted Symptoms", ", ".join(symptoms) if symptoms else "—"),
        ("Symptom Duration", result.get("symptom_duration", "—")),
        ("Self-Reported Severity", result.get("symptom_severity_self_reported", "—")),
        ("Original ESI", str(result.get("original_esi_level", "—"))),
        ("Final ESI (after learning)", str(esi)),
    ]
    if vqs is not None:
        direction = "More urgent" if um < -0.1 else ("Less urgent" if um > 0.1 else "Neutral")
        sym_rows += [
            ("Voice Quality Score", f"{vqs:.1f} / 10"),
            ("Urgency Modifier", f"{um:+.2f}  ({direction})"),
        ]
    story.append(_kv_tbl(sym_rows))

    # ── CLINICAL REASONING ────────────────────────────────────────────────────
    story.append(Paragraph("Clinical Reasoning", H2))
    story.append(Paragraph(result.get("clinical_reasoning", "Not available."), BODY))
    story.append(Spacer(1, 4))
    story.append(_kv_tbl([
        ("Safety Validation", result.get("safety_validation", "—")),
        ("Physician Notification", "Required" if result.get("physician_notification_required") else "Not required"),
        ("Escalation", "Flagged" if result.get("escalation_required") else "Not flagged"),
    ]))

    # ── DETERIORATION RISK ────────────────────────────────────────────────────
    story.append(Paragraph("Deterioration Risk Prediction (30–60 min)", H2))
    risk_level = det.get("risk_level", "—")
    risk_colors_map = {"LOW": "#2e7d32", "MEDIUM": "#e65100", "HIGH": "#c62828", "CRITICAL": "#b71c1c"}
    rc = risk_colors_map.get(risk_level, "#757575")
    risk_score = det.get("risk_score", 0)
    story.append(_kv_tbl([
        ("Risk Level", risk_level),
        ("Risk Score", f"{risk_score:.0%}"),
        ("Trajectory", str(det.get("predicted_trajectory", "—")).replace("_", " ")),
        ("Reassess In", f"{det.get('recommended_reassessment_minutes','—')} minutes"),
    ]))
    risk_factors = det.get("risk_factors") or []
    if risk_factors:
        story.append(Paragraph("Risk Factors:", H3))
        for f in risk_factors:
            story.append(Paragraph(f"• {f}", BULLET))

    # ── IMMEDIATE ACTIONS ─────────────────────────────────────────────────────
    interventions = diag.get("immediate_interventions") or []
    if interventions:
        story.append(Paragraph("Recommended Immediate Actions", H2))
        for iv in interventions:
            story.append(Paragraph(f"▶ {iv}", BULLET))

    # ── DIAGNOSTICS PLAN ──────────────────────────────────────────────────────
    story.append(Paragraph("Diagnostics Plan", H2))

    primary_diff = diag.get("primary_differential") or []
    secondary_diff = diag.get("secondary_differential") or []
    labs = diag.get("labs_ordered") or []
    imaging_list = diag.get("imaging") or []
    monitoring_list = diag.get("monitoring") or []

    if primary_diff:
        story.append(Paragraph("Primary Differential Diagnoses:", H3))
        for i, d in enumerate(primary_diff, 1):
            story.append(Paragraph(f"{i}. {d}", BULLET))

    if secondary_diff:
        story.append(Paragraph("Must-Not-Miss / Secondary Differentials:", H3))
        for d in secondary_diff:
            story.append(Paragraph(f"• {d}", BULLET))

    if labs:
        story.append(Paragraph("Labs Ordered:", H3))
        for lab in labs:
            story.append(Paragraph(f"• {lab}", BULLET))

    if imaging_list:
        story.append(Paragraph("Imaging:", H3))
        for im in imaging_list:
            story.append(Paragraph(f"• {im}", BULLET))

    if monitoring_list:
        story.append(Paragraph("Monitoring Plan:", H3))
        for m in monitoring_list:
            story.append(Paragraph(f"• {m}", BULLET))

    if diag.get("clinical_rationale"):
        story.append(Spacer(1, 4))
        story.append(Paragraph(diag["clinical_rationale"], ITALIC))

    # ── FUTURE DIAGNOSTIC CONSIDERATIONS ─────────────────────────────────────
    story.append(Paragraph("Future Diagnostic Considerations", H2))
    story.append(Paragraph(
        "Re-evaluate the following as initial results return. Update plan based on "
        "troponins, imaging reads, culture results, and response to treatment.",
        BODY,
    ))
    if primary_diff:
        story.append(Spacer(1, 4))
        story.append(Paragraph("Conditions to actively monitor:", H3))
        for d in primary_diff:
            story.append(Paragraph(f"• {d}", BULLET))
    if labs:
        story.append(Paragraph("Pending results to action:", H3))
        for lab in labs:
            story.append(Paragraph(f"• {lab}", BULLET))

    # ── IMAGE ANALYSIS ────────────────────────────────────────────────────────
    img_analyses = img.get("analyses") or []
    if img_analyses:
        story.append(Paragraph(
            f"Image Analysis — {img.get('combined_severity','').upper()} Severity  |  "
            f"ESI Impact: {img.get('combined_esi_impact',0):+d}",
            H2,
        ))
        img_data_rows = [[
            Paragraph("Image", SMALL), Paragraph("Injury Type", SMALL),
            Paragraph("Severity", SMALL), Paragraph("Findings", SMALL),
            Paragraph("Concerning Features", SMALL), Paragraph("ESI Δ", SMALL),
        ]]
        for a in img_analyses:
            img_data_rows.append([
                Paragraph(str(a.get("image_index", "")), BODY),
                Paragraph(a.get("injury_type", ""), BODY),
                Paragraph(a.get("severity_assessment", ""), BODY),
                Paragraph("; ".join(a.get("clinical_observations") or [])[:120], BODY),
                Paragraph("; ".join(a.get("concerning_features") or []) or "—", BODY),
                Paragraph(f"{a.get('esi_impact',0):+d}", BODY),
            ])
        img_tbl = Table(img_data_rows, colWidths=[0.5*inch, 1.2*inch, 0.8*inch, 1.8*inch, 1.5*inch, 0.5*inch])
        img_tbl.setStyle(_tbl_style())
        story.append(img_tbl)

    # ── FOOTER ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#bdbdbd")))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"ED Triage AI — Clinical Decision Support  |  "
        f"This report is AI-generated and is intended to assist clinical decision-making. "
        f"All final decisions must be made by a licensed healthcare provider.  |  "
        f"Patient: {result.get('patient_id','')}  |  {now}",
        SMALL,
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()


with tab5:
    st.subheader("Patient Triage Report")
    st.caption("A comprehensive summary of all triage data, ready to download or print.")

    result = st.session_state.get("last_result")

    if not result:
        st.info("Run a triage in the **Patient Intake** tab first — the report will appear here.")
    else:
        esi = result.get("final_esi_level", 3)
        esi_color = ESI_COLORS.get(esi, "#757575")
        esi_label = ESI_LABELS.get(esi, "")
        det = result.get("deterioration") or {}
        diag = result.get("diagnostics") or {}
        sepsis = result.get("sepsis_result") or {}
        img = result.get("image_analysis") or {}

        # ── REPORT PREVIEW ──────────────────────────────────────────────────

        st.markdown(
            f'<div class="esi-badge" style="background:{esi_color}">ESI {esi} — {esi_label}</div>',
            unsafe_allow_html=True,
        )

        # Patient & Triage Summary
        rc1, rc2 = st.columns(2)
        with rc1:
            st.markdown("#### Patient & Triage Summary")
            st.markdown(f"**Patient ID:** {result.get('patient_id','—')}")
            st.markdown(f"**Name:** {result.get('patient_name','—')}")
            st.markdown(f"**Arrival:** {result.get('arrival_mode','—').replace('_',' ').title()}")
            st.markdown(f"**Assignment:** {result.get('patient_assignment','—')}")
            if result.get("physician_notification_required"):
                st.error("⚠️ Physician notification required")
            if result.get("escalation_required"):
                st.warning("⚠️ Escalation flagged")

        with rc2:
            st.markdown("#### Symptom Summary")
            symptoms = result.get("extracted_symptoms") or []
            st.markdown("**Symptoms:** " + (", ".join(f"`{s}`" for s in symptoms) if symptoms else "—"))
            st.markdown(f"**Duration:** {result.get('symptom_duration','—')}")
            st.markdown(f"**Self-Reported Severity:** {result.get('symptom_severity_self_reported','—')}")
            vqs = result.get("voice_quality_score")
            um = result.get("urgency_modifier", 0)
            if vqs is not None:
                direction = "More urgent" if um < -0.1 else ("Less urgent" if um > 0.1 else "Neutral")
                st.markdown(f"**Voice Quality:** {vqs:.1f}/10 — modifier {um:+.2f} ({direction})")

        st.divider()

        # Clinical Reasoning
        st.markdown("#### Clinical Reasoning")
        st.markdown(result.get("clinical_reasoning", "Not available."))
        sv = result.get("safety_validation", "")
        if sv:
            st.caption(f"Safety validation: {sv}")

        # Sepsis
        if sepsis.get("sepsis_concern"):
            active = [k.replace("_", " ") for k, v in sepsis.get("qsofa_components", {}).items() if v]
            st.error(f"⚠️ SEPSIS ALERT — qSOFA {sepsis.get('qsofa_score',0)}/3: {', '.join(active)}")

        st.divider()

        # Diagnostics
        st.markdown("#### Diagnostics Plan")
        d1, d2, d3 = st.columns(3)
        with d1:
            st.markdown("**Primary Differential**")
            for i, d in enumerate(diag.get("primary_differential") or [], 1):
                st.markdown(f"{i}. {d}")
            st.markdown("**Must-Not-Miss**")
            for d in diag.get("secondary_differential") or []:
                st.markdown(f"• {d}")
        with d2:
            st.markdown("**Immediate Actions**")
            for iv in diag.get("immediate_interventions") or []:
                st.markdown(f"▶ {iv}")
            st.markdown("**Labs**")
            for lab in diag.get("labs_ordered") or []:
                st.markdown(f"• {lab}")
        with d3:
            st.markdown("**Imaging**")
            for im in diag.get("imaging") or []:
                st.markdown(f"• {im}")
            st.markdown("**Monitoring**")
            for m in diag.get("monitoring") or []:
                st.markdown(f"• {m}")

        if diag.get("clinical_rationale"):
            st.caption(diag["clinical_rationale"])

        st.divider()

        # Deterioration
        st.markdown("#### Deterioration Risk (30–60 min)")
        risk_level = det.get("risk_level", "LOW")
        rcolor = RISK_COLORS.get(risk_level, "#757575")
        rs = float(det.get("risk_score", 0))
        st.progress(rs, text=f"{rs:.0%} — {risk_level} — {det.get('predicted_trajectory','').replace('_',' ')}")
        st.caption(f"Reassess in {det.get('recommended_reassessment_minutes','—')} minutes")
        for f in (det.get("risk_factors") or []):
            st.markdown(f"• {f}")

        # Image Analysis
        img_analyses = img.get("analyses") or []
        if img_analyses:
            st.divider()
            st.markdown(f"#### Image Analysis — {img.get('combined_severity','').upper()} severity")
            for a in img_analyses:
                sev = a.get("severity_assessment", "")
                sc = {"minor": "green", "moderate": "orange", "severe": "red", "critical": "red"}.get(sev, "gray")
                st.markdown(
                    f"**Image {a.get('image_index')}:** {a.get('injury_type')} — "
                    f":{sc}[{sev}] | Confidence: {a.get('confidence')} | Quality: {a.get('image_quality')}"
                )
                obs = a.get("clinical_observations") or []
                if obs:
                    st.caption("Findings: " + "; ".join(obs))
                flags = a.get("concerning_features") or []
                if flags:
                    st.warning("⚠️ " + "; ".join(flags))
                ivs_list = a.get("recommended_interventions") or []
                if ivs_list:
                    st.caption("Interventions: " + "; ".join(ivs_list))

        st.divider()

        # Future Diagnostics
        st.markdown("#### Future Diagnostic Considerations")
        st.caption(
            "Conditions and workup to re-evaluate as initial results return. "
            "Update plan based on troponins, imaging, culture results, etc."
        )
        if diag.get("primary_differential"):
            st.markdown("**Watch for / Re-evaluate:**")
            for d in diag.get("primary_differential"):
                st.markdown(f"• {d}")
        if diag.get("labs_ordered"):
            st.markdown("**Pending results to action:**")
            for lab in diag.get("labs_ordered"):
                st.markdown(f"• {lab}")

        adj = result.get("adjusted_esi_rationale", "")
        if adj and "no adjustment" not in adj.lower() and "insufficient" not in adj.lower():
            st.info(f"📚 Nurse Learning Adjustment: {adj}")

        # ── DOWNLOAD BUTTON ──────────────────────────────────────────────────
        st.divider()
        st.markdown("#### Download Report")

        try:
            with st.spinner("Generating PDF..."):
                pdf_bytes = _build_report_pdf(result)
            st.download_button(
                label="⬇️ Download Patient Report (PDF)",
                data=pdf_bytes,
                file_name=f"triage_report_{result.get('patient_id','patient')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
                use_container_width=True,
                type="primary",
            )
        except Exception as pdf_err:
            st.error(f"PDF generation failed: {pdf_err}")

# ============================================================================
# TAB 6 — DEMAND FORECASTING
# ============================================================================

with tab6:
    st.subheader("ED Demand Forecasting")
    st.caption(
        "ML-powered patient arrival forecasts using **Facebook Prophet**. "
        "Captures hourly, weekly, and seasonal patterns from historical encounter data."
    )

    # ── CONTROLS ─────────────────────────────────────────────────────────────
    fc1, fc2, fc3 = st.columns([2, 2, 2])
    with fc1:
        granularity = st.selectbox(
            "Forecast Granularity",
            ["daily", "hourly", "weekly"],
            format_func=lambda x: {
                "hourly": "⏱ Hourly — Next 48 hours",
                "daily":  "📅 Daily — Next 30 days",
                "weekly": "🗓 Weekly — Next 12 weeks",
            }[x],
        )
    with fc2:
        run_cv = st.toggle(
            "Run Cross-Validation",
            value=False,
            help="Computes MAE/RMSE/MAPE via time-series CV folds. Adds ~30s.",
        )
    with fc3:
        st.write("")
        run_forecast_btn = st.button("🔮 Run Forecast", type="primary", use_container_width=True)

    st.divider()

    # ── CACHED FORECAST ───────────────────────────────────────────────────────
    cache_key = f"forecast_{granularity}"

    if run_forecast_btn:
        with st.spinner(f"Fitting Prophet model on historical encounter data ({granularity})…"):
            try:
                from demand_forecasting_agent import run_demand_forecast
                fc_result = run_demand_forecast(granularity=granularity, run_cv=run_cv)
                st.session_state[cache_key] = fc_result
            except Exception as fe:
                st.error(f"Forecasting error: {fe}")

    fc_result = st.session_state.get(cache_key)

    if not fc_result:
        st.info("Select a granularity and click **Run Forecast** to generate predictions.")
    elif fc_result.error:
        st.error(f"Forecast failed: {fc_result.error}")
    else:
        # ── SUMMARY METRICS ──────────────────────────────────────────────────
        sm1, sm2, sm3, sm4, sm5 = st.columns(5)
        fp_df = pd.DataFrame([p.model_dump() for p in fc_result.forecast_points])
        fp_df["ds"] = pd.to_datetime(fp_df["ds"])

        total_pred = fp_df["yhat"].sum()
        avg_pred   = fp_df["yhat"].mean()
        peak_pred  = fp_df["yhat"].max()
        peak_time  = str(fp_df.loc[fp_df["yhat"].idxmax(), "ds"])[:16]

        sm1.metric("Horizon", fc_result.horizon_label)
        sm2.metric("Total Predicted Arrivals", f"{total_pred:.0f}")
        sm3.metric("Avg per Period", f"{avg_pred:.1f}")
        sm4.metric("Peak Predicted", f"{peak_pred:.1f}", help=f"at {peak_time}")
        sm5.metric("Baseline Daily Avg", f"{fc_result.baseline_daily_avg:.1f}")

        model_m = fc_result.model_metrics
        if model_m.get("mae") or model_m.get("mae_train"):
            mae_val = model_m.get("mae") or model_m.get("mae_train")
            st.caption(
                f"Model metrics — MAE: {mae_val:.2f}"
                + (f" | RMSE: {model_m['rmse']:.2f}" if model_m.get("rmse") else "")
                + (f" | MAPE: {model_m['mape']:.1%}" if model_m.get("mape") else "")
                + (f" | trained on {model_m.get('n_train','?')} periods" if model_m.get("n_train") else "")
            )

        st.divider()

        # ── FORECAST CHART ────────────────────────────────────────────────────
        st.markdown("#### Arrival Volume Forecast with Confidence Interval")

        chart_df = fp_df[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
        chart_df = chart_df.set_index("ds")

        # Streamlit line_chart with multiple series for CI shading
        st.line_chart(
            chart_df.rename(columns={
                "yhat": "Predicted",
                "yhat_lower": "Lower 80% CI",
                "yhat_upper": "Upper 80% CI",
            }),
            use_container_width=True,
            height=320,
            color=["#1565c0", "#90caf9", "#90caf9"],
        )

        st.divider()

        # ── TREND & SEASONALITY ───────────────────────────────────────────────
        trend_cols = [c for c in ["trend", "weekly", "daily", "yearly"] if c in fp_df.columns and fp_df[c].notna().any()]
        if len(trend_cols) > 1:
            st.markdown("#### Decomposition — Trend & Seasonality Components")
            comp_df = fp_df[["ds"] + trend_cols].set_index("ds")
            st.line_chart(comp_df, use_container_width=True, height=220)
            st.divider()

        # ── INSIGHTS ─────────────────────────────────────────────────────────
        if fc_result.insights:
            st.markdown("#### 🔍 Model Insights")
            for ins in fc_result.insights:
                st.markdown(f"• {ins}")
            st.divider()

        # ── PEAK / SURGE WINDOWS ──────────────────────────────────────────────
        if fc_result.peak_windows:
            st.markdown("#### ⚡ Predicted Surge Windows")
            peak_rows = []
            for p in fc_result.peak_windows:
                sev_emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🟠", "CRITICAL": "🔴"}.get(p.severity, "⚪")
                peak_rows.append({
                    "Severity": f"{sev_emoji} {p.severity}",
                    "Start": p.start,
                    "End": p.end,
                    "Avg Arrivals": p.predicted_arrivals,
                    "Recommendation": p.recommendation,
                })
            peak_df = pd.DataFrame(peak_rows)

            def _color_sev(val):
                c = {"🔴 CRITICAL": "#ffcdd2", "🟠 HIGH": "#ffe0b2",
                     "🟡 MEDIUM": "#fff9c4", "🟢 LOW": "#c8e6c9"}
                return f"background-color: {c.get(val, 'white')}"

            st.dataframe(
                peak_df.style.applymap(_color_sev, subset=["Severity"]),
                hide_index=True,
                use_container_width=True,
            )
            st.divider()
        else:
            st.success("✅ No significant surge windows predicted in this forecast horizon.")

        # ── STAFFING RECOMMENDATIONS ──────────────────────────────────────────
        st.markdown("#### 👩‍⚕️ Staffing Recommendations")
        if fc_result.staffing_recommendations:
            stf_rows = []
            for s in fc_result.staffing_recommendations:
                load_emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🟠", "CRITICAL": "🔴"}
                load_key = next((k for k in load_emoji if k in s.notes.upper()), "")
                stf_rows.append({
                    "Period": s.period,
                    "Predicted Arrivals": s.predicted_volume,
                    "Nurses": s.recommended_nurses,
                    "Physicians": s.recommended_physicians,
                    "Beds": s.recommended_beds,
                    "Load": f"{load_emoji.get(load_key,'⚪')} {load_key or s.notes}",
                })
            st.dataframe(pd.DataFrame(stf_rows), hide_index=True, use_container_width=True)

        st.divider()

        # ── FULL FORECAST TABLE ───────────────────────────────────────────────
        with st.expander("📋 Full Forecast Table"):
            display_fp = fp_df[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
            display_fp.columns = ["Date/Time", "Predicted", "Lower CI", "Upper CI"]
            display_fp["Date/Time"] = display_fp["Date/Time"].astype(str).str[:16]
            for c in ["Predicted", "Lower CI", "Upper CI"]:
                display_fp[c] = display_fp[c].round(1)
            st.dataframe(display_fp, hide_index=True, use_container_width=True)

            # Download forecast CSV
            csv_data = display_fp.to_csv(index=False)
            st.download_button(
                label="⬇️ Download Forecast CSV",
                data=csv_data,
                file_name=f"ed_forecast_{granularity}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
            )

        # ── HISTORICAL VOLUME ─────────────────────────────────────────────────
        with st.expander("📊 Historical Arrival Volume (training data)"):
            try:
                from demand_forecasting_agent import _load_encounter_series, _aggregate_for_granularity
                raw = _load_encounter_series()
                hist_df = _aggregate_for_granularity(raw, granularity)
                hist_df = hist_df.tail(180).set_index("ds")
                st.line_chart(hist_df.rename(columns={"y": "Actual Arrivals"}),
                              use_container_width=True, height=200,
                              color=["#2e7d32"])
            except Exception as he:
                st.warning(f"Could not load historical chart: {he}")

# ============================================================================
# TAB 7 — APPOINTMENT RECOMMENDATIONS
# ============================================================================

with tab7:
    st.subheader("Follow-Up Appointment Plan")
    st.caption(
        "Automatically generated from the Diagnostics Agent output. "
        "Shows every appointment the patient needs to book after their ED visit, "
        "ranked by urgency, with booking instructions and red-flag warnings."
    )

    result = st.session_state.get("last_result")

    if not result:
        st.info("Run a triage in the **Patient Intake** tab first — appointments will appear here.")
    else:
        diag = result.get("diagnostics") or {}
        esi  = result.get("final_esi_level", 3)

        # Generate plan
        try:
            from appointment_agent import generate_appointment_plan
            appt_plan = generate_appointment_plan(
                patient_id=result.get("patient_id", "—"),
                diagnostics=diag,
                esi_level=esi,
                triage_decision=result.get("triage_decision", ""),
                patient_name=result.get("patient_name", ""),
            )
            st.session_state["appt_plan"] = appt_plan
        except Exception as ae:
            st.error(f"Could not generate appointment plan: {ae}")
            st.stop()

        appt_plan = st.session_state.get("appt_plan")
        if not appt_plan:
            st.stop()

        # ── SUMMARY BANNER ────────────────────────────────────────────────────
        esi_color = ESI_COLORS.get(esi, "#757575")
        ac1, ac2, ac3, ac4, ac5 = st.columns(5)
        ac1.metric("Patient", result.get("patient_id", "—"))
        ac2.metric("Total Appointments", len(appt_plan.appointments))

        urgent_color  = "🔴" if appt_plan.urgent_count  > 0 else "✅"
        soon_color    = "🟠" if appt_plan.soon_count    > 0 else "✅"
        routine_color = "🟢" if appt_plan.routine_count > 0 else "✅"

        ac3.metric(f"{urgent_color} Within 24 hrs",  appt_plan.urgent_count)
        ac4.metric(f"{soon_color} Within 1 week",    appt_plan.soon_count)
        ac5.metric(f"{routine_color} Within 1 month", appt_plan.routine_count)

        # ── PATIENT SUMMARY ───────────────────────────────────────────────────
        st.divider()
        if appt_plan.urgent_count > 0:
            st.error(
                f"⚠️ **ACTION REQUIRED:** You have **{appt_plan.urgent_count} appointment(s)** "
                f"that must be booked within **24 hours**."
            )
        st.markdown(f"**📋 Your appointment plan:** {appt_plan.summary}")

        # ── APPOINTMENT CARDS ─────────────────────────────────────────────────
        st.divider()
        URGENCY_CONFIG = {
            "URGENT_24H":  ("🔴", "#ffebee", "#c62828", "Within 24 hours"),
            "SOON_1WK":    ("🟠", "#fff3e0", "#e65100", "Within 1 week"),
            "ROUTINE_1MO": ("🟡", "#fffde7", "#f9a825", "Within 1 month"),
            "ELECTIVE":    ("🟢", "#e8f5e9", "#2e7d32", "At your convenience"),
        }

        current_urgency = None
        for appt in appt_plan.appointments:
            icon, bg, border, label = URGENCY_CONFIG.get(
                appt.urgency, ("⚪", "#fafafa", "#9e9e9e", appt.urgency)
            )

            # Section header when urgency tier changes
            if appt.urgency != current_urgency:
                current_urgency = appt.urgency
                st.markdown(f"### {icon} {label}")

            with st.container():
                st.markdown(
                    f"""<div style="background:{bg};border-left:4px solid {border};
                    border-radius:6px;padding:12px 16px;margin:6px 0;">
                    <b style="font-size:1.05em">{appt.appointment_type}</b>
                    &nbsp;&nbsp;<span style="color:#666;font-size:0.85em">{appt.specialty}</span>
                    </div>""",
                    unsafe_allow_html=True,
                )
                exp_cols = st.columns([3, 2])
                with exp_cols[0]:
                    st.markdown(f"**Why:** {appt.reason}")
                    if appt.triggered_by:
                        st.caption(f"Triggered by: {appt.triggered_by}")
                with exp_cols[1]:
                    st.markdown(f"**How to book:** {appt.booking_hints}")
                    if appt.prep_notes:
                        with st.expander("Preparation notes"):
                            for note in appt.prep_notes:
                                st.markdown(f"• {note}")
                st.markdown("---")

        # ── DISCHARGE INSTRUCTIONS ────────────────────────────────────────────
        st.divider()
        st.markdown("### 📋 Before You Leave the ED")
        for instruction in appt_plan.discharge_instructions:
            st.markdown(f"• {instruction}")

        # ── RED FLAGS ─────────────────────────────────────────────────────────
        st.divider()
        st.markdown("### 🚨 Return to the ED Immediately If:")
        rf_cols = st.columns(2)
        for i, flag in enumerate(appt_plan.red_flags):
            with rf_cols[i % 2]:
                st.markdown(
                    f'<div class="alert-box alert-critical" style="margin:3px 0;font-size:0.88em;">⚠ {flag}</div>',
                    unsafe_allow_html=True,
                )

        # ── DOWNLOAD ──────────────────────────────────────────────────────────
        st.divider()
        st.markdown("### ⬇️ Download Appointment Plan")

        # Build plain-text version
        lines = [
            f"FOLLOW-UP APPOINTMENT PLAN",
            f"Patient: {appt_plan.patient_id}  |  Generated: {appt_plan.generated_at[:16]}",
            f"ESI Level: {esi}",
            "=" * 60,
            "",
            "SUMMARY",
            "-" * 40,
            appt_plan.summary,
            "",
            "APPOINTMENTS",
            "-" * 40,
        ]
        for appt in appt_plan.appointments:
            lines += [
                f"",
                f"[{appt.urgency}]  {appt.appointment_type}",
                f"Specialty : {appt.specialty}",
                f"Timeframe : {appt.timeframe}",
                f"Why       : {appt.reason}",
                f"How to book: {appt.booking_hints}",
            ]
            if appt.prep_notes:
                lines.append("Preparation:")
                for n in appt.prep_notes:
                    lines.append(f"  • {n}")

        lines += [
            "",
            "BEFORE YOU LEAVE",
            "-" * 40,
        ] + [f"• {d}" for d in appt_plan.discharge_instructions] + [
            "",
            "RETURN TO ED IF:",
            "-" * 40,
        ] + [f"⚠ {r}" for r in appt_plan.red_flags] + [
            "",
            "-" * 60,
            "AI-generated clinical decision support.",
            "All final decisions must be made by a licensed healthcare provider.",
        ]

        dl1, dl2 = st.columns(2)
        with dl1:
            st.download_button(
                label="⬇️ Download as PDF",
                data=_build_appointment_pdf(appt_plan, result),
                file_name=f"appointments_{appt_plan.patient_id}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
                use_container_width=True,
                type="primary",
            )
        with dl2:
            st.download_button(
                label="⬇️ Download as Text",
                data="\n".join(lines).encode("utf-8"),
                file_name=f"appointments_{appt_plan.patient_id}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                mime="text/plain",
                use_container_width=True,
            )
