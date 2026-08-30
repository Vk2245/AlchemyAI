"""
PDF text and table extraction using PyMuPDF.

Takes a PDF file path, returns a list of page-level evidence dicts
containing raw text, markdown-formatted content, and table data.
This is the first step in the ingestion pipeline.
"""

import sys
from pathlib import Path
from typing import Any

import pymupdf
import pymupdf4llm


def extract_pages(pdf_path: str) -> list[dict[str, Any]]:
    """
    Extract text and structural content from every page of a PDF.

    Returns a list of dicts, one per page, each containing:
      - page_number: 1-indexed page number
      - raw_text: plain text extracted by PyMuPDF
      - markdown: markdown-formatted text from pymupdf4llm (preserves tables)
      - char_count: number of characters on the page
      - has_images: whether the page contains embedded images
      - image_refs: list of image metadata dicts (xref, size, etc.)
    """
    pdf_path = str(pdf_path)
    doc = pymupdf.open(pdf_path)
    pages: list[dict[str, Any]] = []

    # Get markdown for all pages at once (pymupdf4llm works on full doc)
    try:
        full_markdown = pymupdf4llm.to_markdown(pdf_path)
    except Exception:
        full_markdown = ""
    # Split markdown by page breaks (pymupdf4llm inserts form-feed or page markers)
    md_pages = _split_markdown_pages(full_markdown, len(doc))

    for page_num in range(len(doc)):
        page = doc[page_num]
        raw_text = page.get_text("text")
        md_text = md_pages[page_num] if page_num < len(md_pages) else ""

        # Use markdown text as fallback if raw text is empty
        # (pymupdf4llm sometimes extracts text from scanned PDFs via built-in OCR)
        effective_text = raw_text if raw_text.strip() else md_text

        # Collect image references from the page
        image_list = page.get_images(full=True)
        image_refs = []
        for img in image_list:
            image_refs.append({
                "xref": img[0],
                "width": img[2],
                "height": img[3],
                "colorspace": img[5],
            })

        page_data = {
            "page_number": page_num + 1,
            "raw_text": effective_text,
            "markdown": md_text or raw_text,
            "char_count": len(effective_text.strip()),
            "has_images": len(image_list) > 0,
            "image_refs": image_refs,
        }
        pages.append(page_data)

    doc.close()
    return pages


def _split_markdown_pages(full_markdown: str, expected_pages: int) -> list[str]:
    """
    Split pymupdf4llm's full-document markdown into per-page chunks.

    pymupdf4llm uses '---' or page break markers between pages. If splitting
    does not produce the expected count, fall back to returning the full
    text as a single page.
    """
    # pymupdf4llm typically uses horizontal rules or form feeds as page separators
    separators = ["\n---\n", "\n\n---\n\n", "\f"]

    for sep in separators:
        parts = full_markdown.split(sep)
        if len(parts) >= expected_pages:
            return parts[:expected_pages]

    # Fallback: return full text as one block repeated
    return [full_markdown] * expected_pages


def extract_text_only(pdf_path: str) -> str:
    """
    Extract all text from a PDF as a single string.

    Use this for quick previews or when page-level detail is not needed.
    """
    pages = extract_pages(pdf_path)
    return "\n\n".join(p["raw_text"] for p in pages)


def get_page_count(pdf_path: str) -> int:
    """Return the number of pages in a PDF."""
    doc = pymupdf.open(str(pdf_path))
    count = len(doc)
    doc.close()
    return count


def extract_images(pdf_path: str, output_dir: str) -> list[dict[str, Any]]:
    """
    Extract all embedded images from a PDF and save them to output_dir.

    Returns a list of dicts with image metadata and saved file paths.
    Used by the visual_match module (bonus stage) for image embedding.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    doc = pymupdf.open(str(pdf_path))
    extracted: list[dict[str, Any]] = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        image_list = page.get_images(full=True)

        for img_idx, img in enumerate(image_list):
            xref = img[0]
            base_image = doc.extract_image(xref)
            if base_image is None:
                continue

            image_bytes = base_image["image"]
            image_ext = base_image.get("ext", "png")
            filename = f"page{page_num + 1}_img{img_idx + 1}.{image_ext}"
            filepath = output_path / filename

            with open(filepath, "wb") as f:
                f.write(image_bytes)

            extracted.append({
                "page_number": page_num + 1,
                "image_index": img_idx + 1,
                "filepath": str(filepath),
                "width": base_image.get("width", 0),
                "height": base_image.get("height", 0),
                "colorspace": base_image.get("colorspace", ""),
                "size_bytes": len(image_bytes),
            })

    doc.close()
    return extracted


# ---------------------------------------------------------------------------
# CLI: run on a sample PDF to verify extraction
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m ingestion.parse_pdf <path_to_pdf>")
        print()
        print("Drop sample PDFs into:")
        print("  tests/sample_pdfs/electrical/")
        print("  tests/sample_pdfs/software/")
        sys.exit(1)

    pdf_file = sys.argv[1]
    print(f"Parsing: {pdf_file}")
    print(f"Pages: {get_page_count(pdf_file)}")
    print()

    pages = extract_pages(pdf_file)
    for page in pages:
        print(f"--- Page {page['page_number']} ---")
        print(f"Chars: {page['char_count']}")
        print(f"Images: {len(page['image_refs'])}")
        # Print first 500 chars of text
        preview = page["raw_text"][:500]
        print(preview)
        print()
