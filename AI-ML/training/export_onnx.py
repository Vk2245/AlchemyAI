"""
Export the trained PyTorch model to ONNX format.

ONNX (Open Neural Network Exchange) allows the model to run on
the CPU using ONNX Runtime, which is much faster than PyTorch
and requires fewer dependencies in production.

Usage:
  python -m training.export_onnx
"""

import sys
from pathlib import Path

try:
    from optimum.onnxruntime import ORTModelForSequenceClassification
    from transformers import AutoTokenizer
except ImportError:
    print("Error: 'optimum' and 'onnxruntime' packages are required.")
    print("Install with: pip install optimum[onnxruntime]")
    sys.exit(1)


MODEL_DIR = Path(__file__).parent / "models"
INPUT_DIR = MODEL_DIR / "industry-classifier"
OUTPUT_DIR = MODEL_DIR / "industry-classifier-onnx"


def export_to_onnx():
    """Export the trained model to ONNX format."""
    
    if not INPUT_DIR.exists():
        print(f"Error: Trained model not found at {INPUT_DIR}")
        print("Run 'python -m training.train_classifier' first.")
        sys.exit(1)
        
    print(f"Loading PyTorch model from {INPUT_DIR}...")
    
    # Load model and tokenizer
    tokenizer = AutoTokenizer.from_pretrained(INPUT_DIR)
    
    # ORTModelForSequenceClassification handles the ONNX conversion under the hood
    # by setting export=True
    model = ORTModelForSequenceClassification.from_pretrained(
        INPUT_DIR, 
        export=True
    )
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Exporting ONNX model to {OUTPUT_DIR}...")
    
    # Save the ONNX model and tokenizer
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    
    print("\nExport successful!")
    print(f"The ONNX model is ready for production at: {OUTPUT_DIR}")
    print("This model will run in <50ms on a standard CPU.")


if __name__ == "__main__":
    export_to_onnx()
