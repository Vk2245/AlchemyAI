"""
Confidence calibration from correction history.

Reads the correction log, identifies fields that get corrected often,
and generates calibration offsets that lower the base confidence for
those fields in future extractions.
"""

import sys
import json
from typing import Any

from memory.correction_log import get_frequently_corrected_fields, get_corrections


# How much to reduce confidence per correction instance
PENALTY_PER_CORRECTION: float = -0.05

# Maximum total penalty for any single field
MAX_PENALTY: float = -0.30


def compute_calibration_offsets(
    min_corrections: int = 2,
) -> dict[str, float]:
    """
    Compute confidence offsets based on correction history.

    Fields that are frequently corrected get a negative offset,
    which lowers their base confidence score in future extractions.

    Returns a dict mapping field name (lowercase) to offset value.
    """
    frequent = get_frequently_corrected_fields(min_count=min_corrections)

    offsets: dict[str, float] = {}
    for field, count in frequent.items():
        penalty = count * PENALTY_PER_CORRECTION
        offsets[field] = max(penalty, MAX_PENALTY)

    return offsets


def get_calibration_summary() -> dict[str, Any]:
    """
    Return a summary of calibration state for display.

    Shows which fields have penalties and how severe they are.
    """
    offsets = compute_calibration_offsets()
    corrections = get_corrections()

    return {
        "total_corrections": len(corrections),
        "calibrated_fields": len(offsets),
        "offsets": offsets,
        "most_corrected": sorted(
            get_frequently_corrected_fields(min_count=1).items(),
            key=lambda x: -x[1],
        )[:10],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    summary = get_calibration_summary()

    print(f"Total corrections in log: {summary['total_corrections']}")
    print(f"Calibrated fields: {summary['calibrated_fields']}")
    print()

    if summary["offsets"]:
        print("Confidence offsets:")
        for field, offset in sorted(summary["offsets"].items(), key=lambda x: x[1]):
            print(f"  {field}: {offset:+.2f}")
    else:
        print("No calibration offsets yet (need at least 2 corrections per field).")

    print()
    if summary["most_corrected"]:
        print("Most corrected fields:")
        for field, count in summary["most_corrected"]:
            print(f"  {field}: {count} corrections")
