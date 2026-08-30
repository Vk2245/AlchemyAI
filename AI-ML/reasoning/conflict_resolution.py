"""
Conflict resolution across sources.

When the same field has different values across sources, uses confidence
scores plus an LLM check to pick and explain the best-supported value.
"""

import sys
import json
from typing import Any

from config.llm_client import get_completion
from config.toon_utils import wrap_for_prompt


def detect_conflicts(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Find fields where multiple records disagree on the value.

    Compares records that share the same part number or product name.
    Returns a list of conflict dicts with the field, values, and sources.
    """
    # Group by part number or product name
    groups: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        key = record.get("part_number") or record.get("product_name", "")
        key = key.lower().strip()
        if key:
            groups.setdefault(key, []).append(record)

    conflicts = []

    for key, group_records in groups.items():
        if len(group_records) < 2:
            continue

        # Compare attributes across records in this group
        attr_values: dict[str, list[dict[str, Any]]] = {}

        for record in group_records:
            for attr in record.get("attributes", []):
                name = attr.get("name", "").lower()
                attr_values.setdefault(name, []).append({
                    "value": attr.get("value", ""),
                    "confidence": attr.get("confidence", 0.0),
                    "source_file": record.get("source_file", "unknown"),
                    "source_text": attr.get("source_text", ""),
                })

        for attr_name, values in attr_values.items():
            unique_values = set(v["value"] for v in values)
            if len(unique_values) > 1:
                conflicts.append({
                    "product_key": key,
                    "field": attr_name,
                    "values": values,
                    "unique_values": list(unique_values),
                })

    return conflicts


def resolve_conflict(
    conflict: dict[str, Any],
    provider: str = "local",
) -> dict[str, Any]:
    """
    Resolve a single field conflict using confidence scores and LLM reasoning.

    Returns the best-supported value with an explanation.
    """
    values = conflict["values"]

    # Step 1: Pick the highest-confidence value
    best_by_confidence = max(values, key=lambda v: v.get("confidence", 0.0))

    # Step 2: Ask LLM to validate the choice
    conflict_prompt = wrap_for_prompt(
        {
            "field": conflict["field"],
            "values": [
                {"value": v["value"], "confidence": v["confidence"], "source": v["source_file"]}
                for v in values
            ],
        },
        "conflict",
    )

    prompt = f"""A product field has conflicting values from different sources.

{conflict_prompt}

Which value is most likely correct and why? Consider:
- Confidence scores from extraction
- Whether values are close (rounding/formatting differences) or fundamentally different
- Which source seems more authoritative

Return the best value and a brief explanation."""

    explanation = get_completion(prompt, provider=provider)

    return {
        "field": conflict["field"],
        "resolved_value": best_by_confidence["value"],
        "resolved_confidence": best_by_confidence["confidence"],
        "resolved_source": best_by_confidence["source_file"],
        "all_values": conflict["unique_values"],
        "explanation": explanation,
    }


def resolve_all_conflicts(
    records: list[dict[str, Any]],
    provider: str = "local",
) -> list[dict[str, Any]]:
    """
    Detect and resolve all conflicts across a set of records.
    """
    conflicts = detect_conflicts(records)
    resolutions = []

    for conflict in conflicts:
        resolution = resolve_conflict(conflict, provider=provider)
        resolutions.append(resolution)

    return resolutions


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python -m reasoning.conflict_resolution <record_a.json> <record_b.json>")
        sys.exit(1)

    records = []
    for path in sys.argv[1:]:
        with open(path, "r", encoding="utf-8") as f:
            records.append(json.load(f))

    conflicts = detect_conflicts(records)
    print(f"Conflicts found: {len(conflicts)}")

    for c in conflicts:
        print(f"\n  Field: {c['field']}")
        print(f"  Values: {c['unique_values']}")
        for v in c["values"]:
            print(f"    {v['value']} (conf={v['confidence']:.2f}, source={v['source_file']})")
