"""
SOAP Note Fallback Generator
=============================
Keyword-based fallback that produces a complete SOAP note + ICD-10/CPT codes
when the LLM fails to return structured output.

Triggered only when `soap_note` is None OR `icd10_codes` is empty after the
LLM diagnostic run.

Usage:
    from soap_fallback import build_fallback_soap
    soap, icd10, cpt = build_fallback_soap(symptoms, patient_age, active_conditions, vitals)
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple


# ── Keyword → condition template mapping ─────────────────────────────────────
# Each entry: list of trigger keywords, and the template to use

CONDITION_TEMPLATES: List[Dict[str, Any]] = [
    {
        "keywords": ["chest pain", "chest pressure", "chest tightness", "heart", "cardiac",
                     "crushing", "radiating arm", "left arm", "jaw pain", "diaphoresis"],
        "condition": "CHEST_PAIN_ACS",
    },
    {
        "keywords": ["shortness of breath", "difficulty breathing", "breathless", "dyspnea",
                     "can't breathe", "wheezing", "respiratory", "oxygen", "spo2"],
        "condition": "RESPIRATORY_DISTRESS",
    },
    {
        "keywords": ["stroke", "facial droop", "arm weakness", "speech", "slurred",
                     "sudden numbness", "vision loss", "worst headache", "thunderclap",
                     "paralysis", "altered mental"],
        "condition": "NEUROLOGICAL_EMERGENCY",
    },
    {
        "keywords": ["abdominal pain", "belly pain", "stomach pain", "nausea", "vomiting",
                     "diarrhea", "appendix", "bowel", "bloating", "cramping"],
        "condition": "ABDOMINAL_PAIN",
    },
    {
        "keywords": ["fever", "sepsis", "infection", "chills", "rigors", "blood culture",
                     "high temperature", "hypothermia", "bacteremia"],
        "condition": "SEPSIS_FEVER",
    },
    {
        "keywords": ["trauma", "fall", "accident", "fracture", "broken", "injury",
                     "head injury", "laceration", "bleeding", "wound"],
        "condition": "TRAUMA",
    },
    {
        "keywords": ["diabetic", "diabetes", "blood sugar", "hypoglycemia", "hyperglycemia",
                     "dka", "ketoacidosis", "glucose"],
        "condition": "DIABETIC_EMERGENCY",
    },
    {
        "keywords": ["anxiety", "panic", "palpitations", "heart racing", "tachycardia",
                     "fast heart"],
        "condition": "CARDIAC_ARRHYTHMIA",
    },
    {
        "keywords": ["urinary", "uti", "dysuria", "frequency", "burning urination",
                     "kidney", "flank pain", "back pain"],
        "condition": "URINARY_RENAL",
    },
    {
        "keywords": ["headache", "migraine", "head pain", "photophobia", "nausea headache"],
        "condition": "HEADACHE",
    },
]

# ── Per-condition SOAP + ICD-10 + CPT templates ───────────────────────────────

_TEMPLATES: Dict[str, Dict[str, Any]] = {

    "CHEST_PAIN_ACS": {
        "soap": {
            "subjective": (
                "{age}-year-old {gender} presenting with chest pain described as crushing/pressure-like, "
                "onset {duration}. Patient reports {pain_level}/10 pain severity, radiating to the left arm and jaw. "
                "Associated symptoms include diaphoresis and shortness of breath. "
                "Active medical history significant for: {conditions}."
            ),
            "objective": (
                "Vitals: HR {hr} bpm, BP {bp} mmHg, RR {rr}/min, Temp {temp}°C, SpO₂ {spo2}%. "
                "Patient appears diaphoretic and in moderate-to-severe distress. "
                "Cardiac exam: regular rate and rhythm, no murmurs on auscultation. "
                "Lungs: clear to auscultation bilaterally. Skin: pale and diaphoretic."
            ),
            "assessment": (
                "Working diagnosis: Acute Coronary Syndrome (ACS) — Rule out STEMI/NSTEMI. "
                "Differential: (1) ST-Elevation Myocardial Infarction (STEMI), "
                "(2) Non-ST-Elevation Myocardial Infarction (NSTEMI), "
                "(3) Unstable Angina, (4) Aortic Dissection, (5) Pulmonary Embolism. "
                "High-risk presentation given age, symptom quality, and associated conditions ({conditions})."
            ),
            "plan": (
                "1. 12-lead ECG within 10 minutes — STAT. "
                "2. IV access x2, cardiac monitor, supplemental O₂. "
                "3. Labs: Troponin I/T (serial), BMP, CBC, PT/INR, BNP, D-dimer. "
                "4. CXR portable. "
                "5. Aspirin 325mg PO if no contraindication. "
                "6. Cardiology consult STAT if ECG shows ischemic changes. "
                "7. NPO in anticipation of possible PCI. "
                "8. Serial troponins q3h x2."
            ),
        },
        "icd10": [
            {"code": "I21.9",  "description": "Acute myocardial infarction, unspecified",      "type": "primary"},
            {"code": "I20.0",  "description": "Unstable angina",                                "type": "secondary"},
            {"code": "I71.00", "description": "Aortic dissection, unspecified",                 "type": "secondary"},
            {"code": "I26.99", "description": "Other pulmonary embolism without acute cor pulmonale", "type": "secondary"},
        ],
        "cpt": [
            {"code": "99285", "description": "ED visit, high medical decision making",           "category": "evaluation"},
            {"code": "93000", "description": "Electrocardiogram, routine ECG 12-lead",          "category": "procedure"},
            {"code": "84484", "description": "Troponin I, quantitative",                        "category": "lab"},
            {"code": "80053", "description": "Comprehensive metabolic panel",                    "category": "lab"},
            {"code": "85025", "description": "Complete blood count (CBC) with differential",     "category": "lab"},
            {"code": "71046", "description": "Chest X-ray, 2 views",                            "category": "imaging"},
            {"code": "74177", "description": "CT chest with contrast",                          "category": "imaging"},
        ],
    },

    "RESPIRATORY_DISTRESS": {
        "soap": {
            "subjective": (
                "{age}-year-old {gender} presenting with shortness of breath and difficulty breathing, "
                "onset {duration}. Patient rates distress as {pain_level}/10. "
                "Reports wheezing and inability to complete full sentences. "
                "Active medical history: {conditions}."
            ),
            "objective": (
                "Vitals: HR {hr} bpm, BP {bp} mmHg, RR {rr}/min, Temp {temp}°C, SpO₂ {spo2}%. "
                "Patient appears in moderate-to-severe respiratory distress, using accessory muscles. "
                "Lung exam: diffuse expiratory wheezes bilaterally. No crepitations. "
                "No JVD. Extremities: no peripheral edema."
            ),
            "assessment": (
                "Working diagnosis: Acute respiratory compromise — likely exacerbation. "
                "Differential: (1) Acute asthma exacerbation / COPD exacerbation, "
                "(2) Congestive heart failure (CHF) with pulmonary edema, "
                "(3) Pulmonary Embolism, (4) Pneumothorax, (5) Community-acquired pneumonia. "
                "SpO₂ of {spo2}% and RR of {rr} indicate significant respiratory compromise."
            ),
            "plan": (
                "1. High-flow O₂ via non-rebreather mask — target SpO₂ ≥94%. "
                "2. Nebulized albuterol 2.5mg + ipratropium 0.5mg STAT. "
                "3. IV access, cardiac monitor. "
                "4. Labs: ABG, BMP, CBC, BNP, D-dimer, procalcitonin. "
                "5. CXR portable STAT. "
                "6. Solumedrol 125mg IV if bronchospasm. "
                "7. CT pulmonary angiography if PE suspected (D-dimer elevated). "
                "8. Pulmonology or critical care consult if no improvement in 30 min."
            ),
        },
        "icd10": [
            {"code": "J45.901", "description": "Unspecified asthma with acute exacerbation",    "type": "primary"},
            {"code": "J44.1",   "description": "COPD with acute exacerbation",                  "type": "secondary"},
            {"code": "I50.9",   "description": "Heart failure, unspecified",                    "type": "secondary"},
            {"code": "I26.99",  "description": "Pulmonary embolism without acute cor pulmonale","type": "secondary"},
        ],
        "cpt": [
            {"code": "99285", "description": "ED visit, high medical decision making",           "category": "evaluation"},
            {"code": "94640", "description": "Pressurized or nonpressurized inhalation treatment","category": "procedure"},
            {"code": "82803", "description": "Blood gases (ABG), any combination",              "category": "lab"},
            {"code": "83880", "description": "Natriuretic peptide (BNP)",                       "category": "lab"},
            {"code": "86850", "description": "D-dimer",                                         "category": "lab"},
            {"code": "71046", "description": "Chest X-ray, 2 views",                            "category": "imaging"},
            {"code": "71275", "description": "CT pulmonary angiography with contrast",          "category": "imaging"},
        ],
    },

    "NEUROLOGICAL_EMERGENCY": {
        "soap": {
            "subjective": (
                "{age}-year-old {gender} presenting with sudden-onset neurological symptoms, "
                "onset {duration}. Patient or family reports facial drooping, arm weakness, "
                "and speech difficulty (FAST positive). Symptom severity {pain_level}/10. "
                "Active medical history: {conditions}."
            ),
            "objective": (
                "Vitals: HR {hr} bpm, BP {bp} mmHg, RR {rr}/min, Temp {temp}°C, SpO₂ {spo2}%. "
                "Neuro exam: GCS assessed, FAST screen positive. Pupils equal and reactive. "
                "Facial asymmetry noted. Unilateral arm drift present. Speech dysarthric. "
                "No meningism. Kernig/Brudzinski negative."
            ),
            "assessment": (
                "Working diagnosis: Acute ischemic stroke — time-sensitive intervention window. "
                "Differential: (1) Ischemic stroke (thrombotic or embolic), "
                "(2) Hemorrhagic stroke (ICH or SAH), "
                "(3) TIA, (4) Todd's paralysis post-seizure, (5) Hypoglycemia mimicking stroke. "
                "Last known well documented — tPA eligibility window must be assessed urgently."
            ),
            "plan": (
                "1. Activate stroke alert / code stroke protocol IMMEDIATELY. "
                "2. Non-contrast CT head STAT (rule out hemorrhage before tPA). "
                "3. Labs: glucose fingerstick STAT, CBC, BMP, PT/INR/aPTT, type & screen. "
                "4. 12-lead ECG (rule out AF as cardioembolic source). "
                "5. IV access x2, keep NPO. "
                "6. Neurology consult STAT — tPA decision if ischemic and within window. "
                "7. MRI brain with DWI if CT negative and suspicion high. "
                "8. Continuous cardiac monitoring for 24h."
            ),
        },
        "icd10": [
            {"code": "I63.9",  "description": "Cerebral infarction, unspecified",               "type": "primary"},
            {"code": "I61.9",  "description": "Nontraumatic intracerebral hemorrhage, unspecified","type": "secondary"},
            {"code": "G45.9",  "description": "Transient cerebral ischemic attack, unspecified", "type": "secondary"},
            {"code": "I60.9",  "description": "Nontraumatic subarachnoid hemorrhage, unspecified","type": "secondary"},
        ],
        "cpt": [
            {"code": "99285", "description": "ED visit, high medical decision making",           "category": "evaluation"},
            {"code": "70450", "description": "CT head/brain without contrast",                  "category": "imaging"},
            {"code": "70553", "description": "MRI brain with and without contrast",             "category": "imaging"},
            {"code": "85730", "description": "Thromboplastin time, partial (aPTT)",             "category": "lab"},
            {"code": "85610", "description": "Prothrombin time (PT/INR)",                       "category": "lab"},
            {"code": "82947", "description": "Glucose, quantitative (fingerstick)",             "category": "lab"},
            {"code": "93000", "description": "Electrocardiogram, routine ECG 12-lead",          "category": "procedure"},
        ],
    },

    "ABDOMINAL_PAIN": {
        "soap": {
            "subjective": (
                "{age}-year-old {gender} presenting with abdominal pain, onset {duration}. "
                "Pain severity {pain_level}/10, associated with nausea and vomiting. "
                "Patient localizes pain to the right lower quadrant / diffuse. "
                "Active medical history: {conditions}."
            ),
            "objective": (
                "Vitals: HR {hr} bpm, BP {bp} mmHg, RR {rr}/min, Temp {temp}°C, SpO₂ {spo2}%. "
                "Abdomen: tender to palpation, guarding present in RLQ. "
                "Rebound tenderness equivocal. Bowel sounds diminished. "
                "No rigidity. McBurney's point tenderness noted. Rovsing's sign positive."
            ),
            "assessment": (
                "Working diagnosis: Acute abdomen — possible appendicitis. "
                "Differential: (1) Acute appendicitis, (2) Bowel obstruction, "
                "(3) Mesenteric ischemia, (4) Ovarian torsion (if applicable), "
                "(5) Abdominal aortic aneurysm. "
                "RLQ tenderness with guarding raises high suspicion for surgical etiology."
            ),
            "plan": (
                "1. IV access, NPO, aggressive IV fluids. "
                "2. Labs: CBC, BMP, lipase, LFTs, UA, urine hCG (females <55). "
                "3. CT abdomen/pelvis with IV contrast STAT. "
                "4. Antiemetics: ondansetron 4mg IV. "
                "5. Analgesia: morphine 0.1mg/kg IV titrated. "
                "6. Surgery consult if appendicitis confirmed or high suspicion. "
                "7. Serial abdominal exams q1h. "
                "8. Ultrasound abdomen if radiation concerns or pediatric patient."
            ),
        },
        "icd10": [
            {"code": "K37",   "description": "Unspecified appendicitis",                        "type": "primary"},
            {"code": "K56.60","description": "Unspecified intestinal obstruction",               "type": "secondary"},
            {"code": "K55.059","description": "Acute intestinal ischemia, unspecified",         "type": "secondary"},
            {"code": "R10.9", "description": "Unspecified abdominal pain",                      "type": "secondary"},
        ],
        "cpt": [
            {"code": "99285", "description": "ED visit, high medical decision making",           "category": "evaluation"},
            {"code": "74177", "description": "CT abdomen and pelvis with contrast",              "category": "imaging"},
            {"code": "76700", "description": "Ultrasound abdomen complete",                     "category": "imaging"},
            {"code": "80053", "description": "Comprehensive metabolic panel",                   "category": "lab"},
            {"code": "85025", "description": "Complete blood count with differential",           "category": "lab"},
            {"code": "84702", "description": "Gonadotropin, chorionic (hCG) quantitative",     "category": "lab"},
            {"code": "81000", "description": "Urinalysis by dipstick",                          "category": "lab"},
        ],
    },

    "SEPSIS_FEVER": {
        "soap": {
            "subjective": (
                "{age}-year-old {gender} presenting with fever, chills, and systemic illness, "
                "onset {duration}. Patient reports rigors, malaise, and decreased urine output. "
                "Symptom severity {pain_level}/10. "
                "Active medical history: {conditions}."
            ),
            "objective": (
                "Vitals: HR {hr} bpm, BP {bp} mmHg, RR {rr}/min, Temp {temp}°C, SpO₂ {spo2}%. "
                "Patient appears acutely ill and diaphoretic. Skin: warm, flushed. "
                "No clear source of infection identified on initial exam. "
                "Abdomen: soft, non-tender. Chest: clear. Neuro: alert and oriented."
            ),
            "assessment": (
                "Working diagnosis: Sepsis — source to be determined. "
                "Differential: (1) Sepsis (bacterial — urinary, pulmonary, or unknown source), "
                "(2) Severe sepsis / septic shock, (3) Viral illness, "
                "(4) Endocarditis, (5) Meningitis. "
                "qSOFA positive — meets SIRS criteria. Lactate and cultures needed urgently."
            ),
            "plan": (
                "1. Sepsis bundle initiation within 1 hour. "
                "2. IV access x2, aggressive fluid resuscitation — 30mL/kg NS bolus. "
                "3. Blood cultures x2 (peripheral + central if CVC) BEFORE antibiotics. "
                "4. Broad-spectrum antibiotics: Piperacillin-tazobactam 4.5g IV STAT. "
                "5. Labs: CBC, BMP, lactate, LFTs, UA/culture, CXR, procalcitonin. "
                "6. Vasopressors (norepinephrine) if MAP <65 despite fluids. "
                "7. ICU consult if hemodynamically unstable. "
                "8. Repeat lactate in 2 hours — target clearance ≥10%."
            ),
        },
        "icd10": [
            {"code": "A41.9",  "description": "Sepsis, unspecified organism",                   "type": "primary"},
            {"code": "R65.20", "description": "Severe sepsis without septic shock",             "type": "secondary"},
            {"code": "N39.0",  "description": "Urinary tract infection, site not specified",    "type": "secondary"},
            {"code": "J18.9",  "description": "Pneumonia, unspecified organism",                "type": "secondary"},
        ],
        "cpt": [
            {"code": "99285", "description": "ED visit, high medical decision making",           "category": "evaluation"},
            {"code": "87040", "description": "Blood culture, aerobic with isolation",            "category": "lab"},
            {"code": "86804", "description": "Procalcitonin (PCT)",                             "category": "lab"},
            {"code": "83605", "description": "Lactate (lactic acid)",                           "category": "lab"},
            {"code": "80053", "description": "Comprehensive metabolic panel",                   "category": "lab"},
            {"code": "71046", "description": "Chest X-ray, 2 views",                            "category": "imaging"},
            {"code": "81001", "description": "Urinalysis with microscopy",                      "category": "lab"},
        ],
    },

    "TRAUMA": {
        "soap": {
            "subjective": (
                "{age}-year-old {gender} presenting following traumatic event, "
                "onset {duration} ago. Mechanism: fall / motor vehicle collision / blunt force. "
                "Patient reports pain severity {pain_level}/10 at site of injury. "
                "Active medical history: {conditions}."
            ),
            "objective": (
                "Vitals: HR {hr} bpm, BP {bp} mmHg, RR {rr}/min, Temp {temp}°C, SpO₂ {spo2}%. "
                "Primary survey (ABCDE): Airway patent, breathing adequate, circulation intact. "
                "Visible lacerations/contusions noted. No obvious deformity on inspection. "
                "GCS 15. FAST exam pending. Spine precautions maintained."
            ),
            "assessment": (
                "Working diagnosis: Blunt trauma — injury extent to be determined. "
                "Differential: (1) Closed head injury / TBI, (2) Rib fractures / pneumothorax, "
                "(3) Intra-abdominal hemorrhage, (4) Long bone fracture, (5) Spinal injury. "
                "Mechanism suggests moderate-to-high energy injury; imaging essential."
            ),
            "plan": (
                "1. Primary and secondary survey per ATLS protocol. "
                "2. IV access x2, type & screen. "
                "3. Trauma labs: CBC, BMP, coagulation studies, lactate, UA, LFTs. "
                "4. CT head/C-spine if head/neck injury. "
                "5. FAST exam STAT. "
                "6. Pan-CT (head/chest/abdomen/pelvis) if high-energy mechanism. "
                "7. Orthopedics consult if fracture confirmed. "
                "8. Neurosurgery consult if intracranial injury on imaging."
            ),
        },
        "icd10": [
            {"code": "T14.90XA","description": "Injury, unspecified, initial encounter",        "type": "primary"},
            {"code": "S09.90XA","description": "Unspecified injury of head, initial encounter", "type": "secondary"},
            {"code": "S22.20XA","description": "Unspecified fracture of sternum, initial encounter","type": "secondary"},
        ],
        "cpt": [
            {"code": "99285", "description": "ED visit, high medical decision making",           "category": "evaluation"},
            {"code": "70450", "description": "CT head without contrast",                        "category": "imaging"},
            {"code": "72125", "description": "CT cervical spine without contrast",              "category": "imaging"},
            {"code": "74177", "description": "CT abdomen and pelvis with contrast",              "category": "imaging"},
            {"code": "76604", "description": "Ultrasound chest (FAST exam)",                    "category": "imaging"},
            {"code": "85025", "description": "Complete blood count with differential",           "category": "lab"},
            {"code": "80053", "description": "Comprehensive metabolic panel",                   "category": "lab"},
        ],
    },

    "DIABETIC_EMERGENCY": {
        "soap": {
            "subjective": (
                "{age}-year-old {gender} with known diabetes presenting with symptoms of "
                "glycemic dysregulation, onset {duration}. Reports dizziness, confusion, "
                "polyuria, or polydipsia. Severity {pain_level}/10. "
                "Active medical history: {conditions}."
            ),
            "objective": (
                "Vitals: HR {hr} bpm, BP {bp} mmHg, RR {rr}/min, Temp {temp}°C, SpO₂ {spo2}%. "
                "Patient appears diaphoretic and confused (if hypoglycemic) or Kussmaul breathing "
                "and fruity odor (if DKA). Bedside glucose: pending. Skin turgor: decreased."
            ),
            "assessment": (
                "Working diagnosis: Diabetic emergency — DKA vs HHS vs hypoglycemia. "
                "Differential: (1) Diabetic ketoacidosis (DKA), "
                "(2) Hyperosmolar hyperglycemic state (HHS), "
                "(3) Severe hypoglycemia, (4) Hypoglycemia unawareness. "
                "Patient's history of {conditions} is directly relevant to this presentation."
            ),
            "plan": (
                "1. Bedside glucose STAT. "
                "2. IV access, NS 1L bolus. "
                "3. If hypoglycemia: D50 1 amp IV or glucagon 1mg IM. "
                "4. Labs: BMP, CBC, HbA1c, blood gas, ketones (urine or serum), UA. "
                "5. If DKA: insulin drip per protocol, aggressive fluids, K+ replacement. "
                "6. Continuous glucose monitoring. "
                "7. Endocrinology consult for DKA/HHS. "
                "8. ICU admission if severe DKA or HHS."
            ),
        },
        "icd10": [
            {"code": "E10.10", "description": "Type 1 diabetes mellitus with ketoacidosis without coma","type": "primary"},
            {"code": "E11.649","description": "Type 2 diabetes mellitus with hypoglycemia without coma","type": "secondary"},
            {"code": "E11.00", "description": "Type 2 diabetes with hyperosmolarity without coma","type": "secondary"},
        ],
        "cpt": [
            {"code": "99285", "description": "ED visit, high medical decision making",           "category": "evaluation"},
            {"code": "82962", "description": "Glucose, blood by glucose monitoring device",     "category": "lab"},
            {"code": "82943", "description": "Glucagon",                                        "category": "lab"},
            {"code": "83037", "description": "Hemoglobin A1c",                                 "category": "lab"},
            {"code": "80053", "description": "Comprehensive metabolic panel",                   "category": "lab"},
            {"code": "82803", "description": "Blood gases",                                    "category": "lab"},
        ],
    },

    "CARDIAC_ARRHYTHMIA": {
        "soap": {
            "subjective": (
                "{age}-year-old {gender} presenting with palpitations and heart racing, "
                "onset {duration}. Reports feeling the heart 'skipping' or 'pounding'. "
                "Severity {pain_level}/10. No syncope or pre-syncope. "
                "Active medical history: {conditions}."
            ),
            "objective": (
                "Vitals: HR {hr} bpm (possibly irregular), BP {bp} mmHg, RR {rr}/min, "
                "Temp {temp}°C, SpO₂ {spo2}%. "
                "Cardiac exam: irregular rhythm noted. No murmurs. JVP normal. "
                "Lungs clear. No peripheral edema. Alert and oriented x3."
            ),
            "assessment": (
                "Working diagnosis: Cardiac arrhythmia — rhythm to be characterised. "
                "Differential: (1) Atrial fibrillation / flutter, "
                "(2) Supraventricular tachycardia (SVT), (3) Ventricular tachycardia, "
                "(4) Sinus tachycardia (secondary cause), (5) Anxiety-related palpitations. "
                "12-lead ECG required immediately to determine rhythm."
            ),
            "plan": (
                "1. 12-lead ECG STAT. "
                "2. Continuous cardiac monitoring, IV access. "
                "3. Labs: BMP (electrolytes), TSH, CBC, troponin, magnesium. "
                "4. If SVT with hemodynamic stability: vagal maneuvers → adenosine 6mg IV. "
                "5. If AF with RVR: rate control with diltiazem or metoprolol. "
                "6. If VT: immediate cardioversion if unstable. "
                "7. Cardiology consult. "
                "8. Echocardiogram to assess cardiac function."
            ),
        },
        "icd10": [
            {"code": "I49.9",  "description": "Cardiac arrhythmia, unspecified",               "type": "primary"},
            {"code": "I48.91", "description": "Unspecified atrial fibrillation",               "type": "secondary"},
            {"code": "I47.1",  "description": "Supraventricular tachycardia",                  "type": "secondary"},
        ],
        "cpt": [
            {"code": "99284", "description": "ED visit, moderate medical decision making",      "category": "evaluation"},
            {"code": "93000", "description": "Electrocardiogram, routine ECG 12-lead",          "category": "procedure"},
            {"code": "93306", "description": "Echocardiography with spectral Doppler",          "category": "imaging"},
            {"code": "84443", "description": "Thyroid stimulating hormone (TSH)",               "category": "lab"},
            {"code": "80053", "description": "Comprehensive metabolic panel",                   "category": "lab"},
            {"code": "84484", "description": "Troponin I, quantitative",                       "category": "lab"},
        ],
    },

    "URINARY_RENAL": {
        "soap": {
            "subjective": (
                "{age}-year-old {gender} presenting with urinary symptoms and/or flank pain, "
                "onset {duration}. Reports dysuria, frequency, urgency, or flank/back pain. "
                "Severity {pain_level}/10. No fever initially. "
                "Active medical history: {conditions}."
            ),
            "objective": (
                "Vitals: HR {hr} bpm, BP {bp} mmHg, RR {rr}/min, Temp {temp}°C, SpO₂ {spo2}%. "
                "CVA tenderness: positive on affected side. Abdomen: suprapubic tenderness. "
                "No peritoneal signs. External genitalia: no lesions. "
                "Urine: cloudy, possible hematuria on visual inspection."
            ),
            "assessment": (
                "Working diagnosis: Urinary tract infection vs nephrolithiasis vs pyelonephritis. "
                "Differential: (1) Lower UTI / cystitis, "
                "(2) Pyelonephritis, (3) Ureteral nephrolithiasis (kidney stone), "
                "(4) Ovarian pathology (if applicable), (5) Appendicitis (atypical). "
                "CVA tenderness suggests upper tract involvement or stone."
            ),
            "plan": (
                "1. Urinalysis with microscopy and culture. "
                "2. Urine hCG (females of childbearing age). "
                "3. BMP, CBC. "
                "4. CT abdomen/pelvis without contrast (stone protocol) if stone suspected. "
                "5. Ultrasound kidneys/bladder if radiation concerns. "
                "6. If uncomplicated UTI: oral antibiotics (nitrofurantoin or trimethoprim). "
                "7. If pyelonephritis: IV ciprofloxacin + IV fluids. "
                "8. Urology consult if obstructing stone >5mm or sepsis signs."
            ),
        },
        "icd10": [
            {"code": "N39.0",  "description": "Urinary tract infection, site not specified",    "type": "primary"},
            {"code": "N20.1",  "description": "Calculus of ureter",                             "type": "secondary"},
            {"code": "N10",    "description": "Acute pyelonephritis",                           "type": "secondary"},
        ],
        "cpt": [
            {"code": "99283", "description": "ED visit, moderate medical decision making",      "category": "evaluation"},
            {"code": "81001", "description": "Urinalysis with microscopy",                      "category": "lab"},
            {"code": "87086", "description": "Urine culture",                                   "category": "lab"},
            {"code": "74178", "description": "CT abdomen and pelvis without contrast (stone protocol)", "category": "imaging"},
            {"code": "76770", "description": "Ultrasound retroperitoneal (kidneys)",             "category": "imaging"},
            {"code": "80053", "description": "Comprehensive metabolic panel",                   "category": "lab"},
        ],
    },

    "HEADACHE": {
        "soap": {
            "subjective": (
                "{age}-year-old {gender} presenting with headache, onset {duration}. "
                "Describes pain as {pain_level}/10 severity. "
                "Reports photophobia and nausea. No prior similar episode. "
                "Active medical history: {conditions}."
            ),
            "objective": (
                "Vitals: HR {hr} bpm, BP {bp} mmHg, RR {rr}/min, Temp {temp}°C, SpO₂ {spo2}%. "
                "Neuro exam: alert and oriented x3, GCS 15. "
                "No focal neurological deficits. Pupils equal and reactive. "
                "No meningismus. Fundoscopy: no papilledema. Kernig/Brudzinski negative."
            ),
            "assessment": (
                "Working diagnosis: Headache — etiology to be determined. "
                "Differential: (1) Migraine with/without aura, "
                "(2) Subarachnoid hemorrhage (thunderclap — must rule out), "
                "(3) Tension headache, (4) Hypertensive headache, "
                "(5) Meningitis / encephalitis. "
                "Thunderclap onset, worst-ever headache, or meningismus = emergent imaging required."
            ),
            "plan": (
                "1. If thunderclap / worst-ever headache: CT head without contrast STAT. "
                "2. If CT negative and SAH still suspected: LP for xanthochromia. "
                "3. If migraine: dark quiet room, ketorolac 15-30mg IV, ondansetron 4mg IV. "
                "4. BP management if hypertensive headache (SBP >180). "
                "5. Labs: BMP, CBC if systemic concern. "
                "6. Neurology consult if focal deficits or imaging abnormality. "
                "7. Discharge with outpatient neurology follow-up if migraine confirmed."
            ),
        },
        "icd10": [
            {"code": "G43.909","description": "Migraine, unspecified, not intractable",         "type": "primary"},
            {"code": "I60.9",  "description": "Nontraumatic subarachnoid hemorrhage",           "type": "secondary"},
            {"code": "G44.309","description": "Post-traumatic headache, unspecified",           "type": "secondary"},
        ],
        "cpt": [
            {"code": "99283", "description": "ED visit, moderate medical decision making",      "category": "evaluation"},
            {"code": "70450", "description": "CT head without contrast",                        "category": "imaging"},
            {"code": "70553", "description": "MRI brain with and without contrast",             "category": "imaging"},
            {"code": "62270", "description": "Spinal puncture, lumbar, diagnostic",             "category": "procedure"},
            {"code": "80053", "description": "Comprehensive metabolic panel",                   "category": "lab"},
        ],
    },
}

# Default for unmatched symptoms
_DEFAULT_TEMPLATE: Dict[str, Any] = {
    "soap": {
        "subjective": (
            "{age}-year-old {gender} presenting to the Emergency Department with {symptoms}. "
            "Onset {duration}. Symptom severity rated {pain_level}/10 by patient. "
            "Active medical history: {conditions}."
        ),
        "objective": (
            "Vitals: HR {hr} bpm, BP {bp} mmHg, RR {rr}/min, Temp {temp}°C, SpO₂ {spo2}%. "
            "General: patient appears in {distress_level} distress, alert and oriented x3. "
            "Physical examination findings pending full bedside assessment by clinician."
        ),
        "assessment": (
            "Working diagnosis: To be determined pending clinical evaluation and investigations. "
            "Patient presents with {symptoms}. Active comorbidities ({conditions}) may be contributing. "
            "Differential diagnosis will be guided by clinical examination and investigation results."
        ),
        "plan": (
            "1. Full clinical assessment by attending physician. "
            "2. Targeted investigations based on clinical findings. "
            "3. IV access and monitoring as indicated. "
            "4. Appropriate analgesia and symptom management. "
            "5. Specialist consult as required. "
            "6. Disposition decision pending investigation results."
        ),
    },
    "icd10": [
        {"code": "R68.89", "description": "Other specified general symptoms and signs",         "type": "primary"},
    ],
    "cpt": [
        {"code": "99283", "description": "ED visit, moderate medical decision making",          "category": "evaluation"},
        {"code": "80053", "description": "Comprehensive metabolic panel",                       "category": "lab"},
        {"code": "85025", "description": "Complete blood count with differential",              "category": "lab"},
    ],
}


# ── Main public function ──────────────────────────────────────────────────────

def build_fallback_soap(
    symptoms: str,
    patient_age: int,
    patient_gender: str,
    active_conditions: List[str],
    vitals: Dict[str, Any],
    duration: str = "unknown duration",
    pain_level: int = 5,
) -> Tuple[Dict[str, str], List[Dict], List[Dict]]:
    """
    Generate a fallback SOAP note + ICD-10/CPT codes from patient context.

    Returns:
        (soap_note_dict, icd10_list, cpt_list)
        soap_note_dict has keys: subjective, objective, assessment, plan
    """
    # 1. Match condition template by keyword scan
    symptoms_lower = symptoms.lower()
    matched_condition = None
    for entry in CONDITION_TEMPLATES:
        if any(kw in symptoms_lower for kw in entry["keywords"]):
            matched_condition = entry["condition"]
            break

    template = _TEMPLATES.get(matched_condition, _DEFAULT_TEMPLATE)

    # 2. Build substitution variables
    conditions_str = (
        ", ".join(active_conditions) if active_conditions else "no significant past medical history"
    )
    gender_str = patient_gender if patient_gender else "patient"
    distress_map = {range(0, 4): "mild", range(4, 7): "moderate", range(7, 11): "severe"}
    distress_level = next(
        (v for k, v in distress_map.items() if pain_level in k), "moderate"
    )

    sub_vars = {
        "age":           str(patient_age),
        "gender":        gender_str,
        "conditions":    conditions_str,
        "symptoms":      symptoms[:200],
        "duration":      duration or "unspecified duration",
        "pain_level":    str(pain_level),
        "distress_level":distress_level,
        "hr":            str(vitals.get("heart_rate", "NR")),
        "bp":            str(vitals.get("blood_pressure", "NR")),
        "rr":            str(vitals.get("respiratory_rate", "NR")),
        "temp":          str(vitals.get("temperature", "NR")),
        "spo2":          str(vitals.get("oxygen_sat", "NR")),
    }

    # 3. Fill template strings
    soap_raw = template["soap"]
    soap_note = {
        "subjective": soap_raw["subjective"].format(**sub_vars),
        "objective":  soap_raw["objective"].format(**sub_vars),
        "assessment": soap_raw["assessment"].format(**sub_vars),
        "plan":       soap_raw["plan"].format(**sub_vars),
    }

    return soap_note, template["icd10"], template["cpt"]


def needs_fallback(diagnostics_output: Dict[str, Any]) -> bool:
    """Return True if the LLM didn't produce a valid SOAP note or billing codes."""
    soap = diagnostics_output.get("soap_note")
    icd  = diagnostics_output.get("icd10_codes", [])
    cpt  = diagnostics_output.get("cpt_codes", [])

    # Needs fallback if soap is missing or all three sections are empty strings
    soap_empty = (
        not soap or
        not any([
            (soap.get("subjective") or "").strip(),
            (soap.get("objective")  or "").strip(),
            (soap.get("assessment") or "").strip(),
            (soap.get("plan")       or "").strip(),
        ])
    )
    codes_empty = len(icd) == 0 and len(cpt) == 0

    return soap_empty or codes_empty
