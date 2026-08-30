"""
Attribute extraction using instructor + LLM.

Takes document evidence text and extracts a structured ExtractionResult
using the LLM with schema enforcement. This is the core intelligence
step: raw text in, structured product record out.
"""

import sys
import json
from typing import Any, Optional
from datetime import datetime, timezone

from config.llm_client import get_structured_output
from config.toon_utils import wrap_for_prompt
from extraction.schema_models import (
    ExtractionResult,
    TrustedProductRecord,
    ProductAttribute,
)


SYSTEM_PROMPT = """You are a product data extraction specialist. Your job is to
extract structured product information from technical documents such as datasheets,
spec sheets, catalogs, and product descriptions.

Rules:
- Extract every relevant technical attribute you can find. Note: Do not invent missing attributes just because they are common. If an attribute is missing from the document, simply omit it.
- For each attribute, include the exact source text snippet where you found it
- If a value has a unit, separate the numeric value and unit
- If you are uncertain about a value, still extract it but note lower confidence
- Do not invent or hallucinate values. If something is not in the document, skip it
- Extract the product name, manufacturer, and part number if present
- Write a brief description summarizing what the product is

IMPORTANT: You must follow the requested JSON schema EXACTLY. Ensure you include ALL required fields, including any `confidence`, `reasoning`, and nested fields. Do not skip top-level fields."""


def extract_from_evidence(
    evidence: dict[str, Any],
    provider: str = "local",
    extra_instructions: str = "",
) -> ExtractionResult:
    """
    Extract structured product attributes from a DocumentEvidence dict.

    Uses the full markdown text (which preserves tables) for best results.
    The LLM is prompted with the document text and returns a validated
    ExtractionResult via instructor.
    """
    # Use markdown text (preserves tables better) with fallback to raw text
    doc_text = evidence.get("full_markdown", evidence.get("full_text", ""))

    # Truncate if extremely long (avoid token limits on local models)
    # Qwen 2B has 8192 token context; ~3 chars/token, so 4000 chars ≈ 1300 tokens
    max_chars = 4000
    if len(doc_text) > max_chars:
        doc_text = doc_text[:max_chars] + "\n\n[Document truncated for extraction]"

    # Build the prompt
    source_info = wrap_for_prompt(
        {"file": evidence.get("source_file", "unknown"), "pages": evidence.get("page_count", 0)},
        "source_metadata",
    )

    prompt = f"""Extract all product information from the following document.

{source_info}

[document_text]
{doc_text}

{extra_instructions}

Extract the product name, manufacturer, part number, description, and every
technical attribute you can find. For each attribute, include the source text
snippet where you found it and the page number if possible."""

    try:
        result = get_structured_output(
            prompt=prompt,
            response_model=ExtractionResult,
            system_prompt=SYSTEM_PROMPT,
            provider=provider,
        )
    except Exception as e:
        print(f"Extraction failed or hit token limit: {e}")
        # Return a fallback empty result so the pipeline doesn't crash
        result = ExtractionResult(
            product_name="Unknown Product (Extraction Failed)",
            manufacturer="Unknown",
            part_number="Unknown",
            description="The AI model failed to extract structured data from this document due to length limits or formatting errors.",
            technical_attributes=[],
            features=[],
            applications=[]
        )

    return result


def extraction_to_record(
    extraction: ExtractionResult,
    evidence: dict[str, Any],
) -> TrustedProductRecord:
    """
    Convert a raw ExtractionResult into a TrustedProductRecord.

    This is a mapping step -- validation and confidence scoring happen
    separately in their own modules.
    """
    record = TrustedProductRecord(
        product_name=extraction.product_name,
        manufacturer=extraction.manufacturer,
        part_number=extraction.part_number,
        description=extraction.description,
        attributes=extraction.attributes,
        source_file=evidence.get("source_file"),
        content_hash=evidence.get("content_hash"),
        extracted_at=datetime.now(timezone.utc).isoformat(),
    )

    return record


def extract_record_from_evidence(
    evidence: dict[str, Any],
    provider: str = "local",
    extra_instructions: str = "",
) -> TrustedProductRecord:
    """
    Convenience function: extract and convert in one call.

    Returns a TrustedProductRecord ready for validation and scoring.
    """
    extraction = extract_from_evidence(
        evidence, provider=provider, extra_instructions=extra_instructions
    )
    return extraction_to_record(extraction, evidence)


# ---------------------------------------------------------------------------
# CLI: extract from a saved evidence JSON file
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m extraction.extract_attributes <evidence_json>")
        print()
        print("Extracts product attributes from a DocumentEvidence JSON file.")
        print("Generate evidence first with: python -m ingestion.evidence_builder <pdf>")
        sys.exit(1)

    evidence_path = sys.argv[1]
    provider = sys.argv[2] if len(sys.argv) > 2 else "local"

    print(f"Loading evidence: {evidence_path}")
    with open(evidence_path, "r", encoding="utf-8") as f:
        evidence = json.load(f)

    print(f"Source: {evidence.get('source_file', 'unknown')}")
    print(f"Provider: {provider}")
    print("Extracting...")
    print()

    record = extract_record_from_evidence(evidence, provider=provider)

    print(f"Product: {record.product_name}")
    print(f"Manufacturer: {record.manufacturer}")
    print(f"Part Number: {record.part_number}")
    print(f"Description: {record.description}")
    print(f"Attributes extracted: {len(record.attributes)}")
    print()

    for attr in record.attributes:
        unit_str = f" ({attr.unit})" if attr.unit else ""
        source_str = f' [from: "{attr.source_text[:60]}..."]' if attr.source_text else ""
        print(f"  {attr.name}: {attr.value}{unit_str}{source_str}")
