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
import sys
import json
import time
import logging
import pandas as pd
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any

# Ensure project root is in sys.path when executed directly
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    import feedparser
except ImportError:
    feedparser = None

from src.event_analyzer import extract_event_features_llm, extract_event_features_rule_based
from src.finlight_feed import is_trading_hours, fetch_finlight_on_demand, UNIFIED_ENERGY_QUERY
from src.lookup_cache import clear_lookup_cache
from src.prediction_logger import log_predictions, resolve_model_tag
try:
    from src.discord_notifier import send_intraday_discord_notification
except ImportError:
    send_intraday_discord_notification = None

logger = logging.getLogger(__name__)

# Primary Free Energy RSS Feeds for Zero-Cost 15-Min Polling
FREE_RSS_FEEDS = [
    "https://news.google.com/rss/search?q=unleaded+gasoline+when:1d&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=refinery+outage+when:1d&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=oil+tariff+when:1d&hl=en-US&gl=US&ceid=US:en",
    "https://rss.nytimes.com/services/xml/rss/nyt/EnergyEnvironment.xml"
]

# Excluded Keywords to Filter Non-Energy Outages & Noise
EXCLUDE_KEYWORDS = [
    "wikipedia", "software outage", "airline outage", "it outage", "cloud outage", "gaming outage", "network outage",
    "canola", "cooking oil", "palm oil", "olive oil", "soybean oil"
]

# Non-Energy Policy Keywords to Filter False Positive Trade/Policy Headlines
NON_ENERGY_TARIFF_EXCLUDE = [
    "house should not transfer", "tariff authority", "steel tariff", "aluminum tariff", "copper tariff",
    "lumber tariff", "auto tariff", "solar tariff", "washing machine", "semiconductor tariff", "chip tariff",
    "reciprocal trade act", "section 301", "section 232", "canola", "canola oil"
]

# High-Risk Keyword Lexicon for Stage 1 Cascading Gate
TRIGGER_KEYWORDS = [
    "energy tariff", "oil tariff", "fuel tariff", "crude tariff", "gasoline tariff", "retaliatory tariff", "counter-tariff",
    "retaliat", "trade war", "opec emergency", "pipeline halt", "pipeline outage",
    "explosion", "tornado", "blackout", "blockade", "sanction",
    "refinery outage", "refinery halt", "power grid outage", "plant outage", "terminal outage",
    "strait of hormuz", "red sea attack", "spill",
    # Market Technicals & Volatility
    "crack spread", "crack-spread", "ovx spike", "futures spike", "futures crash", "wti surge", "rbob surge", "barrel price",
    # Executive Policy & Geopolitics
    "executive order", "sanction threat", "strait blockade", "strategic petroleum reserve", "spr release", "opec cut", "opec quota",
    # Logistics & Infrastructure Hubs
    "colonial pipeline", "keystone pipeline", "refinery explosion", "refinery fire", "cushing inventory", "barge congestion",
    "catlettsburg", "delaware city", "west tulsa", "richmond refinery",
    # Refinery Operator 8-K Signals (Issue #129 — EDGAR 8-K Monitor)
    "pbf energy", "hf sinclair", "holly frontier", "marathon petroleum", "valero", "phillips 66",
    "force majeure", "unplanned outage", "crude distillation unit", "fcc unit",
    "hydrocracker", "coker unit", "capacity reduction", "el dorado refinery",
    "sweeny refinery", "bayway refinery",
]

ANOMALY_LOG_FILE = os.path.join("data", "intraday_events.json")
EVALUATED_CACHE_FILE = os.path.join("data", "evaluated_headlines.json")


