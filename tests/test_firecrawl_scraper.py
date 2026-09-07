"""
Unit Tests for Firecrawl Web-to-Markdown Scraper Connector (tests/test_firecrawl_scraper.py)
Verifies:
- Firecrawl API response parsing and markdown extraction
- 24-hour disk & memory caching
- Quota safety valve enforcement (800 monthly / 30 daily cap)
- Deterministic offline HTML-to-markdown fallback extractor
- HTTP error (429/500) resilience & fallback routing
- Event analyzer extract_event_features_from_url integration
"""

import os
import json
import time
import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO

from src.firecrawl_scraper import (
    FirecrawlConnector,
    SimpleHTMLTextExtractor,
    _get_url_hash,
    _check_and_increment_quota,
    get_firecrawl_quota_status,
    MAX_MONTHLY_CALLS,
    MAX_DAILY_CALLS
)
from src.event_analyzer import extract_event_features_from_url
from src.telemetry import get_all_quota_statuses


@pytest.fixture(autouse=True)
def setup_test_env(tmp_path, monkeypatch):
    """Sets up temporary files and isolated test environment."""
    test_cache = str(tmp_path / "firecrawl_cache.json")
    test_quota = str(tmp_path / "firecrawl_quota.json")
    monkeypatch.setattr("src.firecrawl_scraper.CACHE_FILE", test_cache)
    monkeypatch.setattr("src.firecrawl_scraper.QUOTA_FILE", test_quota)
    monkeypatch.setattr("src.firecrawl_scraper._IN_MEMORY_SCRAPE_CACHE", {})
    monkeypatch.setenv("TESTING", "1")


