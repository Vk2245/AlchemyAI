"""
Auto-generate a document summary from extracted entities.

Prompts the LLM to turn the structured JSON record into a readable,
human-friendly executive summary. This uses the extracted JSON (Method A)
to save on token limits compared to summarizing the full raw document text.
"""

import sys
import json
from typing import Any

from config.llm_client import get_completion
from config.toon_utils import wrap_for_prompt


SYSTEM_PROMPT = """You are a professional business analyst. Your job is to write a concise, executive summary of a document based on its extracted structured data.

Rules:
- Write in clear, professional English.
- Use 3 to 4 bullet points.
- Explain who is doing what, by when, and for how much (if applicable).
- Do not hallucinate. Only use the provided structured data.
- Keep the summary under 150 words.
- Format as standard Markdown bullet points."""


def summarize_document(
    record: dict[str, Any],
    provider: str = "local",
) -> str:
    """
    Generate a concise bulleted summary from a document record.
    """
    # Build a compact version of the record for the prompt to save tokens
    compact = {
        "document_title": record.get("document_title", "Unknown"),
        "primary_party": record.get("primary_party", "Unknown"),
        "document_type": record.get("document_type", "Unknown"),
        "document_date": record.get("document_date", "Unknown"),
        "record_confidence": record.get("record_confidence", 0.0),
    }

    # Include entities
    entities = []
    for ent in record.get("entities", []):
        entities.append({
            "type": ent.get("entity_type", ""),
            "value": ent.get("value", ""),
            "unit": ent.get("unit", ""),
        })
    compact["entities"] = entities

    record_prompt = wrap_for_prompt(compact, "extracted_data")

    prompt = f"""Write a 3-bullet executive summary based on this document data.

{record_prompt}

Focus on the key parties, monetary amounts, and critical dates."""

    try:
        return get_completion(
            prompt,
            system_prompt=SYSTEM_PROMPT,
            provider=provider,
            max_tokens=300,
            temperature=0.3,
        )
    except Exception as e:
        print(f"Summarization failed: {e}")
        return "- Document summary could not be generated due to an AI processing error."


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m summarizer.summarize_document <record_json>")
        sys.exit(1)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        record = json.load(f)

    print(f"Generating summary for: {record.get('document_title', '?')}")
    markdown = summarize_document(record)

    print("\n--- EXECUTIVE SUMMARY ---\n")
    print(markdown)
