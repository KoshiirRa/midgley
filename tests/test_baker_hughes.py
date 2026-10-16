"""
Unit Tests for Multi-Tier Baker Hughes Rig Count Connector & VintageStore Persistence (Issue #555)
"""

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from src.alternative_data_feeds import BakerHughesDataConnector
from src.vintage_store import get_vintage_store


def test_baker_hughes_fred_rotary_rigs():
    connector = BakerHughesDataConnector()
    with patch("src.http_client.http_get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "observation_date,OGUSROTRIG\n2026-09-18,590\n2026-09-25,595\n"
        mock_get.return_value = mock_resp

        records = connector.fetch_fred_rotary_rigs()
        assert records is not None
        assert len(records) == 2
        assert records[-1]["baker_hughes_us_rig_count"] == 595
        assert records[-1]["baker_hughes_oil_rigs"] == int(595 * 0.80)
        assert records[-1]["source_tier"] == "FRED_OGUSROTRIG"


def test_baker_hughes_official_site_scrape():
    connector = BakerHughesDataConnector()
    with patch("src.firecrawl_scraper.FirecrawlConnector.scrape_url") as mock_scrape:
        mock_scrape.return_value = {
            "success": True,
            "markdown": "## U.S. Rig Count: 588\nOil Rigs: 480\nGas Rigs: 104\nPermian: 300"
        }
        records = connector.fetch_official_site_rig_counts()
        assert records is not None
        assert len(records) == 1
        assert records[0]["baker_hughes_us_rig_count"] == 588
        assert records[0]["baker_hughes_oil_rigs"] == 480
        assert records[0]["baker_hughes_gas_rigs"] == 104
        assert records[0]["permian_rigs"] == 300
        assert records[0]["source_tier"] == "OFFICIAL_WEB"


def test_baker_hughes_fetch_rig_counts_and_database_persistence():
    from src.lookup_cache import global_cache
    global_cache.delete("altdata:baker_hughes:all")
    connector = BakerHughesDataConnector()
    with patch.object(connector, "fetch_fred_rotary_rigs") as mock_fred:
        mock_fred.return_value = [
            {
                "date": "2026-09-25",
                "us_active_oil_rigs": 480,
                "baker_hughes_oil_rigs": 480,
                "baker_hughes_us_rig_count": 600,
                "baker_hughes_gas_rigs": 120,
                "permian_rigs": 310,
                "source_tier": "FRED_OGUSROTRIG"
            }
        ]
        df = connector.fetch_rig_counts()
        assert not df.empty
        assert "baker_hughes_us_rig_count" in df.columns
        assert "baker_hughes_rig_delta_4w" in df.columns

        # Verify point-in-time querying via VintageStore
        vstore = get_vintage_store()
        as_of_record = vstore.query_as_of(
            feed="baker_hughes",
            entity="us_rotary_rigs",
            target_date="2026-09-25"
        )
        assert as_of_record is not None
        assert as_of_record.get("total_rigs") == 600
