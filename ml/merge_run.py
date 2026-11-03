"""Rebuild a trained model from a saved run: download its LoRA adapter from the HF repo and merge it into the base.

    python ml/merge_run.py --hub-repo Successthom/wilo-toolcall --out /workspace/out/merged      # newest run
    python ml/merge_run.py --hub-repo Successthom/wilo-toolcall --run runs/20261029-120637 --out ...

Needs HF_TOKEN (the repo is private). The merged copy serves on vLLM with the same flags as the base model.
"""
import argparse
import json

from huggingface_hub import HfApi, snapshot_download


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--hub-repo', required=True)
    ap.add_argument('--run', help='runs/<UTC time>; default: the newest')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()

    runs = sorted({f.split('/')[1] for f in HfApi().list_repo_files(a.hub_repo) if f.startswith('runs/')})
    run = a.run or f'runs/{runs[-1]}'
    local = snapshot_download(a.hub_repo, allow_patterns=[f'{run}/*'])
    base = json.load(open(f'{local}/{run}/run.json'))['base']
    print(f'merging {a.hub_repo}/{run} into {base}', flush=True)

    import torch
    from peft import PeftModel
    from transformers import AutoModelForImageTextToText, AutoProcessor
    model = AutoModelForImageTextToText.from_pretrained(base, dtype=torch.bfloat16)
    model = PeftModel.from_pretrained(model, f'{local}/{run}/adapter').merge_and_unload()
    model.save_pretrained(a.out)
    AutoProcessor.from_pretrained(base).save_pretrained(a.out)
    print(f'MERGE_OK {run} -> {a.out}', flush=True)


if __name__ == '__main__':
    main()
