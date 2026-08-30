"""
Builds a unified DocumentEvidence object from parsed PDF pages.

Combines page-level text, tables, images, and metadata into a single
structured dict that downstream modules (extraction, validation) consume.
This is the bridge between raw PDF parsing and the intelligence pipeline.
"""

import sys
import json
import hashlib
from pathlib import Path
from typing import Any
from datetime import datetime, timezone


def build_evidence(
    pdf_path: str,
    pages: list[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Assemble a DocumentEvidence dict from parsed pages.

    The evidence object is the canonical input for all Stage 1 modules.
    It contains the full document text, per-page details, source metadata,
    and a content hash for deduplication.
    """
    pdf_path_obj = Path(pdf_path)
    full_text = "\n\n".join(p["raw_text"] for p in pages)
    full_markdown = "\n\n".join(p.get("markdown", p["raw_text"]) for p in pages)

    # Count totals
    total_chars = sum(p["char_count"] for p in pages)
    total_images = sum(len(p.get("image_refs", [])) for p in pages)
    ocr_pages = sum(1 for p in pages if p.get("ocr_applied", False))

    # Content hash for deduplication
    content_hash = hashlib.sha256(full_text.encode("utf-8")).hexdigest()[:16]

    evidence: dict[str, Any] = {
        "source_file": pdf_path_obj.name,
        "source_path": str(pdf_path_obj.resolve()),
        "content_hash": content_hash,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "page_count": len(pages),
        "total_chars": total_chars,
        "total_images": total_images,
        "ocr_pages": ocr_pages,
        "full_text": full_text,
        "full_markdown": full_markdown,
        "pages": pages,
        "metadata": metadata or {},
    }

    return evidence


def save_evidence(evidence: dict[str, Any], output_dir: str) -> str:
    """
    Save a DocumentEvidence dict to a JSON file.

    Returns the path to the saved file. The filename is based on the
    source PDF name and content hash for uniqueness.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    source_name = Path(evidence["source_file"]).stem
    content_hash = evidence["content_hash"]
    filename = f"{source_name}_{content_hash}.json"
    filepath = output_path / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2, ensure_ascii=False)

    return str(filepath)


def load_evidence(filepath: str) -> dict[str, Any]:
    """Load a previously saved DocumentEvidence from a JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def summarize_evidence(evidence: dict[str, Any]) -> str:
    """
    Return a human-readable summary of the evidence object.

    Useful for quick inspection and debugging.
    """
    lines = [
        f"Source: {evidence['source_file']}",
        f"Pages: {evidence['page_count']}",
        f"Characters: {evidence['total_chars']}",
        f"Images: {evidence['total_images']}",
        f"OCR pages: {evidence['ocr_pages']}",
        f"Hash: {evidence['content_hash']}",
        f"Ingested: {evidence['ingested_at']}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI: build evidence from a PDF
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m ingestion.evidence_builder <path_to_pdf> [output_dir]")
        print()
        print("Parses the PDF and builds a DocumentEvidence JSON file.")
        print("If output_dir is not given, saves to ./data/evidence/")
        sys.exit(1)

    from ingestion.parse_pdf import extract_pages
    from ingestion.ocr_fallback import process_pages_with_ocr

    pdf_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "./data/evidence"

    print(f"Parsing: {pdf_file}")
    pages = extract_pages(pdf_file)
    print(f"Extracted {len(pages)} pages")

    print("Checking for scanned pages...")
    pages = process_pages_with_ocr(pdf_file, pages)

    print("Building evidence...")
    evidence = build_evidence(pdf_file, pages)

    print()
    print(summarize_evidence(evidence))
    print()

    saved_path = save_evidence(evidence, output_dir)
    print(f"Saved to: {saved_path}")
