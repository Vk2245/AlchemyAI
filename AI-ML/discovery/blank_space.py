"""
Blank space discovery.

Compares schema field coverage across records in a product family to
surface systematic gaps -- fields that should be populated but are
consistently missing.
"""

import sys
import json
from typing import Any
from collections import defaultdict


def analyze_field_coverage(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Analyze which attribute fields are populated across a set of records.

    Returns a coverage report showing:
      - field_coverage: dict mapping field name to the fraction of records that have it
      - missing_fields: fields present in some records but missing in others
      - universal_fields: fields present in all records
      - blank_spaces: fields that are present in less than 30% of records
    """
    if not records:
        return {"field_coverage": {}, "missing_fields": [], "universal_fields": [], "blank_spaces": []}

    # Count occurrences of each attribute name across all records
    field_counts: dict[str, int] = defaultdict(int)
    total = len(records)

    for record in records:
        seen_fields: set[str] = set()
        for attr in record.get("attributes", []):
            name = attr.get("name", "").lower()
            if name and name not in seen_fields:
                field_counts[name] += 1
                seen_fields.add(name)

    # Compute coverage ratios
    coverage = {}
    universal = []
    blank_spaces = []
    partial = []

    for field, count in sorted(field_counts.items()):
        ratio = count / total
        coverage[field] = round(ratio, 3)

        if ratio >= 1.0:
            universal.append(field)
        elif ratio < 0.30:
            blank_spaces.append({"field": field, "coverage": round(ratio, 3), "present_in": count, "total": total})
        else:
            partial.append({"field": field, "coverage": round(ratio, 3), "present_in": count, "total": total})

    return {
        "field_coverage": coverage,
        "universal_fields": universal,
        "blank_spaces": blank_spaces,
        "partial_coverage": partial,
        "total_records": total,
        "total_unique_fields": len(field_counts),
    }


def find_gaps_for_record(
    record: dict[str, Any],
    all_records: list[dict[str, Any]],
    min_coverage: float = 0.5,
) -> list[dict[str, Any]]:
    """
    Find fields that this specific record is missing but most other
    records in the same category have.

    Returns a list of gaps with the field name and how common it is.
    """
    # Filter to same category/industry for meaningful comparison
    category = (record.get("category") or "").lower()
    industry = (record.get("industry") or "").lower()

    comparable = []
    for r in all_records:
        r_cat = (r.get("category") or "").lower()
        r_ind = (r.get("industry") or "").lower()
        if r_cat == category or r_ind == industry:
            comparable.append(r)

    if len(comparable) < 2:
        comparable = all_records

    coverage_report = analyze_field_coverage(comparable)

    # Find fields this record does not have
    record_fields = {a.get("name", "").lower() for a in record.get("attributes", [])}
    gaps = []

    for field, ratio in coverage_report["field_coverage"].items():
        if ratio >= min_coverage and field not in record_fields:
            gaps.append({
                "field": field,
                "coverage_in_similar": ratio,
                "message": f"Field '{field}' is present in {ratio*100:.0f}% of similar records but missing here",
            })

    gaps.sort(key=lambda g: -g["coverage_in_similar"])
    return gaps


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m discovery.blank_space <records_dir_or_json>")
        print()
        print("Analyzes field coverage across a set of product records.")
        sys.exit(1)

    path = sys.argv[1]

    # Support both a single JSON array file and a directory of JSON files
    from pathlib import Path
    p = Path(path)

    if p.is_file():
        with open(p, "r", encoding="utf-8") as f:
            records = json.load(f)
        if isinstance(records, dict):
            records = [records]
    else:
        records = []
        for f in p.glob("*.json"):
            with open(f, "r", encoding="utf-8") as fh:
                records.append(json.load(fh))

    report = analyze_field_coverage(records)

    print(f"Records analyzed: {report['total_records']}")
    print(f"Unique fields: {report['total_unique_fields']}")
    print(f"Universal fields: {len(report['universal_fields'])}")
    print()

    if report["blank_spaces"]:
        print("Blank spaces (< 30% coverage):")
        for bs in report["blank_spaces"]:
            print(f"  {bs['field']}: {bs['coverage']*100:.0f}% ({bs['present_in']}/{bs['total']})")

    if report["partial_coverage"]:
        print("\nPartial coverage:")
        for pc in report["partial_coverage"]:
            print(f"  {pc['field']}: {pc['coverage']*100:.0f}% ({pc['present_in']}/{pc['total']})")
