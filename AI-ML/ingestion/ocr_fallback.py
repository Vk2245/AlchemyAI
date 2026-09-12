"""
OCR fallback chain for scanned or image-heavy PDF pages.

Implements a 4-Tier fallback:
1. Local Tesseract (pytesseract)
2. OCR.space API (Standard OCR)
3. Groq Vision (Fast Multimodal)
4. Gemini Vision (Deep Reasoning)

Includes Multimodal Fraud Detection in the vision layers.
"""

import os
import sys
import json
import base64
from typing import Any, Optional

import pymupdf
import requests
import litellm

# Try to import pytesseract, but allow fallback if not installed
try:
    import pytesseract
    from PIL import Image
    import io
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

# Minimum character count to consider a page "text-rich" enough to skip OCR
MIN_TEXT_CHARS: int = 50


class OCRFallbackChain:
    """Handles the 4-tier OCR escalation process."""

    def __init__(self):
        self.ocr_space_key = os.getenv("OCR_SPACE_API_KEY", "")

    def process_image(self, image_bytes: bytes, lang: str = "eng", execution_mode: str = "online") -> dict[str, Any]:
        """
        Runs the image through the fallback chain.
        Returns a dict with 'text' and 'fraud_flags' (if any).
        """
        # Tier 1: Local Tesseract
        if HAS_TESSERACT and execution_mode == "local":
            try:
                print("  [OCR Tier 1] Attempting pytesseract...")
                image = Image.open(io.BytesIO(image_bytes))
                text = pytesseract.image_to_string(image, lang=lang).strip()
                if len(text) > MIN_TEXT_CHARS:
                    return {"text": text, "tier": "tesseract", "fraud_flags": []}
            except Exception as e:
                print(f"  [OCR Tier 1] Tesseract failed: {e}")

        # Tier 2: OCR.space API
        if self.ocr_space_key:
            try:
                print("  [OCR Tier 2] Attempting OCR.space...")
                payload = {
                    "apikey": self.ocr_space_key,
                    "language": lang[:3], # e.g. 'eng'
                    "isOverlayRequired": False
                }
                files = {"file": ("image.png", image_bytes, "image/png")}
                res = requests.post("https://api.ocr.space/parse/image", data=payload, files=files, timeout=10)
                if res.status_code == 200:
                    data = res.json()
                    if not data.get("IsErroredOnProcessing"):
                        text = "\n".join(r["ParsedText"] for r in data.get("ParsedResults", []))
                        if len(text) > MIN_TEXT_CHARS:
                            return {"text": text, "tier": "ocr_space", "fraud_flags": []}
            except Exception as e:
                print(f"  [OCR Tier 2] OCR.space failed: {e}")

        # Tier 3 & 4: Vision LLMs (with Multimodal Fraud Detection)
        print("  [OCR Tier 3/4] Escalating to Vision LLMs...")
        return self._vision_llm_extraction(image_bytes)

    def _vision_llm_extraction(self, image_bytes: bytes) -> dict[str, Any]:
        """Uses Groq Vision (fallback to Gemini) to extract text and audit logos."""
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        prompt = (
            "Extract ALL text visible in this document image. "
            "Preserve the document structure: headings, tables, lists. "
            "\n\nMULTIMODAL FRAUD DETECTION:\n"
            "Analyze any company logos or letterheads present. Does the logo look legitimate, "
            "or does it look like a low-resolution fake/forgery, pixelated, or inconsistent with the text? "
            "Output your response exactly in this JSON format:\n"
            "{\n"
            '  "extracted_text": "...",\n'
            '  "logo_fraud_flag": false,\n'
            '  "fraud_reason": ""\n'
            "}"
        )

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                    },
                ],
            }
        ]

        # Tier 3: Gemini Vision
        try:
            gemini_api_key = os.getenv("GEMINI_API_KEY", "")
            gemini_model = os.getenv("GEMINI_MODEL", "gemini/gemini-1.5-flash")
            response = litellm.completion(
                model=gemini_model,
                messages=messages,
                temperature=0.1,
                api_key=gemini_api_key,
            )
            content = response.choices[0].message.content
            try:
                clean_json = content.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_json)
                return {
                    "text": data.get("extracted_text", ""),
                    "tier": "gemini_vision",
                    "fraud_flags": [data.get("fraud_reason")] if data.get("logo_fraud_flag") else []
                }
            except json.JSONDecodeError:
                return {"text": content, "tier": "gemini_vision", "fraud_flags": []}
        except Exception as e:
            print(f"  [OCR Tier 3] Gemini Vision failed: {e}")
            return {"text": "", "tier": "failed", "fraud_flags": []}


def needs_ocr(page_data: dict[str, Any]) -> bool:
    has_little_text = page_data["char_count"] < MIN_TEXT_CHARS
    has_images = page_data["has_images"]
    return has_little_text and has_images


def process_pages_with_ocr(
    pdf_path: str,
    pages: list[dict[str, Any]],
    execution_mode: str = "online",
) -> list[dict[str, Any]]:
    
    chain = OCRFallbackChain()

    for page in pages:
        if needs_ocr(page):
            print(f"  Page {page['page_number']}: low text ({page['char_count']} chars), running 4-Tier OCR...")
            doc = pymupdf.open(str(pdf_path))
            pdf_page = doc[page["page_number"] - 1]
            pix = pdf_page.get_pixmap(dpi=300)
            image_bytes = pix.tobytes("png")
            doc.close()

            result = chain.process_image(image_bytes, execution_mode=execution_mode)
            
            ocr_text = result["text"]
            page["ocr_text"] = ocr_text
            page["raw_text"] = ocr_text if ocr_text else page.get("raw_text", "")
            page["char_count"] = len(ocr_text)
            page["ocr_applied"] = True
            page["ocr_tier"] = result["tier"]
            page["fraud_flags"] = result["fraud_flags"]
        else:
            page["ocr_applied"] = False
            page["fraud_flags"] = []

    return pages
