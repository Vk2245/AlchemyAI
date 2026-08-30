"""
Evidence comparison for human reviewers.

Returns a side-by-side view of conflicting source snippets for a field,
formatted for the review UI.
"""

import sys
import json
from typing import Any

from reasoning.conflict_resolution import detect_conflicts


def build_evidence_comparison(
    conflict: dict[str, Any],
) -> dict[str, Any]:
    """
    Build a side-by-side comparison of source evidence for a conflicting field.

    Returns a structured comparison ready for the review UI.
    """
    field = conflict["field"]
    values = conflict["values"]

    sides = []
    for v in values:
        sides.append({
            "value": v["value"],
            "confidence": v.get("confidence", 0.0),
            "source_file": v.get("source_file", "unknown"),
            "source_text": v.get("source_text", ""),
        })

    return {
        "field": field,
        "sides": sides,
        "value_count": len(conflict.get("unique_values", [])),
        "needs_review": True,
    }


def build_all_comparisons(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Build evidence comparisons for all conflicting fields across records.
    """
    conflicts = detect_conflicts(records)
    comparisons = []

    for conflict in conflicts:
        comparison = build_evidence_comparison(conflict)
        comparisons.append(comparison)

    return comparisons


def format_comparison_text(comparison: dict[str, Any]) -> str:
    """
    Format a comparison as readable text for CLI output or logging.
    """
    lines = [f"Field: {comparison['field']}"]
    lines.append(f"Conflicting values: {comparison['value_count']}")
    lines.append("")

    for i, side in enumerate(comparison["sides"]):
        lines.append(f"  Source {i + 1}: {side['source_file']}")
        lines.append(f"  Value: {side['value']}")
        lines.append(f"  Confidence: {side['confidence']:.2f}")
        if side["source_text"]:
            snippet = side["source_text"][:200]
            lines.append(f"  Evidence: \"{snippet}\"")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python -m reasoning.evidence_comparison <record_a.json> <record_b.json>")
        sys.exit(1)

    records = []
    for path in sys.argv[1:]:
        with open(path, "r", encoding="utf-8") as f:
            records.append(json.load(f))

    comparisons = build_all_comparisons(records)
    print(f"Evidence comparisons: {len(comparisons)}")
    print()

    for comp in comparisons:
        print(format_comparison_text(comp))
        print("---")
