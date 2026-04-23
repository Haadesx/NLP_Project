#!/bin/bash
set -euo pipefail

REMOTE_HOST="${ICONOCLAST_REMOTE_HOST:-vp752@ilab.cs.rutgers.edu}"
REMOTE_DIR="${ICONOCLAST_REMOTE_DIR:-~/iconoclast}"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

rsync -av --delete \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude 'logs' \
  --exclude '.pytest_cache' \
  --exclude 'checkpoints*' \
  --exclude 'results_cluster' \
  "$PROJECT_ROOT"/ "$REMOTE_HOST:$REMOTE_DIR"/

echo "Synced $PROJECT_ROOT -> $REMOTE_HOST:$REMOTE_DIR"
