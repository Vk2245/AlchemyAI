"""
Final report generation.

Generates a comprehensive PDF report containing all pipeline outputs:
extraction results, validation, confidence scores, taxonomy, industry
detection, knowledge layer findings, risk flags, and the one-pager.
This is a COMPULSORY output of every pipeline run.
"""

import sys
import json
from typing import Any
from datetime import datetime, timezone

from config.llm_client import get_completion
from config.toon_utils import wrap_for_prompt
from config.settings import REPORTS_DIR


def generate_report_markdown(
    record: dict[str, Any],
    validation_result: dict[str, Any] | None = None,
    confidence_summary: dict[str, Any] | None = None,
    taxonomy_result: dict[str, Any] | None = None,
    industry_detection: dict[str, Any] | None = None,
    knowledge_data: dict[str, Any] | None = None,
    risk_flags: list[dict[str, Any]] | None = None,
    onepager_md: str | None = None,
) -> str:
    """
    Generate the full report as Markdown.

    Combines all pipeline outputs into one structured document.
    """
    lines = []

    # Header
    lines.append("# Product Intelligence Report")
    lines.append("")
    from datetime import timedelta
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    lines.append(f"**Generated:** {datetime.now(ist_tz).strftime('%Y-%m-%d %I:%M %p IST')}")
    lines.append(f"**Source:** {record.get('source_file', 'N/A')}")
    lines.append("")

    # --- Section 1: Product Overview ---
    lines.append("## 1. Product Overview")
    lines.append("")
    lines.append(f"| Field | Value |")
    lines.append(f"|---|---|")
    lines.append(f"| **Product Name** | {record.get('product_name', 'N/A')} |")
    lines.append(f"| **Manufacturer** | {record.get('manufacturer', 'N/A')} |")
    lines.append(f"| **Part Number** | {record.get('part_number', 'N/A')} |")
    lines.append(f"| **Description** | {record.get('description', 'N/A')} |")
    lines.append("")

    # --- Section 2: Industry Detection ---
    lines.append("## 2. Industry Detection")
    lines.append("")
    if industry_detection:
        lines.append(f"| Field | Value |")
        lines.append(f"|---|---|")
        lines.append(f"| **Industry** | {industry_detection.get('industry', 'N/A')} |")
        lines.append(f"| **Product Domain** | {industry_detection.get('product_domain', 'N/A')} |")
        lines.append(f"| **Product Family** | {industry_detection.get('product_family', 'N/A')} |")
        lines.append(f"| **Document Type** | {industry_detection.get('document_type', 'N/A')} |")
        lines.append(f"| **Confidence** | {industry_detection.get('confidence', 0):.0%} |")
        lines.append(f"| **Reasoning** | {industry_detection.get('reasoning', 'N/A')} |")
    else:
        lines.append("_Industry detection was not run._")
    lines.append("")

    # --- Section 3: Extracted Attributes ---
    lines.append("## 3. Extracted Attributes")
    lines.append("")
    attrs = record.get("attributes", [])
    if attrs:
        lines.append(f"| Attribute | Value | Unit | Confidence | Source |")
        lines.append(f"|---|---|---|---|---|")
        for attr in attrs:
            name = attr.get("name", "")
            value = attr.get("value", "")
            unit = attr.get("unit", "") or ""
            conf = attr.get("confidence", 0.0)
            source = (attr.get("source_text", "") or "")[:50]
            conf_str = f"{conf:.0%}"
            lines.append(f"| {name} | {value} | {unit} | {conf_str} | {source} |")
    else:
        lines.append("_No attributes extracted._")
    lines.append("")

    # --- Section 4: Taxonomy ---
    lines.append("## 4. Taxonomy Classification")
    lines.append("")
    if taxonomy_result:
        lines.append(f"| Field | Value |")
        lines.append(f"|---|---|")
        lines.append(f"| **Category** | {taxonomy_result.get('segment', '')} > {taxonomy_result.get('family', '')} > {taxonomy_result.get('product_class', '')} |")
        lines.append(f"| **Code** | {taxonomy_result.get('category_code', 'N/A')} |")
        lines.append(f"| **Confidence** | {taxonomy_result.get('confidence', 0):.0%} |")
        lines.append(f"| **Reasoning** | {taxonomy_result.get('reasoning', 'N/A')} |")
    else:
        lines.append(f"**Category:** {record.get('category', 'N/A')}")
    lines.append("")

    # --- Section 5: Validation ---
    lines.append("## 5. Validation Results")
    lines.append("")
    if validation_result:
        passed = validation_result.get("passed", False)
        lines.append(f"**Status:** {'PASSED' if passed else 'FAILED'}")
        lines.append(f"**Errors:** {validation_result.get('error_count', 0)}")
        lines.append(f"**Warnings:** {validation_result.get('warning_count', 0)}")
        issues = validation_result.get("issues", [])
        if issues:
            lines.append("")
            lines.append("| Severity | Field | Message |")
            lines.append("|---|---|---|")
            for issue in issues:
                sev = issue.get("severity", "info").upper()
                field = issue.get("field", "")
                msg = issue.get("message", "")
                lines.append(f"| {sev} | {field} | {msg} |")
    else:
        passed = record.get("validation_passed", False)
        lines.append(f"**Status:** {'PASSED' if passed else 'FAILED'}")
        errors = record.get("validation_errors", [])
        if errors:
            for err in errors:
                lines.append(f"- {err}")
    lines.append("")

    # --- Section 6: Confidence ---
    lines.append("## 6. Confidence Scoring")
    lines.append("")
    if confidence_summary:
        rc = confidence_summary.get("record_confidence", 0.0)
        lines.append(f"**Record Confidence:** {rc:.0%}")
        lines.append(f"**Total Attributes:** {confidence_summary.get('total_attributes', 0)}")
        lines.append(f"**High Confidence (>=70%):** {confidence_summary.get('high_confidence', 0)}")
        lines.append(f"**Medium Confidence (40-70%):** {confidence_summary.get('medium_confidence', 0)}")
        lines.append(f"**Low Confidence (<40%):** {confidence_summary.get('low_confidence', 0)}")
        review = confidence_summary.get("fields_for_review", [])
        if review:
            lines.append(f"**Fields for Review:** {', '.join(review)}")
    else:
        rc = record.get("record_confidence", 0.0)
        lines.append(f"**Record Confidence:** {rc:.0%}")
    lines.append("")

    # --- Section 7: Risk Radar ---
    lines.append("## 7. Safety and Compliance Risk Radar")
    lines.append("")
    if risk_flags:
        lines.append(f"**Total Flags:** {len(risk_flags)}")
        lines.append("")
        for flag in risk_flags:
            sev = flag.get("severity", "info")
            lines.append(f"### [{sev.upper()}] {flag.get('rule_name', '')}")
            lines.append(f"{flag.get('explanation', flag.get('description', ''))}")
            lines.append("")
    else:
        lines.append("_No safety/compliance risks detected._")
    lines.append("")

    # --- Section 8: Knowledge Layer ---
    if knowledge_data:
        lines.append("## 8. Knowledge Layer")
        lines.append("")
        if knowledge_data.get("similar_products"):
            lines.append("### Similar Products")
            for sp in knowledge_data["similar_products"][:5]:
                lines.append(f"- {sp.get('product_name', '?')} ({sp.get('manufacturer', '?')}) - Similarity: {sp.get('similarity_score', 0):.0%}")
            lines.append("")
        if knowledge_data.get("compatible_products"):
            lines.append("### Compatible Products")
            for cp in knowledge_data["compatible_products"][:5]:
                lines.append(f"- {cp.get('product_name', '?')} ({cp.get('manufacturer', '?')})")
            lines.append("")

    # --- Section 9: One-Pager ---
    if onepager_md:
        lines.append("## 9. Auto-Generated Product One-Pager")
        lines.append("")
        lines.append(onepager_md)
        lines.append("")

    # Footer
    lines.append("---")
    lines.append(f"*Report generated by Product Intelligence Platform AI-ML Module*")
    lines.append(f"*Content hash: {record.get('content_hash', 'N/A')}*")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

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
