# WILO Inference — RunPod Setup

## Goal
Run Qwen 2.5 3B inference on a RunPod RTX 3090/4090 GPU.

## RunPod Setup

1. Go to RunPod, rent a pod with:
   - GPU: RTX 3090 or 4090 (24GB VRAM)
   - Template: `RunPod PyTorch 2.x` (has CUDA pre-installed)
   - Disk: 50GB

2. Open a terminal in the pod.

## Install Dependencies

```bash
git clone https://github.com/YOUR_REPO/wilo.git
cd wilo/be
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Set Up HuggingFace Token

```bash
echo 'HUGGING_FACE_TOKEN="hf_your_token_here"' > .env
```

## Run

```bash
python3 inf_1.py
```

First run downloads ~6GB of weights from HuggingFace. Subsequent runs use the cache.

## Notes

- `device_map="auto"` will automatically use the GPU
- On a 3090/4090 with 24GB VRAM, the 3B model fits entirely in GPU memory — no swapping
- To use a different model, change `MODEL_ID` in `inf_1.py`

---

## Next: Fine-Tuning with LoRA

LoRA (Low-Rank Adaptation) lets you fine-tune the model on your workout history without retraining all 3B parameters — only a small set of adapter weights get updated, which is fast and cheap.

### What you'll need

- Your Hevy CSV export (`workout_data.csv`)
- Your WILO session JSONs (`sess_*.json`)
- A training script (to be written)

### Plan

1. Convert workout history into a prompt/response dataset (e.g. "given this history, what should I do next?")
2. Fine-tune Qwen 2.5 3B with LoRA using `peft` + `trl`
3. Save the adapter weights (small — a few hundred MB)
4. Load base model + adapter at inference time

### Additional dependencies

```
peft
trl
datasets
```

### Notes

- LoRA adapters are separate from the base model weights — you can swap them out or stack them
- Training on a 3090 for a few hundred examples takes minutes, not hours
- The adapter teaches the model your coaching style and history; the base model handles language
