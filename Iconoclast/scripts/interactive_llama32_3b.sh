#!/bin/bash
set -euo pipefail

echo "Requesting one GPU interactive session from Rutgers Slurm..."
echo "When the shell starts on the compute node, run the setup block below."
echo
echo "srun -G 1 --mem=40g -t 04:00:00 --pty /bin/bash -l"
echo
echo "Then inside the session:"
cat <<'EOF'
cd /path/to/NLP_PROJECT_NEW/iconoclast
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
export HF_HUB_ENABLE_HF_TRANSFER=1
cp config.llama32_3b.quick.toml config.toml
python -m iconoclast.main \
  --model meta-llama/Llama-3.2-3B-Instruct
EOF
