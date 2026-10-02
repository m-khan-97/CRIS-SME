"""Project private runner events into a bounded browser-safe progress timeline."""
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from cris_sme.api.artifact_access import read_regular_file


MAX_EVENT_FILE_BYTES = 1024 * 1024
MAX_PUBLIC_EVENTS = 200
PHASE_LABELS = {
    "collect_evidence": "Evidence collection",
    "evaluate_controls": "Control evaluation",
    "score_findings": "Finding scoring",
    "map_compliance": "Compliance mapping",
    "assess_evidence_sufficiency": "Evidence sufficiency assessment",
}


def read_public_events(path: Path) -> list[dict[str, Any]]:
    try:
        data = read_regular_file(path.parent, Path(path.name), max_bytes=MAX_EVENT_FILE_BYTES)
        lines = data.decode("utf-8").splitlines()
    except (OSError, ValueError, UnicodeError):
        return []
    events = []
    for line in lines:
        try:
            event = json.loads(line)
        except (ValueError, RecursionError):
            continue
        if not isinstance(event, dict):
            continue
        phase, status = event.get("phase"), event.get("status")
        sequence, timestamp = event.get("sequence"), event.get("generated_at")
        if not isinstance(phase, str) or phase not in PHASE_LABELS:
            continue
        if status not in ("started", "completed"):
            continue
        if type(sequence) is not int or not 1 <= sequence <= 10000:
            continue
        if not isinstance(timestamp, str) or len(timestamp) > 40:
            continue
        try:
            parsed_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            continue
        if parsed_time.tzinfo is None:
            continue
        message = f"{PHASE_LABELS[phase]} {status}."
        if phase == "collect_evidence" and status == "started":
            message = "Collecting provider-normalized evidence profiles."
        events.append({
            "sequence": sequence, "phase": phase, "status": status,
            "message": message,
            "generated_at": parsed_time.isoformat().replace("+00:00", "Z"),
            "detail": {},
        })
        if len(events) >= MAX_PUBLIC_EVENTS:
            break
    return events
