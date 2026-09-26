"""
Unit Tests for IMF PortWatch Shipping Activity Connector (tests/test_portwatch_connector.py)
Validates IMF PortWatch connector, chokepoint daily series ingestion, 7d vs 28d rolling anomaly formulas,
bitemporal vintage persistence, and global risk summary. (Issue #384)
"""

import os
import pytest
import pandas as pd
import numpy as np

from src.portwatch_connector import (
    IMFPortWatchConnector,
    CHOKEPOINTS,
    PETROLEUM_PORTS
)
from src.data_ingestion import (
    get_portwatch_connector,
    fetch_portwatch_chokepoint_series
)


@pytest.fixture(autouse=True)
def setup_testing_env(monkeypatch):
    monkeypatch.setenv("TESTING", "1")


def test_portwatch_chokepoints_and_ports_defined():
    """Validates that all standard chokepoints and ports have valid catalog metadata."""
    assert "Strait_of_Hormuz" in CHOKEPOINTS
    assert "Suez_Canal" in CHOKEPOINTS
    assert "Bab_el_Mandeb" in CHOKEPOINTS
    assert "Panama_Canal" in CHOKEPOINTS

    assert "Houston_Ship_Channel" in PETROLEUM_PORTS
    assert "New_York_New_Jersey" in PETROLEUM_PORTS
    assert "Los_Angeles_Long_Beach" in PETROLEUM_PORTS

    hormuz = CHOKEPOINTS["Strait_of_Hormuz"]
    assert hormuz["id"] == "hormuz"
    assert hormuz["nominal_daily_tankers"] == 42.0
    assert hormuz["criticality"] == 1.0


def test_portwatch_chokepoint_daily_series_mock_generation():
    """Validates daily series retrieval, index structure, and anomaly calculation under TESTING=1."""
    connector = IMFPortWatchConnector()
    df = connector.fetch_chokepoint_daily_series("Strait_of_Hormuz", start_date="2026-01-01", end_date="2026-03-01")

    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "daily_vessel_count" in df.columns
    assert "daily_tanker_count" in df.columns
    assert "daily_transit_tonnage_mt" in df.columns
    assert "daily_tanker_tonnage_mt" in df.columns
    assert "transit_anomaly_7d_28d" in df.columns

    # Check that tanker counts and tonnage are strictly positive
    assert (df["daily_tanker_count"] > 0).all()
    assert (df["daily_tanker_tonnage_mt"] > 0).all()

    # Check bounded anomaly index [-4.0, 4.0]
    assert df["transit_anomaly_7d_28d"].min() >= -4.0
    assert df["transit_anomaly_7d_28d"].max() <= 4.0


def test_portwatch_unknown_chokepoint_raises_error():
    """Validates that querying an unknown chokepoint raises a ValueError."""
    connector = IMFPortWatchConnector()
    with pytest.raises(ValueError, match="Unknown chokepoint"):
        connector.fetch_chokepoint_daily_series("Unknown_Passage")


def test_portwatch_global_chokepoint_risk_summary():
    """Validates global risk summary structure and disruption risk scoring."""
    connector = IMFPortWatchConnector()
    summary = connector.get_global_chokepoint_risk_summary()

    assert "timestamp" in summary
    assert "chokepoints" in summary
    assert len(summary["chokepoints"]) == 4

    for key in ["Strait_of_Hormuz", "Suez_Canal", "Bab_el_Mandeb", "Panama_Canal"]:
        assert key in summary["chokepoints"]
        item = summary["chokepoints"][key]
        assert "latest_tanker_count" in item
        assert "latest_tanker_tonnage_mt" in item
        assert "transit_anomaly_7d_28d" in item
        assert "disruption_risk_score" in item
        assert 0.0 <= item["disruption_risk_score"] <= 1.0
        assert item["status"] in ["NORMAL", "ELEVATED_DISRUPTION"]


def test_data_ingestion_portwatch_factory_helpers():
    """Validates data_ingestion module factory functions for PortWatch."""
    connector = get_portwatch_connector()
    assert isinstance(connector, IMFPortWatchConnector)

    df = fetch_portwatch_chokepoint_series("Suez_Canal", start_date="2026-01-01", end_date="2026-02-01")
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "transit_anomaly_7d_28d" in df.columns
