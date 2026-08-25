#!/usr/bin/env bash
set -e

# Midgley Local Dev Server Daily Forecast Runner
# Executes daily gas price LLM forecasting and updates public dashboard on dev-vm

PROJECT_DIR="/home/marty/projects/midgley"
cd "$PROJECT_DIR"

# Source environment variables if .env exists
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] Starting Local Dev Daily Gas Price Forecast..."

# Activate python virtual environment
if [ -f "/home/marty/.antigravity-env/bin/activate" ]; then
    source /home/marty/.antigravity-env/bin/activate
fi

# Execute Full LLM Gas Price Forecasting Pipeline
python run_all.py --use-llm-api

# Regenerate Public Web Dashboard
python -m src.dashboard_generator

# Auto-commit updated history & dashboard if on dev branch and working tree is dirty
if [ -d ".git" ]; then
    git add README.md docs/ data/prediction_history.csv 2>/dev/null || true
    if ! git diff-index --quiet HEAD --; then
        git commit -m "chmod: Daily automated local dev gas price forecast update [skip ci]" || true
        echo "Committed daily forecast updates to dev branch."
    fi
fi

echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] Local Dev Daily Forecast Complete."
