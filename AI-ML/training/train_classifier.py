"""
Train a DistilBERT model on the downloaded MAVE/Synthetic dataset.

This model is part of the "Fast Path" (Phase 2 optimization) of Alchemy AI.
Instead of using a large LLM (Qwen) for industry detection and basic
attribute extraction, we train a small, blazing-fast model that runs
on CPU in <50ms.

Usage:
  python -m training.train_classifier
"""

import os
import json
from pathlib import Path

import torch
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    DataCollatorWithPadding
)
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score


# Paths
DATA_DIR = Path(__file__).parent / "data"
MODEL_DIR = Path(__file__).parent / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME = "distilbert-base-uncased"
OUTPUT_DIR = MODEL_DIR / "industry-classifier"


def compute_metrics(pred):
    labels = pred.label_ids
    preds = pred.predictions.argmax(-1)
    f1 = f1_score(labels, preds, average="weighted")
    acc = accuracy_score(labels, preds)
    return {"accuracy": acc, "f1": f1}


def train_model():
    """Train the industry classification model."""
    data_path = DATA_DIR / "product_classification_train.jsonl"
    if not data_path.exists():
        print(f"Dataset not found at {data_path}. Run download_dataset.py first.")
        return

    print("Loading dataset...")
    texts = []
    labels = []
    label_to_id = {}
    id_to_label = {}
    
    with open(data_path, "r", encoding="utf-8") as f:
        for line in f:
            sample = json.loads(line.strip())
            
            # WDC/MAVE format vs Synthetic format
            text = sample.get("text", "") or sample.get("title", "")
            label = sample.get("label", "") or sample.get("category", "")
            
            if text and label:
                if label not in label_to_id:
                    idx = len(label_to_id)
                    label_to_id[label] = idx
                    id_to_label[idx] = label
                
                texts.append(text)
                labels.append(label_to_id[label])

    print(f"Found {len(texts)} samples across {len(label_to_id)} industries.")
    
    # Save label mappings for inference
    with open(MODEL_DIR / "label_mapping.json", "w", encoding="utf-8") as f:
        json.dump({"label_to_id": label_to_id, "id_to_label": id_to_label}, f, indent=2)

    # Train/Test Split
    train_texts, val_texts, train_labels, val_labels = train_test_split(
        texts, labels, test_size=0.1, random_state=42
    )

    print("Tokenizing...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    
    train_encodings = tokenizer(train_texts, truncation=True, padding=True, max_length=128)
    val_encodings = tokenizer(val_texts, truncation=True, padding=True, max_length=128)
    
    # Create HF Datasets
    class ProductDataset(torch.utils.data.Dataset):
        def __init__(self, encodings, labels):
            self.encodings = encodings
            self.labels = labels

        def __getitem__(self, idx):
            item = {key: torch.tensor(val[idx]) for key, val in self.encodings.items()}
            item['labels'] = torch.tensor(self.labels[idx])
            return item

        def __len__(self):
            return len(self.labels)

    train_dataset = ProductDataset(train_encodings, train_labels)
    val_dataset = ProductDataset(val_encodings, val_labels)

    # Load Model
    print("Initializing model...")
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME, 
        num_labels=len(label_to_id),
        id2label=id_to_label,
        label2id=label_to_id
    )

    # Training Arguments
    training_args = TrainingArguments(
        output_dir=str(OUTPUT_DIR),
        num_train_epochs=3,
        per_device_train_batch_size=32,
        per_device_eval_batch_size=64,
        warmup_steps=500,
        weight_decay=0.01,
        logging_dir=str(OUTPUT_DIR / "logs"),
        logging_steps=100,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1"
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        tokenizer=tokenizer,
        compute_metrics=compute_metrics,
        data_collator=DataCollatorWithPadding(tokenizer)
    )

    print("Starting training...")
    trainer.train()

    print(f"Saving best model to {OUTPUT_DIR}")
    trainer.save_model(str(OUTPUT_DIR))
    
    print("\nTraining complete!")
    print("Next step: export to ONNX for fast CPU inference.")
    print("Run: python -m training.export_onnx")


if __name__ == "__main__":
    train_model()
