"""
Key Market Movers Intelligence Module (src/key_movers_feed.py)
Monitors high-impact global figures influencing unleaded gas and crude oil prices:
1. Saudi Energy Minister (Prince Abdulaziz bin Salman) - OPEC+ Quotas & Surprise Cuts
2. Federal Reserve Chair (Jerome Powell) - Interest Rates, USD DXY & Macro Demand
3. US Secretary of Energy & DOE - Strategic Petroleum Reserve (SPR) Releases/Buybacks
4. IEA Executive Director (Fatih Birol) - Global Oil Demand Growth & Emergency Stock Releases
5. Russian Deputy Prime Minister (Alexander Novak) - OPEC+ Production Compliance & Exports
6. EU Sanctions & Energy Commissioners - Russian Maritime Oil Price Cap Enforcement
7. EIA Lead Analysts - Weekly Petroleum Status Report (Stock Draws/Builds)
"""

import os
import json
import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

KEY_MOVERS = {
    "Prince_Abdulaziz_bin_Salman": {
        "title": "Saudi Arabian Energy Minister",
        "institution": "Ministry of Energy / OPEC+",
        "primary_mechanism": "Surprise voluntary production cuts, OPEC+ quota enforcement, warnings to short-sellers.",
        "avg_historical_market_impact": "+2.5% to +4.8% RBOB price jump on surprise cut announcements."
    },
    "Jerome_Powell": {
        "title": "Federal Reserve Chair",
        "institution": "US Federal Reserve",
        "primary_mechanism": "FOMC interest rate policy, inflation guidance, US Dollar ($DXY$) strength impacting global oil demand.",
        "avg_historical_market_impact": "-1.2% to -2.1% demand destruction sell-off on aggressive rate hikes."
    },
    "US_Energy_Secretary_DOE": {
        "title": "US Secretary of Energy",
        "institution": "US Department of Energy (DOE)",
        "primary_mechanism": "Strategic Petroleum Reserve (SPR) emergency releases (ceiling) and SPR repurchase tender offers ($70-$79 floor).",
        "avg_historical_market_impact": "-2.5% RBOB drop on SPR release; +1.2% support on SPR refill buybacks."
    },
    "Fatih_Birol": {
        "title": "IEA Executive Director",
        "institution": "International Energy Agency (Paris)",
        "primary_mechanism": "Monthly IEA Oil Market Report (OMR) demand revisions and coordinated 31-member emergency stock drawdowns.",
        "avg_historical_market_impact": "-1.5% to +1.8% demand sentiment shift."
    },
    "Alexander_Novak": {
        "title": "Russian Deputy Prime Minister",
        "institution": "Russian Government / OPEC+ Joint Ministerial Committee",
        "primary_mechanism": "Russian crude export cut commitments, shadow fleet maritime logistics, and OPEC+ co-chair announcements.",
        "avg_historical_market_impact": "+1.8% to +3.2% crude/gasoline rally on export reduction announcements."
    },
    "EU_Sanctions_Commissioners": {
        "title": "EU Climate & Energy Commissioners",
        "institution": "European Commission (Brussels)",
        "primary_mechanism": "G7/EU $60/bbl Russian crude price cap enforcement, maritime insurance bans, and EU ETS carbon tariffs.",
        "avg_historical_market_impact": "+1.5% transatlantic refined product spread widening."
    }
}

