import pytest
import os
import json
import pandas as pd
from src.geopolitical_feeds import (
    GeopoliticalFeedConnector,
    get_geopolitical_maritime_events,
    calculate_chokepoint_risk_index,
    save_geopolitical_vintage_record,
    get_geopolitical_vintages_as_of,
    CHOKEPOINTS
)


def test_geopolitical_historical_events():
    df = get_geopolitical_maritime_events()
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "date" in df.columns
    assert "headline" in df.columns
    assert "chokepoint" in df.columns
    assert "Strait_of_Hormuz" in df["chokepoint"].values


def test_chokepoint_risk_index():
    df = get_geopolitical_maritime_events()
    scores = calculate_chokepoint_risk_index(df)
    assert isinstance(scores, dict)
    assert "Strait_of_Hormuz" in scores
    assert "Suez_Bab_el_Mandeb" in scores
    assert "Venezuela_Orinoco" in scores
    assert "chokepoint_risk_score" in scores["Strait_of_Hormuz"]


def test_geopolitical_vintage_persistence(tmp_path):
    temp_file = str(tmp_path / "geopolitical_vintages.json")
    records = [
        {"date": "2026-09-15", "headline": "Test Hormuz Event", "chokepoint": "Strait_of_Hormuz"}
    ]
    save_geopolitical_vintage_record(records, filepath=temp_file)
    assert os.path.exists(temp_file)

    loaded = get_geopolitical_vintages_as_of("2099-12-31", filepath=temp_file)
    assert loaded is not None
    assert len(loaded) == 1
    assert loaded[0]["headline"] == "Test Hormuz Event"


def test_geopolitical_connector():
    connector = GeopoliticalFeedConnector()
    assert connector.is_free_alternative is True
    assert connector.cost_per_query == 0.0
    headlines = connector.fetch_geopolitical_headlines()
    assert isinstance(headlines, list)


def test_normalize_url_nan_and_null_handling():
    """Asserts that normalize_url safely handles None, float('nan'), and invalid non-string inputs (Issue #603)."""
    from src.geopolitical_feeds import normalize_url
    assert normalize_url(None) == ""
    assert normalize_url(float("nan")) == ""
    assert normalize_url("nan") == ""
    assert normalize_url("https://example.com/article?utm_source=rss&ref=test") == "https://example.com/article"


def test_normalize_headline_preserves_hyphenated_words():
    """Asserts that intra-word hyphens like 'Iran-backed' are preserved while publisher suffixes are removed (Issue #603)."""
    from src.geopolitical_feeds import normalize_headline
    h1 = "Iran-backed Houthis Target Tanker in Red Sea - Reuters"
    norm = normalize_headline(h1)
    assert "iran-backed" in norm
    assert "reuters" not in norm
    assert norm == "iran-backed houthis target tanker in red sea"

    h2 = "U.S.-flagged Container Ship Encounters Naval Drone | Bloomberg"
    norm2 = normalize_headline(h2)
    assert "us-flagged" in norm2
    assert "bloomberg" not in norm2


def test_deduplicate_events_rolling_dates_and_urls():
    """Asserts that deduplicate_events catches duplicates across rolling dates and canonical URLs (Issue #603)."""
    from src.geopolitical_feeds import deduplicate_events
    events = [
        {
            "date": "2026-10-01",
            "headline": "Iran-backed Houthis launch missile at Red Sea tanker",
            "url": "https://news.example.com/houthi-missile?utm_source=feed"
        },
        {
            "date": "2026-10-02",  # Next day syndicated rewrite with same URL
            "headline": "Iran-backed Houthis fired missile at Red Sea oil tanker",
            "url": "https://news.example.com/houthi-missile?utm_source=twitter"
        },
        {
            "date": "2026-10-02",  # Next day rewrite without URL, but high headline similarity
            "headline": "Iran-backed Houthis launch missile targeting Red Sea tanker",
            "url": "https://other.example.com/story2"
        },
        {
            "date": "2026-10-01",  # Distinct story
            "headline": "Strait of Hormuz daily transit volume drops 15 percent",
            "url": "https://energy.example.com/hormuz-transit"
        }
    ]
    deduped = deduplicate_events(events, similarity_threshold=0.75)
    assert len(deduped) == 2
    assert any("hormuz" in e["headline"].lower() for e in deduped)
    assert any("houthi" in e["headline"].lower() for e in deduped)


def test_refresh_geopolitical_merge_semantics(tmp_path, monkeypatch):
    """Asserts that refresh_geopolitical merges new headlines instead of wiping existing history (Issue #603)."""
    from src.benchmark_updater import HistoricalBenchmarkManager, save_historical_benchmark, load_historical_benchmark

    bench_file = str(tmp_path / "geopolitical_historical.json")
    monkeypatch.setattr("src.benchmark_updater.BENCHMARK_STORAGE_DIR", str(tmp_path))

    initial_events = [
        {"date": "2026-09-01", "headline": "Initial historic event in Hormuz", "url": "https://a.com/1"}
    ]
    save_historical_benchmark("geopolitical", initial_events, filename=bench_file)

    # Mock fetch_geopolitical_headlines to return new event
    new_event = [{"date": "2026-10-05", "headline": "Brand new event in Suez", "url": "https://b.com/2"}]
    monkeypatch.setattr("src.geopolitical_feeds.GeopoliticalFeedConnector.fetch_geopolitical_headlines", lambda self, force_refresh=True: new_event)

    res = HistoricalBenchmarkManager.refresh_geopolitical()
    assert res["status"] == "SUCCESS"

    merged = load_historical_benchmark("geopolitical", filename=bench_file)
    assert len(merged) == 2
    assert any("initial" in e["headline"].lower() for e in merged)
    assert any("brand new" in e["headline"].lower() for e in merged)

