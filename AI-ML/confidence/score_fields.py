"""
Field-level confidence scoring.

Scores each attribute in a product record based on extraction quality
signals: whether source text is present, whether a numeric value was
parsed, unit presence, and value completeness.
"""

from extraction.schema_models import ProductAttribute, TrustedProductRecord


# Default weights for each scoring factor
DEFAULT_WEIGHTS: dict[str, float] = {
    "has_source_text": 0.30,
    "has_numeric_value": 0.15,
    "has_unit": 0.10,
    "value_not_empty": 0.25,
    "source_page_present": 0.10,
    "value_length": 0.10,
}

# Review threshold: attributes below this score get flagged
REVIEW_THRESHOLD: float = 0.5


def score_attribute(
    attr: ProductAttribute,
    weights: dict[str, float] | None = None,
    calibration_offset: float = 0.0,
) -> float:
    """
    Compute a confidence score for a single attribute.

    The score is a weighted sum of boolean signals about extraction quality.
    calibration_offset is added by the memory module (Stage 4) to adjust
    scores for attributes that historically get corrected.

    Returns a float between 0.0 and 1.0.
    """
    w = weights or DEFAULT_WEIGHTS
    score = 0.0

    # Does the attribute have source text (provenance)?
    if attr.source_text and len(attr.source_text.strip()) > 0:
        score += w.get("has_source_text", 0.0)

    # Was a numeric value successfully parsed?
    if attr.numeric_value is not None:
        score += w.get("has_numeric_value", 0.0)

    # Is a unit specified?
    if attr.unit and len(attr.unit.strip()) > 0:
        score += w.get("has_unit", 0.0)

    # Is the value non-empty?
    if attr.value and len(attr.value.strip()) > 0:
        score += w.get("value_not_empty", 0.0)

    # Is the source page recorded?
    if attr.source_page is not None and attr.source_page > 0:
        score += w.get("source_page_present", 0.0)

    # Value length signal: longer values tend to be more specific
    if attr.value and len(attr.value.strip()) >= 3:
        score += w.get("value_length", 0.0)

    # Apply calibration offset from memory module
    score = max(0.0, min(1.0, score + calibration_offset))

    return round(score, 3)


def score_all_fields(
    record: TrustedProductRecord,
    weights: dict[str, float] | None = None,
    calibration_offsets: dict[str, float] | None = None,
) -> TrustedProductRecord:
    """
    Score every attribute in the record and update their confidence values.

    Also flags low-confidence attributes for human review.
    Returns the same record with updated confidence scores.
    """
    offsets = calibration_offsets or {}
    review_fields: list[str] = []

    for attr in record.attributes:
        offset = offsets.get(attr.name.lower(), 0.0)
        attr.confidence = score_attribute(attr, weights=weights, calibration_offset=offset)

        if attr.confidence < REVIEW_THRESHOLD:
            review_fields.append(attr.name)

    # Update the record's review list (merge with any existing entries)
    existing_review = set(record.fields_for_review)
    existing_review.update(review_fields)
    record.fields_for_review = sorted(existing_review)

    return record


# ---------------------------------------------------------------------------
# CLI: score a record's fields
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python -m confidence.score_fields <record_json>")
        print()
        print("Scores each attribute's confidence in a TrustedProductRecord.")
        sys.exit(1)

    record_path = sys.argv[1]

    with open(record_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    record = TrustedProductRecord(**data)
    record = score_all_fields(record)

    print(f"Product: {record.product_name}")
    print(f"Attributes scored: {len(record.attributes)}")
    print()

    for attr in record.attributes:
        flag = " [REVIEW]" if attr.confidence < REVIEW_THRESHOLD else ""
        print(f"  {attr.name}: {attr.confidence:.3f}{flag}")

    print()
    if record.fields_for_review:
        print(f"Fields for review: {', '.join(record.fields_for_review)}")
