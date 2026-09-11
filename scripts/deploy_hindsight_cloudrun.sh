#!/usr/bin/env bash
set -e

# ============================================================================
# Google Cloud Run Deployment Script for Vectorize Hindsight Agent Memory
# Issue #230: [Weekly Review 2.0] Qualitative Anomaly Post-Mortems (Retain-Recall-Reflect)
# ============================================================================

SERVICE_NAME="midgley-hindsight"
REGION="us-central1"
PROJECT_ID="${GCP_PROJECT_ID:-midgley}"
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
    --min-instances 0 \
    --max-instances 1 \
    --memory 512Mi \
    --cpu 1 \
    --timeout 30 \
    --set-env-vars HINDSIGHT_API_DATABASE_URL="$SUPABASE_DATABASE_URL",HINDSIGHT_API_LLM_PROVIDER="gemini",HINDSIGHT_API_LLM_API_KEY="$GEMINI_API_KEY"

# 3. Retrieve service URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --project "$PROJECT_ID" --platform managed --region "$REGION" --format 'value(status.url)')

echo "✅ Deployment Complete!"
echo "🔗 Hindsight Cloud Run Endpoint: $SERVICE_URL"
echo ""
echo "To link with Midgley, export the following environment variable:"
echo "export HINDSIGHT_API_URL=\"$SERVICE_URL\""
