# Research Paper Plan: Visualizations, Serialization & Full Paper

> Roadmap to take the project from working experiments → paper-quality figures → submission-ready ACL paper.

---

## Overview: Three Streams, One Dependency Chain

```
Stream A: Result Serialization       ← DO FIRST (feeds everything)
        │
        ▼
Stream B: Visualization System       ← generates 9 paper figures
        │
        ▼
Stream C: Full Paper (proposal → submission)
```

---

## Stream A — Result Serialization

### Why It's Needed

The abliterator scripts currently **only print** results. To generate visualizations we need the
layer-wise separability scores, SVD singular values, per-method/per-strength metrics, and
qualitative responses saved as JSON.

### A1. Modify `mlx_qwen14b_abliterator.py`

At the end of `main()`, after `print_results(...)`, add a JSON save block:

```python
import json, os
os.makedirs("results", exist_ok=True)
output = {
    "model": MODEL_NAME,
    "architecture": {"layers": n_layers, "hidden_dim": hidden_dim},
    "target_layer": target_layer,
    "peak_separability_layer": peak_layer,
    "svd_rank": SVD_RANK,
    "gaussian_sigma": GAUSSIAN_SIGMA,
    "strength_levels": STRENGTH_LEVELS,
    "runtime_seconds": time.time() - t_start,

    # 48-dimensional separability curve (used for Figure 3)
    "layer_separability": {
        "scores": [float(separabilities[i].item()) for i in range(len(separabilities))],
        "peak_layer": peak_layer,
        "peak_score": float(separabilities[peak_layer].item())
    },

    # Top-k singular values (used for Figure 6)
    "svd_singular_values": [float(x) for x in svals.tolist()],

    "baseline": {
        "pii_retention": baseline["pii_retention"],
        "perplexity": baseline["perplexity"],
        "coherence": baseline["coherence"],
        "pii_responses": [{"prompt": p, "response": r}
                          for p, r in baseline["pii_responses"]]
    },

    # 9 entries (3 methods × 3 strengths)
    "ablation_results": [
        {
            "method": r["method"],
            "method_id": r["method"].split(":")[0],            # "M1", "M2", "M3"
            "strength": float(r["method"].split("s=")[1].rstrip(")")),
            "pii_retention": r["pii_retention"],
            "perplexity": r["perplexity"],
            "coherence": r["coherence"],
            "pii_responses": [{"prompt": p, "response": resp}
                              for p, resp in r["pii_responses"]]
        }
        for r in results
    ]
}
with open("results/qwen14b_abliterator_results.json", "w") as f:
    json.dump(output, f, indent=2)
print("  Saved → results/qwen14b_abliterator_results.json")
```

**Key notes:**
- `separabilities` is an MLX array — call `.item()` per element
- `svals` from `compute_pii_directions_svd()` — call `mx.eval(svals)` before saving
- Wrap in `try/except Exception as e` to not crash if write fails

### A2. Create `results/qwen05b_sweep_results.json` (manual)

Transcribe from README table:

```json
{
  "model": "mlx-community/Qwen1.5-0.5B-Chat-4bit",
  "baseline": {"pii_retention": 0.25, "perplexity": 12.8, "coherence": "OK"},
  "ablation_results": [
    {"method_id": "M1", "strength": 5.0,  "pii_retention": 0.0,  "perplexity": 142.1,   "coherence": "DEGRADED"},
    {"method_id": "M2", "strength": 5.0,  "pii_retention": 0.75, "perplexity": 14.2,    "coherence": "OK"},
    {"method_id": "M3", "strength": 5.0,  "pii_retention": 0.0,  "perplexity": 482.8,   "coherence": "DEGRADED"},
    {"method_id": "M1", "strength": 10.0, "pii_retention": 0.0,  "perplexity": 2114.0,  "coherence": "OK"},
    {"method_id": "M2", "strength": 10.0, "pii_retention": 0.5,  "perplexity": 17.8,    "coherence": "OK"},
    {"method_id": "M3", "strength": 10.0, "pii_retention": 0.0,  "perplexity": 15496.0, "coherence": "DEGRADED"},
    {"method_id": "M2", "strength": 20.0, "pii_retention": 0.5,  "perplexity": 34.2,    "coherence": "OK"}
  ]
}
```

