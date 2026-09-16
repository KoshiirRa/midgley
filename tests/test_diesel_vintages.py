"""
Unit tests for ULSD / Regional Retail Diesel Vintage Persistence (Issue #295).
"""
import os
import tempfile
import pytest
from src.diesel_regional import (
    UltraLowSulfurDieselForecastingAgent,
    save_diesel_vintage_record,
    get_diesel_vintages_as_of,
)

def test_diesel_vintage_persistence_and_as_of_filtering():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        temp_path = tf.name

    try:
        rec1 = {
            "locale": "tulsa",
            "as_of": "2026-03-01 10:00:00",
            "valid_date": "2026-03-01",
            "price": 3.650
        }
        rec2 = {
            "locale": "oakland",
            "as_of": "2026-03-10 10:00:00",
            "valid_date": "2026-03-10",
            "price": 5.250
        }
        rec3 = {
            "locale": "tulsa",
            "as_of": "2026-03-15 10:00:00",
            "valid_date": "2026-03-15",
            "price": 3.680
        }

        save_diesel_vintage_record(rec1, filepath=temp_path)
        save_diesel_vintage_record(rec2, filepath=temp_path)
        save_diesel_vintage_record(rec3, filepath=temp_path)

        # Query as of 2026-03-05
        vintages_early = get_diesel_vintages_as_of("2026-03-05", filepath=temp_path)
        assert len(vintages_early) == 1
        assert vintages_early[0]["locale"] == "tulsa"
        assert vintages_early[0]["price"] == 3.650

        # Query as of 2026-03-12 for oakland
        vintages_oakland = get_diesel_vintages_as_of("2026-03-12", locale="oakland", filepath=temp_path)
        assert len(vintages_oakland) == 1
        assert vintages_oakland[0]["price"] == 5.250

        # Query as of 2026-03-20
        vintages_all = get_diesel_vintages_as_of("2026-03-20", filepath=temp_path)
        assert len(vintages_all) == 3

        # Agent methods
        agent = UltraLowSulfurDieselForecastingAgent()
        agent_vintages = agent.get_diesel_vintages_as_of("2026-03-20", locale="tulsa", filepath=temp_path)
        assert len(agent_vintages) == 2

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
