"""Unit tests for TCEQ Emissions Connector (TCEQEmissionsConnector).

Tests Gulf Coast refinery air emissions incident ingestion, facility RN filtering,
event categorization, and disruption benchmark matrix generation.
"""

import pandas as pd
import pytest

from src.tceq_emissions import TCEQEmissionsConnector


def test_tceq_connector_initialization(tmp_path):
    """Test connector initialization with custom storage paths."""
    storage = tmp_path / "tceq_test.csv"
    vintage = tmp_path / "tceq_vintages.json"
    connector = TCEQEmissionsConnector(storage_path=str(storage), vintage_path=str(vintage))
    
    assert connector.storage_path == str(storage)
    assert connector.vintage_path == str(vintage)


def test_tceq_fetch_emissions_events():
    """Test retrieving emissions events with facility RN and category filtering."""
    connector = TCEQEmissionsConnector()
    df = connector.fetch_emissions_events(facility_rn="RN102579307")
    
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert (df["facility_rn"] == "RN102579307").all()
    assert "so2_emitted_lbs" in df.columns
    assert "voc_emitted_lbs" in df.columns
    assert "affected_unit" in df.columns


def test_tceq_event_categorization():
    """Test standard event categories."""
    connector = TCEQEmissionsConnector()
    df = connector.fetch_emissions_events()
    
    valid_categories = {"unplanned_upset", "planned_maintenance", "facility_restart", "flaring_safety_relief"}
    unique_cats = set(df["event_category"].unique())
    assert unique_cats.issubset(valid_categories)


def test_tceq_facility_event_history():
    """Test retrieving facility event history for Motiva Port Arthur."""
    connector = TCEQEmissionsConnector()
    history = connector.get_facility_event_history(facility_rn="RN100209451")
    
    assert isinstance(history, list)
    assert len(history) >= 1
    event = history[0]
    assert event["facility_rn"] == "RN100209451"
    assert "incident_id" in event
    assert "duration_hours" in event


def test_tceq_gulf_coast_disruption_matrix():
    """Test generating Gulf Coast disruption validation matrix."""
    connector = TCEQEmissionsConnector()
    matrix = connector.get_gulf_coast_disruption_matrix()
    
    assert isinstance(matrix, pd.DataFrame)
    assert not matrix.empty
    assert "incident_id" in matrix.columns
    assert "facility_name" in matrix.columns
    assert "so2_emitted_lbs" in matrix.columns
    assert "disruption_severity" in matrix.columns
    assert set(matrix["disruption_severity"].unique()).issubset({"Low", "Medium", "High"})


def test_tceq_live_portal_mock(monkeypatch, tmp_path):
    """Test live TCEQ Air Emission Event Report scraping and parsing."""
    storage = tmp_path / "tceq_live.csv"
    vintage = tmp_path / "tceq_live_vintages.json"
    connector = TCEQEmissionsConnector(storage_path=str(storage), vintage_path=str(vintage))

    mock_html = """
    <html>
    <body>
    <table>
      <tr>
        <td><a href="index.cfm?fuseaction=main.getDetails&target=425199">425199</a></td>
        <td>RN102579307</td>
        <td>BAYTOWN REFINERY</td>
        <td>09/20/2026</td>
        <td>AIR EMISSIONS EVENT</td>
      </tr>
    </table>
    </body>
    </html>
    """

    class MockResponse:
        status = 200
        def read(self):
            return mock_html.encode("utf-8")
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=8: MockResponse())

    events = connector.fetch_live_tceq_reports(facility_rn="RN102579307", days_back=7)
    assert len(events) >= 1
    assert events[0]["incident_id"] == "TCEQ-STEERS-425199"
    assert events[0]["facility_rn"] == "RN102579307"
    assert events[0]["source"] == "TCEQ_LIVE_PORTAL"
    assert events[0]["event_date"] == "2026-09-20"
