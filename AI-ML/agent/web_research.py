"""
Agentic Web Research Module.

Autonomously researches a vendor or company using a fallback chain:
1. Tavily (AI-optimized search)
2. Serper (Standard Google Search)
3. Gemini Search (Grounding) if available.
"""

import os
from typing import Any

from tavily import TavilyClient
import requests

def research_category(category_name: str) -> dict[str, Any]:
    """
    Researches an industrial product category to find general compliance, usage, and safety specs.
    """
    if not category_name or category_name in ["Failed", "Uncategorized"]:
        return {"summary": "Skipped web search for invalid category.", "flags": []}

    tavily_key = os.getenv("TAVILY_API_KEY")
    serper_key = os.getenv("SERPER_API_KEY")
    
    query = f'"{category_name}" industrial specifications compliance safety standards'

    # Tier 1: Tavily
    if tavily_key:
        try:
            print(f"  [Agent] Researching category '{category_name}' via Tavily...")
            client = TavilyClient(api_key=tavily_key)
            response = client.search(query=query, search_depth="basic", max_results=2)
            
            summary = ""
            flags = []
            
            for result in response.get("results", []):
                summary += f"- {result['title']}: {result['content'][:200]}...\n"
                
            return {"summary": summary.strip(), "flags": flags, "tier": "tavily"}
        except Exception as e:
            print(f"  [Agent] Tavily failed: {e}")

    # Tier 2: Serper.dev
    if serper_key:
        try:
            print(f"  [Agent] Researching category '{category_name}' via Serper...")
            url = "https://google.serper.dev/search"
            payload = {"q": query}
            headers = {
                'X-API-KEY': serper_key,
                'Content-Type': 'application/json'
            }
            res = requests.post(url, headers=headers, json=payload, timeout=10)
            if res.status_code == 200:
                data = res.json()
                summary = ""
                for result in data.get("organic", [])[:2]:
                    summary += f"- {result['title']}: {result['snippet']}\n"
                
                return {"summary": summary.strip(), "flags": [], "tier": "serper"}
        except Exception as e:
            print(f"  [Agent] Serper failed: {e}")

    return {
        "summary": "Agentic search skipped (API keys missing or limits exceeded).",
        "flags": [],
        "tier": "failed"
    }

def research_vendor(company_name: str) -> dict[str, Any]:
    """
    Researches a company name on the live internet to determine legitimacy.
    Returns a dictionary with the research summary and any red flags.
    """
    if not company_name:
        return {"summary": "No company name provided.", "flags": []}

    tavily_key = os.getenv("TAVILY_API_KEY")
    serper_key = os.getenv("SERPER_API_KEY")
    
    query = f'"{company_name}" company official website legitimate reviews shell company'

    # Tier 1: Tavily
    if tavily_key:
        try:
            print(f"  [Agent] Researching '{company_name}' via Tavily...")
            client = TavilyClient(api_key=tavily_key)
            response = client.search(query=query, search_depth="advanced", max_results=3)
            
            summary = ""
            flags = []
            
            for result in response.get("results", []):
                summary += f"- {result['title']}: {result['content'][:200]}...\n"
                
            if not response.get("results"):
                flags.append("Company has ZERO online presence. High risk of being a shell company.")
            
            return {"summary": summary.strip(), "flags": flags, "tier": "tavily"}
        except Exception as e:
            print(f"  [Agent] Tavily failed: {e}")

    # Tier 2: Serper.dev
    if serper_key:
        try:
            print(f"  [Agent] Researching '{company_name}' via Serper...")
            import requests
            url = "https://google.serper.dev/search"
            payload = {"q": query}
            headers = {
                'X-API-KEY': serper_key,
                'Content-Type': 'application/json'
            }
            res = requests.post(url, headers=headers, json=payload, timeout=10)
            if res.status_code == 200:
                data = res.json()
                summary = ""
                for result in data.get("organic", [])[:3]:
                    summary += f"- {result['title']}: {result['snippet']}\n"
                
                flags = []
                if not data.get("organic"):
                    flags.append("Company has ZERO Google search results. High risk of being a shell company.")
                    
                return {"summary": summary.strip(), "flags": flags, "tier": "serper"}
        except Exception as e:
            print(f"  [Agent] Serper failed: {e}")

    # Fallback if APIs fail or keys are missing
    return {
        "summary": "Agentic search skipped (API keys missing or limits exceeded).",
        "flags": ["Could not verify vendor legitimacy online."],
        "tier": "failed"
    }
