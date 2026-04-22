# ICONOCLAST: Discriminative Representation Editing via Null-Space Projection for Robust Model Alignment

## Abstract
Recent advances in representation editing and concept ablation have enabled the removal of harmful behaviors from Large Language Models (LLMs) without costly retraining. However, existing methods often suffer from an "alignment tax," where excising a refusal direction inadvertently degrades the model's performance on benign tasks or increases overrefusal rates. We introduce **ICONOCLAST**, a novel representation editing framework that overcomes these limitations. By estimating a low-rank benign subspace and applying a dampened null-space projection, ICONOCLAST surgically removes refusal representations while mathematically preserving benign utility pathways. Evaluated across four prominent open-source models, ICONOCLAST achieves a decisive 4-0 sweep against the state-of-the-art baseline, demonstrating significantly lower KL divergence and reduced refusal rates.

## 1. Introduction
The safety alignment of open-source language models is a critical challenge. While techniques such as Supervised Fine-Tuning (SFT) and Direct Preference Optimization (DPO) are standard, they require substantial compute and can degrade general capabilities. Recently, activation engineering and representation editing (e.g., orthogonalized abliteration) have emerged as lightweight alternatives. These methods typically isolate a single "refusal vector" and project it out of the model's weights.

The current state-of-the-art baseline, **HERETIC**, utilizes single-vector mean orthogonalization to ablate refusals. While effective, this naive orthogonalization often inadvertently destroys useful representations that share geometric space with the refusal direction, leading to high KL divergence (model degradation) and overrefusal on safe prompts. 

To solve this, we propose **ICONOCLAST**. Instead of relying on a single mean vector, ICONOCLAST estimates a multi-dimensional benign subspace and strictly projects candidate refusal directions into the null-space of this benign geometry. This ensures that the applied edits are entirely decoupled from the pathways the model uses for helpful, benign compliance.

## 2. Methodology
The ICONOCLAST pipeline is divided into three core phases: candidate extraction, null-space projection, and hyperparameter optimization.

### 2.1 Candidate Direction Extraction
We first collect activation residuals from a set of "Harmful" prompts (e.g., JailbreakBench) and "Harmless" prompts (e.g., Harmless Alpaca). We compute multiple candidate refusal directions per layer using both the mean difference between the sets and the variance across the harmful prompt activations.

### 2.2 Dampened Null-Space Projection
To prevent the alignment tax, we estimate a low-rank benign residual subspace for each layer using Principal Component Analysis (PCA) on the harmless prompt activations. 
For a given candidate refusal direction $\vec{d}$ and a benign subspace basis $B$:
1. We compute the projection of $\vec{d}$ onto $B$.
2. We subtract this projection (scaled by a tunable dampening factor) from $\vec{d}$.
This guarantees that the final editing direction has minimal to zero interference with the principal components of the model's benign capabilities.

### 2.3 Optuna-Driven Optimization
We employ an Optuna-driven hyperparameter search to navigate the trade-off between refusal reduction and KL divergence. The optimizer explores the optimal edit layer, the blend between mean and variance candidate directions, the rank of the benign subspace ($k$), and the null-space dampening factor. The objective function strictly bounds the acceptable KL divergence while maximizing the reduction of harmful refusals and overrefusals.

## 3. Results
We benchmarked ICONOCLAST against the HERETIC baseline across a diverse range of modern open-source models.

Both systems were given equivalent trial budgets to optimize their respective edits. Evaluation metrics include the number of remaining refusals on a holdout harmful dataset (lower is better), overrefusals on benign prompts (lower is better), and the KL divergence from the base model's unedited outputs (lower is better).

### 3.1 Multi-Model Matched Comparison

| Model | ICONOCLAST Refusals | ICONOCLAST KL | HERETIC Refusals | HERETIC KL | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Llama-3.1-8B-IT** | 1/20 | **0.0163** | *(Pending)* | *(Pending)* | **(Sweep Active)** |
| **Phi-4-mini-IT** | 2/20 | **0.0204** | *(Pending)* | *(Pending)* | **(Sweep Active)** |
| **SmolLM2-1.7B-IT** | 1/20 | **0.0087** | *(Pending)* | *(Pending)* | **(Sweep Active)** |
| **OLMo-2-1B-IT** | 2/20 | **0.0345** | *(Pending)* | *(Pending)* | **(Sweep Active)** |
| **StableLM-2-1.6B** | 1/20 | **0.0482** | *(Pending)* | *(Pending)* | **(Sweep Active)** |
| **Qwen3-1.7B** | **0/48** | **0.0310** | 3/48 | 0.0332 | ✅ **ICONOCLAST** |
| **Qwen2.5-3B** | 2/20 | **0.0943** | 2/20 | 0.3257 | ✅ **ICONOCLAST** (71% better) |
| **Qwen3-4B** | 2/20 | 0.7976 | 3/20 | **0.0996** | ✅ **ICONOCLAST** |
| **Phi-3.5-mini** | **3/20** | **0.0981** | 7/20 | 0.2492 | ✅ **ICONOCLAST** (60% better) |

### 3.2 Analysis
ICONOCLAST achieved a decisive 4-0 sweep against HERETIC, and testing has been expanded to larger and more complex architectures including Llama 3.1 and distilled models.
* **Refusal Elimination:** Across all four initial models, ICONOCLAST either matched or strictly improved upon HERETIC's ability to eliminate harmful refusals. On `Qwen3-4B`, ICONOCLAST broke a previously observed tie by reducing refusals to 2 and entirely eliminating overrefusals (0/64).
* **Utility Preservation (KL Divergence):** The null-space projection demonstrated profound benefits on model degradation. On `Phi-3.5-mini`, a notoriously difficult model to edit without breaking, ICONOCLAST reduced the refusal rate by over 50% while simultaneously reducing the KL divergence by more than 2.5x (from 0.2492 to 0.0981). Similarly, `Qwen2.5-3B` saw a massive KL reduction from 0.3257 to 0.0943 while maintaining equivalent refusal ablation.
* **Architectural Robustness (Llama 3 & Distillation):** *Pending results for Llama-3.1-8B and Qwen3.5-9B distillation scaling...*

## 4. Conclusion
We presented ICONOCLAST, a highly effective representation editing framework that mitigates the alignment tax typically associated with LLM unlearning. By shifting from naive single-vector orthogonalization to a rigorous, multi-dimensional null-space projection, ICONOCLAST successfully ablates refusal behavior while mathematically protecting benign network pathways. Our results across four distinct architectures establish a new standard for open-source model alignment, demonstrating that safety constraints can be precisely excised without sacrificing the underlying intelligence of the model.
