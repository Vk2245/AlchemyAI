"""
Record-level confidence scoring.

Aggregates entity-level scores into an overall record confidence.
Also factors in completeness metrics.
"""

import sys
import json

from extraction.schema_models import DocumentRecord

def score_record(record: DocumentRecord) -> DocumentRecord:
    """
    Compute the overall record confidence score.

    The record score combines:
    - Average entity confidence (weighted 70%)
    - Completeness: ratio of non-empty core fields (weighted 30%)

    Updates record.record_confidence in place and returns the record.
    """
    # 1. Average entity confidence
    if record.entities:
        avg_entity_conf = sum(e.confidence for e in record.entities) / len(record.entities)
    else:
        avg_entity_conf = 0.5  # Neutral fallback if no entities extracted but doc processed

    # 2. Completeness of core fields
    core_fields = ["document_title", "primary_party", "document_date"]
    filled = sum(
        1 for f in core_fields
        if getattr(record, f, None) and str(getattr(record, f, "")).strip()
    )
    completeness = filled / len(core_fields)

    # Weighted combination
    record_score = (avg_entity_conf * 0.70) + (completeness * 0.30)

    record.record_confidence = round(record_score, 3)
    return record


def get_confidence_summary(record: DocumentRecord) -> dict:
    """
    Return a summary dict of confidence metrics for display.
    """
    high_conf = [e for e in record.entities if e.confidence >= 0.7]
    medium_conf = [e for e in record.entities if 0.4 <= e.confidence < 0.7]
    low_conf = [e for e in record.entities if e.confidence < 0.4]

    return {
        "record_confidence": record.record_confidence,
        "total_entities": len(record.entities),
        "high_confidence": len(high_conf),
        "medium_confidence": len(medium_conf),
        "low_confidence": len(low_conf),
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m confidence.score_record <record_json>")
        sys.exit(1)

    record_path = sys.argv[1]

    with open(record_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    record = DocumentRecord(**data)
    record = score_record(record)
    summary = get_confidence_summary(record)

    print(f"Document: {record.document_title}")
    print(f"Record confidence: {summary['record_confidence']:.3f}")
    print(f"Total entities: {summary['total_entities']}")
