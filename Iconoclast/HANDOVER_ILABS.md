# ICONOCLAST — iLabs Cluster Handover & Session State

> **Last updated:** 2026-04-22 09:10 EDT
> **Session objective:** Scale ICONOCLAST benchmarks to 11+ open-source models for publishable results

---

## 1. What Is Running Right Now

### Active SLURM Jobs (as of 22:05 EDT)

| Job ID | Model / Script | Status | Node | Notes |
|--------|----------------|--------|------|-------|
| **130619** | Qwen 3.5-9B (Base) | RUNNING | rlab2 | Re-running with `set_submodule` patch. |
| **130618** | Qwen 2.5-3B (Base) | RUNNING | rlab7 | Continuing from earlier. |
| **130620** | **ICONOCLAST Sequential Sweep** | RUNNING | ilab2 | Runs 7 models one-by-one. |
| **130621** | **HERETIC Sequential Sweep** | PENDING | (Dep) | Waits for 130620 to finish. Runs baselines. |
| **130640** | **Large-N Evaluator Sweep** | PENDING | (Dep) | Waits for 130621 to finish. Evaluates best parameters on 520 prompts. |

### Sequential Runner (Job 130620) — Models in Order

This job runs **7 models one after another**, cleaning up disk cache between each:

1. `google/gemma-2-2b-it` → run name `gemma2-2b-seq`
2. `mistralai/Mistral-7B-Instruct-v0.3` → run name `mistral-7b-seq`
3. `microsoft/Phi-4-mini-instruct` → run name `phi4-mini-seq`
4. `stabilityai/stablelm-2-zephyr-1_6b` → run name `stablelm2-1p6b-seq`
5. `01-ai/Yi-1.5-9B-Chat` → run name `yi-1p5-9b-seq`
6. `tiiuae/Falcon3-7B-Instruct` → run name `falcon3-7b-seq`
7. `allenai/OLMo-2-0425-1B-Instruct` → run name `olmo2-1b-seq`

**Log file:** `~/iconoclast/logs/iconoclast-seq-130620.out`

---

## 2. Completed Results (from prior sessions)

These models already have `batch_summary.json` files on the cluster:

| Model | Run Name | Checkpoint Dir | Verdict |
|-------|----------|----------------|---------|
| Qwen3-1.7B | `qwen3-1p7b-rutgers-paper-directness` | `/common/users/vp752/iconoclast_ilabs/checkpoints/qwen3-1p7b-rutgers-paper-directness/` | **ICONOCLAST** |
| Qwen2.5-3B-Instruct | `qwen2-5-3b-rutgers-benchmark` | `/common/users/vp752/iconoclast_ilabs/checkpoints/qwen2-5-3b-rutgers-benchmark/` | **ICONOCLAST** |
| Qwen3-4B-Instruct | `qwen3-4b-rutgers-benchmark-v2` | `/common/users/vp752/iconoclast_ilabs/checkpoints/qwen3-4b-rutgers-benchmark-v2/` | **ICONOCLAST** |
| Phi-3.5-mini-instruct | `phi35-mini-rutgers-nullspace-benchmark-v3` | `/common/users/vp752/iconoclast_ilabs/checkpoints/phi35-mini-rutgers-nullspace-benchmark-v3/` | **ICONOCLAST** |

### Current Scorecard (4-0 from prior sessions)

| Model | ICONOCLAST Refusals | ICONOCLAST Overrefusals | ICONOCLAST KL | HERETIC Refusals | HERETIC Overrefusals | HERETIC KL | Verdict |
|---|---|---|---|---|---|---|---|
| **Qwen3-1.7B** | 0/48 | 0/48 | 0.0310 | 3/48 | 0/48 | 0.0332 | **ICONOCLAST** |
| **Qwen2.5-3B** | 2/20 | 1/64 | 0.0943 | 2/20 | 1/64 | 0.3257 | **ICONOCLAST** |
| **Qwen3-4B** | 2/20 | 0/64 | 0.7976 | 3/20 | 1/64 | 0.0996 | **ICONOCLAST** |
| **Phi-3.5-mini** | 3/20 | 2/64 | 0.0981 | 7/20 | 2/64 | 0.2492 | **ICONOCLAST** |