HISTORICAL_KEY_MOVERS_EVENTS = [
    {
        "date": "2022-03-31",
        "entity": "US_Energy_Secretary_DOE",
        "person": "Jennifer Granholm / Biden Admin",
        "headline": "US announces historic 180 million barrel Strategic Petroleum Reserve (SPR) release over 6 months; gasoline futures drop.",
        "impact_category": "SPR_Release",
        "category": "SPR_Release",
        "source": "US Department of Energy / Executive Action",
        "market_reaction_pct": -3.85
    },
    {
        "date": "2023-06-04",
        "entity": "Prince_Abdulaziz_bin_Salman",
        "person": "Prince Abdulaziz bin Salman (Saudi Arabia)",
        "headline": "Saudi Arabia announces solo 'Saudi Lollipop' voluntary oil production cut of 1.0 million barrels per day starting July; crude surges +4%.",
        "impact_category": "OPEC_Surprise_Cut",
        "category": "OPEC_Surprise_Cut",
        "source": "Saudi Ministry of Energy / OPEC+",
        "market_reaction_pct": 4.12
    },
    {
        "date": "2023-07-26",
        "entity": "Jerome_Powell",
        "person": "Jerome Powell (Fed Chair)",
        "headline": "Fed raises interest rates to 22-year high of 5.50%; Powell emphasizes data-dependent stance, dampening energy demand outlook.",
        "impact_category": "Fed_Rate_Hike",
        "category": "Fed_Rate_Hike",
        "source": "US Federal Reserve FOMC",
        "market_reaction_pct": -1.15
    },
    {
        "date": "2023-10-19",
        "entity": "US_Energy_Secretary_DOE",
        "person": "US Department of Energy",
        "headline": "US DOE solicits offers to buy back 6 million barrels of crude for Strategic Petroleum Reserve refill at $79/bbl target price.",
        "impact_category": "SPR_Refill_Floor",
        "category": "SPR_Refill_Floor",
        "source": "US Department of Energy SPR Office",
        "market_reaction_pct": 1.45
    },
    {
        "date": "2024-02-15",
        "entity": "Fatih_Birol",
        "person": "Fatih Birol (IEA)",
        "headline": "IEA trims 2024 global oil demand growth forecast by 100,000 bpd citing slowing Chinese industrial activity.",
        "impact_category": "IEA_Demand_Downgrade",
        "category": "IEA_Demand_Downgrade",
        "source": "International Energy Agency Oil Market Report",
        "market_reaction_pct": -1.38
    },
    {
        "date": "2024-06-03",
        "entity": "Alexander_Novak",
        "person": "Alexander Novak (Russia)",
        "headline": "Russia promises to compensate for overproduction in Q1 by deepening crude export cuts through Q3 2024.",
        "impact_category": "Russian_Export_Cut",
        "category": "Russian_Export_Cut",
        "source": "Russian Ministry of Energy / OPEC+ JMMC",
        "market_reaction_pct": 1.90
    }
]


