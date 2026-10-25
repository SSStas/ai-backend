#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

SSH_HOST="colab-gpu"
REMOTE_DIR="/content/ai-backend"

echo "Deploying AI Backend to Colab..."

echo "Uploading project..."

tar \
    --exclude='.git' \
    --exclude='.venv' \
    --exclude='runtime' \
    --exclude='__pycache__' \
    -C "$PROJECT_DIR" \
    -czf - . \
| ssh "$SSH_HOST" \
    "rm -rf '$REMOTE_DIR' &&
     mkdir -p '$REMOTE_DIR' &&
     tar -xzf - -C '$REMOTE_DIR'"

echo "Preparing and bootstrapping remote runtime..."

ssh "$SSH_HOST" "
    set -e
    cd '$REMOTE_DIR'

    bash deploy/colab/prepare.sh
    bash scripts/bootstrap.sh
    bash scripts/start.sh
"

echo
echo "Deployment complete."