---

## 3. Pending Results (waiting for jobs to finish)

Once the running jobs complete, their results will appear as `batch_summary.json` files in:
```
/common/users/vp752/iconoclast_ilabs/checkpoints/<run-name>/batch_summary.json
```

### Models pending results:

| Model | Run Name | Quant | Expected Checkpoint |
|-------|----------|-------|---------------------|
| Llama-3.1-8B-Instruct | `llama3-1-8b-rutgers-benchmark` | bnb_4bit | `checkpoints/llama3-1-8b-rutgers-benchmark/` |
| SmolLM2-1.7B-Instruct | `smollm2-1p7b-rutgers-benchmark` | none | `checkpoints/smollm2-1p7b-rutgers-benchmark/` |
| Gemma-2-2B-IT | `gemma2-2b-seq` | none | `checkpoints/gemma2-2b-seq/` |
| Mistral-7B-Instruct-v0.3 | `mistral-7b-seq` | bnb_4bit | `checkpoints/mistral-7b-seq/` |
| Phi-4-mini-instruct | `phi4-mini-seq` | none | `checkpoints/phi4-mini-seq/` |
| StableLM-2-Zephyr-1.6B | `stablelm2-1p6b-seq` | none | `checkpoints/stablelm2-1p6b-seq/` |
| Yi-1.5-9B-Chat | `yi-1p5-9b-seq` | bnb_4bit | `checkpoints/yi-1p5-9b-seq/` |
| Falcon3-7B-Instruct | `falcon3-7b-seq` | bnb_4bit | `checkpoints/falcon3-7b-seq/` |
| OLMo-2-1B-Instruct | `olmo2-1b-seq` | none | `checkpoints/olmo2-1b-seq/` |

---

## 4. How to Check Status

### SSH into the cluster
```bash
ssh vp752@ilab.cs.rutgers.edu
```

### Check running jobs
```bash
squeue -u vp752
```

### Check job history (completed/failed)
```bash
sacct -u vp752 --starttime=2026-04-21 --format=JobID%10,JobName%15,State%12,ExitCode,Elapsed%10
```

### Tail the sequential runner log
```bash
tail -f ~/iconoclast/logs/iconoclast-seq-130468.out
```

### Tail a specific job's log
```bash
tail -f ~/iconoclast/logs/iconoclast-<JOBID>.out
tail -f ~/iconoclast/logs/iconoclast-<JOBID>.err
```

### List all batch_summary.json files (completed benchmarks)
```bash
find /common/users/vp752/iconoclast_ilabs/checkpoints/ -name batch_summary.json
```

### Generate the comparison table (once results exist)
```bash
python3 ~/iconoclast/scripts/summarize_multimodel_benchmark.py \
  --spec "ModelName|/path/to/iconoclast/batch_summary.json|/path/to/heretic/batch_summary.json"
```

---

## 5. Known Issues & Fixes Applied

### Disk Quota
- **Problem:** Concurrent jobs all downloading models simultaneously blow the per-user quota on `/common/users/vp752/`.
- **Fix:** Created `scripts/run_sequential_benchmark.slurm` which runs models one-at-a-time and `rm -rf` the cache between each.
- **Key:** Never run more than ~2 model downloads concurrently.

### Transformers Version
- **Upgraded to `transformers==5.5.4`** (from 4.57.6) to support `qwen3_5` architecture.
- Also upgraded `huggingface_hub==1.11.0`, `tokenizers==0.22.2`, plus new deps `typer`, `annotated-doc`, `shellingham`, `click`.
- Installed via `--no-deps` to avoid pulling in a new PyTorch/CUDA stack that would blow disk quota.
- **Risk:** The new transformers v5 may have breaking changes for some older model architectures. If a model fails with `Failed to load model with all configured dtypes`, check if it's an architecture compatibility issue.

