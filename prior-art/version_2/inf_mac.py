import torch
import gradio as gr
from transformers import AutoModelForCausalLM, AutoTokenizer

if torch.backends.mps.is_available():
    device = torch.device("mps")
    print("Using Apple MPS acceleration")
else:
    device = torch.device("cpu")
    print("MPS not available, using CPU")

model_id = "Qwen/Qwen2.5-3B-Instruct"

print(f"Loading {model_id}...")
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    torch_dtype=torch.float16,
).to(device)
print("Model loaded.")

def chat(message, history):
    messages = [{"role": "system", "content": "You are a helpful and concise AI"}]
    for user_msg, assistant_msg in history:
        messages.append({"role": "user", "content": user_msg})
        messages.append({"role": "assistant", "content": assistant_msg})
    messages.append({"role": "user", "content": message})

    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    model_inputs = tokenizer([text], return_tensors="pt").to(device)

    with torch.no_grad():
        generated_ids = model.generate(
            **model_inputs,
            max_new_tokens=1024,
            temperature=0.7,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )

    output_ids = generated_ids[0][len(model_inputs.input_ids[0]):]
    return tokenizer.decode(output_ids, skip_special_tokens=True)

gr.ChatInterface(chat).launch(server_name="0.0.0.0", server_port=7860)
