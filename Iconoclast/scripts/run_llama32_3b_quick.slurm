#!/bin/bash -l
#SBATCH -J iconoclast-3b
#SBATCH -o logs/iconoclast-3b-%j.out
#SBATCH -e logs/iconoclast-3b-%j.err
#SBATCH -G 1
#SBATCH --mem=40g
#SBATCH -t 08:00:00

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"
mkdir -p logs

# Optional: uncomment if you want to prefer newer Ampere-class cards.
#SBATCH -C ampere

export HF_HUB_ENABLE_HF_TRANSFER=1
export PYTHONUNBUFFERED=1

# If the model is gated, set HUGGING_FACE_HUB_TOKEN or run `huggingface-cli login` first.
# If your environment already has torch/cuda set up, replace the venv block below with that.
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .

cp config.llama32_3b.quick.toml config.toml

python -m iconoclast.main \
  --model meta-llama/Llama-3.2-3B-Instruct
