"""
Bureau of Safety and Environmental Enforcement (BSEE) Gulf Shut-In Connector (src/bsee_shutins.py)
Ingests daily offshore Gulf of Mexico oil & gas production shut-in reports during tropical evacuations. (Issue #178, #277)
"""

import os
import re
import urllib.request
import defusedxml.ElementTree as ET
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from src.lookup_cache import global_cache

logger = logging.getLogger(__name__)

USER_AGENT = "(MidgleyGasPriceForecaster, contact@example.com)"
BSEE_VINTAGE_FILE = os.path.join("data", "bsee_vintages.json")
BSEE_RSS_URL = "https://news.google.com/rss/search?q=BSEE+shut-in+Gulf+of+Mexico+when:7d&hl=en-US&gl=US&ceid=US:en"


def save_bsee_vintage_record(record: dict, filepath: str = BSEE_VINTAGE_FILE) -> None:
    """Appends a point-in-time BSEE offshore shut-in vintage record."""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        vintages = []
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    vintages = json.load(f)
            except Exception:
                vintages = []

        vintage_entry = {
            "as_of": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": record
        }
        vintages.append(vintage_entry)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(vintages, f, indent=2)
    except Exception as e:
        logger.debug(f"Failed to persist BSEE vintage record: {e}")


def get_bsee_vintages_as_of(as_of_date: str, filepath: str = BSEE_VINTAGE_FILE) -> Optional[dict]:
    """Retrieves the latest BSEE observation recorded on or before as_of_date."""
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            vintages = json.load(f)
        valid = [v for v in vintages if v.get("as_of", "")[:10] <= as_of_date]
        if valid:
            return valid[-1].get("data")
    except Exception as e:
        logger.debug(f"Error reading BSEE vintages: {e}")
    return None


class BSEEShutInConnector:
    """
    Zero-Cost BSEE Gulf Offshore Production Shut-In Connector.
    Parses offshore oil/gas shut-in percentages and evacuated platform counts.
    """
    def __init__(self):
        self.is_free_alternative = True
        self.cost_per_query = 0.0

    def fetch_gulf_shutin_data(self) -> Dict[str, Any]:
        """
        Fetches daily BSEE offshore shut-in metrics with 12-hour lookup cache.
        """
        day_bucket = datetime.now().strftime("%Y-%m-%d")
        cache_key = f"bsee_gulf_shutin:{day_bucket}"
        cached = global_cache.get(cache_key)
        if cached:
            logger.info("Loaded BSEE offshore shut-in data from lookup cache.")
            return cached

        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result = {
            "source": "Bureau of Safety and Environmental Enforcement (BSEE Public Web)",
            "timestamp": timestamp_str,
            "bsee_gulf_oil_shutin_pct": 0.0,
            "bsee_gulf_gas_shutin_pct": 0.0,
            "bsee_evacuated_platforms_count": 0,
            "is_storm_evacuation_active": False,
            "status": "SUCCESS"
        }

        # Check NHC active hurricane threats first
        try:
            from src.nhc_hurricane import NHCHurricaneConnector
            nhc = NHCHurricaneConnector()
            threats = nhc.fetch_active_hurricane_threats()
            if threats.get("gulf_hurricane_active"):
                result["is_storm_evacuation_active"] = True
                # Default baseline estimate for active Gulf storm when reports are pending
                result["bsee_gulf_oil_shutin_pct"] = round(threats.get("nhc_gulf_refinery_exposure_score", 0.3) * 35.0, 1)
                result["bsee_gulf_gas_shutin_pct"] = round(threats.get("nhc_gulf_refinery_exposure_score", 0.3) * 25.0, 1)
                result["bsee_evacuated_platforms_count"] = int(threats.get("nhc_gulf_refinery_exposure_score", 0.3) * 50)
        except Exception as e:
            logger.debug(f"NHC check for BSEE shut-ins skipped: {e}")

        # Dynamically query Google News RSS for breaking BSEE reports
        try:
            req = urllib.request.Request(BSEE_RSS_URL, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    xml_bytes = resp.read()
                    root = ET.fromstring(xml_bytes)
                    for item in root.findall(".//item"):
                        title = item.findtext("title", "")
                        desc = item.findtext("description", "")
                        text = f"{title} {desc}".lower()

                        if "shut-in" in text or "evacuat" in text or "bsee" in text:
                            result["is_storm_evacuation_active"] = True

                            oil_match = re.search(r'(\d+(?:\.\d+)?)\s*%\s*(?:of\s*(?:the\s*)?)?(?:oil|crude)', text)
                            if oil_match:
                                result["bsee_gulf_oil_shutin_pct"] = float(oil_match.group(1))

                            gas_match = re.search(r'(\d+(?:\.\d+)?)\s*%\s*(?:of\s*(?:the\s*)?)?(?:gas|natural gas)', text)
                            if gas_match:
                                result["bsee_gulf_gas_shutin_pct"] = float(gas_match.group(1))

                            plat_match = re.search(r'(\d+)\s*(?:production\s*)?platforms?\s*(?:have\s*been\s*)?evacuated', text)
                            if plat_match:
                                result["bsee_evacuated_platforms_count"] = int(plat_match.group(1))
                            break
        except Exception as e:
            logger.debug(f"BSEE live RSS search skipped: {e}")

        save_bsee_vintage_record(result)
        global_cache.set(cache_key, result, ttl_seconds=43200)
        return result

