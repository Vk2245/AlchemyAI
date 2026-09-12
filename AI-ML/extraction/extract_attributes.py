"""
Entity extraction using instructor + LLM.

Takes document evidence text and extracts a structured ExtractionResult
using the LLM with schema enforcement. This is the core intelligence
step: raw text in, structured document record out.
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


SYSTEM_PROMPT = """You are an elite Document Intelligence and adaptive Named Entity Recognition (NER) specialist. 
Your job is to extract structured entities from any business document (e.g., invoices, bills, contracts, medical reports).

Rules for Adaptive NER:
- First, infer the document type (e.g., Invoice, Receipt, Legal Contract, Bill of Lading, etc.).
- Dynamically adapt your entity categories to the document type. Do NOT restrict yourself to standard NER types.
  - E.g., for Invoices: extract VENDOR, BUYER, INVOICE_NUMBER, TOTAL_AMOUNT, TAX_AMOUNT, DUE_DATE, LINE_ITEM.
  - E.g., for Contracts: extract PARTY_1, PARTY_2, EFFECTIVE_DATE, CLAUSE, GOVERNING_LAW, JURISDICTION.
- Extract every relevant entity. If an entity is missing from the document, simply omit it; do not invent values.
- For each entity, include the exact source text snippet where you found it.
- If a value has a unit (e.g. USD, EUR, kg), include it in the unit field.
- If you are uncertain about a value, still extract it but note lower confidence.
- Extract the document title, primary party (e.g. vendor/company name), and document date.
- Write a brief description summarizing what the document is.

IMPORTANT: You must follow the requested JSON schema EXACTLY. Ensure you include ALL required fields, including any `confidence`, `source_text`, and nested fields. Do not skip top-level fields."""


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
    doc_text = evidence.get("full_markdown", evidence.get("full_text", ""))

    max_chars = 4000
    if len(doc_text) > max_chars:
        doc_text = doc_text[:max_chars] + "\n\n[Document truncated for extraction]"

    source_info = wrap_for_prompt(
        {"file": evidence.get("source_file", "unknown"), "pages": evidence.get("page_count", 0)},
        "source_metadata",
    )

    prompt = f"""Extract all critical entities and information from the following document.

{source_info}

[document_text]
{doc_text}

{extra_instructions}

Extract the document title, primary party, document date, a brief summary, and every
relevant entity (PERSON, ORG, DATE, MONEY, etc.). For each entity, include the source text
snippet where you found it."""

    try:
        result = get_structured_output(
            prompt=prompt,
            response_model=ExtractionResult,
            system_prompt=SYSTEM_PROMPT,
            provider=provider,
        )
    except Exception as e:
        print(f"Extraction failed or hit token limit: {e}")
        error_msg = str(e)
        if "api_key" in error_msg.lower() or "authentication" in error_msg.lower() or "401" in error_msg:
            summary_msg = "API KEY ERROR: Your Gemini or Groq API Key is missing or invalid in the Railway Variables. Please set a valid API key."
        else:
            summary_msg = "The AI model failed to extract structured data from this document due to length limits or formatting errors."
            
        # Return a fallback empty result so the pipeline doesn't crash
        result = ExtractionResult(
            document_title="Unknown Document (Extraction Failed)",
            document_type="Unknown",
            primary_party="Unknown",
            document_date="Unknown",
            summary=summary_msg,
            entities=[],
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
        document_type=extraction.document_type,
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
        print("Usage: python -m extraction.extract_attributes <evidence_json>")
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

    print(f"Document: {record.document_title}")
    print(f"Primary Party: {record.primary_party}")
    print(f"Date: {record.document_date}")
    print(f"Summary: {record.summary}")
    print(f"Entities extracted: {len(record.entities)}")
    print()

    for ent in record.entities:
        unit_str = f" ({ent.unit})" if getattr(ent, 'unit', None) else ""
        source_str = f' [from: "{ent.source_text[:60]}..."]' if getattr(ent, 'source_text', None) else ""
        print(f"  [{ent.entity_type}] {ent.value}{unit_str}{source_str}")
