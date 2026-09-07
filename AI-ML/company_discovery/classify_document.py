"""
Automatic Document Type Classification.

Classifies the document into a specific business type using an LLM call.
This helps downstream processing (e.g., knowing we need to extract an Invoice Number vs a Contract Clause).
"""

import sys
import json
from typing import Any

from pydantic import BaseModel, Field

from config.llm_client import get_structured_output
from config.toon_utils import wrap_for_prompt


class DocumentClassification(BaseModel):
    """Structured output from the document classifier."""

    document_type: str = Field(
        description=(
            "Detected document type in lowercase, e.g. 'invoice', 'contract', "
            "'receipt', 'purchase_order', 'bank_statement', 'letter', 'report', 'other'"
        )
    )
    confidence: float = Field(
        default=0.85,
        ge=0.0, le=1.0,
        description="Confidence in the document type classification",
    )
    language: str = Field(
        default="english",
        description="Primary language of the document (e.g. 'english', 'hindi', 'spanish')"
    )
    reasoning: str = Field(
        default="Not provided by model",
        description="Brief explanation of how the document type was determined"
    )


SYSTEM_PROMPT = """You are a highly skilled document classification specialist. 
Given the text content of a document, determine its specific document type.

Common document types include but are not limited to:
- invoice (requests for payment, usually contains totals and line items)
- receipt (proof of payment)
- purchase_order (PO, request to buy goods/services)
- contract (agreements, NDAs, MSA, terms and conditions)
- bank_statement (financial ledger)
- letter (formal correspondence)
- report (technical, financial, or business report)
- other (if none of the above fit perfectly)

Look for structural clues like "Total Due", "Terms and Conditions", "INVOICE #", signatures, or formatting to make your decision. Be precise."""


def classify_document(
    evidence: dict[str, Any], provider: str = "local"
) -> DocumentClassification | None:
    """
    Classify the document type from the first few pages of evidence text.
    """
    # Use just the first ~3000 chars to save tokens -- doc type is usually obvious early on
    doc_text = evidence.get("full_text", "")
    if not doc_text:
        return None
        
    doc_text = doc_text[:3000]

    source_info = wrap_for_prompt(
        {"file": evidence.get("source_file", "unknown"), "pages": evidence.get("page_count", 0)},
        "source_metadata",
    )

    prompt = f"""Classify the following document based on its starting text.

{source_info}

[document_text_start]
{doc_text}

Determine the document type, language, and your confidence score."""

    try:
        result = get_structured_output(
            prompt=prompt,
            response_model=DocumentClassification,
            system_prompt=SYSTEM_PROMPT,
            provider=provider,
            temperature=0.1, # Low temp for classification
        )
        return result
    except Exception as e:
        print(f"Document classification failed: {e}")
        return None


# ---------------------------------------------------------------------------
# CLI: classify from a saved evidence JSON file
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m company_discovery.classify_document <evidence_json>")
        sys.exit(1)

    evidence_path = sys.argv[1]
    provider = sys.argv[2] if len(sys.argv) > 2 else "local"

    print(f"Loading evidence: {evidence_path}")
    with open(evidence_path, "r", encoding="utf-8") as f:
        evidence = json.load(f)

    print(f"Provider: {provider}")
    print("Classifying...")
    
    result = classify_document(evidence, provider=provider)
    if result:
        print("\n--- CLASSIFICATION RESULT ---")
        print(f"Type:       {result.document_type}")
        print(f"Language:   {result.language}")
        print(f"Confidence: {result.confidence:.0%}")
        print(f"Reasoning:  {result.reasoning}")
    else:
        print("\nClassification failed.")
