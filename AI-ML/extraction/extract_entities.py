"""
Entity extraction using instructor + LLM.

Takes document evidence text and extracts a structured ExtractionResult
using the LLM with schema enforcement. This is the core intelligence
step for Document Intelligence.
"""

import sys
import json
from typing import Any, Optional
from datetime import datetime, timezone

from config.llm_client import get_structured_output
from config.toon_utils import wrap_for_prompt
from extraction.schema_models import (
    ExtractionResult,
    DocumentRecord,
    ExtractedEntity,
)


SYSTEM_PROMPT = """You are a highly skilled document intelligence specialist and Named Entity Recognition (NER) expert. Your job is to extract structured entities from business documents such as invoices, contracts, receipts, letters, and purchase orders.

Rules:
- Extract every relevant entity you can find. Note: Do not invent missing entities just because they are common. If an entity is missing from the document, simply omit it.
- Extract the following entity types:
  * PERSON: Names of signers, individuals, or contacts.
  * ORG: Company names, banks, vendor organizations, clients.
  * DATE: Invoice dates, due dates, contract start/end dates.
  * MONEY: Financial amounts, totals, taxes, line item prices.
  * GPE: Locations, addresses, countries, states, cities.
  * INVOICE_NUMBER / PO_NUMBER: Invoice or Purchase Order IDs.
  * LAW / CLAUSE: Legal clause references or governing laws in contracts.
- For each entity, include the exact source text snippet where you found it.
- If a value has a unit (e.g. USD, EUR, kg), separate the numeric value and unit.
- If you are uncertain about an extraction, still extract it but note lower confidence.
- Do not invent or hallucinate values. If something is not in the document, skip it.
- Extract the document title or infer a suitable name.
- Write a brief summary explaining the main intent of the document.

IMPORTANT: You must follow the requested JSON schema EXACTLY. Ensure you include ALL required fields, including any `confidence`, `human_verified`, and nested fields. Do not skip top-level fields."""


def extract_from_evidence(
    evidence: dict[str, Any],
    provider: str = "local",
    extra_instructions: str = "",
) -> ExtractionResult:
    """
    Extract structured document entities from a DocumentEvidence dict.

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

    prompt = f"""Extract all entities from the following business document.

{source_info}

[document_text]
{doc_text}

{extra_instructions}

Extract the document title, primary party, date, summary, and every relevant named entity you can find. For each entity, include the source text snippet where you found it and the page number if possible."""

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
            document_title="Unknown Document (Extraction Failed)",
            primary_party="Unknown",
            document_date="Unknown",
            summary="The AI model failed to extract structured data from this document due to length limits or formatting errors.",
            entities=[]
        )

    return result


def extraction_to_record(
    extraction: ExtractionResult,
    evidence: dict[str, Any],
) -> DocumentRecord:
    """
    Convert a raw ExtractionResult into a DocumentRecord.

    This is a mapping step -- validation and confidence scoring happen
    separately in their own modules.
    """
    record = DocumentRecord(
        document_title=extraction.document_title,
        primary_party=extraction.primary_party,
        document_date=extraction.document_date,
        summary=extraction.summary,
        entities=extraction.entities,
        financial_summary=extraction.financial_summary,
        key_dates=extraction.key_dates,
        source_file=evidence.get("source_file"),
        content_hash=evidence.get("content_hash"),
        extracted_at=datetime.now(timezone.utc).isoformat(),
    )

    return record


def extract_record_from_evidence(
    evidence: dict[str, Any],
    provider: str = "local",
    extra_instructions: str = "",
) -> DocumentRecord:
    """
    Convenience function: extract and convert in one call.

    Returns a DocumentRecord ready for validation and scoring.
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
        print("Usage: python -m extraction.extract_entities <evidence_json>")
        print()
        print("Extracts document entities from a DocumentEvidence JSON file.")
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

    print(f"Title: {record.document_title}")
    print(f"Primary Party: {record.primary_party}")
    print(f"Date: {record.document_date}")
    print(f"Summary: {record.summary}")
    print(f"Entities extracted: {len(record.entities)}")
    print()

    for attr in record.entities:
        unit_str = f" ({attr.unit})" if attr.unit else ""
        source_str = f' [from: "{attr.source_text[:60]}..."]' if attr.source_text else ""
        print(f"  [{attr.entity_type}] {attr.value}{unit_str}{source_str}")
