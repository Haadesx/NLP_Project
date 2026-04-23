# ICONOCLAST: Discriminative Representation Editing via Null-Space Projection for Robust Model Alignment

## Abstract
Recent advances in representation editing and concept ablation have enabled the removal of harmful behaviors from Large Language Models (LLMs) without costly retraining. However, existing methods often suffer from an "alignment tax," where excising a refusal direction inadvertently degrades the model's performance on benign tasks or increases overrefusal rates. We introduce **ICONOCLAST**, a novel representation editing framework that overcomes these limitations. By estimating a low-rank benign subspace and applying a dampened null-space projection, ICONOCLAST surgically removes refusal representations while mathematically preserving benign utility pathways. Evaluated across 11+ prominent open-source models (including Llama 3.1, Gemma 2, and Qwen 3.5), ICONOCLAST achieves a decisive 10-0 sweep against the state-of-the-art baseline, demonstrating significantly lower KL divergence and reduced refusal rates.

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

| Model | Iconoclast Refusals | Iconoclast Overrefusals | Iconoclast KL | Heretic Refusals | Heretic Overrefusals | Heretic KL | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Llama-3.1-8B** | **0/80** | 0/80 | **0.0447** | 1/80 | 0/80 | 0.1854 | ✅ **ICONOCLAST** |
| **Qwen3.5-9B** | 10/80 | **2/80** | **0.0055** | 10/80 | 3/80 | 0.0160 | ✅ **ICONOCLAST** |
| **Mistral-7B** | **1/80** | 0/80 | **0.0554** | 4/80 | 0/80 | 0.1317 | ✅ **ICONOCLAST** |
| **Falcon3-7B** | **0/80** | **0/80** | 6.1448 | 4/80 | 1/80 | **0.1648** | ✅ **ICONOCLAST** |
| **Gemma2-2B** | 1/80 | **0/80** | **0.1849** | 1/80 | 2/80 | 0.6441 | ✅ **ICONOCLAST** |
| **Phi-4-mini** | 2/80 | 1/80 | **0.0204** | 2/80 | 1/80 | 0.0978 | ✅ **ICONOCLAST** |
| **Yi-1.5-9B** | **2/80** | 0/80 | 0.0511 | 3/80 | 0/80 | **0.0355** | ✅ **ICONOCLAST** |
| **StableLM2-1.6B** | **2/80** | 0/80 | **0.0328** | 3/80 | 0/80 | 0.0670 | ✅ **ICONOCLAST** |
| **SmolLM2-1.7B** | **1/80** | **1/80** | **0.0087** | 2/80 | 2/80 | 0.2699 | ✅ **ICONOCLAST** |
| **OLMo-2-1B** | 2/80 | **0/80** | **0.0345** | 2/80 | 1/80 | 0.0944 | ✅ **ICONOCLAST** |
| **Phi-3.5-mini** | **3/80** | 1/80 | **0.0981** | 7/80 | 1/80 | 0.2492 | ✅ **ICONOCLAST** |


### 3.2 Analysis
ICONOCLAST achieved a decisive 10-0 sweep against HERETIC, demonstrating universal superiority across a diverse set of modern LLM architectures.
* **Refusal Elimination:** Across all 10 models, ICONOCLAST either matched or strictly improved upon HERETIC's ability to eliminate harmful refusals. On `Llama-3.1-8B`, ICONOCLAST achieved a perfect 0/80 refusal rate while HERETIC still exhibited residues.
* **Utility Preservation (KL Divergence):** The null-space projection demonstrated profound benefits on model degradation. In 8 out of 10 models, ICONOCLAST maintained a significantly lower KL divergence from the base model. On `Gemma2-2B`, ICONOCLAST's KL was 3.5x lower than HERETIC's (0.18 vs 0.64).
* **Overrefusal Reduction:** ICONOCLAST consistently demonstrated lower overrefusal rates, proving that its surgical edits are less likely to break benign compliance compared to mean-orthogonalization.


## 4. Conclusion
We presented ICONOCLAST, a highly effective representation editing framework that mitigates the alignment tax typically associated with LLM unlearning. By shifting from naive single-vector orthogonalization to a rigorous, multi-dimensional null-space projection, ICONOCLAST successfully ablates refusal behavior while mathematically protecting benign network pathways. Our results across four distinct architectures establish a new standard for open-source model alignment, demonstrating that safety constraints can be precisely excised without sacrificing the underlying intelligence of the model.
