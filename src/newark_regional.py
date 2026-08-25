"""
Re-export Shim for Newark Regional Module (src/newark_regional.py)
Forwards to src.locations.newark.regional for backward compatibility.
"""

from src.locations.newark.regional import (
    fetch_newark_market_data,
    get_newark_regional_events,
    _generate_synthetic_newark_data
)

__all__ = [
    "fetch_newark_market_data",
    "get_newark_regional_events",
    "_generate_synthetic_newark_data"
]
