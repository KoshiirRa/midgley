"""Unit tests for PHMSA Hazardous Liquid Incident Connector (PHMSAPipelineConnector).

Tests incident ingestion, operator and commodity filtering, shutdown duration parsing,
corridor catalog categorization, and historical disruption validation matrix generation.
"""

import pandas as pd
import pytest

from src.phmsa_pipeline import PHMSAPipelineConnector


def test_phmsa_connector_initialization(tmp_path):
    """Test connector initialization with custom storage paths."""
    storage_path = tmp_path / "phmsa_test.csv"
    vintage_path = tmp_path / "phmsa_vintages.json"
    connector = PHMSAPipelineConnector(storage_path=str(storage_path), vintage_path=str(vintage_path))
    
    assert connector.storage_path == str(storage_path)
    assert connector.vintage_path == str(vintage_path)


def test_phmsa_fetch_pipeline_incidents():
    """Test incident retrieval from offline mock/bundled baseline and filtering."""
    connector = PHMSAPipelineConnector()
    # Offline fetch with mock fallback
    df = connector.fetch_pipeline_incidents(force_refresh=True)
    
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "report_number" in df.columns
    assert "incident_date" in df.columns
    assert "operator_name" in df.columns
    assert "commodity_subgroup" in df.columns
    assert "shutdown_hours" in df.columns
    assert "significant_disruption" in df.columns

    # Verify commodity types are filtered to refined products & crude
    valid_commodities = {"GASOLINE", "REFINED PRODUCTS", "CRUDE OIL", "HVLS", "ETHANOL", "DIESEL", "JET FUEL"}
    unique_commodities = set(df["commodity_subgroup"].dropna().unique())
    assert unique_commodities.issubset(valid_commodities)


def test_phmsa_corridor_incident_catalog():
    """Test categorized corridor incidents for major pipeline routes."""
    connector = PHMSAPipelineConnector()
    catalog = connector.get_corridor_incident_catalog()
    
    assert isinstance(catalog, dict)
    assert "Colonial_Mainline_PADD1" in catalog
    assert "Explorer_Midwest_PADD2" in catalog
    assert "SFPP_KinderMorgan_PADD5" in catalog
    
    colonial_events = catalog["Colonial_Mainline_PADD1"]
    assert len(colonial_events) >= 1
    event = colonial_events[0]
    assert "report_number" in event
    assert "operator_name" in event
    assert "shutdown_hours" in event
    assert "spill_barrels" in event


def test_phmsa_disruption_validation_matrix():
    """Test generation of retrospective disruption validation benchmark matrix."""
    connector = PHMSAPipelineConnector()
    matrix = connector.get_disruption_validation_matrix()
    
    assert isinstance(matrix, pd.DataFrame)
    assert not matrix.empty
    assert "incident_date" in matrix.columns
    assert "corridor" in matrix.columns
    assert "disruption_severity" in matrix.columns
    assert "shutdown_days" in matrix.columns
    
    # Severity should be Low, Medium, or High
    assert set(matrix["disruption_severity"].unique()).issubset({"Low", "Medium", "High"})