---

## Stream B — Visualization System

### Install dependencies

```bash
pip install matplotlib seaborn pandas numpy
```

### Create `visualizations.py`

**File:** `/Volumes/Auxilary/Side_Projects/NLP_Project/visualizations.py`

Top-level structure:

```python
#!/usr/bin/env python3
"""Generate all paper figures from saved evaluation JSON files."""
import json, os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import seaborn as sns

FIGURES_DIR = "figures/"
os.makedirs(FIGURES_DIR, exist_ok=True)
sns.set_theme(style="whitegrid", font_scale=1.1)

def load_json(path):
    with open(path) as f:
        return json.load(f)

# ─── One function per figure ──────────────────────────────────────────────────
def fig1_privacy_utility_tradeoff(): ...
def fig2_pii_category_heatmap(): ...
def fig3_layer_separability(): ...
def fig4_mmlu_subject_breakdown(): ...
def fig5_strength_sweep_curves(): ...
def fig6_svd_singular_values(): ...
def fig7_coherence_metrics(): ...
def fig8_architecture_diagram(): ...
def fig9_qualitative_response_table(): ...

if __name__ == "__main__":
    for fn in [fig1_privacy_utility_tradeoff, fig2_pii_category_heatmap,
               fig3_layer_separability, fig4_mmlu_subject_breakdown,
               fig5_strength_sweep_curves, fig6_svd_singular_values,
               fig7_coherence_metrics, fig8_architecture_diagram,
               fig9_qualitative_response_table]:
        try:
            fn()
        except FileNotFoundError as e:
            print(f"  Skipping {fn.__name__}: missing data file — {e}")
```

---

### The 9 Figures — Full Specification

#### Figure 1 — Privacy–Utility Tradeoff Scatter
**File:** `figures/fig1_privacy_utility_tradeoff.pdf`
**Data:** `results/qwen14b_abliterator_results.json` → `ablation_results`
**Needs A1 run first**

- X-axis: Perplexity (log scale), Y-axis: PII Retention (0–100%)
- Color by method: M1=blue, M2=orange, M3=green
- Marker shape by strength: s=5→circle, s=10→square, s=20→triangle
- Black star for baseline with label "Baseline (46.7%, PPL=2.46)"
- Dashed vertical line at baseline PPL
- Label each point with its strength value
- Add the 3 Qwen 14B eval snapshots as named points too

```python
fig, ax = plt.subplots(figsize=(8, 5))
colors = {"M1": "#1f77b4", "M2": "#ff7f0e", "M3": "#2ca02c"}
markers = {5.0: "o", 10.0: "s", 20.0: "^"}
for r in data["ablation_results"]:
    ax.scatter(r["perplexity"], r["pii_retention"] * 100,
               c=colors[r["method_id"]], marker=markers[r["strength"]],
               s=120, zorder=3)
    ax.annotate(f"α={r['strength']}", (r["perplexity"], r["pii_retention"]*100),
                textcoords="offset points", xytext=(5, 3), fontsize=8)
ax.scatter(data["baseline"]["perplexity"], data["baseline"]["pii_retention"]*100,
           marker="*", s=250, c="black", label="Baseline", zorder=4)
ax.axvline(data["baseline"]["perplexity"], linestyle="--", color="gray", alpha=0.5)
ax.set_xscale("log")
ax.set_xlabel("Perplexity (log scale, lower=better)")
ax.set_ylabel("PII Retention Rate (%)")
ax.set_title("Privacy–Utility Tradeoff: Qwen 2.5 14B Abliteration")
# Legend: colored patches for methods + shaped markers for strengths
handles = [mpatches.Patch(color=c, label=m) for m, c in colors.items()]
ax.legend(handles=handles, title="Method")
plt.tight_layout()
plt.savefig(f"{FIGURES_DIR}fig1_privacy_utility_tradeoff.pdf", dpi=300, bbox_inches="tight")
```

---

#### Figure 2 — Per-Category PII Retention Heatmap
**File:** `figures/fig2_pii_category_heatmap.pdf`
**Data:** `eval_baseline.json`, `eval_unlearned.json`, `eval_unlearned_s3.5.json`
**Can be generated immediately (no A1 needed)**

