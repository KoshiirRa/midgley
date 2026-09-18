"""
Geopolitical & Maritime Chokepoint Data Module (src/geopolitical_feeds.py)
Monitors Middle East / Iran conflict alerts, Strait of Hormuz & Suez Canal maritime transit disruptions,
and Venezuela heavy crude production & OFAC sanctions dynamics. (Issue #178, #278)
"""

import os
import re
import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging
from src.lookup_cache import global_cache

logger = logging.getLogger(__name__)

USER_AGENT = "(MidgleyGasPriceForecaster, contact@example.com)"
GEOPOLITICAL_VINTAGE_FILE = os.path.join("data", "geopolitical_vintages.json")

# Key Chokepoint Definitions & Risk Weighting
CHOKEPOINTS = {
    "Strait_of_Hormuz": {
        "daily_volume_mbpd": 21.0,
        "share_global_petroleum": 0.20,
        "primary_risk": "Iran conflict, naval mines, tanker seizures, IRGC harassment"
    },
    "Suez_Bab_el_Mandeb": {
        "daily_volume_mbpd": 8.8,
        "share_global_petroleum": 0.09,
        "primary_risk": "Red Sea Houthi missile/drone attacks, Cape of Good Hope rerouting (+12 days)"
    },
    "Venezuela_Orinoco": {
        "daily_volume_mbpd": 0.85,
        "share_global_petroleum": 0.01,
        "primary_risk": "OFAC General License 44 sanctions status, PDVSA heavy crude diluent supply"
    }
}

HISTORICAL_GEOPOLITICAL_EVENTS = [
    # --- STRAIT OF HORMUZ & IRAN CONFLICT ---
    {
        "date": "2023-04-27",
        "headline": "Iran IRGC Navy seizes Marshall Islands-flagged oil tanker Advantage Sweet in Strait of Hormuz.",
        "category": "Iran_Hormuz",
        "chokepoint": "Strait_of_Hormuz"
    },
    {
        "date": "2023-05-03",
        "headline": "Iran seizes Panama-flagged oil tanker Niovi transiting Strait of Hormuz near Fujairah.",
        "category": "Iran_Hormuz",
        "chokepoint": "Strait_of_Hormuz"
    },
    {
        "date": "2024-01-11",
        "headline": "Iran seizes oil tanker St Nikolas off coast of Oman in Gulf of Oman; crude futures surge +3%.",
        "category": "Iran_Hormuz",
        "chokepoint": "Strait_of_Hormuz"
    },
    {
        "date": "2024-04-13",
        "headline": "Iran IRGC forces board and seize Portuguese-flagged container vessel MSC Aries near Strait of Hormuz.",
        "category": "Iran_Hormuz",
        "chokepoint": "Strait_of_Hormuz"
    },
    {
        "date": "2024-10-01",
        "headline": "Iran launches major ballistic missile strike against Israel; energy markets price in Strait of Hormuz risk premium.",
        "category": "Iran_Hormuz",
        "chokepoint": "Strait_of_Hormuz"
    },

    # --- SUEZ CANAL & RED SEA / BAB-EL-MANDEB ---
    {
        "date": "2023-11-19",
        "headline": "Houthi militants hijack Galaxy Leader cargo vessel in Red Sea near Bab-el-Mandeb strait.",
        "category": "Suez_RedSea",
        "chokepoint": "Suez_Bab_el_Mandeb"
    },
    {
        "date": "2023-12-15",
        "headline": "Major international tanker operators Maersk, BP, and Frontline suspend Red Sea & Suez transit due to drone attacks.",
        "category": "Suez_RedSea",
        "chokepoint": "Suez_Bab_el_Mandeb"
    },
    {
        "date": "2024-01-12",
        "headline": "US and UK launch Operation Prosperity Guardian airstrikes on Houthi targets; Suez oil tanker traffic drops 45%.",
        "category": "Suez_RedSea",
        "chokepoint": "Suez_Bab_el_Mandeb"
    },
    {
        "date": "2024-03-06",
        "headline": "Houthi missile strike damages bulk carrier True Confidence in Gulf of Aden, killing 3 crew members; shipping insurance rates spike.",
        "category": "Suez_RedSea",
        "chokepoint": "Suez_Bab_el_Mandeb"
    },

    # --- VENEZUELA HEAVY CRUDE & OFAC SANCTIONS ---
    {
        "date": "2023-10-18",
        "headline": "US Treasury OFAC issues General License 44, temporarily lifting sanctions on Venezuela oil & gas exports.",
        "category": "Venezuela",
        "chokepoint": "Venezuela_Orinoco"
    },
    {
        "date": "2024-01-30",
        "headline": "US threatens to reinstate Venezuela oil sanctions as electoral reform commitments stall in Caracas.",
        "category": "Venezuela",
        "chokepoint": "Venezuela_Orinoco"
    },
    {
        "date": "2024-04-17",
        "headline": "US lets Venezuela oil sanction relief General License 44 expire; PDVSA heavy crude exports restricted.",
        "category": "Venezuela",
        "chokepoint": "Venezuela_Orinoco"
    },
    {
        "date": "2024-07-29",
        "headline": "Venezuelan presidential election dispute sparks political instability; US considers individual sanctions on PDVSA officials.",
        "category": "Venezuela",
        "chokepoint": "Venezuela_Orinoco"
    }
]


