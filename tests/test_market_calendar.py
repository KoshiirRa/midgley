"""
Unit Test Suite for NYMEX & CME Energy Trading Calendar (tests/test_market_calendar.py)
Tests NYMEXTradingCalendar, holiday detection, contract roll boundaries, and target date calculation.
"""

from datetime import date
from src.market_calendar import get_trading_calendar, get_nymex_holidays


def test_nymex_holiday_presence():
    cal = get_trading_calendar()
    # 2026 holidays
    holidays_2026 = cal.get_holidays_for_year(2026)
    
    # New Year's Day 2026 (Thursday Jan 1)
    assert date(2026, 1, 1) in holidays_2026
    # Memorial Day 2026 (Monday May 25)
    assert date(2026, 5, 25) in holidays_2026
    # Independence Day 2026 (July 4 is Saturday -> Friday July 3 observed)
    assert date(2026, 7, 3) in holidays_2026
    # Labor Day 2026 (Monday Sept 7)
    assert date(2026, 9, 7) in holidays_2026
    # Thanksgiving 2026 (Thursday Nov 26)
    assert date(2026, 11, 26) in holidays_2026
    # Christmas 2026 (Friday Dec 25)
    assert date(2026, 12, 25) in holidays_2026


def test_is_trading_day_weekend_and_holiday():
    cal = get_trading_calendar()
    # Saturday Oct 3, 2026
    assert not cal.is_trading_day(date(2026, 10, 3))
    # Sunday Oct 4, 2026
    assert not cal.is_trading_day(date(2026, 10, 4))
    # Monday Oct 5, 2026 (regular trading day)
    assert cal.is_trading_day(date(2026, 10, 5))
    # Thanksgiving 2026
    assert not cal.is_trading_day(date(2026, 11, 26))


def test_trading_days_range_skips_weekends_and_holidays():
    cal = get_trading_calendar()
    # Starting Friday Oct 2, 2026 -> 3 trading days should be Mon Oct 5, Tue Oct 6, Wed Oct 7
    days = cal.get_trading_days_range(date(2026, 10, 2), 3)
    assert len(days) == 3
    assert days[0] == date(2026, 10, 5)
    assert days[1] == date(2026, 10, 6)
    assert days[2] == date(2026, 10, 7)


def test_rbob_contract_expiry_calculation():
    cal = get_trading_calendar()
    # Nov 2026 contract (RBX26) expires on the last trading day of Oct 2026
    # Oct 31, 2026 is Saturday -> Friday Oct 30, 2026
    expiry_nov26 = cal.get_rbob_contract_expiry(2026, 11)
    assert expiry_nov26 == date(2026, 10, 30)
    assert cal.is_trading_day(expiry_nov26)

    # Dec 2026 contract (RBZ26) expires on the last trading day of Nov 2026
    # Nov 30, 2026 is Monday
    expiry_dec26 = cal.get_rbob_contract_expiry(2026, 12)
    assert expiry_dec26 == date(2026, 11, 30)


def test_roll_straddling_detection():
    cal = get_trading_calendar()
    # Window from Oct 28, 2026 to Nov 2, 2026 straddles Oct 30 expiry
    straddles, exp = cal.is_roll_straddling("2026-10-28", "2026-11-02")
    assert straddles is True
    assert exp == date(2026, 10, 30)

    # Window from Oct 5 to Oct 9 does NOT straddle roll
    straddles_clean, _ = cal.is_roll_straddling("2026-10-05", "2026-10-09")
    assert straddles_clean is False