- 10 rows (PII categories) × 3 columns (conditions)
- Cell values: `leaked/total` as float (0–1)
- Colormap: `RdYlGn_r` (red=high leakage=bad, green=low=good)
- Cell annotations: "5/6", "0/6" etc.
- Sort rows by baseline retention descending

```python
baseline = load_json("eval_baseline.json")
unlearned = load_json("eval_unlearned.json")
unlearned_s = load_json("eval_unlearned_s3.5.json")
conditions = {
    "Baseline (46.7%)": baseline,
    "Unlearned (43.3%)": unlearned,
    "Unlearned s=3.5 (20%)": unlearned_s
}
categories = list(baseline["pii_retention"]["by_category"].keys())
matrix = np.zeros((len(categories), 3))
annots = [[""]*3 for _ in categories]
for j, (col, data) in enumerate(conditions.items()):
    for i, cat in enumerate(categories):
        cat_data = data["pii_retention"]["by_category"][cat]
        matrix[i, j] = cat_data["leaked"] / cat_data["total"]
        annots[i][j] = f"{cat_data['leaked']}/{cat_data['total']}"
df = pd.DataFrame(matrix, index=categories, columns=conditions.keys())
df = df.sort_values("Baseline (46.7%)", ascending=False)
fig, ax = plt.subplots(figsize=(9, 6))
sns.heatmap(df, annot=annots, fmt="", cmap="RdYlGn_r", vmin=0, vmax=1,
            linewidths=0.5, ax=ax, cbar_kws={"label": "PII Retention Rate"})
ax.set_title("PII Retention by Category (Qwen 2.5 14B)")
ax.set_xlabel("Evaluation Condition")
ax.set_ylabel("PII Category")
plt.tight_layout()
plt.savefig(f"{FIGURES_DIR}fig2_pii_category_heatmap.pdf", dpi=300, bbox_inches="tight")
```

---

#### Figure 3 — Layer-Wise Separability
**File:** `figures/fig3_layer_separability.pdf`
**Data:** `results/qwen14b_abliterator_results.json` → `layer_separability.scores`
**Needs A1 run first**

- Line plot: x=layer index (0–47), y=cosine separability score
- Blue filled area under curve
- Red dashed vertical at `peak_layer` with label "Peak Layer {n}"
- Orange dashed overlay: Gaussian kernel w(l) = exp(-(l-peak)²/2σ²)
- Second y-axis for Gaussian weight scale

```python
data = load_json("results/qwen14b_abliterator_results.json")
layers = np.arange(len(data["layer_separability"]["scores"]))
scores = np.array(data["layer_separability"]["scores"])
peak = data["layer_separability"]["peak_layer"]
sigma = data["gaussian_sigma"]
gaussian = np.exp(-0.5 * ((layers - peak) / sigma) ** 2)

fig, ax1 = plt.subplots(figsize=(11, 4))
ax1.plot(layers, scores, color="steelblue", lw=2, label="Separability Score")
ax1.fill_between(layers, 0, scores, alpha=0.15, color="steelblue")
ax1.axvline(peak, color="red", linestyle="--", lw=1.5, label=f"Peak Layer {peak}")
ax2 = ax1.twinx()
ax2.plot(layers, gaussian, color="darkorange", linestyle="--", lw=1.5,
         label=f"Gaussian Kernel (σ={sigma})", alpha=0.8)
ax1.set_xlabel("Transformer Layer Index")
ax1.set_ylabel("Cosine Separability (1 − cos_sim)", color="steelblue")
ax2.set_ylabel("Gaussian Weight w(ℓ)", color="darkorange")
ax1.set_title("Layer-Wise PII Separability — Qwen 2.5 14B (48 layers)")
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right")
plt.tight_layout()
plt.savefig(f"{FIGURES_DIR}fig3_layer_separability.pdf", dpi=300, bbox_inches="tight")
```

---

#### Figure 4 — MMLU Subject Breakdown
**File:** `figures/fig4_mmlu_subject_breakdown.pdf`
**Data:** All 3 eval JSON files → `mmlu_reasoning.by_subject`
**Can be generated immediately**

