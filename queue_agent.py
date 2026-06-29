"""
Queue Intelligence Agent

Maintains a live, dynamically-prioritised patient queue.
Priority is computed from ESI level, deterioration risk, and time waited.

The queue is an in-process singleton — each call to add_or_update_patient()
triggers a full re-sort so the charge nurse always sees the most critical
patient at the top, regardless of arrival order.
"""

import math
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Literal

from pydantic import BaseModel, Field


# ============================================================================
# PRIORITY SCORE FORMULA
# ============================================================================
#
# priority = esi_weight(esi_level)           # ESI 1→100, 2→80, 3→50, 4→20, 5→5
#           + deterioration_weight * 30      # risk_score 0–1 × 30 → 0–30 pts
#           + wait_bonus(wait_minutes)       # log-scaled 0–20 pts
#
# Sorted descending — higher score = assigned first.

_ESI_WEIGHTS = {1: 100, 2: 80, 3: 50, 4: 20, 5: 5}
_DETERIORATION_WEIGHT = 30.0
_WAIT_SCALE = 4.0   # wait_bonus = min(20, log1p(minutes) * _WAIT_SCALE)
_WAIT_CAP = 20.0


def compute_priority_score(
    esi_level: int,
    deterioration_risk: float,
    wait_minutes: float,
) -> tuple[float, str]:
    """
    Compute a numeric priority score and human-readable rationale.

    Returns:
        (priority_score, rationale_string)
    """
    esi_pts = _ESI_WEIGHTS.get(esi_level, 50)
    det_pts = deterioration_risk * _DETERIORATION_WEIGHT
    wait_pts = min(_WAIT_CAP, math.log1p(max(0.0, wait_minutes)) * _WAIT_SCALE)

    total = esi_pts + det_pts + wait_pts

    rationale = (
        f"ESI {esi_level} (+{esi_pts}), "
        f"Deterioration {deterioration_risk*100:.0f}% (+{det_pts:.1f}), "
        f"Wait {wait_minutes:.0f}min (+{wait_pts:.1f}) = {total:.1f}"
    )

    return round(total, 2), rationale


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class PatientQueueEntry(BaseModel):
    patient_id: str
    patient_name: str = Field(default="Unknown")
    esi_level: int = Field(description="ESI 1-5")
    triage_decision: str = Field(description="e.g. EMERGENT")
    deterioration_risk: float = Field(default=0.0, description="0.0-1.0 from deterioration agent")
    deterioration_level: str = Field(default="LOW", description="LOW/MEDIUM/HIGH/CRITICAL")
    predicted_trajectory: str = Field(default="STABLE")
    arrival_time: str = Field(description="ISO 8601 arrival timestamp")
    wait_minutes: float = Field(default=0.0, description="Computed dynamically")
    priority_score: float = Field(default=0.0)
    priority_rationale: str = Field(default="")
    patient_assignment: str = Field(default="")
    queue_position: int = Field(default=0)
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())


class QueueUpdateResult(BaseModel):
    updated_queue: List[PatientQueueEntry]
    new_entry: PatientQueueEntry
    total_patients: int
    critical_count: int = Field(description="ESI 1 or deterioration CRITICAL patients")
    high_risk_count: int = Field(description="ESI 2 or deterioration HIGH patients")
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class QueueSummary(BaseModel):
    total_patients: int
    critical_count: int
    high_risk_count: int
    esi_breakdown: Dict[str, int]
    avg_wait_minutes: float
    longest_wait_patient: Optional[str]
    top_priority_patient: Optional[str]
    summarized_at: str = Field(default_factory=lambda: datetime.now().isoformat())


# ============================================================================
# MODULE-LEVEL QUEUE STATE (in-process singleton)
# ============================================================================

_patient_queue: List[PatientQueueEntry] = []


def _parse_arrival(arrival_time: str) -> datetime:
    """Parse ISO 8601 timestamp, returning UTC-aware or naive datetime."""
    try:
        dt = datetime.fromisoformat(arrival_time)
        return dt
    except Exception:
        return datetime.now()


