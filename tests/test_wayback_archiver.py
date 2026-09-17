"""
Unit Tests for Wayback Machine Archiver & Canonical URL Resolver (tests/test_wayback_archiver.py)
Issue #259 & Issue #197
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock

from src.wayback_archiver import (
    is_google_news_redirect,
    resolve_canonical_url,
    archive_url_to_wayback,
    _load_wayback_cache,
    _save_wayback_cache,
)


def test_is_google_news_redirect():
    """Verifies identification of Google News redirect URLs vs direct publisher URLs."""
    assert is_google_news_redirect("https://news.google.com/rss/articles/CBMivwFBVV95cUxN?oc=5") is True
    assert is_google_news_redirect("https://news.google.com/articles/CBMivwFBVV95cUxN") is True
    assert is_google_news_redirect("https://news.google.com/__i/rss/rd/articles/CBMivwFBVV95cUxN") is True
    assert is_google_news_redirect("https://www.reuters.com/business/energy/oil-prices-rise-2026-09-15/") is False
    assert is_google_news_redirect("https://www.bloomberg.com/news/articles/2026-09-15/refinery-fire") is False
    assert is_google_news_redirect("") is False
    assert is_google_news_redirect(None) is False


def test_resolve_canonical_url_direct_pass_through():
    """Verifies that non-Google URLs pass through immediately without HTTP requests."""
    url = "https://www.reuters.com/business/energy/oil-prices-rise-2026-09-15/"
    with patch("requests.head") as mock_head:
        resolved = resolve_canonical_url(url)
        assert resolved == url
        mock_head.assert_not_called()


def test_resolve_canonical_url_google_news_mocked_head():
    """Verifies successful uncurling of Google News redirect URL via HTTP HEAD."""
    google_url = "https://news.google.com/rss/articles/CBMivwFBVV95cUxN?oc=5"
    publisher_url = "https://www.reuters.com/business/energy/oil-prices-rise-2026-09-15/"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.url = publisher_url

    with patch("requests.head", return_value=mock_resp) as mock_head:
        resolved = resolve_canonical_url(google_url)
        assert resolved == publisher_url
        mock_head.assert_called_once()


def test_resolve_canonical_url_fallback_to_get():
    """Verifies fallback to HTTP GET when HEAD is not supported (HTTP 405)."""
    google_url = "https://news.google.com/rss/articles/CBMivwFBVV95cUxN?oc=5"
    publisher_url = "https://www.bloomberg.com/news/articles/2026-09-15/refinery-fire"

    mock_head_resp = MagicMock()
    mock_head_resp.status_code = 405
    mock_head_resp.url = google_url

    mock_get_resp = MagicMock()
    mock_get_resp.status_code = 200
    mock_get_resp.url = publisher_url

    with patch("requests.head", return_value=mock_head_resp), \
         patch("requests.get", return_value=mock_get_resp):
        resolved = resolve_canonical_url(google_url)
        assert resolved == publisher_url


def test_resolve_canonical_url_timeout_fallback():
    """Verifies that network errors/timeouts return the original URL gracefully."""
    google_url = "https://news.google.com/rss/articles/CBMivwFBVV95cUxN?oc=5"

    with patch("requests.head", side_effect=Exception("Connection timed out")):
        resolved = resolve_canonical_url(google_url)
        assert resolved == google_url


def test_archive_url_to_wayback_testing_mode():
    """Verifies testing mode behavior with canonical resolution and URL formatting."""
    google_url = "https://news.google.com/rss/articles/CBMivwFBVV95cUxN?oc=5"
    publisher_url = "https://www.nst.com.my/business/corporate/2026/09/oil-surge"

    with patch.dict(os.environ, {"TESTING": "1"}), \
         patch("src.wayback_archiver.resolve_canonical_url", return_value=publisher_url):
        res = archive_url_to_wayback(google_url, headline="Oil Prices Surge 3%")

        assert res["status"] == "TEST_SUPPRESSED"
        assert res["url"] == google_url
        assert res["canonical_url"] == publisher_url
        assert res["archive_url"] == f"https://web.archive.org/web/*/{publisher_url}"
        assert res["headline"] == "Oil Prices Surge 3%"


def test_archive_url_invalid_url():
    """Verifies handling of empty or non-HTTP URLs."""
    res = archive_url_to_wayback("ftp://invalid.com")
    assert res["status"] == "SKIPPED_INVALID_URL"
    assert archive_url_to_wayback("")["status"] == "SKIPPED_INVALID_URL"


def test_archive_url_cache_hit(tmp_path):
    """Verifies cache hits bypass outbound HTTP requests."""
    cache_file = str(tmp_path / "wayback_archive_cache.json")
    cached_url = "https://www.reuters.com/business/energy/test-article"
    cached_record = {
        "status": "SUBMITTED",
        "url": cached_url,
        "canonical_url": cached_url,
        "archive_url": f"https://web.archive.org/web/*/{cached_url}"
    }

    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump({cached_url: cached_record}, f)

    with patch("src.wayback_archiver.CACHE_PATH", cache_file):
        res = archive_url_to_wayback(cached_url)
        assert res["status"] == "SUBMITTED"
        assert res["archive_url"] == cached_record["archive_url"]
