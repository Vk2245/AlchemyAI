"""
API-ready output formatting.

Thin formatting layer that the full-stack side calls directly.
Wraps the export payload with HTTP-style response metadata.
"""

import sys
import json
from typing import Any
from datetime import datetime, timezone

from extraction.schema_models import TrustedProductRecord
from export.export_record import export_record


def format_api_response(
    record: TrustedProductRecord,
    request_id: str = "",
    knowledge_data: dict[str, Any] | None = None,
    reasoning_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Format a record into an API-ready response envelope.

    Wraps the export payload with metadata the backend expects:
    status, request_id, timestamp, and the data payload.
    """
    payload = export_record(record, knowledge_data, reasoning_data)

    return {
        "status": "success",
        "request_id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": payload,
    }


def format_batch_response(
    records: list[TrustedProductRecord],
    request_id: str = "",
) -> dict[str, Any]:
    """Format a batch of records into an API-ready response."""
    payloads = [export_record(r) for r in records]

    return {
        "status": "success",
        "request_id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "count": len(payloads),
        "data": payloads,
    }


def format_error_response(
    error_message: str,
    request_id: str = "",
) -> dict[str, Any]:
    """Format an error into an API-ready error response."""
    return {
        "status": "error",
        "request_id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "error": error_message,
        "data": None,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m export.api_ready_output <record_json>")
        sys.exit(1)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        data = json.load(f)

    record = TrustedProductRecord(**data)
    response = format_api_response(record, request_id="test-001")

    print(json.dumps(response, indent=2))
