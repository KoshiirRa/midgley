"""
Tests for Provenance Chains & Stale-While-Revalidate (SWR) Cache Architecture (Issue #45).
"""

import time
import pytest
from unittest.mock import MagicMock
from src.lookup_cache import LookupCache, global_cache
from src.api_server import app
from fastapi.testclient import TestClient

client = TestClient(app)

def test_build_provenance_chain():
    """Tests static provenance chain object creation and granularity mismatch detection."""
    prov_metro = LookupCache.build_provenance_chain(
        source="GasBuddy GraphQL API",
        region_id="Oakland_CA",
        padd="PADD 5",
        requested_granularity="METRO",
        served_granularity="METRO",
        cache_status="HIT_FRESH"
    )
    assert prov_metro["source"] == "GasBuddy GraphQL API"
    assert prov_metro["region_id"] == "Oakland_CA"
    assert prov_metro["padd"] == "PADD 5"
    assert prov_metro["requested_granularity"] == "METRO"
    assert prov_metro["served_granularity"] == "METRO"
    assert prov_metro["is_fallback_granularity"] is False
    assert prov_metro["cache_status"] == "HIT_FRESH"

    prov_fallback = LookupCache.build_provenance_chain(
        source="EIA State Gasoline Price Average (CA)",
        region_id="Oakland_CA",
        padd="PADD 5",
        requested_granularity="METRO",
        served_granularity="STATE",
        cache_status="MISS"
    )
    assert prov_fallback["requested_granularity"] == "METRO"
    assert prov_fallback["served_granularity"] == "STATE"
    assert prov_fallback["is_fallback_granularity"] is True


def test_swr_cache_protocol(monkeypatch):
    """Tests SWR cache state transitions: HIT_FRESH, HIT_STALE (with bg revalidation), and MISS."""
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("TURSO_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("CLOUDFLARE_CACHE_URL", raising=False)
    monkeypatch.delenv("CLOUDFLARE_AUTH_TOKEN", raising=False)

    test_cache = LookupCache(db_path=":memory:")
    key = "test_swr_key"
    val = {"price": 3.890, "source": "Test Source"}

    # 1. Miss Test
    val_res, status = test_cache.get_swr(key, fresh_ttl_seconds=1, stale_ttl_seconds=5)
    assert status == "MISS"
    assert val_res is None

    # Set value manually
    test_cache.set(key, val, ttl_seconds=5)

    # 2. Fresh Hit Test
    val_fresh, status_fresh = test_cache.get_swr(key, fresh_ttl_seconds=2, stale_ttl_seconds=5)
    assert status_fresh == "HIT_FRESH"
    assert val_fresh["price"] == 3.890

    # Sleep past fresh threshold
    time.sleep(1.1)

    # 3. Stale Hit Test with Async Background Revalidation
    revalidated = False
    def mock_fetch():
        nonlocal revalidated
        revalidated = True
        return {"price": 3.990, "source": "Revalidated Source"}

    val_stale, status_stale = test_cache.get_swr(
        key,
        fetch_func=mock_fetch,
        fresh_ttl_seconds=1,
        stale_ttl_seconds=5
    )
    assert status_stale == "HIT_STALE"
    assert val_stale["price"] == 3.890  # Instant stale value returned

    # Give background thread a short moment to execute
    time.sleep(0.2)
    assert revalidated is True


def test_api_live_prices_provenance():
    """Tests /api/v1/prices/live response for presence of provenance metadata."""
    resp = client.get("/api/v1/prices/live?locale=oakland")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "provenance" in data
    prov = data["provenance"]
    assert "source" in prov
    assert "region_id" in prov
    assert "padd" in prov
    assert "requested_granularity" in prov
    assert "served_granularity" in prov
    assert "is_fallback_granularity" in prov


def test_api_combined_provenance():
    """Tests /api/v1/combined response for presence of provenance metadata in live_lookup."""
    resp = client.get("/api/v1/combined?locale=tulsa")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "live_lookup" in data
    assert "provenance" in data["live_lookup"]
    prov = data["live_lookup"]["provenance"]
    assert prov["region_id"] == "Tulsa_OK"
