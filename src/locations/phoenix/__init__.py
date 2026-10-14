"""
Phoenix Metro & Desert Southwest Regional Location Package (src/locations/phoenix)
"""

from src.locations.phoenix.regional import (
    fetch_phoenix_market_data,
    get_phoenix_regional_events,
    _generate_synthetic_phoenix_data
)
from src.locations.phoenix.main import run_phoenix_pipeline
from src.locations.phoenix.notebook_builder import build_phoenix_notebook

__all__ = [
    "fetch_phoenix_market_data",
    "get_phoenix_regional_events",
    "_generate_synthetic_phoenix_data",
    "run_phoenix_pipeline",
    "build_phoenix_notebook"
]
