"""
Product revision history tracking.

Detects version/revision relationships between records that share the
same part number but have different revision dates, version numbers,
or content hashes.
"""

import sys
import json
from typing import Any

from knowledge.embed_products import query_similar, get_collection


def find_revisions(
    record: dict[str, Any],
    n_results: int = 10,
) -> list[dict[str, Any]]:
    """
    Find other records that appear to be revisions of the same product.

    Looks for records with matching part numbers or very high similarity
    that differ in version, date, or content hash.
    """
    part_number = record.get("part_number", "")
    product_name = record.get("product_name", "")
    content_hash = record.get("content_hash", "")

    if not part_number and not product_name:
        return []

    # Search by part number for precise matches
    query = part_number if part_number else product_name
    candidates = query_similar(query, n_results=n_results)

    # Filter to likely revisions (same part number or very high similarity)
    revisions = []
    for c in candidates:
        if c["id"] == content_hash:
            continue  # Skip self

        meta = c.get("metadata", {})
        candidate_part = meta.get("part_number", "")
        similarity = 1 - (c.get("distance", 1.0))

        # Same part number = likely revision
        is_same_part = (
            part_number
            and candidate_part
            and candidate_part.lower() == part_number.lower()
        )
        # Very high similarity = possible revision
        is_very_similar = similarity > 0.92

        if is_same_part or is_very_similar:
            revisions.append({
                "id": c["id"],
                "product_name": meta.get("product_name", ""),
                "part_number": candidate_part,
                "manufacturer": meta.get("manufacturer", ""),
                "similarity": round(similarity, 3),
                "likely_revision": is_same_part,
            })

    return revisions


def build_revision_timeline(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Given a list of records for the same product (different revisions),
    sort them by extracted_at timestamp to build a revision timeline.
    """
    sorted_records = sorted(
        records,
        key=lambda r: r.get("extracted_at", ""),
    )

    timeline = []
    for i, record in enumerate(sorted_records):
        entry = {
            "revision_index": i + 1,
            "product_name": record.get("product_name", ""),
            "part_number": record.get("part_number", ""),
            "content_hash": record.get("content_hash", ""),
            "extracted_at": record.get("extracted_at", ""),
            "attribute_count": len(record.get("attributes", [])),
        }
        timeline.append(entry)

    return timeline


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m knowledge.revision_history <record_json>")
        sys.exit(1)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        record = json.load(f)

    revisions = find_revisions(record)
    print(f"Revisions for: {record.get('product_name', '?')} ({record.get('part_number', '?')})")
    print(f"Found: {len(revisions)} potential revisions")

    for r in revisions:
        rev_flag = " [REVISION]" if r["likely_revision"] else ""
        print(f"  {r['product_name']} ({r['part_number']}) sim={r['similarity']:.3f}{rev_flag}")
