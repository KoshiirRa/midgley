"""
Unit Tests for Headline Normalization & Syndicated Story Deduplication (Issue #566)
"""

import pytest
from src.geopolitical_feeds import (
    normalize_url,
    normalize_headline,
    compute_headline_similarity,
    deduplicate_events
)


def test_normalize_url():
    raw_url = "https://www.reuters.com/business/energy/oil-prices-rise-2026-10-02/?utm_source=twitter&utm_medium=social&ref=feed#anchor"
    norm = normalize_url(raw_url)
    assert norm == "https://www.reuters.com/business/energy/oil-prices-rise-2026-10-02"
    assert "utm_source" not in norm
    assert "anchor" not in norm


def test_normalize_headline():
    h1 = "Iran Seizes Oil Tanker Near Strait of Hormuz - Reuters"
    h2 = "Iran seizes oil tanker near Strait of Hormuz | AP News"
    assert normalize_headline(h1) == "iran seizes oil tanker near strait of hormuz"
    assert normalize_headline(h2) == "iran seizes oil tanker near strait of hormuz"


def test_compute_headline_similarity():
    h1 = "Iran IRGC Navy seizes oil tanker Advantage Sweet in Strait of Hormuz"
    h2 = "Iran seizes oil tanker Advantage Sweet in Strait of Hormuz - AP"
    sim = compute_headline_similarity(h1, h2)
    assert sim >= 0.70


def test_deduplicate_events_syndicated():
    events = [
        {
            "date": "2026-10-02",
            "headline": "Iran IRGC Navy seizes oil tanker in Strait of Hormuz - Reuters",
            "url": "https://reuters.com/article1?utm_source=rss"
        },
        {
            "date": "2026-10-02",
            "headline": "Iran IRGC Navy seizes oil tanker in Strait of Hormuz - Bloomberg",
            "url": "https://bloomberg.com/news1?utm_medium=web"
        },
        {
            "date": "2026-10-02",
            "headline": "Suez Canal container traffic halts after Red Sea drone strike",
            "url": "https://maritime-exec.com/news2"
        }
    ]
    deduped = deduplicate_events(events, similarity_threshold=0.80)
    assert len(deduped) == 2
    assert deduped[0]["headline"] == "Iran IRGC Navy seizes oil tanker in Strait of Hormuz - Reuters"
    assert deduped[1]["headline"] == "Suez Canal container traffic halts after Red Sea drone strike"
