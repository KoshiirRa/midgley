"""
Unit Test Suite for Refinery Outage Connectors & Historical Evaluation Storage (tests/test_outage_connectors.py)
Tests TCEQEmissionsConnector, LDEQEmissionsConnector, NRCIncidentConnector,
unified outage dataset compilation, and weekly review attribution formatting. (Issue #406)
"""

import os
import pytest
import pandas as pd
from src.tceq_emissions import TCEQEmissionsConnector, get_unified_gulf_coast_outages
from src.ldeq_emissions import LDEQEmissionsConnector, LOUISIANA_REFINERIES
from src.nrc_incidents import NRCIncidentConnector
from src.weekly_issue_reporter import format_refinery_outage_attribution_markdown


def test_tceq_emissions_connector_storage():
    connector = TCEQEmissionsConnector()
    df = connector.fetch_emissions_events(only_unplanned=True)
    assert not df.empty
    assert "incident_id" in df.columns
    assert "facility_rn" in df.columns
    assert "event_date" in df.columns
    assert "duration_hours" in df.columns
    assert "so2_emitted_lbs" in df.columns
    assert "unplanned_shutdown" in df.columns


def test_ldeq_emissions_connector_storage():
    connector = LDEQEmissionsConnector()
    df = connector.fetch_emissions_events(only_unplanned=True)
    assert not df.empty
    assert "incident_id" in df.columns
    assert "agency_interest_id" in df.columns
    assert "event_date" in df.columns
    assert "duration_hours" in df.columns
    assert "unplanned_shutdown" in df.columns

    # Test facility history lookup
    history = connector.get_facility_event_history("AI_3154")
    assert isinstance(history, list)
    assert len(history) >= 1
    assert history[0]["facility_name"] == "Marathon Garyville Refinery"


def test_nrc_incident_connector_storage():
    connector = NRCIncidentConnector()
    df = connector.fetch_incident_events(only_unplanned=True)
    assert not df.empty
    assert "incident_id" in df.columns
    assert "incident_date" in df.columns
    assert "facility_or_carrier" in df.columns
    assert "corridor" in df.columns


def test_get_unified_gulf_coast_outages():
    df_unified = get_unified_gulf_coast_outages(force_refresh=True)
    assert not df_unified.empty
    assert "incident_id" in df_unified.columns
    assert "source_agency" in df_unified.columns
    assert "facility_name" in df_unified.columns
    assert "state" in df_unified.columns
    assert "event_date" in df_unified.columns
    assert "disruption_severity" in df_unified.columns

    # Verify cross-agency presence
    sources = df_unified["source_agency"].unique()
    assert "TCEQ" in sources
    assert "LDEQ" in sources
    assert "USCG_NRC" in sources


def test_weekly_review_outage_attribution_markdown():
    section_md = format_refinery_outage_attribution_markdown(window_days=365)
    assert "### 🏭 Gulf Coast Refinery & Midstream Outage Error Attribution" in section_md
    assert "TCEQ" in section_md or "LDEQ" in section_md
    assert "Normal Operations Rolling MAE" in section_md