class KeyMoversFeedConnector:
    """
    Key Market Movers Intelligence Connector (Issue #270).
    Monitors public RSS feeds for breaking statements from central bankers,
    OPEC oil ministers, DOE leadership, and energy agency directors.
    """
    def __init__(self):
        self.is_free_alternative = True
        self.cost_per_query = 0.0
        self.keywords = {
            "Prince_Abdulaziz_bin_Salman": ["abdulaziz", "saudi energy minister", "saudi oil minister"],
            "Jerome_Powell": ["jerome powell", "powell fed", "federal reserve rate"],
            "US_Energy_Secretary_DOE": ["strategic petroleum reserve", "doe spr", "energy secretary granholm", "wright energy secretary"],
            "Fatih_Birol": ["fatih birol", "iea director", "iea oil market report"],
            "Alexander_Novak": ["alexander novak", "russia deputy prime minister oil"]
        }

    def fetch_live_events(self, feed_urls: list = None) -> list:
        """
        Polls live public RSS feeds for breaking statements from top energy policymakers,
        with 15-minute lookup caching.
        """
        from src.lookup_cache import global_cache
        cache_key = "key_movers:live_events"
        cached = global_cache.get(cache_key)
        if cached and "events" in cached:
            return cached["events"]

        if feed_urls is None:
            feed_urls = [
                "https://news.google.com/rss/search?q=Saudi+Energy+Minister+OR+Strategic+Petroleum+Reserve+OR+Jerome+Powell+interest+rate&hl=en-US&gl=US&ceid=US:en"
            ]

        live_events = []
        try:
            import feedparser
        except ImportError:
            feedparser = None

        if feedparser:
            for url in feed_urls:
                try:
                    feed = feedparser.parse(url)
                    for entry in feed.entries[:10]:
                        title = entry.get("title", "").strip()
                        title_lower = title.lower()
                        
                        matched_entity = None
                        matched_person = "Energy Official"
                        for entity_key, kw_list in self.keywords.items():
                            if any(kw in title_lower for kw in kw_list):
                                matched_entity = entity_key
                                matched_person = entity_key.replace("_", " ")
                                break

                        if matched_entity:
                            pub_dt = datetime.now()
                            if hasattr(entry, "published_parsed") and entry.published_parsed:
                                try:
                                    pub_dt = datetime(*entry.published_parsed[:6])
                                except Exception:
                                    pass

                            event_obj = {
                                "date": pub_dt.strftime("%Y-%m-%d"),
                                "entity": matched_entity,
                                "person": matched_person,
                                "headline": title,
                                "impact_category": f"{matched_entity}_Statement",
                                "category": f"{matched_entity}_Statement",
                                "source": f"Key Movers Live RSS ({matched_entity})",
                                "market_reaction_pct": 0.0
                            }
                            live_events.append(event_obj)
                            self.save_key_movers_vintage_record(event_obj)
                except Exception as e:
                    logger.debug(f"Could not poll key movers feed '{url}': {e}")

        # Cache in global_cache (15 minutes TTL)
        try:
            global_cache.set(cache_key, {"events": live_events}, ttl_seconds=900)
        except Exception:
            pass

        return live_events

    def get_combined_feed(self, include_live: bool = True) -> pd.DataFrame:
        base_events = None
        try:
            from src.benchmark_updater import load_historical_benchmark
            loaded = load_historical_benchmark("key_movers")
            if loaded and isinstance(loaded, list):
                base_events = list(loaded)
        except Exception:
            pass

        if base_events is None:
            base_events = list(HISTORICAL_KEY_MOVERS_EVENTS)

        all_events = list(base_events)
        if include_live:
            try:
                live_events = self.fetch_live_events()
                if live_events:
                    all_events.extend(live_events)
                    try:
                        from src.benchmark_updater import save_historical_benchmark
                        save_historical_benchmark("key_movers", all_events)
                    except Exception:
                        pass
            except Exception as e:
                logger.debug(f"Live key movers fetch skipped: {e}")

        df = pd.DataFrame(all_events)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df = df.drop_duplicates(subset=['date', 'headline']).sort_values('date').reset_index(drop=True)
        return df

    @staticmethod
    def save_key_movers_vintage_record(record: dict, filepath: str = os.path.join("data", "key_movers_vintages.json")) -> None:
        """
        Saves or appends a key market movers event snapshot to persistent vintage storage (Issue #270).
        """
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            vintages = []
            if os.path.exists(filepath):
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        vintages = json.load(f)
                except Exception:
                    vintages = []

            rec_copy = dict(record)
            if "as_of" not in rec_copy:
                rec_copy["as_of"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if "valid_date" not in rec_copy:
                rec_copy["valid_date"] = str(rec_copy.get("date", datetime.now().strftime("%Y-%m-%d")))[:10]

            vintages = [v for v in vintages if not (v.get("date") == rec_copy.get("date") and v.get("headline") == rec_copy.get("headline"))]
            vintages.append(rec_copy)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(json.dumps(vintages, indent=2))
        except Exception as e:
            logger.warning(f"Could not persist key movers vintage record: {e}")

    @staticmethod
    def get_key_movers_vintages_as_of(target_as_of: str = None, filepath: str = os.path.join("data", "key_movers_vintages.json")) -> list:
        """
        Retrieves key market mover observations published on or before target_as_of (Issue #270).
        """
        try:
            if not os.path.exists(filepath):
                return []
            with open(filepath, "r", encoding="utf-8") as f:
                vintages = json.load(f)
            if not target_as_of:
                return vintages
            
            target_str = str(target_as_of)
            filtered = []
            for v in vintages:
                as_of_val = v.get("as_of", "")
                if as_of_val <= target_str or as_of_val[:10] <= target_str[:10]:
                    filtered.append(v)
            return filtered
        except Exception as e:
            logger.warning(f"Could not read key movers vintages as of {target_as_of}: {e}")
            return []

    def fetch_key_movers_events(self, force_refresh: bool = False) -> list:
        """
        Fetches combined key movers events with caching.
        """
        from src.lookup_cache import global_cache
        cache_key = "key_movers:events:all"
        if not force_refresh:
            cached = global_cache.get(cache_key)
            if cached and isinstance(cached, dict) and "events" in cached:
                return cached["events"]

        df = self.get_combined_feed(include_live=True)
        if not df.empty:
            df_export = df.copy()
            if 'date' in df_export.columns:
                df_export['date'] = df_export['date'].astype(str).str[:10]
            events = df_export.to_dict(orient="records")
        else:
            events = list(HISTORICAL_KEY_MOVERS_EVENTS)
        global_cache.set(cache_key, {"events": events}, ttl_seconds=900)
        return events

    def fetch_key_movers_headlines(self, force_refresh: bool = False) -> list:
        """
        Alias for fetch_key_movers_events to support unified benchmark updater interface.
        """
        return self.fetch_key_movers_events(force_refresh=force_refresh)


def get_key_movers_event_feed(include_live: bool = True) -> pd.DataFrame:
    """
    Returns high-impact key market movers dataset via KeyMoversFeedConnector.
    """
    connector = KeyMoversFeedConnector()
    return connector.get_combined_feed(include_live=include_live)


def fetch_key_movers_headlines() -> list:
    """
    Convenience helper extracting breaking key mover headlines for intraday event monitoring.
    """
    connector = KeyMoversFeedConnector()
    events = connector.fetch_key_movers_events()
    return [ev["headline"] for ev in events if "headline" in ev]


if __name__ == "__main__":
    df = get_key_movers_event_feed()
    print(f"Loaded {len(df)} Key Market Movers Events.")
    print(json.dumps(KEY_MOVERS, indent=2))