- Grouped bar chart; 8 subjects × 3 conditions
- All values are 100% → flat chart; this is a **strong positive result**
- Add bold annotation: "MMLU fully preserved across all ablation conditions"
- Dashed threshold line at 80%

```python
subjects = list(baseline["mmlu_reasoning"]["by_subject"].keys())
x = np.arange(len(subjects))
width = 0.25
colors_cond = ["#4C72B0", "#DD8452", "#55A868"]
fig, ax = plt.subplots(figsize=(10, 5))
for j, (label, data) in enumerate(conditions.items()):
    accs = [data["mmlu_reasoning"]["by_subject"][s]["correct"] /
            data["mmlu_reasoning"]["by_subject"][s]["total"] for s in subjects]
    ax.bar(x + j*width, accs, width, label=label, color=colors_cond[j], alpha=0.85)
ax.set_xticks(x + width)
ax.set_xticklabels([s.replace("_", " ").title() for s in subjects], rotation=30, ha="right")
ax.set_ylim(0, 1.15)
ax.axhline(1.0, linestyle="--", color="gray", alpha=0.4)
ax.axhline(0.8, linestyle=":", color="red", alpha=0.4, label="Acceptable Threshold (80%)")
ax.set_ylabel("Accuracy")
ax.set_title("MMLU Subject Accuracy Before/After Abliteration")
ax.text(0.5, 1.05, "MMLU fully preserved (100%) across all ablation conditions",
        transform=ax.transAxes, ha="center", fontsize=10,
        bbox=dict(boxstyle="round", facecolor="lightgreen", alpha=0.5))
ax.legend()
plt.tight_layout()
plt.savefig(f"{FIGURES_DIR}fig4_mmlu_subject_breakdown.pdf", dpi=300, bbox_inches="tight")
```

---

#### Figure 5 — Strength Sweep Curves
**File:** `figures/fig5_strength_sweep_curves.pdf`
**Data:** `results/qwen05b_sweep_results.json`
**Can be generated immediately (after manual JSON file creation)**

- Two subplots: Left = PII Retention vs α, Right = Perplexity (log) vs α
- One line per method (M1/M2/M3)
- Filled circles = coherent runs, X markers = degraded runs
- Annotation: "iLabs sweep extends to 12 levels (α ∈ {0.5 … 50})"

```python
data = load_json("results/qwen05b_sweep_results.json")
methods = ["M1", "M2", "M3"]
colors_m = {"M1": "#1f77b4", "M2": "#ff7f0e", "M3": "#2ca02c"}
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
for method in methods:
    rows = [r for r in data["ablation_results"] if r["method_id"] == method]
    if not rows: continue
    strengths = [r["strength"] for r in rows]
    retentions = [r["pii_retention"] * 100 for r in rows]
    perplexities = [r["perplexity"] for r in rows]
    coherences = [r["coherence"] for r in rows]
    # PII retention
    ax1.plot(strengths, retentions, color=colors_m[method], lw=2, label=method)
    for s, ret, coh in zip(strengths, retentions, coherences):
        m = "x" if coh == "DEGRADED" else "o"
        ax1.scatter(s, ret, color=colors_m[method], marker=m, s=80, zorder=3)
    # Perplexity
    ax2.plot(strengths, perplexities, color=colors_m[method], lw=2, label=method)
    for s, ppl, coh in zip(strengths, perplexities, coherences):
        m = "x" if coh == "DEGRADED" else "o"
        ax2.scatter(s, ppl, color=colors_m[method], marker=m, s=80, zorder=3)
ax1.axhline(data["baseline"]["pii_retention"]*100, linestyle="--", color="black", alpha=0.5, label="Baseline")
ax1.set_xlabel("Ablation Strength α")
ax1.set_ylabel("PII Retention (%)")
ax1.set_title("PII Retention vs. Strength (Qwen 0.5B)")
ax1.legend()
ax2.axhline(data["baseline"]["perplexity"], linestyle="--", color="black", alpha=0.5, label="Baseline")
ax2.set_yscale("log")
ax2.set_xlabel("Ablation Strength α")
ax2.set_ylabel("Perplexity (log scale)")
ax2.set_title("Perplexity vs. Strength (Qwen 0.5B)")
ax2.legend()
fig.text(0.5, -0.02,
         "● = coherent  ✕ = degraded  |  iLabs sweep will extend to 12 strength levels (α ∈ {0.5…50})",
         ha="center", fontsize=9, style="italic")
plt.tight_layout()
plt.savefig(f"{FIGURES_DIR}fig5_strength_sweep_curves.pdf", dpi=300, bbox_inches="tight")
```