### Quantization
- Only `"none"` and `"bnb_4bit"` are supported by ICONOCLAST's config validator.
- Models >4B params need `bnb_4bit` to fit on RTX A4000 (16GB) / A5000 (22GB).
- `bitsandbytes` is installed in the site-packages.

### HF Token
- **`HF_TOKEN`** is set in `scripts/run_rutgers_ilabs.slurm` (line 51) and in the sequential runner.
- Required for gated repos like `meta-llama/Llama-3.1-8B-Instruct` and `google/gemma-2-2b-it`.

### Qwen2.5-3B (Base) — Job 130448
- Ran for 31 minutes, produced trial data, but crashed with `AssertionError: Should not reach.` in Optuna.
- The Optuna study DB may have partial results. Check if `batch_summary.json` was written before crash.
- Last observed metrics: KL=0.0408, Refusals=1/20, Overrefusals=3/64 (excellent).

### Qwen3.5-9B (Base) & Mistral-7B
- **Problem:** `transformers v5.5.4` removed/changed internal methods, causing `'Qwen3_5ForConditionalGeneration' object has no attribute 'set_submodule'` and similar errors for Mistral.
- **Fix:** Applied a monkey-patch to `torch.nn.Module` in `src/iconoclast/model.py` that injects `set_submodule` if missing.
- **Status:** Qwen 3.5-9B is currently re-running as Job **130619**.

### Gemma-2-2B (Chat Template)
- **Problem:** Gemma 2 chat template does not support the "system" role, causing crashes during evaluation.
- **Fix:** Updated `Model.generate` in `src/iconoclast/model.py` to automatically merge system prompts into the first user message if the chat template fails.
- **Status:** Currently being retried in the sequential runner (Job **130620**).

---

## 6. Key File Locations

### Local (your Mac)
```
/Volumes/Auxilary/Side_Projects/NLP_PROJECT_NEW/iconoclast/
├── PUBLISHABLE_RESULTS.md          # Draft paper with results table
├── HANDOVER_ILABS.md               # This file
├── config.*.benchmark.rutgers.toml # All model configs
├── scripts/
│   ├── run_rutgers_ilabs.slurm             # Single-model SLURM script
│   ├── run_sequential_benchmark.slurm      # Multi-model sequential runner
│   ├── setup_rutgers_env.sh                # Environment bootstrap
│   ├── sync_to_rutgers.sh                  # rsync to cluster
│   ├── summarize_multimodel_benchmark.py   # Results aggregator
│   └── bootstrap_and_submit_rutgers_*.sh   # Per-model submit scripts
└── src/iconoclast/
    ├── main.py        # Core pipeline (Optuna objective, ablation loop)
    ├── direction.py   # Null-space projection (dampening factor)
    └── model.py       # Model loading & weight editing
```

### Remote (iLabs cluster)
```
/common/home/vp752/iconoclast/              # Project source (synced from local)
/common/users/vp752/iconoclast_ilabs/       # Persistent storage root
├── bootstrap-venv/                         # Python venv for pip
├── python312-site/                         # All pip packages (transformers, optuna, etc.)
├── checkpoints/                            # Optuna study DBs + batch_summary.json
│   ├── qwen3-1p7b-rutgers-paper-directness/
│   ├── qwen2-5-3b-rutgers-benchmark/
│   ├── qwen3-4b-rutgers-benchmark-v2/
│   ├── phi35-mini-rutgers-nullspace-benchmark-v3/
│   ├── llama3-1-8b-rutgers-benchmark/      # Pending
│   ├── smollm2-1p7b-rutgers-benchmark/     # Pending
│   ├── gemma2-2b-seq/                      # Pending (sequential)
│   ├── mistral-7b-seq/                     # Pending (sequential)
│   └── ... (more from sequential runner)
├── job-stage/                              # Temporary per-job project copies
└── job-cache/                              # Temporary per-job HF model downloads
```

---

## 7. What To Do Next

### Step 1: Check if jobs finished
```bash
ssh vp752@ilab.cs.rutgers.edu
squeue -u vp752
sacct -u vp752 --starttime=2026-04-21
```

