"""
Federal Highway Administration (FHWA) Monthly Traffic Volume Trends (TVT) Module (src/fhwa_traffic_volume.py)
Re-exports FHWATrafficVolumeConnector, fetch_fhwa_traffic_features, and bitemporal vintage handlers (Issue #369).
"""

from src.bts_transportation import (
    FHWATrafficVolumeConnector,
    fetch_fhwa_traffic_features,
    save_fhwa_vintage_record,
    get_fhwa_vintages_as_of,
    HISTORICAL_FHWA_BASELINE,
    FHWA_VINTAGE_FILE,
    FHWA_PUBLICATION_LAG_DAYS
)

__all__ = [
    "FHWATrafficVolumeConnector",
    "fetch_fhwa_traffic_features",
    "save_fhwa_vintage_record",
    "get_fhwa_vintages_as_of",
    "HISTORICAL_FHWA_BASELINE",
    "FHWA_VINTAGE_FILE",
    "FHWA_PUBLICATION_LAG_DAYS"
]
