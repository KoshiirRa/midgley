"""
NOAA National Hurricane Center (NHC) Advisory Connector (src/nhc_hurricane.py)
Ingests active Atlantic/Gulf tropical cyclone advisories, hurricane track threats,
and calculates physical supply risk scores for Gulf Coast refining hubs (PADD 3)
and Colonial Pipeline Line 1/2 intake terminals. (Issue #177)
"""

import urllib.request
import xml.etree.ElementTree as ET
import json
import logging
from typing import Dict, Any, List
from datetime import datetime
from src.lookup_cache import global_cache

logger = logging.getLogger(__name__)

NHC_RSS_URL = "https://www.nhc.noaa.gov/index-at.xml"
USER_AGENT = "(MidgleyGasPriceForecaster, contact@example.com)"

class NHCHurricaneConnector:
    """
    Zero-Cost NOAA NHC Tropical Cyclone Advisory Connector.
    Parses active Atlantic & Gulf tropical storm/hurricane advisories and projects refinery threat scores.
    """
    def __init__(self):
        self.is_free_alternative = True
        self.cost_per_query = 0.0

    def fetch_active_hurricane_threats(self) -> Dict[str, Any]:
        """
        Fetches active NHC advisories with 3-hour lookup cache.
        Returns risk scores and active storm counts.
        """
        hour_bucket = datetime.now().strftime("%Y-%m-%d-%H")
        cache_key = f"nhc_hurricane_threats:{hour_bucket}"
        cached = global_cache.get(cache_key)
        if cached:
            logger.info("Loaded NHC hurricane advisory data from lookup cache.")
            return cached

        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result = {
            "source": "NOAA National Hurricane Center (Zero-Cost Public Feed)",
            "timestamp": timestamp_str,
            "active_storms_count": 0,
            "gulf_hurricane_active": False,
            "nhc_hurricane_threat_index": 0.0,
            "nhc_gulf_refinery_exposure_score": 0.0,
            "nhc_colonial_pipeline_risk_score": 0.0,
            "active_advisories": [],
            "status": "SUCCESS"
        }

        try:
            req = urllib.request.Request(NHC_RSS_URL, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=5) as response:
                    xml_bytes = response.read()
                    items = []
                    try:
                        root = ET.fromstring(xml_bytes)
                        for item in root.findall(".//item"):
                            items.append((item.findtext("title", ""), item.findtext("description", "")))
                    except Exception:
                        import re
                        raw_text = xml_bytes.decode('utf-8', errors='ignore')
                        item_blocks = re.findall(r'<item>(.*?)</item>', raw_text, re.DOTALL)
                        for block in item_blocks:
                            t_match = re.search(r'<title>(.*?)</title>', block, re.DOTALL)
                            d_match = re.search(r'<description>(.*?)</description>', block, re.DOTALL)
                            title_val = t_match.group(1).strip() if t_match else ""
                            desc_val = d_match.group(1).strip() if d_match else ""
                            items.append((title_val, desc_val))

                    advisories = []
                    threat_score = 0.0
                    gulf_active = False

                    for title, description in items:
                        title_lower = title.lower()
                        if any(kw in title_lower for kw in ["tropical storm", "hurricane", "tropical depression"]):
                            advisories.append({"title": title, "description": description[:200]})

                            # Score threat levels
                            if "hurricane" in title_lower:
                                threat_score += 0.40
                            elif "tropical storm" in title_lower:
                                threat_score += 0.20

                            # Check for Gulf of Mexico or Caribbean location mentions
                            desc_lower = description.lower()
                            if any(loc in desc_lower or loc in title_lower for loc in ["gulf of mexico", "gulf coast", "louisiana", "texas", "florida"]):
                                gulf_active = True
                                threat_score += 0.30

                    threat_score = min(threat_score, 1.0)
                    result["active_storms_count"] = len(advisories)
                    result["gulf_hurricane_active"] = gulf_active
                    result["nhc_hurricane_threat_index"] = round(threat_score, 4)
                    result["nhc_gulf_refinery_exposure_score"] = round(threat_score * (1.5 if gulf_active else 1.0), 4)
                    result["nhc_colonial_pipeline_risk_score"] = round(threat_score * (1.2 if gulf_active else 0.8), 4)
                    result["active_advisories"] = advisories
        except Exception as e:
            logger.warning(f"Could not fetch live NHC hurricane advisories: {e}")
            result["status"] = f"PARTIAL_FALLBACK: {e}"

        global_cache.set(cache_key, result, ttl_seconds=10800)
        return result
