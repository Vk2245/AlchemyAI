"""
FILE: ocr_engine.py
PURPOSE: Handles OCR text extraction from images/PDFs using a resilient fallback chain (OCR.Space -> Groq Vision/HF -> OpenRouter -> Gemini).
USED BY: document_processor.py
USES: config.py
"""

# ──────────────────────────────────────────────
# IMPORTS
# ──────────────────────────────────────────────
import os
import json
import base64
import requests
from io import BytesIO

# Import from our own project files
# We will import API keys from config once it's set up
# from config import OCR_SPACE_API_KEY, GROQ_API_KEY, GEMINI_API_KEY, OPENROUTER_API_KEY

# ──────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────
# Replace these with your actual keys later via .env / config
OCR_SPACE_API_KEY = os.environ.get("OCR_SPACE_API_KEY", "helloworld")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# ──────────────────────────────────────────────
# MAIN FUNCTIONS
# ──────────────────────────────────────────────

def encode_image_to_base64(image_path: str) -> str:
    """Reads an image file and converts it to a base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def _run_ocr_space(image_path: str) -> str:
    """
    Attempts to extract text using the free OCR.Space API.
    
    Args:
        image_path: Absolute path to the image file
        
    Returns:
        Extracted text string
    """
    print("[OCR] Trying OCR.Space...")
    url = "https://api.ocr.space/parse/image"
    
    with open(image_path, "rb") as f:
        payload = {
            "apikey": OCR_SPACE_API_KEY,
            "language": "eng",
            "isOverlayRequired": "false"
        }
        files = {"file": f}
        response = requests.post(url, files=files, data=payload, timeout=30)
        
    if response.status_code == 200:
        result = response.json()
        if not result.get("IsErroredOnProcessing"):
            parsed_results = result.get("ParsedResults", [])
            if parsed_results:
                return parsed_results[0].get("ParsedText", "")
    
    raise Exception(f"OCR.Space failed. Status Code: {response.status_code}, Response: {response.text}")


def _run_groq_vision(image_path: str) -> str:
    """
    Attempts to extract text using Groq's Llama-3.2-11b-vision model.
    """
    print("[OCR] Trying Groq Vision API...")
    url = "https://api.groq.com/openai/v1/chat/completions"
    base64_image = encode_image_to_base64(image_path)
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.2-11b-vision-preview",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Extract all the text from this image exactly as it appears. Do not add any extra commentary, just the raw text."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        "temperature": 0.1
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
        
    raise Exception(f"Groq Vision failed. Status Code: {response.status_code}")


def _run_openrouter_vision(image_path: str) -> str:
    """
    Attempts to extract text using OpenRouter (e.g., free tier vision models).
    """
    print("[OCR] Trying OpenRouter Vision API...")
    url = "https://openrouter.ai/api/v1/chat/completions"
    base64_image = encode_image_to_base64(image_path)
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "mistralai/pixtral-12b", # Can be changed to any free vision model on OpenRouter
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Extract all the text from this document."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ]
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
        
    raise Exception(f"OpenRouter Vision failed. Status Code: {response.status_code}")


def _run_gemini_ocr(image_path: str) -> str:
    """
    Attempts to extract text using Gemini 1.5 Flash via native API.
    """
    print("[OCR] Trying Gemini 1.5 Flash...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    base64_image = encode_image_to_base64(image_path)
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": "Extract all text from this image."},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": base64_image
                        }
                    }
                ]
            }
        ]
    }
    
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    
    if response.status_code == 200:
        result = response.json()
        try:
            return result["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            raise Exception("Gemini returned an unexpected response format.")
            
    raise Exception(f"Gemini Vision failed. Status Code: {response.status_code}")


def extract_text_from_image(image_path: str) -> dict:
    """
    Orchestrates the OCR fallback chain.
    
    What it does:
        - Tries OCR.Space first
        - Falls back to Groq Vision
        - Falls back to OpenRouter
        - Falls back to Gemini 1.5 Flash
        
    Args:
        image_path: The file path to the image/document.
        
    Returns:
        A dictionary containing the extracted text and the source provider.
    """
    
    if not os.path.exists(image_path):
        return {"text": "", "source": "error", "error": "File not found"}

    # --- Step 1: OCR.Space ---
    try:
        text = _run_ocr_space(image_path)
        if text.strip():
            return {"text": text, "source": "ocr_space"}
    except Exception as e:
        print(f"[Fallback Triggered] {e}")

    # --- Step 2: Groq Vision / HF ---
    try:
        text = _run_groq_vision(image_path)
        if text.strip():
            return {"text": text, "source": "groq_vision"}
    except Exception as e:
        print(f"[Fallback Triggered] {e}")

    # --- Step 3: Gemini 1.5 Flash (Last Resort) ---
    try:
        text = _run_gemini_ocr(image_path)
        if text.strip():
            return {"text": text, "source": "gemini"}
    except Exception as e:
        print(f"[Fallback Triggered] {e}")

    return {"text": "", "source": "none", "error": "All OCR providers failed"}
