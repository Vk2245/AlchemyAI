"""
Renders generated content (one-pager, reports) to Markdown and HTML.

Converts Markdown strings to styled HTML documents suitable for
viewing in a browser or converting to PDF.
"""

import sys
from pathlib import Path
from typing import Optional


# Minimal CSS for clean rendered output
REPORT_CSS = """
@page {
    margin: 0.4in;
    @bottom-right {
        content: counter(page) " / " counter(pages);
        font-family: 'Inter', system-ui, sans-serif;
        font-size: 9pt;
        color: #52525b;
    }
}
body {
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
    max-width: 100%;
    margin: 0;
    padding: 0;
    color: #18181b;
    background-color: #ffffff;
    line-height: 1.6;
}
h1 { color: #000000; border-bottom: 3px solid #3b82f6; padding-bottom: 12px; font-weight: 800; font-size: 24pt; margin-bottom: 16px; letter-spacing: -0.02em; }
h2 { color: #4c1d95; background-color: #f5f3ff; border-left: 4px solid #7c3aed; padding: 10px 14px; margin-top: 32px; font-weight: 700; font-size: 14pt; letter-spacing: 0.02em; text-transform: uppercase; border-radius: 0 4px 4px 0; }
h3 { color: #52525b; font-size: 12pt; font-weight: 600; padding-bottom: 4px; border-bottom: 1px solid #e4e4e7; }
table { border-collapse: separate; border-spacing: 0; width: 100%; margin: 24px 0; font-size: 10pt; border: 1px solid #d4d4d8; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
th, td { border-bottom: 1px solid #e4e4e7; border-right: 1px solid #e4e4e7; padding: 12px 16px; text-align: left; }
th:last-child, td:last-child { border-right: none; }
tr:last-child th, tr:last-child td { border-bottom: none; }
th { background-color: #f4f4f5; color: #18181b; font-size: 9pt; font-weight: 700; letter-spacing: 0.03em; text-transform: uppercase; border-bottom: 2px solid #d4d4d8; }
tr:nth-child(even) { background-color: #fafafa; }
tr:nth-child(odd) { background-color: #ffffff; }
.confidence-high { color: #059669; font-weight: 600; }
.confidence-medium { color: #d97706; font-weight: 600; }
.confidence-low { color: #dc2626; font-weight: 600; }
.risk-critical { background-color: rgba(239, 68, 68, 0.1); padding: 12px; border-left: 4px solid #ef4444; margin: 12px 0; border-radius: 0 6px 6px 0; color: #b91c1c; font-weight: 500; }
.risk-high { background-color: rgba(245, 158, 11, 0.1); padding: 12px; border-left: 4px solid #f59e0b; margin: 12px 0; border-radius: 0 6px 6px 0; color: #b45309; font-weight: 500; }
.risk-medium { background-color: rgba(59, 130, 246, 0.1); padding: 12px; border-left: 4px solid #3b82f6; margin: 12px 0; border-radius: 0 6px 6px 0; color: #1d4ed8; font-weight: 500; }
code { background-color: #f4f4f5; padding: 4px 6px; border-radius: 6px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 9pt; color: #2563eb; border: 1px solid rgba(0, 0, 0, 0.1); }
"""


def render_to_html(
    markdown_content: str,
    title: str = "Product Intelligence Report",
    extra_css: str = "",
) -> str:
    """
    Convert Markdown content to a styled HTML document.
    """
    import markdown as md

    html_body = md.markdown(
        markdown_content,
        extensions=["tables", "fenced_code", "toc"],
    )

    css = REPORT_CSS + extra_css

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>{css}</style>
</head>
<body>
{html_body}
</body>
</html>"""

    return html_doc


def save_html(
    html_content: str,
    output_path: str,
) -> str:
    """Save HTML content to a file. Returns the output path."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    return output_path


def render_to_pdf(
    html_content: str,
    output_path: str,
) -> str:
    """
    Convert HTML to PDF using weasyprint.

    Returns the output PDF path. Falls back to saving HTML only
    if weasyprint is not available.
    """
    try:
        import os
        import sys
        if sys.platform == "win32":
            # Add GTK bin directories to path for WeasyPrint
            gtk_bin = r"C:\msys64\mingw64\bin"
            if os.path.exists(gtk_bin):
                if gtk_bin not in os.environ["PATH"]:
                    os.environ["PATH"] = gtk_bin + os.path.pathsep + os.environ["PATH"]
                if hasattr(os, "add_dll_directory"):
                    try:
                        os.add_dll_directory(gtk_bin)
                    except Exception as ex:
                        print(f"[WeasyPrint Setup] Failed to add dll directory {gtk_bin}: {ex}")

        from weasyprint import HTML
        HTML(string=html_content).write_pdf(output_path)
        return output_path
    except Exception as e:
        # Fallback: save as HTML if weasyprint or its GTK dependencies fail to load
        html_path = output_path.replace(".pdf", ".html")
        save_html(html_content, html_path)
        print(f"PDF generation failed ({e}), saved as HTML instead: {html_path}")
        return html_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m onepager.render_output <markdown_file> [output.html|output.pdf]")
        sys.exit(1)

    md_path = sys.argv[1]
    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    output = sys.argv[2] if len(sys.argv) > 2 else md_path.replace(".md", ".html")

    html = render_to_html(md_content)

    if output.endswith(".pdf"):
        result = render_to_pdf(html, output)
    else:
        result = save_html(html, output)

    print(f"Rendered to: {result}")
