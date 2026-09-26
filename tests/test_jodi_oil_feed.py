"""Unit tests for JODI Oil Fundamentals Connector (JODIOilConnector).

Tests global oil supply data ingestion, country filtering, publication lag point-in-time filtering,
tightness index computation, and latest supply snapshot generation.
"""

import pandas as pd
import pytest

from src.jodi_oil_feed import JODIOilConnector


def test_jodi_connector_initialization(tmp_path):
    """Test connector initialization with custom storage paths."""
    storage = tmp_path / "jodi_test.csv"
    vintage = tmp_path / "jodi_vintages.json"
    connector = JODIOilConnector(storage_path=str(storage), vintage_path=str(vintage))
    
    assert connector.storage_path == str(storage)
    assert connector.vintage_path == str(vintage)


def test_jodi_fetch_oil_data():
    """Test retrieving JODI monthly oil balance data and country filters."""
    connector = JODIOilConnector()
    df = connector.fetch_jodi_oil_data(countries=["SA", "US"])
    
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert set(df["country"].unique()).issubset({"SA", "US"})
    assert "crude_production_kbd" in df.columns
    assert "refinery_intake_kbd" in df.columns
    assert "stock_change_kbd" in df.columns


def test_jodi_point_in_time_publication_lag():
    """Test that as_of filtering respects publication lag and excludes unreleased data."""
    connector = JODIOilConnector(publication_lag_days=50)
    
    # As of mid-2023, 2024-2025 data should not be accessible
    df_2023 = connector.fetch_jodi_oil_data(as_of="2023-07-01")
    assert not df_2023.empty
    assert (df_2023["period"] <= "2023-05").all()
    assert not (df_2023["period"] >= "2024-01").any()


def test_jodi_supply_tightness_index():
    """Test computation of aggregated global supply tightness and OPEC core metrics."""
    connector = JODIOilConnector()
    tightness_df = connector.compute_global_supply_tightness_index()
    
    assert isinstance(tightness_df, pd.DataFrame)
    assert not tightness_df.empty
    assert "jodi_global_crude_prod_kbd" in tightness_df.columns
    assert "jodi_opec_core_prod_kbd" in tightness_df.columns
    assert "jodi_tightness_score" in tightness_df.columns
    
    # Tightness score should be bounded [0, 1]
    assert (tightness_df["jodi_tightness_score"] >= 0.0).all()
    assert (tightness_df["jodi_tightness_score"] <= 1.0).all()


def test_jodi_latest_supply_snapshot():
    """Test generating structured latest supply regime snapshot."""
    connector = JODIOilConnector()
    snapshot = connector.get_latest_supply_snapshot()
    
    assert snapshot["status"] == "VALID"
    assert "latest_period" in snapshot
    assert "supply_regime" in snapshot
    assert snapshot["supply_regime"] in {"DEFICIT_TIGHT", "SURPLUS_LOOSE", "BALANCED"}
    assert snapshot["provenance"] == "JODI_OIL_WORLD_DATABASE"
