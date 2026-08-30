"""
Alchemy AI MCP Server — Model Context Protocol.

Exposes the Alchemy AI AI-ML pipeline as tools that any MCP-compatible
AI assistant (Claude Desktop, Cursor, etc.) can use directly.

Tools:
  - analyze_product: Run full pipeline on a PDF file
  - search_products: Search the product knowledge base
  - check_risks: Get safety/compliance risk flags for a product
  - get_product_record: Retrieve a saved product record

Testing:
  1. Run:  python server.py
  2. Or:   mcp dev server.py  (opens the MCP Inspector)
  3. Or:   Add to Claude Desktop config (see README)

Claude Desktop config (claude_desktop_config.json):
{
    "mcpServers": {
        "Alchemy AI": {
            "command": "python",
            "args": ["<path>/DEV/mcp_server/server.py"]
        }
    }
}
"""

import sys
import json
import logging
from pathlib import Path
from typing import Any

# Add AI-ML to path
AI_ML_DIR = Path(__file__).resolve().parent.parent / "AI-ML"
if str(AI_ML_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ML_DIR))

from mcp.server.fastmcp import FastMCP

# Use stderr for logging (stdout is reserved for MCP JSON-RPC)
logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("Alchemy AI-mcp")


# ---------------------------------------------------------------------------
# Initialize MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "Alchemy AI",
    description="Product Intelligence Platform — analyze product PDFs, search knowledge base, check compliance risks",
)


# ---------------------------------------------------------------------------
# Tool: Analyze Product PDF
# ---------------------------------------------------------------------------

@mcp.tool()
def analyze_product(pdf_path: str) -> str:
    """
    Analyze a product PDF and extract structured intelligence.

    Takes a path to a PDF file and runs the full Alchemy AI pipeline:
    ingestion, extraction, validation, confidence scoring, industry
    detection, taxonomy, risk radar, and report generation.

    Returns a JSON string with the complete product record.
    """
    logger.info(f"Analyzing: {pdf_path}")

    if not Path(pdf_path).exists():
        return json.dumps({"error": f"File not found: {pdf_path}"})

    try:
        from pipeline.run import run_pipeline

        result = None
        for update in run_pipeline(pdf_path):
            logger.info(f"[{update['progress']:>3}%] {update['message']}")
            if update["progress"] == 100:
                result = update["data"]
            elif update["progress"] == -1:
                return json.dumps({"error": update["message"]})

        if result:
            # Return a clean summary
            record = result.get("record", {})
            risks = result.get("risks", {})
            return json.dumps({
                "product_name": record.get("product_name", ""),
                "manufacturer": record.get("manufacturer", ""),
                "part_number": record.get("part_number", ""),
                "industry": record.get("industry", ""),
                "category": record.get("category", ""),
                "record_confidence": record.get("record_confidence", 0),
                "validation_passed": record.get("validation_passed", False),
                "attributes": record.get("attributes", []),
                "risk_level": risks.get("overall_risk_level", "unknown"),
                "risk_flags": risks.get("total_flags", 0),
                "report_paths": result.get("report_paths", {}),
                "processing_time_sec": result.get("processing_time_sec", 0),
            }, indent=2)

        return json.dumps({"error": "Pipeline did not produce results"})

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Tool: Search Products
# ---------------------------------------------------------------------------

@mcp.tool()
def search_products(query: str, n_results: int = 5) -> str:
    """
    Search the Alchemy AI product knowledge base.

    Uses semantic search (nomic-embed-text) to find products
    similar to the query. Works with product names, descriptions,
    part numbers, or natural language queries.
    """
    logger.info(f"Searching: {query}")

    try:
        from knowledge.embed_products import query_similar

        results = query_similar(query, n_results=n_results)

        matches = []
        for r in results:
            meta = r.get("metadata", {})
            matches.append({
                "id": r["id"],
                "product_name": meta.get("product_name", ""),
                "manufacturer": meta.get("manufacturer", ""),
                "distance": r.get("distance", None),
            })

        return json.dumps({"query": query, "count": len(matches), "matches": matches}, indent=2)

    except Exception as e:
        logger.error(f"Search failed: {e}")
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Tool: Check Risks
# ---------------------------------------------------------------------------

@mcp.tool()
def check_risks(product_name: str, industry: str, description: str = "") -> str:
    """
    Check safety and compliance risks for a product.

    Dynamically generates industry-specific safety rules and checks
    if the product might be missing critical specifications.
    """
    logger.info(f"Checking risks for: {product_name} ({industry})")

    try:
        from risk_radar.detect_risk import detect_risks, get_risk_summary

        record = {
            "product_name": product_name,
            "industry": industry,
            "description": description,
            "attributes": [],
        }

        flags = detect_risks(record, industry=industry)
        summary = get_risk_summary(flags)

        return json.dumps(summary, indent=2)

    except Exception as e:
        logger.error(f"Risk check failed: {e}")
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Tool: Match Product (Snap and Find)
# ---------------------------------------------------------------------------

@mcp.tool()
def match_product(input_value: str) -> str:
    """
    Find the nearest catalog match for a photo or text snippet.

    Accepts either an image file path or a text string (error log,
    config line, version string). Auto-detects the input type.
    """
    logger.info(f"Matching: {input_value[:100]}")

    try:
        from visual_match.match_input import match_input

        matches = match_input(input_value, n_results=5)
        return json.dumps({"input": input_value[:100], "matches": matches}, indent=2)

    except Exception as e:
        logger.error(f"Match failed: {e}")
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Resource: Product Record by ID
# ---------------------------------------------------------------------------

@mcp.resource("product://{product_id}")
def get_product_record(product_id: str) -> str:
    """Get a product record from the knowledge base by its ID."""
    logger.info(f"Fetching product: {product_id}")

    try:
        from knowledge.embed_products import get_product_collection

        collection = get_product_collection()
        result = collection.get(ids=[product_id], include=["documents", "metadatas"])

        if not result["ids"]:
            return json.dumps({"error": f"Product '{product_id}' not found"})

        return json.dumps({
            "id": result["ids"][0],
            "document": result["documents"][0] if result["documents"] else "",
            "metadata": result["metadatas"][0] if result["metadatas"] else {},
        }, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("Starting Alchemy AI MCP Server...")
    mcp.run()
