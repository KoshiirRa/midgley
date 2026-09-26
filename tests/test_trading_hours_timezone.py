"""
Tests for timezone-aware is_trading_hours evaluation across Finlight, AlphaVantage, and OilPriceAPI (Issue #328).
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import pytest

from src.finlight_feed import is_trading_hours as finlight_is_trading_hours
from src.data_ingestion import AlphaVantageDataConnector, OilPriceAPIDataConnector


class TestTradingHoursTimezoneAwareness:
    """Test suite ensuring trading hours evaluation respects US Eastern Time across UTC and naive timestamps."""

    @pytest.fixture
    def connectors(self):
        return [
            ("Finlight", lambda dt: finlight_is_trading_hours(dt)),
            ("AlphaVantage", lambda dt: AlphaVantageDataConnector().is_trading_hours(dt)),
            ("OilPriceAPI", lambda dt: OilPriceAPIDataConnector().is_trading_hours(dt)),
        ]

    def test_utc_active_trading_hours(self, connectors):
        """14:00 UTC during summer/winter is 10:00/09:00 ET -> Active trading."""
        # A Wednesday at 14:00 UTC (10:00 AM EDT)
        dt_utc = datetime(2026, 9, 23, 14, 0, tzinfo=timezone.utc)
        for name, fn in connectors:
            assert fn(dt_utc) is True, f"{name} should evaluate 14:00 UTC as active trading hours"

    def test_utc_pre_market_hours(self, connectors):
        """10:00 UTC is 06:00 AM EDT -> Pre-market off-hours."""
        # A Wednesday at 10:00 UTC (06:00 AM EDT)
        dt_utc = datetime(2026, 9, 23, 10, 0, tzinfo=timezone.utc)
        for name, fn in connectors:
            assert fn(dt_utc) is False, f"{name} should evaluate 10:00 UTC as off-hours (06:00 AM EDT)"

    def test_utc_post_market_hours(self, connectors):
        """22:00 UTC is 18:00 (06:00 PM) EDT -> Post-market off-hours."""
        # A Wednesday at 22:00 UTC (06:00 PM EDT)
        dt_utc = datetime(2026, 9, 23, 22, 0, tzinfo=timezone.utc)
        for name, fn in connectors:
            assert fn(dt_utc) is False, f"{name} should evaluate 22:00 UTC as off-hours (06:00 PM EDT)"

    def test_weekend_trading_hours(self, connectors):
        """Saturday and Sunday should always be off-hours regardless of time."""
        # Saturday at 14:00 UTC
        sat_utc = datetime(2026, 9, 26, 14, 0, tzinfo=timezone.utc)
        # Sunday at 14:00 UTC
        sun_utc = datetime(2026, 9, 27, 14, 0, tzinfo=timezone.utc)
        for name, fn in connectors:
            assert fn(sat_utc) is False, f"{name} should return False on Saturday"
            assert fn(sun_utc) is False, f"{name} should return False on Sunday"

    def test_naive_datetime_handling(self, connectors):
        """Naive datetimes should be localized to US Eastern time."""
        # Naive Wednesday 10:30 AM (intended as ET)
        dt_naive_active = datetime(2026, 9, 23, 10, 30)
        # Naive Wednesday 05:00 AM (intended as ET)
        dt_naive_off = datetime(2026, 9, 23, 5, 0)
        for name, fn in connectors:
            assert fn(dt_naive_active) is True, f"{name} should evaluate naive 10:30 AM as active"
            assert fn(dt_naive_off) is False, f"{name} should evaluate naive 05:00 AM as off-hours"

    def test_default_now_evaluation(self, connectors):
        """Calling without arguments evaluates live time without raising exceptions."""
        for name, fn in connectors:
            res = fn(None)
            assert isinstance(res, bool), f"{name} default evaluation must return a boolean"
