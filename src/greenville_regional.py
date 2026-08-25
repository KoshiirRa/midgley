"""
Re-export Shim for Greenville Regional Module (src/greenville_regional.py)
Forwards to src.locations.greenville.regional for backward compatibility.
"""

from src.locations.greenville.regional import (
    fetch_greenville_market_data,
    get_greenville_regional_events,
    _generate_synthetic_greenville_data
)

__all__ = [
    "fetch_greenville_market_data",
    "get_greenville_regional_events",
    "_generate_synthetic_greenville_data"
]
