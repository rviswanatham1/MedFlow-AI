"""
Care Plan Fallback Generator
==============================
Symptom-keyword-based fallback that produces a complete patient-facing care plan
(labs, medications, instructions, follow-up, diet, activity) when no doctor-created
plan exists in the triage store.

Mirrors the pattern of soap_fallback.py — keyword → template → substitution.

Usage:
    from care_plan_fallback import build_fallback_care_plan
    plan = build_fallback_care_plan(symptoms, patient_age, patient_gender, active_conditions)
"""

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List


# ── Keyword → condition mapping ───────────────────────────────────────────────

CONDITION_TEMPLATES: List[Dict[str, Any]] = [
    {
        "keywords": ["chest pain", "chest pressure", "chest tightness", "crushing",
                     "radiating arm", "left arm", "jaw pain", "diaphoresis", "cardiac"],
        "condition": "CHEST_PAIN_ACS",
    },
    {
        "keywords": ["shortness of breath", "difficulty breathing", "breathless",
                     "dyspnea", "wheezing", "can't breathe", "productive cough",
                     "dry cough", "cough"],
        "condition": "RESPIRATORY",
    },
    {
        "keywords": ["stroke", "weakness in one side", "facial droop", "arm weakness",
                     "slurred speech", "sudden numbness", "vision loss", "paralysis"],
        "condition": "NEUROLOGICAL",
    },
    {
        "keywords": ["abdominal pain", "belly pain", "stomach pain", "nausea",
                     "vomiting", "diarrhea", "bloating", "cramping"],
        "condition": "ABDOMINAL_PAIN",
    },
    {
        "keywords": ["fever", "sepsis", "infection", "chills", "rigors",
                     "high temperature", "sore throat", "productive cough"],
        "condition": "INFECTION_FEVER",
    },
    {
        "keywords": ["trauma", "fall", "accident", "fracture", "broken",
                     "head injury", "laceration", "bleeding", "wound", "injury"],
        "condition": "TRAUMA",
    },
    {
        "keywords": ["blood sugar", "hypoglycemia", "hyperglycemia", "dka",
                     "ketoacidosis", "glucose", "diabetic"],
        "condition": "DIABETIC_EMERGENCY",
    },
    {
        "keywords": ["palpitations", "heart racing", "tachycardia", "fast heart",
                     "irregular heartbeat", "skipping beats"],
        "condition": "ARRHYTHMIA",
    },
    {
        "keywords": ["urinary", "uti", "dysuria", "frequency", "burning urination",
                     "flank pain", "kidney stone", "blood in urine"],
        "condition": "URINARY_RENAL",
    },
    {
        "keywords": ["headache", "migraine", "head pain", "photophobia",
                     "thunderclap headache"],
        "condition": "HEADACHE",
    },
    {
        "keywords": ["dizziness", "vertigo", "lightheaded", "balance", "spinning",
                     "fainting", "syncope", "presyncope"],
        "condition": "DIZZINESS",
    },
    {
        "keywords": ["low mood", "depression", "suicidal", "self-harm", "mental health",
                     "anxiety", "panic attack", "hopeless"],
        "condition": "MENTAL_HEALTH",
    },
    {
        "keywords": ["joint pain", "swollen joint", "arthritis", "rheumatoid",
                     "osteoarthritis", "gout", "knee pain", "hip pain"],
        "condition": "JOINT_PAIN",
    },
]


# ── Per-condition care plan templates ─────────────────────────────────────────

