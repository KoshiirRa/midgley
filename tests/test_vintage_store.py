"""
Unit tests for Bitemporal VintageStore (src/vintage_store.py).
"""

import os
import tempfile
import pytest
from datetime import datetime, date, timedelta
from src.db.client import DatabaseClient
from src.vintage_store import VintageStore, QUALITY_LIVE, QUALITY_CACHED, QUALITY_BENCHMARK


@pytest.fixture
def isolated_vintage_store():
    """Provides an isolated VintageStore backed by temporary database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    client = DatabaseClient(sqlite_path=db_path)
    store = VintageStore(db=client)
    yield store
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception:
            pass


def test_record_and_query_as_of(isolated_vintage_store):
    """Verifies that query_as_of respects bitemporal timestamps and publication lags."""
    store = isolated_vintage_store
    
    # 1. Record vintage on 2026-09-01
    store.record_observation(
        feed="eia_stocks",
        entity="PADD3",
        obs_date="2026-09-01",
        values={"stocks_mbbl": 220.5},
        published_at="2026-09-02T10:00:00Z",
        fetched_at="2026-09-02T10:05:00Z",
        quality=QUALITY_LIVE
    )

    # 2. Record revision on 2026-09-08
    store.record_observation(
        feed="eia_stocks",
        entity="PADD3",
        obs_date="2026-09-01",
        values={"stocks_mbbl": 221.2},
        published_at="2026-09-08T10:00:00Z",
        fetched_at="2026-09-08T10:05:00Z",
        quality=QUALITY_LIVE
    )

    # Point-in-time query before revision was published (e.g. as of 2026-09-05)
    as_of_early = datetime(2026, 9, 5, 12, 0, 0)
    res_early = store.query_as_of(
        feed="eia_stocks",
        entity="PADD3",
        target_date="2026-09-01",
        as_of_time=as_of_early
    )
    assert res_early is not None
    assert res_early["stocks_mbbl"] == 220.5
    assert res_early["_provenance_published_at"] == "2026-09-02T10:00:00Z"

    # Point-in-time query after revision was published (e.g. as of 2026-09-10)
    as_of_late = datetime(2026, 9, 10, 12, 0, 0)
    res_late = store.query_as_of(
        feed="eia_stocks",
        entity="PADD3",
        target_date="2026-09-01",
        as_of_time=as_of_late
    )
    assert res_late is not None
    assert res_late["stocks_mbbl"] == 221.2
    assert res_late["_provenance_published_at"] == "2026-09-08T10:00:00Z"