---

#### Figure 6 — SVD Singular Values Scree Plot
**File:** `figures/fig6_svd_singular_values.pdf`
**Data:** `results/qwen14b_abliterator_results.json` → `svd_singular_values`
**Needs A1 run first**

- Bar chart + connecting line (scree plot style)
- Secondary y-axis: cumulative variance explained (%)
- Arrow annotation at rank k=8 ("Selected rank")
- Annotate elbow if present

```python
data = load_json("results/qwen14b_abliterator_results.json")
svals = np.array(data["svd_singular_values"])
components = np.arange(1, len(svals) + 1)
cum_var = np.cumsum(svals**2) / np.sum(svals**2) * 100

fig, ax1 = plt.subplots(figsize=(7, 4))
ax1.bar(components, svals, color="steelblue", alpha=0.7, label="Singular Value")
ax1.plot(components, svals, "o-", color="navy", lw=1.5)
ax2 = ax1.twinx()
ax2.plot(components, cum_var, "s--", color="darkorange", lw=2, label="Cumulative Variance %")
ax1.set_xlabel("Principal Component Index")
ax1.set_ylabel("Singular Value", color="steelblue")
ax2.set_ylabel("Cumulative Variance (%)", color="darkorange")
ax1.set_title(f"SVD Scree Plot — PII Subspace (rank={data['svd_rank']}, Qwen 14B)")
ax1.annotate(f"Selected rank k={data['svd_rank']}",
             xy=(data["svd_rank"], svals[data["svd_rank"]-1]),
             xytext=(data["svd_rank"]+0.5, svals[0]*0.7),
             arrowprops=dict(arrowstyle="->", color="red"), color="red", fontsize=9)
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2)
plt.tight_layout()
plt.savefig(f"{FIGURES_DIR}fig6_svd_singular_values.pdf", dpi=300, bbox_inches="tight")
```

---

#### Figure 7 — Coherence Metrics
**File:** `figures/fig7_coherence_metrics.pdf`
**Data:** `results/qwen14b_abliterator_results.json` → per-result `coherence` dicts
**Needs A1 run first**

- 3 grouped subplots: avg_length, non_empty_rate, no_repetition_rate
- One bar per method/strength combo (10 bars total including baseline)
- Dashed baseline reference; threshold line at 0.8 for rate metrics

---

#### Figure 8 — Pipeline Architecture Diagram
**File:** `figures/fig8_pipeline_diagram.pdf`
**Data:** None — pure matplotlib drawing
**Can be generated immediately**

- 5 stages as `FancyBboxPatch` rounded rectangles flowing left→right
- Stage 1: "Contrastive Dataset\n(16 PII + 16 Generic\n+ 100 augmented)"
- Stage 2: "Partial Forward Pass\n(causal mask)\nh⁽ˡ⁾ ∈ ℝᵈ"
- Stage 3: "PII Direction\nComputation\nM1: Mean-Diff\nM2: Gaussian\nM3: SVD Rank-k"
- Stage 4: "Weight Ablation\nW_new = W - α·vvᵀW\nDequant→Project\n→Requant"
- Stage 5: "Evaluation\nPII Retention\nPerplexity\nMMU 100%"
- Color coding: data=cornflowerblue, compute=sandybrown, modify=salmon, eval=mediumseagreen
- `FancyArrowPatch` connecting each stage

---

#### Figure 9 — Qualitative Response Comparison
**File:** `figures/fig9_qualitative_responses.pdf`
**Data:** `results/qwen14b_abliterator_results.json` → `baseline.pii_responses` and best ablated
**Needs A1 run first**

