"""
Unified Multi-Layer Intraday Event Monitor (src/intraday_event_monitor.py)

Combines:
- Strategy 2: Free 15-minute RSS & Social Bridge Poller (Google News, NYT, CNBC)
- Strategy 1: Two-Stage Cascading Anomaly Keyword Filter
- Strategy 3: Trading Hours Adaptive Ingestion with Tiered LLM Failover
- Strategy 4: Webhook Ingestion Handler Integration

Flashes 15-minute response cache, logs intraday prediction revisions, and updates alert banners.
"""

import os
import json
import time
import logging
import pandas as pd
from datetime import datetime
from typing import List, Dict, Tuple, Optional

try:
    import feedparser
except ImportError:
    feedparser = None

from src.event_analyzer import extract_event_features_llm, extract_event_features_rule_based
from src.finlight_feed import is_trading_hours, fetch_finlight_on_demand, UNIFIED_ENERGY_QUERY
from src.lookup_cache import clear_lookup_cache
from src.prediction_logger import log_predictions

logger = logging.getLogger(__name__)

# Primary Free Energy RSS Feeds for Zero-Cost 15-Min Polling
FREE_RSS_FEEDS = [
    "https://news.google.com/rss/search?q=unleaded+gasoline+when:3d&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=refinery+outage+when:3d&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=oil+tariff+when:3d&hl=en-US&gl=US&ceid=US:en",
    "https://rss.nytimes.com/services/xml/rss/nyt/EnergyEnvironment.xml"
]

# Excluded Keywords to Filter Non-Energy Outages & Noise
EXCLUDE_KEYWORDS = [
    "wikipedia", "software outage", "airline outage", "it outage", "cloud outage", "gaming outage", "network outage"
]

# High-Risk Keyword Lexicon for Stage 1 Cascading Gate
TRIGGER_KEYWORDS = [
    "tariff", "retaliat", "trade war", "opec emergency", "pipeline halt", "pipeline outage",
    "explosion", "tornado", "blackout", "blockade", "sanction",
    "refinery outage", "refinery halt", "power grid outage", "plant outage", "terminal outage",
    "strait of hormuz", "red sea attack", "spill",
    # Market Technicals & Volatility
    "crack spread", "crack-spread", "ovx spike", "futures spike", "futures crash", "wti surge", "rbob surge", "barrel price",
    # Executive Policy & Geopolitics
    "executive order", "energy tariff", "sanction threat", "strait blockade", "strategic petroleum reserve", "spr release", "opec cut", "opec quota",
    # Logistics & Infrastructure Hubs
    "colonial pipeline", "keystone pipeline", "refinery explosion", "refinery fire", "cushing inventory", "barge congestion",
    "catlettsburg", "delaware city", "west tulsa", "richmond refinery"
]

ANOMALY_LOG_FILE = os.path.join("data", "intraday_events.json")


