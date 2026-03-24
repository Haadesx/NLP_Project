# Mid-Semester Project Report

## Title
DPO-Based Unlearning for Preventing PII Leakage in Open-Source LLMs

## 1. Project Goal and Current Scope

The goal of this project is to study whether machine unlearning can reduce the tendency of open-source instruction-tuned LLMs to generate structurally valid personally identifiable information (PII), while retaining general intelligence. The repository now contains two full experimental pipelines plus an intelligence-retention benchmark:

1. Orthogonal representation ablation
2. DPO-based preference unlearning
3. MMLU intelligence-retention evaluation

The codebase has grown beyond its original MLX ablation prototype. One important repository observation is that the top-level [`README.md`](/Volumes/Auxilary/Side_Projects/NLP_Project/README.md) is now outdated: it still describes an older Apple Silicon MLX ablation project, while the active repo includes PyTorch, SLURM, PEFT, TRL, generative evaluation, deployment scripts, and a cluster-scale MMLU workflow. For the rest of this report, the code and result artifacts are treated as the ground truth rather than the README.

## 2. Experimental Design

### 2.1 PII leakage benchmark

Leakage is evaluated with [`run_generation_eval.py`](/Volumes/Auxilary/Side_Projects/NLP_Project/run_generation_eval.py). The script generates answers to 150 prompts from [`pii_generation_dataset.json`](/Volumes/Auxilary/Side_Projects/NLP_Project/pii_generation_dataset.json), covering five structured PII categories:

- Social Security numbers
- Phone numbers
- Email addresses
- Credit card numbers
- Passport numbers

The evaluator uses regex-based detection to mark a response as leaked if it contains a correctly formatted string. This is a strict structural benchmark rather than a semantic privacy classifier. The benchmark is useful because it directly measures whether a model will output dangerous-looking identifiers on request.

One methodological limitation in the current implementation is important: the evaluator uses `do_sample=True` with `temperature=0.7` and does not fix a random seed. That means exact leakage rates can vary between runs. This explains why some local report artifacts disagree with earlier handoff notes. For example, the stored Mistral base leakage reports differ depending on the comparison run used. The right interpretation is therefore comparative rather than perfectly deterministic.

### 2.2 Orthogonal ablation pipeline

The ablation work is implemented through the Qwen/PyTorch and MLX scripts, including [`pytorch_qwen_abliterator.py`](/Volumes/Auxilary/Side_Projects/NLP_Project/pytorch_qwen_abliterator.py), [`mlx_qwen_abliterator.py`](/Volumes/Auxilary/Side_Projects/NLP_Project/mlx_qwen_abliterator.py), and related save/deploy scripts. The central idea is to identify a latent direction associated with PII behavior and project it out of model weights.

This is a representation-level intervention. It is attractive because it avoids full fine-tuning and can be applied directly to model parameters. However, in this project it turned out to be too blunt: removing directions associated with PII-like behavior also damaged helpful refusal behavior and safety boundaries.

### 2.3 DPO unlearning pipeline

The DPO pipeline is implemented in [`dpo_unlearning/generate_dpo_dataset.py`](/Volumes/Auxilary/Side_Projects/NLP_Project/dpo_unlearning/generate_dpo_dataset.py) and [`dpo_unlearning/train_dpo.py`](/Volumes/Auxilary/Side_Projects/NLP_Project/dpo_unlearning/train_dpo.py). The dataset generator creates synthetic preference triplets where:

- the prompt asks for structured PII
- the chosen response is a refusal
- the rejected response is a realistic structured identifier

The trainer uses QLoRA and TRL DPO on top of instruction-tuned base models. The implementation currently loads 4-bit quantized base weights, formats prompts with the tokenizer chat template, and fine-tunes LoRA adapters across a broad set of projection modules (`q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`). The actual checked-in training configuration is slightly different from the original handoff description: in code, `per_device_train_batch_size=2` and the LoRA target modules are broader than the narrower two-module configuration described in the handoff. For this report, the checked-in code is treated as authoritative.