### Step 2: List all completed results
```bash
find /common/users/vp752/iconoclast_ilabs/checkpoints/ -name batch_summary.json -newer /common/users/vp752/iconoclast_ilabs/checkpoints/phi35-mini-rutgers-nullspace-benchmark-v3/batch_summary.json
```

### Step 3: Run Qwen3.5-9B if disk is free
```bash
# Clean old caches first
rm -rf /common/users/vp752/iconoclast_ilabs/job-cache/*
# Then submit
cd ~/iconoclast
ICONOCLAST_CONFIG_TEMPLATE=config.qwen3_5_9b_base.benchmark.rutgers.toml \
ICONOCLAST_RUN_NAME=qwen3-5-9b-base-rutgers-benchmark-v2 \
sbatch scripts/run_rutgers_ilabs.slurm
```

### Step 4: Verify the HERETIC Baselines
To prove ICONOCLAST is better, we need a side-by-side comparison with the standard HERETIC ablation (orthogonal ablation without null-space projection).
- `scripts/run_heretic_baselines.slurm` is queued to run automatically after the main sweep.
- It will produce `batch_summary.json` files for all HERETIC models.

### Step 5: Large-N Evaluation (520 Prompts)
To provide statistically significant proof, we evaluate the best trial configurations on a 520-prompt holdout set (`mlabonne/harmful_behaviors`).
- `scripts/run_large_eval_sweep.slurm` is queued to run automatically after the HERETIC baselines.
- The results for each model will be written to `/common/users/vp752/iconoclast_ilabs/large_evals/<model-name>_large_eval.json`.

### Step 6: Generate the final comparison table
```bash
python3 ~/iconoclast/scripts/summarize_multimodel_benchmark.py \
  --spec "Qwen3-1.7B|.../iconoclast/batch_summary.json|.../heretic/batch_summary.json" \
  # ... one --spec per model
```

### Step 6: Update PUBLISHABLE_RESULTS.md
Fill in the pending rows in the results table with actual numbers.

### Step 7: Write the in-depth analysis
Key questions to answer:
1. **Scaling hypothesis:** Does KL divergence decrease with model size? (Compare 1B vs 3B vs 8B vs 9B)
2. **Architecture universality:** Does ICONOCLAST work across Qwen, Llama, Gemma, Mistral, Phi, etc.?
3. **Base vs Instruct:** Is the raw base model easier to edit than the RLHF-aligned instruct model?

---

## 8. Environment Variables Reference

| Variable | Purpose |
|----------|---------|
| `ICONOCLAST_CONFIG_TEMPLATE` | Which `.toml` config file to use |
| `ICONOCLAST_RUN_NAME` | Unique name for the Optuna study (changing this forces a fresh study) |
| `ICONOCLAST_EXIT_AFTER_OPTIMIZATION` | Set `true` for batch mode (no interactive menu) |
| `ICONOCLAST_STUDY_CHECKPOINT_DIR` | Where Optuna DB + batch_summary.json are saved |
| `HF_TOKEN` | HuggingFace token for gated repos |
| `PERSIST_ROOT` | `/common/users/vp752/iconoclast_ilabs` |

---

## 9. Quick Reference Commands

```bash
# Sync local changes to cluster
./scripts/sync_to_rutgers.sh

# Submit a single model benchmark
ICONOCLAST_CONFIG_TEMPLATE=config.xxx.toml \
ICONOCLAST_RUN_NAME=xxx-benchmark \
sbatch scripts/run_rutgers_ilabs.slurm

# Submit the sequential 7-model runner
sbatch scripts/run_sequential_benchmark.slurm

# Cancel a job
scancel <JOBID>

# Check disk usage
du -sh /common/users/vp752/iconoclast_ilabs/job-cache/

# Clean up all caches (only when no jobs are running!)
rm -rf /common/users/vp752/iconoclast_ilabs/job-cache/*
rm -rf /common/users/vp752/iconoclast_ilabs/job-stage/*
```