_CARE_PLANS: Dict[str, Dict[str, Any]] = {

    "CHEST_PAIN_ACS": {
        "labs": [
            {"name": "Troponin I (High-sensitivity)", "urgency": "STAT", "timing": "Within 1 hour — repeat at 3h", "notes": "Rule out myocardial infarction"},
            {"name": "Comprehensive Metabolic Panel (CMP)", "urgency": "STAT", "timing": "Within 2 hours", "notes": "Electrolytes and kidney function check"},
            {"name": "CBC with Differential", "urgency": "ASAP", "timing": "Within 4 hours", "notes": "Check for anemia or infection"},
            {"name": "Lipid Panel (Fasting)", "urgency": "Routine", "timing": "Next morning fasting draw", "notes": "Cardiovascular risk assessment — fast 12 hours before"},
            {"name": "BNP (B-type Natriuretic Peptide)", "urgency": "ASAP", "timing": "Within 4 hours", "notes": "Assess heart failure component if shortness of breath present"},
        ],
        "medications": [
            {"name": "Aspirin", "dose": "81 mg", "frequency": "Once daily", "route": "PO", "duration": "Ongoing", "notes": "Antiplatelet therapy — do NOT stop without consulting your cardiologist"},
            {"name": "Atorvastatin (Lipitor)", "dose": "40 mg", "frequency": "Once daily at bedtime", "route": "PO", "duration": "Ongoing", "notes": "Cholesterol management — take consistently; avoid grapefruit juice"},
            {"name": "Metoprolol Succinate", "dose": "25 mg", "frequency": "Once daily (morning)", "route": "PO", "duration": "Ongoing", "notes": "Heart rate and blood pressure control; do not stop abruptly"},
            {"name": "Nitroglycerin SL (PRN)", "dose": "0.4 mg", "frequency": "Every 5 min as needed (max 3 doses)", "route": "SQ", "duration": "As needed for chest pain", "notes": "Place under tongue at first sign of chest pain. Call 911 if no relief after 3 doses"},
        ],
        "instructions": (
            "1. Call 911 immediately if chest pain returns — do not drive yourself to the hospital.\n"
            "2. Take all heart medications at the same time each day without skipping doses.\n"
            "3. Place nitroglycerin tablet under your tongue at the first sign of chest pain. "
            "Take up to 3 doses, 5 minutes apart. If no relief, call 911.\n"
            "4. Avoid strenuous activity until cleared by your cardiologist.\n"
            "5. Monitor for signs of worsening: shortness of breath, swelling in legs, dizziness, or fainting.\n"
            "6. Weigh yourself every morning — alert your doctor if weight increases more than 2 lbs overnight."
        ),
        "follow_up": "Cardiology follow-up within 5 days. Repeat ECG and troponin review at follow-up. Primary care visit in 2 weeks for medication review and blood pressure check.",
        "diet": (
            "Heart-healthy diet: reduce saturated fats, avoid trans fats and processed foods. "
            "Limit sodium to <2g/day (avoid table salt, canned goods, fast food). "
            "Increase vegetables, fruits, whole grains, and omega-3 rich fish (salmon, mackerel) 2x/week. "
            "Limit alcohol to 1 drink/day maximum. Avoid energy drinks and caffeine excess."
        ),
        "activity": (
            "Complete rest for 48 hours after discharge. "
            "Avoid lifting anything over 5 lbs until cardiologist clears you. "
            "Cardiac rehabilitation program will be scheduled at your follow-up visit. "
            "No driving for 48 hours or while taking nitroglycerin. "
            "Short gentle walks (5–10 min) are acceptable after 48 hours if pain-free."
        ),
    },

    "RESPIRATORY": {
        "labs": [
            {"name": "Pulse Oximetry (SpO₂ monitoring)", "urgency": "STAT", "timing": "Continuous monitoring during visit", "notes": "Target SpO₂ ≥94% — alert staff if drops below 92%"},
            {"name": "Peak Flow Measurement", "urgency": "ASAP", "timing": "Before and after bronchodilator treatment", "notes": "Assess severity of airflow obstruction"},
            {"name": "CBC with Differential", "urgency": "ASAP", "timing": "Within 4 hours", "notes": "Rule out infection — elevated WBC suggests bacterial cause"},
            {"name": "Procalcitonin", "urgency": "ASAP", "timing": "Within 4 hours", "notes": "Distinguish bacterial from viral respiratory infection"},
            {"name": "Chest X-Ray (2 views)", "urgency": "ASAP", "timing": "Within 2 hours", "notes": "Assess lung fields for pneumonia, effusion, or collapse"},
        ],
        "medications": [
            {"name": "Salbutamol (Albuterol) Inhaler", "dose": "2 puffs (200 mcg)", "frequency": "Every 4–6 hours as needed", "route": "Inhaled", "duration": "7 days or until follow-up", "notes": "Use spacer for best delivery. Shake well before each puff. Rinse mouth after use"},
            {"name": "Prednisolone (Oral Steroid)", "dose": "40 mg", "frequency": "Once daily in the morning", "route": "PO", "duration": "5 days", "notes": "Complete the full course — do not stop early. Take with food to protect stomach"},
            {"name": "Amoxicillin", "dose": "500 mg", "frequency": "Three times daily", "route": "PO", "duration": "7 days", "notes": "Only if bacterial infection confirmed. Complete full course even if feeling better"},
            {"name": "Montelukast (Singulair)", "dose": "10 mg", "frequency": "Once daily at bedtime", "route": "PO", "duration": "Ongoing", "notes": "Long-term asthma/allergy controller — take nightly even on symptom-free days"},
        ],
        "instructions": (
            "1. Use your reliever inhaler (salbutamol) at the first sign of breathlessness.\n"
            "2. If you need your reliever inhaler more than 3 times per week, contact your doctor — "
            "your preventer medication may need adjusting.\n"
            "3. Avoid known triggers: smoke, dust, cold air, strong odors, pets, pollen.\n"
            "4. Complete the steroid course fully — stopping early can cause a rebound.\n"
            "5. Call 999/911 or return to ED immediately if: lips turn blue, can't speak in full sentences, "
            "inhaler gives no relief.\n"
            "6. Keep your home well-ventilated and humidity between 40–60%."
        ),
        "follow_up": "GP/primary care follow-up within 48 hours. Respiratory specialist review in 4 weeks. Bring your inhaler to all appointments for technique check.",
        "diet": (
            "Stay well hydrated — drink 8–10 glasses of water daily to thin mucus secretions. "
            "Warm fluids (herbal tea, warm water with honey and lemon) soothe airways. "
            "Avoid cold drinks and ice cream during flare-ups. "
            "Anti-inflammatory foods: turmeric, ginger, berries, and leafy greens support lung health. "
            "Avoid dairy if it worsens mucus production."
        ),
        "activity": (
            "Rest during active respiratory flare — avoid exertion that worsens breathlessness. "
            "Once stabilized, gentle breathing exercises (pursed-lip breathing, diaphragmatic breathing) daily. "
            "Avoid outdoor exercise during high pollen or pollution days — check air quality index. "
            "Pulmonary rehabilitation referral will be arranged at follow-up if COPD confirmed. "
            "Sleep with head elevated (2 extra pillows) to ease nighttime breathing."
        ),
    },

    "NEUROLOGICAL": {
        "labs": [
            {"name": "Glucose (Fasting & Post-meal)", "urgency": "STAT", "timing": "Immediate — check bedside glucose first", "notes": "Hypoglycemia can mimic stroke — must exclude first"},
            {"name": "CBC, CMP, PT/INR/aPTT", "urgency": "STAT", "timing": "Within 1 hour", "notes": "Assess clotting ability before any anticoagulation decision"},
            {"name": "Lipid Panel", "urgency": "Routine", "timing": "Next available morning draw", "notes": "Cardiovascular risk stratification post-neurological event"},
            {"name": "HbA1c", "urgency": "ASAP", "timing": "Within 24 hours", "notes": "Long-term glucose control — key stroke risk factor"},
            {"name": "ECG (Cardiac Rhythm)", "urgency": "STAT", "timing": "Within 30 minutes", "notes": "Rule out atrial fibrillation as cardioembolic stroke source"},
        ],
        "medications": [
            {"name": "Aspirin", "dose": "75–100 mg", "frequency": "Once daily", "route": "PO", "duration": "Ongoing (unless anticoagulated)", "notes": "Secondary stroke prevention — never stop without neurology guidance"},
            {"name": "Atorvastatin (Lipitor)", "dose": "40–80 mg", "frequency": "Once daily at bedtime", "route": "PO", "duration": "Ongoing", "notes": "High-intensity statin for stroke prevention — take consistently"},
            {"name": "Ramipril (ACE Inhibitor)", "dose": "5 mg", "frequency": "Once daily", "route": "PO", "duration": "Ongoing", "notes": "Blood pressure control for stroke prevention; monitor potassium"},
            {"name": "Clopidogrel (if AF or dual antiplatelet prescribed)", "dose": "75 mg", "frequency": "Once daily", "route": "PO", "duration": "As directed by neurologist", "notes": "Do not take with ibuprofen or aspirin unless specifically instructed"},
        ],
        "instructions": (
            "1. Call 999/911 immediately if any new neurological symptoms occur: "
            "sudden face drooping, arm weakness, speech difficulty, vision changes.\n"
            "2. FAST test reminder: Face drooping, Arm weakness, Speech difficulty, Time to call 911.\n"
            "3. Take all blood pressure and anti-clot medications exactly as prescribed — never skip.\n"
            "4. Monitor blood pressure at home twice daily. Target: below 130/80 mmHg.\n"
            "5. Avoid driving until cleared by your neurologist.\n"
            "6. Report any falls, confusion episodes, or new weakness to your doctor immediately."
        ),
        "follow_up": "Neurology outpatient clinic within 1 week. TIA/stroke clinic referral if not already made. Brain imaging review appointment in 2 weeks. Physiotherapy and speech therapy assessment within 5 days.",
        "diet": (
            "Mediterranean diet strongly recommended for secondary stroke prevention: "
            "olive oil, fish, nuts, legumes, vegetables, and whole grains. "
            "Strict sodium reduction (<2g/day) — critical for blood pressure control. "
            "Avoid alcohol — increases re-bleed risk in haemorrhagic stroke. "
            "Adequate fluid intake to prevent dehydration-related blood viscosity increase."
        ),
        "activity": (
            "Activity level guided by your neurologist and physiotherapist. "
            "Early mobilisation is beneficial — gentle sitting up and standing as tolerated. "
            "Physiotherapy exercises to rebuild strength and coordination — attend all sessions. "
            "Occupational therapy assessment for home safety and daily activities. "
            "No driving until neurological review confirms it is safe — this is a legal requirement. "
            "Swimming and unaccompanied bathing should be avoided initially."
        ),
    },

    "ABDOMINAL_PAIN": {
        "labs": [
            {"name": "CBC with Differential", "urgency": "ASAP", "timing": "Within 2 hours", "notes": "Elevated WBC suggests infection or appendicitis"},
            {"name": "CMP + Lipase", "urgency": "ASAP", "timing": "Within 2 hours", "notes": "Assess liver function and rule out pancreatitis"},
            {"name": "Urinalysis with Culture", "urgency": "ASAP", "timing": "Within 2 hours", "notes": "Rule out UTI or kidney stone as cause of pain"},
            {"name": "Urine Pregnancy Test (if applicable)", "urgency": "STAT", "timing": "Within 1 hour", "notes": "Must exclude ectopic pregnancy in females of childbearing age"},
            {"name": "Abdominal Ultrasound", "urgency": "ASAP", "timing": "Within 4 hours", "notes": "Assess gallbladder, appendix, and other abdominal organs"},
        ],
        "medications": [
            {"name": "Ondansetron (Zofran)", "dose": "4 mg", "frequency": "Every 8 hours as needed", "route": "PO", "duration": "3–5 days", "notes": "For nausea and vomiting — dissolves under tongue (ODT form) or take with small sip of water"},
            {"name": "Omeprazole (Prilosec)", "dose": "20 mg", "frequency": "Once daily before breakfast", "route": "PO", "duration": "14 days", "notes": "Reduces stomach acid — take 30 minutes before eating for best effect"},
            {"name": "Hyoscine Butylbromide (Buscopan)", "dose": "10 mg", "frequency": "Three times daily as needed", "route": "PO", "duration": "5 days", "notes": "For cramping / IBS-type spasm — avoid if constipation is severe"},
            {"name": "Paracetamol (Acetaminophen)", "dose": "1000 mg", "frequency": "Every 6 hours as needed", "route": "PO", "duration": "As needed", "notes": "For mild-moderate pain. Max 4g per day. Avoid alcohol while taking."},
        ],
        "instructions": (
            "1. Stay on a clear liquid diet for 24 hours (water, broth, clear juice) — no solid food until pain improves.\n"
            "2. Return to ED immediately if pain becomes severe (>8/10), you develop high fever (>38.5°C/101°F), "
            "vomit blood, or abdomen becomes rigid and board-like.\n"
            "3. Take anti-nausea medication before eating to improve tolerance.\n"
            "4. Avoid NSAIDs (ibuprofen, naproxen) as they can irritate the stomach lining.\n"
            "5. Stay well hydrated — small frequent sips are better than large amounts at once.\n"
            "6. Keep a food diary to identify any trigger foods."
        ),
        "follow_up": "GP review within 48 hours if symptoms persist. If imaging showed gallstones or other findings, surgical outpatient review within 1 week. Return to ED if fever develops or pain worsens significantly.",
        "diet": (
            "BRAT diet initially (Bananas, Rice, Applesauce, Toast) for first 24–48 hours. "
            "Gradually reintroduce bland foods: boiled chicken, crackers, plain pasta. "
            "Avoid: spicy foods, fatty or fried foods, alcohol, caffeine, carbonated drinks. "
            "Eat small meals every 3–4 hours rather than large meals. "
            "Increase fibre gradually once pain resolves to prevent constipation."
        ),
        "activity": (
            "Rest and avoid strenuous activity while in pain. "
            "Short gentle walks help stimulate digestion and reduce gas pain. "
            "Avoid heavy lifting (>5 lbs) until reviewed by surgeon if surgical cause is suspected. "
            "Apply a warm heat pack to abdomen for cramping — avoid direct skin contact."
        ),
    },

    "INFECTION_FEVER": {
        "labs": [
            {"name": "CBC with Differential", "urgency": "ASAP", "timing": "Within 2 hours", "notes": "WBC count to assess severity of infection"},
            {"name": "CRP (C-Reactive Protein)", "urgency": "ASAP", "timing": "Within 2 hours", "notes": "Inflammatory marker — helps monitor treatment response"},
            {"name": "Blood Cultures x2", "urgency": "STAT", "timing": "Before first antibiotic dose", "notes": "MUST be collected before starting antibiotics — do not miss this window"},
            {"name": "Procalcitonin", "urgency": "ASAP", "timing": "Within 4 hours", "notes": "Differentiates bacterial from viral infection"},
            {"name": "Throat Swab / Urine Culture (as indicated)", "urgency": "Routine", "timing": "Within 24 hours", "notes": "Identify infection source and guide antibiotic choice"},
        ],
        "medications": [
            {"name": "Amoxicillin-Clavulanate (Augmentin)", "dose": "625 mg", "frequency": "Three times daily", "route": "PO", "duration": "7 days", "notes": "Broad-spectrum antibiotic — complete full course even if feeling better. Take with food"},
            {"name": "Paracetamol (Acetaminophen)", "dose": "1000 mg", "frequency": "Every 6 hours as needed", "route": "PO", "duration": "5 days or until fever resolves", "notes": "Reduces fever and pain — max 4 doses per day. Do not exceed 4g/day"},
            {"name": "Ibuprofen", "dose": "400 mg", "frequency": "Every 8 hours with food", "route": "PO", "duration": "5 days", "notes": "Alternating with paracetamol can better control high fever. Avoid if kidney problems"},
            {"name": "Oral Rehydration Salts (ORS)", "dose": "1 sachet in 200ml water", "frequency": "After each episode of sweating/vomiting", "route": "PO", "duration": "Until fever resolves", "notes": "Replaces electrolytes lost through sweating and fever — critical to prevent dehydration"},
        ],
        "instructions": (
            "1. Take your temperature every 4 hours — return to ED if fever exceeds 39.5°C (103°F) "
            "or if you develop neck stiffness, confusion, or a rash.\n"
            "2. Complete your full antibiotic course — stopping early causes resistance and relapse.\n"
            "3. Drink at least 2–3 litres of fluid daily to stay hydrated.\n"
            "4. Stay home and rest — avoid contact with vulnerable individuals (elderly, newborns, immunocompromised).\n"
            "5. Return to ED immediately if you feel significantly worse, develop difficulty breathing, "
            "or cannot keep fluids down.\n"
            "6. Wash hands frequently — infection control is important for household members."
        ),
        "follow_up": "GP review in 48–72 hours to assess treatment response. Blood culture results available in 48–72 hours — your GP will contact you if results require treatment change. Return to ED if fever does not improve within 48 hours of antibiotics.",
        "diet": (
            "High-fluid diet essential: water, clear broths, coconut water, diluted fruit juices. "
            "Aim for 2–3 litres of fluid daily. "
            "Eat light, easily digestible foods: soups, toast, rice, fruit. "
            "Vitamin C-rich foods (oranges, kiwi, berries) support immune function. "
            "Avoid alcohol completely during infection and antibiotic course."
        ),
        "activity": (
            "Complete rest while feverish — the body needs energy for immune response. "
            "Return to light activity only when fever has been absent for 24 hours. "
            "Avoid going to work or school while infectious. "
            "Sleep is the most important recovery tool — aim for 9–10 hours nightly. "
            "Avoid strenuous exercise for 2 weeks after significant infection to prevent relapse."
        ),
    },

    "TRAUMA": {
        "labs": [
            {"name": "CBC + Coagulation Studies (PT/INR/aPTT)", "urgency": "STAT", "timing": "Immediately", "notes": "Assess blood loss and clotting ability"},
            {"name": "CMP (Metabolic Panel)", "urgency": "STAT", "timing": "Within 2 hours", "notes": "Kidney function and electrolytes post-trauma"},
            {"name": "X-Ray of Affected Area", "urgency": "STAT", "timing": "Within 1 hour", "notes": "Rule out fractures — bring previous X-rays if available"},
            {"name": "CT Head (if head injury)", "urgency": "STAT", "timing": "Within 30 minutes", "notes": "Rule out intracranial bleeding — mandatory if loss of consciousness occurred"},
            {"name": "Urinalysis", "urgency": "ASAP", "timing": "Within 2 hours", "notes": "Blood in urine may indicate kidney trauma"},
        ],
        "medications": [
            {"name": "Paracetamol (Acetaminophen)", "dose": "1000 mg", "frequency": "Every 6 hours", "route": "PO", "duration": "7 days", "notes": "First-line pain relief — safe for all ages. Max 4g/day"},
            {"name": "Ibuprofen", "dose": "400 mg", "frequency": "Every 8 hours with food", "route": "PO", "duration": "5–7 days", "notes": "For pain and swelling reduction — avoid if stomach ulcers or kidney injury"},
            {"name": "Tetanus Toxoid (if open wound)", "dose": "0.5 mL single dose", "frequency": "One-time dose", "route": "IM", "duration": "Single dose", "notes": "Required if tetanus vaccination not up to date in last 5 years"},
            {"name": "Topical Antibiotic Ointment (Bacitracin)", "dose": "Apply thin layer", "frequency": "Twice daily", "route": "Topical", "duration": "Until wound heals", "notes": "For open wounds or lacerations — keep covered with clean dressing"},
        ],
        "instructions": (
            "1. Apply ice wrapped in a cloth (never directly on skin) for 20 minutes on, 20 minutes off "
            "for the first 48 hours to reduce swelling.\n"
            "2. Elevate the injured limb above heart level when resting to reduce swelling.\n"
            "3. Do NOT return to sport or strenuous activity until cleared by your doctor or physiotherapist.\n"
            "4. Watch for danger signs — return to ED immediately if: numbness/tingling in limb, "
            "limb turns cold or pale, pain suddenly worsens, confusion or persistent vomiting after head injury.\n"
            "5. For head injuries: have someone wake you every 2 hours for the first night. "
            "Return to ED if vomiting, confusion, or unequal pupils develop.\n"
            "6. Keep wounds clean and dry — change dressings daily and watch for signs of infection "
            "(redness spreading, pus, increasing warmth)."
        ),
        "follow_up": "GP or orthopaedics review in 5–7 days. If fracture confirmed, orthopaedic clinic within 3 days. Physiotherapy referral will be made at follow-up. Return to ED if pain worsens or new symptoms develop.",
        "diet": (
            "Protein-rich diet to support tissue repair: eggs, chicken, fish, legumes, dairy. "
            "Vitamin C (citrus fruits, berries) promotes collagen formation and wound healing. "
            "Calcium and Vitamin D foods (dairy, leafy greens, sunlight) support bone healing. "
            "Stay well hydrated — at least 2 litres of water daily. "
            "Avoid alcohol — it slows healing and increases bleeding risk."
        ),
        "activity": (
            "RICE protocol for first 48 hours: Rest, Ice, Compression, Elevation. "
            "Protect the injured area from further strain. "
            "Use prescribed crutches, sling, or splint as directed — wear it as instructed. "
            "Gradually increase mobility as pain allows, guided by physiotherapist. "
            "No return to sport or heavy work until cleared at follow-up appointment."
        ),
    },

    "DIABETIC_EMERGENCY": {
        "labs": [
            {"name": "Blood Glucose (Bedside Glucometer)", "urgency": "STAT", "timing": "Immediately and every hour until stable", "notes": "Target range: 4–10 mmol/L (72–180 mg/dL) during stabilisation"},
            {"name": "HbA1c (Glycated Haemoglobin)", "urgency": "ASAP", "timing": "Within 24 hours", "notes": "Reflects 3-month average glucose — key for long-term management review"},
            {"name": "Serum Ketones / Urinalysis (Ketones)", "urgency": "STAT", "timing": "Within 1 hour", "notes": "Elevated ketones = DKA risk — critical to identify early"},
            {"name": "CMP (Renal Function + Electrolytes)", "urgency": "STAT", "timing": "Within 1 hour", "notes": "Potassium levels are critical in DKA — must be corrected before insulin"},
            {"name": "Thyroid Function (TSH)", "urgency": "Routine", "timing": "Within 48 hours", "notes": "Thyroid disorders commonly worsen glucose control"},
        ],
        "medications": [
            {"name": "Insulin (as prescribed — Basal/Bolus)", "dose": "Per individual sliding scale", "frequency": "As directed by your diabetes team", "route": "SQ", "duration": "Ongoing", "notes": "NEVER skip insulin doses. If sick and not eating, contact diabetes team immediately — 'sick day rules' apply"},
            {"name": "Metformin 500 mg (Type 2 only)", "dose": "500 mg", "frequency": "Twice daily with meals", "route": "PO", "duration": "Ongoing", "notes": "Stop metformin if vomiting, dehydrated, or having a procedure with contrast dye"},
            {"name": "Glucose Gel / Dextrose Tablets", "dose": "15g fast-acting glucose", "frequency": "Immediately for blood sugar <4 mmol/L (<70 mg/dL)", "route": "PO", "duration": "As needed (hypoglycaemia treatment)", "notes": "Always carry glucose tablets. After treating low, eat a snack with slow carbs (crackers, peanut butter)"},
            {"name": "Glucagon Emergency Kit", "dose": "1 mg", "frequency": "One-time for severe hypoglycaemia (unconscious)", "route": "IM", "duration": "Emergency use only", "notes": "Teach a family member how to use this. Call 999/911 after using"},
        ],
        "instructions": (
            "1. Check blood glucose before meals and at bedtime. Keep a log to share with your diabetes team.\n"
            "2. Know your hypoglycaemia symptoms: shakiness, sweating, confusion, pale skin. "
            "Treat immediately with 15g fast-acting glucose (glucose gel, 3–4 glucose tablets, or 150ml fruit juice).\n"
            "3. If blood sugar is below 4 mmol/L (70 mg/dL) twice in one week, contact your diabetes nurse.\n"
            "4. Sick day rules: if vomiting or unable to eat, contact your diabetes team before adjusting insulin.\n"
            "5. Check your feet daily for cuts, blisters, or sores — diabetics have reduced sensation.\n"
            "6. Wear a medical alert bracelet or carry a diabetes ID card at all times."
        ),
        "follow_up": "Diabetes nurse/educator appointment within 1 week. Endocrinologist review in 4 weeks to adjust medication. Annual diabetic eye exam, foot exam, and kidney function test due — confirm with your GP.",
        "diet": (
            "Carbohydrate-consistent meals (45–60g carbs per meal) at regular times — avoid skipping meals. "
            "Choose low glycaemic index (GI) foods: oats, lentils, beans, non-starchy vegetables. "
            "Avoid sugary drinks, sweets, white bread, and refined carbohydrates. "
            "Protein with each meal slows glucose absorption: eggs, chicken, fish, tofu, nuts. "
            "Alcohol can cause dangerous hypoglycaemia — limit strictly and always eat when drinking."
        ),
        "activity": (
            "Regular moderate exercise significantly improves insulin sensitivity. "
            "Aim for 30 minutes of brisk walking or cycling 5 days/week. "
            "Check blood glucose before and after exercise — carry glucose tablets during exercise. "
            "Avoid exercise if blood glucose is >14 mmol/L (252 mg/dL) or ketones are present. "
            "Wear proper footwear during exercise — inspect feet carefully afterwards."
        ),
    },

    "ARRHYTHMIA": {
        "labs": [
            {"name": "ECG (12-lead)", "urgency": "STAT", "timing": "Within 10 minutes of arrival", "notes": "Identify exact rhythm — essential for diagnosis"},
            {"name": "CMP with Magnesium", "urgency": "STAT", "timing": "Within 1 hour", "notes": "Electrolyte imbalances (low potassium, magnesium) trigger arrhythmias"},
            {"name": "Thyroid Function (TSH, Free T4)", "urgency": "ASAP", "timing": "Within 24 hours", "notes": "Hyperthyroidism is a common cause of atrial fibrillation"},
            {"name": "Troponin I", "urgency": "ASAP", "timing": "Within 2 hours, repeat at 4 hours", "notes": "Rule out myocardial infarction as trigger for arrhythmia"},
            {"name": "Echocardiogram (Heart Echo)", "urgency": "Routine", "timing": "Within 1 week as outpatient", "notes": "Assess heart structure and function — required before cardioversion if AF persists"},
        ],
        "medications": [
            {"name": "Bisoprolol (Beta-blocker)", "dose": "2.5–5 mg", "frequency": "Once daily (morning)", "route": "PO", "duration": "Ongoing", "notes": "Slows heart rate — do not stop abruptly; gradually taper if ever stopping"},
            {"name": "Apixaban (Eliquis) — if AF confirmed", "dose": "5 mg", "frequency": "Twice daily", "route": "PO", "duration": "Ongoing", "notes": "Blood thinner for stroke prevention in atrial fibrillation. Do not miss doses. Watch for unusual bruising or bleeding"},
            {"name": "Magnesium Glycinate", "dose": "400 mg", "frequency": "Once daily at bedtime", "route": "PO", "duration": "3 months then review", "notes": "Supports heart rhythm stability — particularly beneficial if magnesium was low"},
            {"name": "Digoxin (if prescribed for rate control)", "dose": "62.5–125 mcg", "frequency": "Once daily", "route": "PO", "duration": "Ongoing", "notes": "Narrow therapeutic window — do not take double dose. Report nausea, visual changes, or extreme bradycardia immediately"},
        ],
        "instructions": (
            "1. Take all heart rhythm medications at the same time each day — consistency is critical.\n"
            "2. If taking a blood thinner (anticoagulant): watch for unusual bruising, prolonged bleeding "
            "from cuts, blood in urine/stool, or severe headache — seek emergency care immediately.\n"
            "3. Monitor your pulse daily — place two fingers on your wrist or neck for 60 seconds. "
            "Report to your doctor if rate is consistently >100 or <50 beats per minute.\n"
            "4. Avoid caffeine, alcohol, and energy drinks — all can trigger palpitations.\n"
            "5. Manage stress: chronic anxiety and stress are major palpitation triggers.\n"
            "6. Wear a medical alert ID if you are on anticoagulant therapy."
        ),
        "follow_up": "Cardiology clinic within 1 week. Holter monitor (24–48h heart rhythm recorder) will be arranged. Echocardiogram within 1 week. If atrial fibrillation confirmed, rate/rhythm control plan to be finalised at cardiology review.",
        "diet": (
            "Limit caffeine (coffee, tea, cola, energy drinks) — a maximum of 1 cup of coffee per day. "
            "Avoid alcohol — even small amounts can trigger AF episodes in susceptible individuals. "
            "Potassium-rich foods (bananas, avocado, potatoes) support heart rhythm. "
            "Magnesium-rich foods (dark chocolate, nuts, spinach, seeds) reduce arrhythmia risk. "
            "Stay well hydrated — dehydration stresses the heart."
        ),
        "activity": (
            "Avoid strenuous exercise until cardiologist review confirms it is safe. "
            "Gentle walking (20–30 min daily) is generally safe and beneficial. "
            "Avoid activities with high fall risk if on blood thinners. "
            "Practice stress-reduction techniques: yoga, meditation, or deep breathing exercises. "
            "Avoid vigorous exercise within 2 hours of any palpitation episode."
        ),
    },

    "URINARY_RENAL": {
        "labs": [
            {"name": "Urinalysis with Microscopy", "urgency": "STAT", "timing": "Within 1 hour", "notes": "Confirms infection — look for nitrites, leukocytes, blood"},
            {"name": "Urine Culture and Sensitivity", "urgency": "ASAP", "timing": "Within 2 hours — collect midstream clean catch", "notes": "Identifies exact bacteria and best antibiotic — results in 24–48 hours"},
            {"name": "CMP (Renal Function)", "urgency": "ASAP", "timing": "Within 2 hours", "notes": "Assess kidney function — creatinine and eGFR"},
            {"name": "CBC with Differential", "urgency": "ASAP", "timing": "Within 2 hours", "notes": "Rule out systemic infection or anaemia"},
            {"name": "Renal Ultrasound (if stone suspected)", "urgency": "Routine", "timing": "Within 48 hours as outpatient", "notes": "Identify kidney stones, obstruction, or structural abnormalities"},
        ],
        "medications": [
            {"name": "Trimethoprim", "dose": "200 mg", "frequency": "Twice daily", "route": "PO", "duration": "7 days (uncomplicated UTI)", "notes": "First-line UTI antibiotic — take with food, complete full course"},
            {"name": "Nitrofurantoin (if Trimethoprim resistant)", "dose": "100 mg (modified release)", "frequency": "Twice daily", "route": "PO", "duration": "5–7 days", "notes": "Take with food to reduce nausea. Not suitable if eGFR <30"},
            {"name": "Paracetamol (Acetaminophen)", "dose": "1000 mg", "frequency": "Every 6 hours as needed", "route": "PO", "duration": "3–5 days", "notes": "For pain and discomfort. Safe for kidneys unlike NSAIDs"},
            {"name": "Tamsulosin (if kidney stone)", "dose": "0.4 mg", "frequency": "Once daily at bedtime", "route": "PO", "duration": "Until stone passes (up to 4 weeks)", "notes": "Relaxes ureter muscles to help stone pass — may cause dizziness on standing up"},
        ],
        "instructions": (
            "1. Drink 2–3 litres of water daily — this is the single most important thing for UTI and kidney stone recovery.\n"
            "2. Complete your full antibiotic course even if symptoms improve in 1–2 days.\n"
            "3. Urinate frequently — do not 'hold' urine as this allows bacteria to multiply.\n"
            "4. Wipe front to back after using the toilet to prevent reinfection.\n"
            "5. Return to ED immediately if: high fever (>38.5°C), severe flank/back pain, "
            "shivering and rigors, vomiting that prevents fluid intake.\n"
            "6. Avoid bubble baths, scented soaps, and tight synthetic underwear — these increase UTI risk."
        ),
        "follow_up": "GP review in 5–7 days with urine culture results. If recurrent UTI (3rd episode this year), referral to urology for investigation. Kidney stone follow-up with urology in 2 weeks if stone >5mm or not passed.",
        "diet": (
            "Drink at least 2–3 litres of water daily — light yellow urine is the goal. "
            "Cranberry juice (unsweetened) may reduce UTI recurrence — 300ml daily. "
            "Avoid high oxalate foods if kidney stones present (spinach, rhubarb, nuts, chocolate). "
            "Low sodium diet (<2g/day) reduces calcium in urine and stone formation risk. "
            "Limit animal protein if uric acid stones confirmed on analysis."
        ),
        "activity": (
            "Rest during acute UTI or kidney stone pain. "
            "Gentle walking and movement help kidney stones pass by gravity. "
            "Warm bath or heat pack on lower back/abdomen can relieve stone pain. "
            "Avoid swimming in public pools during active UTI. "
            "Return to normal activity once antibiotic course is complete and symptoms resolved."
        ),
    },

    "HEADACHE": {
        "labs": [
            {"name": "Blood Pressure Measurement (serial)", "urgency": "STAT", "timing": "Immediately and every 30 minutes", "notes": "Hypertensive headache is dangerous — SBP >180 requires urgent treatment"},
            {"name": "CT Head Without Contrast", "urgency": "STAT", "timing": "Within 30 minutes if thunderclap/worst-ever headache", "notes": "Rule out subarachnoid haemorrhage — mandatory for 'worst headache of life'"},
            {"name": "CBC, CMP", "urgency": "ASAP", "timing": "Within 2 hours", "notes": "Anaemia and metabolic causes of headache"},
            {"name": "ESR and CRP (if over 50 years old)", "urgency": "ASAP", "timing": "Within 2 hours", "notes": "Rule out giant cell arteritis — causes severe headache + visual loss in elderly"},
            {"name": "Eye Examination (Fundoscopy)", "urgency": "ASAP", "timing": "During the visit", "notes": "Papilloedema indicates raised intracranial pressure — emergency"},
        ],
        "medications": [
            {"name": "Sumatriptan (Imigran)", "dose": "50 mg", "frequency": "At onset of migraine — may repeat once after 2 hours if partial relief", "route": "PO", "duration": "As needed for migraine", "notes": "Triptan for migraine attack. Take as early as possible in attack. Max 2 doses per 24h. Do not use if cardiovascular disease"},
            {"name": "Ibuprofen", "dose": "400–600 mg", "frequency": "At onset, repeat after 6 hours if needed", "route": "PO", "duration": "2–3 days maximum during attack", "notes": "Take with food. Avoid overuse (>10 days/month) — causes medication-overuse headache"},
            {"name": "Paracetamol (Acetaminophen)", "dose": "1000 mg", "frequency": "Every 6 hours as needed", "route": "PO", "duration": "During attack", "notes": "Safer option for frequent headaches. Avoid alcohol while taking"},
            {"name": "Topiramate (Migraine Preventer — if frequent)", "dose": "25 mg", "frequency": "Once daily initially — titrate up with GP", "route": "PO", "duration": "3–6 months minimum", "notes": "Preventative medication — must be taken daily even on headache-free days. Takes 4–8 weeks to work"},
        ],
        "instructions": (
            "1. Identify and avoid your migraine triggers: bright lights, stress, dehydration, "
            "skipped meals, hormonal changes, alcohol, strong smells.\n"
            "2. Keep a headache diary — record trigger, duration, severity, and medication used. "
            "Share this with your neurologist.\n"
            "3. Take your migraine medication as early as possible when symptoms start — waiting makes it less effective.\n"
            "4. Rest in a dark, quiet room during a migraine attack.\n"
            "5. Seek emergency care immediately if: worst headache of your life, fever + headache + stiff neck, "
            "confusion, vision changes, headache after head injury, or sudden onset thunderclap headache.\n"
            "6. Avoid sleeping more than 8 hours or less than 6 hours — irregular sleep triggers migraines."
        ),
        "follow_up": "GP review in 1 week to discuss preventative treatment if migraines occur >4 times/month. Neurology outpatient referral if diagnosis unclear or complex. Ophthalmology review if visual symptoms present.",
        "diet": (
            "Stay well hydrated — dehydration is the most common migraine trigger (8 glasses water daily). "
            "Eat regular meals and never skip breakfast — blood sugar drops trigger migraines. "
            "Common food triggers to test eliminating: red wine, aged cheese, chocolate, processed meats, MSG. "
            "Keep a food-headache diary to identify your personal triggers. "
            "Limit caffeine — sudden caffeine withdrawal also triggers migraines, so reduce gradually."
        ),
        "activity": (
            "Rest in a dark, quiet room during an active migraine — sleep often provides the most relief. "
            "Apply cold pack or ice to forehead or neck during attack. "
            "Regular aerobic exercise (30 min, 3x/week) reduces migraine frequency over time. "
            "Avoid overexertion and exercising in extreme heat — known migraine triggers. "
            "Yoga, mindfulness, and biofeedback are evidence-based complementary treatments for prevention."
        ),
    },

    "DIZZINESS": {
        "labs": [
            {"name": "Blood Glucose (Bedside)", "urgency": "STAT", "timing": "Immediately", "notes": "Hypoglycaemia is a common and easily reversible cause of dizziness"},
            {"name": "CBC", "urgency": "ASAP", "timing": "Within 2 hours", "notes": "Rule out anaemia as cause of dizziness and light-headedness"},
            {"name": "CMP (Electrolytes + Renal Function)", "urgency": "ASAP", "timing": "Within 2 hours", "notes": "Sodium and potassium imbalances cause dizziness"},
            {"name": "ECG (12-lead)", "urgency": "ASAP", "timing": "Within 30 minutes", "notes": "Cardiac arrhythmia can present as dizziness — must exclude"},
            {"name": "Blood Pressure (lying and standing)", "urgency": "STAT", "timing": "Immediately", "notes": "Orthostatic hypotension: BP drop >20 systolic on standing confirms diagnosis"},
        ],
        "medications": [
            {"name": "Prochlorperazine (Stemetil)", "dose": "5 mg", "frequency": "Three times daily as needed", "route": "PO", "duration": "5–7 days", "notes": "For vertigo and nausea — may cause drowsiness. Do not drive or operate machinery"},
            {"name": "Betahistine (Serc) — if Meniere's/vestibular", "dose": "16 mg", "frequency": "Three times daily with food", "route": "PO", "duration": "3 months then review", "notes": "Takes 2–4 weeks to show benefit. Take consistently. Continue even on symptom-free days"},
            {"name": "Cinnarizine", "dose": "15 mg", "frequency": "Three times daily", "route": "PO", "duration": "2–4 weeks", "notes": "Motion sickness and vestibular dizziness. Avoid alcohol — increases drowsiness"},
            {"name": "Fludrocortisone (if postural hypotension)", "dose": "0.1 mg", "frequency": "Once daily", "route": "PO", "duration": "As directed — review in 4 weeks", "notes": "Increases blood pressure. Monitor BP at home. May cause ankle swelling"},
        ],
        "instructions": (
            "1. Move slowly when changing position — sit on the edge of the bed for 1 minute before standing.\n"
            "2. Do not drive or operate heavy machinery while experiencing dizziness or taking anti-vertigo medication.\n"
            "3. Use grab rails, remove rugs, and ensure good lighting to prevent falls at home.\n"
            "4. Drink adequate fluids (2 litres/day) — dehydration worsens dizziness.\n"
            "5. Avoid alcohol and caffeine — both can worsen balance and dizziness.\n"
            "6. Return to ED immediately if dizziness is accompanied by: sudden severe headache, "
            "double vision, face drooping, arm weakness, slurred speech, or chest pain."
        ),
        "follow_up": "GP review in 1 week. ENT (ear, nose, and throat) referral if vertigo suspected. Neurology referral if neurological cause suspected. Vestibular rehabilitation therapy referral for persistent dizziness.",
        "diet": (
            "Maintain adequate salt intake (unless hypertensive) — low-salt diet worsens postural hypotension. "
            "Stay well hydrated: 2–2.5 litres of fluid daily. "
            "Eat regular small meals — large meals can cause blood pressure drop after eating. "
            "Low-caffeine diet recommended — caffeine can worsen vestibular disorders. "
            "Avoid alcohol completely during active vertigo episodes."
        ),
        "activity": (
            "Avoid heights, ladders, and activities requiring precise balance until dizziness resolves. "
            "Epley manoeuvre (repositioning technique for BPPV) can be taught by your physiotherapist — very effective for inner-ear vertigo. "
            "Vestibular rehabilitation exercises improve brain adaptation to balance problems over time. "
            "Use a walking aid (stick) if dizziness causes unsteadiness and fall risk. "
            "Gradually increase activity as tolerated — avoid sudden head movements initially."
        ),
    },

    "MENTAL_HEALTH": {
        "labs": [
            {"name": "Thyroid Function (TSH, Free T4)", "urgency": "Routine", "timing": "Within 48 hours", "notes": "Thyroid disorders cause or worsen depression and anxiety — essential to rule out"},
            {"name": "CBC", "urgency": "Routine", "timing": "Within 48 hours", "notes": "Anaemia commonly causes fatigue and worsens low mood"},
            {"name": "Vitamin D Level (25-OH)", "urgency": "Routine", "timing": "Within 48 hours", "notes": "Vitamin D deficiency is strongly linked to depression"},
            {"name": "Vitamin B12 and Folate", "urgency": "Routine", "timing": "Within 48 hours", "notes": "B12 and folate deficiency cause neurological and mood symptoms"},
            {"name": "Blood Glucose (Fasting)", "urgency": "Routine", "timing": "Within 48 hours", "notes": "Diabetic conditions significantly impact mood and mental health"},
        ],
        "medications": [
            {"name": "Sertraline (Zoloft)", "dose": "50 mg", "frequency": "Once daily (morning with food)", "route": "PO", "duration": "Minimum 6 months — review with psychiatrist", "notes": "Takes 4–6 weeks to notice full effect. Do not stop abruptly — always taper under supervision"},
            {"name": "Mirtazapine (if sleep problems prominent)", "dose": "15 mg", "frequency": "Once daily at bedtime", "route": "PO", "duration": "Minimum 6 months", "notes": "Taken at night — improves sleep and appetite. Causes drowsiness initially"},
            {"name": "Lorazepam (short-term, if acute anxiety)", "dose": "0.5–1 mg", "frequency": "As needed for acute anxiety (max 3 days)", "route": "PO", "duration": "Short-term only — 3 days maximum", "notes": "Risk of dependence — not for regular or long-term use. Do not drive or drink alcohol"},
            {"name": "Vitamin D3", "dose": "1000–2000 IU", "frequency": "Once daily with the largest meal", "route": "PO", "duration": "3 months then repeat level", "notes": "Take with food containing fat for best absorption — supports mood and bone health"},
        ],
        "instructions": (
            "1. If you are having thoughts of harming yourself: call the Crisis Helpline immediately "
            "(988 in the US / 116 123 Samaritans in the UK) or go to your nearest emergency department.\n"
            "2. Share your medication plan with a trusted family member or friend who can support you.\n"
            "3. Antidepressants take 4–6 weeks to show full effect — do not stop if you don't feel "
            "better immediately. Missing doses can cause withdrawal symptoms.\n"
            "4. Attend all therapy appointments — talking therapy (CBT) combined with medication "
            "is more effective than either alone.\n"
            "5. Establish a daily routine: regular sleep times, meals, and light outdoor activity "
            "significantly improve mood over time.\n"
            "6. Reach out to your crisis contact or emergency services immediately if thoughts "
            "of self-harm intensify or you make a plan."
        ),
        "follow_up": "Psychiatry or GP mental health review within 1 week. Community mental health team (CMHT) referral if complex needs. Cognitive Behavioural Therapy (CBT) referral — usually 8–12 sessions. Crisis team contact details provided at discharge.",
        "diet": (
            "Mediterranean-style diet is evidence-based for mental health: "
            "olive oil, fish (omega-3), nuts, colourful vegetables, whole grains, legumes. "
            "Avoid ultra-processed foods, refined sugars, and high-fructose corn syrup — they worsen mood and energy. "
            "Fermented foods (yogurt, kefir, kimchi) support gut-brain axis and serotonin production. "
            "Limit alcohol — it is a depressant and worsens anxiety and depression significantly. "
            "Regular meal times stabilise blood sugar and prevent mood swings."
        ),
        "activity": (
            "Exercise is as effective as antidepressants for mild-moderate depression: "
            "aim for 30 minutes of aerobic activity 5 days/week (walking, cycling, swimming). "
            "Outdoor exercise in natural light is particularly beneficial for mood. "
            "Start small — even a 10-minute walk matters. Gradually increase. "
            "Group activities (classes, walking groups) reduce isolation alongside physical benefits. "
            "Avoid alcohol and recreational drugs — they destabilise mood and counteract treatment."
        ),
    },

    "JOINT_PAIN": {
        "labs": [
            {"name": "CRP (C-Reactive Protein) and ESR", "urgency": "ASAP", "timing": "Within 24 hours", "notes": "Inflammatory markers — elevated in rheumatoid arthritis and septic arthritis"},
            {"name": "Rheumatoid Factor (RF) and Anti-CCP Antibodies", "urgency": "Routine", "timing": "Within 48 hours", "notes": "Diagnostic for rheumatoid arthritis — if not previously tested"},
            {"name": "Uric Acid (Urate) Level", "urgency": "ASAP", "timing": "Within 24 hours", "notes": "Elevated in gout — classic cause of acute joint pain with swelling"},
            {"name": "CBC + CMP", "urgency": "Routine", "timing": "Within 48 hours", "notes": "Baseline before starting anti-inflammatory medications"},
            {"name": "X-Ray of Affected Joint(s)", "urgency": "Routine", "timing": "Within 48 hours", "notes": "Assess joint space, erosions, or fracture"},
        ],
        "medications": [
            {"name": "Ibuprofen (NSAID)", "dose": "400–600 mg", "frequency": "Three times daily with food", "route": "PO", "duration": "7–14 days for flare", "notes": "Most effective anti-inflammatory — take with food to protect stomach. Avoid if kidney disease"},
            {"name": "Omeprazole (Stomach Protection)", "dose": "20 mg", "frequency": "Once daily before breakfast", "route": "PO", "duration": "While taking ibuprofen", "notes": "Always take alongside NSAIDs to prevent stomach ulcers"},
            {"name": "Methotrexate (if RA — ongoing DMARD)", "dose": "As previously prescribed", "frequency": "Once weekly (same day each week)", "route": "PO", "duration": "Ongoing — review with rheumatologist", "notes": "Take with folic acid supplement. Weekly blood tests required. Avoid alcohol completely"},
            {"name": "Naproxen Sodium (alternative NSAID)", "dose": "500 mg", "frequency": "Twice daily with food", "route": "PO", "duration": "7–14 days for flare", "notes": "Longer-acting alternative to ibuprofen. Take consistently with meals"},
        ],
        "instructions": (
            "1. Rest the affected joint during acute pain — but gentle range-of-motion exercises "
            "prevent stiffness.\n"
            "2. Apply ice pack (wrapped in cloth) for 15–20 minutes, 3–4 times daily during "
            "acute flare to reduce swelling.\n"
            "3. After 48 hours, switch to warmth (heat pack or warm bath) to ease stiffness "
            "and improve mobility.\n"
            "4. Take NSAIDs (ibuprofen) with food and never on an empty stomach — always pair "
            "with a stomach protector (omeprazole).\n"
            "5. If on methotrexate: never miss your weekly blood test. Avoid alcohol completely. "
            "Seek urgent care for fever, mouth sores, or shortness of breath.\n"
            "6. Maintain a healthy weight — each extra 5 lbs adds 15–20 lbs of force on knee joints."
        ),
        "follow_up": "Rheumatology review within 4 weeks. Physiotherapy assessment for joint rehabilitation within 2 weeks. If gout confirmed, urology dietitian referral. Annual medication safety bloods if on DMARDs.",
        "diet": (
            "Anti-inflammatory diet for joint health: oily fish (salmon, sardines, mackerel) 3x/week, "
            "olive oil, turmeric, ginger, berries, leafy greens. "
            "If gout: strict low-purine diet — avoid red meat, organ meats, shellfish, beer, and sugary drinks. "
            "Adequate hydration (2+ litres/day) reduces uric acid crystal formation. "
            "Vitamin D and calcium foods support bone health around joints: dairy, fortified plant milks, eggs. "
            "Achieve/maintain healthy weight — obesity is the biggest modifiable risk factor for osteoarthritis."
        ),
        "activity": (
            "RICE during acute flare: Rest, Ice, Compression (bandage), Elevation. "
            "Low-impact exercise is best for joints long-term: swimming, cycling, water aerobics, tai chi. "
            "Avoid high-impact activities (running, jumping) during flares and if cartilage damage confirmed. "
            "Physiotherapy exercises strengthen muscles around the joint — reducing pain and slowing progression. "
            "Use walking aids (sticks, splints) during flares to protect the affected joint."
        ),
    },
}

