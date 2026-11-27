"""Modular dashboard template and component package (Issue #562)."""

from src.dashboard.badges import (
    get_analytics_script,
    get_carto_basemap_url,
    get_model_badge,
    get_multi_agent_sim_badge,
    get_release_badge,
)

__all__ = [
    "get_analytics_script",
    "get_carto_basemap_url",
    "get_model_badge",
    "get_multi_agent_sim_badge",
    "get_release_badge",
]
