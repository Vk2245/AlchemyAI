"""
Record-level confidence scoring.

Aggregates field-level scores into an overall record confidence.
Also factors in validation results and completeness metrics.
"""

import sys
import json

from extraction.schema_models import TrustedProductRecord
from confidence.score_fields import score_all_fields, REVIEW_THRESHOLD


def score_record(record: TrustedProductRecord) -> TrustedProductRecord:
    """
    Compute the overall record confidence score.

    The record score combines:
    - Average field confidence (weighted 50%)
    - Validation pass rate (weighted 30%)
    - Completeness: ratio of non-empty core fields (weighted 20%)

    Updates record.record_confidence in place and returns the record.
    """
    # Make sure field scores are computed first
    record = score_all_fields(record)

    # 1. Average field confidence
    if record.attributes:
        avg_field_conf = sum(a.confidence for a in record.attributes) / len(record.attributes)
    else:
        avg_field_conf = 0.0

    # 2. Validation pass rate
    validation_score = 1.0 if record.validation_passed else 0.3

    # 3. Completeness of core fields
    core_fields = ["product_name", "manufacturer", "part_number", "description"]
    filled = sum(
        1 for f in core_fields
        if getattr(record, f, None) and str(getattr(record, f, "")).strip()
    )
    completeness = filled / len(core_fields)

    # Weighted combination
    record_score = (
        avg_field_conf * 0.50
        + validation_score * 0.30
        + completeness * 0.20
    )

    record.record_confidence = round(record_score, 3)
    return record


def get_confidence_summary(record: TrustedProductRecord) -> dict:
    """
    Return a summary dict of confidence metrics for display.
    """
    high_conf = [a for a in record.attributes if a.confidence >= 0.7]
    medium_conf = [a for a in record.attributes if 0.4 <= a.confidence < 0.7]
    low_conf = [a for a in record.attributes if a.confidence < 0.4]

    return {
        "record_confidence": record.record_confidence,
        "total_attributes": len(record.attributes),
        "high_confidence": len(high_conf),
        "medium_confidence": len(medium_conf),
        "low_confidence": len(low_conf),
        "fields_for_review": record.fields_for_review,
        "validation_passed": record.validation_passed,
    }


# ---------------------------------------------------------------------------
# CLI: score a full record
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m confidence.score_record <record_json>")
        print()
        print("Computes the overall record confidence score.")
        sys.exit(1)

    record_path = sys.argv[1]

    with open(record_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    record = TrustedProductRecord(**data)
    record = score_record(record)
    summary = get_confidence_summary(record)

    print(f"Product: {record.product_name}")
    print(f"Record confidence: {summary['record_confidence']:.3f}")
    print(f"Total attributes: {summary['total_attributes']}")
    print(f"  High confidence (>=0.7): {summary['high_confidence']}")
    print(f"  Medium confidence (0.4-0.7): {summary['medium_confidence']}")
    print(f"  Low confidence (<0.4): {summary['low_confidence']}")
    print(f"Validation passed: {summary['validation_passed']}")

    if summary["fields_for_review"]:
        print(f"Fields for review: {', '.join(summary['fields_for_review'])}")
