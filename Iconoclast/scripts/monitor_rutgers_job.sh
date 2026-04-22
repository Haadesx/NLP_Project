#!/bin/bash
set -euo pipefail

REMOTE_HOST="${ICONOCLAST_REMOTE_HOST:-vp752@ilab.cs.rutgers.edu}"
REMOTE_DIR="${ICONOCLAST_REMOTE_DIR:-~/iconoclast}"

ssh "$REMOTE_HOST" "cd $REMOTE_DIR && echo '--- squeue ---' && squeue -u \$USER && echo && echo '--- recent logs ---' && ls -1t logs 2>/dev/null | head -n 5"
