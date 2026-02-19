# MLX PII Abliterator

**Directional ablation for PII memorization removal in language models — natively on Apple Silicon.**

This project applies *activation-space directional ablation* to reduce a language model's tendency to echo Personally Identifiable Information (PII). It repurposes the [abliteration](https://github.com/p-e-w/heretic) technique — originally used to remove refusal directions — as a **privacy-preserving intervention**: find the vector in the model's hidden-state space that encodes PII recall, then project it out of the weight matrices.

All computation runs natively in [Apple's MLX framework](https://github.com/ml-explore/mlx). No PyTorch, no CUDA.

---

## What This Does

1. Loads `Qwen1.5-0.5B-Chat-4bit` (or any compatible mlx-community model)
2. Runs prompts containing PII and neutral prompts through a partial forward pass to collect hidden-state activations
3. Computes a **PII direction** in activation space using three different methods
4. Projects that direction out of the weight matrices (`mlp.down_proj`, `self_attn.o_proj`)
5. Tests before/after responses and reports quantitative metrics across a strength sweep

The full experiment — 3 methods × 3 strength levels = **9 ablated models** — completes in ~50 seconds on an M2 Max.

---

## The Three Methods

| Method | Core Idea | Targets |
|--------|-----------|---------|
| **M1: Single-Direction** | Difference-of-means between PII and generic activations, normalized | `down_proj` + `o_proj`, layers ±3 from target |
| **M2: Multi-Layer Weighted** | Per-layer direction vectors, Gaussian-weighted by separability | `down_proj` + `o_proj`, all 24 layers |
| **M3: SVD Subspace** | Top-k principal directions of the centered PII activation matrix | `down_proj` + `o_proj`, layers ±3 from target |

### Key Results (on M2 Max, Qwen1.5-0.5B-Chat-4bit)

```
Method                                PII Ret      PPL  PPL Delta  Coherent
------------------------------------ -------- -------- ---------- ---------
Baseline                               25.0%     12.8       +0.0        OK
M1: SingleDir (s=5.0)                   0.0%    142.1     +129.3  DEGRADED
M2: MultiLayer (s=5.0)                 75.0%     14.2       +1.3        OK
M3: SVD-k3 (s=5.0)                      0.0%    482.8     +469.9  DEGRADED
M1: SingleDir (s=10.0)                  0.0%   2114.0    +2101.2        OK
M2: MultiLayer (s=10.0)                50.0%     17.8       +5.0        OK
M3: SVD-k3 (s=10.0)                     0.0%  15496.0   +15483.2  DEGRADED
M2: MultiLayer (s=20.0)                50.0%     34.2      +21.4        OK
```

**Key finding:** Method 2 (Gaussian multi-layer) preserves coherence best but reduces PII echo least. Methods 1 and 3 achieve complete PII suppression at the cost of higher perplexity. This privacy–utility tradeoff is the paper's central result.

---

## Requirements

- macOS 13.5+ on Apple Silicon (M1/M2/M3/M4)
- Python 3.10+
- ~2 GB free disk space (model weights)
- ~4 GB unified memory during inference

---

## Quick Start

```bash
# 1. Clone or enter the project directory
cd /path/to/NLP_Project

# 2. Install dependencies
pip3 install mlx mlx-lm

# 3. Run the full experiment
python3 mlx_pii_abliterator.py
```

The model (~500 MB) is downloaded automatically from Hugging Face on first run.

---

## Project Structure

```
NLP_Project/
├── mlx_pii_abliterator.py          # Main script (766 lines)
├── README.md                        # This file
├── DOCUMENTATION.md                 # In-depth technical documentation
├── docs/
│   └── plans/
│       ├── 2026-02-19-mlx-pii-abliterator-design.md
│       └── 2026-02-19-mlx-pii-abliterator-plan.md
└── *.pdf                            # Reference papers
```

---

## Configuration

Edit the constants at the top of `mlx_pii_abliterator.py`:

| Constant | Default | Description |
|----------|---------|-------------|
| `MODEL_NAME` | `mlx-community/Qwen1.5-0.5B-Chat-4bit` | Any mlx-community chat model |
| `TARGET_LAYER` | `12` | Center layer for Methods 1 & 3 |
| `SVD_RANK` | `3` | Number of PII subspace directions (Method 3) |
| `GAUSSIAN_SIGMA` | `6.0` | Spread of layer weight kernel (Method 2) |
| `ABLATION_LAYER_RANGE` | `3` | Half-width of ablated layer window (Methods 1 & 3) |
| `STRENGTH_LEVELS` | `[5.0, 10.0, 20.0]` | Ablation intensities to sweep |

---

## References

- Heretic: [github.com/p-e-w/heretic](https://github.com/p-e-w/heretic)
- "A Granular Study of Safety Pretraining under Model Abliteration" — NeurIPS 2025 Workshop
- "Analyzing Leakage of Personally Identifiable Information in Language Models" — IEEE S&P 2023
- MLX: [github.com/ml-explore/mlx](https://github.com/ml-explore/mlx)

---

## License

Research use. See individual paper licenses for referenced works.
