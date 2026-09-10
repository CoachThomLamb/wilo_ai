# Qwen on RunPod — Planning Notes
*2026-08-17*

## The Idea

Run Qwen2.5-14B on a RunPod GPU for inference — expose it via a Gradio web interface so people can use it as a self-hosted alternative to ChatGPT. The ownership/privacy angle: users aren't sending their data to OpenAI or Google.

## Hardware Plan

- **GPU:** RTX 4090 (~$0.69/hr on RunPod, 24GB VRAM)
- **Model:** Qwen2.5-14B-Instruct with 4-bit quantization (drops VRAM requirement from ~28GB to ~9GB)
- **Alternative:** A100 (80GB) or L40S (48GB) for full bfloat16, no quantization needed

## How the Code Works

1. **Check for CUDA** — confirm we're on an NVIDIA GPU
2. **Load tokenizer** — stays on CPU, converts text ↔ token ids. Qwen2.5 vocab size is ~150,000 tokens (byte-level BPE, same approach as GPT-2 but larger)
3. **Load model weights** — 14B parameters moved to GPU via `.to(device)`, loaded in 4-bit quantization via `bitsandbytes`
4. **Inference loop** — tokenize input → model generates next tokens → decode back to text, streamed token by token

## Gradio Web Interface Plan

Wrap the inference in a Gradio `ChatInterface` — one page, shareable URL, RunPod exposes port 7860 publicly.

```python
import gradio as gr

def chat(message, history):
    # inference code here
    return response

gr.ChatInterface(chat).launch(server_name="0.0.0.0", server_port=7860)
```

## Future: Fine-Tuning

After collecting usage data:
1. Save conversations from the Gradio app
2. Have users rate/flag outputs
3. Format as instruction/response pairs
4. Fine-tune with Unsloth or TRL (feasible on single GPU)

Makes the model better for the specific community rather than a generic audience — fits the ownership angle.

## Libraries Needed

```bash
pip install transformers accelerate bitsandbytes gradio
```

## Next Steps

- [ ] Spin up 4090 pod on RunPod
- [ ] Write and test the inference script
- [ ] Wrap in Gradio interface
- [ ] Test with a few people
- [ ] Collect feedback, decide if 14B is good enough or need bigger
