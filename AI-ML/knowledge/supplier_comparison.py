"""
Supplier comparison for the same or equivalent products.

Finds records for the same product from different suppliers and
compares their attribute values side-by-side.
"""

import sys
import json
from typing import Any

from knowledge.embed_products import query_similar


def find_same_product_across_suppliers(
    record: dict[str, Any],
    n_results: int = 5,
) -> list[dict[str, Any]]:
    """
    Find records that describe the same product but from different sources.

    Uses the part number and product name for a targeted similarity search.
    """
    part_number = record.get("part_number", "")
    product_name = record.get("product_name", "")

    # Search by part number for exact matches
    query = f"{part_number} {product_name}"
    candidates = query_similar(query, n_results=n_results + 1)

    # Remove self-match
    record_hash = record.get("content_hash", "")
    candidates = [c for c in candidates if c["id"] != record_hash][:n_results]

    return candidates


def compare_records(
    record_a: dict[str, Any],
    record_b: dict[str, Any],
) -> dict[str, Any]:
    """
    Compare two product records side-by-side.

    Returns a dict with matching fields, differing fields, and fields
    present in only one record.
    """
    # Compare top-level fields
    compare_fields = ["product_name", "manufacturer", "part_number", "description"]
    matches = {}
    differences = {}

    for field in compare_fields:
        val_a = record_a.get(field, "")
        val_b = record_b.get(field, "")
        if val_a == val_b:
            matches[field] = val_a
        else:
            differences[field] = {"record_a": val_a, "record_b": val_b}

    # Compare attributes by name
    attrs_a = {a["name"].lower(): a for a in record_a.get("attributes", [])}
    attrs_b = {a["name"].lower(): a for a in record_b.get("attributes", [])}

    all_attr_names = set(attrs_a.keys()) | set(attrs_b.keys())
    attr_matches = {}
    attr_differences = {}
    only_in_a = {}
    only_in_b = {}

    for name in sorted(all_attr_names):
        in_a = name in attrs_a
        in_b = name in attrs_b

        if in_a and in_b:
            if attrs_a[name].get("value") == attrs_b[name].get("value"):
                attr_matches[name] = attrs_a[name].get("value", "")
            else:
                attr_differences[name] = {
                    "record_a": attrs_a[name].get("value", ""),
                    "record_b": attrs_b[name].get("value", ""),
                }
        elif in_a:
            only_in_a[name] = attrs_a[name].get("value", "")
        else:
            only_in_b[name] = attrs_b[name].get("value", "")

    return {
        "field_matches": matches,
        "field_differences": differences,
        "attribute_matches": attr_matches,
        "attribute_differences": attr_differences,
        "only_in_record_a": only_in_a,
        "only_in_record_b": only_in_b,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python -m knowledge.supplier_comparison <record_a.json> <record_b.json>")
        sys.exit(1)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        record_a = json.load(f)
    with open(sys.argv[2], "r", encoding="utf-8") as f:
        record_b = json.load(f)

    comparison = compare_records(record_a, record_b)

    print("=== Field Matches ===")
    for k, v in comparison["field_matches"].items():
        print(f"  {k}: {v}")

    print("\n=== Field Differences ===")
    for k, v in comparison["field_differences"].items():
        print(f"  {k}: A={v['record_a']} | B={v['record_b']}")

    print("\n=== Attribute Differences ===")
    for k, v in comparison["attribute_differences"].items():
        print(f"  {k}: A={v['record_a']} | B={v['record_b']}")
