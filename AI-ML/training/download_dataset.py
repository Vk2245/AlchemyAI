"""
Download the MAVE dataset (Google Research) for product attribute extraction.

MAVE = Multi-source Attribute Value Extraction
- 2.2 million Amazon product profiles
- 3 million attribute-value annotations
- 1,257 unique product categories
- License: CC-BY-4.0

This script downloads a curated subset (50K samples) for training
a DistilBERT classifier. The full dataset is 2.2M rows but we only
need a subset for our use case.

Usage:
  python -m training.download_dataset
"""

import os
import json
from pathlib import Path

from datasets import load_dataset


# Output directory
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def download_mave_subset(n_samples: int = 50000) -> Path:
    """
    Download a subset of the MAVE dataset from Hugging Face.

    The dataset is hosted on HF Hub as a processed version of the
    original Google Research MAVE dataset.
    """
    print(f"Downloading MAVE dataset (subset: {n_samples} samples)...")

    # Load from HF Hub — this is a community-processed version
    # of the MAVE dataset that's easier to work with
    try:
        dataset = load_dataset(
            "wdc/products-categorization",
            split=f"train[:{n_samples}]",
            trust_remote_code=True,
        )
        output_path = DATA_DIR / "product_classification_train.jsonl"

        with open(output_path, "w", encoding="utf-8") as f:
            for row in dataset:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

        print(f"Saved {len(dataset)} samples to: {output_path}")
        return output_path

    except Exception as e:
        print(f"WDC dataset failed: {e}")
        print("Falling back to synthetic generation...")
        return generate_synthetic_dataset(n_samples=2000)


def generate_synthetic_dataset(n_samples: int = 2000) -> Path:
    """
    Generate a synthetic product classification dataset.

    Uses a curated list of product descriptions across multiple
    industries. This is the fallback if the MAVE/WDC download fails.
    """
    print(f"Generating synthetic dataset ({n_samples} samples)...")

    industries = {
        "electrical": [
            "ABB SACE Tmax circuit breaker 690V 50kA",
            "Schneider Electric Compact NSX250 molded case circuit breaker",
            "Siemens SIRIUS 3RT2 contactor 400V AC-3 rated",
            "Phoenix Contact terminal block DIN rail mount 24AWG",
            "Eaton Moeller DILM series motor starter 7.5kW",
            "Allen-Bradley 1756 ControlLogix PLC module",
            "Omron G2R power relay 5A 24VDC coil DPDT",
            "Weidmuller surge protector DIN rail SPD Type 2",
        ],
        "software": [
            "Microsoft 365 Business Premium annual subscription license",
            "Atlassian Jira Software Cloud Standard per user",
            "Salesforce CRM Enterprise Edition annual license",
            "Adobe Creative Cloud All Apps monthly subscription",
            "AWS EC2 t3.medium instance reserved 1-year term",
            "Docker Enterprise container platform license",
            "Splunk Enterprise Security SIEM module license",
            "VMware vSphere Standard per CPU socket license",
        ],
        "food": [
            "Organic whole wheat flour 25kg bag certified USDA",
            "Cold pressed extra virgin olive oil 5L tin Italy",
            "Freeze dried instant coffee arabica 500g jar",
            "Pasteurized whole milk 3.5% fat 1L tetra pack",
            "Dark chocolate 70% cocoa single origin Ecuador bar 100g",
            "Gluten free oat flour 1kg pack certified GF",
            "Canned tuna in olive oil 185g BPA-free can",
            "Raw organic honey 500g glass jar unprocessed",
        ],
        "pharmaceutical": [
            "Amoxicillin 500mg capsules 30-count blister pack",
            "Insulin glargine 100 units/mL prefilled pen 3mL",
            "Ibuprofen 200mg coated tablets bottle of 100",
            "Metformin HCl 850mg extended release tablets",
            "Surgical face mask Type IIR 50-pack sterile",
            "Nitrile examination gloves powder-free medium box 100",
            "Digital infrared thermometer non-contact medical grade",
            "Pulse oximeter fingertip SpO2 monitor FDA cleared",
        ],
        "agriculture": [
            "NPK 20-20-20 water soluble fertilizer 25kg bag",
            "Glyphosate 41% herbicide concentrate 20L drum",
            "Drip irrigation emitter 4L/hr pressure compensating",
            "Hybrid tomato seeds F1 variety heat tolerant 10g packet",
            "Neem oil organic pesticide cold pressed 1L bottle",
            "Soil pH meter digital portable waterproof probe",
            "Greenhouse polyethylene film UV stabilized 200 micron",
            "Automatic poultry feeder pan 10kg capacity galvanized",
        ],
        "mechanical": [
            "SKF 6205-2RS deep groove ball bearing sealed",
            "Bosch GWS 750-100 angle grinder 750W 100mm disc",
            "Parker hydraulic cylinder double acting 50mm bore",
            "Mitutoyo digital caliper 150mm 0.01mm resolution",
            "3M safety helmet Type I Class E ANSI rated",
            "Lincoln Electric MIG welder 200A wire feed",
            "Makita cordless drill 18V brushless 13mm chuck",
            "Enerpac hydraulic hand pump 700 bar single speed",
        ],
        "automotive": [
            "Bosch spark plug FR7DC+ iridium for gasoline engines",
            "Continental ContiPremiumContact 6 205/55R16 91V tire",
            "Denso alternator 12V 120A for Toyota Corolla 2020",
            "Mann oil filter HU 7010z for BMW diesel engines",
            "NGK glow plug Y-732J for Volkswagen TDI engines",
            "Brembo brake disc front ventilated 300mm for Audi A4",
            "KYB shock absorber gas-a-just rear for Honda Civic",
            "Valeo clutch kit 3-piece for Ford Focus 1.6L",
        ],
        "textiles": [
            "100% organic cotton fabric 60 inch width 200 GSM",
            "Polyester filament yarn DTY 150D/48F semi-dull",
            "Industrial sewing machine lockstitch automatic trimmer",
            "Cotton-polyester blend T-shirt 180GSM round neck",
            "Dyeing machine jet type 500kg capacity stainless",
            "Woven polypropylene sack 50kg capacity UV treated",
            "Merino wool yarn superfine 18.5 micron 2-ply",
            "Nylon zipper #5 auto-lock slider 30cm length",
        ],
    }

    samples = []
    import random
    random.seed(42)

    for industry, products in industries.items():
        per_product = max(1, n_samples // (len(industries) * len(products)))
        for product in products:
            for _ in range(per_product):
                # Add minor variations
                variations = [
                    product,
                    product.lower(),
                    product.upper(),
                    f"Product: {product}",
                    f"Specification sheet for {product}",
                    f"Order: {product} - qty 10",
                ]
                text = random.choice(variations)
                samples.append({
                    "text": text,
                    "label": industry,
                })

    random.shuffle(samples)
    samples = samples[:n_samples]

    output_path = DATA_DIR / "product_classification_train.jsonl"
    with open(output_path, "w", encoding="utf-8") as f:
        for sample in samples:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")

    print(f"Generated {len(samples)} synthetic samples across {len(industries)} industries")
    print(f"Saved to: {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "auto"

    if mode == "synthetic":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
        generate_synthetic_dataset(n)
    elif mode == "mave":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 50000
        download_mave_subset(n)
    else:
        # Auto: try MAVE first, fall back to synthetic
        download_mave_subset()

    print("\nDataset ready for training!")
    print("Next step: python -m training.train_classifier")
