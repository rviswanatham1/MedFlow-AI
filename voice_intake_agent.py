"""
Voice Intake Agent

Processes patient voice/text input at ED arrival or 911 call.
Scores voice quality signals (coherence, distress, pace, clarity)
and extracts structured symptom information from the transcript.

No external audio library needed — accepts text transcripts with optional
STT metadata. Voice quality is inferred from lexical and structural features.
"""

import re
import math
from datetime import datetime
from typing import Optional, Dict, Any, List, Literal

from pydantic import BaseModel, Field


# ============================================================================
# VOCABULARY & SIGNAL DICTIONARIES
# ============================================================================

DISTRESS_MARKERS = {
    # High-weight (0.3 each)
    "can't breathe": 0.30, "cannot breathe": 0.30, "dying": 0.30,
    "i'm dying": 0.30, "help me": 0.30, "please help": 0.25,
    "worst pain": 0.25, "unbearable": 0.25, "crushing": 0.25,
    "severe": 0.20, "excruciating": 0.25, "agony": 0.25,
    # Medium-weight (0.15 each)
    "chest pain": 0.15, "can't move": 0.15, "can't walk": 0.15,
    "bleeding": 0.15, "collapsed": 0.15, "passed out": 0.15,
    "blacked out": 0.15, "seizing": 0.20, "seizure": 0.20,
    "stroke": 0.20, "can't speak": 0.15, "slurred": 0.15,
    "heart attack": 0.20, "not breathing": 0.30,
    # Low-weight (0.05–0.10)
    "really bad": 0.08, "scared": 0.08, "worried": 0.05,
    "hurt": 0.05, "pain": 0.05, "nausea": 0.05, "vomiting": 0.08,
    "dizzy": 0.08, "faint": 0.10, "weak": 0.08,
}

# Maps symptom phrases to canonical clinical terms
SYMPTOM_VOCABULARY: Dict[str, str] = {
    # Chest
    "chest pain": "chest pain", "chest hurts": "chest pain",
    "chest tightness": "chest tightness", "chest pressure": "chest pressure",
    "palpitations": "palpitations", "heart racing": "palpitations",
    "heart pounding": "palpitations", "irregular heartbeat": "palpitations",
    # Respiratory
    "shortness of breath": "shortness of breath",
    "can't breathe": "shortness of breath", "difficulty breathing": "shortness of breath",
    "wheezing": "wheezing", "coughing": "cough", "cough": "cough",
    "coughing blood": "hemoptysis", "blood in sputum": "hemoptysis",
    # Neurological
    "headache": "headache", "head pain": "headache",
    "worst headache": "thunderclap headache", "sudden headache": "thunderclap headache",
    "weakness": "weakness", "arm weakness": "unilateral arm weakness",
    "leg weakness": "unilateral leg weakness", "facial droop": "facial droop",
    "face drooping": "facial droop", "slurred speech": "dysarthria",
    "can't speak": "aphasia", "confusion": "confusion",
    "confused": "confusion", "dizzy": "dizziness", "dizziness": "dizziness",
    "passed out": "syncope", "blacked out": "syncope", "fainted": "syncope",
    "seizure": "seizure", "seizing": "seizure", "convulsion": "seizure",
    "vision loss": "vision loss", "blurry vision": "visual disturbance",
    # Abdominal
    "stomach pain": "abdominal pain", "belly pain": "abdominal pain",
    "abdominal pain": "abdominal pain", "nausea": "nausea",
    "vomiting": "vomiting", "throwing up": "vomiting",
    "vomiting blood": "hematemesis", "blood in vomit": "hematemesis",
    "blood in stool": "hematochezia", "black stool": "melena",
    "diarrhea": "diarrhea",
    # Trauma / Other
    "bleeding": "active bleeding", "blood": "bleeding",
    "cut": "laceration", "laceration": "laceration",
    "bruise": "contusion", "broken": "possible fracture",
    "fell": "fall injury", "hit": "trauma", "accident": "trauma",
    "burn": "burn injury",
    # Systemic
    "fever": "fever", "high temperature": "fever",
    "chills": "chills", "rigors": "rigors",
    "sweating": "diaphoresis", "sweaty": "diaphoresis",
    "rash": "rash", "swelling": "edema", "swollen": "edema",
    "back pain": "back pain",
    # Metabolic
    "low blood sugar": "hypoglycemia", "diabetic": "diabetic",
    "passed out diabetic": "hypoglycemia",
}

