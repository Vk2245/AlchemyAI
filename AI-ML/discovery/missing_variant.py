"""
Missing variant detection.

Compares attribute value sets across similar products to spot variants
that should exist but do not. For example, if a product family has
24V and 48V variants but no 12V variant, this module flags it.
"""

import sys
import json
from typing import Any
from collections import defaultdict

from knowledge.similar_products import find_similar_products


def detect_missing_variants(
    records: list[dict[str, Any]],
    variant_fields: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Analyze a set of records for missing product variants.

    Groups records by product family (same manufacturer + similar name),
    then for each variant field (e.g. voltage, size), checks what values
    exist and whether there are gaps in the expected value set.

    If variant_fields is not specified, uses common variant fields.
    """
    if variant_fields is None:
        variant_fields = [
            "voltage rating", "current rating", "size", "color",
            "capacity", "version", "power rating", "temperature range",
        ]

    # Group records by manufacturer + approximate product family
    families: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        manufacturer = (record.get("manufacturer") or "unknown").lower()
        name = (record.get("product_name") or "unknown").lower()
        # Use first few words of name as family key
        name_key = " ".join(name.split()[:3])
        family_key = f"{manufacturer}|{name_key}"
        families[family_key].append(record)

    # Only analyze families with multiple members
    missing_variants = []

    for family_key, family_records in families.items():
        if len(family_records) < 2:
            continue

        # For each variant field, collect the values across the family
        for field_name in variant_fields:
            values_seen: set[str] = set()
            for record in family_records:
                for attr in record.get("attributes", []):
                    if attr.get("name", "").lower() == field_name.lower():
                        values_seen.add(attr.get("value", ""))

            if len(values_seen) >= 2:
                # There are variants -- flag this for review
                missing_variants.append({
                    "family": family_key,
                    "field": field_name,
                    "existing_values": sorted(values_seen),
                    "family_size": len(family_records),
                    "message": (
                        f"Product family '{family_key.split('|')[1]}' has "
                        f"{len(values_seen)} variants for '{field_name}': "
                        f"{', '.join(sorted(values_seen))}. "
                        f"Check if additional variants are expected."
                    ),
                })

    return missing_variants


def suggest_missing_values(
    existing_values: list[str],
) -> list[str]:
    """
    Given a list of existing variant values, suggest values that might
    be missing from the set.

    This is a simple heuristic for numeric sequences. For example,
    if [12V, 24V, 48V] exists, it might suggest 36V.
    """
    # Try to parse as numeric values
    numerics = []
    for v in existing_values:
        cleaned = ""
        for c in v:
            if c.isdigit() or c == ".":
                cleaned += c
        if cleaned:
            try:
                numerics.append(float(cleaned))
            except ValueError:
                pass

    if len(numerics) < 2:
        return []

    numerics.sort()

    # Check for regular spacing
    diffs = [numerics[i+1] - numerics[i] for i in range(len(numerics) - 1)]
    if not diffs:
        return []

    # If spacing is roughly uniform, suggest missing values
    avg_diff = sum(diffs) / len(diffs)
    suggestions = []

    for i in range(len(numerics) - 1):
        if diffs[i] > avg_diff * 1.5:
            # Gap detected -- suggest intermediate values
            gap_count = round(diffs[i] / avg_diff) - 1
            for j in range(1, gap_count + 1):
                suggested_val = numerics[i] + avg_diff * j
                if suggested_val not in numerics:
                    suggestions.append(str(int(suggested_val)) if suggested_val == int(suggested_val) else str(suggested_val))

    return suggestions


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m discovery.missing_variant <records_json>")
        sys.exit(1)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        data = json.load(f)

    records = data if isinstance(data, list) else [data]
    variants = detect_missing_variants(records)

    print(f"Analyzed {len(records)} records")
    print(f"Missing variant opportunities: {len(variants)}")

    for v in variants:
        print(f"\n  Family: {v['family']}")
        print(f"  Field: {v['field']}")
        print(f"  Existing: {', '.join(v['existing_values'])}")

        suggestions = suggest_missing_values(v["existing_values"])
        if suggestions:
            print(f"  Suggested missing: {', '.join(suggestions)}")
