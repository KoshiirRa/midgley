"""
Unit & Integration Tests for U.S. BTS Freight Transportation Services Index (TSI) & Truck Demand (tests/test_bts_transportation.py)
Validates data ingestion, fallback mechanisms, bitemporal vintages, caching,
feature matrix fusion, and REST API exposure. (Issue #74)
"""

import os
import json
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.bts_transportation import (
    BTSTransportationConnector,
    fetch_bts_transportation_features,
    save_bts_vintage_record,
    get_bts_vintages_as_of,
    HISTORICAL_BTS_BASELINE
)
from src.lookup_cache import global_cache
from src.feature_engineering import create_feature_matrix
from src.api_server import app


@pytest.fixture
def bts_connector():
    return BTSTransportationConnector(cache_ttl_seconds=3600)


def test_bts_fetch_schema_and_types(bts_connector):
    """Verifies that BTS TSI dataset returns expected columns and valid numerical types."""
    df = bts_connector.fetch_bts_tsi_dataset(start_date="2022-01-01")
    assert not df.empty
    assert "date" in df.columns
    assert "bts_tsi_freight" in df.columns
    assert "bts_truck_tonnage" in df.columns
    assert "bts_petroleum_transport" in df.columns
    assert "bts_tsi_freight_mom_pct" in df.columns
    assert "bts_truck_tonnage_mom_pct" in df.columns
    assert (df['date'] >= pd.to_datetime("2022-01-01")).all()
    assert (df['bts_tsi_freight'] > 50.0).all()
    assert not df['bts_tsi_freight'].isna().any()


def test_bts_current_demand_summary(bts_connector):
    """Verifies the physical freight demand momentum summary output."""
    summary = bts_connector.get_bts_current_demand_summary()
    assert isinstance(summary, dict)
    assert summary["status"] == "SUCCESS"
    assert "freight_tsi_index" in summary
    assert "truck_tonnage_index" in summary
    assert "demand_momentum_pressure" in summary
    assert "demand_state" in summary
    assert summary["demand_state"] in ["Expanding", "Contracting", "Neutral"]
    assert -1.0 <= summary["demand_momentum_pressure"] <= 1.0


def test_bts_caching(bts_connector):
    """Verifies that lookup_cache stores and returns cached BTS data."""
    cache_key = "bts_tsi_dataset:2024-01-01:50000"
    global_cache.delete(cache_key)

    df1 = bts_connector.fetch_bts_tsi_dataset(start_date="2024-01-01")
    cached = global_cache.get(cache_key)
    assert cached is not None
    assert "records" in cached

    # Second fetch returns cached records
    df2 = bts_connector.fetch_bts_tsi_dataset(start_date="2024-01-01")
    assert len(df1) == len(df2)


def test_bts_bitemporal_vintage_persistence(tmp_path):
    """Verifies point-in-time vintage recording and as-of cutoff retrieval."""
    test_file = str(tmp_path / "bts_vintages_test.json")

    record1 = {
        "as_of": "2026-05-01 10:00:00",
        "valid_date": "2026-04-01",
        "tsi_freight": 138.2,
        "truck_d11": 116.3,
        "petroleum_d11": 366998.0,
        "tsi_total": 131.8,
        "is_vintage_reconstructed": False
    }
    record2 = {
        "as_of": "2026-06-01 10:00:00",
        "valid_date": "2026-05-01",
        "tsi_freight": 135.3,
        "truck_d11": 112.8,
        "petroleum_d11": 359762.0,
        "tsi_total": 130.2,
        "is_vintage_reconstructed": False
    }

    save_bts_vintage_record(record1, filepath=test_file)
    save_bts_vintage_record(record2, filepath=test_file)

    assert os.path.exists(test_file)

    # Query as of May 15
    vintages_may = get_bts_vintages_as_of("2026-05-15", filepath=test_file)
    assert len(vintages_may) == 1
    assert vintages_may[0]["valid_date"] == "2026-04-01"
    assert vintages_may[0]["tsi_freight"] == 138.2

    # Query as of June 15
    vintages_june = get_bts_vintages_as_of("2026-06-15", filepath=test_file)
    assert len(vintages_june) == 2


def test_bts_fred_fallback():
    """Tests FRED open CSV fallback when SODA API fails."""
    connector = BTSTransportationConnector()
    fred_mock_csv = "DATE,TSIFRGHT\n2024-01-01,136.2\n2024-02-01,137.1\n2024-03-01,138.0\n"

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = fred_mock_csv.encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        df = connector._fetch_fred_bts_fallback(start_date="2024-01-01")
        assert df is not None
        assert not df.empty
        assert len(df) == 3
        assert "bts_tsi_freight" in df.columns
        assert df.iloc[0]["bts_tsi_freight"] == 136.2


def test_bts_offline_curated_baseline_fallback():
    """Tests fallback to curated historical baseline constant when all network queries fail."""
    connector = BTSTransportationConnector()

    with patch("urllib.request.urlopen", side_effect=Exception("Network unreachable")):
        with patch("src.benchmark_updater.load_historical_benchmark", return_value=None):
            # Bypass lookup cache
            with patch("src.lookup_cache.global_cache.get", return_value=None):
                df = connector.fetch_bts_tsi_dataset(start_date="2022-01-01")
                assert not df.empty
                assert "bts_tsi_freight" in df.columns
                assert len(df) >= 10


def test_feature_engineering_matrix_bts_fusion():
    """Verifies that create_feature_matrix merges BTS features with zero nulls."""
    dates = pd.date_range("2024-01-01", "2024-03-01", freq="B")
    market_df = pd.DataFrame({
        "date": dates,
        "gasoline_rbob": np.linspace(2.30, 2.70, len(dates)),
        "wti_crude": np.linspace(70.0, 80.0, len(dates)),
        "brent_crude": np.linspace(74.0, 84.0, len(dates)),
        "heating_oil": np.linspace(2.50, 2.90, len(dates))
    })

    feature_df = create_feature_matrix(market_df, forecast_horizon=5)

    assert not feature_df.empty
    bts_cols = [
        'bts_tsi_freight', 'bts_truck_tonnage', 'bts_petroleum_transport',
        'bts_tsi_freight_mom_pct', 'bts_truck_tonnage_mom_pct', 'bts_petroleum_transport_mom_pct',
        'bts_tsi_total', 'bts_rail_carloads'
    ]
    for col in bts_cols:
        assert col in feature_df.columns, f"Missing feature column: {col}"
        assert not feature_df[col].isna().any(), f"NaNs found in feature column: {col}"


def test_bts_api_endpoint():
    """Verifies the GET /api/v1/macro/freight-tsi REST API endpoint."""
    client = TestClient(app)
    response = client.get("/api/v1/macro/freight-tsi?start_date=2024-01-01")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert "demand_summary" in data
    assert "history" in data
    assert data["sample_count"] > 0

    # Test summary_only flag
    sum_resp = client.get("/api/v1/macro/freight-tsi?summary_only=true")
    assert sum_resp.status_code == 200
    sum_data = sum_resp.json()
    assert sum_data["status"] == "SUCCESS"
    assert "freight_tsi_index" in sum_data
