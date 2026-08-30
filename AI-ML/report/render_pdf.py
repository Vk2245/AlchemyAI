"""
Render the final report to PDF.

Takes the Markdown report from generate_report.py and converts it
to a styled HTML document, then to PDF using weasyprint.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

from config.settings import REPORTS_DIR
from onepager.render_output import render_to_html, render_to_pdf, save_html


def render_report(
    markdown_content: str,
    product_name: str = "product",
    output_dir: str | None = None,
    formats: list[str] | None = None,
) -> dict[str, str]:
    """
    Render a report Markdown string to HTML and/or PDF.

    Returns a dict mapping format to output file path.
    """
    if output_dir is None:
        output_dir = str(REPORTS_DIR)
    if formats is None:
        formats = ["html", "pdf"]

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Clean filename
    safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in product_name)
    safe_name = safe_name.strip().replace(" ", "_")[:50]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    base_name = f"report_{safe_name}_{timestamp}"

    html_content = render_to_html(
        markdown_content,
        title=f"Product Intelligence Report - {product_name}",
    )

    outputs: dict[str, str] = {}

    if "html" in formats:
        html_path = str(out_dir / f"{base_name}.html")
        save_html(html_content, html_path)
        outputs["html"] = html_path

    if "pdf" in formats:
        pdf_path = str(out_dir / f"{base_name}.pdf")
        result = render_to_pdf(html_content, pdf_path)
        outputs["pdf"] = result

    return outputs


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m report.render_pdf <report.md> [product_name]")
        sys.exit(1)

    md_path = sys.argv[1]
    product_name = sys.argv[2] if len(sys.argv) > 2 else "product"

    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    outputs = render_report(md_content, product_name=product_name)
    for fmt, path in outputs.items():
        print(f"  {fmt.upper()}: {path}")