# Duration regex patterns (ordered most-specific first)
_DURATION_PATTERNS = [
    r"(?:for|since|about|started|began)\s+(?:the\s+)?"
    r"(\d+\s*(?:second|minute|hour|day|week|month)s?(?:\s+ago)?)",
    r"(\d+\s*(?:second|minute|hour|day|week|month)s?)\s+(?:ago|now|already)",
    r"since\s+(this\s+morning|last\s+night|yesterday|this\s+afternoon|this\s+evening)",
    r"(a few minutes|a few hours|several hours|all day|all night)",
]

_SEVERITY_PATTERNS = [
    r"(\d{1,2})\s*(?:out of|\/)\s*10",          # "8/10" or "8 out of 10"
    r"(excruciating|unbearable|agonizing|severe|moderate|mild|slight|minimal)",
]


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class VoiceQualityScores(BaseModel):
    coherence_score: float = Field(description="Logical sentence structure, 0-10")
    distress_score: float = Field(description="Distress level inferred from markers, 0-10")
    speech_pace_label: Literal["SLOW", "NORMAL", "FAST", "FRAGMENTED"] = Field(
        description="Inferred speech pace from sentence structure"
    )
    clarity_score: float = Field(description="Speech clarity from metadata or defaults, 0-10")
    overall_voice_quality: float = Field(description="Weighted composite score, 0-10")


class VoiceIntakeResult(BaseModel):
    patient_id: str
    transcript: str
    extracted_symptoms: List[str] = Field(description="Canonical symptom list from transcript")
    symptom_duration: Optional[str] = Field(default=None, description="Duration expression extracted from transcript")
    symptom_severity_self_reported: Optional[str] = Field(default=None, description="Self-reported severity scale or descriptor")
    voice_quality_scores: VoiceQualityScores
    voice_quality_score: float = Field(description="Overall voice quality (0-10); lower = more concerning")
    urgency_modifier: float = Field(
        description="Range -1.0 to +1.0. Negative = more urgent (distressed/incoherent). "
                    "Positive = less urgent (calm/clear)."
    )
    intake_timestamp: str


# ============================================================================
# SCORING FUNCTIONS
# ============================================================================

def score_coherence(transcript: str) -> float:
    """
    Score logical coherence of speech.
    Short/fragmented sentences penalise coherence; moderate sentences score well.
    """
    transcript = transcript.strip()
    if not transcript:
        return 5.0

    # Split on sentence-ending punctuation
    sentences = [s.strip() for s in re.split(r'[.?!]', transcript) if s.strip()]
    if not sentences:
        return 5.0

    word_counts = [len(s.split()) for s in sentences]
    avg_words = sum(word_counts) / len(word_counts)

    # 1–4 words per sentence → fragmented (low coherence)
    # 5–20 words → good coherence
    # > 40 words → run-on, lower coherence
    if avg_words < 3:
        base = 2.0
    elif avg_words < 6:
        base = 4.5
    elif avg_words <= 20:
        base = 8.5 - max(0, (avg_words - 20) * 0.1)
    else:
        # run-on sentences
        base = max(3.0, 8.5 - (avg_words - 20) * 0.15)

    # Penalise very few sentences (not enough info to assess)
    if len(sentences) == 1 and avg_words < 8:
        base = min(base, 5.0)

    return round(min(10.0, max(0.0, base)), 2)


