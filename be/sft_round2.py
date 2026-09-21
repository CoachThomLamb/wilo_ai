"""
sft_round2.py - bare PyTorch SFT on top of an already-chat-tuned nanochat checkpoint.

Only dependencies: torch, plus the nanochat repo on PYTHONPATH (for the GPT class
and tokenizer). Everything else - chat rendering, loss masking, batching, the
training loop, the LR schedule, checkpointing - is written out here on purpose.

Run the SAME script for both arms, changing only --data and --out:
  python sft_round2.py --data generic.jsonl  --out runs/arm_generic
  python sft_round2.py --data coaching.jsonl --out runs/arm_coaching

Data format (JSONL, one conversation per line):
  {"messages": [{"role": "user", "content": "..."},
                {"role": "assistant", "content": "..."}, ...]}

NOTE: nanochat's internals move fast. The three imports/calls marked VERIFY below
are the only places this touches nanochat's API - check them against your clone.
"""
import argparse, json, math, os, random, shutil, time
import torch
import torch.nn.functional as F

from nanochat.gpt import GPT, GPTConfig                 # VERIFY: module/class names
from nanochat.tokenizer import RustBPETokenizer         # VERIFY: tokenizer class

p = argparse.ArgumentParser()
p.add_argument("--ckpt_dir", required=True, help="dir holding model_XXXXXX.pt + meta_XXXXXX.json")
p.add_argument("--step", required=True, type=int, help="the XXXXXX in the filenames")
p.add_argument("--tokenizer_dir", required=True, help="dir holding tokenizer.pkl + token_bytes.pt")
p.add_argument("--data", required=True)
p.add_argument("--out", required=True)
p.add_argument("--token_budget", type=int, default=2_000_000, help="SUPERVISED tokens to train on (match across arms)")
p.add_argument("--batch_tokens", type=int, default=32_000, help="supervised tokens per optimizer step (approx)")
p.add_argument("--micro_bs", type=int, default=4, help="conversations per forward pass")
p.add_argument("--seq_len", type=int, default=2048)
p.add_argument("--lr", type=float, default=2e-5)
p.add_argument("--seed", type=int, default=1337)
args = p.parse_args()

torch.manual_seed(args.seed); random.seed(args.seed)
device = "cuda"
torch.backends.cuda.matmul.allow_tf32 = True

# ---------------------------------------------------------------- load model
meta_path = os.path.join(args.ckpt_dir, f"meta_{args.step:06d}.json")
model_path = os.path.join(args.ckpt_dir, f"model_{args.step:06d}.pt")
meta = json.load(open(meta_path))
model = GPT(GPTConfig(**meta["model_config"]))          # VERIFY: meta key name

sd = torch.load(model_path, map_location="cpu")
sd = {k.removeprefix("_orig_mod."): v for k, v in sd.items()}  # strip torch.compile prefix if present
model.load_state_dict(sd, strict=True)
model.to(device).train()
print(f"params: {sum(t.numel() for t in model.parameters())/1e6:.0f}M")

tok = RustBPETokenizer.from_directory(args.tokenizer_dir)  # VERIFY: constructor
S = lambda name: tok.encode_special(name)
BOS, U0, U1, A0, A1 = S("<|bos|>"), S("<|user_start|>"), S("<|user_end|>"), S("<|assistant_start|>"), S("<|assistant_end|>")

# ---------------------------------------------------------------- render + mask
def render(conv):
    """Returns token ids and a mask: 1 where the model should learn to predict, 0 elsewhere.
    We only train on assistant content + the assistant_end token."""
    ids, mask = [BOS], [0]
    for m in conv["messages"]:
        body = tok.encode(m["content"])
        if m["role"] == "user":
            chunk, cmask = [U0] + body + [U1], [0] * (len(body) + 2)
        elif m["role"] == "assistant":
            chunk, cmask = [A0] + body + [A1], [0] + [1] * (len(body) + 1)
        else:
            continue
        ids += chunk; mask += cmask
    return ids[: args.seq_len + 1], mask[: args.seq_len + 1]

data = [render(json.loads(l)) for l in open(args.data) if l.strip()]
data = [(i, m) for i, m in data if sum(m[1:]) > 0]
print(f"conversations: {len(data)}, supervised tokens/epoch: {sum(sum(m[1:]) for _, m in data):,}")

def batches():
    while True:                                          # loop epochs until budget is spent
        random.shuffle(data)
        for i in range(0, len(data), args.micro_bs):
            yield data[i : i + args.micro_bs]

def collate(rows):
    T = max(len(ids) for ids, _ in rows) - 1
    x = torch.full((len(rows), T), BOS, dtype=torch.long)
    y = torch.full((len(rows), T), -1, dtype=torch.long)  # -1 = ignored in loss
    for r, (ids, mask) in enumerate(rows):
        t = torch.tensor(ids); mk = torch.tensor(mask, dtype=torch.bool)
        n = len(ids) - 1
        x[r, :n] = t[:-1]
        tgt = t[1:].clone(); tgt[~mk[1:]] = -1
        y[r, :n] = tgt
    return x.to(device), y.to(device)

# ---------------------------------------------------------------- train
# Plain AdamW. (nanochat itself uses Muon for matrices; AdamW keeps this simple.)
opt = torch.optim.AdamW(model.parameters(), lr=args.lr, betas=(0.9, 0.95), weight_decay=0.0)
total_steps = math.ceil(args.token_budget / args.batch_tokens)
lr_at = lambda s: args.lr * (1 - s / total_steps)       # linear decay to zero

seen, step, it, t0 = 0, 0, batches(), time.time()
while seen < args.token_budget:
    for g in opt.param_groups: g["lr"] = lr_at(step)
    step_tokens, loss_sum = 0, 0.0
    opt.zero_grad(set_to_none=True)
    while step_tokens < args.batch_tokens:               # grad accumulation by token count
        x, y = collate(next(it))
        n = int((y != -1).sum())
        with torch.autocast("cuda", dtype=torch.bfloat16):
            logits = model(x)                             # no targets -> logits
        loss = F.cross_entropy(logits.float().view(-1, logits.size(-1)), y.view(-1),
                               ignore_index=-1, reduction="sum")
        (loss / args.batch_tokens).backward()             # token-weighted mean across micro-batches
        step_tokens += n; loss_sum += loss.item()
    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
    opt.step()
    seen += step_tokens; step += 1
    print(f"step {step}/{total_steps} | loss {loss_sum/step_tokens:.4f} | lr {lr_at(step-1):.2e} "
          f"| tokens {seen:,}/{args.token_budget:,} | {time.time()-t0:.0f}s")

# ---------------------------------------------------------------- save (nanochat layout)
os.makedirs(args.out, exist_ok=True)
torch.save(model.state_dict(), os.path.join(args.out, f"model_{step:06d}.pt"))
meta["sft_round2"] = vars(args) | {"steps": step, "supervised_tokens": seen}
json.dump(meta, open(os.path.join(args.out, f"meta_{step:06d}.json"), "w"), indent=2)
print("saved to", args.out)
