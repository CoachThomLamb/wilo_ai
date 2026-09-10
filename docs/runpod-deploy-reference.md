# RunPod Deployment Reference

## 1. SSH Auth with GitHub

```bash
ssh-keygen -t ed25519
cat ~/.ssh/id_ed25519.pub | wl-copy  # Linux/Wayland
```

GitHub → Settings → SSH and GPG Keys → New SSH Key → paste.

Update repo remote to SSH:
```bash
git remote set-url origin git@github.com:yourusername/yourrepo.git
```

---

## 2. Spin Up a Pod

- Go to RunPod → create pod with PyTorch template
- Add your SSH public key in RunPod settings
- Grab the SSH connection string from the pod dashboard:
```
ssh root@38.80.152.148 -p 30365 -i ~/.ssh/id_ed25519
```

---

## 3. Deploy Code

```bash
scp -P 30365 -i ~/.ssh/id_ed25519 train_gpt2.py root@38.80.152.148:/workspace/
```

Convert notebook first if needed:
```bash
pip install jupytext
jupytext --to notebook train_gpt2.py
scp -P 30365 -i ~/.ssh/id_ed25519 train_gpt2.ipynb root@38.80.152.148:/workspace/
```

Working directory on the pod: `/workspace/`

---

## 4. Compare Against a Reference Repo

```bash
git remote add karpathy git@github.com:karpathy/build-nanogpt.git
git fetch karpathy
git diff -w karpathy/master -- train_gpt2.py  # -w ignores whitespace
```

---

## 5. Portable Device Detection

```python
device = "cpu"
if torch.cuda.is_available():
    device = "cuda"
elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
    device = "mps"
print(f"using device: {device}")
```

---

## 6. HuggingFace Model Downloads

Point cache to `/workspace` to avoid filling the root filesystem:

```bash
export HF_HOME=/workspace/hf_cache
```

Or at the top of your script before any imports:
```python
import os
os.environ["HF_HOME"] = "/workspace/hf_cache"
```

Clear failed downloads:
```bash
rm -rf /workspace/hf_cache/hub/models--<ModelName>*
```
