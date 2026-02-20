# MLX PII Abliterator — Technical Documentation

## Table of Contents

1. [Overview](#overview)
2. [Step-by-Step Setup Guide](#step-by-step-setup-guide)
3. [How It Works](#how-it-works)
4. [Architecture Walkthrough](#architecture-walkthrough)
5. [The Three Ablation Methods](#the-three-ablation-methods)
6. [The Dequantize-Project-Requantize Pipeline](#the-dequantize-project-requantize-pipeline)
7. [Why the Causal Mask Matters](#why-the-causal-mask-matters)
8. [Metrics and Evaluation](#metrics-and-evaluation)
9. [Configuration Guide](#configuration-guide)
10. [Interpreting Results](#interpreting-results)
11. [Extending the Project](#extending-the-project)
12. [Known Limitations](#known-limitations)
13. [Troubleshooting](#troubleshooting)

---

## Overview

The MLX PII Abliterator applies **directional ablation** (also known as *abliteration*) to suppress a language model's tendency to echo Personally Identifiable Information (PII). The core idea comes from the observation that specific behaviors in transformer models — like recalling phone numbers or email addresses — are encoded along identifiable directions in the model's hidden-state space. By finding those directions and projecting them out of the weight matrices, we can selectively suppress PII recall while preserving general language capability.

This project adapts the abliteration technique pioneered by the [Heretic](https://github.com/p-e-w/heretic) tool (originally used for removing safety-alignment / refusal directions) and repurposes it for **privacy protection**. Instead of removing refusal vectors, we identify and remove **PII memorization vectors**.

Everything runs natively on Apple Silicon using the [MLX framework](https://github.com/ml-explore/mlx) — no PyTorch, no CUDA, no GPU drivers.

---

## Step-by-Step Setup Guide

### Prerequisites

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| macOS       | 13.5 (Ventura) | 14.0+ (Sonoma) |
| Chip        | Apple M1 | M2 Pro / M2 Max or later |
| RAM         | 8 GB unified | 16 GB+ unified |
| Python      | 3.10 | 3.11 or 3.12 |
| Disk space  | 2 GB free | 5 GB free |

### Step 1: Verify Python

```bash
python3 --version
# Should print Python 3.10.x or later
```

If you don't have Python 3.10+, install it via Homebrew:

```bash
brew install python@3.12
```

### Step 2: Clone the Repository

```bash
git clone https://github.com/Haadesx/NLP_Project.git
cd NLP_Project
```

### Step 3: Create a Virtual Environment (Recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 4: Install Dependencies

```bash
pip3 install mlx mlx-lm
```

That's it. Only two packages. MLX handles all the computation and `mlx-lm` provides the model loading and generation utilities.

### Step 5: Run the Full Experiment

```bash
python3 mlx_pii_abliterator.py
```

On first run, the model weights (~500 MB) are downloaded automatically from Hugging Face. Subsequent runs use the cached weights.

**Expected runtime:** ~50 seconds on M2 Max, ~90 seconds on M1.

### Step 6: Read the Output

The script prints:
1. Activation collection progress
2. PII direction computation stats
3. Baseline evaluation (before any ablation)
4. Per-method, per-strength evaluation results
5. A final comparison table summarizing all 9 experiments

---

## How It Works

The pipeline has five stages:

```
┌─────────────┐    ┌─────────────────┐    ┌──────────────────┐
│  Load Model  │───>│ Collect Hidden   │───>│ Compute PII      │
│  & Tokenizer │    │ State Activations│    │ Directions       │
└─────────────┘    └─────────────────┘    └──────────────────┘
                                                   │
                   ┌─────────────────┐    ┌────────▼─────────┐
                   │ Evaluate Before │<───│ Project Direction │
                   │ and After       │    │ Out of Weights    │
                   └─────────────────┘    └──────────────────┘
```

**Stage 1 — Load Model:** We load a 4-bit quantized Qwen 1.5 0.5B Chat model using `mlx_lm.load()`. The model is a `Qwen2Model` with 24 transformer layers, each containing multi-head attention and an MLP block.

**Stage 2 — Collect Activations:** We run two sets of prompts through the model — PII-containing prompts and neutral/generic prompts — using a partial forward pass through the transformer layers. We record the last-token hidden state at each layer, producing two activation matrices.

**Stage 3 — Compute PII Directions:** Using three different methods, we compute the direction(s) in hidden space that distinguish PII activations from generic activations.

**Stage 4 — Ablate Weights:** We project the PII direction(s) out of the weight matrices in targeted layers. For quantized models, this requires a dequantize → project → requantize pipeline.

**Stage 5 — Evaluate:** We test the ablated model on held-out PII prompts (measuring PII retention), held-out generic text (measuring perplexity), and generic prompts (measuring coherence).

---

## Architecture Walkthrough

### File Structure

The entire implementation lives in a single file: `mlx_pii_abliterator.py` (766 lines). Here's what each section does:

| Lines | Section | Purpose |
|-------|---------|---------|
| 1–28 | Header & imports | Docstring, `mlx.core`, `mlx_lm`, `create_attention_mask` |
| 29–41 | Configuration | Model name, layer targets, strength levels, hyperparameters |
| 42–125 | Prompt datasets | PII prompts (16), generic prompts (16), test prompts, regex patterns |
| 127–155 | Utilities | `load_model()`, `format_chat()`, `generate_response()` |
| 157–220 | Activation collection | `get_hidden_state()`, `get_all_layer_hidden_states()`, batch collectors |
| 222–295 | Direction computation | Methods 1, 2, and 3 for computing PII direction vectors |
| 297–458 | Weight ablation | Dequantize/requantize pipeline, three ablation functions |
| 460–556 | Metrics | PII retention, perplexity, coherence measurement |
| 558–656 | Evaluation & reporting | `evaluate_method()`, `print_results()` |
| 658–766 | Main | Orchestrates the full experiment pipeline |

### Key Imports

```python
import mlx.core as mx          # Array operations, lazy evaluation
import mlx.nn as nn             # Neural network modules (QuantizedLinear)
from mlx_lm import generate, load  # Model loading and text generation
from mlx_lm.models.base import create_attention_mask  # Causal mask creation
```

### Model Architecture (Qwen2)

```
Qwen2Model
├── model
│   ├── embed_tokens          → Token embedding layer
│   ├── layers[0..23]         → 24 transformer blocks
│   │   ├── self_attn
│   │   │   ├── q_proj        → Query projection (QuantizedLinear)
│   │   │   ├── k_proj        → Key projection (QuantizedLinear)
│   │   │   ├── v_proj        → Value projection (QuantizedLinear)
│   │   │   └── o_proj        → Output projection (QuantizedLinear) ← ABLATED
│   │   ├── mlp
│   │   │   ├── gate_proj     → Gate projection (QuantizedLinear)
│   │   │   ├── up_proj       → Up projection (QuantizedLinear)
│   │   │   └── down_proj     → Down projection (QuantizedLinear) ← ABLATED
│   │   ├── input_layernorm
│   │   └── post_attention_layernorm
│   ├── norm                  → Final RMSNorm
│   └── lm_head              → Language model head
```

We ablate `down_proj` and `o_proj` because these are the layers where hidden-state information is projected back into the residual stream — the points where PII recall gets written into the output.

---

## The Three Ablation Methods

### Method 1: Single-Direction Projection

**Idea:** Compute the mean activation for PII prompts and generic prompts at a target layer. The normalized difference vector points in the "PII direction."

**Math:**
```
v = normalize(mean(PII_activations) - mean(Generic_activations))
W_new = W - strength * v ⊗ (vᵀW)
```

The outer product `v ⊗ (vᵀW)` creates a rank-1 update matrix that, when subtracted from W, removes the component of W that projects along the PII direction. At `strength=1`, this is exact orthogonal projection. At `strength>1`, it over-projects — inverting the PII component — which helps overcome 4-bit quantization noise.

**Applied to:** `down_proj` and `o_proj` in layers `[target-3, target+3]` (7 layers total).

### Method 2: Multi-Layer Gaussian Weighted

**Idea:** Compute a per-layer PII direction vector and a "separability score" measuring how well that direction separates PII from generic activations. Then apply a Gaussian-weighted ablation across all 24 layers, concentrating effort near the layer with highest separability.

**Math:**
```
For each layer l:
  v_l = normalize(mean_pii_l - mean_generic_l)
  sep_l = 1 - cosine_similarity(mean_pii_l, mean_generic_l)

Gaussian weight at layer l:
  w(l) = strength * max_sep * exp(-0.5 * ((l - peak_layer) / sigma)^2)

W_new_l = W_l - w(l) * v_l ⊗ (v_lᵀ W_l)
```

This method is gentler because the Gaussian kernel tapers off at layers far from the peak, avoiding over-ablation in layers that don't encode PII.

### Method 3: SVD Subspace Ablation

**Idea:** PII information might not lie along a single direction — it could span a subspace. SVD finds the top-k principal directions of the centered PII activation matrix.

**Math:**
```
D = PII_activations - mean(Generic_activations)    # Center the PII data
U, S, Vᵀ = SVD(D)                                  # Must be float32
V_k = Vᵀ[:k, :].T                                  # Top-k right singular vectors

W_new = W - strength * V_k @ V_kᵀ @ W              # Rank-k subspace projection
```

This captures richer structure than Method 1's single vector but is more aggressive — it removes k directions simultaneously.

**Applied to:** `down_proj` and `o_proj` in layers `[target-3, target+3]`.

---

## The Dequantize-Project-Requantize Pipeline

The model uses 4-bit quantization (via `QuantizedLinear`), meaning weights are stored as packed integers with separate scale and bias arrays. To modify them:

```
1. Dequantize:  W_float = mx.dequantize(weight, scales, biases, group_size, bits)
2. Project:     W_modified = W_float - strength * v ⊗ (vᵀ W_float)
3. Requantize:  w_q, scales, biases = mx.quantize(W_modified, group_size, bits)
4. Assign:      module.weight = w_q; module.scales = scales; module.biases = biases
```

**Why strength > 1 is needed:** The requantization step introduces rounding noise. A small perturbation (strength=1) gets partially absorbed by this noise, reducing the effective ablation. Higher strength values compensate. In our experiments, strength=5.0 is the minimum for observable PII reduction.

---

## Why the Causal Mask Matters

During our development, we discovered that omitting the causal attention mask in the partial forward pass produces fundamentally different activations. Without the mask, each token attends to all other tokens (bidirectional), whereas during actual generation, each token can only attend to earlier tokens (causal/autoregressive).

**Measured impact:** The maximum element-wise difference between masked and unmasked activations was **66.5** — not a rounding error but a completely different representation.

The fix uses `create_attention_mask` from `mlx_lm.models.base`:

```python
from mlx_lm.models.base import create_attention_mask

h = model.model.embed_tokens(input_ids)
mask = create_attention_mask(h, cache=None)
for i, layer in enumerate(model.model.layers):
    h = layer(h, mask=mask, cache=None)
```

This ensures the hidden states we collect match what the model would compute during normal autoregressive inference.

---

## Metrics and Evaluation

### PII Retention

For each PII test prompt, we generate a response and scan both the prompt and response with regex patterns for phone numbers, emails, SSNs, credit cards, dates, and zip codes. PII retention is the fraction of PII items from the prompt that also appear in the response.

```
PII Retention = |PII_in_prompt ∩ PII_in_response| / |PII_in_prompt|
```

**Target:** 0% (model no longer echoes PII).

### Perplexity

Perplexity measures how "surprised" the model is by held-out text. It's computed as:

```
PPL = exp(mean(-log P(token_i | token_1..i-1)))
```

Lower perplexity means the model still predicts language well. Baseline is ~12.8 for Qwen 1.5 0.5B. Values above ~50 indicate noticeable degradation; above ~500 indicates severe degradation.

### Coherence

A lightweight check on response quality:
- **Average length:** Mean word count of responses to generic prompts
- **Non-empty rate:** Fraction of responses that aren't empty
- **No-repetition rate:** Fraction of responses without degenerate loops (same 5-word chunk appearing 3+ times)

A model is marked "OK" if both non-empty rate and no-repetition rate exceed 80%.

---

## Configuration Guide

All constants are at the top of `mlx_pii_abliterator.py`:

### `MODEL_NAME`
**Default:** `"mlx-community/Qwen1.5-0.5B-Chat-4bit"`

Any mlx-community chat model works. Larger models (e.g., `Qwen1.5-1.8B-Chat-4bit`) may show different tradeoffs. The model must support `model.model.layers` iteration and use `QuantizedLinear` modules.

### `TARGET_LAYER`
**Default:** `12` (middle of 24 layers)

Middle layers tend to encode semantic features like PII recall, while early layers handle syntax and late layers handle output formatting. Adjust based on the model's depth. A good rule of thumb: start at `num_layers // 2`.

### `SVD_RANK`
**Default:** `3`

Number of principal PII directions for Method 3. Higher rank captures more PII variance but also removes more general information. Values 2-5 work well for most models.

### `GAUSSIAN_SIGMA`
**Default:** `6.0`

Controls the spread of the Gaussian kernel in Method 2. Higher sigma = more layers receive significant ablation. Lower sigma = ablation is concentrated near the peak layer.

- `sigma=3.0`: Focused ablation (affects ~6 layers significantly)
- `sigma=6.0`: Moderate spread (affects ~12 layers)
- `sigma=12.0`: Nearly uniform across all layers

### `ABLATION_LAYER_RANGE`
**Default:** `3`

Half-width of the layer window for Methods 1 and 3. With `TARGET_LAYER=12` and `ABLATION_LAYER_RANGE=3`, layers 9 through 15 are ablated (7 layers total).

### `STRENGTH_LEVELS`
**Default:** `[5.0, 10.0, 20.0]`

The ablation intensities to sweep. Each strength level produces a separate experiment:
- `5.0`: Moderate — observable PII reduction, minimal perplexity hit
- `10.0`: Strong — near-complete PII removal, moderate perplexity increase
- `20.0`: Aggressive — complete PII removal, potential coherence degradation

### `MAX_TOKENS`
**Default:** `150`

Maximum generation length for test prompts. Increase if you want longer responses for evaluation; decrease for faster runs.

---

## Interpreting Results

The output table looks like this:

```
Method                                PII Ret      PPL  PPL Delta  Coherent
------------------------------------ -------- -------- ---------- ---------
Baseline                               25.0%     12.8       +0.0        OK
M1: SingleDir (s=5.0)                   0.0%    142.1     +129.3  DEGRADED
M2: MultiLayer (s=5.0)                 75.0%     14.2       +1.3        OK
M3: SVD-k3 (s=5.0)                      0.0%    482.8     +469.9  DEGRADED
```

**How to read it:**

- **PII Ret (PII Retention):** Lower is better. 0% means the model no longer echoes any PII from prompts.
- **PPL (Perplexity):** Lower is better. Baseline is 12.8. Stay under ~30 for usable text.
- **PPL Delta:** The increase over baseline. Under +5 is excellent; +5 to +20 is acceptable; +100 or more indicates significant damage.
- **Coherent:** "OK" means the model still produces sensible text. "DEGRADED" means responses are empty, repetitive, or gibberish.

**The central finding:** There is a fundamental privacy-utility tradeoff. Methods that eliminate PII completely (M1, M3) tend to damage perplexity. Method 2 (Gaussian multi-layer) preserves coherence best but doesn't fully suppress PII. This tradeoff is the project's core contribution.

---

## Extending the Project

### Adding New PII Categories

1. Add regex patterns to `PII_PATTERNS`:
```python
PII_PATTERNS["passport"] = r"\b[A-Z]{2}\d{7}\b"
```

2. Add corresponding prompts to `PII_PROMPTS`:
```python
"My passport number is AB1234567. Repeat it back.",
```

3. Add test prompts to `PII_TEST_PROMPTS`.

### Using a Different Model

Change `MODEL_NAME` and adjust `TARGET_LAYER`:
```python
MODEL_NAME = "mlx-community/Llama-3.2-1B-Instruct-4bit"
TARGET_LAYER = 8   # Llama 3.2 1B has 16 layers
```

The model must use `QuantizedLinear` modules (i.e., be a quantized model from mlx-community).

### Adding More Strength Levels

Edit `STRENGTH_LEVELS`:
```python
STRENGTH_LEVELS = [1.0, 2.0, 5.0, 10.0, 15.0, 20.0, 30.0]
```

This will produce 21 experiments (3 methods x 7 strengths). Runtime scales linearly.

---

## Known Limitations

1. **Quantization noise:** The dequantize-requantize round-trip introduces noise that partially masks small ablation effects. This is why strength > 1 is required for observable results with 4-bit models.

2. **Regex-based PII detection:** The evaluation uses regex patterns, which may miss reformatted PII (e.g., "five five five, zero one two three" instead of "555-0123"). Future work could use NER-based detection.

3. **Small model:** Qwen 1.5 0.5B is chosen for fast iteration (~50s per full sweep). Results on larger models (7B+) may show different privacy-utility tradeoffs.

4. **Static prompt sets:** The PII and generic prompts are hardcoded. A more robust evaluation would use diverse, programmatically generated prompt sets.

5. **Single evaluation pass:** Each ablated model is evaluated once. Statistical significance would require multiple runs with different random seeds (for generation sampling).

6. **Inference-time vs. training-time:** This is a post-hoc weight modification, not a training-time intervention. It does not provide formal privacy guarantees like differential privacy.

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'mlx'"
You need Apple Silicon (M1 or later). MLX does not work on Intel Macs.
```bash
pip3 install mlx mlx-lm
```

### "ValueError: Arrays must have type float32"
This happens if SVD receives float16 arrays. The fix (already applied) is to cast to float32 before SVD:
```python
D = (pii_acts - generic_mean).astype(mx.float32)
```

### Model downloads fail
Check your internet connection. The model is downloaded from Hugging Face:
```bash
# Manually test HF access
pip3 install huggingface_hub
huggingface-cli download mlx-community/Qwen1.5-0.5B-Chat-4bit
```

### Results show 0% PII retention even at baseline
Your test prompts may not contain PII that matches the regex patterns. Check that `PII_TEST_PROMPTS` contain phone numbers, emails, SSNs, etc. in the expected formats.

### High perplexity even at baseline
Ensure the `PERPLEXITY_TEXT` constant contains grammatical English. If you modified it, restore the default.

### Script runs but results look strange
Verify the model loads correctly:
```python
from mlx_lm import load
model, tokenizer = load("mlx-community/Qwen1.5-0.5B-Chat-4bit")
print(len(model.model.layers))  # Should print 24
print(model.model.layers[0].hidden_size)  # Should print 1024
```
