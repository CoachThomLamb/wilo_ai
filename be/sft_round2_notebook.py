# %% [markdown]
# # SFT Round 2 — nanochat Coaching Fine-Tune
#
# Fine-tunes a pretrained nanochat checkpoint on your own conversation data.
# Run twice — once with generic data (baseline), once with coaching data — and compare.
#
# **Data format (JSONL):**
# ```json
# {"messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
# ```

# %% [markdown]
# ## 0. Setup — clone nanochat and install dependencies

# %%
import os
if not os.path.exists("/workspace/nanochat"):
    os.system("git clone https://github.com/karpathy/nanochat /workspace/nanochat")
os.system("pip install -e /workspace/nanochat[cpu] -q")
print("nanochat ready.")

# %% [markdown]
# ## 1. Config — set these before running

# %%
import sys

# Path to the nanochat repo
NANOCHAT_DIR = "/workspace/nanochat"
sys.path.insert(0, NANOCHAT_DIR)

# Checkpoint to start from
CKPT_DIR  = "/workspace/checkpoints/base"   # dir containing model_XXXXXX.pt + meta_XXXXXX.json
CKPT_STEP = 10000                            # the XXXXXX in the filenames

# Tokenizer
TOKENIZER_DIR = "/workspace/tokenizer"      # dir containing tokenizer.pkl

# Data — swap between arms
DATA_PATH = "/workspace/coaching.jsonl"     # or generic.jsonl for baseline arm

# Output — use different dirs for each arm
OUT_DIR = "/workspace/sft_out/coaching"

# Training hyperparams — keep these IDENTICAL across both arms
TOKEN_BUDGET = 2_000_000   # total supervised tokens to train on
BATCH_TOKENS = 32_000      # tokens per optimizer step
MICRO_BS     = 4           # conversations per forward pass
SEQ_LEN      = 2048
LR           = 2e-5
SEED         = 1337

print("Config ready.")

# %% [markdown]
# ## 2. Imports and GPU check

# %%
import json, math, os, random, time
import torch
import torch.nn.functional as F

from nanochat.gpt import GPT, GPTConfig
from nanochat.tokenizer import RustBPETokenizer

torch.manual_seed(SEED)
random.seed(SEED)
torch.backends.cuda.matmul.allow_tf32 = True

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Device: {device}")
if device == "cuda":
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
else:
    print("WARNING: no GPU detected — training will be very slow")

# %% [markdown]
# ## 3. Load the pretrained checkpoint
#
# Loads the model architecture from the meta file and fills in the weights.
# The `_orig_mod.` prefix stripping handles checkpoints saved after `torch.compile()`.

# %%
meta_path  = os.path.join(CKPT_DIR, f"meta_{CKPT_STEP:06d}.json")
model_path = os.path.join(CKPT_DIR, f"model_{CKPT_STEP:06d}.pt")

print(f"Meta:   {meta_path}")
print(f"Weights: {model_path}")

meta = json.load(open(meta_path))
print(f"\nModel config: {meta['model_config']}")

model = GPT(GPTConfig(**meta["model_config"]))
sd = torch.load(model_path, map_location="cpu")
sd = {k.removeprefix("_orig_mod."): v for k, v in sd.items()}
model.load_state_dict(sd, strict=True)
model.to(device).train()

n_params = sum(t.numel() for t in model.parameters()) / 1e6
print(f"\nLoaded. Parameters: {n_params:.0f}M")

# %% [markdown]
# ## 4. Load the tokenizer
#
# Loads from a pickle file — no Rust compilation needed at inference time.

# %%
print(f"Loading tokenizer from: {TOKENIZER_DIR}")
tok = RustBPETokenizer.from_directory(TOKENIZER_DIR)

S   = lambda name: tok.encode_special(name)
BOS = S("<|bos|>")
U0  = S("<|user_start|>")
U1  = S("<|user_end|>")
A0  = S("<|assistant_start|>")
A1  = S("<|assistant_end|>")

print(f"Vocab size: {tok.get_vocab_size():,}")
print(f"Special token IDs — BOS:{BOS} U0:{U0} U1:{U1} A0:{A0} A1:{A1}")

# %% [markdown]
# ## 5. Load and render the dataset
#
# Each conversation is tokenized and given a **loss mask**.
# The model only learns to predict assistant tokens — user turns are masked out (set to -1, ignored in loss).

# %%
def render(conv):
    ids, mask = [BOS], [0]
    for m in conv["messages"]:
        body = tok.encode(m["content"])
        if m["role"] == "user":
            chunk = [U0] + body + [U1]
            cmask = [0] * len(chunk)
        elif m["role"] == "assistant":
            chunk = [A0] + body + [A1]
            cmask = [0] + [1] * (len(body) + 1)  # learn body + end token
        else:
            continue
        ids += chunk
        mask += cmask
    return ids[:SEQ_LEN + 1], mask[:SEQ_LEN + 1]

print(f"Loading: {DATA_PATH}")
raw  = [json.loads(l) for l in open(DATA_PATH) if l.strip()]
data = [render(c) for c in raw]
data = [(i, m) for i, m in data if sum(m[1:]) > 0]  # drop empty examples

