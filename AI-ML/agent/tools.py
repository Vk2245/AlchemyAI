"""
Agent tools for the tiered research pipeline.

Tier 1: DuckDuckGo search + Playwright scrape
Tier 2: Firecrawl (open-source, self-hosted) scrape
Tier 3: Gemini API fallback (knowledge-based)

Each tool returns a dict with the scraped content and metadata.
All tools are standalone-runnable for testing.
"""

import sys
import json
import time
import asyncio
from typing import Any, Optional
from urllib.parse import quote_plus

import requests

from config.settings import GEMINI_API_KEY


# ---------------------------------------------------------------------------
# TIER 1a: DuckDuckGo Search
# ---------------------------------------------------------------------------

def search_duckduckgo(
    query: str,
    max_results: int = 5,
) -> list[dict[str, str]]:
    """
    Search DuckDuckGo for product information.

    Returns a list of result dicts with 'title', 'url', and 'snippet'.
    Uses the duckduckgo-search library (no API key needed).
    """
    try:
        from duckduckgo_search import DDGS

        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                    "source": "duckduckgo",
                })
        return results

    except Exception as e:
        print(f"[DDG] Search failed: {e}")
        return []


# ---------------------------------------------------------------------------
# TIER 1b: Playwright Scrape (headless browser)
# ---------------------------------------------------------------------------

def scrape_with_playwright(
    url: str,
    timeout_ms: int = 15000,
) -> dict[str, Any]:
    """
    Scrape a URL using Playwright (headless Chromium).

    Returns a dict with 'content' (extracted text), 'url', and 'success'.
    Handles JavaScript-heavy pages that simple HTTP requests can't.
    """
    try:
        import concurrent.futures

        def _do_scrape():
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")

                # Wait a bit for dynamic content
                page.wait_for_timeout(2000)

                # Extract main content text
                content = page.inner_text("body")

                # Trim to reasonable size (avoid token bloat)
                content = content[:10000]

                browser.close()

                return {
                    "content": content,
                    "url": url,
                    "success": True,
                    "source": "playwright",
                    "char_count": len(content),
                }

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(_do_scrape).result()

    except Exception as e:
        print(f"[Playwright] Scrape failed for {url}: {e}")
        return {
            "content": "",
            "url": url,
            "success": False,
            "source": "playwright",
            "error": str(e),
        }


# ---------------------------------------------------------------------------
# TIER 1c: Simple HTTP scrape (lightweight fallback if Playwright unavailable)
# ---------------------------------------------------------------------------

def scrape_with_jina(
    url: str,
    timeout: int = 15,
) -> dict[str, Any]:
    """
    Scrape a URL using Jina Reader API (free, no auth).

    Converts any URL into clean Markdown. Rate limited but
    excellent for Project use.
    """
    try:
        jina_url = f"https://r.jina.ai/{url}"
        headers = {"Accept": "text/markdown"}

        response = requests.get(jina_url, headers=headers, timeout=timeout)
        response.raise_for_status()

        content = response.text[:10000]

        return {
            "content": content,
            "url": url,
            "success": True,
            "source": "jina_reader",
            "char_count": len(content),
        }

    except Exception as e:
        print(f"[Jina] Scrape failed for {url}: {e}")
        return {
            "content": "",
            "url": url,
            "success": False,
            "source": "jina_reader",
            "error": str(e),
        }


# ---------------------------------------------------------------------------
# TIER 2: Firecrawl (open-source, self-hosted)
# ---------------------------------------------------------------------------

