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

# Default fallback configuration for Midgley Supabase instance
SUPABASE_DATABASE_URL="${SUPABASE_DATABASE_URL:-postgresql://postgres.tmnitbsqbkmgheppogjt:M603z4gsC7E3pICG@aws-0-us-west-2.pooler.supabase.com:5432/postgres}"
GCP_PROJECT_ID="${GCP_PROJECT_ID:-midgley}"

SERVICE_NAME="midgley-hindsight"
REGION="us-central1"
PROJECT_ID="${GCP_PROJECT_ID}"
IMAGE="ghcr.io/vectorize-io/hindsight:latest"

# 1. Check required environment variables
if [ -z "$SUPABASE_DATABASE_URL" ]; then
    echo "⚠️ ERROR: SUPABASE_DATABASE_URL is not set."
    echo "Please set SUPABASE_DATABASE_URL before deploying."
    exit 1
fi

if [ -z "$GEMINI_API_KEY" ]; then
    echo "ℹ️ Notice: GEMINI_API_KEY is not set. Defaulting to offline/deterministic mode."
fi

echo "🚀 Deploying Hindsight Agent Memory Service to Google Cloud Run..."
echo "Service Name: $SERVICE_NAME"
echo "Region:       $REGION"
echo "Image:        $IMAGE"
echo "Scale Policy: Min Instances = 0 (Scale-to-Zero for $0 Idle Cost)"

# 2. Execute gcloud deployment
gcloud run deploy "$SERVICE_NAME" \
    --project "$PROJECT_ID" \
    --image "$IMAGE" \
    --platform managed \
    --region "$REGION" \
    --allow-unauthenticated \
    --port 8888 \
    --min-instances 0 \
    --max-instances 1 \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --set-env-vars HINDSIGHT_API_PORT="8888",HINDSIGHT_API_DATABASE_URL="$SUPABASE_DATABASE_URL",DATABASE_URL="$SUPABASE_DATABASE_URL",HINDSIGHT_API_RUN_MIGRATIONS_ON_STARTUP="true",HINDSIGHT_API_SKIP_LLM_VERIFICATION="true",HINDSIGHT_API_LLM_PROVIDER="gemini",HINDSIGHT_API_LLM_API_KEY="$GEMINI_API_KEY"

# 3. Retrieve service URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --project "$PROJECT_ID" --platform managed --region "$REGION" --format 'value(status.url)')

echo "✅ Deployment Complete!"
echo "🔗 Hindsight Cloud Run Endpoint: $SERVICE_URL"
echo ""
echo "To link with Midgley, export the following environment variable:"
echo "export HINDSIGHT_API_URL=\"$SERVICE_URL\""
