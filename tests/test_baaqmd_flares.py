"""Unit tests for BAAQMD Flare Incident Connector (BAAQMDFlareConnector).

Tests Bay Area refinery flare causal report ingestion, facility filtering, root cause
categorization, and refinery disruption benchmark matrix generation.
"""

import pandas as pd
import pytest

from src.baaqmd_flares import BAAQMDFlareConnector


def test_baaqmd_connector_initialization(tmp_path):
    """Test connector initialization with custom storage paths."""
    storage = tmp_path / "baaqmd_test.csv"
    vintage = tmp_path / "baaqmd_vintages.json"
    connector = BAAQMDFlareConnector(storage_path=str(storage), vintage_path=str(vintage))
    
    assert connector.storage_path == str(storage)
    assert connector.vintage_path == str(vintage)


def test_baaqmd_fetch_flare_incidents():
    """Test retrieving flare causal incidents with facility and unplanned filters."""
    connector = BAAQMDFlareConnector()
    df = connector.fetch_flare_incidents(facility_id="CHEVRON_RICHMOND")
    
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert (df["facility_id"] == "CHEVRON_RICHMOND").all()
    assert "flared_gas_scf" in df.columns
    assert "so2_emissions_lbs" in df.columns
    assert "root_cause_category" in df.columns


def test_baaqmd_root_cause_classification():
    """Test root cause categorization of major flaring incidents."""
    connector = BAAQMDFlareConnector()
    df = connector.fetch_flare_incidents()
    
    valid_causes = {
        "unplanned_power_outage",
        "compressor_trip",
        "unit_turnaround",
        "flaring_safety_relief",
        "routine_operational_adjustment"
    }
    unique_causes = set(df["root_cause_category"].unique())
    assert unique_causes.issubset(valid_causes)


def test_baaqmd_facility_incident_history():
    """Test retrieving facility incident report history for a specific refinery."""
    connector = BAAQMDFlareConnector()
    history = connector.get_facility_incident_history(facility_id="VALERO_BENICIA")
    
    assert isinstance(history, list)
    assert len(history) >= 1
    event = history[0]
    assert event["facility_id"] == "VALERO_BENICIA"
    assert "report_id" in event
    assert "affected_unit" in event


def test_baaqmd_disruption_benchmark_matrix():
    """Test generating disruption benchmark summary matrix."""
    connector = BAAQMDFlareConnector()
    matrix = connector.get_refinery_disruption_benchmark_matrix()
    
    assert isinstance(matrix, pd.DataFrame)
    assert not matrix.empty
    assert "report_id" in matrix.columns
    assert "facility_name" in matrix.columns
    assert "flared_gas_scf" in matrix.columns
    assert "disruption_severity" in matrix.columns
    assert set(matrix["disruption_severity"].unique()).issubset({"Low", "Medium", "High"})
