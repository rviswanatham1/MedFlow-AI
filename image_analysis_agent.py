"""
Image Analysis Agent

Analyzes patient injury/symptom photographs using Claude Vision API.
Supports: lacerations, burns, bruises, rashes, swelling, deformities,
          wound infections, fracture signs.

Uses claude-sonnet-4-6 vision. Requires ANTHROPIC_API_KEY env variable.
"""

import base64
import json
import os
import re
from datetime import datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field

try:
    import anthropic
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False

try:
    from PIL import Image as PILImage
    import io as _io
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class SingleImageAnalysis(BaseModel):
    image_index: int = Field(description="1-based index of this image in the upload set")
    injury_type: str = Field(description="Primary type of injury/finding")
    severity_assessment: str = Field(
        description="minor | moderate | severe | critical"
    )
    clinical_observations: List[str] = Field(
        description="Specific visible clinical findings"
    )
    concerning_features: List[str] = Field(
        default_factory=list,
        description="Red-flag features if present (active bleeding, infection signs, etc.)"
    )
    recommended_interventions: List[str] = Field(
        description="Immediate care actions based on visible injury"
    )
    suggested_diagnostics: List[str] = Field(
        default_factory=list,
        description="Additional diagnostics suggested by the image"
    )
    esi_impact: int = Field(
        description="-1 = escalate ESI (more urgent), 0 = no change, +1 = de-escalate"
    )
    esi_impact_reason: str = Field(description="Brief reason for ESI impact")
    clinical_rationale: str = Field(description="Overall clinical assessment narrative")
    confidence: str = Field(description="HIGH | MEDIUM | LOW")
    image_quality: str = Field(description="adequate | limited | poor")


class ImageAnalysisResult(BaseModel):
    patient_id: str
    num_images: int
    analyses: List[SingleImageAnalysis]
    combined_esi_impact: int = Field(
        description="Net ESI impact across all images (most severe wins)"
    )
    combined_severity: str = Field(
        description="Overall severity across all images"
    )
    all_interventions: List[str] = Field(
        description="Deduplicated interventions across all images"
    )
    all_observations: List[str] = Field(
        description="Deduplicated observations across all images"
    )
    symptoms_injection: str = Field(
        description="Text to inject into symptoms context for triage pipeline"
    )
    analyzed_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    error: Optional[str] = None


# ============================================================================
# ANALYSIS PROMPT
# ============================================================================

_CLINICAL_IMAGE_PROMPT = """You are an emergency medicine physician analyzing patient injury/symptom photographs for ED triage support.

Analyze the provided image and give a structured clinical assessment.

Assess for:
1. Type of injury or finding (laceration, burn, contusion/bruise, swelling/edema, rash, deformity, open wound, foreign body, etc.)
2. Severity: minor / moderate / severe / critical
3. Visible characteristics: size estimate, depth appearance, wound edges, contamination, active bleeding
4. Concerning features: infection signs (erythema/tracking, pus, swelling beyond wound margins), arterial involvement, tendon/bone exposure, compartment syndrome risk, neurovascular compromise signs
5. ESI triage impact: does this image finding change the triage level?

IMPORTANT: This is clinical DECISION SUPPORT. State your confidence. Note if image quality limits assessment.

Return ONLY valid JSON — no text before or after:
{
  "injury_type": "primary type",
  "severity_assessment": "minor | moderate | severe | critical",
  "clinical_observations": ["specific finding 1", "specific finding 2"],
  "concerning_features": [],
  "recommended_interventions": ["action 1", "action 2"],
  "suggested_diagnostics": ["X-ray if fracture suspected", "wound culture if infected"],
  "esi_impact": 0,
  "esi_impact_reason": "brief explanation",
  "clinical_rationale": "overall assessment paragraph",
  "confidence": "HIGH | MEDIUM | LOW",
  "image_quality": "adequate | limited | poor"
}"""


# ============================================================================
# IMAGE UTILITIES
# ============================================================================