def save_geopolitical_vintage_record(records: list, filepath: str = GEOPOLITICAL_VINTAGE_FILE) -> None:
    """Appends a point-in-time geopolitical event observation vintage record."""
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
            "events_count": len(records),
            "events": records
        }
        vintages.append(vintage_entry)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(vintages, f, indent=2)
    except Exception as e:
        logger.debug(f"Failed to persist geopolitical vintage record: {e}")


def get_geopolitical_vintages_as_of(as_of_date: str, filepath: str = GEOPOLITICAL_VINTAGE_FILE) -> Optional[List[dict]]:
    """Retrieves geopolitical events recorded on or before as_of_date."""
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            vintages = json.load(f)
        valid = [v for v in vintages if v.get("as_of", "")[:10] <= as_of_date]
        if valid:
            return valid[-1].get("events", [])
    except Exception as e:
        logger.debug(f"Error reading geopolitical vintages: {e}")
    return None


class GeopoliticalFeedConnector:
    """
    Zero-Cost Dynamic Geopolitical & Maritime Chokepoints Feed Connector.
    Polls public RSS streams for Strait of Hormuz, Red Sea / Suez Canal, and Venezuela energy events.
    """
    def __init__(self):
        self.is_free_alternative = True
        self.cost_per_query = 0.0

    def fetch_geopolitical_headlines(self) -> List[Dict[str, Any]]:
        """
        Fetches live breaking maritime and geopolitical headlines with 15-minute lookup caching.
        """
        minute_bucket = datetime.now().strftime("%Y-%m-%d-%H")
        cache_key = f"geopolitical_headlines:{minute_bucket}"
        cached = global_cache.get(cache_key)
        if cached and isinstance(cached, dict) and "headlines" in cached:
            return cached["headlines"]

        queries = [
            ("Strait_of_Hormuz", "Iran+tanker+OR+Strait+of+Hormuz+when:2d"),
            ("Suez_Bab_el_Mandeb", "Red+Sea+tanker+OR+Houthi+Suez+when:2d"),
            ("Venezuela_Orinoco", "Venezuela+oil+sanction+OR+PDVSA+when:2d")
        ]

        live_events = []
        for chokepoint, q in queries:
            url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    if resp.status == 200:
                        root = ET.fromstring(resp.read())
                        for item in root.findall(".//item")[:5]:
                            title = item.findtext("title", "")
                            pub_date = item.findtext("pubDate", "")
                            link = item.findtext("link", "")
                            
                            # Clean title attribution
                            clean_title = re.sub(r"\s*-\s*[^-]+$", "", title).strip()
                            dt_str = datetime.now().strftime("%Y-%m-%d")
                            if pub_date:
                                try:
                                    dt_str = pd.to_datetime(pub_date).strftime("%Y-%m-%d")
                                except Exception:
                                    pass

                            live_events.append({
                                "date": dt_str,
                                "headline": clean_title,
                                "category": f"Geopolitical_{chokepoint}",
                                "chokepoint": chokepoint,
                                "url": link
                            })
            except Exception as e:
                logger.debug(f"Geopolitical query failed for {chokepoint}: {e}")

        # If live events are empty, trigger Reachability Cascade fallback (Issue #308)
        if not live_events:
            try:
                from src.reachability_adapters import ReachabilityCascadeRouter
                router = ReachabilityCascadeRouter()
                for chokepoint, q in queries:
                    resilient_items = router.fetch_resilient_posts(q.replace("+", " "), target_feed=f"geopolitical_{chokepoint.lower()}", limit=3)
                    for item in resilient_items:
                        live_events.append({
                            "date": datetime.now().strftime("%Y-%m-%d"),
                            "headline": item["text"],
                            "category": f"Geopolitical_{chokepoint}",
                            "chokepoint": chokepoint,
                            "url": item.get("url", "")
                        })
            except Exception as e:
                logger.debug(f"Geopolitical reachability cascade skipped: {e}")

        if live_events:
            save_geopolitical_vintage_record(live_events)
            global_cache.set(cache_key, {"headlines": live_events}, ttl_seconds=900)

        return live_events


