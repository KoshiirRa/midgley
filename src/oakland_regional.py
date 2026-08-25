"""
Re-export Shim for Oakland Regional Module (src/oakland_regional.py)
Forwards to src.locations.oakland.regional for backward compatibility.
"""

from src.locations.oakland.regional import (
    fetch_oakland_market_data,
    get_oakland_regional_events,
    _generate_synthetic_oakland_data,
    TOTAL_CARB_TAX_BURDEN
)

__all__ = [
    "fetch_oakland_market_data",
    "get_oakland_regional_events",
    "_generate_synthetic_oakland_data",
    "TOTAL_CARB_TAX_BURDEN"
]