def _compute_wait_minutes(arrival_time: str) -> float:
    """Compute elapsed wait time in minutes from arrival timestamp."""
    arrival = _parse_arrival(arrival_time)
    now = datetime.now()
    # Handle timezone-aware vs naive
    if arrival.tzinfo is not None:
        now = datetime.now(timezone.utc)
    delta = now - arrival
    return max(0.0, delta.total_seconds() / 60.0)


def _update_wait_and_score(entry: PatientQueueEntry) -> PatientQueueEntry:
    """Recompute wait_minutes and priority_score for a queue entry."""
    entry.wait_minutes = _compute_wait_minutes(entry.arrival_time)
    score, rationale = compute_priority_score(
        entry.esi_level,
        entry.deterioration_risk,
        entry.wait_minutes,
    )
    entry.priority_score = score
    entry.priority_rationale = rationale
    entry.last_updated = datetime.now().isoformat()
    return entry


def _resort_and_number(queue: List[PatientQueueEntry]) -> List[PatientQueueEntry]:
    """Sort queue descending by priority score and assign positions."""
    queue.sort(key=lambda e: e.priority_score, reverse=True)
    for i, entry in enumerate(queue):
        entry.queue_position = i + 1
    return queue


# ============================================================================
# PUBLIC FUNCTIONS
# ============================================================================

def add_or_update_patient(entry_data: Dict[str, Any]) -> QueueUpdateResult:
    """
    Add a new patient to the queue or update an existing entry.
    Triggers full re-prioritisation of the entire queue.

    Args:
        entry_data: Dict with fields matching PatientQueueEntry.
                    Required: patient_id, esi_level, triage_decision,
                              deterioration_risk, deterioration_level,
                              arrival_time, patient_assignment.
                    Optional: patient_name, predicted_trajectory.

    Returns:
        QueueUpdateResult with the updated sorted queue.
    """
    global _patient_queue

    patient_id = entry_data["patient_id"]

    # Check if patient already in queue (update vs new)
    existing_index = next(
        (i for i, e in enumerate(_patient_queue) if e.patient_id == patient_id),
        None
    )

    new_entry = PatientQueueEntry(
        patient_id=patient_id,
        patient_name=entry_data.get("patient_name", "Unknown"),
        esi_level=int(entry_data.get("esi_level", 3)),
        triage_decision=entry_data.get("triage_decision", "URGENT"),
        deterioration_risk=float(entry_data.get("deterioration_risk", 0.0)),
        deterioration_level=entry_data.get("deterioration_level", "LOW"),
        predicted_trajectory=entry_data.get("predicted_trajectory", "STABLE"),
        arrival_time=entry_data.get("arrival_time", datetime.now().isoformat()),
        patient_assignment=entry_data.get("patient_assignment", ""),
        wait_minutes=0.0,
        priority_score=0.0,
        queue_position=0,
    )

    if existing_index is not None:
        # Keep original arrival_time for wait calculation
        new_entry.arrival_time = _patient_queue[existing_index].arrival_time
        _patient_queue[existing_index] = new_entry
    else:
        _patient_queue.append(new_entry)

    # Recompute wait + scores for all entries, then re-sort
    _patient_queue = [_update_wait_and_score(e) for e in _patient_queue]
    _patient_queue = _resort_and_number(_patient_queue)

    # Find the updated entry to return
    updated_entry = next(e for e in _patient_queue if e.patient_id == patient_id)

    critical_count = sum(
        1 for e in _patient_queue
        if e.esi_level == 1 or e.deterioration_level == "CRITICAL"
    )
    high_risk_count = sum(
        1 for e in _patient_queue
        if e.esi_level == 2 or e.deterioration_level == "HIGH"
    )

    return QueueUpdateResult(
        updated_queue=list(_patient_queue),
        new_entry=updated_entry,
        total_patients=len(_patient_queue),
        critical_count=critical_count,
        high_risk_count=high_risk_count,
    )


def get_current_queue() -> List[PatientQueueEntry]:
    """Return the current sorted queue (refreshes wait times and scores first)."""
    global _patient_queue
    _patient_queue = [_update_wait_and_score(e) for e in _patient_queue]
    _patient_queue = _resort_and_number(_patient_queue)
    return list(_patient_queue)