# ── Default fallback for unmatched symptoms ───────────────────────────────────

_DEFAULT_PLAN: Dict[str, Any] = {
    "labs": [
        {"name": "CBC with Differential", "urgency": "Routine", "timing": "Within 48 hours", "notes": "General health screen"},
        {"name": "Comprehensive Metabolic Panel (CMP)", "urgency": "Routine", "timing": "Within 48 hours", "notes": "Organ function and electrolytes"},
        {"name": "Blood Glucose (Fasting)", "urgency": "Routine", "timing": "Next morning fasting draw", "notes": "Baseline metabolic check"},
    ],
    "medications": [
        {"name": "Paracetamol (Acetaminophen)", "dose": "1000 mg", "frequency": "Every 6 hours as needed", "route": "PO", "duration": "5 days", "notes": "For pain or discomfort. Max 4 doses per day. Do not exceed 4g/day"},
    ],
    "instructions": (
        "1. Take medications as prescribed and complete any courses fully.\n"
        "2. Stay well hydrated — drink at least 2 litres of water daily.\n"
        "3. Rest adequately and avoid overexertion.\n"
        "4. Monitor your symptoms and seek emergency care if they worsen significantly.\n"
        "5. Follow up with your GP as scheduled."
    ),
    "follow_up": "GP follow-up within 1 week. Return to ED if symptoms significantly worsen or new symptoms develop.",
    "diet": (
        "Balanced diet with plenty of fruits, vegetables, whole grains, and lean protein. "
        "Stay hydrated with 2+ litres of water daily. "
        "Limit processed foods, alcohol, and excessive caffeine."
    ),
    "activity": (
        "Rest as needed. "
        "Return to normal activity gradually as symptoms allow. "
        "Avoid strenuous exercise until you feel fully recovered."
    ),
}


