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
import defusedxml.ElementTree as ET
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import logging
from src.lookup_cache import global_cache

logger = logging.getLogger(__name__)

from src.http_client import http_get, DEFAULT_USER_AGENT

USER_AGENT = DEFAULT_USER_AGENT
GEOPOLITICAL_VINTAGE_FILE = os.path.join("data", "geopolitical_vintages.json")

TRACKING_QUERY_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "gclid", "fbclid", "ref", "source", "ncid", "ocid", "ved", "usqp"
}


def normalize_url(url: Any) -> str:
    """Strips query tracking parameters, anchors, and normalizes URL safely handling NaN/null inputs."""
    if url is None:
        return ""
    if not isinstance(url, str):
        # Handle pandas / numpy NaN
        if str(url).lower() == "nan" or (isinstance(url, float) and url != url):
            return ""
        url = str(url)
    url_str = url.strip()
    if not url_str or url_str.lower() in ("nan", "none"):
        return ""
    try:
        parsed = urllib.parse.urlparse(url_str)
        if not parsed.scheme or not parsed.netloc:
            return url_str
        query_pairs = urllib.parse.parse_qsl(parsed.query)
        filtered_pairs = [(k, v) for k, v in query_pairs if k.lower() not in TRACKING_QUERY_PARAMS]
        new_query = urllib.parse.urlencode(filtered_pairs)
        normalized = urllib.parse.urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip('/'),
            "",
            new_query,
            ""
        ))
        return normalized
    except Exception:
        return url_str


def normalize_headline(headline: str) -> str:
    """
    Normalizes headline text by removing publisher suffixes and special characters.
    Preserves intra-word hyphens (e.g., 'Iran-backed Houthis' -> 'iran-backed houthis').
    """
    if not headline:
        return ""
    # Strip trailing publisher attributions (preceded by whitespace and hyphen/pipe)
    text = re.sub(r"\s+-\s+[^-\n]+$", "", headline).strip()
    text = re.sub(r"\s+\|\s+[^|\n]+$", "", text).strip()
    # Preserve intra-word hyphens: keep alphanumeric, whitespace, and hyphens
    text = re.sub(r"[^\w\s-]", "", text).lower()
    return re.sub(r"\s+", " ", text).strip()


def compute_headline_similarity(h1: str, h2: str) -> float:
    """Computes word-token Jaccard similarity between two headlines."""
    tokens1 = set(normalize_headline(h1).split())
    tokens2 = set(normalize_headline(h2).split())
    if not tokens1 or not tokens2:
        return 0.0
    intersection = len(tokens1 & tokens2)
    union = len(tokens1 | tokens2)
    return float(intersection) / float(union) if union > 0 else 0.0


def deduplicate_events(events: List[Dict[str, Any]], similarity_threshold: float = 0.85) -> List[Dict[str, Any]]:
    """
    Deduplicates a list of event dictionaries across rolling dates (+/- 1 day)
    using canonical URLs and pre-tokenized Jaccard similarity.
    """
    unique_events: List[Dict[str, Any]] = []
    seen_urls: set = set()
    tokenized_by_date: Dict[str, List[Tuple[set, str]]] = {}

    for ev in events:
        if not isinstance(ev, dict):
            continue

        raw_url = ev.get("url")
        canon_url = normalize_url(raw_url)
        if canon_url and canon_url in seen_urls:
            continue

        headline = str(ev.get("headline") or ev.get("title") or ev.get("chokepoint") or ev.get("event") or "")
        norm_h = normalize_headline(headline) if headline else ""
        tokens = set(norm_h.split()) if norm_h else set(f"{k}:{v}" for k, v in ev.items() if k != "url")
        if not tokens:
            tokens = {"event"}

        dt_str = str(ev.get("date", ""))[:10]
        candidate_dates = [dt_str]
        try:
            base_dt = datetime.strptime(dt_str, "%Y-%m-%d").date()
            candidate_dates.append((base_dt - timedelta(days=1)).strftime("%Y-%m-%d"))
            candidate_dates.append((base_dt + timedelta(days=1)).strftime("%Y-%m-%d"))
        except Exception:
            pass

        is_duplicate = False
        for c_dt in candidate_dates:
            if c_dt in tokenized_by_date:
                for seen_tokens, _ in tokenized_by_date[c_dt]:
                    intersection = len(tokens & seen_tokens)
                    union = len(tokens | seen_tokens)
                    sim = float(intersection) / float(union) if union > 0 else 0.0
                    if sim >= similarity_threshold:
                        is_duplicate = True
                        break
            if is_duplicate:
                break

        if not is_duplicate:
            if canon_url:
                seen_urls.add(canon_url)
                ev["url"] = canon_url
            if dt_str not in tokenized_by_date:
                tokenized_by_date[dt_str] = []
            tokenized_by_date[dt_str].append((tokens, norm_h))
            unique_events.append(ev)

    return unique_events


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