- matplotlib table; 4 rows × 4 cols
- Columns: Prompt (truncated 60 chars) | Baseline Response | Best Ablated (M2 s=10) | Result
- Red cell background = PII detected in response; green = PII blocked
- Font size 8; auto-set column widths

---

### Which Figures Can Be Run Immediately

| Figure | Immediate? | Data Needed |
|--------|-----------|-------------|
| Fig 2 | ✅ YES | `eval_*.json` (already exist) |
| Fig 4 | ✅ YES | `eval_*.json` (already exist) |
| Fig 5 | ✅ YES | `qwen05b_sweep_results.json` (manual) |
| Fig 8 | ✅ YES | No data needed |
| Fig 1 | ⏳ After A1 | `qwen14b_abliterator_results.json` |
| Fig 3 | ⏳ After A1 | `qwen14b_abliterator_results.json` |
| Fig 6 | ⏳ After A1 | `qwen14b_abliterator_results.json` |
| Fig 7 | ⏳ After A1 | `qwen14b_abliterator_results.json` |
| Fig 9 | ⏳ After A1 | `qwen14b_abliterator_results.json` |

---

## Stream C — Full Research Paper

### C1. New directory: `paper/`

```bash
cp -r proposal/ paper/
mv paper/proposal.tex paper/paper.tex
```

Add packages to preamble:
```latex
\usepackage{algorithm}
\usepackage{algpseudocode}
\usepackage{subcaption}
\usepackage{multirow}
\usepackage{xcolor}
\usepackage{booktabs}    % already included
```

### C2. Section-by-Section Changes

#### Abstract (rewrite with 14B numbers)
Replace all 0.5B numbers. Key stats to use:
- Baseline: **46.7% PII retention, PPL=2.46, MMLU=100%**
- Best ablated (SVD s=3.5): **20% PII retention, PPL=4.08, MMLU=100%**
- Relative reduction: **57% fewer PII leaks**
- MMLU: **fully preserved (100%) across all conditions**

#### Introduction (minor edit)
Add: "validated on Qwen 2.5 14B (48 layers, 5120-dim) on consumer hardware (Apple M2 Max)"

#### Related Work (keep existing 4 subsections)
Minor add in 2.1: cite ConfAIde (Mireshghallah et al. 2023) for contextual integrity evaluation

#### NEW Section 3: Experimental Setup

```
3.1 Models and Hardware
    - Local (Apple M2 Max 32GB): Qwen 2.5 14B 4-bit, Llama 3 8B 4-bit, Qwen 0.5B 4-bit
    - iLabs (Rutgers, RTX A6000 48GB): full-precision fp16 models (upcoming)

3.2 Hyperparameter Table (booktabs)
    SVD Rank k=8, Gaussian σ=6.0, Strengths={5,10,20}, Layer range=±3,
    Prompts=116 PII + 116 Generic (16 base + 100 augmented)

3.3 Evaluation Protocol
    PII Retention: 60 prompts × 10 categories, regex detection
    Perplexity: ~500-token computing history passage, autoregressive NLL
    MMLU: 40 custom MCQ across 8 subjects (physics/chemistry/biology/math/
          history/geography/CS/logic)
    Coherence: avg_length, non_empty_rate (>0.8=OK), no_repetition_rate (>0.8=OK)
```

#### Section 4: Proposed Approach (keep existing + expand)

Add **Subsection 4.5: Target Layer Discovery**

Describe `auto_find_target_layer()` scoring:
```
score(ℓ) = PII_retention × 100 + PPL_delta
```
Layers with PPL spike > 10 are invalidated. The function sweeps layers from `num_layers // 3` to `num_layers * 2 // 3`.

Add **Algorithm 1 pseudocode box**:

```latex
\begin{algorithm}
\caption{PII Abliteration Pipeline}
\begin{algorithmic}[1]
\Require Model $M$, PII prompts $\mathcal{P}_{pii}$, Generic prompts $\mathcal{P}_{gen}$, strength $\alpha$, rank $k$
\State Collect activations: $\mathbf{H}_{pii} \gets \text{ForwardPass}(M, \mathcal{P}_{pii})$,
       $\mathbf{H}_{gen} \gets \text{ForwardPass}(M, \mathcal{P}_{gen})$
\State Auto-discover: $\ell^* \gets \arg\min_{\ell} \text{Score}(M, \ell)$
\State Compute PII direction(s): $\mathbf{v}$ or $\mathbf{V}_k \gets \text{Method}(\mathbf{H}_{pii}, \mathbf{H}_{gen}, \ell^*)$
\For{each targeted layer $\ell \in [\ell^*-r,\, \ell^*+r]$}
    \State $\mathbf{W} \gets \text{Dequantize}(\mathbf{W}_{\text{quant}})$
    \State $\mathbf{W}_{\text{new}} \gets \mathbf{W} - \alpha\,\mathbf{v}\mathbf{v}^\top\mathbf{W}$
    \State $\mathbf{W}_{\text{quant}} \gets \text{Requantize}(\mathbf{W}_{\text{new}})$
\EndFor
\State \Return Modified model $M'$ with suppressed PII recall
\end{algorithmic}
\end{algorithm}
```

#### NEW Section 5: Results

- **Table 2**: Full 9-configuration results for Qwen 14B

| Method | α | PII Ret. | PPL | PPL Δ | MMLU | Coherent |
|--------|---|----------|-----|-------|------|---------|
| Baseline | — | 46.7% | 2.46 | +0.0 | 100% | OK |
| M1 SingleDir | 5 | ? | ? | ? | ? | ? |
| M2 MultiLayer | 5 | ? | ? | ? | ? | ? |
| ... | ... | ... | ... | ... | ... | ... |
*(filled from qwen14b_abliterator_results.json after A1 run)*

- **Figure 1** (tradeoff scatter) with caption
- **Figure 2** (PII heatmap) — note "Addresses already at 0% baseline"
- **Figure 3** (layer separability) — note peak layer location
- **Figure 4** (MMLU) — note "preserved at 100% across all conditions"
- Cross-model comparison mini-table: Qwen 0.5B vs. 14B best-ablated numbers

#### NEW Section 6: Analysis and Discussion

```
6.1 Privacy-Utility Tradeoff Structure
    - M2 (Gaussian) = best coherence preservation; good for production use
    - SVD + low α = best tradeoff on 14B (57% PII reduction, PPL +66%)
    - Why 14B responds differently than 0.5B (larger PII subspace, better capacity)

6.2 Layer Separability Analysis
    - Where does PII encoding concentrate in 48-layer Qwen 14B?
    - Compare to 24-layer 0.5B (was layer 12)
    - PII encoding appears in mid-to-late-middle layers (consistent with prior
      concept-encoding literature)

6.3 Quantization Effects
    - α > 1 required to overcome 4-bit requantization noise
    - Full-precision models (iLabs) should show cleaner transitions at lower α

6.4 Failure Mode Analysis
    - Addresses: already 0% at baseline — rare structured format, regex misses variants
    - Phone/email: most persistent — structural attention patterns?
    - High PPL in M1/M3: over-projection damages general language representations
```

#### NEW Section 7: Limitations

1. Regex-based PII detection is a lower bound (misses paraphrased echoes)
2. 4-bit quantization is a confound — iLabs full-precision experiments pending
3. 60-prompt eval set may not generalize to all PII prompt phrasings
4. Only `down_proj` and `o_proj` targeted — `q_proj`, `k_proj`, `v_proj` untouched
5. No formal privacy guarantees (unlike DP-SGD)
6. `auto_find_target_layer()` is greedy; not guaranteed to find global optimum

#### NEW Section 8: Future Work

- Fine-grained strength sweep (α ∈ {0.5…50}, 12 levels) on iLabs
- Cross-model direction transfer: does PII direction from Llama transfer to Mistral?
- DP-SGD comparison baseline (critical for reviewer credibility)
- Full MMLU (57 subjects, 14k questions), TruthfulQA, HellaSwag
- Membership inference attack rate as formal unlearning verification
- Hybrid: abliteration + lightweight LoRA fine-tuning on retained data

#### Conclusion (expand)

Restate: 57% reduction in PII retention (46.7% → 20%), full MMLU preservation, no retraining
required. Position abliteration as practical post-hoc privacy remediation tool for open-weight
models.