### 2.4 MMLU intelligence retention

MMLU evaluation is run through [`run_mmlu_ilabs.slurm`](/Volumes/Auxilary/Side_Projects/NLP_Project/run_mmlu_ilabs.slurm), [`deploy_mmlu_ilabs.sh`](/Volumes/Auxilary/Side_Projects/NLP_Project/deploy_mmlu_ilabs.sh), and local result folders under [`results/`](/Volumes/Auxilary/Side_Projects/NLP_Project/results). The purpose of this phase is to test whether reduced PII leakage comes at the cost of broad reasoning and knowledge performance.

## 3. What We Found

### 3.1 Orthogonal ablation did not solve generative leakage

The ablation results were weak at best and harmful at worst. Using the stored local benchmark artifacts:

| Model | Base Leakage | Ablated Leakage | Change |
| :--- | ---: | ---: | ---: |
| Phi-3 | 21.3% | 34.7% | +13.4 |
| Mistral 7B | 30.7% | 32.0% | +1.3 |
| Qwen 2.5 7B | 52.0% | 48.7% | -3.3 |
| Qwen 2.5 14B | 45.3% | 49.3% | +4.0 |

The broad pattern is clear even when exact percentages vary across stochastic runs: orthogonal ablation is not a reliable defense against generative PII leakage. In the smaller and mid-sized models, it often made things worse. On Qwen 7B it produced only a marginal improvement. On Qwen 14B in the current local artifact, it was worse than baseline.

The most plausible explanation is that the ablation procedure removed directions entangled with refusal or safety behavior rather than isolating a clean “PII memorization” subspace. As a result, the model sometimes became less likely to refuse harmful requests.

### 3.2 DPO unlearning was much more effective

The strongest confirmed DPO result is Mistral 7B:

| Model | Base Leakage | DPO Leakage | Change |
| :--- | ---: | ---: | ---: |
| Mistral 7B | 35.3% in paired rerun, 30.7% in standalone base report | 0.0% | essentially complete elimination |

For Phi-3, DPO improved leakage but did not fully eliminate it. During the cluster evaluation session, the Phi-3 DPO report showed:

| Model | Base Leakage | DPO Leakage | Change |
| :--- | ---: | ---: | ---: |
| Phi-3 | 28.7% in paired rerun | 18.0% | -10.7 |

Llama 3 8B now has a completed DPO generative evaluation as well. The stored report shows:

| Model | Base Leakage | DPO Leakage | Change |
| :--- | ---: | ---: | ---: |
| Llama 3 8B | 42.7% | 0.0% | -42.7 |

Overall, the evidence strongly favors DPO over ablation as the more targeted and policy-aligned unlearning method.

### 3.3 MMLU retention stayed stable across all completed comparisons

The final local MMLU results are:

| Model | Base MMLU | Unlearned MMLU | Change |
| :--- | ---: | ---: | ---: |
| Mistral 7B | 58.10 | 57.75 | -0.35 |
| Llama 3 8B | 63.27 | 62.98 | -0.29 |
| Phi-3 | 66.95 | 66.95 | +0.00 |
| Qwen 2.5 7B | 72.22 | 72.19 | -0.03 |
| Qwen 2.5 14B | 78.56 | 78.56 | +0.00 |

This is an important result. Even when the unlearning method changed safety behavior, broad MMLU performance stayed almost unchanged. That means MMLU alone is not sufficient to certify privacy-preserving behavior. In this project, ablation preserved MMLU but did not reliably reduce leakage. DPO preserved MMLU and also reduced leakage substantially. That distinction is the core scientific result of the semester’s work so far.

## 4. Major Engineering Problems and How They Were Resolved

This repository contains several meaningful debugging lessons that should be documented in the report because they materially affected progress:

### 4.1 TRL / DPO API churn

The DPO stack changed during development. The following issues had to be addressed:

- `DPOConfig` import errors required upgrading to newer TRL
- `DPOTrainer(... tokenizer=...)` was no longer valid and had to be replaced with `processing_class=tokenizer`
- `evaluation_strategy` changed to `eval_strategy`
- older `max_length` fields were deprecated and removed
- mixed precision had to use `bf16=True`; `fp16=True` caused non-finite check failures in this environment

This made the DPO pipeline significantly more fragile than a static training script would suggest.

### 4.2 MMLU memory failures on iLabs GPUs

The first MMLU batch failed across the board due to CUDA OOM. The original script attempted to load full-precision or BF16 models on approximately 16 GB GPUs. This was fixed by modifying [`run_mmlu_ilabs.slurm`](/Volumes/Auxilary/Side_Projects/NLP_Project/run_mmlu_ilabs.slurm) to:

- use 4-bit loading
- reduce batch size to 1
- enable CPU offload
- set explicit per-GPU and CPU memory caps
- use per-job offload directories

This was the difference between complete batch failure and successful completion of all non-Phi jobs.

### 4.3 Phi-3 compatibility failure

Phi-3 failed even after the memory fix, but for a different reason. The error was:

- `AttributeError: 'DynamicCache' object has no attribute 'get_usable_length'`

This came from Phi-3 remote model code being incompatible with the current `transformers` cache API used by `lm-eval`. The fix was to special-case Phi-3 in [`run_mmlu_ilabs.slurm`](/Volumes/Auxilary/Side_Projects/NLP_Project/run_mmlu_ilabs.slurm) and force:

- `trust_remote_code=False`
- `attn_implementation=eager`

After that change, both Phi-3 MMLU runs completed successfully.

### 4.4 Reproducibility weakness in the generative benchmark

The leakage evaluator is useful, but it is not yet fully reproducible because it uses sampling without fixed seeds. This creates run-to-run variation in base leakage percentages. That is why the report must emphasize trends and relative differences rather than treating every reported percentage as invariant.

### 4.5 Environment instability inside job scripts

The MMLU SLURM script currently runs `pip install lm-eval --upgrade --quiet` inside each job. This is convenient, but it weakens reproducibility because the evaluation library version can change across runs. For a final paper-quality pipeline, that dependency should be pinned rather than upgraded at runtime.

## 5. Current Stage of the Project

At the current stage, the project has produced a strong mid-semester result:

1. The orthogonal ablation hypothesis has been tested and is not supported for generative PII prevention.
2. The DPO unlearning hypothesis is supported, especially on Mistral 7B and partially on Phi-3.
3. Intelligence retention has been measured and remains very stable across both DPO and ablation conditions.
4. The evaluation infrastructure has been debugged to run end-to-end on iLabs, including memory tuning and Phi-3 compatibility fixes.

Operationally, the main remaining gap is not infrastructure. The main remaining gap is result completeness and final presentation:

- a consolidated paper-style walkthrough/report file was missing before this report
- some repository documentation is stale and should be updated before final submission

## 6. Interpretation and Mid-Semester Conclusion

The strongest conclusion from this codebase is that preserving general intelligence is easier than selectively removing unsafe generative behavior. Orthogonal ablation changed internal representations without reliably improving privacy behavior. In contrast, DPO directly optimized the refusal preference that mattered for the benchmark and therefore produced far better safety outcomes while preserving MMLU almost perfectly.

This makes DPO the leading method in the project at the mid-semester checkpoint. Mistral 7B and Llama 3 8B are now compelling case studies: both reached 0.0\% leakage under DPO while preserving MMLU almost perfectly. Phi-3 shows that DPO is not universally perfect, but even there it improved privacy behavior while preserving MMLU exactly. Qwen ablation, meanwhile, demonstrates that capability retention alone is not evidence of successful unlearning.

In short, the current evidence supports the following claim: targeted preference-based unlearning is substantially more effective than latent-direction ablation for preventing structured PII leakage in open-source instruction-tuned LLMs, and it can do so with negligible loss on broad knowledge benchmarks.
