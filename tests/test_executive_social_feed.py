import os
import json
import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import patch, MagicMock
from src.executive_social_feed import (
    ExecutiveSocialFeedConnector,
    get_executive_social_energy_feed,
    calculate_weekend_social_sentiment_index,
    is_timestamp_weekend,
    HISTORICAL_EXECUTIVE_ENERGY_POSTS
)
from src.lookup_cache import global_cache

def test_is_timestamp_weekend():
    # Friday 16:00 (not weekend)
    fri_open = datetime(2026, 9, 11, 16, 0)
    assert not is_timestamp_weekend(fri_open)
    
    # Friday 18:00 (weekend)
    fri_close = datetime(2026, 9, 11, 18, 0)
    assert is_timestamp_weekend(fri_close)
    
    # Saturday 12:00 (weekend)
    sat = datetime(2026, 9, 12, 12, 0)
    assert is_timestamp_weekend(sat)
    
    # Sunday 17:00 (weekend)
    sun_before_open = datetime(2026, 9, 13, 17, 0)
    assert is_timestamp_weekend(sun_before_open)
    
    # Sunday 19:00 (not weekend - futures opened)
    sun_after_open = datetime(2026, 9, 13, 19, 0)
    assert not is_timestamp_weekend(sun_after_open)
    
    # Monday 09:00 (not weekend)
    mon = datetime(2026, 9, 14, 9, 0)
    assert not is_timestamp_weekend(mon)

def test_historical_executive_posts_preserved():
    connector = ExecutiveSocialFeedConnector()
    df = connector.get_combined_feed(include_live=False)
    assert len(df) >= len(HISTORICAL_EXECUTIVE_ENERGY_POSTS)
    assert "is_weekend" in df.columns
    assert "actual_1d_rbob_return_pct" in df.columns
    assert "post_text" in df.columns

def test_calculate_weekend_social_sentiment_index():
    df = get_executive_social_energy_feed(include_live=False)
    metrics = calculate_weekend_social_sentiment_index(df)
    assert metrics["total_posts_analyzed"] >= 9
    assert metrics["weekend_posts_count"] >= 3
    assert metrics["weekday_posts_count"] >= 5
    assert metrics["weekend_volatility_multiplier"] == 1.42

def test_live_feed_parsing_and_bitemporal(tmp_path):
    temp_vintage_file = str(tmp_path / "executive_social_vintages_test.json")
    connector = ExecutiveSocialFeedConnector()
    
    test_post = {
        "date": "2026-09-13 14:00:00",
        "as_of": "2026-09-13 14:00:00",
        "platform": "Truth Social",
        "post_text": "We will lower oil and gasoline prices immediately!",
        "target": "Energy_Market",
        "sentiment_type": "Live_Executive_Commentary",
        "is_weekend": True,
        "actual_1d_crude_return_pct": 0.0,
        "actual_1d_rbob_return_pct": 0.0
    }
    
    connector.save_executive_social_vintage_record(test_post, filepath=temp_vintage_file)
    assert os.path.exists(temp_vintage_file)
    
    vintages = connector.get_executive_social_vintages_as_of("2026-09-14", filepath=temp_vintage_file)
    assert len(vintages) == 1
    assert vintages[0]["is_weekend"] is True
