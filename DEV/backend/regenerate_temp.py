import sqlite3
import os
import sys
from pathlib import Path

# Add AI-ML to path for onepager import
sys.path.append(os.path.abspath("../../AI-ML"))
from onepager.render_output import render_to_html, render_to_pdf

def regenerate():
    conn = sqlite3.connect("Alchemy AI.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, report_markdown, report_pdf_path, report_html_path FROM reports")
    reports = cursor.fetchall()
    
    updated = 0
    for row in reports:
        id_, markdown, pdf_path, html_path = row
        if markdown and pdf_path:
            html_content = render_to_html(markdown, title="Product Intelligence Report")
            # Force create parent dirs
            Path(pdf_path).parent.mkdir(parents=True, exist_ok=True)
            try:
                render_to_pdf(html_content, pdf_path)
                updated += 1
                print(f"Updated {pdf_path}")
            except Exception as e:
                print(f"Failed PDF: {e}")
            if html_path:
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
    
    print(f"Total updated: {updated}")

if __name__ == "__main__":
    regenerate()
