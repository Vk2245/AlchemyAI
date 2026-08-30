"""
Automatic industry detection from document evidence.

Classifies the document into an industry using an LLM call. The detected
industry key is used to load the corresponding profile from industry_profiles.
This is fully industry-agnostic -- it can detect any domain.
"""

import sys
import json
from typing import Any

from pydantic import BaseModel, Field

from config.llm_client import get_structured_output
from config.toon_utils import wrap_for_prompt


class IndustryDetection(BaseModel):
    """Structured output from the industry detector."""

    industry: str = Field(
        description=(
            "Detected industry key in lowercase, e.g. 'electrical', 'software', "
            "'food', 'agriculture', 'pharmaceutical', 'mechanical', 'chemical'"
        )
    )
    product_domain: str = Field(
        description="More specific product domain, e.g. 'power distribution', 'cloud services'"
    )
    product_family: str = Field(
        description="Product family if detectable, e.g. 'circuit breakers', 'CRM software'"
    )
    document_type: str = Field(
        description="Type of document: 'datasheet', 'spec_sheet', 'catalog', 'manual', 'other'"
    )
    confidence: float = Field(
        default=0.85,
        ge=0.0, le=1.0,
        description="Confidence in the industry detection",
    )
    reasoning: str = Field(
        default="Not provided by model",
        description="Brief explanation of how the industry was determined"
    )


SYSTEM_PROMPT = """You are an industry classification specialist. Given the text
content of a product document, determine which industry it belongs to.

You must detect the industry from the document content -- look for industry-specific
terminology, product types, technical specifications, compliance standards, and
other domain signals.

Common industries include but are not limited to:
- electrical (power equipment, wiring, lighting, electronics)
- software (applications, cloud services, IT infrastructure)
- mechanical (machinery, tools, bearings, HVAC)
- food (packaged food, beverages, ingredients)
- agriculture (farming equipment, seeds, fertilizers)
- pharmaceutical (drugs, medical devices, diagnostics)
- chemical (industrial chemicals, materials, coatings)
- automotive (vehicles, parts, accessories)
- aerospace (aircraft, spacecraft, defense)
- construction (building materials, structural components)
- textile (fabrics, apparel, manufacturing)
- energy (renewable, oil/gas, power generation)

If the document does not clearly belong to any industry, use 'general'.
The industry key must be a single lowercase word or short phrase.

IMPORTANT: You MUST include the fields `confidence` (a float between 0.0 and 1.0) and `reasoning` (a brief explanation of your choice)."""


def detect_industry(
    evidence: dict[str, Any],
    provider: str = "local",
) -> IndustryDetection:
    """
    Detect the industry from document evidence using an LLM call.

    Sends a sample of the document text to the LLM for classification.
    Returns an IndustryDetection with the industry key and metadata.
    """
    # Use a sample of the text to keep tokens manageable (Qwen 2B: 8192 token limit)
    full_text = evidence.get("full_text", "")
    sample_text = full_text[:3000]

    source_meta = wrap_for_prompt(
        {"file": evidence.get("source_file", "unknown"), "pages": evidence.get("page_count", 0)},
        "source",
    )

    prompt = f"""Analyze this product document and determine which industry it belongs to.

{source_meta}

[document_sample]
{sample_text}

Identify the industry, product domain, product family, and document type."""

    result = get_structured_output(
        prompt=prompt,
        response_model=IndustryDetection,
        system_prompt=SYSTEM_PROMPT,
        provider=provider,
    )

    return result


def detect_industry_from_text(
    text: str,
    provider: str = "local",
) -> IndustryDetection:
    """
    Convenience function: detect industry from plain text instead of a
    full evidence dict.
    """
    evidence = {"full_text": text, "source_file": "text_input", "page_count": 1}
    return detect_industry(evidence, provider=provider)


# ---------------------------------------------------------------------------
# CLI: detect industry from a document
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m company_discovery.detect_industry <evidence_json>")
        print("   or: python -m company_discovery.detect_industry --text 'product description'")
        sys.exit(1)

    if sys.argv[1] == "--text":
        text = " ".join(sys.argv[2:])
        result = detect_industry_from_text(text)
    else:
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            evidence = json.load(f)
        result = detect_industry(evidence)

    print(f"Industry: {result.industry}")
    print(f"Product domain: {result.product_domain}")
    print(f"Product family: {result.product_family}")
    print(f"Document type: {result.document_type}")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Reasoning: {result.reasoning}")
