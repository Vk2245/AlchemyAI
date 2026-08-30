"""
LangGraph research state machine.

Implements the 3-tier agentic research pipeline:
  Tier 1: DDG search + Playwright/Jina scrape → LLM Judge
  Tier 2: Firecrawl OSS scrape → LLM Judge
  Tier 3: Gemini API fallback (knowledge-based)

The graph takes a product record with missing attributes and autonomously
researches the web to fill them in. Each tier has an LLM-as-Judge gate
that decides whether to proceed or escalate.

Can run standalone: python -m agent.research_graph <record.json>
"""

import sys
import json
import operator
from typing import Any, Annotated, TypedDict

from langgraph.graph import StateGraph, END

from agent.tools import (
    search_duckduckgo,
    scrape_with_playwright,
    scrape_with_jina,
    scrape_with_firecrawl,
    query_gemini_for_specs,
)
from agent.judge import judge_content, quick_relevance_check, QUALITY_THRESHOLD
from config.llm_client import get_structured_output
from config.toon_utils import wrap_for_prompt
from extraction.schema_models import ProductAttribute

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# State definition
# ---------------------------------------------------------------------------

class ResearchState(TypedDict):
    """State that flows through the research graph."""

    # Input
    product_name: str
    manufacturer: str
    part_number: str
    industry: str
    missing_attributes: list[str]

    # Accumulated results
    search_results: list[dict[str, Any]]
    scraped_content: str
    scrape_source: str

    # Judge results
    judge_score: float
    judge_passed: bool
    found_attributes: list[str]
    still_missing: list[str]

    # Extracted attributes (final output)
    extracted_attributes: list[dict[str, Any]]

    # Control
    current_tier: int
    tier_log: list[str]
    final_status: str


# ---------------------------------------------------------------------------
# Extraction helper
# ---------------------------------------------------------------------------

class ExtractedSpecs(BaseModel):
    """Specs extracted from scraped content."""

    attributes: list[ProductAttribute] = Field(
        default_factory=list,
        description="Product attributes found in the scraped content"
    )

    @field_validator("attributes", mode="before")
    @classmethod
    def ensure_list(cls, v):
        if isinstance(v, dict):
            return [v]
        return v


def extract_from_content(
    content: str,
    product_name: str,
    target_attributes: list[str],
    provider: str = "local",
) -> list[dict[str, Any]]:
    """Extract specific attributes from scraped content using the LLM."""
    attrs_str = ", ".join(target_attributes)

    prompt = f"""Extract the following product specifications from this web content.

Product: {product_name}
Target attributes: {attrs_str}

Content:
---
{content[:2000]}
---

Extract ONLY the attributes listed above. For each, provide:
- name: the attribute name
- value: the extracted value
- unit: the unit if applicable
- source_text: the exact text snippet where you found it"""

    try:
        result = get_structured_output(
            prompt=prompt,
            response_model=ExtractedSpecs,
            provider=provider,
        )
        if result and hasattr(result, "attributes"):
            return [a.model_dump() for a in result.attributes]
        return []
    except Exception as e:
        print(f"[Extract] Failed: {e}")
        return []


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------

def tier1_search(state: ResearchState) -> dict:
    """Tier 1a: Search DuckDuckGo for product specs."""
    product = state["product_name"]
    manufacturer = state["manufacturer"]
    part_number = state["part_number"]

    # Build a targeted search query
    query_parts = [manufacturer, product]
    if part_number:
        query_parts.append(part_number)
    query_parts.append("specifications datasheet")
    query = " ".join(filter(None, query_parts))

    print(f"  [Tier 1] Searching DDG: {query}")
    results = search_duckduckgo(query, max_results=5)

    return {
        "search_results": results,
        "current_tier": 1,
        "tier_log": state.get("tier_log", []) + [f"Tier 1: DDG search for '{query}', got {len(results)} results"],
    }


