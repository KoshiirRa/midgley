"""
Unit Tests for API Dynamic Rate Limiting & Validation Bounds (tests/test_api_rate_limiter.py)
Validates Issue #571: X-RateLimit-* headers, sliding-window rate limiting, and parameter validation bounds.
"""

import os
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from src.api_server import app
from src.key_manager import KeyManager


@pytest.fixture
def test_client_and_key(tmp_path):
    # Set up isolated key manager DB
    db_path = str(tmp_path / "test_keys.sqlite")
    km = KeyManager(db_path=db_path)
    
    import src.api_server as api_module
    old_km = api_module.global_key_manager
    api_module.global_key_manager = km
    
    # Create test key with RPM=3
    key_dict = km.create_key(user_id="rate_limit_tester", tier="basic", rate_limit_rpm=3)
    raw_key = key_dict["token"]
    prefix = key_dict["key_prefix"]
    client = TestClient(app)
    
    yield client, raw_key, prefix, km
    
    api_module.global_key_manager = old_km


@patch("src.api_server._get_live_prices_impl")
def test_rate_limit_headers_on_success(mock_live, test_client_and_key):
    mock_live.return_value = {"price": 3.45, "locale": "national"}
    client, raw_key, prefix, km = test_client_and_key
    headers = {"X-API-Key": raw_key}
    
    response = client.get("/api/v1/prices/live", headers=headers)
    assert response.status_code == 200
    assert "X-RateLimit-Limit" in response.headers
    assert response.headers["X-RateLimit-Limit"] == "3"
    assert "X-RateLimit-Remaining" in response.headers
    assert int(response.headers["X-RateLimit-Remaining"]) >= 0
    assert "X-RateLimit-Reset" in response.headers
    assert int(response.headers["X-RateLimit-Reset"]) > 0


@patch("src.api_server._get_live_prices_impl")
def test_rate_limit_exceeded_returns_429(mock_live, test_client_and_key):
    mock_live.return_value = {"price": 3.45, "locale": "national"}
    client, raw_key, prefix, km = test_client_and_key
    headers = {"X-API-Key": raw_key}
    
    # Send requests up to limit (limit is 3)
    r1 = client.get("/api/v1/prices/live", headers=headers)
    assert r1.status_code == 200
    r2 = client.get("/api/v1/prices/live", headers=headers)
    assert r2.status_code == 200
    r3 = client.get("/api/v1/prices/live", headers=headers)
    assert r3.status_code == 200
    
    # 4th request exceeds rate limit
    r4 = client.get("/api/v1/prices/live", headers=headers)
    assert r4.status_code == 429
    assert "Retry-After" in r4.headers
    assert "X-RateLimit-Limit" in r4.headers
    assert r4.headers["X-RateLimit-Remaining"] == "0"
    assert "X-RateLimit-Reset" in r4.headers


def test_query_parameter_validation_bounds(test_client_and_key):
    client, raw_key, prefix, km = test_client_and_key
    headers = {"X-API-Key": raw_key}
    
    # Invalid days parameter (>30) on /api/v1/forecast/predict
    resp = client.get("/api/v1/forecast/predict?days=99", headers=headers)
    assert resp.status_code == 422
    
    # Invalid days parameter (<1)
    resp2 = client.get("/api/v1/forecast/predict?days=0", headers=headers)
    assert resp2.status_code == 422
