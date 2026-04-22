#!/bin/bash
set -euo pipefail

REMOTE_HOST="${ICONOCLAST_REMOTE_HOST:-vp752@ilab.cs.rutgers.edu}"
REMOTE_DIR="${ICONOCLAST_REMOTE_DIR:-~/iconoclast}"

ssh "$REMOTE_HOST" "cd $REMOTE_DIR && latest=\$(ls -1t logs/*.out 2>/dev/null | head -n 1) && if [ -z \"\${latest:-}\" ]; then echo 'No log files found'; exit 1; fi; echo \"Tailing \$latest\"; tail -n 200 -f \"\$latest\""