def tier1_scrape(state: ResearchState) -> dict:
    """Tier 1b: Scrape the top search result with Playwright or Jina."""
    results = state.get("search_results", [])

    if not results:
        return {
            "scraped_content": "",
            "scrape_source": "none",
            "tier_log": state.get("tier_log", []) + ["Tier 1: No search results to scrape"],
        }

    # Try top 2 results
    for result in results[:2]:
        url = result.get("url", "")
        if not url:
            continue

        print(f"  [Tier 1] Scraping: {url}")

        # Try Playwright first, fall back to Jina
        scraped = scrape_with_playwright(url)
        if not scraped["success"]:
            print(f"  [Tier 1] Playwright failed, trying Jina...")
            scraped = scrape_with_jina(url)

        if scraped["success"] and quick_relevance_check(scraped["content"], state["product_name"]):
            # Fill missing
            print(f"Agent found {len(result['extracted_attributes'])} missing attributes.")
            
            # Mark source
            for attr in result["extracted_attributes"]:
                if "source" not in attr or not attr["source"]:
                    attr["source"] = "(web search agent)"
                    
            return {
                "scrape_source": "(web search agent)",
                "scraped_content": scraped["content"],
                "tier_log": state.get("tier_log", []) + [
                    f"Tier 1: Scraped {url} via {scraped['source']} ({scraped.get('char_count', 0)} chars)"
                ],
            }

    return {
        "scraped_content": "",
        "scrape_source": "none",
        "tier_log": state.get("tier_log", []) + ["Tier 1: All scrape attempts failed or irrelevant"],
    }


def tier1_judge(state: ResearchState) -> dict:
    """Tier 1 Judge: Evaluate scraped content quality."""
    content = state.get("scraped_content", "")
    product = state["product_name"]
    missing = state["missing_attributes"]

    if not content:
        return {
            "judge_score": 0.0,
            "judge_passed": False,
            "found_attributes": [],
            "still_missing": missing,
            "tier_log": state.get("tier_log", []) + ["Tier 1 Judge: No content to judge"],
        }

    print(f"  [Tier 1 Judge] Evaluating {len(content)} chars...")
    verdict = judge_content(content, product, missing)

    return {
        "judge_score": verdict.score,
        "judge_passed": verdict.passed,
        "found_attributes": verdict.found_attributes,
        "still_missing": verdict.missing_still,
        "tier_log": state.get("tier_log", []) + [
            f"Tier 1 Judge: score={verdict.score:.2f}, passed={verdict.passed}, found={verdict.found_attributes}"
        ],
    }


def tier2_firecrawl(state: ResearchState) -> dict:
    """Tier 2: Scrape with self-hosted Firecrawl."""
    results = state.get("search_results", [])

    if not results:
        return {
            "scraped_content": "",
            "scrape_source": "none",
            "current_tier": 2,
            "tier_log": state.get("tier_log", []) + ["Tier 2: No URLs to scrape with Firecrawl"],
        }

    # Try top 3 results with Firecrawl
    for result in results[:3]:
        url = result.get("url", "")
        if not url:
            continue

        print(f"  [Tier 2] Firecrawl scraping: {url}")
        scraped = scrape_with_firecrawl(url)

        if scraped["success"] and quick_relevance_check(scraped["content"], state["product_name"]):
            return {
                "scraped_content": scraped["content"],
                "scrape_source": "firecrawl_oss",
                "current_tier": 2,
                "tier_log": state.get("tier_log", []) + [
                    f"Tier 2: Firecrawl scraped {url} ({scraped.get('char_count', 0)} chars)"
                ],
            }

    return {
        "scraped_content": "",
        "scrape_source": "none",
        "current_tier": 2,
        "tier_log": state.get("tier_log", []) + ["Tier 2: Firecrawl scrape failed for all URLs"],
    }


