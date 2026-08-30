"""
Human correction logging.

Appends every human correction to a local JSON file with the field name,
old value, new value, timestamp, and optional reason. This log is consumed
by confidence_calibration and memory_matrix.
"""

import sys
import json
from pathlib import Path
from typing import Any, Optional
from datetime import datetime, timezone

from config.settings import CORRECTION_LOG_PATH


def _ensure_log_file() -> Path:
    """Ensure the correction log file exists and return its path."""
    path = Path(CORRECTION_LOG_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("[]", encoding="utf-8")
    return path


def log_correction(
    record_id: str,
    field_name: str,
    old_value: str,
    new_value: str,
    reason: str = "",
    industry: str = "",
    category: str = "",
) -> dict[str, Any]:
    """
    Log a single human correction.

    Appends a correction entry to the local JSON log file.
    Returns the correction entry that was logged.
    """
    path = _ensure_log_file()

    entry = {
        "record_id": record_id,
        "field_name": field_name,
        "old_value": old_value,
        "new_value": new_value,
        "reason": reason,
        "industry": industry,
        "category": category,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Read existing log
    with open(path, "r", encoding="utf-8") as f:
        log = json.load(f)

    log.append(entry)

    # Write back
    with open(path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)

    return entry


def get_corrections(
    record_id: Optional[str] = None,
    field_name: Optional[str] = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """
    Retrieve corrections from the log, optionally filtered by record or field.
    """
    path = _ensure_log_file()

    with open(path, "r", encoding="utf-8") as f:
        log = json.load(f)

    if record_id:
        log = [e for e in log if e.get("record_id") == record_id]
    if field_name:
        log = [e for e in log if e.get("field_name", "").lower() == field_name.lower()]

    # Return most recent first
    log.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    return log[:limit]


def get_correction_count() -> int:
    """Return the total number of corrections logged."""
    path = _ensure_log_file()
    with open(path, "r", encoding="utf-8") as f:
        log = json.load(f)
    return len(log)


def get_frequently_corrected_fields(min_count: int = 2) -> dict[str, int]:
    """
    Return fields that have been corrected more than min_count times.

    Used by confidence_calibration to lower base confidence for
    unreliable fields.
    """
    path = _ensure_log_file()
    with open(path, "r", encoding="utf-8") as f:
        log = json.load(f)

    field_counts: dict[str, int] = {}
    for entry in log:
        field = entry.get("field_name", "").lower()
        field_counts[field] = field_counts.get(field, 0) + 1

    return {f: c for f, c in field_counts.items() if c >= min_count}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m memory.correction_log add <record_id> <field> <old> <new> [reason]")
        print("  python -m memory.correction_log list [field_name]")
        print("  python -m memory.correction_log stats")
        sys.exit(1)

    command = sys.argv[1]

    if command == "add":
        record_id = sys.argv[2]
        field = sys.argv[3]
        old = sys.argv[4]
        new = sys.argv[5]
        reason = sys.argv[6] if len(sys.argv) > 6 else ""

        entry = log_correction(record_id, field, old, new, reason)
        print(f"Logged correction: {field} '{old}' -> '{new}'")

    elif command == "list":
        field = sys.argv[2] if len(sys.argv) > 2 else None
        corrections = get_corrections(field_name=field)
        print(f"Corrections: {len(corrections)}")
        for c in corrections[:10]:
            print(f"  {c['field_name']}: '{c['old_value']}' -> '{c['new_value']}' ({c['timestamp'][:10]})")

    elif command == "stats":
        print(f"Total corrections: {get_correction_count()}")
        frequent = get_frequently_corrected_fields()
        if frequent:
            print("Frequently corrected fields:")
            for field, count in sorted(frequent.items(), key=lambda x: -x[1]):
                print(f"  {field}: {count} corrections")
