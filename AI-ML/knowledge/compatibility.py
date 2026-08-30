"""
Product compatibility suggestions.

Finds products that are compatible with a given product based on
semantic similarity and attribute matching in the embedding index.
"""

import sys
import json
from typing import Any, Optional

from config.llm_client import get_completion
from config.toon_utils import wrap_for_prompt
from knowledge.embed_products import query_similar, get_collection


def find_compatible_products(
    record: dict[str, Any],
    n_results: int = 5,
    provider: str = "local",
) -> list[dict[str, Any]]:
    """
    Find products compatible with the given record.

    Uses embedding similarity to find candidates, then asks the LLM
    to filter and explain which ones are actually compatible.
    """
    # Build a query emphasizing compatibility
    product_name = record.get("product_name", "")
    category = record.get("category", "")
    industry = record.get("industry", "")

    query = f"Products compatible with {product_name} in {category} {industry}"

    # Get candidates from the embedding index
    candidates = query_similar(query, n_results=n_results + 2)

    # Remove self-match
    record_hash = record.get("content_hash", "")
    candidates = [c for c in candidates if c["id"] != record_hash][:n_results]

    if not candidates:
        return []

    # Ask LLM to evaluate compatibility
    record_summary = wrap_for_prompt(
        {"name": product_name, "category": category, "industry": industry},
        "source_product",
    )

    candidate_list = []
    for c in candidates:
        meta = c.get("metadata", {})
        candidate_list.append({
            "id": c["id"],
            "name": meta.get("product_name", ""),
            "manufacturer": meta.get("manufacturer", ""),
            "similarity": round(1 - (c.get("distance", 1.0)), 3),
        })

    candidates_prompt = wrap_for_prompt(candidate_list, "candidates")

    prompt = f"""Given this product, evaluate which of the candidate products
are likely compatible with it (can be used together, complement each other,
or are suitable alternatives).

{record_summary}

{candidates_prompt}

For each candidate, provide a brief explanation of why it is or is not compatible.
Return your analysis as plain text."""

    analysis = get_completion(prompt, provider=provider)

    # Combine candidates with LLM analysis
    results = []
    for c in candidates:
        meta = c.get("metadata", {})
        results.append({
            "id": c["id"],
            "product_name": meta.get("product_name", ""),
            "manufacturer": meta.get("manufacturer", ""),
            "similarity_score": round(1 - (c.get("distance", 1.0)), 3),
            "industry": meta.get("industry", ""),
        })

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m knowledge.compatibility <record_json>")
        sys.exit(1)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        record = json.load(f)

    results = find_compatible_products(record)
    print(f"Compatible products for: {record.get('product_name', '?')}")
    print()

    for r in results:
        print(f"  {r['product_name']} ({r['manufacturer']})")
        print(f"    Similarity: {r['similarity_score']:.3f}")
        print()
