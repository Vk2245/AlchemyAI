"""
OCR fallback for scanned or image-heavy PDF pages.

When parse_pdf detects a page with very little text (likely scanned),
this module sends the page image to a vision-capable model for OCR.
Uses local Ollama vision models by default.
"""

import sys
from typing import Any, Optional

import pymupdf

from config.llm_client import get_completion


# Minimum character count to consider a page "text-rich" enough to skip OCR
MIN_TEXT_CHARS: int = 50


def needs_ocr(page_data: dict[str, Any]) -> bool:
    """
    Determine whether a page needs OCR based on its text content.

    A page needs OCR if it has very few characters but contains images,
    which suggests it is a scanned document page.
    """
    has_little_text = page_data["char_count"] < MIN_TEXT_CHARS
    has_images = page_data["has_images"]
    return has_little_text and has_images


def ocr_page_from_pdf(
    pdf_path: str,
    page_number: int,
    provider: str = "local",
) -> str:
    """
    Perform OCR on a single page by rendering it to an image and
    sending it to a vision-capable LLM.

    page_number is 1-indexed to match the evidence_builder convention.
    Returns the extracted text as a string.
    """
    doc = pymupdf.open(str(pdf_path))
    page = doc[page_number - 1]

    # Render page to a high-res PNG in memory
    pix = page.get_pixmap(dpi=300)
    image_bytes = pix.tobytes("png")
    doc.close()

    return ocr_image_bytes(image_bytes, provider=provider)


def ocr_image_bytes(
    image_bytes: bytes,
    provider: str = "local",
) -> str:
    """
    Send raw image bytes to a vision model and extract all visible text.

    The prompt instructs the model to return only the text content,
    preserving structure (tables, lists, headings) as much as possible.
    """
    import base64

    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    prompt = (
        "Extract ALL text visible in this image. "
        "Preserve the document structure: headings, tables, lists, paragraphs. "
        "For tables, format them as markdown tables. "
        "Return only the extracted text, nothing else."
    )

    # For vision models, we need to construct the message with image content
    # litellm supports vision via the standard OpenAI image_url format
    import litellm
    from config.llm_client import _get_model_string, _build_kwargs

    model = _get_model_string(provider)
    kwargs = _build_kwargs(provider)

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_b64}",
                    },
                },
            ],
        }
    ]

    response = litellm.completion(
        model=model,
        messages=messages,
        temperature=0.1,
        max_tokens=4096,
        **kwargs,
    )

    return response.choices[0].message.content


from config.settings import VISION_PROVIDER

def process_pages_with_ocr(
    pdf_path: str,
    pages: list[dict[str, Any]],
    provider: str = VISION_PROVIDER,
) -> list[dict[str, Any]]:
    """
    Check each page and apply OCR where needed. Updates the page dicts
    in place, adding an 'ocr_text' field and updating 'raw_text' for
    pages that needed OCR.

    If OCR fails on the first attempt (e.g., no vision model available),
    skips remaining pages to avoid blocking the pipeline.

    Returns the same list of page dicts, modified.
    """
    ocr_available = True  # Assume available until first failure

    for page in pages:
        if needs_ocr(page):
            if not ocr_available:
                # OCR already failed once, skip remaining pages
                page["ocr_applied"] = False
                page["ocr_error"] = "OCR skipped (vision model unavailable)"
                continue

            print(f"  Page {page['page_number']}: low text ({page['char_count']} chars), running OCR...")
            try:
                ocr_text = ocr_page_from_pdf(
                    pdf_path,
                    page["page_number"],
                    provider=provider,
                )
                page["ocr_text"] = ocr_text
                page["raw_text"] = ocr_text
                page["char_count"] = len(ocr_text)
                page["ocr_applied"] = True
            except Exception as e:
                print(f"  OCR failed for page {page['page_number']}: {e}")
                print(f"  Skipping OCR for remaining pages (vision model likely unavailable)")
                page["ocr_applied"] = False
                page["ocr_error"] = str(e)
                ocr_available = False  # Don't retry on remaining pages
        else:
            page["ocr_applied"] = False

    return pages


# ---------------------------------------------------------------------------
# CLI: test OCR on a specific page
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m ingestion.ocr_fallback <path_to_pdf> [page_number]")
        print()
        print("Tests OCR on the specified page (default: page 1).")
        print("The page is rendered to an image and sent to the local vision model.")
        sys.exit(1)

    pdf_file = sys.argv[1]
    page_num = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    print(f"Running OCR on page {page_num} of {pdf_file}...")
    text = ocr_page_from_pdf(pdf_file, page_num)
    print()
    print("--- OCR Result ---")
    print(text)
