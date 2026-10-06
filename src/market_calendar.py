"""
NYMEX & CME Energy Market Trading Calendar (src/market_calendar.py)
Provides official exchange trading session schedules, holiday awareness,
and RBOB futures contract roll expiry detection (Issue #404, Finding A-5 & A-8).

Features:
- Precise CME Globex Energy / NYMEX trading day generation (skips weekends + holidays).
- Deterministic calculation of U.S. federal and exchange holidays (Good Friday, MLK, Presidents' Day, Memorial Day, Juneteenth, July 4th, Labor Day, Thanksgiving, Christmas, New Year's).
- Contract roll boundary identification: RBOB contracts expire on the last business day of the month preceding delivery.
- Flagging and adjustment for forecast horizons that straddle contract rolls.
"""

from datetime import datetime, date, timedelta
from typing import List, Union, Optional, Tuple, Set
import pandas as pd


def _calculate_easter(year: int) -> date:
    """Calculates Easter Sunday using the Anonymous Gregorian algorithm."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _observed_date(d: date) -> date:
    """Adjusts weekend fixed-date holidays to observed Friday/Monday."""
    if d.weekday() == 5:  # Saturday -> Friday
        return d - timedelta(days=1)
    if d.weekday() == 6:  # Sunday -> Monday
        return d + timedelta(days=1)
    return d


def get_nymex_holidays(year: int) -> Set[date]:
    """
    Returns official CME/NYMEX holiday closures for a given year.
    Ref: CME Rulebook Chapter 5, Globex Energy & Metals Schedule.
    """
    holidays: Set[date] = set()

    # 1. New Year's Day (Jan 1, observed)
    holidays.add(_observed_date(date(year, 1, 1)))

    # 2. Martin Luther King Jr. Day (3rd Monday in Jan)
    d = date(year, 1, 1)
    mlk_day = d + timedelta(days=(0 - d.weekday() + 7) % 7 + 14)
    holidays.add(mlk_day)

    # 3. Washington's Birthday / Presidents' Day (3rd Monday in Feb)
    d = date(year, 2, 1)
    pres_day = d + timedelta(days=(0 - d.weekday() + 7) % 7 + 14)
    holidays.add(pres_day)

    # 4. Good Friday (Friday before Easter)
    easter = _calculate_easter(year)
    good_friday = easter - timedelta(days=2)
    holidays.add(good_friday)

    # 5. Memorial Day (Last Monday in May)
    d = date(year, 5, 31)
    memorial_day = d - timedelta(days=(d.weekday() - 0) % 7)
    holidays.add(memorial_day)

    # 6. Juneteenth National Independence Day (June 19, observed)
    holidays.add(_observed_date(date(year, 6, 19)))

    # 7. Independence Day (July 4, observed)
    holidays.add(_observed_date(date(year, 7, 4)))

    # 8. Labor Day (1st Monday in Sept)
    d = date(year, 9, 1)
    labor_day = d + timedelta(days=(0 - d.weekday() + 7) % 7)
    holidays.add(labor_day)

    # 9. Thanksgiving Day (4th Thursday in Nov)
    d = date(year, 11, 1)
    thanksgiving = d + timedelta(days=(3 - d.weekday() + 7) % 7 + 21)
    holidays.add(thanksgiving)

    # 10. Christmas Day (Dec 25, observed)
    holidays.add(_observed_date(date(year, 12, 25)))

    return holidays


class NYMEXTradingCalendar:
    """
    Exchange calendar for NYMEX Energy Futures.
    Evaluates trading session days and rolls without external dependency.
    """

    def __init__(self):
        self._holiday_cache: dict = {}

    def get_holidays_for_year(self, year: int) -> Set[date]:
        if year not in self._holiday_cache:
            self._holiday_cache[year] = get_nymex_holidays(year)
        return self._holiday_cache[year]

    def is_trading_day(self, d: Union[date, datetime, str, pd.Timestamp]) -> bool:
        """Returns True if date is an active NYMEX trading day (non-weekend, non-holiday)."""
        if isinstance(d, str):
            dt = datetime.strptime(d[:10], "%Y-%m-%d").date()
        elif isinstance(d, datetime):
            dt = d.date()
        elif isinstance(d, pd.Timestamp):
            dt = d.date()
        else:
            dt = d

        # Monday=0 ... Sunday=6
        if dt.weekday() >= 5:
            return False

        holidays = self.get_holidays_for_year(dt.year)
        return dt not in holidays

    def get_next_trading_day(self, start_date: Union[date, datetime, str]) -> date:
        """Returns the first trading day strictly after start_date."""
        if isinstance(start_date, str):
            cur = datetime.strptime(start_date[:10], "%Y-%m-%d").date()
        elif isinstance(start_date, datetime):
            cur = start_date.date()
        else:
            cur = start_date

        cur += timedelta(days=1)
        while not self.is_trading_day(cur):
            cur += timedelta(days=1)
        return cur

    def get_trading_days_range(self, start_date: Union[date, datetime, str], n_days: int) -> List[date]:
        """
        Generates an array of n_days consecutive trading days starting strictly after start_date.
        Replaces naive pd.bdate_range.
        """
        if isinstance(start_date, str):
            cur = datetime.strptime(start_date[:10], "%Y-%m-%d").date()
        elif isinstance(start_date, datetime):
            cur = start_date.date()
        else:
            cur = start_date

        trading_days: List[date] = []
        while len(trading_days) < n_days:
            cur += timedelta(days=1)
            if self.is_trading_day(cur):
                trading_days.append(cur)
        return trading_days

    def get_target_date_for_horizon(self, origin_date: Union[date, datetime, str], horizon: int) -> str:
        """Returns the target date string (YYYY-MM-DD) h trading days after origin_date."""
        days = self.get_trading_days_range(origin_date, horizon)
        return days[-1].strftime("%Y-%m-%d")

    def get_rbob_contract_expiry(self, delivery_year: int, delivery_month: int) -> date:
        """
        RBOB (RB) futures contract expiration date:
        Trading terminates on the last business day of the month preceding the delivery month.
        (e.g., Nov delivery expires on last business day of Oct).
        """
        # First day of delivery month minus one day = last day of preceding month
        first_of_deliv = date(delivery_year, delivery_month, 1)
        last_day_prev = first_of_deliv - timedelta(days=1)
        cur = last_day_prev
        while not self.is_trading_day(cur):
            cur -= timedelta(days=1)
        return cur

    def is_roll_straddling(
        self,
        start_date: Union[date, datetime, str],
        end_date: Union[date, datetime, str]
    ) -> Tuple[bool, Optional[date]]:
        """
        Checks whether any monthly contract expiration falls strictly inside (start_date, end_date].
        Returns (is_straddling, expiry_date).
        """
        if isinstance(start_date, str):
            d_start = datetime.strptime(start_date[:10], "%Y-%m-%d").date()
        elif isinstance(start_date, datetime):
            d_start = start_date.date()
        else:
            d_start = start_date

        if isinstance(end_date, str):
            d_end = datetime.strptime(end_date[:10], "%Y-%m-%d").date()
        elif isinstance(end_date, datetime):
            d_end = end_date.date()
        else:
            d_end = end_date

        # Check delivery months covering start to end + 2 months
        for month_offset in range(0, 3):
            # approximate month
            test_dt = d_start + timedelta(days=32 * month_offset)
            expiry = self.get_rbob_contract_expiry(test_dt.year, test_dt.month)
            if d_start < expiry <= d_end:
                return True, expiry

        return False, None


_GLOBAL_CALENDAR: Optional[NYMEXTradingCalendar] = None


def get_trading_calendar() -> NYMEXTradingCalendar:
    """Returns singleton NYMEXTradingCalendar instance."""
    global _GLOBAL_CALENDAR
    if _GLOBAL_CALENDAR is None:
        _GLOBAL_CALENDAR = NYMEXTradingCalendar()
    return _GLOBAL_CALENDAR
