"""
Voice Transcription Agent

Transcribes audio input using OpenAI Whisper (local inference).
Accepts raw audio bytes and returns transcript + confidence metadata.

Requires: pip install openai-whisper
Optional:  pip install soundfile  (for non-WAV formats)
"""

import io
import os
import tempfile
from typing import Optional

from pydantic import BaseModel, Field

try:
    import whisper as _whisper
    _WHISPER_AVAILABLE = True
except ImportError:
    _WHISPER_AVAILABLE = False


# ============================================================================
# MODELS
# ============================================================================

class TranscriptionResult(BaseModel):
    transcript: str = Field(description="Transcribed text from audio")
    language: str = Field(default="en", description="Detected language code")
    confidence: str = Field(description="HIGH | MEDIUM | LOW based on avg log-prob")
    avg_logprob: Optional[float] = Field(default=None, description="Raw Whisper avg log-probability")
    no_speech_prob: Optional[float] = Field(default=None, description="Probability of no speech in segment")
    model_used: str = Field(default="base", description="Whisper model size used")
    duration_seconds: Optional[float] = Field(default=None, description="Audio duration in seconds")
    error: Optional[str] = None


# ============================================================================
# MODEL CACHE
# ============================================================================

_model_cache: dict = {}


def _get_model(model_size: str = "base"):
    if not _WHISPER_AVAILABLE:
        raise RuntimeError("openai-whisper not installed. Run: pip install openai-whisper")
    if model_size not in _model_cache:
        _model_cache[model_size] = _whisper.load_model(model_size)
    return _model_cache[model_size]


# ============================================================================
# CONFIDENCE MAPPING
# ============================================================================

def _map_confidence(avg_logprob: float, no_speech_prob: float) -> str:
    """Map Whisper log-prob metrics to HIGH/MEDIUM/LOW confidence label."""
    if no_speech_prob > 0.6:
        return "LOW"
    if avg_logprob > -0.3:
        return "HIGH"
    if avg_logprob > -0.7:
        return "MEDIUM"
    return "LOW"


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def transcribe_audio(
    audio_bytes: bytes,
    filename: str = "audio.wav",
    model_size: str = "base",
    language: Optional[str] = None,
) -> TranscriptionResult:
    """
    Transcribe audio bytes using Whisper.

    Args:
        audio_bytes: Raw audio file bytes (WAV, MP3, M4A, OGG, FLAC, WEBM)
        filename: Original filename (used to detect format for temp file suffix)
        model_size: Whisper model — "tiny", "base", "small", "medium", "large"
        language: Optional ISO language hint (e.g. "en"). None = auto-detect.

    Returns:
        TranscriptionResult
    """
    if not audio_bytes:
        return TranscriptionResult(
            transcript="",
            confidence="LOW",
            model_used=model_size,
            error="No audio data provided",
        )

    if not _WHISPER_AVAILABLE:
        return TranscriptionResult(
            transcript="",
            confidence="LOW",
            model_used=model_size,
            error="openai-whisper not installed. Run: pip install openai-whisper",
        )

    # Determine temp file suffix from filename
    ext = os.path.splitext(filename)[-1].lower() or ".wav"
    if ext not in {".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm", ".mp4"}:
        ext = ".wav"

    try:
        model = _get_model(model_size)

        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            decode_opts = {}
            if language:
                decode_opts["language"] = language

            result = model.transcribe(tmp_path, **decode_opts)
        finally:
            os.unlink(tmp_path)

        transcript = result.get("text", "").strip()
        detected_lang = result.get("language", "en")

        # Aggregate segment-level metrics
        segments = result.get("segments", [])
        avg_logprob = None
        no_speech_prob = None
        duration = None

        if segments:
            avg_logprob = sum(s.get("avg_logprob", -1.0) for s in segments) / len(segments)
            no_speech_prob = max(s.get("no_speech_prob", 0.0) for s in segments)
            last = segments[-1]
            duration = last.get("end")

        confidence = _map_confidence(
            avg_logprob if avg_logprob is not None else -1.0,
            no_speech_prob if no_speech_prob is not None else 0.0,
        )

        return TranscriptionResult(
            transcript=transcript,
            language=detected_lang,
            confidence=confidence,
            avg_logprob=avg_logprob,
            no_speech_prob=no_speech_prob,
            model_used=model_size,
            duration_seconds=duration,
        )

    except Exception as e:
        return TranscriptionResult(
            transcript="",
            confidence="LOW",
            model_used=model_size,
            error=str(e),
        )


# ============================================================================
# CLI DEMO
# ============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python voice_transcription_agent.py <audio_file> [model_size]")
        sys.exit(1)

    path = sys.argv[1]
    size = sys.argv[2] if len(sys.argv) > 2 else "base"

    with open(path, "rb") as f:
        audio = f.read()

    res = transcribe_audio(audio, filename=os.path.basename(path), model_size=size)

    if res.error:
        print(f"Error: {res.error}")
    else:
        print(f"Transcript: {res.transcript}")
        print(f"Language: {res.language} | Confidence: {res.confidence}")
        if res.duration_seconds:
            print(f"Duration: {res.duration_seconds:.1f}s")
