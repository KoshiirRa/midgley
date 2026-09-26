"""
Unit & Integration Tests for FHWA Monthly Traffic Volume Trends (TVT) Connector (tests/test_fhwa_traffic_volume.py)
Validates data ingestion, fallback mechanisms, bitemporal vintages, caching,
feature matrix fusion, and consumer demand indicators. (Issue #369)
"""

import os
import json
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

from src.bts_transportation import (
    FHWATrafficVolumeConnector,
    fetch_fhwa_traffic_features,
    save_fhwa_vintage_record,
    get_fhwa_vintages_as_of,
    HISTORICAL_FHWA_BASELINE
)
from src.fhwa_traffic_volume import (
    FHWATrafficVolumeConnector as ModularFHWAConnector,
    fetch_fhwa_traffic_features as modular_fetch_fhwa
)
from src.data_ingestion import (
    get_fhwa_traffic_volume_connector,
    fetch_fhwa_traffic_volume_features
)
from src.lookup_cache import global_cache
from src.feature_engineering import create_feature_matrix


@pytest.fixture
def fhwa_connector():
    return FHWATrafficVolumeConnector(cache_ttl_seconds=3600)


def test_fhwa_fetch_schema_and_types(fhwa_connector):
    """Verifies that FHWA TVT dataset returns expected columns and valid numerical types."""
    df = fhwa_connector.fetch_fhwa_vmt_dataset(start_date="2022-01-01")
    assert not df.empty
    assert "date" in df.columns
    assert "fhwa_vmt_national_billions" in df.columns
    assert "fhwa_vmt_mom_pct" in df.columns
    assert "fhwa_vmt_yoy_growth_pct" in df.columns
    assert "fhwa_vmt_12m_moving_total" in df.columns
    assert "fhwa_gasoline_demand_proxy" in df.columns
    assert "fhwa_vmt_northeast_index" in df.columns
    assert "fhwa_vmt_south_atlantic_index" in df.columns
    assert "fhwa_vmt_north_central_index" in df.columns
    assert "fhwa_vmt_south_central_index" in df.columns
    assert "fhwa_vmt_west_index" in df.columns

    assert (df['date'] >= pd.to_datetime("2022-01-01")).all()
    assert (df['fhwa_vmt_national_billions'] > 150.0).all()
    assert not df['fhwa_vmt_national_billions'].isna().any()


def test_fhwa_current_demand_summary(fhwa_connector):
    """Verifies the consumer vehicle travel demand summary output."""
    summary = fhwa_connector.get_fhwa_current_demand_summary()
    assert isinstance(summary, dict)
    assert summary["status"] == "SUCCESS"
    assert "vmt_national_billion_miles" in summary
    assert "vmt_yoy_growth_pct" in summary
    assert "vmt_mom_growth_pct" in summary
    assert "gasoline_demand_proxy" in summary
    assert "demand_state" in summary
    assert summary["demand_state"] in ["Expanding", "Contracting", "Seasonal Baseline"]
    assert -1.0 <= summary["gasoline_demand_proxy"] <= 1.0


def test_fhwa_caching(fhwa_connector):
    """Verifies that lookup_cache stores and returns cached FHWA data."""
    cache_key = "fhwa_vmt_dataset:2024-01-01:50000"
    global_cache.delete(cache_key)

    df1 = fhwa_connector.fetch_fhwa_vmt_dataset(start_date="2024-01-01")
    cached = global_cache.get(cache_key)
    assert cached is not None
    assert "records" in cached

    # Second fetch returns cached records
    df2 = fhwa_connector.fetch_fhwa_vmt_dataset(start_date="2024-01-01")
    assert len(df1) == len(df2)


def test_fhwa_bitemporal_vintage_persistence(tmp_path):
    """Verifies point-in-time vintage recording and as-of cutoff retrieval."""
    test_file = str(tmp_path / "fhwa_vintages_test.json")

    record1 = {
        "as_of": "2026-05-01 10:00:00",
        "valid_date": "2026-03-01",
        "vmt_billions": 278.9,
        "fhwa_vmt_yoy_growth_pct": 1.8,
        "fhwa_vmt_mom_pct": 0.9,
        "is_vintage_reconstructed": False
    }
    record2 = {
        "as_of": "2026-06-01 10:00:00",
        "valid_date": "2026-04-01",
        "vmt_billions": 285.2,
        "fhwa_vmt_yoy_growth_pct": 2.1,
        "fhwa_vmt_mom_pct": 1.2,
        "is_vintage_reconstructed": False
    }

    save_fhwa_vintage_record(record1, filepath=test_file)
    save_fhwa_vintage_record(record2, filepath=test_file)

    vintages_all = get_fhwa_vintages_as_of("2026-06-15", filepath=test_file)
    assert len(vintages_all) == 2
    assert vintages_all[-1]["valid_date"] == "2026-04-01"

    vintages_cutoff = get_fhwa_vintages_as_of("2026-05-15", filepath=test_file)
    assert len(vintages_cutoff) == 1
    assert vintages_cutoff[0]["valid_date"] == "2026-03-01"


def test_modular_reexport():
    """Verifies that src/fhwa_traffic_volume.py properly re-exports symbols."""
    connector = ModularFHWAConnector()
    df = modular_fetch_fhwa(start_date="2024-01-01")
    assert not df.empty
    assert "fhwa_vmt_national_billions" in df.columns


def test_data_ingestion_helpers():
    """Verifies data_ingestion.py factory helper functions for FHWA."""
    connector = get_fhwa_traffic_volume_connector()
    assert isinstance(connector, FHWATrafficVolumeConnector)
    df = fetch_fhwa_traffic_volume_features(start_date="2024-01-01")
    assert not df.empty
    assert "fhwa_gasoline_demand_proxy" in df.columns


def test_fhwa_feature_engineering_matrix_integration():
    """Verifies that create_feature_matrix merges FHWA traffic volume features cleanly."""
    dates = pd.date_range("2024-01-01", "2024-03-31", freq="D")
    raw_df = pd.DataFrame({
        "date": dates,
        "gasoline_rbob": np.linspace(2.40, 2.70, len(dates)),
        "wti_crude": np.linspace(72.0, 78.0, len(dates)),
        "brent_crude": np.linspace(76.0, 82.0, len(dates)),
        "heating_oil": np.linspace(2.50, 2.90, len(dates))
    })

    mat = create_feature_matrix(raw_df, region="National")
    assert not mat.empty
    assert "fhwa_vmt_national_billions" in mat.columns
    assert "fhwa_gasoline_demand_proxy" in mat.columns
    assert "fhwa_vmt_yoy_growth_pct" in mat.columns
    assert not mat["fhwa_vmt_national_billions"].isna().any()


def test_fhwa_api_endpoint():
    """Verifies the GET /api/v1/macro/traffic-volume REST API endpoint."""
    from fastapi.testclient import TestClient
    from src.api_server import app

    client = TestClient(app)
    response = client.get("/api/v1/macro/traffic-volume?start_date=2024-01-01")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert "demand_summary" in data
    assert "history" in data
    assert data["sample_count"] > 0

    # Test summary_only flag
    sum_resp = client.get("/api/v1/macro/traffic-volume?summary_only=true")
    assert sum_resp.status_code == 200
    sum_data = sum_resp.json()
    assert sum_data["status"] == "SUCCESS"
    assert "vmt_national_billion_miles" in sum_data