def score_distress(transcript: str) -> float:
    """Score emotional/clinical distress from distress marker density."""
    if not transcript:
        return 0.0

    text_lower = transcript.lower()
    total_words = max(1, len(transcript.split()))
    raw_score = 0.0

    for marker, weight in DISTRESS_MARKERS.items():
        if marker in text_lower:
            raw_score += weight

    # Normalise per 100 tokens so longer transcripts don't inflate score
    normalised = (raw_score / total_words) * 100

    # Scale so that 3+ serious markers = ~10
    scaled = min(10.0, normalised * 2.5 + (raw_score * 2.5))
    return round(scaled, 2)


def infer_speech_pace(transcript: str) -> Literal["SLOW", "NORMAL", "FAST", "FRAGMENTED"]:
    """
    Infer pace from average words-per-sentence.
    Very short sentences → FRAGMENTED (may indicate laboured breathing).
    """
    sentences = [s.strip() for s in re.split(r'[.?!]', transcript) if s.strip()]
    if not sentences:
        return "FRAGMENTED"

    avg_words = sum(len(s.split()) for s in sentences) / len(sentences)

    if avg_words < 4:
        return "FRAGMENTED"
    elif avg_words < 8:
        return "SLOW"
    elif avg_words <= 22:
        return "NORMAL"
    else:
        return "FAST"


def score_clarity(transcript: str, metadata: Optional[Dict[str, Any]] = None) -> float:
    """
    Score clarity. Uses STT metadata when available; defaults to 8.0.
    """
    if metadata is None:
        return 8.0

    score = 10.0

    # unknown_token_ratio: fraction of [inaudible]/[unclear] tokens
    unk_ratio = metadata.get("unknown_token_ratio", 0.0)
    score = (1.0 - unk_ratio) * 10.0

    # audio_quality override
    quality = metadata.get("audio_quality", "")
    if quality == "poor":
        score = min(score, 5.0)
    elif quality == "fair":
        score = min(score, 7.5)

    # confidence_scores: average per-word STT confidence
    conf_scores = metadata.get("confidence_scores", [])
    if conf_scores:
        avg_conf = sum(conf_scores) / len(conf_scores)
        score = min(score, avg_conf * 10.0)

    return round(min(10.0, max(0.0, score)), 2)


def extract_symptoms_from_transcript(transcript: str) -> List[str]:
    """
    Lexical symptom extraction. Returns deduplicated canonical symptom names.
    """
    if not transcript:
        return []

    text_lower = transcript.lower()
    found: Dict[str, bool] = {}

    # Sort by length descending so longer phrases match before substrings
    for phrase, canonical in sorted(SYMPTOM_VOCABULARY.items(), key=lambda x: -len(x[0])):
        if phrase in text_lower and canonical not in found:
            found[canonical] = True

    return list(found.keys())