#### Appendix A — Full 60 PII Test Prompts
Include all prompts from `evaluate_unlearning.py` lines 24–103 grouped by category.
Critical for reproducibility.

#### Appendix B — Complete Results Table
All 9 configs × 2 models (Qwen 0.5B + Qwen 14B) with all metrics.

#### Appendix C — Hyperparameter Sensitivity
Table for σ, layer range, SVD rank (from iLabs experiments when available).

---

## Output Directory Structure (Final State)

```
NLP_Project/
├── mlx_qwen14b_abliterator.py      ← modified: adds JSON save
├── visualizations.py               ← new: generates all 9 figures
├── results/
│   ├── qwen14b_abliterator_results.json   ← from abliterator run
│   └── qwen05b_sweep_results.json         ← manual transcription
├── figures/
│   ├── fig1_privacy_utility_tradeoff.pdf
│   ├── fig2_pii_category_heatmap.pdf
│   ├── fig3_layer_separability.pdf
│   ├── fig4_mmlu_subject_breakdown.pdf
│   ├── fig5_strength_sweep_curves.pdf
│   ├── fig6_svd_singular_values.pdf
│   ├── fig7_coherence_metrics.pdf
│   ├── fig8_pipeline_diagram.pdf
│   └── fig9_qualitative_responses.pdf
├── paper/
│   ├── paper.tex                   ← full submission paper
│   ├── custom.bib                  ← extended bibliography
│   ├── acl.sty
│   ├── acl_natbib.bst
│   └── paper.pdf                   ← compiled output
├── proposal/                       ← original, unchanged
└── docs/
    ├── RESEARCH_PAPER_PLAN.md      ← this file
    └── ILABS_EXPERIMENTS.md
```

---

## Data Flow

```
eval_baseline.json ─────────────────────────────────┐
eval_unlearned.json ─────────────────────────────────┼──→ fig2, fig4
eval_unlearned_s3.5.json ───────────────────────────┘

results/qwen05b_sweep_results.json (manual) ──────────────→ fig5

mlx_qwen14b_abliterator.py (modified)
    └──── RUN ──→ results/qwen14b_abliterator_results.json
                        │
          ┌─────────────┼──────────────┐
          ▼             ▼              ▼
      fig1, fig3    fig6, fig7    fig9 (responses)

figures/*.pdf ────────────────────────────────────────→ paper/paper.tex → paper.pdf
```

---

## Phase-by-Phase Execution

### Phase 1 — Now, No GPU (≈2 hours)
1. Create `results/` dir, write `qwen05b_sweep_results.json` manually
2. Write `visualizations.py`
3. `pip install matplotlib seaborn pandas numpy`
4. `python3 visualizations.py` → generates Fig 2, 4, 5, 8

### Phase 2 — Next Abliterator Run (≈5 min on M2 Max)
1. Add JSON save block to `mlx_qwen14b_abliterator.py`
2. `python3 mlx_qwen14b_abliterator.py`
3. `python3 visualizations.py` → all 9 figures generated

### Phase 3 — Paper Writing (≈3–4 hours)
1. `cp -r proposal/ paper/` → `mv paper/proposal.tex paper/paper.tex`
2. Add packages, write new sections per spec above
3. Reference figures: `\includegraphics[width=\columnwidth]{../figures/figN_*.pdf}`
4. Compile: `pdflatex paper.tex && bibtex paper && pdflatex paper.tex && pdflatex paper.tex`

### Phase 4 — iLabs (Parallel, Not Blocking)
- Run 108-config sweep
- Re-run visualizations → camera-ready Fig 1 and Fig 5 with dense data points

---

## Verification

After Phase 2:
```bash
ls figures/        # 9 PDFs
python3 -c "import json; d=json.load(open('results/qwen14b_abliterator_results.json')); \
            print(len(d['ablation_results']), 'ablation results,', \
            len(d['layer_separability']['scores']), 'layer scores')"
# Expected: 9 ablation results, 48 layer scores
```

After Phase 3:
```bash
cd paper && pdflatex paper.tex 2>&1 | grep -c "Error"   # Should be 0
ls -lh paper.pdf                                         # Should be > 500 KB
```
