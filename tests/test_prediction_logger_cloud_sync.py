"""
Unit Tests for Prediction History Cloud Synchronization (tests/test_prediction_logger_cloud_sync.py)
Issue #82: Synchronize Prediction History & Lookup Cache with Serverless Postgres (Neon / D1)
"""

import os
import json
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.prediction_logger import (
    sync_predictions_to_cloud,
    get_cloud_sync_status,
    log_predictions
)
from src.api_server import app


@pytest.fixture
def clean_env(monkeypatch):
    """Cleans cloud database environment variables for isolated offline test execution."""
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("TURSO_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("CLOUDFLARE_CACHE_URL", raising=False)
    monkeypatch.delenv("CLOUDFLARE_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("NEON_DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTGRES_URL", raising=False)


def test_offline_fallback(clean_env):
    """Verifies that 0 credentials gracefully fall back to local CSV storage."""
    df = pd.DataFrame([{
        "log_timestamp": "2026-09-03 12:00:00",
        "forecast_target_date": "2026-09-10",
        "region": "Tulsa_OK",
        "model_version": "v1.4-Test",
        "run_type": "TEST_RUN",
        "current_base_price": 3.85,
        "predicted_5d_price": 3.90
    }])
    res = sync_predictions_to_cloud(df)
    assert res["status"] == "offline_fallback"
    assert res["provider"] == "local_csv"
    assert res["synced_rows"] == 1


def test_get_cloud_sync_status(clean_env):
    """Verifies get_cloud_sync_status output schema."""
    status_info = get_cloud_sync_status()
    assert "cloud_sync_enabled" in status_info
    assert "active_providers" in status_info
    assert status_info["fallback_store"] == "local_csv"
    assert "total_local_records" in status_info
    assert isinstance(status_info["total_local_records"], int)


def test_turso_cloud_sync_mocked(monkeypatch):
    """Verifies Turso Edge REST pipeline synchronization when credentials exist."""
    monkeypatch.setenv("TURSO_DATABASE_URL", "https://test-db.turso.io")
    monkeypatch.setenv("TURSO_AUTH_TOKEN", "test-token-123")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.read.return_value = b'{"results":[{"type":"ok"}]}'

    df = pd.DataFrame([{
        "log_timestamp": "2026-09-03 12:00:00",
        "forecast_target_date": "2026-09-10",
        "region": "Tulsa_OK",
        "model_version": "v1.4-Test",
        "run_type": "TEST_RUN",
        "current_base_price": 3.85,
        "predicted_5d_price": 3.90
    }])

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = sync_predictions_to_cloud(df)
        assert res["status"] == "synced"
        assert res["provider"] == "turso_edge"
        assert res["synced_rows"] == 1


def test_cloudflare_d1_cloud_sync_mocked(monkeypatch):
    """Verifies Cloudflare D1 Edge Worker REST synchronization when credentials exist."""
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.setenv("CLOUDFLARE_CACHE_URL", "https://midgley-cache-worker.workers.dev")
    monkeypatch.setenv("CLOUDFLARE_AUTH_TOKEN", "test-cf-token")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.read.return_value = b'{"status":"ok"}'

    df = pd.DataFrame([{
        "log_timestamp": "2026-09-03 12:00:00",
        "forecast_target_date": "2026-09-10",
        "region": "Newark_DE",
        "model_version": "v1.4-Test",
        "run_type": "TEST_RUN",
        "current_base_price": 3.35,
        "predicted_5d_price": 3.40
    }])

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = sync_predictions_to_cloud(df)
        assert res["status"] == "synced"
        assert res["provider"] == "cloudflare_d1"
        assert res["synced_rows"] == 1


def test_api_server_cloud_endpoints(clean_env):
    """Verifies GET /api/v1/forecast/cloud-status and POST /api/v1/forecast/cloud-sync endpoints."""
    client = TestClient(app)
    
    # 1. Test GET /api/v1/forecast/cloud-status
    resp = client.get("/api/v1/forecast/cloud-status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "cloud_sync_status" in data
    assert data["cloud_sync_status"]["fallback_store"] == "local_csv"

    # 2. Test POST /api/v1/forecast/cloud-sync
    post_resp = client.post("/api/v1/forecast/cloud-sync")
    assert post_resp.status_code == 200
    post_data = post_resp.json()
    assert post_data["status"] == "success"
    assert "result" in post_data
    assert post_data["result"]["provider"] == "local_csv"
