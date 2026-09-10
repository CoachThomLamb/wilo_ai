import os
os.environ["HF_HOME"] = "/workspace/hf_cache"

import torch
import gradio as gr
import csv
import time
from datetime import datetime
from transformers import AutoModelForCausalLM, AutoTokenizer

LOG_FILE = "/workspace/usage_log.csv"

def log_request(input_tokens, output_tokens, duration_sec):
    file_exists = os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "input_tokens", "output_tokens", "duration_sec"])
        writer.writerow([datetime.utcnow().isoformat(), input_tokens, output_tokens, round(duration_sec, 2)])

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model_id = "Qwen/Qwen2.5-3B-Instruct"

print(f"Loading {model_id}...")
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    torch_dtype=torch.bfloat16,
    device_map="auto"
)
print("Model loaded.")

def chat(message, history):
    messages = [{"role": "system", "content": "You are a helpful and concise AI"}]
    for user_msg, assistant_msg in history:
        messages.append({"role": "user", "content": user_msg})
        messages.append({"role": "assistant", "content": assistant_msg})
    messages.append({"role": "user", "content": message})

    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    model_inputs = tokenizer([text], return_tensors="pt").to(device)

    t0 = time.time()
    with torch.no_grad():
        generated_ids = model.generate(
            **model_inputs,
            max_new_tokens=1024,
            temperature=0.7,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )
    duration = time.time() - t0

    output_ids = generated_ids[0][len(model_inputs.input_ids[0]):]
    input_tokens = len(model_inputs.input_ids[0])
    output_tokens = len(output_ids)
    log_request(input_tokens, output_tokens, duration)

    return tokenizer.decode(output_ids, skip_special_tokens=True)

gr.ChatInterface(chat).launch(server_name="0.0.0.0", server_port=7860)