def get_geopolitical_maritime_events() -> pd.DataFrame:
    """
    Returns structured historical and real-time event feeds for Iran/Hormuz, Suez/Red Sea, and Venezuela.
    Dynamically fetched via public RSS endpoints and finlight.me when available.
    """
    base_events = None
    try:
        from src.benchmark_updater import load_historical_benchmark
        loaded = load_historical_benchmark("geopolitical")
        if loaded and isinstance(loaded, list):
            base_events = list(loaded)
    except Exception:
        pass

    if base_events is None:
        base_events = list(HISTORICAL_GEOPOLITICAL_EVENTS)

    df = pd.DataFrame(base_events)
    df['date'] = pd.to_datetime(df['date'])

    # 1. Dynamically augment with live RSS feed
    try:
        connector = GeopoliticalFeedConnector()
        live_headlines = connector.fetch_geopolitical_headlines()
        if live_headlines:
            live_df = pd.DataFrame(live_headlines)
            live_df['date'] = pd.to_datetime(live_df['date'])
            df = pd.concat([df, live_df], ignore_index=True)
            logger.info(f"Augmented geopolitical feed with {len(live_headlines)} live RSS events.")
            try:
                from src.benchmark_updater import save_historical_benchmark
                save_historical_benchmark("geopolitical", df.to_dict(orient="records"))
            except Exception:
                pass
    except Exception as e:
        logger.debug(f"Live RSS geopolitical augmentation notice: {e}")

    # 2. Dynamically augment with live finlight.me news if API key is present
    try:
        from src.finlight_feed import fetch_finlight_articles
        live_articles = fetch_finlight_articles(page_size=30)
        fin_events = []
        for a in live_articles:
            text = f"{a.get('title', '')} - {a.get('summary', '')}".lower()
            chokepoint = None
            category = "Geopolitical_News"
            if "hormuz" in text or "iran" in text:
                chokepoint = "Strait_of_Hormuz"
                category = "Iran_Hormuz"
            elif "red sea" in text or "houthi" in text or "suez" in text:
                chokepoint = "Suez_Bab_el_Mandeb"
                category = "Suez_RedSea"
            elif "venezuela" in text or "sanction" in text:
                chokepoint = "Venezuela_Orinoco"
                category = "Venezuela"

            if chokepoint:
                dt_str = pd.to_datetime(a.get("publishDate")).strftime("%Y-%m-%d") if a.get("publishDate") else datetime.now().strftime("%Y-%m-%d")
                fin_events.append({
                    "date": pd.to_datetime(dt_str),
                    "headline": a.get("title", ""),
                    "category": category,
                    "chokepoint": chokepoint
                })
        if fin_events:
            fin_df = pd.DataFrame(fin_events)
            df = pd.concat([df, fin_df], ignore_index=True)
            logger.info(f"Augmented geopolitical feed with {len(fin_events)} live finlight.me events.")
    except Exception as e:
        logger.debug(f"Finlight geopolitical augmentation notice: {e}")

    return df.sort_values('date').reset_index(drop=True)


def calculate_chokepoint_risk_index(events_df: pd.DataFrame) -> dict:
    """
    Computes real-time maritime chokepoint risk scores based on active geopolitical events.
    """
    scores = {}
    for key, info in CHOKEPOINTS.items():
        subset = events_df[events_df['chokepoint'] == key]
        count = len(subset)
        risk_score = round(min(1.0, count * 0.25), 2)
        scores[key] = {
            "active_events_count": count,
            "chokepoint_risk_score": risk_score,
            "daily_volume_mbpd": info["daily_volume_mbpd"],
            "share_global_petroleum": f"{info['share_global_petroleum']*100:.0f}%",
            "status": "ELEVATED RISK" if risk_score > 0.4 else "NORMAL"
        }
    return scores


if __name__ == "__main__":
    df = get_geopolitical_maritime_events()
    print(f"Loaded {len(df)} Geopolitical & Maritime Events.")
    print(json.dumps(calculate_chokepoint_risk_index(df), indent=2))

