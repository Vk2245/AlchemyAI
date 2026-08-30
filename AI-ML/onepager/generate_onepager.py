"""
Auto-generate a product one-pager from a trusted record.

Prompts the LLM to turn the structured JSON record into a readable,
human-friendly spec sheet in Markdown format. Works unchanged across
any industry vertical.
"""

import sys
import json
from typing import Any

from config.llm_client import get_completion
from config.toon_utils import wrap_for_prompt


SYSTEM_PROMPT = """You are a technical writer creating a clean, professional product
spec sheet narrative from structured data. Write in clear, direct language. No marketing fluff.

Format as a human-readable narrative with these sections (use bold headings, but DO NOT use Markdown tables):
- Product Overview
- Key Specifications (list them as bullet points)
- Classification
- Quality Notes (confidence score, any fields flagged for review)
- Certifications and Compliance (if available)

Keep it to one page of content. Do NOT use markdown tables."""


def generate_onepager(
    record: dict[str, Any],
    provider: str = "local",
) -> str:
    """
    Generate a one-page product spec sheet from a trusted record.

    Returns the spec sheet as a Markdown string.
    """
    # Build a compact version of the record for the prompt
    compact = {
        "product_name": record.get("product_name", ""),
        "manufacturer": record.get("manufacturer", ""),
        "part_number": record.get("part_number", ""),
        "description": record.get("description", ""),
        "industry": record.get("industry", ""),
        "category": record.get("category", ""),
        "record_confidence": record.get("record_confidence", 0.0),
        "validation_passed": record.get("validation_passed", False),
        "fields_for_review": record.get("fields_for_review", []),
    }

    # Include attributes
    attrs = []
    for attr in record.get("attributes", []):
        attrs.append({
            "name": attr.get("name", ""),
            "value": attr.get("value", ""),
            "unit": attr.get("unit", ""),
            "confidence": attr.get("confidence", 0.0),
        })
    compact["attributes"] = attrs

    record_prompt = wrap_for_prompt(compact, "product_record")

    prompt = f"""Generate a clean, professional one-page product spec sheet from this data.

{record_prompt}

Format as Markdown. Include a specifications table with all attributes.
Add a confidence badge (High/Medium/Low) based on the record confidence score.
Note any fields flagged for review."""

    return get_completion(
        prompt,
        system_prompt=SYSTEM_PROMPT,
        provider=provider,
        max_tokens=2000,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m onepager.generate_onepager <record_json> [output.md]")
        sys.exit(1)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        record = json.load(f)

    print(f"Generating one-pager for: {record.get('product_name', '?')}")
    markdown = generate_onepager(record)

    if len(sys.argv) > 2:
        with open(sys.argv[2], "w", encoding="utf-8") as f:
            f.write(markdown)
        print(f"Saved to: {sys.argv[2]}")
    else:
        print()
        print(markdown)
