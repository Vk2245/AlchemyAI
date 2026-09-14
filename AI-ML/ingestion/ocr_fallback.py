"""
OCR fallback chain for scanned or image-heavy pages and direct images.

Implements a 2-Tier fallback:
1. OCR.space API (Standard OCR, Fast, Free)
2. Gemini Vision (Deep Reasoning, with Dual-Key Rotation)
"""

import os
import json
import base64
import time
import concurrent.futures
from typing import Any
import itertools

import pymupdf
import requests
import litellm

from config.settings import GEMINI_MODEL, GEMINI_API_KEYS


class OCRFallbackChain:
    """Handles the 2-tier OCR escalation process."""

    def __init__(self):
        ocr_keys = os.getenv("OCR_SPACE_API_KEYS", os.getenv("OCR_SPACE_API_KEY", "K86348633988957"))
        self.ocr_space_key_cycle = itertools.cycle([k.strip() for k in ocr_keys.split(",") if k.strip()])
        self.gemini_key_cycle = itertools.cycle(GEMINI_API_KEYS) if GEMINI_API_KEYS else None

    def process_image(self, image_bytes: bytes, execution_mode: str = "online") -> dict[str, Any]:
        """
        Runs the image through the fallback chain.
        Returns a dict with 'text'.
        """
        if execution_mode == "online":
            try:
                print("  [OCR Tier 1] Attempting OCR.space...")
                res = requests.post(
                    "https://api.ocr.space/parse/image",
                    files={"file": ("image.jpg", image_bytes, "image/jpeg")},
                    data={
                        "apikey": next(self.ocr_space_key_cycle),
                        "language": "eng",
                        "filetype": "jpg",
                    },
                    timeout=25
                )
                if res.status_code == 200:
                    data = res.json()
                    if not data.get("IsErroredOnProcessing"):
                        text = "\n".join(r["ParsedText"] for r in data.get("ParsedResults", []))
                        if len(text.strip()) > 50:
                            return {"text": text, "tier": "ocr_space"}
            except Exception as e:
                print(f"  [OCR Tier 1] OCR.space failed: {e}")

        # Tier 2: Gemini Vision
        print("  [OCR Tier 2] Escalating to Gemini Vision...")
        return self._vision_llm_extraction(image_bytes)

    def _vision_llm_extraction(self, image_bytes: bytes) -> dict[str, Any]:
        """Uses Gemini Vision to extract text."""
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        prompt = "Extract ALL text visible in this document image. Preserve the document structure: headings, tables, lists. Return only the extracted text."

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                ],
            }
        ]

        if not self.gemini_key_cycle:
            print("  [OCR Tier 2] No Gemini keys available.")
            return {"text": "", "tier": "failed"}

        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Rotate key
                current_key = next(self.gemini_key_cycle)
                print(f"  [OCR Tier 2] Trying Gemini Vision (attempt {attempt + 1}/{max_retries})...")
                
                response = litellm.completion(
                    model=GEMINI_MODEL,
                    messages=messages,
                    temperature=0.1,
                    api_key=current_key,
                )
                content = response.choices[0].message.content
                return {"text": content, "tier": "gemini_vision"}
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "RateLimitError" in error_str:
                    wait_time = 5 * (attempt + 1)  # Reduced waits: 5s, 10s, 15s
                    print(f"  [OCR Tier 2] Rate limited. Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
                print(f"  [OCR Tier 2] Gemini Vision failed: {e}")
                break

        return {"text": "", "tier": "failed"}


def needs_ocr(page_data: dict[str, Any]) -> bool:
    return page_data.get("char_count", 0) < 50 and page_data.get("has_images", True)


def _process_single_page(page: dict[str, Any], doc_path: str, execution_mode: str, chain: OCRFallbackChain) -> dict[str, Any]:
    """Worker function for ThreadPoolExecutor to process a single page."""
    try:
        if str(doc_path).lower().endswith(('.png', '.jpg', '.jpeg')):
            # Direct image file
            with open(doc_path, "rb") as f:
                image_bytes = f.read()
        else:
            # PDF page extraction
            doc = pymupdf.open(str(doc_path))
            pdf_page = doc[page["page_number"] - 1]
            # Compress using 150 DPI and JPEG to stay under OCR.space 1MB limit
            pix = pdf_page.get_pixmap(dpi=150)
            image_bytes = pix.tobytes("jpeg")
            doc.close()

        result = chain.process_image(image_bytes, execution_mode=execution_mode)
        
        ocr_text = result["text"]
        page["ocr_text"] = ocr_text
        page["raw_text"] = ocr_text if ocr_text else page.get("raw_text", "")
        page["char_count"] = len(ocr_text)
        page["ocr_applied"] = True
        page["ocr_tier"] = result["tier"]
    except Exception as e:
        print(f"  [ERROR] OCR failed for page {page.get('page_number', 1)}: {e}")
        page["ocr_applied"] = False
        
    return page


def process_pages_with_ocr(
    doc_path: str,
    pages: list[dict[str, Any]],
    execution_mode: str = "online",
    status_callback=None
) -> list[dict[str, Any]]:
    
    chain = OCRFallbackChain()
    
    # Filter pages needing OCR
    pages_to_ocr = [page for page in pages if needs_ocr(page)]
    
    if not pages_to_ocr:
        return pages

    msg = f"Running PARALLEL OCR on {len(pages_to_ocr)} pages..."
    print(f"  {msg}")
    if status_callback:
        status_callback(25, msg)

    # Use ThreadPoolExecutor to run OCR calls in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(_process_single_page, page, doc_path, execution_mode, chain): page
            for page in pages_to_ocr
        }
        
        processed_count = 0
        for future in concurrent.futures.as_completed(futures):
            processed_count += 1
            if status_callback:
                progress = 25 + int(10 * (processed_count / len(pages_to_ocr)))
                status_callback(progress, f"OCR completed for {processed_count}/{len(pages_to_ocr)} pages...")
    
    # Non-OCR pages are untouched, OCR pages are updated in place
    return pages
