"""
Release Reconciliation Manifest Engine (src/release_manifest.py)
Generates machine-readable release manifests and migration contracts (Issue #299).
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

# Ensure repository root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.version import get_version, get_model_engine_version

logger = logging.getLogger(__name__)

MANIFEST_SCHEMA_VERSION = 3
MANIFEST_FILE_PATH = "RELEASE_MANIFEST.json"


def generate_release_manifest() -> Dict[str, Any]:
    """
    Compiles structured release reconciliation manifest metadata for self-hosters and AI agents.
    """
    pkg_ver = get_version()
    model_ver = get_model_engine_version()

    manifest = {
        "version": pkg_ver,
        "model_version": model_ver,
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "release_date": datetime.now().strftime("%Y-%m-%d"),
        "compatibility": {
            "minimum_compatible_client": "0.5.0",
            "breaking_changes": False,
            "requires_regional_retraining": False
        },
        "environment_changes": {
            "added": [
                {
                    "name": "USGS_WATER_FEED_ENABLED",
                    "default": "true",
                    "required": False,
                    "description": "Enables inland waterway gauge tracking for river navigation constraints."
                },
                {
                    "name": "HINDSIGHT_API_URL",
                    "default": "",
                    "required": False,
                    "description": "Remote Vectorize Hindsight / Supabase pgvector episodic memory endpoint."
                }
            ],
            "deprecated": []
        },
        "model_engine": {
            "feature_matrix_columns": [
                "rbob_return_1d",
                "wti_return_1d",
                "event_shock_decayed",
                "noaa_spc_risk",
                "ovx_implied_vol",
                "usgs_gauge_stage",
                "weekend_gap_shock"
            ],
            "added_features": ["usgs_gauge_stage", "weekend_gap_shock"],
            "retrain_action": "retrain_regional_models",
            "retrain_command": "python scripts/manage_regions.py retrain --all"
        },
        "database_migrations": [
            {
                "id": "20260917_add_gauge_stations",
                "description": "Adds inland river gauge telemetry table",
                "automatic": True
            },
            {
                "id": "20260918_add_reachability_telemetry",
                "description": "Adds multi-protocol reachability tracking columns",
                "automatic": True
            }
        ],
        "agent_action_items": [
            "Verify optional environment variables are documented or defaulted.",
            "Inspect regional calibration model weights: run `python scripts/manage_regions.py check`.",
            "Execute `pytest tests/` to confirm all regression tests pass."
        ]
    }
    return manifest


def save_release_manifest(filepath: str = MANIFEST_FILE_PATH) -> str:
    """Compiles and writes RELEASE_MANIFEST.json to disk."""
    manifest = generate_release_manifest()
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        logger.info(f"Generated release manifest at {filepath}")
    except Exception as e:
        logger.error(f"Failed to write release manifest to {filepath}: {e}")
    return filepath


if __name__ == "__main__":
    out_path = save_release_manifest()
    print(f"Release manifest saved to {out_path}")
