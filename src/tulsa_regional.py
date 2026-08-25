"""
Re-export Shim for Tulsa Regional Module (src/tulsa_regional.py)
Forwards to src.locations.tulsa.regional for backward compatibility.
"""

from src.locations.tulsa.regional import (
    fetch_tulsa_market_data,
    get_tulsa_regional_events,
    _generate_synthetic_tulsa_data
)

__all__ = [
    "fetch_tulsa_market_data",
    "get_tulsa_regional_events",
    "_generate_synthetic_tulsa_data"
]
