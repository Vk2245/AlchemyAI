"""
FILE: document_processor.py
PURPOSE: Dynamically extracts Named Entities (NER) from OCR text without hardcoded JSON schemas.
USED BY: backend API routes (e.g., upload.py)
USES: ocr_engine.py, litellm
"""

# ──────────────────────────────────────────────
# IMPORTS
# ──────────────────────────────────────────────
import json
import os
from litellm import completion
from .ocr_engine import extract_text_from_image

# ──────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────
# In a real app, these would come from config.py or environment variables
DEFAULT_BRAIN_MODEL = "gemini/gemini-2.5-flash"

# ──────────────────────────────────────────────
# MAIN FUNCTIONS
# ──────────────────────────────────────────────

def _repair_json(raw: str) -> dict:
    """
    Best-effort JSON repair for common LLM output issues.
    """
    text = raw.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
        
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError as e:
        print(f"JSON Parsing failed: {e}. Raw text was: {text}")
        return {}


def infer_schema(document_text: str) -> dict:
    """
    Dynamically generates a JSON Schema based on the document type.
    
    What it does:
        - Reads the document text
        - Determines if it's an Invoice, Contract, Receipt, etc.
        - Generates a list of essential fields to extract
        
    Args:
        document_text: The raw text extracted from OCR.
        
    Returns:
        A dictionary containing the document type and the dynamic schema.
    """
    prompt = f"""
    You are an expert Document Intelligence AI. Read the following OCR text and determine what kind of document it is (e.g., Invoice, Contract, Receipt).
    Then, define a JSON schema of the most important fields that should be extracted from it.
    
    Return ONLY a valid JSON object in this exact format:
    {{
        "document_type": "Invoice",
        "schema": ["Vendor Name", "Total Amount", "Invoice Date", "Tax Amount", "Line Items"]
    }}
    
    Document Text:
    {document_text[:4000]}  # Limiting length just for schema inference
    """
    
    try:
        response = completion(
            model=DEFAULT_BRAIN_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        raw_output = response.choices[0].message.content
        return _repair_json(raw_output)
    except Exception as e:
        print(f"Schema Inference failed: {e}")
        return {"document_type": "Unknown", "schema": []}


def extract_entities(document_text: str, dynamic_schema: list) -> dict:
    """
    Extracts actual data values based on the dynamically generated schema.
    
    What it does:
        - Uses the LLM to map the raw text into the requested schema fields.
        
    Args:
        document_text: Raw OCR text.
        dynamic_schema: List of fields to extract (e.g. ["Total Amount", "Date"]).
        
    Returns:
        A dictionary with the extracted data.
    """
    if not dynamic_schema:
        return {}
        
    schema_str = ", ".join([f'"{field}": "string or number"' for field in dynamic_schema])
    
    prompt = f"""
    Extract the following fields from the document text: {dynamic_schema}.
    
    Return ONLY a valid JSON object in this exact format:
    {{
        {schema_str}
    }}
    
    Document Text:
    {document_text}
    """
    
    try:
        response = completion(
            model=DEFAULT_BRAIN_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        raw_output = response.choices[0].message.content
        return _repair_json(raw_output)
    except Exception as e:
        print(f"Entity Extraction failed: {e}")
        return {}


def process_document(file_path: str) -> dict:
    """
    Orchestrates the entire Document Intelligence pipeline.
    
    What it does:
        1. Runs OCR fallback chain to get raw text.
        2. Infers the document type and required schema.
        3. Extracts the actual entities using the schema.
        
    Args:
        file_path: Absolute path to the uploaded document image/pdf.
        
    Returns:
        A complete dictionary with OCR text, type, schema, and extracted data.
    """
    print(f"Processing document: {file_path}")
    
    # Step 1: Ingestion & OCR
    ocr_result = extract_text_from_image(file_path)
    raw_text = ocr_result.get("text", "")
    ocr_source = ocr_result.get("source", "unknown")
    
    if not raw_text:
        return {"status": "error", "message": "Failed to extract text from document."}
        
    print(f"OCR successful (Source: {ocr_source}). Inferring schema...")
    
    # Step 2: Infer Schema
    schema_info = infer_schema(raw_text)
    doc_type = schema_info.get("document_type", "Unknown")
    schema_fields = schema_info.get("schema", [])
    
    print(f"Document Type: {doc_type}. Extracting entities...")
    
    # Step 3: Extract Entities
    extracted_data = extract_entities(raw_text, schema_fields)
    
    return {
        "status": "success",
        "ocr_source": ocr_source,
        "document_type": doc_type,
        "schema_used": schema_fields,
        "extracted_data": extracted_data,
        "raw_text": raw_text  # Keeping it for potential Chatbot context
    }
