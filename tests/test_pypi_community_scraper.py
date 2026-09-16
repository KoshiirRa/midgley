import pytest
from unittest.mock import patch
from src.live_fuel_feed import PyPICommunityFuelScraper, REGION_METADATA

def test_pypi_community_scraper_dynamic_resolution():
    scraper = PyPICommunityFuelScraper()
    mock_live = {
        "region": "Tulsa_OK",
        "price": 2.799,
        "source": "GasBuddy Live GraphQL API",
        "timestamp": "2026-03-15 12:00:00"
    }
    with patch("src.live_fuel_feed.fetch_live_metro_retail_price", return_value=mock_live):
        res = scraper.fetch_community_price("Tulsa_OK")
        assert res["region"] == "Tulsa_OK"
        assert res["price"] == 2.799
        assert "GasBuddy" in res["source"]
        assert res["is_live_dynamic"] is True

def test_pypi_community_scraper_fallback():
    scraper = PyPICommunityFuelScraper()
    with patch("src.live_fuel_feed.fetch_live_metro_retail_price", side_effect=Exception("API offline")):
        res = scraper.fetch_community_price("Tulsa_OK")
        assert res["region"] == "Tulsa_OK"
        assert res["price"] == REGION_METADATA["Tulsa_OK"]["static_anchor"]
        assert res["is_live_dynamic"] is False
