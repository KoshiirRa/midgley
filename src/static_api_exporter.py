"""
Static API Feeds Exporter (src/static_api_exporter.py)
Exports static JSON payloads for all supported metro hubs into docs/api/v1/
so mobile and web clients can query https://koshiirra.github.io/midgley/api/v1/
directly with 100% uptime and $0 infrastructure overhead.
"""

import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

SUPPORTED_LOCALES = [
    "national",
    "tulsa",
    "oakland",
    "newark",
    "cincinnati",
    "greenville",
    "charlotte",
    "port_st_lucie",
    "bayarea"
]


def export_all_static_api_endpoints(docs_dir: str = "docs") -> dict:
    """
    Generates and saves static JSON API payloads into docs/api/v1/
    """
    from src.api_server import _get_combined_impl, list_supported_locales

    api_dir = os.path.join(docs_dir, "api", "v1")
    combined_dir = os.path.join(api_dir, "combined")
    os.makedirs(api_dir, exist_ok=True)
    os.makedirs(combined_dir, exist_ok=True)

    all_combined_map = {}

    for loc in SUPPORTED_LOCALES:
        try:
            payload = _get_combined_impl(locale=loc)
            all_combined_map[loc] = payload

            # 1. Save flat: docs/api/v1/combined_<loc>.json
            flat_path = os.path.join(api_dir, f"combined_{loc}.json")
            with open(flat_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)

            # 2. Save flat short: docs/api/v1/<loc>.json
            short_path = os.path.join(api_dir, f"{loc}.json")
            with open(short_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)

            # 3. Save nested: docs/api/v1/combined/<loc>.json
            nested_path = os.path.join(combined_dir, f"{loc}.json")
            with open(nested_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)

            logger.info("Exported static API endpoint for locale: %s", loc)
        except Exception as e:
            logger.error("Failed to export static API payload for locale %s: %s", loc, e)

    # Export master combined index: docs/api/v1/combined.json
    master_combined = {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "locales": all_combined_map
    }
    with open(os.path.join(api_dir, "combined.json"), "w", encoding="utf-8") as f:
        json.dump(master_combined, f, indent=2)

    # Export locales metadata: docs/api/v1/locales.json
    try:
        locales_payload = list_supported_locales()
        with open(os.path.join(api_dir, "locales.json"), "w", encoding="utf-8") as f:
            json.dump(locales_payload, f, indent=2)
    except Exception as e:
        logger.error("Failed to export static locales.json: %s", e)

    return {
        "status": "success",
        "exported_locales_count": len(all_combined_map),
        "api_dir": api_dir
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    res = export_all_static_api_endpoints()
    print("Export result:", res)
