import os
import json
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
import urllib.error

from src.prediction_logger import sync_predictions_to_cloud, get_cloud_sync_status

@pytest.fixture
def sample_prediction_df():
    return pd.DataFrame([{
        "log_timestamp": "2026-09-17 12:00:00",
        "forecast_target_date": "2026-09-22",
        "forecast_horizon_days": 5,
        "region": "Tulsa_OK",
        "model_version": "v1.6-Ipatieff-Tulsa-Ridge",
        "run_type": "DAILY_BATCH",
        "current_base_price": 3.15,
        "predicted_5d_price": 3.20,
        "predicted_direction": "UP",
        "llm_price_pressure": 0.25,
        "data_source_provenance": "test_runner"
    }])

def test_sync_predictions_offline_fallback(sample_prediction_df, monkeypatch):
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("CLOUDFLARE_CACHE_URL", raising=False)
    
    res = sync_predictions_to_cloud(sample_prediction_df)
    assert res["status"] == "offline_fallback"
    assert res["provider"] == "local_csv"

def test_sync_predictions_cloudflare_success(sample_prediction_df, monkeypatch):
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.setenv("CLOUDFLARE_CACHE_URL", "https://midgley-cache-worker.workers.dev")
    monkeypatch.setenv("CLOUDFLARE_AUTH_TOKEN", "test_token")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.read.return_value = b'{"status": "synced", "synced_rows": 1}'

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = sync_predictions_to_cloud(sample_prediction_df)
        assert res["status"] == "synced"
        assert res["provider"] == "cloudflare_d1"
        assert res["synced_rows"] == 1

def test_sync_predictions_cloudflare_http_500_resilience(sample_prediction_df, monkeypatch, caplog):
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.setenv("CLOUDFLARE_CACHE_URL", "https://midgley-cache-worker.workers.dev")

    mock_fp = MagicMock()
    mock_fp.read.return_value = b'{"error": "D1 database execution timeout"}'
    http_err = urllib.error.HTTPError(
        url="https://midgley-cache-worker.workers.dev/api/v1/sync/predictions",
        code=500,
        msg="Internal Server Error",
        hdrs={},
        fp=mock_fp
    )

    with patch("urllib.request.urlopen", side_effect=http_err):
        res = sync_predictions_to_cloud(sample_prediction_df)
        assert res["status"] == "offline_fallback"
        assert "HTTP Error 500" in caplog.text
        assert "D1 database execution timeout" in caplog.text

def test_get_cloud_sync_status(monkeypatch):
    monkeypatch.setenv("TURSO_DATABASE_URL", "https://test-turso.turso.io")
    monkeypatch.setenv("CLOUDFLARE_CACHE_URL", "https://test-cf.workers.dev")
    
    status = get_cloud_sync_status()
    assert "turso_edge_sqlite" in status["active_providers"]
    assert "cloudflare_d1" in status["active_providers"]
