# Rutgers iLabs GPU Experiments Guide

> What we can do with 30-hour GPU batch jobs on Rutgers iLabs — and how to run them.

---

## What iLabs Gives Us

The Rutgers CS iLab/rLab cluster provides access to research-grade NVIDIA GPUs via SLURM. Key specs relevant to our project:

### GPU Hardware Available

| GPU | Count | VRAM | Architecture | Best For |
|-----|-------|------|-------------|----------|
| RTX A6000 | 8 | 48 GB | Ampere | Full-precision 7B–13B models |
| RTX A5000 | 4 | 24 GB | Ampere | 7B models, large batches |
| RTX A4500 ADA | 11 | 24 GB | Ada Lovelace | Fast 7B inference |
| RTX A4500 | 16 | 20 GB | Ampere | 3B–7B models |
| RTX A4000 | 32 | 16 GB | Ampere | 1B–3B models, our Qwen 0.5B |

**Total:** 71 GPUs across iLab1-4 and rLab1-7 servers. Each server has 512 GB–1.5 TB RAM.

### Job Limits

| Resource | Limit |
|----------|-------|
| Max GPUs per job | 4 |
| Max memory per job | ~1 TB (via `--mem`) |
| Max job duration | 7 days (168 hours) |
| **Batch window we have** | **30 hours** |

---

## Why This Changes Everything for Our Project

On Apple Silicon (M2 Max, 32 GB unified), we are limited to:
- 4-bit quantized models (Qwen 1.5 0.5B, Qwen 2.5 14B)
- ~50 seconds per 9-experiment sweep
- No multi-GPU parallelism
- Can't run full-precision 7B+ models

On iLabs (RTX A6000, 48 GB VRAM), we can:
- Run **full-precision (fp16/bf16) Llama 3 8B** without quantization
- Run **Qwen 2.5 14B in fp16** natively
- Run **Llama 3 70B in 4-bit** (fits on 4x A6000 = 192 GB VRAM)
- **Parallelize** across 4 GPUs simultaneously
- Run **100+ strength sweep configurations** in a single 30-hour batch
- **Abliterate and evaluate** using full HuggingFace Transformers (not just MLX)

---

## Experiments to Run in 30 Hours

### Experiment 1: Scale to Full-Precision Models (High Priority)

Our MLX results use 4-bit quantization, which adds noise and forces `strength > 1`. On iLabs with A6000 GPUs, we can run the same abliteration on **fp16 models**, getting cleaner scientific results.

**Models to target:**
- `meta-llama/Meta-Llama-3-8B-Instruct` (fp16, ~16 GB VRAM)
- `Qwen/Qwen2.5-7B-Instruct` (fp16, ~14 GB VRAM)
- `mistralai/Mistral-7B-Instruct-v0.3` (fp16, ~14 GB VRAM)

**Expected time:** 2–4 hours per model × 3 models = ~12 hours

**Why it matters for the paper:** Quantization noise is a confound in our current results. Full-precision abliteration at `strength=1.0` gives us clean orthogonal projection results — a much stronger scientific claim.

---

### Experiment 2: Comprehensive Strength Sweep (Critical for Paper)

Currently we only test `strength ∈ {5.0, 10.0, 20.0}`. A proper paper needs a fine-grained curve.

**Proposed sweep:** `strength ∈ {0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 7.5, 10.0, 15.0, 20.0, 30.0, 50.0}`

For each strength:
- All 3 methods (SingleDir, MultiLayer, SVD)
- All 3 models (Llama 8B, Qwen 7B, Mistral 7B)
- Full PII retention + perplexity + MMLU evaluation

**Total configs:** 12 strengths × 3 methods × 3 models = **108 experiments**

**Expected time:** ~15 minutes each (fp16 inference) × 108 = ~27 hours → fits in 30-hour batch!

**Why it matters:** This produces the continuous privacy–utility tradeoff curve that is the central figure of the paper. Currently our curve has only 3 points.

---

### Experiment 3: SVD Rank Ablation Study

Currently `SVD_RANK = 3` for small models and `SVD_RANK = 8` for large models. We picked these somewhat arbitrarily.

**Proposed sweep:** `rank ∈ {1, 2, 3, 5, 8, 16, 32, 64}` across Llama 8B

**Questions to answer:**
- What's the minimum rank needed to suppress PII?
- At what rank does utility start degrading?
- Is there a "PII subspace dimensionality" that's consistent across models?

**Expected time:** ~3 hours

---

### Experiment 4: Cross-Model Transferability (Novel Contribution)

Does a PII direction computed on Llama 8B transfer to Mistral 7B? Both use similar architectures. If PII directions transfer, it suggests a universal structure in how LLMs encode PII.

**Setup:**
1. Compute PII direction on Llama 8B
2. Apply it to Mistral 7B (after alignment via CKA or linear map)
3. Measure PII retention on Mistral

**Expected time:** ~4 hours

**Why it matters:** Transfer of abliteration directions would be a genuinely novel finding. No prior work (including Heretic) has studied cross-model direction transfer.

---

### Experiment 5: Broader Evaluation — MMLU, TruthfulQA, HellaSwag

Our current evaluation uses a homegrown 40-question MMLU subset. Standard benchmarks would make the paper much more credible.

**Benchmarks to run:**
- **MMLU** (full, 57 subjects, ~14k questions) — general knowledge
- **TruthfulQA** — tests model honesty/coherence
- **HellaSwag** — commonsense reasoning

Run baseline and abliterated versions of each model.

**Expected time:** ~6 hours total across 3 benchmarks × 3 models

---

### Experiment 6: Differential Privacy Baseline (For Comparison)

To position our work against existing defenses, we should compare to DP-SGD fine-tuning on a sample of the PII prompts.