def _bytes_to_base64(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    """Encode raw image bytes to base64 string."""
    return base64.standard_b64encode(image_bytes).decode("utf-8")


def _detect_mime_type(image_bytes: bytes, filename: str = "") -> str:
    """Detect MIME type from magic bytes or filename extension."""
    if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        return "image/png"
    if image_bytes[:3] == b'\xff\xd8\xff':
        return "image/jpeg"
    if image_bytes[:4] == b'GIF8':
        return "image/gif"
    if image_bytes[:4] == b'RIFF' and image_bytes[8:12] == b'WEBP':
        return "image/webp"
    # Fallback by extension
    ext = filename.lower().split('.')[-1] if filename else ""
    return {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "gif": "image/gif",
        "webp": "image/webp",
    }.get(ext, "image/jpeg")


def _resize_for_api(image_bytes: bytes, max_size: int = 1568) -> bytes:
    """Resize image if too large for API (Claude supports up to 8000×8000 but smaller = faster)."""
    if not _PIL_AVAILABLE:
        return image_bytes
    try:
        img = PILImage.open(_io.BytesIO(image_bytes))
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size), PILImage.LANCZOS)
            buf = _io.BytesIO()
            fmt = "JPEG" if img.mode == "RGB" else "PNG"
            img.save(buf, format=fmt, quality=85)
            return buf.getvalue()
    except Exception:
        pass
    return image_bytes


# ============================================================================
# SINGLE IMAGE ANALYSIS
# ============================================================================

def _analyze_single_image(
    client: "anthropic.Anthropic",
    image_bytes: bytes,
    filename: str,
    image_index: int,
    patient_context: str = "",
) -> SingleImageAnalysis:
    """Analyze one image using Claude Vision API."""

    resized = _resize_for_api(image_bytes)
    mime = _detect_mime_type(resized, filename)
    b64 = _bytes_to_base64(resized, mime)

    context_note = ""
    if patient_context:
        context_note = f"\n\nPatient context: {patient_context}"

    message_content = [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": mime,
                "data": b64,
            },
        },
        {
            "type": "text",
            "text": _CLINICAL_IMAGE_PROMPT + context_note,
        },
    ]

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": message_content}],
    )

    response_text = response.content[0].text if response.content else ""

    # Extract JSON
    json_str = None
    if "```json" in response_text:
        start = response_text.find("```json") + 7
        end = response_text.find("```", start)
        json_str = response_text[start:end].strip() if end > start else None
    elif "```" in response_text:
        start = response_text.find("```") + 3
        end = response_text.find("```", start)
        json_str = response_text[start:end].strip() if end > start else None
    else:
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        if start >= 0 and end > start:
            json_str = re.sub(r',(\s*[}\]])', r'\1', response_text[start:end])

    if json_str:
        data = json.loads(json_str)
        data["image_index"] = image_index
        return SingleImageAnalysis(**data)

    # Fallback if JSON parsing fails
    return SingleImageAnalysis(
        image_index=image_index,
        injury_type="Unable to parse — review manually",
        severity_assessment="moderate",
        clinical_observations=["Image received but structured analysis failed"],
        recommended_interventions=["Physician review of uploaded image required"],
        esi_impact=0,
        esi_impact_reason="Parsing error — no adjustment applied",
        clinical_rationale=response_text[:500] if response_text else "No response",
        confidence="LOW",
        image_quality="poor",
    )


# ============================================================================
# MULTI-IMAGE AGGREGATION
# ============================================================================

_SEVERITY_RANK = {"minor": 1, "moderate": 2, "severe": 3, "critical": 4}


