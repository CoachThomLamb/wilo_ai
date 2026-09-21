#!/usr/bin/env python3
"""
SFT fine-tuning of GPT-2 on coaching conversation data.
Run on RunPod RTX 3090/4090.

Dataset format (JSONL): one conversation per line
{"messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
"""
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments
from trl import SFTTrainer, DataCollatorForCompletionOnlyLM
from datasets import load_dataset
from huggingface_hub import login
import torch, os, json

# --- Config ---
MODEL_ID   = "gpt2"
DATA_PATH  = "/workspace/coaching_data.jsonl"
OUTPUT_DIR = "/workspace/sft_output"
HF_TOKEN   = os.environ.get("HF_TOKEN", "")

if HF_TOKEN:
    login(token=HF_TOKEN)

# --- Load model and tokenizer ---
print("Loading model...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(MODEL_ID, torch_dtype=torch.float16)
model = model.to("cuda")
print(f"Model loaded on: {next(model.parameters()).device}")

# --- Load dataset ---
print("Loading dataset...")
dataset = load_dataset("json", data_files=DATA_PATH, split="train")
print(f"Dataset size: {len(dataset)} examples")

def format_conversation(example):
    messages = example["messages"]
    text = ""
    for msg in messages:
        role = msg["role"].upper()
        text += f"{role}: {msg['content']}\n"
    return {"text": text}

dataset = dataset.map(format_conversation)

# --- Training args ---
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=3,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,
    learning_rate=2e-5,
    warmup_steps=10,
    logging_steps=10,
    save_steps=100,
    fp16=True,
    report_to="none",
)

# --- Trainer ---
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=512,
    args=training_args,
)

print("Starting SFT...")
trainer.train()

# --- Save ---
trainer.save_model(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)
print(f"Model saved to {OUTPUT_DIR}")