def normalize_headline(headline: str) -> str:
    """
    Normalizes a news headline by stripping trailing RSS publisher attribution suffixes
    (e.g., ' - National Taxpayers Union', ' - Reuters', ' | OilPrice.com', ' — CNBC'),
    removing extraneous quotes/punctuation, and lowercasing for consistent deduplication.
    """
    if not headline:
        return ""
    import re
    # Strip trailing publisher tag: " - Publisher Name" or " | Publisher Name" or " — Publisher Name"
    cleaned = re.sub(r'\s+[-–—|]\s+[^-–—|]+$', '', headline.strip())
    # Lowercase and collapse whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned.lower()).strip()
    # Strip surrounding quotes or brackets
    cleaned = re.sub(r'^[\'"“‘\[\(]+|[\'"”’\]\)]+$', '', cleaned).strip()
    return cleaned


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

    def fetch_executive_social_headlines(self) -> List[Dict[str, str]]:
        """Fetches breaking energy commentary from executive social feeds (Issue #268)."""
        headlines = []
        try:
            from src.executive_social_feed import ExecutiveSocialFeedConnector
            connector = ExecutiveSocialFeedConnector()
            posts = connector.fetch_live_posts()
            for p in posts:
                post_text = p.get("post_text", "").strip()
                if post_text:
                    headlines.append({
                        "headline": post_text,
                        "published": p.get("date", datetime.now().isoformat()),
                        "url": f"https://truthsocial.com/post/{abs(hash(post_text)) % 10000000}",
                        "source": "Executive_Social_Media"
                    })
        except Exception as e:
            logger.debug(f"Could not poll live executive social headlines: {e}")
        return headlines

    def fetch_key_movers_headlines(self) -> List[Dict[str, str]]:
        """Fetches breaking statements from key energy policymakers (Issue #270)."""
        headlines = []
        try:
            from src.key_movers_feed import KeyMoversFeedConnector
            connector = KeyMoversFeedConnector()
            events = connector.fetch_live_events()
            for ev in events:
                hl = ev.get("headline", "").strip()
                if hl:
                    headlines.append({
                        "headline": hl,
                        "published": ev.get("date", datetime.now().isoformat()),
                        "url": f"https://news.google.com/search?q={abs(hash(hl)) % 10000000}",
                        "source": f"Key_Mover_{ev.get('entity', 'Official')}"
                    })
        except Exception as e:
            logger.debug(f"Could not poll live key movers headlines: {e}")
        return headlines

    def fetch_geopolitical_headlines(self) -> List[Dict[str, str]]:
        """Fetches breaking geopolitical and maritime chokepoints news (Issue #278)."""
        headlines = []
        try:
            from src.geopolitical_feeds import GeopoliticalFeedConnector
            connector = GeopoliticalFeedConnector()
            events = connector.fetch_geopolitical_headlines()
            for ev in events:
                hl = ev.get("headline", "").strip()
                if hl:
                    headlines.append({
                        "headline": hl,
                        "published": ev.get("date", datetime.now().isoformat()),
                        "url": ev.get("url", f"https://news.google.com/search?q={abs(hash(hl)) % 10000000}"),
                        "source": f"Geopolitical_{ev.get('chokepoint', 'Maritime')}"
                    })
        except Exception as e:
            logger.debug(f"Could not poll live geopolitical headlines: {e}")
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

        if any(ex in text_lower for ex in NON_ENERGY_TARIFF_EXCLUDE):
            return False, {"overall_price_pressure": 0.0, "supply_disruption": 0.0}

        has_keyword = any(kw in text_lower for kw in TRIGGER_KEYWORDS)

        # Allow tariff/tariffs if accompanied by energy/fuel/oil terms
        if not has_keyword and ("tariff" in text_lower or "tariffs" in text_lower):
            energy_context = any(e in text_lower for e in ["oil", "crude", "gasoline", "fuel", "petroleum", "refin", "diesel", "opec", "energy"])
            if energy_context:
                has_keyword = True

        if not has_keyword:
            return False, {"overall_price_pressure": 0.0, "supply_disruption": 0.0}

        # Generate CoSPOT Spectral Context if market data is available (Issue #215)
        spectral_ctx = ""
        try:
            from src.cospot_spectral_engine import generate_spectral_prompt_context
            from src.data_ingestion import fetch_all_data
            m_df = fetch_all_data()
            if not m_df.empty and 'gasoline_rbob' in m_df.columns:
                spectral_ctx = generate_spectral_prompt_context(m_df['gasoline_rbob'].values)
        except Exception:
            pass

        # Keyword matched -> Trigger impact scoring
        scores = extract_event_features_llm(headline, spectral_context=spectral_ctx)
        overall_pressure = abs(scores.get("overall_price_pressure", 0.0))
        supply_disruption = scores.get("supply_disruption", 0.0)

        is_anomaly = (overall_pressure >= self.shock_threshold) or (supply_disruption >= 0.50)
        return is_anomaly, scores

    def is_headline_already_processed(self, headline: str, url: str = "", max_age_hours: float = 24.0) -> bool:
        """
        Checks data/intraday_events.json and data/evaluated_headlines.json to see if this
        headline or URL has already been evaluated and logged within the last max_age_hours.
        Uses normalized headline matching to handle publisher attribution variations.
        """
        from datetime import timezone
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        clean_headline = headline.lower().strip()
        norm_headline = normalize_headline(headline)

        # 1. Check positive anomaly records
        if os.path.exists(ANOMALY_LOG_FILE):
            try:
                with open(ANOMALY_LOG_FILE, "r", encoding="utf-8") as f:
                    events = json.load(f)
                    if isinstance(events, list):
                        for evt in events:
                            evt_headline = evt.get("headline", "").lower().strip()
                            evt_norm = normalize_headline(evt.get("headline", ""))
                            evt_url = evt.get("url", "").strip()
                            evt_ts_str = evt.get("timestamp", "")

                            url_match = bool(url and evt_url and url == evt_url)
                            headline_match = bool(clean_headline == evt_headline or (norm_headline and norm_headline == evt_norm))

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
                logger.warning(f"Failed to check anomaly deduplication log: {e}")

        # 2. Check rolling evaluated ledger (captures non-anomalies as well)
        if os.path.exists(EVALUATED_CACHE_FILE):
            try:
                with open(EVALUATED_CACHE_FILE, "r", encoding="utf-8") as f:
                    evaluated = json.load(f)
                    if isinstance(evaluated, list):
                        for evt in evaluated:
                            evt_headline = evt.get("headline", "").lower().strip()
                            evt_norm = evt.get("norm_headline") or normalize_headline(evt.get("headline", ""))
                            evt_url = evt.get("url", "").strip()
                            evt_ts_str = evt.get("timestamp", "")

                            url_match = bool(url and evt_url and url == evt_url)
                            headline_match = bool(clean_headline == evt_headline or (norm_headline and norm_headline == evt_norm))

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
                logger.warning(f"Failed to check evaluated headlines cache: {e}")

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

        # Refinery Operator 8-K Locale Routing (Issue #129 — EDGAR 8-K Monitor)
        # PBF Energy → Newark (Delaware City Refinery, PADD 1B)
        if any(k in text for k in ["pbf energy", "pbf 8-k", "delaware city refinery"]):
            targets.add("Newark")

        # HF Sinclair → Tulsa (El Dorado / Tulsa-area, PADD 2 Mid-Continent)
        if any(k in text for k in ["hf sinclair", "holly frontier", "el dorado refinery"]):
            targets.add("Tulsa")

        # Marathon Petroleum → Cincinnati (Catlettsburg, PADD 3/2 junction)
        if any(k in text for k in ["marathon petroleum", "marathon 8-k"]):
            targets.add("Cincinnati")

        # Valero / Phillips 66 → National (multi-PADD footprint, no single dominant locale)
        if any(k in text for k in ["valero 8-k", "phillips 66 8-k", "sweeny refinery", "bayway refinery"]):
            targets.add("National")

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
        resolved_url = url
        if url:
            try:
                from src.wayback_archiver import archive_url_to_wayback
                arch_res = archive_url_to_wayback(url, headline=headline)
                archive_url = arch_res.get("archive_url", "")
                resolved_url = arch_res.get("canonical_url") or url
                logger.info(f"  -> Wayback Machine archive URL logged: {archive_url}")
            except Exception as e:
                logger.warning(f"Wayback Machine archive trigger error: {e}")

        result = {
            "timestamp": datetime.now().isoformat(),
            "headline": headline,
            "source": source,
            "url": resolved_url or url,
            "raw_url": url,
            "archive_url": archive_url,
            "is_anomaly": is_anomaly_bool,
            "target_locales": target_locales,
            "scores": clean_scores
        }

        is_test = source.startswith("Test_") or os.environ.get("TESTING") == "1"
        if not is_test:
            self._save_evaluated_record(result)

        if is_anomaly:
            logger.info(f"🚨 HIGH-IMPACT INTRADAY ANOMALY DETECTED [{source}] (Targets: {target_locales}): '{headline}' (Scores: {scores})")

            # Dispatch Discord Webhook Notification (Issue #234)
            if send_intraday_discord_notification:
                try:
                    discord_sent = send_intraday_discord_notification(result)
                    result["discord_notified"] = bool(discord_sent)
                except Exception as e:
                    logger.warning(f"Discord notification dispatch error: {e}")
                    result["discord_notified"] = False

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
                        model_version=resolve_model_tag(region=loc, model_type="Intraday"),
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

                # 5. Headline Arena Benchmark Submission for Intraday Anomaly Revisions (Issue #182)
                try:
                    from src.headline_arena_connector import HeadlineArenaConnector, submit_midgley_energy_forecasts
                    from src.data_ingestion import fetch_market_data
                    ha_conn = HeadlineArenaConnector()
                    live_dev = os.environ.get("HEADLINE_ARENA_DEV_SUBMIT") == "1"
                    if ha_conn.is_configured and (ha_conn.is_prod or live_dev):
                        m_df = fetch_market_data(start_date="2024-01-01")
                        if not m_df.empty:
                            rb_open = float(m_df['gasoline_rbob'].iloc[-1])
                            cl_open = float(m_df['crude_wti'].iloc[-1]) if 'crude_wti' in m_df.columns else 75.0
                            pressure = scores.get("overall_price_pressure", 0.0)
                            rb_revised = rb_open * (1.0 + pressure * 0.04)
                            cl_revised = cl_open * (1.0 + pressure * 0.035)
                            ha_res = submit_midgley_energy_forecasts(
                                rb_open_price=rb_open,
                                rb_p50=rb_revised,
                                cl_open_price=cl_open,
                                cl_p50=cl_revised,
                                live_in_dev=live_dev
                            )
                            logger.info(f"  -> Headline Arena Intraday Benchmark Submission: {ha_res.get('status')}")
                            result["headline_arena_submission"] = ha_res
                except Exception as ha_err:
                    logger.debug(f"Notice during Headline Arena intraday submission: {ha_err}")

        return result

    def run_polling_cycle(self) -> Dict:
        """Executes a full 15-minute polling cycle across free RSS, executive social, and key mover streams."""
        logger.info("Executing 15-minute Intraday Event Monitor cycle...")
        headlines_data = self.fetch_rss_headlines()
        social_data = self.fetch_executive_social_headlines()
        if social_data:
            headlines_data.extend(social_data)
        movers_data = self.fetch_key_movers_headlines()
        if movers_data:
            headlines_data.extend(movers_data)
        geo_data = self.fetch_geopolitical_headlines()
        if geo_data:
            headlines_data.extend(geo_data)
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

    def _save_evaluated_record(self, record: Dict):
        """Appends evaluated headline record to data/evaluated_headlines.json and prunes records older than 48 hours."""
        os.makedirs("data", exist_ok=True)
        from datetime import timezone
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        evaluated = []
        if os.path.exists(EVALUATED_CACHE_FILE):
            try:
                with open(EVALUATED_CACHE_FILE, "r", encoding="utf-8") as f:
                    evaluated = json.load(f)
                    if not isinstance(evaluated, list):
                        evaluated = []
            except Exception:
                evaluated = []

        entry = {
            "timestamp": record.get("timestamp", datetime.now().isoformat()),
            "headline": record.get("headline", ""),
            "norm_headline": normalize_headline(record.get("headline", "")),
            "url": record.get("url", ""),
            "is_anomaly": record.get("is_anomaly", False),
            "source": record.get("source", "")
        }

        # Keep records within rolling 48h
        pruned = []
        for e in evaluated:
            ts_str = e.get("timestamp", "")
            if ts_str:
                try:
                    dt = datetime.fromisoformat(ts_str).replace(tzinfo=None)
                    if (now - dt).total_seconds() <= 48 * 3600.0:
                        pruned.append(e)
                except Exception:
                    pruned.append(e)
            else:
                pruned.append(e)

        pruned.append(entry)
        try:
            with open(EVALUATED_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(pruned, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to write evaluated headlines cache '{EVALUATED_CACHE_FILE}': {e}")


    def check_feed_health(self) -> Dict[str, Any]:
        """
        Diagnostic Health Check across all intraday news and event ingestion feeds (Issue #267).
        Probes RSS feeds, Executive Social Media, Key Movers, and Geopolitical feeds with latency profiling.
        """
        import time
        results = []
        overall_healthy = True

        # 1. Probe Free RSS Feeds
        for feed_url in FREE_RSS_FEEDS:
            start_t = time.time()
            feed_res = {
                "source": "RSS",
                "target": feed_url,
                "status": "UNKNOWN",
                "latency_ms": 0.0,
                "item_count": 0,
                "error": None
            }
            try:
                import urllib.request
                req = urllib.request.Request(
                    feed_url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                )
                with urllib.request.urlopen(req, timeout=8) as resp:
                    code = resp.getcode()
                    content = resp.read().decode("utf-8", errors="ignore")
                    latency = (time.time() - start_t) * 1000.0
                    item_count = 0
                    if feedparser:
                        parsed = feedparser.parse(content)
                        item_count = len(parsed.entries)
                    else:
                        item_count = len(re.findall(r'<item>|<entry>', content, re.I))
                    feed_res["status"] = "HEALTHY" if code == 200 and item_count > 0 else "DEGRADED"
                    feed_res["http_code"] = code
                    feed_res["latency_ms"] = round(latency, 2)
                    feed_res["item_count"] = item_count
            except Exception as e:
                feed_res["status"] = "FAILED"
                feed_res["error"] = str(e)
                feed_res["latency_ms"] = round((time.time() - start_t) * 1000.0, 2)
                overall_healthy = False
            results.append(feed_res)

        # 2. Probe Executive Social Feed
        start_t = time.time()
        soc_res = {"source": "Executive_Social", "target": "TruthSocial / RSS Mirror", "status": "UNKNOWN"}
        try:
            posts = self.fetch_executive_social_headlines()
            soc_res["status"] = "HEALTHY" if posts else "DEGRADED"
            soc_res["latency_ms"] = round((time.time() - start_t) * 1000.0, 2)
            soc_res["item_count"] = len(posts)
        except Exception as e:
            soc_res["status"] = "FAILED"
            soc_res["error"] = str(e)
            soc_res["latency_ms"] = round((time.time() - start_t) * 1000.0, 2)
        results.append(soc_res)

        # 3. Probe Key Movers Feed
        start_t = time.time()
        mov_res = {"source": "Key_Movers", "target": "KeyMoversFeedConnector", "status": "UNKNOWN"}
        try:
            movers = self.fetch_key_movers_headlines()
            mov_res["status"] = "HEALTHY" if movers else "DEGRADED"
            mov_res["latency_ms"] = round((time.time() - start_t) * 1000.0, 2)
            mov_res["item_count"] = len(movers)
        except Exception as e:
            mov_res["status"] = "FAILED"
            mov_res["error"] = str(e)
            mov_res["latency_ms"] = round((time.time() - start_t) * 1000.0, 2)
        results.append(mov_res)

        # 4. Probe Geopolitical Feed
        start_t = time.time()
        geo_res = {"source": "Geopolitical", "target": "GeopoliticalFeedConnector", "status": "UNKNOWN"}
        try:
            geo_items = self.fetch_geopolitical_headlines()
            geo_res["status"] = "HEALTHY" if geo_items else "DEGRADED"
            geo_res["latency_ms"] = round((time.time() - start_t) * 1000.0, 2)
            geo_res["item_count"] = len(geo_items)
        except Exception as e:
            geo_res["status"] = "FAILED"
            geo_res["error"] = str(e)
            geo_res["latency_ms"] = round((time.time() - start_t) * 1000.0, 2)
        results.append(geo_res)

        return {
            "timestamp": datetime.now().isoformat(),
            "overall_healthy": overall_healthy,
            "feeds_tested": len(results),
            "feed_details": results
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Multi-Layer Intraday Event Monitor")
    parser.add_argument("--headline", type=str, default="", help="Single headline string to process")
    parser.add_argument("--source", type=str, default="Cloudflare_Worker", help="Headline source identifier")
    parser.add_argument("--url", type=str, default="", help="Headline URL")
    parser.add_argument("--skip-dedup", action="store_true", help="Skip 24h deduplication check")
    parser.add_argument("--check-feeds", action="store_true", help="Execute feed health and latency diagnostics")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    monitor = IntradayEventMonitor()

    if args.check_feeds:
        print("\n[DIAGNOSTICS] Executing Intraday Ingestion Feed Health Diagnostics...")
        health = monitor.check_feed_health()
        health_status = "[HEALTHY]" if health['overall_healthy'] else "[DEGRADED/ISSUES]"
        print(f"\nOverall Health: {health_status}")
        print(f"Feeds Tested: {health['feeds_tested']}")
        print("\n" + "=" * 80)
        print(f"{'Source':<18} | {'Status':<10} | {'Latency':<10} | {'Items':<6} | Target / Error")
        print("-" * 80)
        for f in health["feed_details"]:
            target_desc = f.get("error") if f.get("error") else f.get("target", "")[:40]
            lat_str = f"{f.get('latency_ms', 0):.1f}ms"
            print(f"{f.get('source'):<18} | {f.get('status'):<10} | {lat_str:<10} | {f.get('item_count', 0):<6} | {target_desc}")
        print("=" * 80 + "\n")
        return health

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

