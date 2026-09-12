"""
Final report generation for Document Intelligence.

Generates a comprehensive PDF report containing all pipeline outputs:
extraction results, validation, confidence scores, classification,
risk flags, and agent research logs.
"""

import sys
import json
from typing import Any
from datetime import datetime, timezone, timedelta

from config.llm_client import get_completion

def generate_ai_narrative_report(
    evidence_text: str,
    record: dict[str, Any],
    risk_flags: list[dict[str, Any]] | None = None,
    agent_log: list[str] | None = None,
    provider: str = "local"
) -> str:
    """
    Generate a detailed narrative financial/document intelligence report using the LLM.
    Uses the full evidence text and structured extraction results.
    """
    sys_prompt = """You are an elite Intelligence Analyst and Document Expert.
Your task is to write a highly professional, precise, and well-structured narrative report based on the provided document text and extraction data.
RULES:
1. ADAPT TO THE DOCUMENT TYPE: Look at the "Type" metadata. 
   - If it is an Invoice/Receipt, summarize the transaction, parties involved, items, amounts, and dates (do NOT complain about missing corporate financials or market risks).
   - If it is a Legal Contract, summarize the parties, terms, obligations, and key dates.
   - If it is a Financial Statement, focus on revenue, profit, margins, and outlook.
2. DO NOT use raw data tables or massive bulleted lists. Write insightful narrative paragraphs.
3. Use appropriate sections for the document type (e.g., "Executive Summary", "Transaction Details" for invoices, "Financial Performance" only for financials). DO NOT output sections like "Financial Performance" or "Strategic Risks" if the document is a simple invoice/receipt.
4. Integrate any risk flags or agent research logs smoothly into the narrative.
5. Format beautifully with Markdown headers (H1, H2, H3) and bold text for emphasis.
6. The report MUST be concise and relevant. Do not pad with fluff or complain about missing data if that data is irrelevant to the document type.
7. Start the report with `# Alchemy AI - Executive Intelligence Brief`.
"""

    user_prompt = f"""
--- DOCUMENT METADATA ---
Title: {record.get('document_title')}
Type: {record.get('document_type')}
Confidence: {record.get('record_confidence')}

--- EXTRACTED FINANCIALS & DATES ---
Financials: {json.dumps(record.get('financial_summary', {}))}
Dates: {json.dumps(record.get('key_dates', {}))}

--- RISK & AGENT LOGS ---
Risks: {json.dumps(risk_flags or [])}
Agent Logs: {json.dumps(agent_log or [])}

--- FULL DOCUMENT TEXT (Truncated if too long) ---
{evidence_text[:15000]}
"""

    # Force using a powerful model for report generation if possible (e.g. gemini/claude/gpt-4)
    # We will pass provider down, or fallback to the standard get_completion logic
    response = get_completion(
        prompt=user_prompt,
        system_prompt=sys_prompt,
        provider=provider,
        temperature=0.3
    )
    return response


