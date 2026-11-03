#!/bin/bash
# Runs on the pod (vllm/vllm-openai image): train the LoRA, then serve the base model and the trained one side by
# side so ml/score.py can score both on ml/test.jsonl. Needs VLLM_KEY in the env. No SSH: the pod's start command
# downloads this branch and runs this script; follow it with the pod logs.
cd "$(dirname "$0")/../.."
# Every run is saved off the pod (ml/train.py uploads it). Don't spend GPU time on a run that can't be saved.
# Checked before `set -x`: tracing would print the token into the pod logs.
if [ -z "$HF_TOKEN" ] || [ -z "$WILO_HF_REPO" ]; then echo "TRAIN_REFUSED: set HF_TOKEN and WILO_HF_REPO"; exit 1; fi
set -x
export HF_HOME=/workspace/hf

# Training libs only; --no-deps keeps the image's transformers/torch, which vLLM needs.
pip install -q --no-deps trl peft flash-linear-attention fla-core && pip install -q datasets accelerate einops huggingface_hub
python3 -c "import transformers, trl, peft, torch, fla; print('versions', transformers.__version__, trl.__version__, peft.__version__, torch.__version__, fla.__version__)"
PYTHONUNBUFFERED=1 python3 ml/train.py --out /workspace/out --hub-repo "$WILO_HF_REPO" && echo TRAIN_OK || echo TRAIN_FAILED

set +x  # keep VLLM_KEY out of the logs
ARGS="--max-model-len 16384 --gpu-memory-utilization 0.42 --api-key $VLLM_KEY --reasoning-parser qwen3
      --enable-auto-tool-choice --tool-call-parser qwen3_coder --language-model-only"
vllm serve Qwen/Qwen3.5-4B --port 8001 $ARGS &
sleep 180  # let the first one claim its memory before the second profiles the GPU
[ -d /workspace/out/merged ] && vllm serve /workspace/out/merged --served-model-name wilo-ft --port 8000 $ARGS &
wait
