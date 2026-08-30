"""
Similar product discovery.

Finds products similar to a given product using the shared embedding
index. Simpler than compatibility -- pure nearest-neighbor search.
"""

import sys
import json
from typing import Any, Optional

from knowledge.embed_products import query_similar


def find_similar_products(
    record: dict[str, Any],
    n_results: int = 5,
    industry_filter: Optional[str] = None,
) -> list[dict[str, Any]]:
    """
    Find products most similar to the given record.

    Returns a list of similar products ranked by embedding distance.
    Optionally filters by industry.
    """
    product_name = record.get("product_name", "")
    description = record.get("description", "")
    query = f"{product_name}. {description}"

    where_filter = None
    if industry_filter:
        where_filter = {"industry": industry_filter}

    candidates = query_similar(
        query, n_results=n_results + 1, where_filter=where_filter
    )

    # Remove self-match
    record_hash = record.get("content_hash", "")
    candidates = [c for c in candidates if c["id"] != record_hash][:n_results]

    results = []
    for c in candidates:
        meta = c.get("metadata", {})
        results.append({
            "id": c["id"],
            "product_name": meta.get("product_name", ""),
            "manufacturer": meta.get("manufacturer", ""),
            "similarity_score": round(1 - (c.get("distance", 1.0)), 3),
            "industry": meta.get("industry", ""),
            "category": meta.get("category", ""),
        })

    return results


def find_alternatives(
    record: dict[str, Any],
    n_results: int = 5,
) -> list[dict[str, Any]]:
    """
    Find alternative products -- similar products from different manufacturers.
    """
    all_similar = find_similar_products(record, n_results=n_results * 2)

    manufacturer = (record.get("manufacturer") or "").lower()
    alternatives = [
        r for r in all_similar
        if (r.get("manufacturer") or "").lower() != manufacturer
    ]

    return alternatives[:n_results]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m knowledge.similar_products <record_json>")
        sys.exit(1)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        record = json.load(f)

    print(f"Similar products for: {record.get('product_name', '?')}")
    results = find_similar_products(record)

    for r in results:
        print(f"  {r['product_name']} by {r['manufacturer']} (sim: {r['similarity_score']:.3f})")