total_supervised = sum(sum(m[1:]) for _, m in data)
print(f"\nConversations:          {len(data)}")
print(f"Supervised tokens/epoch: {total_supervised:,}")
print(f"Epochs to hit budget:    {TOKEN_BUDGET / total_supervised:.1f}x")

# Preview
print("\n--- First conversation preview ---")
for msg in raw[0]["messages"][:4]:
    snippet = msg["content"][:120] + "..." if len(msg["content"]) > 120 else msg["content"]
    print(f"[{msg['role'].upper()}] {snippet}")

# %% [markdown]
# ## 6. Training
#
# Plain AdamW with linear LR decay to zero.
# Gradient accumulation runs until we've seen `BATCH_TOKENS` supervised tokens, then we step the optimizer.
# Loss is computed only on assistant tokens.

# %%
def batches():
    while True:
        random.shuffle(data)
        for i in range(0, len(data), MICRO_BS):
            yield data[i : i + MICRO_BS]

def collate(rows):
    T = max(len(ids) for ids, _ in rows) - 1
    x = torch.full((len(rows), T), BOS, dtype=torch.long)
    y = torch.full((len(rows), T), -1,  dtype=torch.long)
    for r, (ids, mask) in enumerate(rows):
        t  = torch.tensor(ids)
        mk = torch.tensor(mask, dtype=torch.bool)
        n  = len(ids) - 1
        x[r, :n] = t[:-1]
        tgt = t[1:].clone()
        tgt[~mk[1:]] = -1
        y[r, :n] = tgt
    return x.to(device), y.to(device)

opt         = torch.optim.AdamW(model.parameters(), lr=LR, betas=(0.9, 0.95), weight_decay=0.0)
total_steps = math.ceil(TOKEN_BUDGET / BATCH_TOKENS)
lr_at       = lambda s: LR * (1 - s / total_steps)

print(f"Steps:      {total_steps}")
print(f"LR:         {LR:.2e} → 0.0 (linear decay)")
print(f"Batch size: ~{BATCH_TOKENS:,} supervised tokens/step\n")

seen, step, it, t0 = 0, 0, batches(), time.time()
losses = []

while seen < TOKEN_BUDGET:
    for g in opt.param_groups:
        g["lr"] = lr_at(step)

    step_tokens, loss_sum = 0, 0.0
    opt.zero_grad(set_to_none=True)

    while step_tokens < BATCH_TOKENS:
        x, y = collate(next(it))
        n = int((y != -1).sum())
        with torch.autocast("cuda", dtype=torch.bfloat16):
            logits = model(x)
        loss = F.cross_entropy(
            logits.float().view(-1, logits.size(-1)),
            y.view(-1),
            ignore_index=-1,
            reduction="sum"
        )
        (loss / BATCH_TOKENS).backward()
        step_tokens += n
        loss_sum    += loss.item()

    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
    opt.step()
    seen += step_tokens
    step += 1

    avg_loss = loss_sum / step_tokens
    losses.append(avg_loss)
    elapsed  = time.time() - t0
    eta      = (elapsed / step) * (total_steps - step)
    print(f"step {step:03d}/{total_steps} | loss {avg_loss:.4f} | lr {lr_at(step-1):.2e} | {elapsed:.0f}s elapsed | ETA {eta:.0f}s")

print(f"\nDone. Total time: {time.time() - t0:.0f}s")

# %% [markdown]
# ## 7. Save checkpoint

# %%
os.makedirs(OUT_DIR, exist_ok=True)
model_out = os.path.join(OUT_DIR, f"model_{step:06d}.pt")
meta_out  = os.path.join(OUT_DIR, f"meta_{step:06d}.json")

torch.save(model.state_dict(), model_out)
meta["sft_round2"] = {
    "data":               DATA_PATH,
    "out":                OUT_DIR,
    "steps":              step,
    "supervised_tokens":  seen,
    "token_budget":       TOKEN_BUDGET,
    "lr":                 LR,
    "seed":               SEED,
}
json.dump(meta, open(meta_out, "w"), indent=2)

print(f"Saved to: {OUT_DIR}")
print(f"  model → {model_out}")
print(f"  meta  → {meta_out}")

# %% [markdown]
# ## 8. Sanity check — generate a response
#
# Use the same prompt for both arms so you can directly compare the outputs.

# %%
model.eval()

TEST_PROMPT = "I've been training for about a year. My bench is stuck at 135 lbs. What should I focus on to break through?"

ids = [BOS, U0] + tok.encode(TEST_PROMPT) + [U1, A0]
x   = torch.tensor([ids], dtype=torch.long).to(device)

print(f"User: {TEST_PROMPT}")
print(f"Assistant: ", end="", flush=True)

with torch.no_grad():
    for _ in range(300):
        logits     = model(x)
        next_token = logits[0, -1].argmax().item()
        if next_token == A1:
            break
        print(tok.id_to_token(next_token), end="", flush=True)
        x = torch.cat([x, torch.tensor([[next_token]], device=device)], dim=1)

print()
