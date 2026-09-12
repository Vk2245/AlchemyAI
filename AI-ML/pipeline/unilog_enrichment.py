import polars as pl
import json
import re
import os
from pathlib import Path
from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BASE_DIR / "dataset"
OUTPUT_FILE = DATASET_DIR / "Delivery_Format_1000.xlsx"

from config.llm_client import get_completion, _get_model_string, _build_kwargs
from config.settings import DEFAULT_PROVIDER

MODEL_NAME = _get_model_string(DEFAULT_PROVIDER)


def _repair_json(raw: str) -> dict:
    """
    Best-effort JSON repair for common LLM output issues:
    1. Strip markdown fences (```json ... ```)
    2. Fix unescaped double quotes inside string values (e.g. 14"x1" -> 14\\"x1\\")
    3. Remove trailing commas before } or ]
    """
    text = raw.strip()
    
    # Strip markdown fences
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    # First attempt: try parsing as-is
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Second attempt: fix unescaped quotes inside string values
    # Strategy: find all string values and escape internal quotes
    # Match pattern: after a colon and optional whitespace, a quoted string value
    def fix_value_quotes(m):
        prefix = m.group(1)  # the ": or ", part
        content = m.group(2)
        # Escape any unescaped double quotes inside the value
        # But don't double-escape already escaped ones
        fixed = content.replace('\\"', '\x00').replace('"', '\\"').replace('\x00', '\\"')
        return f'{prefix}"{fixed}"'
    
    # Try a simpler approach: replace inch marks (") that appear inside values with escaped versions
    # Common pattern: digits followed by " (inch mark) followed by non-comma, non-brace chars
    repaired = re.sub(r'(\d)"(\s*x|\s*X)', r'\1\\"\2', text)  # 14"x -> 14\"x
    repaired = re.sub(r'(\d)"(\s*-)', r'\1\\"\2', repaired)    # 5" - -> 5\" -
    repaired = re.sub(r'(\d)"(\s*[A-Za-z])', r'\1\\"\2', repaired)  # 5" P -> 5\" P
    repaired = re.sub(r'(\d)"(\s*,)', r'\1\\"\2', repaired)    # 5", -> 5\",
    repaired = re.sub(r'(\d)"(\s*})', r'\1\\"\2', repaired)    # 5"} -> 5\"}
    
    # Remove trailing commas before } or ]
    repaired = re.sub(r',\s*([}\]])', r'\1', repaired)
    
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass
    
    # Third attempt: try to extract just the JSON object using regex
    json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
    if json_match:
        try:
            candidate = json_match.group(0)
            # Apply same inch-mark fixes
            candidate = re.sub(r'(\d)"(\s*x|\s*X)', r'\1\\"\2', candidate)
            candidate = re.sub(r'(\d)"(\s*-)', r'\1\\"\2', candidate)
            candidate = re.sub(r'(\d)"(\s*[A-Za-z])', r'\1\\"\2', candidate)
            candidate = re.sub(r'(\d)"(\s*,)', r'\1\\"\2', candidate)
            candidate = re.sub(r'(\d)"(\s*})', r'\1\\"\2', candidate)
            candidate = re.sub(r',\s*([}\]])', r'\1', candidate)
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    
    # All attempts failed
    raise json.JSONDecodeError("Could not repair JSON", text, 0)


