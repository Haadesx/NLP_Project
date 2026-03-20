Context
The NLP project implements directional ablation (abliteration) for PII privacy in LLMs. The core
experiments are working — Qwen 14B shows 46.7% → 20% PII retention with MMLU 100% preserved — but:

Results are only printed to console, never saved in a machine-readable format
No visualizations exist to showcase the work
The existing proposal/proposal.tex is a course proposal, not a submission-ready paper

The goal is to: (a) serialize all intermediate data, (b) generate 9 paper-quality figures, and (c)
upgrade the proposal into a full research paper. The three streams have a strict dependency chain:
Serialize first → Visualize second → Write paper third.

Stream A — Result Serialization (Do First)
A1. Modify mlx_qwen14b_abliterator.py
File: /Volumes/Auxilary/Side_Projects/NLP_Project/mlx_qwen14b_abliterator.py
At the end of main(), after print_results(baseline, results, target_layer), add a JSON save block:
pythonimport json, os
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
"layer_separability": {
"scores": [float(separabilities[i].item()) for i in range(len(separabilities))],
"peak_layer": peak_layer,
"peak_score": float(separabilities[peak_layer].item())
},
"svd_singular_values": [float(x) for x in svals.tolist()],
"baseline": {
"pii_retention": baseline["pii_retention"],
"perplexity": baseline["perplexity"],
"coherence": baseline["coherence"],
"pii_responses": [{"prompt": p, "response": r} for p, r in baseline["pii_responses"]]
},
"ablation_results": [
{
"method": r["method"],
"method_id": r["method"].split(":")[0], # "M1", "M2", "M3"
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
print(" Saved → results/qwen14b_abliterator_results.json")
Key conversion notes:

separabilities is an MLX array — use .item() per element (not .tolist() directly)
svals is from compute_pii_directions_svd() which returns an MLX array — call mx.eval(svals) before saving
Wrap in try/except Exception as e: print(f" Warning: could not save JSON: {e}") to be safe

A2. Create results/qwen05b_sweep_results.json (Manual Transcription)
Create this file manually from the README table (the 9 Qwen 0.5B results):
json{
"model": "mlx-community/Qwen1.5-0.5B-Chat-4bit",
"baseline": {"pii_retention": 0.25, "perplexity": 12.8, "coherence": "OK"},
"ablation_results": [
{"method_id": "M1", "strength": 5.0, "pii_retention": 0.0, "perplexity": 142.1, "coherence": "DEGRADED"},
{"method_id": "M2", "strength": 5.0, "pii_retention": 0.75, "perplexity": 14.2, "coherence": "OK"},
{"method_id": "M3", "strength": 5.0, "pii_retention": 0.0, "perplexity": 482.8, "coherence": "DEGRADED"},
{"method_id": "M1", "strength": 10.0, "pii_retention": 0.0, "perplexity": 2114.0, "coherence": "OK"},
{"method_id": "M2", "strength": 10.0, "pii_retention": 0.5, "perplexity": 17.8, "coherence": "OK"},
{"method_id": "M3", "strength": 10.0, "pii_retention": 0.0, "perplexity": 15496.0,"coherence": "DEGRADED"},
{"method_id": "M2", "strength": 20.0, "pii_retention": 0.5, "perplexity": 34.2, "coherence": "OK"}
]
}

Stream B — Visualization System
B1. Create visualizations.py
File: /Volumes/Auxilary/Side_Projects/NLP_Project/visualizations.py
Install deps first: pip install matplotlib seaborn pandas numpy
Script structure:
python#!/usr/bin/env python3
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
with open(path) as f: return json.load(f)

def fig1_privacy_utility_tradeoff(): ...
def fig2_pii_category_heatmap(): ...
def fig3_layer_separability(): ...
def fig4_mmlu_subject_breakdown(): ...
def fig5_strength_sweep_curves(): ...
def fig6_svd_singular_values(): ...
def fig7_coherence_metrics(): ...
def fig8_architecture_diagram(): ...
def fig9_qualitative_response_table(): ...

if **name** == "**main**":
for fn in [fig1_privacy_utility_tradeoff, fig2_pii_category_heatmap,
fig3_layer_separability, fig4_mmlu_subject_breakdown,
fig5_strength_sweep_curves, fig6_svd_singular_values,
fig7_coherence_metrics, fig8_architecture_diagram,
fig9_qualitative_response_table]:
try:
fn()
except FileNotFoundError as e:
print(f" Skipping {fn.**name**}: missing data — {e}")
B2. The 9 Figures
Figure 1 — Privacy–Utility Tradeoff Scatter

File: figures/fig1_privacy_utility_tradeoff.pdf
Data: results/qwen14b_abliterator_results.json → ablation_results array
X-axis: Perplexity (log scale), Y-axis: PII Retention (0–1)
Color by method (M1=blue, M2=orange, M3=green); marker shape by strength (s=5→circle, s=10→square, s=20→triangle)
Black star for baseline; label each point with its strength value
Add baseline PPL vertical dashed reference line

Figure 2 — Per-Category PII Heatmap

File: figures/fig2_pii_category_heatmap.pdf
Data: eval_baseline.json, eval_unlearned.json, eval_unlearned_s3.5.json
10-row × 3-column seaborn heatmap; RdYlGn_r colormap; annotate cells with "3/6" fractions
Sort rows by baseline retention descending (email/phone at top, address at bottom)

Figure 3 — Layer-Wise Separability

File: figures/fig3_layer_separability.pdf
Data: results/qwen14b_abliterator_results.json → layer_separability.scores (48 values)
Line plot + shaded area; red dashed vertical line at peak_layer
Overlay Gaussian kernel w(l) = exp(-(l-peak)²/2σ²) as orange dashed line
Requires A1 to be run first

Figure 4 — MMLU Subject Breakdown

File: figures/fig4_mmlu_subject_breakdown.pdf
Data: All 3 eval JSON files → mmlu_reasoning.by_subject
Grouped bar chart; 8 subjects on x-axis; 3 bars per subject
Note: all conditions show 100% → flat chart is a strong positive result; annotate prominently

Figure 5 — Strength Sweep Curves

File: figures/fig5_strength_sweep_curves.pdf
Data: results/qwen05b_sweep_results.json
Two subplots: Left = PII Retention vs α, Right = Perplexity (log) vs α
One line per method; filled circles = coherent, X markers = degraded
Annotation: "iLabs sweep will extend to 12 levels (α ∈ {0.5…50})"

Figure 6 — SVD Singular Values Scree Plot

File: figures/fig6_svd_singular_values.pdf
Data: results/qwen14b_abliterator_results.json → svd_singular_values (8 values)
Bar chart with line; secondary y-axis showing cumulative variance %
Arrow annotation at rank=8 ("Selected rank"); annotate elbow if present
Requires A1 to be run first

Figure 7 — Coherence Metrics

File: figures/fig7_coherence_metrics.pdf
Data: results/qwen14b_abliterator_results.json → per-result coherence dicts
Grouped bar chart: avg_length, non_empty_rate, no_repetition_rate for all 10 conditions
Dashed reference lines at baseline values; threshold line at 0.8 for rate metrics
Requires A1 to be run first

Figure 8 — Pipeline Architecture Diagram

File: figures/fig8_pipeline_diagram.pdf
Pure matplotlib FancyBboxPatch + FancyArrowPatch — no data needed
5 stages left→right: Dataset → Activation Collection → PII Direction (M1/M2/M3) → Weight Ablation → Evaluation
Color-coded by stage type (data=blue, compute=orange, modify=red, eval=green)
Include the math W_new = W - α·vvᵀW in the ablation box

Figure 9 — Qualitative Response Table

File: figures/fig9_qualitative_responses.pdf
Data: results/qwen14b_abliterator_results.json → baseline.pii_responses and best-ablated responses
matplotlib table; 4 rows × 4 cols (Prompt | Baseline | Best Ablated | Result)
Color cell red if response contains PII, green if blocked
Requires A1 to be run first

B3. Which Figures Can Be Generated Immediately
FigureNeeds A1 Run?Data SourceFig 1YESqwen14b_abliterator_results.jsonFig 2NO3 existing eval JSON filesFig 3YESqwen14b_abliterator_results.jsonFig 4NO3 existing eval JSON filesFig 5NOqwen05b_sweep_results.json (manual)Fig 6YESqwen14b_abliterator_results.jsonFig 7YESqwen14b_abliterator_results.jsonFig 8NONo data neededFig 9YESqwen14b_abliterator_results.json

Stream C — Full Research Paper
C1. New File: paper/paper.tex
Copy proposal/ to paper/ then expand. Add these LaTeX packages:
latex\usepackage{algorithm}
\usepackage{algpseudocode}
\usepackage{subcaption}
\usepackage{multirow}
\usepackage{xcolor}

```

### C2. Section-by-Section Spec

**Abstract** — Replace 0.5B numbers with 14B numbers:
- Baseline 46.7% PII retention → best ablated 20% (57% reduction), PPL 2.46→4.08, MMLU 100% preserved

**Introduction** — Keep existing, minor edit: add "consumer hardware (Apple M2 Max) and validated on Qwen 2.5 14B"

**Related Work** — Keep existing 4 subsections; add reference to ConfAIde (Mireshghallah 2023) in subsection 2.1

**New Section 3: Experimental Setup**
- Subsection 3.1: Models and Hardware (14B 4-bit, 8B 4-bit, 0.5B 4-bit on M2 Max; fp16 on iLabs A6000)
- Subsection 3.2: Hyperparameter Table (booktabs table — SVD_RANK=8, σ=6.0, strengths, layer range, prompt counts)
- Subsection 3.3: Evaluation Protocol (PII 60 prompts, PPL ~500 tokens, MMLU 40 questions)

**Section 4: Proposed Approach** — Keep existing 4 subsections + add:
- Subsection 4.5: "Layer Discovery" — describe `auto_find_target_layer()` scoring function
- Algorithm box (using `algorithmic` environment) with the 5-step pseudocode

**New Section 5: Results**
- Table 2: Full 9-configuration results for Qwen 14B (Method × Strength × PII/PPL/MMLU/Coherence)
- Figure 1 (tradeoff scatter), Figure 2 (heatmap), Figure 3 (layer sep), Figure 4 (MMLU bars)
- Cross-model comparison: 0.5B vs. 14B best-ablated numbers side by side

**New Section 6: Analysis and Discussion**
- 6.1 Privacy-Utility Tradeoff: M2 best coherence; SVD+low-α best tradeoff on 14B
- 6.2 Layer Analysis: where does PII encoding concentrate in 14B vs. 0.5B?
- 6.3 Quantization Effects: why α > 1 is required; implications for fp16 experiments
- 6.4 Failure Modes: which PII categories are hardest to suppress and why

**New Section 7: Limitations**
- Regex detection is lower bound (misses paraphrased PII)
- 4-bit quantization confound (iLabs experiments pending)
- No formal privacy guarantees unlike DP-SGD
- Only `down_proj` and `o_proj` targeted — other weight matrices untouched

**New Section 8: Future Work**
- Fine-grained strength sweep (12 levels, 0.5–50)
- Cross-model direction transfer study
- DP-SGD comparison baseline
- Full MMLU/TruthfulQA/HellaSwag benchmarks on iLabs

**Conclusion** — Expand existing: restate 57% PII reduction, full MMLU preservation, and practical significance as post-hoc inference-time tool

**Appendix A** — Full 60 PII test prompts (from `evaluate_unlearning.py` lines 24–103), grouped by category

**Appendix B** — All hyperparameter sensitivity results (from iLabs experiments when available)

**Appendix C** — Complete results table for all 9 configurations × 2 models

---

## Data Flow Summary
```

eval_baseline.json ──────────────────────────────────────────┐
eval_unlearned.json ─────────────────────────────────────────┼──→ fig2, fig4
eval_unlearned_s3.5.json ────────────────────────────────────┘

results/qwen05b_sweep_results.json (manual transcription) ────────→ fig5

mlx_qwen14b_abliterator.py (add JSON save) ──── RUN ──→ results/qwen14b_abliterator_results.json
│
┌─────────────────┴────────────────────┐
↓ ↓
fig1, fig3, fig6 fig7, fig9
(tradeoff, layer sep, SVD) (coherence, responses)

figures/\*.pdf ──────────────────────────────────────────────────────→ paper/paper.tex → paper.pdf

Order of Operations
Phase 1 — Right Now (No GPU Needed, ~2 hours)

Create results/ directory
Write results/qwen05b_sweep_results.json manually
Write visualizations.py with all 9 figure functions
pip install matplotlib seaborn pandas numpy
Run python3 visualizations.py → generates Fig 2, 4, 5, 8 immediately
(Fig 1, 3, 6, 7, 9 will print "skipping — missing data")

Phase 2 — Next Abliterator Run (~5 min on M2 Max)

Modify mlx_qwen14b_abliterator.py to add JSON serialization
Run python3 mlx_qwen14b_abliterator.py
Output: results/qwen14b_abliterator_results.json
Re-run python3 visualizations.py → all 9 figures generated

Phase 3 — Paper Writing (~3–4 hours)

cp -r proposal/ paper/
Rename paper/proposal.tex → paper/paper.tex
Add packages, write new sections per spec above
Include figures: \includegraphics[width=\columnwidth]{../figures/figN\_\*.pdf}
Compile: pdflatex paper.tex && bibtex paper && pdflatex paper.tex && pdflatex paper.tex

Phase 4 — iLabs (Parallel, Not Blocking)

Run 108-configuration sweep; update results/ with dense data
Re-run visualizations → camera-ready versions of Fig 1 and Fig 5

Files to Create/Modify
ActionFileNotesMODIFYmlx_qwen14b_abliterator.pyAdd ~30 lines of JSON save at end of main()CREATEresults/qwen05b_sweep_results.jsonManual, 7 data points from READMECREATEvisualizations.py~400 lines, 9 figure functionsCREATEfigures/ (dir)Auto-created by visualizations.pyCREATEresults/ (dir)Auto-created by abliteratorCREATEpaper/paper.texFull paper, extended from proposal.texCOPYpaper/custom.bibCopy from proposal/custom.bib, add 2–3 new refsCOPYpaper/acl.styCopy from proposal/COPYpaper/acl_natbib.bstCopy from proposal/

Verification
After Phase 2:
bashls figures/ # Should show 9 .pdf files
python3 -c "import json; d=json.load(open('results/qwen14b_abliterator_results.json')); print(len(d['ablation_results']), 'results')"

# Should print: 9 results

After Phase 3:
bashcd paper && pdflatex paper.tex 2>&1 | grep -E "Warning|Error|Overfull"

# Should show only minor overfull warnings, no errors

ls -la paper.pdf # Should exist and be > 500KB (includes embedded figures)