def tier2_judge(state: ResearchState) -> dict:
    """Tier 2 Judge: Evaluate Firecrawl content quality."""
    content = state.get("scraped_content", "")
    product = state["product_name"]
    missing = state.get("still_missing", state["missing_attributes"])

    if not content:
        return {
            "judge_score": 0.0,
            "judge_passed": False,
            "still_missing": missing,
            "tier_log": state.get("tier_log", []) + ["Tier 2 Judge: No content to judge"],
        }

    print(f"  [Tier 2 Judge] Evaluating {len(content)} chars...")
    verdict = judge_content(content, product, missing)

    return {
        "judge_score": verdict.score,
        "judge_passed": verdict.passed,
        "found_attributes": verdict.found_attributes,
        "still_missing": verdict.missing_still,
        "tier_log": state.get("tier_log", []) + [
            f"Tier 2 Judge: score={verdict.score:.2f}, passed={verdict.passed}"
        ],
    }


def tier3_gemini(state: ResearchState) -> dict:
    """Tier 3: Gemini API fallback (knowledge-based)."""
    product = state["product_name"]
    manufacturer = state["manufacturer"]
    part_number = state.get("part_number", "")
    missing = state.get("still_missing", state["missing_attributes"])

    print(f"  [Tier 3] Querying Gemini for: {missing}")

    result = query_gemini_for_specs(
        product_name=product,
        manufacturer=manufacturer,
        missing_attributes=missing,
        part_number=part_number,
    )

    return {
        "scraped_content": result.get("content", ""),
        "scrape_source": "(web search agent)",
        "current_tier": 3,
        "tier_log": state.get("tier_log", []) + [
            f"Tier 3: Gemini fallback, success={result['success']}"
        ],
    }


def extract_attributes_node(state: ResearchState) -> dict:
    """Extract attributes from the best available content."""
    content = state.get("scraped_content", "")
    product = state["product_name"]
    missing = state.get("still_missing", state["missing_attributes"])

    if not content:
        return {
            "extracted_attributes": [],
            "final_status": "no_content",
            "tier_log": state.get("tier_log", []) + ["Extract: No content available"],
        }

    print(f"  [Extract] Extracting {len(missing)} attributes from {len(content)} chars...")

    # Determine provider based on source
    source = state.get("scrape_source", "")
    from config.settings import DEFAULT_PROVIDER
    provider = DEFAULT_PROVIDER

    extracted = extract_from_content(content, product, missing, provider=provider)

    # Mark source for each attribute
    for attr in extracted:
        attr["source_text"] = f"[web:{source}] {attr.get('source_text', '')}"

    return {
        "extracted_attributes": extracted,
        "final_status": "success" if extracted else "extraction_failed",
        "tier_log": state.get("tier_log", []) + [
            f"Extract: Got {len(extracted)} attributes from {source}"
        ],
    }


# ---------------------------------------------------------------------------
# Routing functions
# ---------------------------------------------------------------------------

def route_after_tier1_judge(state: ResearchState) -> str:
    """Route after Tier 1 judge: pass → extract, fail → Tier 2."""
    if state.get("judge_passed", False):
        return "extract"
    return "tier2_firecrawl"


def route_after_tier2_judge(state: ResearchState) -> str:
    """Route after Tier 2 judge: pass → extract, fail → Tier 3."""
    if state.get("judge_passed", False):
        return "extract"
    return "tier3_gemini"


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------

