"""
Re-export Shim for Cincinnati Regional Module (src/cincinnati_regional.py)
Forwards to src.locations.cincinnati.regional for backward compatibility.
"""

from src.locations.cincinnati.regional import (
    fetch_cincinnati_market_data,
    get_cincinnati_regional_events,
    _generate_synthetic_cincinnati_data
)

__all__ = [
    "fetch_cincinnati_market_data",
    "get_cincinnati_regional_events",
    "_generate_synthetic_cincinnati_data"
]
