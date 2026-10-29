"""Fine-tune Qwen3.5-4B to call the right WILO tool: TRL SFTTrainer + LoRA, on a 24 GB GPU.

    pip install -r ml/requirements-train.txt
    python ml/train.py --show 2            # print 2 rendered examples, no GPU needed
    python ml/train.py --hub-repo <user>/wilo-toolcall   # train → ml/out/{adapter,merged}, then upload the run

Every run is saved (Thom, 2026-10-29: the first trained model was lost with its pod): the LoRA adapter, the exact
training data and the run settings go to a private Hugging Face repo (HF_TOKEN in the env), one folder per run
(runs/<UTC time>). If the upload fails, the script exits non-zero. --no-upload only for a local dry run.

Data: ml/train_synth.jsonl + ml/seeds.jsonl (both committed). Never ml/test.jsonl. Each item becomes the same
prompt score.py sends (messages(item), with the tool definitions) and one target: the expected tool call, or a fixed
"No tool needed." when Claude answered without a tool (the small model is only the tool caller; Claude replies).
Loss is on the target only. The chat template gives the target an empty <think> block, so the model learns to call
the tool without reasoning first.
"""
import argparse
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

from score import messages

HERE = Path(__file__).resolve().parent
BASE = 'Qwen/Qwen3.5-4B'
NO_TOOL = 'No tool needed.'


def load_items(use_seeds):
    files = [HERE / 'train_synth.jsonl'] + ([HERE / 'seeds.jsonl'] if use_seeds else [])
    items = [json.loads(l) for f in files for l in open(f)]
    # Old claude.ai labels kept only a summary of the workout ("same as dry run"): not a call to learn from.
    items = [i for i in items if i['expected'].get('args_complete', True)]
    test_ids = {json.loads(l)['id'] for l in open(HERE / 'test.jsonl')}
    assert not test_ids & {i['id'] for i in items}, 'a test item is in the training data'
    return items


def target(item):
    want = item['expected']
    if not want['tool']:
        return {'role': 'assistant', 'content': NO_TOOL}
    # The Qwen template wants arguments as a dict (it renders <parameter=...> blocks itself).
    call = {'type': 'function', 'function': {'name': want['tool'], 'arguments': want.get('args') or {}}}
    return {'role': 'assistant', 'content': '', 'tool_calls': [call]}


