"""
Upload this script to Kaggle along with your train.jsonl file.
Ensure you are using a T4 x2 GPU environment in Kaggle.

1. In Kaggle, click "Add Data" -> Upload your `unilog_train.jsonl`
2. Make sure Internet is turned ON in Kaggle Notebook settings.
3. Install required libraries:
   !pip install -q transformers peft trl datasets accelerate bitsandbytes
4. Run this script!
"""

import torch
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer, SFTConfig

# Configuration
# Since we are running the AWQ locally, we can fine-tune the BF16/FP16 base version of the same model size on Kaggle
MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct" 
DATASET_PATH = "/kaggle/input/unilog-dataset/unilog_train.jsonl" # Adjust path after uploading to Kaggle
OUTPUT_DIR = "/kaggle/working/unilog_qwen_adapter"

def train():
    print("🚀 Initializing Kaggle LoRA Training for Unilog Dataset...")
    
    # 1. Load the Dataset
    dataset = load_dataset("json", data_files=DATASET_PATH, split="train")
    
    # 2. Configure 4-bit Quantization (to fit inside Kaggle's 16GB VRAM)
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16
    )

    # 3. Load Base Model and Tokenizer
    print("Loading Model...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True
    )
    
    # 4. Prepare for LoRA
    model = prepare_model_for_kbit_training(model)
    
    lora_config = LoraConfig(
        r=16, 
        lora_alpha=32, 
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # 5. Format the Chat Dataset
    def format_chat_template(example):
        example["text"] = tokenizer.apply_chat_template(example["messages"], tokenize=False, add_generation_prompt=False)
        return example

    dataset = dataset.map(format_chat_template)

    # 6. Trainer Setup
    training_args = SFTConfig(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        logging_steps=10,
        max_steps=100, # Adjust based on dataset size (usually 2-3 epochs)
        dataset_text_field="text",
        max_seq_length=1024,
        fp16=False,
        bf16=True, # T4 GPUs support bf16 mixed precision
        optim="paged_adamw_8bit"
    )

    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        args=training_args,
        peft_config=lora_config,
    )

    # 7. Train and Save!
    print("Starting Training... 🚀")
    trainer.train()
    
    print(f"Training Complete! Saving adapter to {OUTPUT_DIR}")
    trainer.model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print("✅ Done! You can now download the `unilog_qwen_adapter` folder from Kaggle output.")

if __name__ == "__main__":
    train()