def _aggregate_analyses(analyses: List[SingleImageAnalysis]) -> Dict[str, Any]:
    """Aggregate multiple image analyses into a combined summary."""
    if not analyses:
        return {
            "combined_esi_impact": 0,
            "combined_severity": "minor",
            "all_interventions": [],
            "all_observations": [],
            "symptoms_injection": "",
        }

    # Most severe ESI impact (most negative = most urgent)
    combined_esi = min(a.esi_impact for a in analyses)

    # Most severe severity
    worst = max(analyses, key=lambda a: _SEVERITY_RANK.get(a.severity_assessment, 1))
    combined_severity = worst.severity_assessment

    # Deduplicate interventions and observations
    seen_interventions: Dict[str, bool] = {}
    seen_observations: Dict[str, bool] = {}
    for a in analyses:
        for iv in a.recommended_interventions:
            if iv not in seen_interventions:
                seen_interventions[iv] = True
        for ob in a.clinical_observations + a.concerning_features:
            if ob not in seen_observations:
                seen_observations[ob] = True

    all_interventions = list(seen_interventions.keys())
    all_observations = list(seen_observations.keys())

    # Build symptoms injection text for the triage pipeline
    injury_types = list(dict.fromkeys(a.injury_type for a in analyses))
    symptoms_injection = (
        f"[IMAGE ANALYSIS: {', '.join(injury_types)} — {combined_severity} severity. "
        f"Findings: {'; '.join(all_observations[:4])}] "
    )

    return {
        "combined_esi_impact": combined_esi,
        "combined_severity": combined_severity,
        "all_interventions": all_interventions,
        "all_observations": all_observations,
        "symptoms_injection": symptoms_injection,
    }


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def analyze_images(
    patient_id: str,
    images: List[tuple[bytes, str]],  # list of (image_bytes, filename)
    patient_context: str = "",
    api_key: Optional[str] = None,
) -> ImageAnalysisResult:
    """
    Analyze one or more patient injury images.

    Args:
        patient_id: Patient identifier
        images: List of (image_bytes, filename) tuples
        patient_context: Optional context string (symptoms, age, etc.)
        api_key: Optional Anthropic API key (defaults to ANTHROPIC_API_KEY env var)

    Returns:
        ImageAnalysisResult with per-image analyses and aggregated summary
    """
    if not images:
        return ImageAnalysisResult(
            patient_id=patient_id,
            num_images=0,
            analyses=[],
            combined_esi_impact=0,
            combined_severity="minor",
            all_interventions=[],
            all_observations=[],
            symptoms_injection="",
            error="No images provided",
        )

    if not _ANTHROPIC_AVAILABLE:
        return ImageAnalysisResult(
            patient_id=patient_id,
            num_images=len(images),
            analyses=[],
            combined_esi_impact=0,
            combined_severity="moderate",
            all_interventions=["Physician visual assessment of uploaded images required"],
            all_observations=["Image analysis unavailable — anthropic package not installed"],
            symptoms_injection="[Image uploaded — manual physician review required] ",
            error="anthropic package not installed. Run: pip install anthropic",
        )

    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return ImageAnalysisResult(
            patient_id=patient_id,
            num_images=len(images),
            analyses=[],
            combined_esi_impact=0,
            combined_severity="moderate",
            all_interventions=["Physician visual assessment of uploaded images required"],
            all_observations=["Image analysis unavailable — ANTHROPIC_API_KEY not set"],
            symptoms_injection="[Image uploaded — manual physician review required] ",
            error="ANTHROPIC_API_KEY environment variable not set",
        )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        analyses: List[SingleImageAnalysis] = []

        for i, (img_bytes, filename) in enumerate(images, 1):
            single = _analyze_single_image(
                client=client,
                image_bytes=img_bytes,
                filename=filename,
                image_index=i,
                patient_context=patient_context,
            )
            analyses.append(single)

        agg = _aggregate_analyses(analyses)

        return ImageAnalysisResult(
            patient_id=patient_id,
            num_images=len(images),
            analyses=analyses,
            **agg,
        )

    except Exception as e:
        return ImageAnalysisResult(
            patient_id=patient_id,
            num_images=len(images),
            analyses=[],
            combined_esi_impact=0,
            combined_severity="moderate",
            all_interventions=["Manual physician review of uploaded images required"],
            all_observations=[f"Image analysis error: {str(e)}"],
            symptoms_injection="[Image uploaded — analysis error, manual review required] ",
            error=str(e),
        )


# ============================================================================
# CLI DEMO
# ============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python image_analysis_agent.py <image_path> [patient_context]")
        sys.exit(1)

    image_path = sys.argv[1]
    context = sys.argv[2] if len(sys.argv) > 2 else ""

    with open(image_path, "rb") as f:
        img_bytes = f.read()

    result = analyze_images(
        patient_id="TEST",
        images=[(img_bytes, image_path)],
        patient_context=context,
    )

    if result.error:
        print(f"Error: {result.error}")
    else:
        for analysis in result.analyses:
            print(f"\nImage {analysis.image_index}: {analysis.injury_type}")
            print(f"Severity: {analysis.severity_assessment} | Confidence: {analysis.confidence}")
            print(f"Observations: {', '.join(analysis.clinical_observations)}")
            if analysis.concerning_features:
                print(f"CONCERNING: {', '.join(analysis.concerning_features)}")
            print(f"Interventions: {', '.join(analysis.recommended_interventions)}")
            print(f"ESI Impact: {analysis.esi_impact:+d} — {analysis.esi_impact_reason}")

        print(f"\nCombined: {result.combined_severity} | ESI impact: {result.combined_esi_impact:+d}")
        print(f"Symptoms injection: {result.symptoms_injection}")
