"""
Master Orchestrator Pipeline.

Ties together all AI-ML phases (0-8) into a single execution flow.
Designed to be called by a FastAPI backend. Yields progress updates
as Server-Sent Events (SSE) so the frontend can display a progress bar
and human-readable logs.
"""

import sys
import json
import time
from typing import Any, Generator

from ingestion.parse_pdf import extract_pages
from ingestion.ocr_fallback import process_pages_with_ocr
from ingestion.evidence_builder import build_evidence
from extraction.extract_attributes import extract_record_from_evidence
from validation.validate_record import validate_record
from confidence.score_record import score_record, get_confidence_summary
from company_discovery.detect_industry import detect_industry
from taxonomy.classify_taxonomy import classify_record
from risk_radar.detect_risk import detect_risks, get_risk_summary
from agent.research_graph import research_missing_attributes
from onepager.generate_onepager import generate_onepager
from report.generate_report import generate_report_markdown
from report.render_pdf import render_report


def run_pipeline(
    pdf_path: str,
    provider: str = "local",
) -> Generator[dict[str, Any], None, None]:
    """
    Run the full end-to-end product intelligence pipeline.
    Yields progress dicts at each step.
    """
    start_time = time.time()

    def _yield_progress(percent: int, message: str, data: Any = None) -> dict:
        return {"progress": percent, "message": message, "data": data}

    try:
        # Phase 0: Ingestion
        yield _yield_progress(5, "Reading PDF document...")
        pages = extract_pages(pdf_path)
        
        # Check if we need OCR
        yield _yield_progress(10, "Checking for scanned pages...")
        from config.settings import VISION_PROVIDER
        pages = process_pages_with_ocr(pdf_path, pages, provider=VISION_PROVIDER)
            
        evidence = build_evidence(pdf_path, pages)
        
        # Check if empty
        if not evidence.get("full_text", "").strip():
            yield {"progress": -1, "message": "Document is empty and OCR failed", "data": None}
            return

        # Phase 2: Industry Detection
        yield _yield_progress(15, "Detecting industry and product domain...")
        industry_res = detect_industry(evidence, provider=provider)
        industry_name = industry_res.industry if industry_res else "General"
        
        # Phase 1: Extraction
        yield _yield_progress(25, f"Extracting attributes for {industry_name} product...")
        record = extract_record_from_evidence(evidence, provider=provider)
        record.industry = industry_name
        record.industry_profile = industry_res.product_domain if industry_res else ""

        # Phase 2: Taxonomy
        yield _yield_progress(40, "Classifying product taxonomy...")
        taxonomy_res = classify_record(record, provider=provider)
        if taxonomy_res:
            record.category = taxonomy_res.segment
            record.subcategory = taxonomy_res.family

        # Phase 1b: Validation
        yield _yield_progress(45, "Validating extracted data against rules...")
        val_result = validate_record(record)
        record.validation_passed = val_result.passed
        
        # Phase 2b: Confidence Scoring
        yield _yield_progress(50, "Calculating confidence scores...")
        record = score_record(record)
        
        # Convert to dict for downstream phases
        record_dict = record.model_dump()
        conf_result = get_confidence_summary(record)

        # Phase 8: Agentic Web Research (if needed)
        missing = record_dict.get("fields_for_review", [])
        agent_log = []
        if missing:
            yield _yield_progress(55, f"Agent researching {len(missing)} missing attributes online...")
            research_res = research_missing_attributes(record_dict, missing)
            
            # Merge findings
            if research_res.get("extracted_attributes"):
                for new_attr in research_res["extracted_attributes"]:
                    # Set default confidence for agent-found items
                    new_attr["confidence"] = 0.7
                    record_dict["attributes"].append(new_attr)
                yield _yield_progress(70, f"Agent found {len(research_res['extracted_attributes'])} missing attributes.")
            else:
                yield _yield_progress(70, "Agent could not find missing attributes.")
            
            agent_log = research_res.get("tier_log", [])

        # Phase 7: Risk Radar
        yield _yield_progress(75, f"Running safety and compliance checks for {industry_name}...")
        risk_flags = detect_risks(record_dict, industry=industry_name, provider=provider)
        risk_summary = get_risk_summary(risk_flags)

        # Phase 8: One-Pager
        yield _yield_progress(85, "Drafting executive one-pager...")
        onepager_md = generate_onepager(record_dict, provider=provider)

        # Phase 8: Final Report Generation
        yield _yield_progress(90, "Generating final PDF report...")
        report_md = generate_report_markdown(
            record=record_dict,
            validation_result=val_result.model_dump(),
            confidence_summary=conf_result,
            taxonomy_result=taxonomy_res.model_dump() if taxonomy_res else None,
            industry_detection=industry_res.model_dump() if industry_res else None,
            risk_flags=risk_flags,
            onepager_md=onepager_md,
        )
        
        outputs = render_report(report_md, product_name=record_dict.get("product_name", "unknown"))

        # Final Payload
        yield _yield_progress(100, "Processing complete!", {
            "record": record_dict,
            "validation": val_result.model_dump(),
            "confidence": conf_result,
            "risks": risk_summary,
            "agent_log": agent_log,
            "report_paths": outputs,
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
        
        if prog == 100:
            print("\nDone! Report saved to:")
            for fmt, path in update["data"]["report_paths"].items():
                print(f"  {fmt.upper()}: {path}")
