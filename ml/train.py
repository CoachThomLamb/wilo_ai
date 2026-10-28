"""Fine-tune Qwen3.5-4B to call the right WILO tool: TRL SFTTrainer + LoRA, on a 24 GB GPU.

    pip install -r ml/requirements-train.txt
    python ml/train.py --show 2            # print 2 rendered examples, no GPU needed
    python ml/train.py                      # train → ml/out/adapter and ml/out/merged (for vLLM)

Data: ml/train_synth.jsonl (local, gitignored) + ml/seeds.jsonl. Never ml/test.jsonl. Each item becomes the same
prompt score.py sends (messages(item), with the tool definitions) and one target: the expected tool call, or a fixed
"No tool needed." when Claude answered without a tool (the small model is only the tool caller; Claude replies).
Loss is on the target only. The chat template gives the target an empty <think> block, so the model learns to call
the tool without reasoning first.
"""
import argparse
import json
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
    ap.add_argument('--epochs', type=float, default=3)
    ap.add_argument('--lr', type=float, default=1e-4)
    ap.add_argument('--rank', type=int, default=16)
    ap.add_argument('--no-seeds', action='store_true', help='train on the synthetic data only')
    ap.add_argument('--show', type=int, help='print this many rendered examples and stop')
    a = ap.parse_args()

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


if __name__ == '__main__':
    main()
