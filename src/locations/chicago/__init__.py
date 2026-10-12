"""
Chicago Metro, IL & Northwest Indiana Regional Location Package (src/locations/chicago)
"""

from src.locations.chicago.regional import (
    fetch_chicago_market_data,
    get_chicago_regional_events,
    compute_chicago_edgeworth_forecast,
    _generate_synthetic_chicago_data
)
from src.locations.chicago.main import run_chicago_pipeline
from src.locations.chicago.notebook_builder import build_chicago_notebook

__all__ = [
    "fetch_chicago_market_data",
    "get_chicago_regional_events",
    "compute_chicago_edgeworth_forecast",
    "_generate_synthetic_chicago_data",
    "run_chicago_pipeline",
    "build_chicago_notebook"
]