def test_simple_html_text_extractor():
    """Verifies that SimpleHTMLTextExtractor strips noise tags and formats basic Markdown."""
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Refinery Fire Halts Production</title>
        <style>.nav { color: red; }</style>
        <script>console.log('tracking');</script>
    </head>
    <body>
        <nav><a href="/home">Home</a><a href="/news">News</a></nav>
        <header>Header Banner</header>
        <h1>Major Refinery Explosion in Delaware City</h1>
        <p>An unexpected <b>explosion</b> occurred at the FCC unit today.</p>
        <ul>
            <li>Unit 4 shutdown</li>
            <li>No casualties reported</li>
        </ul>
        <footer>Copyright 2026 Energy Wire</footer>
    </body>
    </html>
    """
    parser = SimpleHTMLTextExtractor()
    parser.feed(sample_html)
    text = parser.get_text()

    assert parser.title == "Refinery Fire Halts Production"
    assert "Delaware City" in text
    assert "FCC unit" in text
    assert "Unit 4 shutdown" in text
    assert "tracking" not in text
    assert "Header Banner" not in text
    assert "Copyright 2026" not in text


def test_firecrawl_scrape_url_success():
    """Verifies successful scraping via Firecrawl API."""
    mock_api_response = {
        "success": True,
        "data": {
            "markdown": "# West Tulsa Refinery Outage\n\nHF Sinclair reports an unplanned crude distillation unit trip.",
            "metadata": {
                "title": "West Tulsa Refinery Outage",
                "description": "Unplanned shutdown at HF Sinclair",
                "statusCode": 200
            }
        }
    }

    mock_resp = MagicMock()
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.getcode.return_value = 200
    mock_resp.read.return_value = json.dumps(mock_api_response).encode("utf-8")

    with patch("urllib.request.urlopen", return_value=mock_resp):
        connector = FirecrawlConnector(api_key="test_fc_key_123")
        res = connector.scrape_url("https://example.com/energy-news/1")

        assert res["success"] is True
        assert res["provider"] == "firecrawl_v1"
        assert "West Tulsa Refinery Outage" in res["markdown"]
        assert res["title"] == "West Tulsa Refinery Outage"
        assert res["status_code"] == 200


def test_firecrawl_cache_persistence():
    """Verifies that subsequent scrapes for the same URL within TTL hit cache without calling API."""
    mock_api_response = {
        "success": True,
        "data": {
            "markdown": "# Cached Headline\n\nArticle content for caching.",
            "metadata": {"title": "Cached Headline"}
        }
    }
    mock_resp = MagicMock()
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.getcode.return_value = 200
    mock_resp.read.return_value = json.dumps(mock_api_response).encode("utf-8")

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        connector = FirecrawlConnector(api_key="test_fc_key_123")
        url = "https://example.com/test-cache"

        res1 = connector.scrape_url(url)
        assert mock_urlopen.call_count == 1
        assert res1["success"] is True

        # Second call should hit in-memory / disk cache
        res2 = connector.scrape_url(url)
        assert mock_urlopen.call_count == 1  # No additional network call
        assert res2["markdown"] == res1["markdown"]


def test_firecrawl_quota_safety_valve(tmp_path, monkeypatch):
    """Verifies that exceeding monthly or daily quota limits trips safety valve and routes to native fallback."""
    # Seed quota ledger at limit
    test_quota_file = str(tmp_path / "firecrawl_quota.json")
    monkeypatch.setattr("src.firecrawl_scraper.QUOTA_FILE", test_quota_file)
    from datetime import datetime
    now = datetime.now()
    month_key = now.strftime("%Y-%m")
    day_key = now.strftime("%Y-%m-%d")

    capped_data = {
        "current_month": month_key,
        "monthly_calls": MAX_MONTHLY_CALLS,
        "daily_calls": {day_key: MAX_DAILY_CALLS},
        "last_reset": now.isoformat()
    }
    with open(test_quota_file, "w", encoding="utf-8") as f:
        json.dump(capped_data, f)

    allowed, status = _check_and_increment_quota()
    assert allowed is False
    assert status["reason"] == "Quota limit reached"

    quota_status = get_firecrawl_quota_status()
    assert quota_status["status"] == "SAFETY_VALVE_ACTIVE"
    assert quota_status["remaining_monthly"] == 0

    # Test scrape_url under safety valve routes to fallback
    fallback_html = "<html><head><title>Fallback Page</title></head><body><p>Offline article text</p></body></html>"
    mock_fallback_resp = MagicMock()
    mock_fallback_resp.__enter__.return_value = mock_fallback_resp
    mock_fallback_resp.read.return_value = fallback_html.encode("utf-8")

    with patch("urllib.request.urlopen", return_value=mock_fallback_resp):
        connector = FirecrawlConnector(api_key="test_fc_key_123")
        res = connector.scrape_url("https://example.com/quota-test")

        assert res["success"] is True
        assert res["provider"] == "native_html_fallback"
        assert "Offline article text" in res["markdown"]


def test_firecrawl_http_error_graceful_fallback():
    """Verifies that Firecrawl API HTTP errors (e.g. 429 / 500) trigger native fallback gracefully."""
    import urllib.error
    http_error = urllib.error.HTTPError(
        url="https://api.firecrawl.dev/v1/scrape",
        code=429,
        msg="Rate limit exceeded",
        hdrs={},
        fp=BytesIO(b'{"error": "Rate limit exceeded"}')
    )

    fallback_html = "<html><head><title>Fallback Headline</title></head><body><p>Fallback article text after 429</p></body></html>"
    mock_fallback_resp = MagicMock()
    mock_fallback_resp.__enter__.return_value = mock_fallback_resp
    mock_fallback_resp.read.return_value = fallback_html.encode("utf-8")

    def mock_urlopen_side_effect(req, *args, **kwargs):
        if hasattr(req, "full_url") and "api.firecrawl.dev" in req.full_url:
            raise http_error
        return mock_fallback_resp

    with patch("urllib.request.urlopen", side_effect=mock_urlopen_side_effect):
        connector = FirecrawlConnector(api_key="test_fc_key_123")
        res = connector.scrape_url("https://example.com/rate-limit-test")

        assert res["success"] is True
        assert res["provider"] == "native_html_fallback"
        assert "Fallback article text after 429" in res["markdown"]


def test_event_analyzer_extract_from_url():
    """Verifies extract_event_features_from_url in src/event_analyzer.py end-to-end."""
    mock_scrape = {
        "success": True,
        "provider": "firecrawl_v1",
        "markdown": "# Severe Pipeline Explosion Halts Fuel Shipments\nA massive pipeline explosion halted refined product delivery into regional hubs.",
        "title": "Severe Pipeline Explosion Halts Fuel Shipments",
        "url": "https://example.com/breaking-pipeline-outage"
    }

    with patch.object(FirecrawlConnector, "scrape_url", return_value=mock_scrape):
        res = extract_event_features_from_url(
            "https://example.com/breaking-pipeline-outage",
            tier="basic"  # Basic tier uses deterministic offline lexicon
        )

        assert res["url"] == "https://example.com/breaking-pipeline-outage"
        assert res["title"] == "Severe Pipeline Explosion Halts Fuel Shipments"
        assert res["supply_disruption"] > 0.0
        assert res["overall_price_pressure"] > 0.0


def test_telemetry_get_all_quota_statuses_includes_firecrawl():
    """Verifies that telemetry get_all_quota_statuses includes firecrawl service."""
    quotas = get_all_quota_statuses()
    assert "firecrawl" in quotas
    assert quotas["firecrawl"]["service"] == "Firecrawl.dev"
    assert quotas["firecrawl"]["limit"] == 800
    assert quotas["firecrawl"]["remaining"] <= 800
