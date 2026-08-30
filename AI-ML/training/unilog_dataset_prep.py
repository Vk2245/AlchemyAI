import pandas as pd
import json
import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BASE_DIR / "dataset"
TRAIN_OUTPUT = BASE_DIR / "training" / "unilog_train.jsonl"

def prepare_dataset():
    # In the actual implementation, replace these with the exact paths to the Unilog Excel files.
    # We are using mock/placeholder logic here to demonstrate the exact schema Kaggle expects.
    
    # 1. Load the Ground Truth 200 items (Delivery Format)
    delivery_format_path = DATASET_DIR / "Alchemy AI_ Expected Output - Delivery Format.csv"
    
    print(f"Looking for dataset at: {delivery_format_path}")
    
    # Check if the user has placed the actual dataset yet
    if not delivery_format_path.exists():
        print(f"[WARNING] Dataset not found at {delivery_format_path}.")
        print("Please place the Alchemy AI_ Expected Output - Delivery Format.csv in the AI-ML/dataset folder!")
        print("Generating a dummy JSONL file for demonstration purposes...")
        
        # Mock Data for demonstration
        mock_data = [
            {
                "input_desc": "3/8 CPLG BRS 150#",
                "structured_output": {
                    "Item Type": "Coupling",
                    "Size": "3/8 in",
                    "Material": "Brass",
                    "Pressure Rating": "150 PSI"
                }
            },
            {
                "input_desc": "PDSH4816AF Dishwasher SS - Display Only",
                "structured_output": {
                    "Item Type": "Built-In Dishwasher",
                    "Brand": "Frigidaire",
                    "Material": "Stainless Steel",
                    "Manufacturer Part Number": "PDSH4816AF"
                }
            }
        ]
        
        # Ensure output dir exists
        TRAIN_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        
        with open(TRAIN_OUTPUT, "w", encoding="utf-8") as f:
            for item in mock_data:
                # Format exactly as Qwen2 / Llama chat template expects
                convo = {
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert industrial data extraction assistant. Extract structured product attributes from the messy catalog description. Output ONLY valid JSON."
                        },
                        {
                            "role": "user",
                            "content": f"Extract attributes from this raw description: {item['input_desc']}"
                        },
                        {
                            "role": "assistant",
                            "content": json.dumps(item['structured_output'])
                        }
                    ]
                }
                f.write(json.dumps(convo) + "\n")
        
        print(f"[SUCCESS] Generated demo dataset at: {TRAIN_OUTPUT}")
        print("Upload this file to Kaggle for training.")
        return

    # 2. If the actual file exists, parse it
    try:
        df = pd.read_csv(delivery_format_path)
        print(f"Loaded {len(df)} rows from Ground Truth dataset.")
        
        TRAIN_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        
        with open(TRAIN_OUTPUT, "w", encoding="utf-8") as f:
            for _, row in df.iterrows():
                # Extract the messy input string (Assumed column name 'INPUT - Part_Desc')
                input_desc = row.get("INPUT - Part_Desc", "")
                if pd.isna(input_desc) or not input_desc:
                    continue
                
                # Build the JSON output based on the enriched columns
                # Ignoring placeholder values like "-- Unbranded --"
                structured_output = {}
                for col in df.columns:
                    if col.startswith("INPUT"):
                        continue
                    
                    val = row[col]
                    if pd.isna(val) or str(val).strip().startswith("--"):
                        continue
                    
                    structured_output[col] = str(val).strip()
                
                # Write to JSONL
                convo = {
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert industrial data extraction assistant. Extract structured product attributes from the messy catalog description. Output ONLY valid JSON."
                        },
                        {
                            "role": "user",
                            "content": f"Extract attributes from this raw description: {input_desc}"
                        },
                        {
                            "role": "assistant",
                            "content": json.dumps(structured_output)
                        }
                    ]
                }
                f.write(json.dumps(convo) + "\n")
                
        print(f"[SUCCESS] Generated actual training dataset at: {TRAIN_OUTPUT}")
        
    except Exception as e:
        print(f"[ERROR] Error parsing Excel file: {e}")

if __name__ == "__main__":
    prepare_dataset()