def remove_patient(patient_id: str) -> bool:
    """Remove a patient from the queue (on discharge, admission, or diversion)."""
    global _patient_queue
    original_len = len(_patient_queue)
    _patient_queue = [e for e in _patient_queue if e.patient_id != patient_id]
    _patient_queue = _resort_and_number(_patient_queue)
    return len(_patient_queue) < original_len


def get_queue_summary() -> QueueSummary:
    """Return a summary of current queue state."""
    queue = get_current_queue()

    if not queue:
        return QueueSummary(
            total_patients=0,
            critical_count=0,
            high_risk_count=0,
            esi_breakdown={str(i): 0 for i in range(1, 6)},
            avg_wait_minutes=0.0,
            longest_wait_patient=None,
            top_priority_patient=None,
        )

    esi_breakdown = {str(i): 0 for i in range(1, 6)}
    for entry in queue:
        esi_breakdown[str(entry.esi_level)] = (
            esi_breakdown.get(str(entry.esi_level), 0) + 1
        )

    critical_count = sum(
        1 for e in queue if e.esi_level == 1 or e.deterioration_level == "CRITICAL"
    )
    high_risk_count = sum(
        1 for e in queue if e.esi_level == 2 or e.deterioration_level == "HIGH"
    )
    avg_wait = sum(e.wait_minutes for e in queue) / len(queue)
    longest_wait = max(queue, key=lambda e: e.wait_minutes)
    top_priority = queue[0]  # already sorted by priority

    return QueueSummary(
        total_patients=len(queue),
        critical_count=critical_count,
        high_risk_count=high_risk_count,
        esi_breakdown=esi_breakdown,
        avg_wait_minutes=round(avg_wait, 1),
        longest_wait_patient=longest_wait.patient_id,
        top_priority_patient=top_priority.patient_id,
    )


def clear_queue() -> None:
    """Clear all patients from the queue (testing / end-of-shift reset)."""
    global _patient_queue
    _patient_queue = []


def display_queue() -> str:
    """Return a formatted queue board string for CLI/terminal display."""
    queue = get_current_queue()
    if not queue:
        return "Queue is empty."

    lines = [
        f"{'#':<4} {'Patient':<10} {'ESI':<5} {'Decision':<15} "
        f"{'Det.Risk':<10} {'Wait':<8} {'Score':<8} Assignment",
        "-" * 95,
    ]
    for e in queue:
        lines.append(
            f"{e.queue_position:<4} {e.patient_id:<10} {e.esi_level:<5} "
            f"{e.triage_decision:<15} "
            f"{e.deterioration_level:<10} {e.wait_minutes:.0f}min  "
            f"{e.priority_score:<8.1f} {e.patient_assignment[:30]}"
        )
    return "\n".join(lines)


# ============================================================================
# CLI DEMO
# ============================================================================

if __name__ == "__main__":
    import time

    # Simulate 3 patients arriving
    test_patients = [
        {
            "patient_id": "P00001",
            "patient_name": "Alice Smith",
            "esi_level": 3,
            "triage_decision": "URGENT",
            "deterioration_risk": 0.35,
            "deterioration_level": "MEDIUM",
            "predicted_trajectory": "WORSENING",
            "arrival_time": datetime.now().isoformat(),
            "patient_assignment": "General ED Treatment Room",
        },
        {
            "patient_id": "P00002",
            "patient_name": "Bob Jones",
            "esi_level": 2,
            "triage_decision": "EMERGENT",
            "deterioration_risk": 0.72,
            "deterioration_level": "HIGH",
            "predicted_trajectory": "RAPID_DETERIORATION",
            "arrival_time": datetime.now().isoformat(),
            "patient_assignment": "Acute Care / High-Acuity Zone",
        },
        {
            "patient_id": "P00003",
            "patient_name": "Carol Davis",
            "esi_level": 4,
            "triage_decision": "LESS_URGENT",
            "deterioration_risk": 0.10,
            "deterioration_level": "LOW",
            "predicted_trajectory": "STABLE",
            "arrival_time": datetime.now().isoformat(),
            "patient_assignment": "Fast Track",
        },
    ]

    for patient in test_patients:
        result = add_or_update_patient(patient)
        print(f"Added {patient['patient_id']}: queue position #{result.new_entry.queue_position}")

    print("\n" + display_queue())
    print("\n" + str(get_queue_summary()))
