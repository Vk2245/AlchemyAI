"""
Intent-based product search.

Converts a natural-language engineering query into structured filters,
retrieves matching records from the embedding index, and ranks them
with a short explanation for each result.
"""

import sys
import json
from typing import Any, Optional

from pydantic import BaseModel, Field

from config.llm_client import get_structured_output, get_completion
from config.toon_utils import wrap_for_prompt
from knowledge.embed_products import query_similar


class SearchFilters(BaseModel):
    """Structured filters parsed from a natural-language query."""

    keywords: list[str] = Field(
        description="Key terms extracted from the query for embedding search"
    )
    required_attributes: list[dict[str, str]] = Field(
        default_factory=list,
        description="Attributes the product must have, e.g. [{'name': 'IP Rating', 'value': 'IP67'}]",
    )
    industry_hint: Optional[str] = Field(
        default=None,
        description="Industry if detectable from the query",
    )
    intent_summary: str = Field(
        description="One-sentence summary of what the user is looking for",
    )


PARSE_SYSTEM_PROMPT = """You are a product search assistant for industrial commerce.
Given a natural-language query, extract structured search filters.

Extract:
- Key search terms for semantic matching
- Any specific attribute requirements mentioned
- Industry context if apparent
- A clear summary of the user's intent"""


RANK_SYSTEM_PROMPT = """You are a product recommendation expert. Given a user's search
intent and a list of candidate products, rank them by relevance and explain why each
product does or does not match the intent. Be concise."""


def parse_intent(
    query: str,
    provider: str = "local",
) -> SearchFilters:
    """
    Parse a natural-language query into structured search filters.
    """
    prompt = f"""Parse this product search query into structured filters:

Query: "{query}"

Extract keywords, attribute requirements, industry hint, and intent summary."""

    return get_structured_output(
        prompt=prompt,
        response_model=SearchFilters,
        system_prompt=PARSE_SYSTEM_PROMPT,
        provider=provider,
    )


def search_by_intent(
    query: str,
    n_results: int = 5,
    provider: str = "local",
) -> dict[str, Any]:
    """
    Full intent-based search: parse query, retrieve candidates, rank with explanations.

    Returns a dict with the parsed filters, ranked results, and explanations.
    """
    # Step 1: Parse the query into structured filters
    filters = parse_intent(query, provider=provider)

    # Step 2: Retrieve candidates using the keywords
    search_text = " ".join(filters.keywords)
    if filters.industry_hint:
        search_text += f" {filters.industry_hint}"

    candidates = query_similar(search_text, n_results=n_results * 2)

    if not candidates:
        return {
            "query": query,
            "filters": filters.model_dump(),
            "results": [],
            "explanation": "No products found matching the search criteria.",
        }

    # Step 3: Ask LLM to rank and explain
    candidate_summaries = []
    for c in candidates[:n_results]:
        meta = c.get("metadata", {})
        candidate_summaries.append({
            "id": c["id"],
            "name": meta.get("product_name", ""),
            "manufacturer": meta.get("manufacturer", ""),
            "industry": meta.get("industry", ""),
            "similarity": round(1 - (c.get("distance", 1.0)), 3),
        })

    candidates_prompt = wrap_for_prompt(candidate_summaries, "candidates")

    rank_prompt = f"""User is searching for: "{query}"
Intent: {filters.intent_summary}

{candidates_prompt}

For each candidate, briefly explain how well it matches the user's intent.
Rank them from best to worst match."""

    explanation = get_completion(
        rank_prompt,
        system_prompt=RANK_SYSTEM_PROMPT,
        provider=provider,
    )

    results = []
    for c in candidates[:n_results]:
        meta = c.get("metadata", {})
        results.append({
            "id": c["id"],
            "product_name": meta.get("product_name", ""),
            "manufacturer": meta.get("manufacturer", ""),
            "similarity": round(1 - (c.get("distance", 1.0)), 3),
            "industry": meta.get("industry", ""),
        })

    return {
        "query": query,
        "filters": filters.model_dump(),
        "results": results,
        "explanation": explanation,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m reasoning.intent_search 'corrosion resistant connector for outdoor use'")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    print(f"Search query: {query}")
    print()

    result = search_by_intent(query)

    print(f"Intent: {result['filters'].get('intent_summary', '')}")
    print(f"Keywords: {result['filters'].get('keywords', [])}")
    print(f"Results: {len(result['results'])}")
    print()

    for r in result["results"]:
        print(f"  {r['product_name']} ({r['manufacturer']}) sim={r['similarity']:.3f}")

    print()
    print("Explanation:")
    print(result["explanation"])