def extract_duration(transcript: str) -> Optional[str]:
    """Extract time duration expression from transcript."""
    for pattern in _DURATION_PATTERNS:
        match = re.search(pattern, transcript, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def extract_self_reported_severity(transcript: str) -> Optional[str]:
    """Extract pain scale rating or severity descriptor."""
    for pattern in _SEVERITY_PATTERNS:
        match = re.search(pattern, transcript, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def compute_urgency_modifier(scores: VoiceQualityScores) -> float:
    """
    Compute urgency modifier from voice quality.
    Range: -1.0 (very urgent, high distress/incoherence) to +1.0 (calm, clear).
    """
    modifier = 0.0

    # Distress contribution (high distress → more urgent → negative modifier)
    modifier -= (scores.distress_score / 10.0) * 0.50

    # Coherence contribution (very low coherence → possible AMS → more urgent)
    if scores.coherence_score < 4.0:
        modifier -= 0.20

    # Speech pace contribution
    pace_map = {"FRAGMENTED": -0.15, "FAST": -0.05, "SLOW": 0.05, "NORMAL": 0.0}
    modifier += pace_map.get(scores.speech_pace_label, 0.0)

    # Clarity contribution (very unclear may indicate distress or neuro issue)
    if scores.clarity_score < 4.0:
        modifier -= 0.10

    return round(max(-1.0, min(1.0, modifier)), 3)


def _compute_overall_quality(scores: VoiceQualityScores) -> float:
    """Weighted composite voice quality score (0-10)."""
    pace_penalty = {"FRAGMENTED": 2.0, "FAST": 0.5, "SLOW": 0.5, "NORMAL": 0.0}
    pace_p = pace_penalty.get(scores.speech_pace_label, 0.0)
    raw = (
        scores.coherence_score * 0.35
        + scores.clarity_score * 0.30
        + (10.0 - scores.distress_score) * 0.20
        + (10.0 - pace_p) * 0.15
    )
    return round(min(10.0, max(0.0, raw)), 2)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def process_voice_intake(
    patient_id: str,
    transcript: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> VoiceIntakeResult:
    """
    Process a patient's voice/text transcript at ED intake or 911 call.

    Args:
        patient_id: Patient identifier
        transcript: Raw text from patient (direct speech or STT output)
        metadata: Optional STT metadata dict with keys:
                  - unknown_token_ratio (float 0-1)
                  - audio_quality ("good"/"fair"/"poor")
                  - confidence_scores (list of floats 0-1)
                  - speaking_rate ("slow"/"normal"/"fast")  [informational only]
                  - background_noise ("quiet"/"moderate"/"loud")

    Returns:
        VoiceIntakeResult with extracted symptoms and voice quality scores
    """
    coherence = score_coherence(transcript)
    distress = score_distress(transcript)
    pace = infer_speech_pace(transcript)
    clarity = score_clarity(transcript, metadata)

    scores = VoiceQualityScores(
        coherence_score=coherence,
        distress_score=distress,
        speech_pace_label=pace,
        clarity_score=clarity,
        overall_voice_quality=0.0,  # computed below
    )
    scores.overall_voice_quality = _compute_overall_quality(scores)

    symptoms = extract_symptoms_from_transcript(transcript)
    duration = extract_duration(transcript)
    severity = extract_self_reported_severity(transcript)
    urgency_mod = compute_urgency_modifier(scores)

    return VoiceIntakeResult(
        patient_id=patient_id,
        transcript=transcript,
        extracted_symptoms=symptoms,
        symptom_duration=duration,
        symptom_severity_self_reported=severity,
        voice_quality_scores=scores,
        voice_quality_score=scores.overall_voice_quality,
        urgency_modifier=urgency_mod,
        intake_timestamp=datetime.now().isoformat(),
    )


# ============================================================================
# CLI DEMO
# ============================================================================

if __name__ == "__main__":
    test_cases = [
        (
            "P00001",
            "I've been having crushing chest pain for about 30 minutes. "
            "It's radiating to my left arm. I'm sweating. I'm scared. "
            "Worst pain ever, maybe 9 out of 10.",
        ),
        (
            "P00002",
            "Mild headache. Started this morning. Not that bad, maybe 3/10.",
        ),
        (
            "P00003",
            "Can't. Breathe. Really. Bad. Help.",  # fragmented — respiratory distress
        ),
    ]

    for pid, transcript in test_cases:
        result = process_voice_intake(pid, transcript)
        print(f"\n{'='*60}")
        print(f"Patient: {pid}")
        print(f"Transcript: {transcript[:80]}...")
        print(f"Extracted symptoms: {result.extracted_symptoms}")
        print(f"Duration: {result.symptom_duration}")
        print(f"Severity: {result.symptom_severity_self_reported}")
        print(f"Coherence: {result.voice_quality_scores.coherence_score}")
        print(f"Distress:  {result.voice_quality_scores.distress_score}")
        print(f"Pace:      {result.voice_quality_scores.speech_pace_label}")
        print(f"Clarity:   {result.voice_quality_scores.clarity_score}")
        print(f"Overall quality: {result.voice_quality_score}")
        print(f"Urgency modifier: {result.urgency_modifier}  "
              f"({'MORE urgent' if result.urgency_modifier < 0 else 'LESS urgent'})")
