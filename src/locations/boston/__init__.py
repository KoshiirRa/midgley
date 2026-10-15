"""
Boston Metro & New England Regional Location Package (src/locations/boston)
"""

from src.locations.boston.regional import (
    fetch_boston_market_data,
    get_boston_regional_events,
    _generate_synthetic_boston_data
)
from src.locations.boston.main import run_boston_pipeline
from src.locations.boston.notebook_builder import build_boston_notebook

__all__ = [
    "fetch_boston_market_data",
    "get_boston_regional_events",
    "_generate_synthetic_boston_data",
    "run_boston_pipeline",
    "build_boston_notebook"
]