def process_unilog_catalogue(input_file: str):
    """
    Generator function that processes an Excel file row by row using the local vLLM server.
    Yields dicts with {"progress": int, "message": str, "data": dict (optional)}
    """
    path = Path(input_file)
    if not path.exists():
        yield {"progress": -1, "message": f"Input file not found: {input_file}"}
        return
        
    yield {"progress": 5, "message": "Loading Excel file..."}
    try:
        if path.suffix.lower() == '.csv':
            df = pl.read_csv(path)
        else:
            df = pl.read_excel(path, engine="openpyxl")
    except Exception as e:
        yield {"progress": -1, "message": f"Failed to read Excel: {e}"}
        return

    total_items = len(df)
    
    # ---------------------------------------------------------
    # Processing 15 items for demonstration to avoid API Rate Limits (429)
    # on free Groq/Gemini tiers, which only allow 15 RPM.
    # ---------------------------------------------------------
    df = df.head(15)
    
    yield {"progress": 10, "message": f"Loaded {total_items} items (Demo mode: processing top 15 to respect 15 RPM Free API limits). Starting REAL LLM enrichment..."}
    
    results = []
    import concurrent.futures
    import time
    from pydantic import BaseModel
    from config.llm_client import get_structured_output
    
    # Reduced workers to avoid hammering free tier APIs
    MAX_WORKERS = 2
    MAX_RETRIES = 2
    
    # Filter valid rows first
    valid_rows = []
    desc_col = None
    for col in df.columns:
        if "description" in str(col).lower():
            desc_col = col
            break
            
    if not desc_col:
        for col in ["Part_Desc", "INPUT - Part_Desc", "Item Description", "Raw Description"]:
            if col in df.columns:
                desc_col = col
                break
                
    if not desc_col:
        yield {"progress": -1, "message": f"Error: Could not find a description column in the uploaded Excel file. Columns found: {list(df.columns)[:5]}"}
        return
        
    for idx, row in enumerate(df.iter_rows(named=True)):
        raw_desc = row.get(desc_col, "")
        if raw_desc is None or not str(raw_desc).strip():
            continue
        valid_rows.append((idx, str(raw_desc).strip()))
        
    total_valid = len(valid_rows)
    
    class ExcelRowResult(BaseModel):
        Category: str
        Description: str
        Material: str
        Size: str
        Confidence: float
    
    def process_single_item(item):
        idx, raw_desc = item
        
        # -------------------------------------------------------------
        # Call the ACTUAL LLM to structure this row
        # -------------------------------------------------------------
        prompt = f"Extract structured product attributes from this messy catalog description:\n\n{raw_desc}"
        system = "You are an industrial data extraction assistant. Categorize the item, clean up the description, and extract Material and Size if present. Output valid JSON."
        
        try:
            # We use 'gemini' as provider for stable excel processing if default is slow
            res = get_structured_output(
                prompt=prompt,
                response_model=ExcelRowResult,
                system_prompt=system,
                provider="gemini",
                temperature=0.1
            )
            
            result_row = {
                "Item_ID": f"PROD_{idx:04d}",
                "INPUT - Part_Desc": raw_desc,
                "Category": res.Category,
                "Description": res.Description,
                "Material": res.Material,
                "Size": res.Size,
                "Confidence": res.Confidence
            }
            return result_row
            
        except Exception as e:
            # Fallback if API fails for this specific row
            return {
                "Item_ID": f"PROD_{idx:04d}",
                "INPUT - Part_Desc": raw_desc,
                "Category": "Failed",
                "Description": f"Failed to extract: {str(e)[:50]}",
                "Material": "N/A",
                "Size": "N/A",
                "Confidence": 0.0
            }

    results = []
    processed_count = 0
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        future_to_item = {executor.submit(process_single_item, item): item for item in valid_rows}
        
        for future in concurrent.futures.as_completed(future_to_item):
            processed_count += 1
            result = future.result()
            results.append(result)
            
            # Yield progress every 5 items to avoid flooding the frontend SSE queue
            if processed_count % 5 == 0 or processed_count == total_valid:
                progress_pct = 10 + int(80 * (processed_count / total_valid))
                # Get the description of the latest processed item for the status message
                latest_desc = result.get("INPUT - Part_Desc", "")[:30]
                yield {"progress": progress_pct, "message": f"Processing item {processed_count}/{total_valid}: {latest_desc}..."}

    # Compute statistics
    success_count = sum(1 for r in results if r.get("Category", "Failed") != "Failed")
    fail_count = len(results) - success_count
    
    yield {"progress": 95, "message": f"Enrichment complete. {success_count} succeeded, {fail_count} failed. Grouping categories..."}
    
    # Save the raw results to a new CSV file for the Project requirement
    output_path = path.parent / f"Enriched_{path.stem}.csv"
    final_df = pl.DataFrame(results)
    final_df.write_csv(output_path)
    
    # Group results by Category for the PDF generation
    grouped_data = {}
    for r in results:
        cat = r.get("Category", "Uncategorized")
        if cat not in grouped_data:
            grouped_data[cat] = []
        grouped_data[cat].append(r)

    # Build statistics for the dashboard
    category_stats = {}
    for cat, items in grouped_data.items():
        category_stats[cat] = len(items)
        
    yield {
        "progress": 100, 
        "message": f"Successfully processed {len(results)} items ({success_count} enriched, {fail_count} failed).", 
        "data": {
            "excel_path": str(output_path),
            "grouped_data": grouped_data,
            "stats": {
                "total": len(results),
                "success": success_count,
                "failed": fail_count,
                "success_rate": round(success_count / max(len(results), 1) * 100, 1),
                "category_distribution": category_stats,
            }
        }
    }

if __name__ == "__main__":
    # Test CLI mode
    test_file = DATASET_DIR / "Alchemy AI_ Sample Dataset - Input.csv"
    for update in process_unilog_catalogue(test_file):
        print(update)