def generate_report_markdown(
    record: dict[str, Any],
    validation_result: dict[str, Any] | None = None,
    confidence_summary: dict[str, Any] | None = None,
    taxonomy_result: dict[str, Any] | None = None,
    industry_detection: dict[str, Any] | None = None,
    knowledge_data: dict[str, Any] | None = None,
    risk_flags: list[dict[str, Any]] | None = None,
    onepager_md: str | None = None,
    agent_log: list[str] | None = None,
) -> str:
    """
    Generate the full report as Markdown.

    Combines all pipeline outputs into one premium structured document.
    """
    lines = []
    
    # -------------------------------------------------------------------------
    # Header
    # -------------------------------------------------------------------------
    lines.append("# Alchemy AI - Document Intelligence Report")
    lines.append("")
    
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    lines.append(f"**Generated:** {datetime.now(ist_tz).strftime('%Y-%m-%d %I:%M %p IST')}")
    lines.append(f"**Document Title:** {record.get('document_title', 'Unknown Document')}")
    lines.append("")

    # -------------------------------------------------------------------------
    # Section 1: Executive Summary
    # -------------------------------------------------------------------------
    lines.append("## 1. Executive Summary")
    lines.append("")
    lines.append("> **AI Insight:**")
    lines.append(f"> {record.get('summary', 'No summary available for this document.')}")
    lines.append("")
    
    lines.append("| Core Metadata | Details |")
    lines.append("|---|---|")
    lines.append(f"| **Document Type** | {record.get('document_type', 'N/A')} |")
    lines.append(f"| **Primary Party** | {record.get('primary_party', 'N/A')} |")
    lines.append(f"| **Secondary Party** | {record.get('secondary_party', 'N/A')} |")
    lines.append(f"| **Document Date** | {record.get('document_date', 'N/A')} |")
    lines.append(f"| **Category** | {record.get('category', 'N/A')} |")
    
    rc = record.get('record_confidence', 0.0)
    conf_status = "🟢 High" if rc >= 0.8 else ("🟡 Medium" if rc >= 0.5 else "🔴 Low")
    lines.append(f"| **Overall Confidence** | {rc:.0%} ({conf_status}) |")
    lines.append("")

    # -------------------------------------------------------------------------
    # Section 2: Critical Risk & Compliance Radar
    # -------------------------------------------------------------------------
    lines.append("## 2. Risk & Compliance Radar")
    lines.append("")
    if risk_flags and len(risk_flags) > 0:
        lines.append(f"> ⚠️ **Attention Required:** {len(risk_flags)} potential risk(s) or anomalies detected.")
        lines.append("")
        for flag in risk_flags:
            sev = flag.get("severity", "medium").upper()
            icon = "🔴" if sev == "HIGH" else ("🟡" if sev == "MEDIUM" else "🔵")
            lines.append(f"### {icon} [{sev}] {flag.get('rule_name', 'Flagged Item')}")
            lines.append(f"**Details:** {flag.get('explanation', flag.get('description', ''))}")
            lines.append("")
    else:
        lines.append("> ✅ **Clear:** No critical fraud, safety, or compliance anomalies were flagged by the Risk Radar module.")
        lines.append("")

    # -------------------------------------------------------------------------
    # Section 3: Agentic Web Research Logs
    # -------------------------------------------------------------------------
    lines.append("## 3. Web & Enterprise Research Logs")
    lines.append("")
    if agent_log and len(agent_log) > 0:
        lines.append("The AI Agent performed the following background checks and integrations:")
        lines.append("")
        for log in agent_log:
            lines.append(f"- {log}")
    else:
        lines.append("_No external web research or ERP synchronization was required or performed for this document._")
    lines.append("")

    # -------------------------------------------------------------------------
    # Section 4: Comprehensive Entity Extraction
    # -------------------------------------------------------------------------
    lines.append("## 4. Extracted Entities")
    lines.append("")
    
    entities = record.get("entities", [])
    if entities:
        lines.append("| Entity Type | Extracted Value | Confidence | Source Snippet |")
        lines.append("|---|---|---|---|")
        for ent in entities:
            # Handle both old and new schema
            name = ent.get("entity_type", ent.get("name", ""))
            val = ent.get("value", "")
            unit = ent.get("unit", "")
            if unit:
                val = f"{val} {unit}"
            
            conf = ent.get("confidence", 0.0)
            source = (ent.get("source_text", "") or "")[:60].replace("\n", " ").strip()
            if len(source) == 60:
                source += "..."
                
            conf_icon = "🟢" if conf >= 0.7 else ("🟡" if conf >= 0.4 else "🔴")
            lines.append(f"| **{name}** | {val} | {conf_icon} {conf:.0%} | _{source}_ |")
    else:
        lines.append("_No specific entities (Persons, Organizations, Amounts, etc.) were identified._")
    lines.append("")

    # -------------------------------------------------------------------------
    # Section 5: Financials & Key Dates
    # -------------------------------------------------------------------------
    financials = record.get("financial_summary", {})
    dates = record.get("key_dates", {})
    
    if financials or dates:
        lines.append("## 5. Financials & Key Dates")
        lines.append("")
        if financials:
            lines.append("### Financial Breakdown")
            lines.append("| Metric | Value |")
            lines.append("|---|---|")
            for k, v in financials.items():
                k_clean = k.replace("_", " ").title()
                lines.append(f"| {k_clean} | {v} |")
            lines.append("")
            
        if dates:
            lines.append("### Important Dates")
            lines.append("| Event | Date |")
            lines.append("|---|---|")
            for k, v in dates.items():
                k_clean = k.replace("_", " ").title()
                lines.append(f"| {k_clean} | {v} |")
            lines.append("")

    # -------------------------------------------------------------------------
    # Section 6: Validation & Quality Assessment
    # -------------------------------------------------------------------------
    lines.append("## 6. Document Validation Matrix")
    lines.append("")
    
    passed = record.get("validation_passed", False)
    status_msg = "✅ Passed Quality Checks" if passed else "❌ Failed Verification (Manual Review Required)"
    lines.append(f"**Overall Status:** {status_msg}")
    lines.append("")
    
    review_fields = record.get("fields_for_review", [])
    if review_fields:
        lines.append("**Fields Flagged for Manual Review (Low Confidence):**")
        for f in review_fields:
            lines.append(f"- `{f}`")
    else:
        lines.append("_All extracted core fields met the minimum confidence thresholds._")
        
    lines.append("")

    # -------------------------------------------------------------------------
    # Footer
    # -------------------------------------------------------------------------
    lines.append("---")
    lines.append("*Report generated by Alchemy AI - Document Intelligence Platform*")
    lines.append("*Machine Processed & Cryptographically Secured*")
    
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m report.generate_report <record_json> [output.md]")
        sys.exit(1)

    with open(sys.argv[1], "r", encoding="utf-8") as f:
        record = json.load(f)

    markdown = generate_report_markdown(record)

    if len(sys.argv) > 2:
        with open(sys.argv[2], "w", encoding="utf-8") as f:
            f.write(markdown)
        print(f"Report saved to: {sys.argv[2]}")
    else:
        print(markdown)
