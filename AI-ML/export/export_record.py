"""
Export a trusted product record into a clean JSON payload.

Formats the final record with all intelligence layers (knowledge,
reasoning, confidence) into a structured JSON contract. The shape
will be finalized once the shared/ contract is agreed with the
full-stack teammate.
"""

import sys
import json
from typing import Any
from datetime import datetime, timezone

from extraction.schema_models import TrustedProductRecord


def export_record(
    record: TrustedProductRecord,
    knowledge_data: dict[str, Any] | None = None,
    reasoning_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Format a trusted record into the export JSON payload.

    Combines the core record with optional knowledge and reasoning
    layer outputs into one structured document.
    """
    # Core record data
    export = {
        "schema_version": "1.0.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),

        # Identity
        "product": {
            "name": record.product_name,
            "manufacturer": record.manufacturer,
            "part_number": record.part_number,
            "description": record.description,
        },

        # Classification
        "classification": {
            "industry": record.industry,
            "category": record.category,
            "subcategory": record.subcategory,
            "industry_profile": record.industry_profile,
        },

        # Attributes with provenance
        "attributes": [
            {
                "name": attr.name,
                "value": attr.value,
                "unit": attr.unit,
                "numeric_value": attr.numeric_value,
                "confidence": attr.confidence,
                "source_text": attr.source_text,
                "source_page": attr.source_page,
            }
            for attr in record.attributes
        ],

        # Dynamic (industry-specific) attributes
        "dynamic_attributes": record.dynamic_attributes,

        # Quality metrics
        "quality": {
            "record_confidence": record.record_confidence,
            "validation_passed": record.validation_passed,
            "validation_errors": record.validation_errors,
            "fields_for_review": record.fields_for_review,
        },

        # Provenance
        "provenance": {
            "source_file": record.source_file,
            "content_hash": record.content_hash,
            "extracted_at": record.extracted_at,
        },
    }

    # Knowledge layer (Stage 3)
    if knowledge_data:
        export["knowledge"] = knowledge_data

    # Reasoning layer (Stage 6)
    if reasoning_data:
        export["reasoning"] = reasoning_data

    return export


def export_to_file(
    record: TrustedProductRecord,
    output_path: str,
    knowledge_data: dict[str, Any] | None = None,
    reasoning_data: dict[str, Any] | None = None,
) -> str:
    """
    Export a record to a JSON file. Returns the output file path.
    """
    payload = export_record(record, knowledge_data, reasoning_data)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    return output_path


def export_batch(
    records: list[TrustedProductRecord],
) -> list[dict[str, Any]]:
    """Export a batch of records as a list of export payloads."""
    return [export_record(r) for r in records]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m export.export_record <record_json> [output_path]")
        sys.exit(1)

    record_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    with open(record_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    record = TrustedProductRecord(**data)
    payload = export_record(record)

    if output_path:
        export_to_file(record, output_path)
        print(f"Exported to: {output_path}")
    else:
        print(json.dumps(payload, indent=2))
