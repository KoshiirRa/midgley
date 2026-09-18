"""
Unit Tests for Agent-Reach Resilient Reachability Layer (Issue #308)
Tests RSSSyndicationAdapter, PublicProxyAdapter, SearchFallbackAdapter,
and ReachabilityCascadeRouter priority failover and deduplication.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock
from src.reachability_adapters import (
    compute_headline_hash,
    BaseReachabilityAdapter,
    RSSSyndicationAdapter,
    PublicProxyAdapter,
    SearchFallbackAdapter,
    ReachabilityCascadeRouter
)


def test_compute_headline_hash_deduplication():
    h1 = compute_headline_hash("Trump announces new energy tariffs on foreign oil - Reuters")
    h2 = compute_headline_hash("Trump announces new energy tariffs on foreign oil - Bloomberg")
    h3 = compute_headline_hash("TRUMP ANNOUNCES NEW ENERGY TARIFFS ON FOREIGN OIL")
    assert h1 == h2 == h3


def test_rss_syndication_adapter_parsing():
    adapter = RSSSyndicationAdapter()
    
    mock_rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>Google News</title>
            <item>
                <title>OPEC decides to extend voluntary crude oil production cuts - OilPrice.com</title>
                <link>https://news.google.com/articles/12345</link>
                <pubDate>Fri, 18 Sep 2026 14:00:00 GMT</pubDate>
            </item>
        </channel>
    </rss>
    """
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = mock_rss_xml.encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        posts = adapter.fetch_posts("opec oil cuts", limit=5)
        assert len(posts) == 1
        assert "OPEC decides to extend" in posts[0]["text"]
        assert posts[0]["protocol"] == "rss_syndication"
        assert posts[0]["adapter"] == "rss_syndication"


def test_public_proxy_adapter_parsing():
    adapter = PublicProxyAdapter()

    mock_reddit_json = {
        "data": {
            "children": [
                {
                    "data": {
                        "title": "Red Sea tanker transit drops as insurance premiums spike",
                        "permalink": "/r/energy/comments/xyz123/red_sea_tanker/",
                        "subreddit": "energy",
                        "created_utc": 1789760000.0
                    }
                }
            ]
        }
    }
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps(mock_reddit_json).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        posts = adapter.fetch_posts("red sea tanker", limit=5)
        assert len(posts) == 1
        assert "Red Sea tanker" in posts[0]["text"]
        assert posts[0]["protocol"] == "public_proxy"


def test_reachability_cascade_router_failover():
    # Adapter 1 fails/returns empty, Adapter 2 succeeds
    mock_adapter_1 = MagicMock(spec=BaseReachabilityAdapter)
    mock_adapter_1.name = "failing_rss"
    mock_adapter_1.priority = 1
    mock_adapter_1.fetch_posts.return_value = []

    mock_adapter_2 = MagicMock(spec=BaseReachabilityAdapter)
    mock_adapter_2.name = "working_proxy"
    mock_adapter_2.priority = 2
    mock_adapter_2.fetch_posts.return_value = [
        {"text": "Breaking energy headline from backup proxy", "url": "https://example.com/item"}
    ]

    router = ReachabilityCascadeRouter(adapters=[mock_adapter_1, mock_adapter_2])
    results = router.fetch_resilient_posts("energy crisis", target_feed="test_unit", limit=2, cache_ttl_seconds=0)

    assert len(results) == 1
    assert results[0]["text"] == "Breaking energy headline from backup proxy"
    assert "headline_hash" in results[0]
    mock_adapter_1.fetch_posts.assert_called_once()
    mock_adapter_2.fetch_posts.assert_called_once()