# ── Main public function ──────────────────────────────────────────────────────

def build_fallback_care_plan(
    symptoms: str,
    patient_id: str = "UNKNOWN",
    doctor_id: str = "DR001",
) -> Dict[str, Any]:
    """
    Generate a symptom-matched care plan from keyword detection.

    Args:
        symptoms: Free-text symptoms string (e.g. "chest pain, shortness of breath")
        patient_id: Patient identifier
        doctor_id: Approving doctor identifier

    Returns:
        Care plan dict with keys: patient_id, doctor_id, approved_at,
        shared_with_staff, shared_with_patient, labs, medications,
        instructions, follow_up, diet, activity
    """
    symptoms_lower = symptoms.lower()

    # Match the first condition template whose keywords appear in symptoms
    matched_condition = None
    for entry in CONDITION_TEMPLATES:
        if any(kw in symptoms_lower for kw in entry["keywords"]):
            matched_condition = entry["condition"]
            break

    plan = _CARE_PLANS.get(matched_condition, _DEFAULT_PLAN)

    return {
        "patient_id":          patient_id,
        "doctor_id":           doctor_id,
        "approved_at":         datetime.now().isoformat(),
        "shared_with_staff":   True,
        "shared_with_patient": True,
        "labs":                plan["labs"],
        "medications":         plan["medications"],
        "instructions":        plan["instructions"],
        "follow_up":           plan["follow_up"],
        "diet":                plan["diet"],
        "activity":            plan["activity"],
    }
