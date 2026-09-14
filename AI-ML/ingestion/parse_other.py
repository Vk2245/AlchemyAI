"""
Helper parsers for TXT and DOCX formats.
Bypasses PyMuPDF to extract text directly.
"""

import os

try:
    import docx
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


def extract_txt_pages(file_path: str) -> list[dict]:
    """Reads a .txt file and returns it as a single logical page."""
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    
    return [
        {
            "page_number": 1,
            "raw_text": text,
            "char_count": len(text),
            "has_images": False,
            "ocr_applied": False,
            "fraud_flags": []
        }
    ]


def extract_docx_pages(file_path: str) -> list[dict]:
    """Reads a .docx file and returns it as a single logical page."""
    if not HAS_DOCX:
        raise ImportError("python-docx is not installed. Run: pip install python-docx")
    
    doc = docx.Document(file_path)
    text = "\n".join(paragraph.text for paragraph in doc.paragraphs)
    
    return [
        {
            "page_number": 1,
            "raw_text": text,
            "char_count": len(text),
            "has_images": False,
            "ocr_applied": False,
            "fraud_flags": []
        }
    ]
