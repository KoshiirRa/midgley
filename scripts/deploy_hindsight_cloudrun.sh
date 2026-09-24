#!/usr/bin/env bash
set -e

# ============================================================================
# Google Cloud Run Deployment Script for Vectorize Hindsight Agent Memory
# Issue #230: [Weekly Review 2.0] Qualitative Anomaly Post-Mortems (Retain-Recall-Reflect)
# ============================================================================

# Source .env file if present in project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
elif [ -f ".env" ]; then
    set -a
    source ".env"
    set +a
fi

# Hindsight Database Configuration (Must be provided via environment or Google Cloud Secret Manager)
GCP_PROJECT_ID="${GCP_PROJECT_ID:-midgley}"

SERVICE_NAME="midgley-hindsight"
REGION="${GCP_REGION:-us-central1}"
PROJECT_ID="${GCP_PROJECT_ID}"
IMAGE="ghcr.io/vectorize-io/hindsight:latest"

# 1. Check required environment variables
if [ -z "$SUPABASE_DATABASE_URL" ] && [ -z "$HINDSIGHT_DB_SECRET_NAME" ]; then
    echo "⚠️ ERROR: SUPABASE_DATABASE_URL or HINDSIGHT_DB_SECRET_NAME is not set."
    echo "Please set SUPABASE_DATABASE_URL (e.g. export SUPABASE_DATABASE_URL='postgresql://...') or set HINDSIGHT_DB_SECRET_NAME before deploying."
    exit 1
fi

if [ -z "$GEMINI_API_KEY" ]; then
    echo "⚠️ ERROR: GEMINI_API_KEY is required by the Hindsight MemoryEngine container."
    echo "Please export GEMINI_API_KEY='AIzaSy...' or add it to .env before running this deploy script."
    exit 1
fi

echo "🚀 Deploying Hindsight Agent Memory Service to Google Cloud Run..."
echo "Service Name: $SERVICE_NAME"
echo "Region:       $REGION"
echo "Image:        $IMAGE"
echo "Scale Policy: Min Instances = 0 (Scale-to-Zero for $0 Idle Cost)"

# Default LLM model for Hindsight fact extraction & reasoning (gemini-2.5-flash for token-efficient low cost)
HINDSIGHT_LLM_MODEL="${HINDSIGHT_LLM_MODEL:-gemini-2.5-flash}"

# 2. Execute gcloud deployment using Secret Manager or secure env
SECRETS_FLAG=""
if [ -n "$HINDSIGHT_DB_SECRET_NAME" ]; then
    SECRETS_FLAG="--set-secrets=HINDSIGHT_API_DATABASE_URL=${HINDSIGHT_DB_SECRET_NAME}:latest,DATABASE_URL=${HINDSIGHT_DB_SECRET_NAME}:latest"
fi

ENV_VARS="HINDSIGHT_API_PORT=8888,HINDSIGHT_API_RUN_MIGRATIONS_ON_STARTUP=false,HINDSIGHT_API_SKIP_LLM_VERIFICATION=true,HINDSIGHT_API_LLM_PROVIDER=gemini,HINDSIGHT_API_LLM_MODEL=$HINDSIGHT_LLM_MODEL,HINDSIGHT_API_LLM_API_KEY=$GEMINI_API_KEY,HINDSIGHT_API_DB_POOL_MAX=10"
if [ -z "$HINDSIGHT_DB_SECRET_NAME" ]; then
    ENV_VARS="$ENV_VARS,HINDSIGHT_API_DATABASE_URL=$SUPABASE_DATABASE_URL,DATABASE_URL=$SUPABASE_DATABASE_URL"
fi

DEPLOY_CMD="gcloud run deploy \"$SERVICE_NAME\" \
    --project \"$PROJECT_ID\" \
    --image \"$IMAGE\" \
    --platform managed \
    --region \"$REGION\" \
    --allow-unauthenticated \
    --port 8888 \
    --min-instances 0 \
    --max-instances 1 \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --set-env-vars \"$ENV_VARS\""

if [ -n "$SECRETS_FLAG" ]; then
    DEPLOY_CMD="$DEPLOY_CMD $SECRETS_FLAG"
fi

eval $DEPLOY_CMD

# 3. Retrieve service URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --project "$PROJECT_ID" --platform managed --region "$REGION" --format 'value(status.url)')

echo "✅ Deployment Complete!"
echo "🔗 Hindsight Cloud Run Endpoint: $SERVICE_URL"
echo ""
echo "To link with Midgley, export the following environment variable:"
echo "export HINDSIGHT_API_URL=\"$SERVICE_URL\""