**Setup:**
1. Fine-tune Qwen 7B with DP-SGD (ε = 1, 3, 8) on a PII dataset
2. Measure PII retention + perplexity on the DP-fine-tuned models
3. Plot on the same privacy–utility curve as our abliteration results

**Expected time:** ~5 hours (DP fine-tuning is slow but 7B is manageable)

**Why it matters:** This is the comparison reviewers will demand. It contextualizes our tradeoff numbers against the gold-standard baseline.

---

## SLURM Setup: How to Run on iLabs

### Step 1: SSH into iLabs

```bash
ssh <netid>@ilab1.cs.rutgers.edu
# or ilab2, ilab3, ilab4, rlab1-rlab7
```

### Step 2: Check Available GPUs

```bash
sinfo -o "%25N %50f"       # list nodes and their GPU features
snodes                      # summary of all nodes
squeue                      # see currently running jobs
```

### Step 3: Set Up Python Environment

```bash
module load python/3.11     # or whatever version is available
python3 -m venv ~/nlp_env
source ~/nlp_env/bin/activate
pip install torch transformers accelerate datasets tqdm evaluate
pip install lm-eval          # for MMLU/TruthfulQA/HellaSwag
```

### Step 4: Clone the Repo

```bash
cd ~
git clone https://github.com/Haadesx/NLP_Project.git
cd NLP_Project
```

### Step 5: Write SLURM Batch Scripts

#### Basic GPU job (single A6000, 30 hours):

```bash
#!/bin/bash -l
#SBATCH --job-name=pii_abliterate
#SBATCH --output=logs/abliterate_%j.out
#SBATCH --error=logs/abliterate_%j.err
#SBATCH --time=30:00:00
#SBATCH --mem=80G
#SBATCH --gres=gpu:1
#SBATCH -C a6000

source ~/nlp_env/bin/activate
cd ~/NLP_Project

python3 ilabs_sweep.py \
    --model meta-llama/Meta-Llama-3-8B-Instruct \
    --methods all \
    --strengths 0.5 1.0 1.5 2.0 3.0 5.0 7.5 10.0 15.0 20.0 30.0 50.0 \
    --output results/llama8b_sweep.json
```

#### 4-GPU parallel job (for 70B models):

```bash
#!/bin/bash -l
#SBATCH --job-name=pii_llama70b
#SBATCH --output=logs/llama70b_%j.out
#SBATCH --time=30:00:00
#SBATCH --mem=256G
#SBATCH --gres=gpu:4
#SBATCH -C a6000

source ~/nlp_env/bin/activate
cd ~/NLP_Project

python3 ilabs_sweep.py \
    --model meta-llama/Meta-Llama-3-70B-Instruct \
    --load-in-4bit \
    --methods svd \
    --strengths 1.0 2.0 5.0 10.0 \
    --output results/llama70b_sweep.json
```

#### Submit and monitor:

```bash
sbatch job.sh                    # submit
squeue -u $USER                  # check status
tail -f logs/abliterate_12345.out  # watch live output
scancel <jobid>                  # cancel if needed
```

---

## PyTorch Implementation Needed for iLabs

Our current codebase uses MLX (Apple Silicon only). For iLabs, we need a **PyTorch version** of the abliterator. The math is identical — only the framework changes.

Key differences to implement:

| Operation | MLX (current) | PyTorch (iLabs) |
|-----------|---------------|-----------------|
| Load model | `mlx_lm.load()` | `AutoModelForCausalLM.from_pretrained()` |
| Activation hook | Manual loop | `register_forward_hook()` |
| SVD | `mx.linalg.svd(D, stream=mx.cpu)` | `torch.linalg.svd(D)` |
| Outer product | `mx.outer(v, v @ W)` | `torch.outer(v, v @ W)` |
| Dequantize | `mx.dequantize(...)` | Use `bitsandbytes` or load `float16` directly |
| Causal mask | `create_attention_mask(h)` | Built into `model.forward(attention_mask=...)` |
| Weight assign | `module.weight = w_q` | `module.weight.data.copy_(W_new)` |

The PyTorch version is also necessary to compare against DP-SGD baselines (Experiment 6), which require gradient access.

---

## Expected Paper Contributions from iLabs Experiments

| Experiment | Adds to Paper |
|-----------|---------------|
| Full-precision models | Removes quantization confound; cleaner Method 1 results |
| Strength sweep (108 configs) | Main privacy-utility tradeoff figure |
| SVD rank study | Ablation section; "minimum effective subspace dimensionality" |
| Cross-model transfer | Potential major finding: universal PII directions |
| Standard benchmarks | Credibility; comparison to prior work |
| DP-SGD baseline | Contextualization against gold-standard defense |

---

## Recommended 30-Hour Job Allocation

| Hours | Task |
|-------|------|
| 0–4 | Environment setup, model downloads, smoke tests |
| 4–19 | Experiment 2: Full strength sweep (108 configs) |
| 19–22 | Experiment 3: SVD rank ablation on Llama 8B |
| 22–26 | Experiment 5: MMLU/TruthfulQA/HellaSwag on 3 models |
| 26–30 | Experiment 4: Cross-model transfer + results collection |

*Experiment 6 (DP baseline) requires a separate job — it needs gradient access and is slow. Submit as a separate 30-hour batch.*

---

## Resources

- [iLabs GPU Scheduler Docs](https://resources.cs.rutgers.edu/docs/scheduler-for-gpu-jobs/)
- [iLabs Machine Status](https://report.cs.rutgers.edu/nagiosnotes/iLab-machines.html)
- [Rutgers CS Systems Summary](https://resources.cs.rutgers.edu/docs/computer-systems/summary-of-systems/)
- [Amarel HPC (larger jobs)](https://oarc.rutgers.edu/resources/amarel/)
