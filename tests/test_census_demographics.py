"""
Unit Tests for U.S. Census Bureau Demographics & Commuter Metrics Module (tests/test_census_demographics.py)
Tests adaptive annual release window lifecycle, derived commuter metrics, and tiered caching.
"""

import pytest
from datetime import date, datetime
from unittest.mock import patch, MagicMock

from src.census_demographics import (
    CensusDemographicsConnector,
    get_census_release_window_status,
    compute_derived_commuter_metrics,
    METRO_CENSUS_MAPPINGS
)
from src.dynamic_region import DynamicRegionRunner


def test_census_release_window_status_inside_september():
    """Tests that dates in September trigger WINDOW_ACTIVE_CHECKING with 24h TTL."""
    sept_date = date(2026, 9, 15)
    status = get_census_release_window_status(sept_date)

    assert status["is_in_release_window"] is True
    assert status["status_mode"] == "WINDOW_ACTIVE_CHECKING"
    assert status["recommended_ttl_seconds"] == 86400
    assert status["expected_vintage"] == 2025
    assert "Sept 1-30" in status["description"]


def test_census_release_window_status_outside_september():
    """Tests that dates outside September trigger LOCKED_ANNUAL_CACHE with long-term TTL."""
    march_date = date(2026, 3, 15)
    status = get_census_release_window_status(march_date)

    assert status["is_in_release_window"] is False
    assert status["status_mode"] == "LOCKED_ANNUAL_CACHE"
    assert status["recommended_ttl_seconds"] > 86400 * 30
    assert status["expected_vintage"] == 2024
    assert status["locked_until"] == "2026-08-31"

    oct_date = date(2026, 10, 1)
    status_oct = get_census_release_window_status(oct_date)
    assert status_oct["is_in_release_window"] is False
    assert status_oct["status_mode"] == "LOCKED_ANNUAL_CACHE"
    assert status_oct["expected_vintage"] == 2025
    assert status_oct["locked_until"] == "2027-08-31"


def test_compute_derived_commuter_metrics():
    """Tests the econometric calculations for vehicle dependency and captive demand score."""
    sample_raw = {
        "B08201_001E": 100000,
        "B08201_002E": 5000,
        "B08201_003E": 35000,
        "B08201_004E": 40000,
        "B08201_005E": 15000,
        "B08201_006E": 5000,
        "B08301_001E": 120000,
        "B08301_003E": 96000, # 80% drive alone
        "B08301_004E": 12000, # 10% carpool
        "B08301_010E": 2400,  # 2% transit
        "B08301_021E": 6000,  # 5% WFH
        "B08013_001E": 2850000 # 25 min mean commute
    }

    metrics = compute_derived_commuter_metrics(sample_raw, vintage_year=2024)

    assert metrics["vintage_year"] == 2024
    assert metrics["total_households"] == 100000
    assert metrics["zero_vehicle_pct"] == 5.0
    assert metrics["vehicles_per_household"] == 1.80
    assert metrics["drive_alone_share"] == 0.800
    assert metrics["carpool_share"] == 0.100
    assert metrics["vehicle_dependency_ratio"] == 0.900
    assert metrics["public_transit_share"] == 0.020
    assert metrics["work_from_home_share"] == 0.050
    assert metrics["mean_commute_minutes"] == 25.0
    assert 0.75 <= metrics["inelastic_demand_score"] <= 0.95


def test_census_demographics_connector_deterministic_fallback():
    """Tests that CensusDemographicsConnector falls back cleanly when offline."""
    connector = CensusDemographicsConnector()

    with patch.object(connector, "fetch_live_census_acs", return_value=None):
        res = connector.get_metro_demographics("tulsa_ok", current_date=date(2026, 3, 1), force_refresh=True)

        assert res["region_id"] == "tulsa_ok"
        assert "demographics" in res
        assert res["demographics"]["inelastic_demand_score"] >= 0.80
        assert res["is_free_alternative"] is True
        assert res["cost_per_query"] == 0.0


def test_census_demographics_connector_live_fetch():
    """Tests successful live census response parsing and caching."""
    connector = CensusDemographicsConnector()
    mock_raw = {
        "B08201_001E": 200000,
        "B08201_002E": 10000,
        "B08201_003E": 70000,
        "B08201_004E": 80000,
        "B08201_005E": 30000,
        "B08201_006E": 10000,
        "B08301_001E": 250000,
        "B08301_003E": 180000,
        "B08301_004E": 25000,
        "B08301_010E": 10000,
        "B08301_021E": 20000,
        "B08013_001E": 6210000
    }

    with patch.object(connector, "fetch_live_census_acs", return_value=mock_raw):
        res = connector.get_metro_demographics("cincinnati_oh", current_date=date(2026, 9, 15), force_refresh=True)

        assert res["region_id"] == "cincinnati_oh"
        assert res["demographics"]["vintage_year"] == 2025
        assert res["cache_status"] == "LIVE_VINTAGE_UPGRADE_FETCHED"
        assert res["demographics"]["vehicles_per_household"] == 1.80


def test_get_all_metro_demographics():
    """Tests multi-metro dictionary generation across all target hubs."""
    connector = CensusDemographicsConnector()
    with patch.object(connector, "fetch_live_census_acs", return_value=None):
        all_metros = connector.get_all_metro_demographics(current_date=date(2026, 4, 1))

        assert all_metros["status"] == "SUCCESS"
        assert all_metros["supported_metros_count"] >= 7
        assert "tulsa_ok" in all_metros["metros"]
        assert "oakland_ca" in all_metros["metros"]
        assert "newark_de" in all_metros["metros"]
        assert all_metros["metros"]["oakland_ca"]["demographics"]["inelastic_demand_score"] < all_metros["metros"]["tulsa_ok"]["demographics"]["inelastic_demand_score"]


def test_dynamic_region_commuter_demographics_integration():
    """Tests that DynamicRegionRunner ingests and exposes commuter demographics."""
    runner = DynamicRegionRunner("tulsa_ok")
    assert runner.commuter_demographics is not None
    assert runner.commuter_demographics.get("vehicle_dependency_ratio", 0) > 0.85