def tokenize(tok, item, tools):
    """input_ids + completion_mask: loss only on the assistant's answer."""
    prompt = tok.apply_chat_template(messages(item), tools=tools, add_generation_prompt=True, tokenize=False)
    full = tok.apply_chat_template(messages(item) + [target(item)], tools=tools, tokenize=False)
    assert full.startswith(prompt), f"{item['id']}: the prompt isn't a prefix of the full chat"
    p, c = tok(prompt, add_special_tokens=False)['input_ids'], tok(full[len(prompt):], add_special_tokens=False)['input_ids']
    return {'input_ids': p + c, 'completion_mask': [0] * len(p) + [1] * len(c)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default=BASE)
    ap.add_argument('--out', default=str(HERE / 'out'))
    ap.add_argument('--hub-repo', help='private HF repo for the run, e.g. thomlamb/wilo-toolcall')
    ap.add_argument('--no-upload', action='store_true', help='local dry run only: nothing saved off the machine')
    ap.add_argument('--epochs', type=float, default=3)
    ap.add_argument('--lr', type=float, default=1e-4)
    ap.add_argument('--rank', type=int, default=16)
    ap.add_argument('--no-seeds', action='store_true', help='train on the synthetic data only')
    ap.add_argument('--show', type=int, help='print this many rendered examples and stop')
    a = ap.parse_args()
    if a.show is None and not a.no_upload and not a.hub_repo:
        sys.exit('Set --hub-repo (or --no-upload for a local dry run): a trained run must be saved off the machine.')

    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(a.base)
    tools = json.loads((HERE / 'wilo_tools.json').read_text())
    items = load_items(not a.no_seeds)

    if a.show:
        for item in items[:a.show]:
            ex = tokenize(tok, item, tools)
            cut = ex['completion_mask'].index(1)
            print(f"=== {item['id']}: {len(ex['input_ids'])} tokens, {len(ex['input_ids']) - cut} in the target")
            print(tok.decode(ex['input_ids'][cut - 200:cut]), '\n--- target ---')
            print(tok.decode(ex['input_ids'][cut:]))
        return

    import torch
    from datasets import Dataset
    from peft import LoraConfig
    from transformers import AutoModelForImageTextToText
    from trl import SFTConfig, SFTTrainer

    rows = [tokenize(tok, i, tools) for i in items]
    lens = sorted(len(r['input_ids']) for r in rows)
    print(f'{len(rows)} examples, tokens: median {lens[len(lens) // 2]}, max {lens[-1]}')

    # Qwen3.5 is an image+text model; we only use text, so LoRA goes on the language model alone.
    model = AutoModelForImageTextToText.from_pretrained(a.base, dtype=torch.bfloat16, attn_implementation='sdpa')
    lora = LoraConfig(r=a.rank, lora_alpha=2 * a.rank, lora_dropout=0.05, task_type='CAUSAL_LM',
                      target_modules=r'.*language_model.*\.(q_proj|k_proj|v_proj|o_proj|gate_proj|up_proj|down_proj)')
    cfg = SFTConfig(output_dir=a.out, num_train_epochs=a.epochs, learning_rate=a.lr, lr_scheduler_type='cosine',
                    warmup_steps=0.05, per_device_train_batch_size=1, gradient_accumulation_steps=8,
                    gradient_checkpointing=True, bf16=True, max_length=lens[-1], logging_steps=2, disable_tqdm=True,
                    save_strategy='no', report_to='none', seed=42)
    trainer = SFTTrainer(model=model, args=cfg, train_dataset=Dataset.from_list(rows), processing_class=tok,
                         peft_config=lora)
    trainer.train()

    out = Path(a.out)
    trainer.model.save_pretrained(out / 'adapter')
    tok.save_pretrained(out / 'adapter')
    # A merged copy serves on vLLM like the base model (same flags), with no LoRA support needed for this arch.
    merged = trainer.model.merge_and_unload()
    merged.save_pretrained(out / 'merged')
    from transformers import AutoProcessor
    AutoProcessor.from_pretrained(a.base).save_pretrained(out / 'merged')
    print(f'saved {out / "adapter"} and {out / "merged"}')
    if not a.no_upload:
        upload(a, out)


def upload(a, out):
    """Save the run where it outlives the pod: adapter + training data + settings → private HF repo."""
    from huggingface_hub import HfApi
    run = time.strftime('runs/%Y%m%d-%H%M%S', time.gmtime())
    keep = out / 'run'
    shutil.copytree(out / 'adapter', keep / 'adapter', dirs_exist_ok=True)
    (keep / 'data').mkdir(parents=True, exist_ok=True)
    data = [HERE / 'train_synth.jsonl'] + ([HERE / 'seeds.jsonl'] if not a.no_seeds else [])
    for f in data:
        shutil.copy(f, keep / 'data' / f.name)
    info = {'base': a.base, 'args': vars(a), 'data': {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in data}}
    (keep / 'run.json').write_text(json.dumps(info, indent=2, default=str))
    try:
        api = HfApi()
        api.create_repo(a.hub_repo, private=True, exist_ok=True)
        api.upload_folder(repo_id=a.hub_repo, folder_path=str(keep), path_in_repo=run,
                          commit_message=f'{run}: adapter + training data + settings')
        files = [f for f in api.list_repo_files(a.hub_repo) if f.startswith(run + '/adapter/')]
        assert any(f.endswith('.safetensors') for f in files), f'no adapter weights in {a.hub_repo}/{run}'
    except Exception as e:
        sys.exit(f'UPLOAD_FAILED: {e!r}. The trained adapter is only in {out} on this machine: copy it before '
                 f'the pod goes away.')
    print(f'UPLOAD_OK https://huggingface.co/{a.hub_repo}/tree/main/{run}')


if __name__ == '__main__':
    main()
