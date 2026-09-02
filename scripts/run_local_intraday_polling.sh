#!/usr/bin/env bash
set -e

# Midgley Local Dev Server Intraday Polling Runner
# Executes 15-minute intraday news polling and anomaly detection on dev-vm

PROJECT_DIR="/home/marty/projects/midgley"
cd "$PROJECT_DIR"

# Source environment variables if .env exists
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] Starting Local Dev Intraday Event Polling..."

# Activate python virtual environment
if [ -f "/home/marty/.antigravity-env/bin/activate" ]; then
    source /home/marty/.antigravity-env/bin/activate
fi

# Execute Intraday Polling Cycle
python -m src.intraday_event_monitor

# Auto-commit updated history, intraday events & dashboard if on dev branch and working tree is dirty
if [ -d ".git" ]; then
    git add README.md docs/ data/prediction_history.csv data/intraday_events.json 2>/dev/null || true
    if ! git diff-index --quiet HEAD --; then
        git commit -m "chmod: Intraday event anomaly revision & public dashboard update [skip ci]" || true
        echo "Committed intraday forecast revisions to dev branch."
        git push origin dev || echo "Warning: Failed to push intraday forecast revisions to origin dev."
    fi
fi

echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] Local Dev Intraday Polling Complete."
