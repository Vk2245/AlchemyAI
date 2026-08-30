"""
Duplicate product detection.

Flags record pairs above a similarity threshold in the embedding index.
Uses the shared ChromaDB index from the knowledge layer.
"""

import sys
import json
from typing import Any

from knowledge.embed_products import query_similar, get_collection, get_collection_count


# Default similarity threshold for flagging duplicates
DUPLICATE_THRESHOLD: float = 0.90


def find_duplicates(
    record: dict[str, Any],
    threshold: float = DUPLICATE_THRESHOLD,
    n_candidates: int = 10,
) -> list[dict[str, Any]]:
    """
    Find records that are likely duplicates of the given record.

    Returns records with similarity above the threshold, excluding
    exact self-matches.
    """
    product_name = record.get("product_name", "")
    part_number = record.get("part_number", "")
    description = record.get("description", "")

    query = f"{product_name} {part_number} {description}"
    candidates = query_similar(query, n_results=n_candidates)

    content_hash = record.get("content_hash", "")
    duplicates = []

    for c in candidates:
        if c["id"] == content_hash:
            continue

        similarity = 1 - (c.get("distance", 1.0))
        if similarity >= threshold:
            meta = c.get("metadata", {})
            duplicates.append({
                "id": c["id"],
                "product_name": meta.get("product_name", ""),
                "manufacturer": meta.get("manufacturer", ""),
                "part_number": meta.get("part_number", ""),
                "similarity": round(similarity, 3),
                "is_likely_duplicate": similarity >= 0.95,
            })

    return duplicates


def scan_all_for_duplicates(
    records: list[dict[str, Any]],
    threshold: float = DUPLICATE_THRESHOLD,
) -> list[dict[str, Any]]:
    """
    Scan all records and return pairs that are likely duplicates.

    Deduplicates pairs so each pair only appears once.
    """
    seen_pairs: set[tuple[str, str]] = set()
    duplicate_pairs = []

    for record in records:
        record_id = record.get("content_hash", "")
        dups = find_duplicates(record, threshold=threshold)

        for dup in dups:
            pair = tuple(sorted([record_id, dup["id"]]))
            if pair not in seen_pairs:
                seen_pairs.add(pair)
                duplicate_pairs.append({
                    "record_a_id": record_id,
                    "record_a_name": record.get("product_name", ""),
                    "record_b_id": dup["id"],
                    "record_b_name": dup["product_name"],
                    "similarity": dup["similarity"],
                })

    duplicate_pairs.sort(key=lambda d: -d["similarity"])
    return duplicate_pairs


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m discovery.duplicate_detection <record_json>")
        sys.exit(1)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        record = json.load(f)

    duplicates = find_duplicates(record)
    print(f"Duplicate check for: {record.get('product_name', '?')}")
    print(f"Found: {len(duplicates)} potential duplicates")

    for d in duplicates:
        flag = " [LIKELY DUPLICATE]" if d["is_likely_duplicate"] else ""
        print(f"  {d['product_name']} ({d['part_number']}) sim={d['similarity']:.3f}{flag}")
