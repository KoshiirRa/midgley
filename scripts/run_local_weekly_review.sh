#!/usr/bin/env bash
set -e

# Midgley Local Dev Server Weekly Review Runner
# Executes weekly model review, open GitHub issue self-review evaluation, and updates dashboard

PROJECT_DIR="/home/marty/projects/midgley"
cd "$PROJECT_DIR"

# Source environment variables if .env exists
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] Starting Local Dev Weekly Model Review & Performance Audit..."

# Activate python virtual environment
if [ -f "/home/marty/.antigravity-env/bin/activate" ]; then
    source /home/marty/.antigravity-env/bin/activate
fi

# Execute Full LLM Gas Price Forecasting Pipeline & Backtest
python run_all.py --use-llm-api

# Run Weekly Issue Reporter (Open GitHub Issues Self-Review & Report Generation)
python -m src.weekly_issue_reporter

# Regenerate Public Web Dashboard
python -m src.dashboard_generator

# Auto-commit updated history, metrics & dashboard if working tree is dirty
if [ -d ".git" ]; then
    git add README.md docs/ data/ 2>/dev/null || true
    if ! git diff-index --quiet HEAD --; then
        git commit -m "chrono: Weekly Saturday local dev model performance review & issue audit [skip ci]" || true
        echo "Committed weekly review updates to dev branch."
    fi
fi

echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] Local Dev Weekly Model Review Complete."
