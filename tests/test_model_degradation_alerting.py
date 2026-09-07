"""
Unit Tests for MLOps Automated Model Degradation & Baseline Underperformance Alerting (Issue #210).
Tests src/weekly_issue_reporter.py degradation threshold triggering (model_uplift_mae_pct < 0.0),
telemetry logging to data/telemetry_alerts.json, Webhook alert dispatch, GitHub Issue duplicate checks,
and Markdown section formatting.
"""

import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.weekly_issue_reporter import (
    log_degradation_telemetry_alert,
    check_open_degradation_github_issue,
    send_degradation_webhook_alert,
    evaluate_model_degradation_alerts,
    format_degradation_markdown_section,
    TELEMETRY_ALERTS_PATH,
)


@pytest.fixture
def mock_degraded_regional_breakdown():
    return [
        {
            "region": "Tulsa_OK",
            "evaluations": 14,
            "mae_dollars": 0.5820,
            "rmse_dollars": 0.6210,
            "mape_pct": 18.2,
            "directional_hit_rate_pct": 57.14,
            "naive_persistence_mae": 0.5500,
            "model_uplift_mae_pct": -5.82,  # DEGRADED (< 0.0)
        },
        {
            "region": "National",
            "evaluations": 30,
            "mae_dollars": 0.1050,
            "rmse_dollars": 0.1210,
            "mape_pct": 3.4,
            "directional_hit_rate_pct": 83.33,
            "naive_persistence_mae": 0.1250,
            "model_uplift_mae_pct": 16.0,  # HEALTHY (>= 0.0)
        }
    ]


@pytest.fixture
def mock_healthy_regional_breakdown():
    return [
        {
            "region": "Tulsa_OK",
            "evaluations": 14,
            "mae_dollars": 0.4820,
            "naive_persistence_mae": 0.5500,
            "model_uplift_mae_pct": 12.36,
        },
        {
            "region": "National",
            "evaluations": 30,
            "mae_dollars": 0.1050,
            "naive_persistence_mae": 0.1250,
            "model_uplift_mae_pct": 16.0,
        }
    ]


def test_log_degradation_telemetry_alert_suppression():
    with patch.dict(os.environ, {"TESTING": "1"}, clear=False):
        res = log_degradation_telemetry_alert({"is_degraded": True, "degraded_regions": []})
        assert res["status"] == "TEST_SUPPRESSED"


def test_log_degradation_telemetry_alert_persistence(tmp_path):
    test_alerts_file = tmp_path / "telemetry_alerts.json"
    sample_alert = {
        "is_degraded": True,
        "degraded_regions": [{"region": "Tulsa_OK", "model_uplift_mae_pct": -5.82}],
        "github_issue_url": "https://github.com/KoshiirRa/midgley/issues/215",
        "webhook_sent": True
    }

    with patch("src.weekly_issue_reporter.TELEMETRY_ALERTS_PATH", str(test_alerts_file)), \
         patch.dict(os.environ, {"TESTING": "0", "TEST_TELEMETRY_PERSIST": "1"}):
        result = log_degradation_telemetry_alert(sample_alert)
        assert test_alerts_file.exists()
        assert result["total_alerts_logged"] == 1
        assert result["active_degraded_regions"] == ["Tulsa_OK"]
        assert len(result["history"]) == 1
        assert result["history"][0]["is_degraded"] is True


def test_evaluate_model_degradation_alerts_degraded(mock_degraded_regional_breakdown):
    with patch("src.prediction_logger.compute_regional_scoreboard_breakdown", return_value=mock_degraded_regional_breakdown), \
         patch("src.weekly_issue_reporter.send_degradation_webhook_alert", return_value=True), \
         patch("src.weekly_issue_reporter.check_open_degradation_github_issue", return_value=True):

        res = evaluate_model_degradation_alerts(window_days=30)
        assert res["is_degraded"] is True
        assert len(res["degraded_regions"]) == 1
        assert res["degraded_regions"][0]["region"] == "Tulsa_OK"
        assert res["degraded_regions"][0]["model_uplift_mae_pct"] == -5.82
        assert len(res["healthy_regions"]) == 1
        assert res["healthy_regions"][0]["region"] == "National"


def test_evaluate_model_degradation_alerts_healthy(mock_healthy_regional_breakdown):
    with patch("src.prediction_logger.compute_regional_scoreboard_breakdown", return_value=mock_healthy_regional_breakdown):
        res = evaluate_model_degradation_alerts(window_days=30)
        assert res["is_degraded"] is False
        assert len(res["degraded_regions"]) == 0
        assert len(res["healthy_regions"]) == 2


def test_check_open_degradation_github_issue_detection():
    mock_run = MagicMock()
    mock_run.stdout = json.dumps([{"number": 210, "title": "[MODEL DEGRADATION ALERT] Test Issue"}])

    with patch("subprocess.run", return_value=mock_run):
        has_open = check_open_degradation_github_issue("KoshiirRa/midgley")
        assert has_open is True

    mock_run_empty = MagicMock()
    mock_run_empty.stdout = "[]"
    with patch("subprocess.run", return_value=mock_run_empty):
        has_open_empty = check_open_degradation_github_issue("KoshiirRa/midgley")
        assert has_open_empty is False


def test_send_degradation_webhook_alert_dispatch():
    mock_response = MagicMock()
    mock_response.__enter__.return_value = mock_response
    mock_response.status = 200

    alert_data = {
        "is_degraded": True,
        "degraded_regions": [{"region": "Tulsa_OK", "model_uplift_mae_pct": -5.82}],
        "total_evaluations": 44
    }

    with patch("urllib.request.urlopen", return_value=mock_response), \
         patch.dict(os.environ, {"TESTING": "0", "TEST_WEBHOOK_DISPATCH": "1"}):
        ok = send_degradation_webhook_alert(alert_data, webhook_url="https://example.com/webhook")
        assert ok is True


def test_format_degradation_markdown_section():
    degraded_data = {
        "is_degraded": True,
        "degraded_regions": [
            {
                "region": "Tulsa_OK",
                "evaluations": 14,
                "model_mae": 0.5820,
                "naive_mae": 0.5500,
                "model_uplift_mae_pct": -5.82,
                "status": "DEGRADED"
            }
        ],
        "healthy_regions": []
    }

    sec_deg = format_degradation_markdown_section(degraded_data)
    assert "## ⚠️ Model Degradation & Baseline Underperformance Alerts" in sec_deg
    assert "Model Underperformance Alert Active" in sec_deg
    assert "`Tulsa_OK`" in sec_deg
    assert "-5.82%" in sec_deg

    healthy_data = {
        "is_degraded": False,
        "degraded_regions": [],
        "healthy_regions": [{"region": "National"}]
    }

    sec_healthy = format_degradation_markdown_section(healthy_data)
    assert "All Models Healthy" in sec_healthy
    assert "Zero degradation alerts active" in sec_healthy