def scrape_with_firecrawl(
    url: str,
    firecrawl_url: str = "http://localhost:3002",
    timeout: int = 30,
) -> dict[str, Any]:
    """
    Scrape a URL using the self-hosted Firecrawl open-source instance.

    Firecrawl runs locally via Docker:
        docker run -p 3002:3002 mendableai/firecrawl

    Returns clean markdown content from the URL.
    """
    try:
        endpoint = f"{firecrawl_url}/v0/scrape"
        payload = {
            "url": url,
            "pageOptions": {
                "onlyMainContent": True,
            },
        }

        response = requests.post(
            endpoint,
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()

        content = data.get("data", {}).get("markdown", "") or data.get("data", {}).get("content", "")
        content = content[:10000]

        return {
            "content": content,
            "url": url,
            "success": bool(content),
            "source": "firecrawl_oss",
            "char_count": len(content),
        }

    except requests.exceptions.ConnectionError:
        print(f"[Firecrawl] Not running at {firecrawl_url}. Start with: docker run -p 3002:3002 mendableai/firecrawl")
        return {
            "content": "",
            "url": url,
            "success": False,
            "source": "firecrawl_oss",
            "error": f"Firecrawl not running at {firecrawl_url}",
        }
    except Exception as e:
        print(f"[Firecrawl] Scrape failed for {url}: {e}")
        return {
            "content": "",
            "url": url,
            "success": False,
            "source": "firecrawl_oss",
            "error": str(e),
        }


# ---------------------------------------------------------------------------
# TIER 3: Gemini API fallback (knowledge-based)
# ---------------------------------------------------------------------------

def query_gemini_for_specs(
    product_name: str,
    manufacturer: str,
    missing_attributes: list[str],
    part_number: str = "",
) -> dict[str, Any]:
    """
    Use Gemini API as a final fallback to fill missing product specs.

    Asks Gemini to use its internal knowledge to provide the missing
    attribute values. Results are flagged as 'LLM-inferred' since they
    come from the model's training data, not a live source.
    """
    try:
        from config.llm_client import get_completion

        missing_str = ", ".join(missing_attributes)
        part_info = f" (part number: {part_number})" if part_number else ""

        prompt = f"""I need the following technical specifications for the product:
Product: {product_name}{part_info}
Manufacturer: {manufacturer}

Missing specifications needed: {missing_str}

For each missing specification, provide:
- The attribute name
- The most likely value based on your knowledge
- The unit (if applicable)
- Your confidence level (high/medium/low)

If you don't know a value, say "unknown" rather than guessing.
Format as a structured list."""

        from config.settings import DEFAULT_PROVIDER
        response = get_completion(prompt, provider=DEFAULT_PROVIDER)

        return {
            "content": response,
            "success": True,
            "source": "(web search agent)",
            "is_inferred": True,
            "product": product_name,
            "manufacturer": manufacturer,
        }

    except Exception as e:
        print(f"[Gemini] Fallback failed: {e}")
        return {
            "content": "",
            "success": False,
            "source": "(web search agent)",
            "error": str(e),
        }


# ---------------------------------------------------------------------------
# CLI: test individual tools
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python -m agent.tools search 'ABB circuit breaker specs'")
        print("  python -m agent.tools scrape 'https://example.com/product'")
        print("  python -m agent.tools firecrawl 'https://example.com/product'")
        print("  python -m agent.tools jina 'https://example.com/product'")
        print("  python -m agent.tools gemini 'ABB SACE Tmax' 'ABB' 'IP Rating,Voltage Rating'")
        sys.exit(1)

    command = sys.argv[1]

    if command == "search":
        query = " ".join(sys.argv[2:])
        print(f"Searching DDG: {query}")
        results = search_duckduckgo(query)
        for r in results:
            print(f"  [{r['title']}] {r['url']}")
            print(f"    {r['snippet'][:100]}")

    elif command == "scrape":
        url = sys.argv[2]
        print(f"Scraping with Playwright: {url}")
        result = scrape_with_playwright(url)
        print(f"  Success: {result['success']}")
        print(f"  Chars: {result.get('char_count', 0)}")
        if result["content"]:
            print(f"  Preview: {result['content'][:200]}")

    elif command == "firecrawl":
        url = sys.argv[2]
        print(f"Scraping with Firecrawl: {url}")
        result = scrape_with_firecrawl(url)
        print(f"  Success: {result['success']}")
        if result["content"]:
            print(f"  Preview: {result['content'][:200]}")

    elif command == "jina":
        url = sys.argv[2]
        print(f"Scraping with Jina Reader: {url}")
        result = scrape_with_jina(url)
        print(f"  Success: {result['success']}")
        if result["content"]:
            print(f"  Preview: {result['content'][:200]}")

    elif command == "gemini":
        product = sys.argv[2]
        manufacturer = sys.argv[3] if len(sys.argv) > 3 else ""
        missing = sys.argv[4].split(",") if len(sys.argv) > 4 else ["specifications"]
        print(f"Querying Gemini for: {product}")
        result = query_gemini_for_specs(product, manufacturer, missing)
        print(f"  Success: {result['success']}")
        if result["content"]:
            print(result["content"])
