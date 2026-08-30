"""
Zero-shot product taxonomy classification.

Given a product name and description, classifies it into the best-matching
category from the taxonomy using an LLM call. No training data needed.
"""

import sys
import json
from typing import Annotated, Optional, Union

from pydantic import BaseModel, Field

from config.llm_client import get_structured_output
from taxonomy.categories import get_taxonomy_summary, find_category_by_code



class TaxonomyClassification(BaseModel):
    """Structured output from the taxonomy classifier."""

    category_code: Union[str, int] = Field(
        description="The best-matching taxonomy code from the provided list"
    )
    segment: str = Field(description="The top-level segment name")
    family: str = Field(description="The family name within the segment")
    product_class: str = Field(description="The specific class name")
    confidence: float = Field(
        default=0.85,
        ge=0.0, le=1.0,
        description="How confident the classification is, 0.0 to 1.0",
    )
    reasoning: str = Field(
        default="Not provided by model",
        description="Brief explanation of why this category was chosen"
    )


SYSTEM_PROMPT = """You are a product taxonomy classifier. Given a product's name,
description, and any technical attributes, classify it into the most appropriate
category from the provided taxonomy list.

Rules:
- Pick the single best-matching category code from the list
- If multiple categories could fit, pick the most specific one
- Set confidence lower if the match is ambiguous
- Explain your reasoning briefly
- If nothing fits well, use code 99000000 (General/Other)

IMPORTANT: You must follow the requested JSON schema EXACTLY. Ensure you include ALL required fields, including any `confidence` and `reasoning` fields. Do not skip top-level fields."""


def classify_product(
    product_name: str,
    description: str = "",
    attributes_text: str = "",
    provider: str = "local",
) -> TaxonomyClassification:
    """
    Classify a product into the taxonomy using a zero-shot LLM call.

    Returns a TaxonomyClassification with the matched category and confidence.
    """
    taxonomy_text = get_taxonomy_summary()

    prompt = f"""Classify this product into the most appropriate category.

Product name: {product_name}
Description: {description}
Attributes: {attributes_text}

Available taxonomy categories:
{taxonomy_text}

Pick the best matching category code and explain your reasoning."""

    result = get_structured_output(
        prompt=prompt,
        response_model=TaxonomyClassification,
        system_prompt=SYSTEM_PROMPT,
        provider=provider,
    )

    return result


def classify_record(
    record_dict: dict,
    provider: str = "local",
) -> TaxonomyClassification:
    """
    Classify a TrustedProductRecord (as a dict) into the taxonomy.

    Convenience function that extracts the relevant fields from the record
    and passes them to classify_product.
    """
    if hasattr(record_dict, "model_dump"):
        record_dict = record_dict.model_dump()
    elif hasattr(record_dict, "dict"):
        record_dict = record_dict.dict()
        
    product_name = record_dict.get("product_name", "")
    description = record_dict.get("description", "")

    # Build a text summary of attributes for additional context
    attrs = record_dict.get("attributes", [])
    attr_lines = []
    for attr in attrs[:10]:  # Limit to avoid token bloat
        name = attr.get("name", "")
        value = attr.get("value", "")
        unit = attr.get("unit", "")
        attr_lines.append(f"{name}: {value} {unit}".strip())
    attributes_text = "; ".join(attr_lines)

    return classify_product(
        product_name=product_name,
        description=description,
        attributes_text=attributes_text,
        provider=provider,
    )


# ---------------------------------------------------------------------------
# CLI: classify a product from the command line
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m taxonomy.classify_taxonomy <product_name> [description]")
        print("   or: python -m taxonomy.classify_taxonomy --file <record_json>")
        print()
        print("Classifies a product into the taxonomy using a zero-shot LLM call.")
        sys.exit(1)

    if sys.argv[1] == "--file":
        record_path = sys.argv[2]
        with open(record_path, "r", encoding="utf-8") as f:
            record_dict = json.load(f)
        result = classify_record(record_dict)
    else:
        product_name = sys.argv[1]
        description = sys.argv[2] if len(sys.argv) > 2 else ""
        result = classify_product(product_name, description)

    print(f"Category: {result.segment} > {result.family} > {result.product_class}")
    print(f"Code: {result.category_code}")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Reasoning: {result.reasoning}")