class IntradayEventMonitor:
    def __init__(self, shock_threshold: float = 0.40):
        self.shock_threshold = shock_threshold

    def fetch_rss_headlines(self, max_age_hours: float = 72.0) -> List[Dict[str, str]]:
        """Fetches breaking titles from free RSS feeds without using API quotas, discarding stale entries older than max_age_hours."""
        headlines = []
        if feedparser is None:
            logger.warning("feedparser module not installed. Falling back to rule-based scanner.")
            return headlines

        from datetime import timezone
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        for url in FREE_RSS_FEEDS:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:15]:
                    title = entry.get("title", "").strip()
                    published = entry.get("published", "")
                    link = entry.get("link", "")

                    # Filter out stale articles if published_parsed exists
                    pub_parsed = entry.get("published_parsed")
                    if pub_parsed:
                        try:
                            pub_dt = datetime(*pub_parsed[:6])
                            age_hours = (now - pub_dt).total_seconds() / 3600.0
                            if age_hours > max_age_hours:
                                logger.info(f"Skipping stale RSS article ({age_hours:.1f}h old): '{title}'")
                                continue
                        except Exception as parse_err:
                            logger.debug(f"Could not calculate RSS item age: {parse_err}")

                    if title:
                        headlines.append({
                            "headline": title,
                            "published": published if published else now.isoformat(),
                            "url": link,
                            "source": "RSS_Feed"
                        })
            except Exception as e:
                logger.warning(f"Failed to parse RSS feed '{url}': {e}")
        return headlines

    def evaluate_headline_anomaly(self, headline: str) -> Tuple[bool, Dict[str, float]]:
        """
        Stage 1 & 2 Cascading Filter:
        Scans headline for trigger keywords. If matched, extracts factor scores
        via Tiered LLM / Lexicon failover. Returns (is_anomaly, scores).
        """
        text_lower = headline.lower()
        if any(ex in text_lower for ex in EXCLUDE_KEYWORDS):
            return False, {"overall_price_pressure": 0.0, "supply_disruption": 0.0}

        has_keyword = any(kw in text_lower for kw in TRIGGER_KEYWORDS)

        if not has_keyword:
            return False, {"overall_price_pressure": 0.0, "supply_disruption": 0.0}

        # Keyword matched -> Trigger impact scoring
        scores = extract_event_features_llm(headline)
        overall_pressure = abs(scores.get("overall_price_pressure", 0.0))
        supply_disruption = scores.get("supply_disruption", 0.0)

        is_anomaly = (overall_pressure >= self.shock_threshold) or (supply_disruption >= 0.50)
        return is_anomaly, scores

    def is_headline_already_processed(self, headline: str, url: str = "", max_age_hours: float = 24.0) -> bool:
        """
        Checks data/intraday_events.json to see if this headline or URL has already been 
        evaluated and logged within the last max_age_hours.
        """
        if not os.path.exists(ANOMALY_LOG_FILE):
            return False
            
        clean_headline = headline.lower().strip()
        from datetime import timezone
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        
        try:
            with open(ANOMALY_LOG_FILE, "r", encoding="utf-8") as f:
                events = json.load(f)
                if not isinstance(events, list):
                    return False
                    
                for evt in events:
                    evt_headline = evt.get("headline", "").lower().strip()
                    evt_url = evt.get("url", "").strip()
                    evt_ts_str = evt.get("timestamp", "")
                    
                    # Match by exact URL (if present) or headline text
                    url_match = bool(url and evt_url and url == evt_url)
                    headline_match = bool(clean_headline == evt_headline)
                    
                    if url_match or headline_match:
                        if evt_ts_str:
                            try:
                                evt_dt = datetime.fromisoformat(evt_ts_str).replace(tzinfo=None)
                                age_hours = (now - evt_dt).total_seconds() / 3600.0
                                if age_hours <= max_age_hours:
                                    return True
                            except Exception:
                                return True
                        else:
                            return True
        except Exception as e:
            logger.warning(f"Failed to check headline deduplication log: {e}")
            
        return False

    def resolve_target_locales(self, headline: str) -> List[str]:
        """
        Maps incoming headline keywords to affected regional metro calibration agents.
        Returns a sorted list of target locale identifiers (e.g. ['Tulsa'], ['Greenville', 'Charlotte'], or ['National']).
        """
        text = headline.lower()
        targets = set()

        # Tulsa / Cushing / West Tulsa
        if any(k in text for k in ["tulsa", "cushing", "sinclair", "hf sinclair", "west tulsa"]):
            targets.add("Tulsa")

        # Newark / Delaware City / PADD 1B
        if any(k in text for k in ["newark", "delaware city", "delaware", "padd 1b", "padd1b"]):
            targets.add("Newark")

        # Cincinnati / Catlettsburg / Ohio River
        if any(k in text for k in ["cincinnati", "catlettsburg", "ohio river", "markland lock", "mcalpine lock"]):
            targets.add("Cincinnati")

        # Greenville & Charlotte / Colonial Pipeline / Selma / Paw Creek
        if any(k in text for k in ["colonial pipeline", "greenville", "charlotte", "selma", "paw creek"]):
            targets.add("Greenville")
            targets.add("Charlotte")

        # Oakland & SF Bay Area / Richmond / CARB / California
        if any(k in text for k in ["oakland", "sf bay", "san francisco", "richmond refinery", "carb", "california"]):
            targets.add("Oakland")

        # Port St. Lucie / Florida / Waterborne Freight
        if any(k in text for k in ["port st. lucie", "port st lucie", "florida", "waterborne freight"]):
            targets.add("Port_St_Lucie")

        if not targets:
            return ["National"]

        return sorted(list(targets))

    def process_incoming_headline(self, headline: str, source: str = "Webhook", url: str = "", skip_dedup: bool = False) -> Dict:
        """
        Evaluates an individual incoming headline (from Webhook or RSS), logs anomalies,
        and triggers cache invalidation / prediction revision logging if threshold is met.
        Deduplicates against previously processed headlines within 24 hours.
        """
        target_locales = self.resolve_target_locales(headline)

        # Deduplication check unless explicitly skipped or running automated test runner
        if not skip_dedup and not source.startswith("Test_"):
            if self.is_headline_already_processed(headline, url=url):
                logger.info(f"Skipping duplicate headline within 24h window: '{headline}'")
                return {
                    "timestamp": datetime.now().isoformat(),
                    "headline": headline,
                    "source": source,
                    "url": url,
                    "is_anomaly": False,
                    "duplicate": True,
                    "target_locales": target_locales,
                    "scores": {"overall_price_pressure": 0.0, "supply_disruption": 0.0}
                }

        is_anomaly, scores = self.evaluate_headline_anomaly(headline)
        clean_scores = {
            k: float(v) for k, v in scores.items()
            if not k.startswith("_") and isinstance(v, (int, float))
        }
        is_anomaly_bool = bool(is_anomaly)

        archive_url = ""
        if url:
            try:
                from src.wayback_archiver import archive_url_to_wayback
                arch_res = archive_url_to_wayback(url, headline=headline)
                archive_url = arch_res.get("archive_url", "")
                logger.info(f"  -> Wayback Machine archive URL logged: {archive_url}")
            except Exception as e:
                logger.warning(f"Wayback Machine archive trigger error: {e}")

        result = {
            "timestamp": datetime.now().isoformat(),
            "headline": headline,
            "source": source,
            "url": url,
            "archive_url": archive_url,
            "is_anomaly": is_anomaly_bool,
            "target_locales": target_locales,
            "scores": clean_scores
        }

        if is_anomaly:
            logger.info(f"🚨 HIGH-IMPACT INTRADAY ANOMALY DETECTED [{source}] (Targets: {target_locales}): '{headline}' (Scores: {scores})")

            is_test = source.startswith("Test_") or os.environ.get("TESTING") == "1"
            if is_test:
                logger.info(f"  -> Skipping persistent storage & dashboard rebuild for test execution [{source}].")
            else:
                # 1. Log anomaly event to disk
                self._save_anomaly_record(result)

                # 2. Flush 15-minute SQLite response cache
                clear_lookup_cache()
                logger.info("  -> Cleared SQLite response cache for API gateway.")


                # 3. Log Intraday Revision Record across target locales
                for loc in target_locales:
                    dummy_df = pd.DataFrame([{
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "current_price": 3.184,
                        "predicted_5d_price": 3.184 * (1.0 + scores.get("overall_price_pressure", 0.0) * 0.04)
                    }])
                    log_predictions(
                        dummy_df, 
                        region=loc, 
                        model_version="v1.4-Finlight-Intraday",
                        run_type="INTRADAY_REVISION",
                        headline_trigger=headline
                    )

                # 4. Regenerate Public Web Dashboard
                try:
                    from src.dashboard_generator import generate_public_dashboard
                    generate_public_dashboard()
                    logger.info("  -> Regenerated public dashboard web app (docs/).")
                except Exception as e:
                    logger.warning(f"Failed to regenerate dashboard after anomaly: {e}")

        return result

    def run_polling_cycle(self) -> Dict:
        """Executes a full 15-minute polling cycle across free RSS streams."""
        logger.info("Executing 15-minute Intraday Event Monitor cycle...")
        headlines_data = self.fetch_rss_headlines()
        anomalies_found = []

        for item in headlines_data:
            headline = item["headline"]
            url = item.get("url", "")
            res = self.process_incoming_headline(headline, source=item.get("source", "RSS"), url=url)
            if res["is_anomaly"]:
                anomalies_found.append(res)
                # Process primary anomaly per polling cycle to avoid multiple sequential dashboard rebuilds
                break

        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "headlines_scanned": len(headlines_data),
            "anomalies_detected": len(anomalies_found),
            "trading_hours_active": is_trading_hours(),
            "anomalies": anomalies_found
        }

    def _save_anomaly_record(self, record: Dict):
        """Appends anomaly record to data/intraday_events.json."""
        os.makedirs("data", exist_ok=True)
        events = []
        if os.path.exists(ANOMALY_LOG_FILE):
            try:
                with open(ANOMALY_LOG_FILE, "r", encoding="utf-8") as f:
                    events = json.load(f)
            except Exception:
                events = []
        events.append(record)
        try:
            with open(ANOMALY_LOG_FILE, "w", encoding="utf-8") as f:
                json.dump(events, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to write anomaly log '{ANOMALY_LOG_FILE}': {e}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Multi-Layer Intraday Event Monitor")
    parser.add_argument("--headline", type=str, default="", help="Single headline string to process")
    parser.add_argument("--source", type=str, default="Cloudflare_Worker", help="Headline source identifier")
    parser.add_argument("--url", type=str, default="", help="Headline URL")
    parser.add_argument("--skip-dedup", action="store_true", help="Skip 24h deduplication check")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    monitor = IntradayEventMonitor()

    if args.headline:
        res = monitor.process_incoming_headline(
            headline=args.headline,
            source=args.source,
            url=args.url,
            skip_dedup=args.skip_dedup
        )
    else:
        res = monitor.run_polling_cycle()

    print(json.dumps(res, indent=2))
    return res


if __name__ == "__main__":
    main()