def save_geopolitical_vintage_record(records: list, filepath: Optional[str] = None) -> None:
    """Appends a point-in-time geopolitical event observation vintage record with deduplication."""
    if os.environ.get("TESTING") == "1" and filepath is None:
        return
    if filepath is None:
        filepath = GEOPOLITICAL_VINTAGE_FILE
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        vintages = []
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    vintages = json.load(f)
            except Exception:
                vintages = []

        deduped = deduplicate_events(records)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        vintage_entry = {
            "as_of": now_str,
            "events_count": len(deduped),
            "events": deduped
        }
        # Update or append cleanly
        if vintages and vintages[-1].get("as_of", "")[:10] == now_str[:10]:
            vintages[-1] = vintage_entry
        else:
            vintages.append(vintage_entry)
            
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(vintages, f, indent=2)
    except Exception as e:
        logger.debug(f"Failed to persist geopolitical vintage record: {e}")


def get_geopolitical_vintages_as_of(as_of_date: str, filepath: Optional[str] = None) -> Optional[List[dict]]:
    """Retrieves geopolitical events recorded on or before as_of_date."""
    if filepath is None:
        filepath = GEOPOLITICAL_VINTAGE_FILE
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

    def fetch_geopolitical_headlines(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Fetches live breaking maritime and geopolitical headlines with 15-minute lookup caching.
        """
        minute_bucket = datetime.now().strftime("%Y-%m-%d-%H")
        cache_key = f"geopolitical_headlines:{minute_bucket}"
        if not force_refresh:
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
                resp = http_get(url, timeout=5)
                if resp.status_code == 200:
                    root = ET.fromstring(resp.content)
                    for item in root.findall(".//item")[:5]:
                        title = item.findtext("title", "")
                        pub_date = item.findtext("pubDate", "")
                        link = item.findtext("link", "")
                        
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
                            "url": normalize_url(link)
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
                            "url": normalize_url(item.get("url", ""))
                        })
            except Exception as e:
                logger.debug(f"Geopolitical reachability cascade skipped: {e}")

        live_events = deduplicate_events(live_events)

        if live_events:
            save_geopolitical_vintage_record(live_events)
            global_cache.set(cache_key, {"headlines": live_events}, ttl_seconds=900)

        return live_events


def get_geopolitical_maritime_events() -> pd.DataFrame:
    """
    Returns structured historical and real-time event feeds for Iran/Hormuz, Suez/Red Sea, and Venezuela.
    Dynamically fetched via public RSS endpoints and finlight.me when available, with strict deduplication.
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

    all_records = list(base_events)

    # 1. Dynamically augment with live RSS feed
    try:
        connector = GeopoliticalFeedConnector()
        live_headlines = connector.fetch_geopolitical_headlines()
        if live_headlines:
            all_records.extend(live_headlines)
            logger.info(f"Augmented geopolitical feed with {len(live_headlines)} live RSS events.")
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
                    "date": dt_str,
                    "headline": a.get("title", ""),
                    "category": category,
                    "chokepoint": chokepoint,
                    "url": normalize_url(a.get("url", ""))
                })
        if fin_events:
            all_records.extend(fin_events)
            logger.info(f"Augmented geopolitical feed with {len(fin_events)} live finlight.me events.")
    except Exception as e:
        logger.debug(f"Finlight geopolitical augmentation notice: {e}")

    # Deduplicate all records to prevent self-appending duplicate growth (Issue #566)
    deduped_records = deduplicate_events(all_records)
    
    # Save deduplicated benchmark if changed
    try:
        from src.benchmark_updater import save_historical_benchmark
        if len(deduped_records) != len(base_events) or deduped_records != base_events:
            save_historical_benchmark("geopolitical", deduped_records)
    except Exception:
        pass

    df = pd.DataFrame(deduped_records)
    df['date'] = pd.to_datetime(df['date'], format='mixed')
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

