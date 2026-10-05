#!/usr/bin/env python3
"""Load Qwen 2.5 3B from HuggingFace and run a forward pass."""
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

MODEL_ID = "Qwen/Qwen2.5-3B-Instruct"

# Load tokenizer and model
print("Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)

print("Loading model...")
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.float16,
    device_map="auto",
)
model.eval()

print("Model loaded. Running inference...\n")

prompt = "What is the best way to train for strength?"
messages = [{"role": "user", "content": prompt}]
text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
inputs = tokenizer(text, return_tensors="pt").to(model.device)

with torch.no_grad():
    output = model.generate(**inputs, max_new_tokens=200)

response = tokenizer.decode(output[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
print(f"User: {prompt}")
print(f"Model: {response}")
