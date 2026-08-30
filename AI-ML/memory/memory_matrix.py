"""
Industrial memory matrix.

Aggregates correction patterns by field and category to show
which types of products and attributes are most error-prone.
This is the data the dashboard uses to display correction trends.
"""

import sys
import json
from typing import Any
from collections import defaultdict

from memory.correction_log import get_corrections


def build_memory_matrix() -> dict[str, Any]:
    """
    Aggregate correction patterns into a matrix indexed by field and category.

    Returns a dict with:
      - by_field: correction counts per field name
      - by_category: correction counts per product category
      - by_industry: correction counts per industry
      - cross_matrix: field x category counts
      - total: total correction count
    """
    corrections = get_corrections(limit=10000)

    by_field: dict[str, int] = defaultdict(int)
    by_category: dict[str, int] = defaultdict(int)
    by_industry: dict[str, int] = defaultdict(int)
    cross_matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for c in corrections:
        field = c.get("field_name", "unknown").lower()
        category = c.get("category", "unknown").lower()
        industry = c.get("industry", "unknown").lower()

        by_field[field] += 1
        by_category[category] += 1
        by_industry[industry] += 1
        cross_matrix[field][category] += 1

    return {
        "by_field": dict(by_field),
        "by_category": dict(by_category),
        "by_industry": dict(by_industry),
        "cross_matrix": {k: dict(v) for k, v in cross_matrix.items()},
        "total": len(corrections),
    }


def get_error_prone_combinations(
    min_count: int = 2,
) -> list[dict[str, Any]]:
    """
    Return field-category combinations that are frequently corrected.

    Useful for proactively flagging these combinations for review
    in future extractions.
    """
    matrix = build_memory_matrix()
    combinations = []

    for field, categories in matrix["cross_matrix"].items():
        for category, count in categories.items():
            if count >= min_count:
                combinations.append({
                    "field": field,
                    "category": category,
                    "correction_count": count,
                })

    combinations.sort(key=lambda x: -x["correction_count"])
    return combinations


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    matrix = build_memory_matrix()

    print(f"Total corrections: {matrix['total']}")
    print()

    if matrix["by_field"]:
        print("Corrections by field:")
        for field, count in sorted(matrix["by_field"].items(), key=lambda x: -x[1]):
            print(f"  {field}: {count}")

    if matrix["by_industry"]:
        print("\nCorrections by industry:")
        for industry, count in sorted(matrix["by_industry"].items(), key=lambda x: -x[1]):
            print(f"  {industry}: {count}")

    combos = get_error_prone_combinations()
    if combos:
        print("\nError-prone field-category combinations:")
        for c in combos[:10]:
            print(f"  {c['field']} + {c['category']}: {c['correction_count']} corrections")
