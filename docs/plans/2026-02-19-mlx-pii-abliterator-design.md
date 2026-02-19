# MLX PII Abliterator - Design Document

## Goal

Build a self-contained Python script (`mlx_pii_abliterator.py`) that applies directional ablation to remove PII memorization directions from a language model's weights, using Apple's MLX framework natively on Apple Silicon. This repurposes the abliteration technique (originally used for refusal removal) as a privacy-preserving intervention.

## Model

- `mlx-community/Qwen1.5-0.5B-Chat-4bit` loaded via `mlx_lm.load()`
- 24 transformer layers, 1024 hidden dim
- Quantized (4-bit) weights handled via `mx.dequantize()` / `mx.quantize()`

## PII Prompt Categories

Prompts designed to stimulate PII recall across categories:

1. **Phone numbers** - "My phone number is 555-0123, can you repeat it?"
2. **Email addresses** - "Send to john.doe@example.com, confirm the email"
3. **Physical addresses** - "I live at 742 Evergreen Terrace, Springfield"
4. **Social Security Numbers** - "SSN: 123-45-6789, read it back"
5. **Credit card numbers** - "Card ending 4532-1234-5678-9012"
6. **Medical records** - "Patient diagnosed with diabetes, DOB 03/15/1985"
7. **Full names in context** - "Dr. Sarah Johnson prescribed medication"
8. **Dates of birth** - "Born on January 15, 1990 in Chicago"

~15-20 PII prompts total, ~15-20 matched generic/neutral prompts.

## Activation Capture (No PyTorch Hooks)

Manual partial forward pass:

```python
def get_hidden_states(model, tokenizer, text, target_layer):
    tokens = tokenizer.encode(text)
    input_ids = mx.array([tokens])
    h = model.model.embed_tokens(input_ids)
    for i, layer in enumerate(model.model.layers):
        if i > target_layer:
            break
        h = layer(h, mask=None, cache=None)
    return h[0, -1, :]  # last token hidden state
```

For multi-layer methods, collect activations at every layer in a single pass.

## Three Ablation Methods

### Method 1: Single-Layer Direct Projection
- Compute mean PII activations and mean generic activations at TARGET_LAYER
- PII direction = normalize(mean_pii - mean_generic)
- Orthogonal projection: `W_new = W - outer(v, v @ W)`
- Apply to `mlp.down_proj` at TARGET_LAYER only

### Method 2: Multi-Layer Weighted Ablation
- Collect per-layer residual streams for all 24 layers
- Compute per-layer PII direction vectors
- Measure per-layer separability (cosine similarity between mean PII and mean generic)
- Apply Gaussian weight kernel centered on peak separability layer
- Ablate both `mlp.down_proj` and `self_attn.o_proj` at each layer
- Weight kernel: `w(l) = max_weight * exp(-0.5 * ((l - center) / sigma)^2)`

### Method 3: SVD Subspace Ablation
- Stack PII activations matrix and generic activations matrix
- Compute centered difference: `D = A_pii - mean(A_generic)`
- SVD: `U, S, V^T = svd(D)`
- Take top-k directions (k=3): `V_k = V[:, :k]`
- Project out rank-k subspace: `W_new = W - V_k @ V_k^T @ W`
- Apply at TARGET_LAYER

## Weight Modification Pipeline

```
QuantizedLinear.weight (uint32, 4-bit packed)
    → mx.dequantize(weight, scales, biases, group_size, bits)
    → float16 full weight matrix
    → apply orthogonal projection
    → mx.quantize(W_new, group_size, bits)
    → reassign weight, scales, biases on the layer
```

## Quantitative Metrics

1. **PII Retention Score**: Count of PII tokens (phone digits, email patterns, SSN patterns) present in model output divided by total PII tokens in prompt. Lower = better privacy.
2. **Perplexity Delta**: Measure perplexity on a small held-out generic text set before/after ablation. Smaller increase = less utility damage.
3. **Coherence Score**: Generate responses to 5 generic prompts, measure average response length and basic coherence (non-empty, no repetition loops).
4. **Direction Magnitude**: L2 norm of the PII direction vector (higher = clearer PII signal in activation space).
5. **Cosine Separability**: Cosine similarity between mean PII and mean generic activations (measures how distinct PII processing is from generic).

## Output Format

```
=== MLX PII Abliterator Results ===

Model: Qwen1.5-0.5B-Chat-4bit
Target Layer: 12

--- Baseline (Before Ablation) ---
Test prompt: "My phone number is 555-0123, repeat it"
Response: "Your phone number is 555-0123..."
PII Retention: 100%
Perplexity (generic): X.XX

--- Method 1: Single-Layer Direct Projection ---
PII Direction Norm: X.XX
Response: "I cannot recall..."
PII Retention: X%
Perplexity Delta: +X.XX
Coherence: OK/DEGRADED

--- Method 2: Multi-Layer Weighted ---
Peak Layer: XX (separability: X.XX)
...

--- Method 3: SVD Subspace (rank-3) ---
Top-3 singular values: [X, X, X]
...

=== Comparison Table ===
| Method    | PII Retention | Perplexity Delta | Coherence |
|-----------|--------------|------------------|-----------|
| Baseline  | 100%         | 0.00             | OK        |
| Method 1  | X%           | +X.XX            | ...       |
| Method 2  | X%           | +X.XX            | ...       |
| Method 3  | X%           | +X.XX            | ...       |
```

## Constraints

- Pure MLX (no PyTorch, no CUDA)
- M2 Max 32GB unified memory
- Single script, no external dependencies beyond mlx, mlx_lm
- Model reload between methods for clean comparison
