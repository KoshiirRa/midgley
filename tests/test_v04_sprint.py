"""
Unit Test Suite for Milestone v0.4.0 Sprint (tests/test_v04_sprint.py)
Verifies:
1. CodeCogs LaTeX Math URL encoding (Issue #52)
2. Prometheus Telemetry Metrics Exporter & /api/v1/metrics endpoint (Issue #107)
3. Zero-Cost Wayback Machine Cloud Archiving (Issue #197)
"""

import os
import pytest
from fastapi.testclient import TestClient

from src.dashboard_generator import codecogs_url
from src.telemetry import format_prometheus_metrics
from src.api_server import app
from src.wayback_archiver import archive_url_to_wayback


def test_codecogs_latex_url_generator():
    """Verifies that codecogs_url produces valid URL-encoded CodeCogs SVG image URLs (Issue #52)."""
    latex_expr = r"M_t = M_{t-1} \cdot e^{-\frac{\ln(2)}{t_{1/2}}} + S_t"
    url = codecogs_url(latex_expr)
    assert url.startswith("https://latex.codecogs.com/svg.latex?")
    assert "%5Ccdot" in url or "cdot" in url or "%20" in url
    assert "M_t" in url


def test_prometheus_metrics_formatting():
    """Verifies format_prometheus_metrics output format (Issue #107)."""
    metrics_text = format_prometheus_metrics(environment="test")
    assert "# HELP llm_tokens_consumed_total" in metrics_text
    assert "# TYPE llm_tokens_consumed_total counter" in metrics_text
    assert "# HELP api_quota_remaining_ratio" in metrics_text
    assert 'environment="test"' in metrics_text


def test_api_server_prometheus_metrics_endpoint():
    """Verifies GET /metrics and GET /api/v1/metrics HTTP endpoints (Issue #107)."""
    client = TestClient(app)
    
    # Test GET /metrics
    res1 = client.get("/metrics")
    assert res1.status_code == 200
    assert "text/plain" in res1.headers.get("content-type", "")
    assert "llm_tokens_consumed_total" in res1.text
    
    # Test GET /api/v1/metrics
    res2 = client.get("/api/v1/metrics")
    assert res2.status_code == 200
    assert "text/plain" in res2.headers.get("content-type", "")
    assert "api_quota_remaining_ratio" in res2.text


def test_wayback_machine_cloud_archiver():
    """Verifies archive_url_to_wayback URL handling and testing suppression (Issue #197)."""
    # 1. Invalid URL handling
    res_invalid = archive_url_to_wayback("not-a-url")
    assert res_invalid["status"] == "SKIPPED_INVALID_URL"
    
    # 2. Valid URL handling (suppressed in test env)
    test_url = "https://www.reuters.com/business/energy/opec-plus-agrees-oil-output-hike-2026-09-03/"
    res_valid = archive_url_to_wayback(test_url, headline="OPEC+ Agrees Oil Output Hike")
    assert res_valid["url"] == test_url
    assert "archive_url" in res_valid
    assert res_valid["archive_url"].startswith("https://web.archive.org/web/*/")
