"""
SEC EDGAR Feed Compatibility Module (src/sec_edgar_feed.py)
Provides backwards-compatible interface for Issue #69 and Issue #129,
re-exporting the EDGAR 8-K Refinery Operator Monitor implementation.
"""

from src.edgar_8k_monitor import (
    EDGAR8KMonitor,
    DEFAULT_TICKERS,
    OPERATIONAL_KEYWORDS,
    EDGAR_CACHE_FILE,
    _strip_html,
)

__all__ = [
    "EDGAR8KMonitor",
    "DEFAULT_TICKERS",
    "OPERATIONAL_KEYWORDS",
    "EDGAR_CACHE_FILE",
    "_strip_html",
]
