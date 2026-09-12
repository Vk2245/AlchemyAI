"""
Master Orchestrator Pipeline for Document Intelligence.

Ties together all AI-ML phases into a single execution flow.
Designed to be called by a FastAPI backend. Yields progress updates
as Server-Sent Events (SSE) so the frontend can display a progress bar.
"""

import sys
import time
import requests
from typing import Any, Generator

from ingestion.parse_pdf import extract_pages
from ingestion.ocr_fallback import process_pages_with_ocr
from ingestion.evidence_builder import build_evidence
from extraction.extract_attributes import extract_record_from_evidence
# from validation.validate_record import validate_record
from risk_radar.detect_risk import detect_risk
from risk_radar.collusion_graph import detect_collusion
from agent.web_research import research_vendor


def trigger_erp_sync(record_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Mock ERP Webhook trigger (Agentic Workflow Orchestration).
    Sends the extracted JSON to a mock ERP endpoint.
    """
    # In a real scenario, this would hit the FastAPI mock endpoint.
    # We will simulate the network call success here.
    return {
        "status": "success",
        "message": f"Successfully synced Document '{record_dict.get('document_title')}' to ERP."
    }


def run_pipeline(
    pdf_path: str,
    provider: str = "gemini",
    execution_mode: str = "online",
) -> Generator[dict[str, Any], None, None]:
    """
    Run the full end-to-end document intelligence pipeline.
    Yields progress dicts at each step.
    """
    start_time = time.time()

    def _yield_progress(percent: int, message: str, data: Any = None) -> dict:
        return {"progress": percent, "message": message, "data": data}

    try:
        # Branch detection
        branch_name = "Cloud API Pipeline (Gemini/Groq)" if execution_mode == "online" else "Local Edge Pipeline (vLLM)"
        yield _yield_progress(5, f"Branch Selected: {branch_name}")

        # Stage 1: Document Ingestion
        yield _yield_progress(15, "Document Ingestion...")
        pages = extract_pages(pdf_path)
        
        # Stage 2: OCR Fallback
        yield _yield_progress(25, "Running OCR & Vision audit...")
        pages = process_pages_with_ocr(pdf_path, pages, execution_mode=execution_mode)
            
        evidence = build_evidence(pdf_path, pages)
        
        # Check if empty or contains only garbage/punctuation
        import re
        text_content = evidence.get("full_text", "")
        alphanumeric_chars = re.sub(r'[^a-zA-Z0-9]', '', text_content)
        if len(alphanumeric_chars) < 5:
            yield {"progress": -1, "message": "Document is empty or unreadable by OCR", "data": None}
            return

        # Stage 3: Fraud Audit
        yield _yield_progress(40, "Running Multi-Tier Fraud Audit...")

        # Stage 4: Entity Extraction
        yield _yield_progress(55, "Performing Adaptive NER and Data Extraction...")
        record = extract_record_from_evidence(evidence, provider=provider)
        
        # Stage 5: Classification
        yield _yield_progress(70, "Dynamically Classifying Document...")
        
        # Phase 6 & 7: Validation & Scoring
        from confidence.score_record import score_record
        record = score_record(record)
        record_dict = record.model_dump()

        # Stage 6: Agent Research
        yield _yield_progress(80, "Cross-Referencing and Agent Research...")
        # Risk Radar will invoke it if needed
        
        # Stage 7: Risk Radar
        yield _yield_progress(90, "Evaluating Adaptive Risk & Compliance...")
        risk_res = detect_risk(record)
        risk_summary = {
            "overall_risk_level": risk_res["overall_risk_level"],
            "detected_risks": risk_res["risk_flags"]
        }
        
        # Collusion Detection
        collusion_res = detect_collusion(record)
        if collusion_res["is_collusion"]:
            risk_summary["detected_risks"].extend(collusion_res["collusion_flags"])
            risk_summary["overall_risk_level"] = "high"

        # Agentic Web Research (if Risk Radar flags it)
        agent_log = []
        if risk_res.get("requires_agentic_research"):
            vendor_name = record.primary_party
            yield _yield_progress(95, f"Agent autonomously researching '{vendor_name}'...")
            web_res = research_vendor(vendor_name)
            agent_log.append(f"Used Tier: {web_res.get('tier')}")
            agent_log.append(f"Summary: {web_res.get('summary')}")
            if web_res.get("flags"):
                risk_summary["detected_risks"].extend(web_res["flags"])
                risk_summary["overall_risk_level"] = "high"
                
        # Agentic Workflow Orchestration (Mock ERP Sync)
        if risk_summary["overall_risk_level"] == "low" and record.record_confidence > 0.9:
            erp_res = trigger_erp_sync(record_dict)
            agent_log.append(erp_res["message"])

        # Stage 8: AI Narrative Report Generation
        yield _yield_progress(95, "Generating AI Analyst Narrative Report...")
        from report.generate_report import generate_ai_narrative_report
        
        # Determine best provider available, default to what's requested
        report_provider = provider
        if provider == "local" and "gemini" in str(provider).lower():
            report_provider = "gemini" # attempt to escalate
            
        evidence_content = evidence.get("full_markdown") or evidence.get("full_text", "")
        report_md = generate_ai_narrative_report(
            evidence_text=evidence_content,
            record=record_dict,
            risk_flags=risk_summary.get("detected_risks", []),
            agent_log=agent_log,
            provider=report_provider
        )

        # Stage 9: Final Payload
        yield _yield_progress(100, "Report Generation complete!", {
            "record": record_dict,
            "risks": risk_summary,
            "agent_log": agent_log,
            "report_md": report_md,
            "processing_time_sec": round(time.time() - start_time, 2)
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        yield {"progress": -1, "message": f"Error: {str(e)}", "data": None}


# ---------------------------------------------------------------------------
# CLI wrapper
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m pipeline.run <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    
    for update in run_pipeline(pdf_path):
        prog = update["progress"]
        msg = update["message"]
        
        if prog == -1:
            print(f"\n[FAIL] {msg}")
            break
            
        print(f"[{prog:>3}%] {msg}")
