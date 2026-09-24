"""Unit tests for Census Petroleum Trade Connector (CensusTradeConnector).

Tests port-level petroleum import ingestion, HS commodity filtering, publication lag guards,
supplier origin concentration (HHI) computation, and regional metro trade exposure mapping.
"""

import pandas as pd
import pytest

from src.census_trade_feed import CensusTradeConnector


def test_census_trade_connector_initialization(tmp_path):
    """Test connector initialization with custom storage paths."""
    storage = tmp_path / "census_trade_test.csv"
    vintage = tmp_path / "census_trade_vintages.json"
    connector = CensusTradeConnector(storage_path=str(storage), vintage_path=str(vintage))
    
    assert connector.storage_path == str(storage)
    assert connector.vintage_path == str(vintage)


def test_census_trade_fetch_port_imports():
    """Test retrieving port import records with district and HS code filtering."""
    connector = CensusTradeConnector()
    df = connector.fetch_port_imports(district_codes=["10", "28"], hs_codes=["271012"])
    
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert set(df["district_code"].astype(str).unique()).issubset({"10", "28"})
    assert set(df["hs_code"].astype(str).unique()).issubset({"271012"})
    assert "customs_value_usd" in df.columns
    assert "vessel_weight_kg" in df.columns


def test_census_trade_point_in_time_publication_lag():
    """Test that as_of filtering strictly respects 45-day publication delay."""
    connector = CensusTradeConnector(publication_lag_days=45)
    
    df_2023 = connector.fetch_port_imports(as_of="2023-07-01")
    assert not df_2023.empty
    assert (df_2023["period"] <= "2023-05").all()
    assert not (df_2023["period"] >= "2024-01").any()


def test_census_trade_port_import_exposure_and_hhi():
    """Test calculation of total import value, weight, and supplier HHI."""
    connector = CensusTradeConnector()
    # District 10: New York / Newark
    exposure = connector.compute_port_import_exposure(district_code="10")
    
    assert exposure["status"] == "VALID"
    assert exposure["district_code"] == "10"
    assert exposure["total_import_value_usd"] > 0.0
    assert exposure["total_import_weight_mt"] > 0.0
    # HHI must be in [0, 1]
    assert 0.0 <= exposure["hhi_origin_concentration"] <= 1.0
    assert exposure["top_origin_country"] in {"CA", "NL", "GB"}
    assert exposure["provenance"] == "US_CENSUS_BUREAU_INTERNATIONAL_TRADE"


def test_census_trade_coastal_metro_mapping():
    """Test mapping coastal metro hubs to trade districts."""
    connector = CensusTradeConnector()
    
    oakland_exp = connector.get_coastal_metro_trade_exposure(region="Oakland_CA")
    assert oakland_exp["target_region"] == "Oakland_CA"
    assert oakland_exp["district_code"] == "28"
    assert oakland_exp["status"] == "VALID"

    newark_exp = connector.get_coastal_metro_trade_exposure(region="Newark_DE")
    assert newark_exp["target_region"] == "Newark_DE"
    assert newark_exp["district_code"] == "10"
    assert newark_exp["status"] == "VALID"
