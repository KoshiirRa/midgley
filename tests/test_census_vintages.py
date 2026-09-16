"""
Unit tests for Census Demographics Vintage Persistence (Issue #290).
"""
import os
import tempfile
import pytest
from src.census_demographics import (
    CensusDemographicsConnector,
    save_census_vintage_record,
    get_census_vintages_as_of,
)

def test_census_vintage_persistence_and_as_of_filtering():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        temp_path = tf.name

    try:
        # Save sample vintage records
        rec1 = {
            "region_id": "tulsa_ok",
            "as_of": "2026-03-01 10:00:00",
            "valid_date": "2026-03-01",
            "population": 413000,
            "median_household_income": 62000,
            "mean_commute_minutes": 21.5,
            "vehicles_per_household": 1.95
        }
        rec2 = {
            "region_id": "newark_de",
            "as_of": "2026-03-10 10:00:00",
            "valid_date": "2026-03-10",
            "population": 31500,
            "median_household_income": 65000,
            "mean_commute_minutes": 23.0,
            "vehicles_per_household": 1.80
        }
        rec3 = {
            "region_id": "tulsa_ok",
            "as_of": "2026-03-15 10:00:00",
            "valid_date": "2026-03-15",
            "population": 414000,
            "median_household_income": 62500,
            "mean_commute_minutes": 21.6,
            "vehicles_per_household": 1.95
        }

        save_census_vintage_record(rec1, filepath=temp_path)
        save_census_vintage_record(rec2, filepath=temp_path)
        save_census_vintage_record(rec3, filepath=temp_path)

        # Query as of 2026-03-05
        vintages_early = get_census_vintages_as_of("2026-03-05", filepath=temp_path)
        assert len(vintages_early) == 1
        assert vintages_early[0]["region_id"] == "tulsa_ok"
        assert vintages_early[0]["demographics"]["population"] == 413000

        # Query as of 2026-03-12 for tulsa_ok
        vintages_tulsa_mid = get_census_vintages_as_of("2026-03-12", region_id="tulsa_ok", filepath=temp_path)
        assert len(vintages_tulsa_mid) == 1
        assert vintages_tulsa_mid[0]["demographics"]["population"] == 413000

        # Query as of 2026-03-20
        vintages_all = get_census_vintages_as_of("2026-03-20", filepath=temp_path)
        assert len(vintages_all) == 3

        # Test connector methods
        conn = CensusDemographicsConnector()
        conn_vintages = conn.get_census_vintages_as_of("2026-03-20", region_id="newark_de", filepath=temp_path)
        assert len(conn_vintages) == 1
        assert conn_vintages[0]["region_id"] == "newark_de"

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
