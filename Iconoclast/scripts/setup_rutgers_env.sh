#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEFAULT_PERSIST_ROOT="/common/users/$USER/iconoclast_ilabs"
if [ ! -d "/common/users/$USER" ]; then
  DEFAULT_PERSIST_ROOT="$HOME/iconoclast_ilabs"
fi

PERSIST_ROOT="${ICONOCLAST_PERSIST_ROOT:-$DEFAULT_PERSIST_ROOT}"
SITE_PACKAGES="${ICONOCLAST_SITE_PACKAGES:-$PERSIST_ROOT/python312-site}"
SYS_PY="${ICONOCLAST_SYS_PY:-/common/system/venv/python312/bin/python}"
BOOTSTRAP_VENV="${ICONOCLAST_BOOTSTRAP_VENV:-$PERSIST_ROOT/bootstrap-venv}"
TMP_WORKDIR="${ICONOCLAST_TMPDIR:-$PERSIST_ROOT/tmp}"

mkdir -p "$PERSIST_ROOT"/{hf-cache,hf-datasets,checkpoints,plots,runs,xdg-cache,xdg-state,tmp}
mkdir -p "$SITE_PACKAGES"

# pip --target does not reliably clean up downgraded packages, so remove the
# most version-sensitive packages explicitly before reinstalling them.
rm -rf \
  "$SITE_PACKAGES"/numpy \
  "$SITE_PACKAGES"/numpy.libs \
  "$SITE_PACKAGES"/numpy-*.dist-info \
  "$SITE_PACKAGES"/huggingface_hub \
  "$SITE_PACKAGES"/huggingface_hub-*.dist-info

export TMPDIR="$TMP_WORKDIR"
export XDG_CACHE_HOME="$PERSIST_ROOT/xdg-cache"
export XDG_STATE_HOME="$PERSIST_ROOT/xdg-state"
export HF_HOME="$PERSIST_ROOT/hf-cache"
export HF_DATASETS_CACHE="$PERSIST_ROOT/hf-datasets"
export TRANSFORMERS_CACHE="$PERSIST_ROOT/hf-cache/transformers"
export HUGGINGFACE_HUB_CACHE="$PERSIST_ROOT/hf-cache/hub"
export HF_HUB_ENABLE_HF_TRANSFER=1
export PIP_NO_CACHE_DIR=1
export PIP_CACHE_DIR="$PERSIST_ROOT/pip-cache"

if [ ! -x "$BOOTSTRAP_VENV/bin/python" ]; then
  python3 -m venv "$BOOTSTRAP_VENV"
fi

"$BOOTSTRAP_VENV/bin/python" -m pip install --upgrade pip

"$BOOTSTRAP_VENV/bin/python" -m pip install --target "$SITE_PACKAGES" --upgrade --no-cache-dir --only-binary=:all: \
  "numpy<2,>=1.26" \
  "huggingface_hub<1.0,>=0.34" \
  questionary \
  pydantic-settings \
  immutabledict \
  hf-transfer \
  sentencepiece \
  optuna \
  safetensors \
  tokenizers \
  regex \
  tqdm \
  requests \
  pyarrow \
  pandas \
  multiprocess \
  xxhash \
  dill \
  fsspec \
  aiohttp \
  httpx \
  rich

"$BOOTSTRAP_VENV/bin/python" -m pip install --target "$SITE_PACKAGES" --upgrade --no-cache-dir --no-deps --only-binary=:all: \
  accelerate \
  datasets \
  peft \
  gguf \
  bitsandbytes \
  "transformers>=5.5"

echo "Rutgers Iconoclast environment is ready:"
echo "  project:      $PROJECT_ROOT"
echo "  sys python:   $SYS_PY"
echo "  bootstrap:    $BOOTSTRAP_VENV"
echo "  site-packages $SITE_PACKAGES"
echo "  state:        $PERSIST_ROOT"