def build_research_graph() -> StateGraph:
    """
    Build and compile the LangGraph research state machine.

    Flow:
      tier1_search → tier1_scrape → tier1_judge
        → PASS → extract → END
        → FAIL → tier2_firecrawl → tier2_judge
          → PASS → extract → END
          → FAIL → tier3_gemini → extract → END
    """
    graph = StateGraph(ResearchState)

    # Add nodes
    graph.add_node("tier1_search", tier1_search)
    graph.add_node("tier1_scrape", tier1_scrape)
    graph.add_node("tier1_judge", tier1_judge)
    graph.add_node("tier2_firecrawl", tier2_firecrawl)
    graph.add_node("tier2_judge", tier2_judge)
    graph.add_node("tier3_gemini", tier3_gemini)
    graph.add_node("extract", extract_attributes_node)

    # Add edges
    graph.set_entry_point("tier1_search")
    graph.add_edge("tier1_search", "tier1_scrape")
    graph.add_edge("tier1_scrape", "tier1_judge")

    graph.add_conditional_edges(
        "tier1_judge",
        route_after_tier1_judge,
        {"extract": "extract", "tier2_firecrawl": "tier2_firecrawl"},
    )

    graph.add_edge("tier2_firecrawl", "tier2_judge")

    graph.add_conditional_edges(
        "tier2_judge",
        route_after_tier2_judge,
        {"extract": "extract", "tier3_gemini": "tier3_gemini"},
    )

    graph.add_edge("tier3_gemini", "extract")
    graph.add_edge("extract", END)

    return graph.compile()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def research_missing_attributes(
    record: dict[str, Any],
    missing_attributes: list[str] | None = None,
) -> dict[str, Any]:
    """
    Research missing attributes for a product record.

    If missing_attributes is not specified, uses the record's
    fields_for_review list.

    Returns a dict with:
      - extracted_attributes: list of attribute dicts found
      - tier_log: list of log messages showing the research process
      - final_status: 'success', 'no_content', or 'extraction_failed'
    """
    if missing_attributes is None:
        missing_attributes = record.get("fields_for_review", [])

    if not missing_attributes:
        return {
            "extracted_attributes": [],
            "tier_log": ["No missing attributes to research"],
            "final_status": "nothing_to_do",
        }

    # Build initial state
    initial_state: ResearchState = {
        "product_name": record.get("product_name", ""),
        "manufacturer": record.get("manufacturer", ""),
        "part_number": record.get("part_number", ""),
        "industry": record.get("industry", ""),
        "missing_attributes": missing_attributes,
        "search_results": [],
        "scraped_content": "",
        "scrape_source": "",
        "judge_score": 0.0,
        "judge_passed": False,
        "found_attributes": [],
        "still_missing": missing_attributes,
        "extracted_attributes": [],
        "current_tier": 0,
        "tier_log": [],
        "final_status": "",
    }

    print(f"\n{'='*60}")
    print(f"Research Agent: {record.get('product_name', '?')}")
    print(f"Missing: {missing_attributes}")
    print(f"{'='*60}")

    # Run the graph
    app = build_research_graph()
    final_state = app.invoke(initial_state)

    print(f"\n{'='*60}")
    print(f"Result: {final_state.get('final_status', '?')}")
    print(f"Extracted: {len(final_state.get('extracted_attributes', []))} attributes")
    print(f"{'='*60}\n")

    return {
        "extracted_attributes": final_state.get("extracted_attributes", []),
        "tier_log": final_state.get("tier_log", []),
        "final_status": final_state.get("final_status", ""),
    }


# ---------------------------------------------------------------------------
# CLI: run the research agent
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m agent.research_graph <record.json> [attr1,attr2,...]")
        print()
        print("Examples:")
        print("  python -m agent.research_graph record.json 'IP Rating,Voltage Rating'")
        print("  python -m agent.research_graph record.json  # uses fields_for_review")
        sys.exit(1)

    record_path = sys.argv[1]
    with open(record_path, "r", encoding="utf-8") as f:
        record = json.load(f)

    missing = None
    if len(sys.argv) > 2:
        missing = sys.argv[2].split(",")

    result = research_missing_attributes(record, missing_attributes=missing)

    print("\n--- Research Log ---")
    for log in result["tier_log"]:
        print(f"  {log}")

    print(f"\n--- Extracted Attributes ({len(result['extracted_attributes'])}) ---")
    for attr in result["extracted_attributes"]:
        print(f"  {attr.get('name', '?')}: {attr.get('value', '?')} {attr.get('unit', '')}")

    print(f"\nFinal status: {result['final_status']}")
