"""
Tests for Wayback Machine Cloud Archiver & Availability Pre-Check (Issue #491).
"""

import os
import time
import pytest
from unittest.mock import patch, MagicMock
from src.wayback_archiver import (
    is_google_news_redirect,
    resolve_canonical_url,
    check_wayback_availability,
    archive_url_to_wayback
)


def test_is_google_news_redirect():
    assert is_google_news_redirect("https://news.google.com/rss/articles/CBMiRGh0dHBzOi...") is True
    assert is_google_news_redirect("https://news.google.com/articles/CBMiRGh0dHBzOi...") is True
    assert is_google_news_redirect("https://www.reuters.com/business/energy/oil-rises-2026-10-02") is False
    assert is_google_news_redirect("") is False


def test_wayback_availability_pre_check_mock():
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.getcode.return_value = 200
        mock_resp.read.return_value = b'{"archived_snapshots":{"closest":{"available":true,"url":"https://web.archive.org/web/20261001120000/https://reuters.com/article"}}}'
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        res = check_wayback_availability("https://reuters.com/article")
        assert res == "https://web.archive.org/web/20261001120000/https://reuters.com/article"


def test_archive_url_with_availability_avoids_write_save():
    with patch.dict(os.environ, {"TESTING": "0", "SUPPRESS_OUTBOUND_APIS": "0"}):
        with patch("src.wayback_archiver.check_wayback_availability") as mock_avail:
            mock_avail.return_value = "https://web.archive.org/web/20261001120000/https://reuters.com/sample"

            rec = archive_url_to_wayback("https://reuters.com/sample", headline="Oil Rises")
            assert rec["status"] == "AVAILABLE_SNAPSHOT"
            assert rec["archive_url"] == "https://web.archive.org/web/20261001120000/https://reuters.com/sample"


def test_wayback_archive_test_suppression():
    with patch.dict(os.environ, {"TESTING": "1"}):
        rec = archive_url_to_wayback("https://bloomberg.com/energy-test", headline="Test Article")
        assert rec["status"] == "TEST_SUPPRESSED"
        assert "archive_url" in rec
