"""
Finlight.me Real-Time Energy News Data Module (src/finlight_feed.py)
Ingests real-time financial news articles regarding oil, gasoline, refining, OPEC,
and global maritime energy chokepoints using finlight.me REST API.

Optimized for hourly workflow execution:
- Consolidates queries into a single unified search expression (1 call per run).
- Disk-backed response caching at data/finlight_cache.json with 30-minute TTL (1800s).
- Graceful HTTP 429 / 403 rate limit & quota fallback to cached articles or NLP lexicon.
"""

import os
import time
import requests
import json
import hashlib
import pandas as pd
from datetime import datetime
from typing import Tuple, Dict, Any, List
import logging
from src.lookup_cache import global_cache

logger = logging.getLogger(__name__)

FINLIGHT_BASE_URL = "https://api.finlight.me/v2/articles"
CACHE_FILE = os.path.join("data", "finlight_cache.json")
CACHE_TTL_SECONDS = 1800  # 30-minute disk cache TTL
QUOTA_FILE = os.path.join("data", "finlight_quota.json")
MAX_MONTHLY_CALLS = 150  # Hard safety cap (out of 250 free tier allowance)
MAX_DAILY_CALLS = 10     # Soft daily cap to prevent burst exhaustion


def _check_and_increment_quota() -> Tuple[bool, dict]:
    """
    Checks data/finlight_quota.json and global multi-tier cache ledger against
    MAX_MONTHLY_CALLS and MAX_DAILY_CALLS caps.
    If under limits, increments usage and returns (True, status).
    If limit reached, returns (False, status) to trigger the safety valve intercept.
    """
    os.makedirs("data", exist_ok=True)
    now = datetime.now()
    month_key = now.strftime("%Y-%m")
    day_key = now.strftime("%Y-%m-%d")

    data = {
        "current_month": month_key,
        "monthly_calls": 0,
        "daily_calls": {},
        "last_reset": now.isoformat()
    }

    if os.path.exists(QUOTA_FILE):
        try:
            with open(QUOTA_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if loaded.get("current_month") == month_key:
                    data = loaded
        except Exception as e:
            logger.warning(f"Could not read quota ledger '{QUOTA_FILE}': {e}")

    # Check shared edge cache ledger and merge higher count
    edge_ledger = global_cache.get_quota_ledger("finlight")
    if edge_ledger and edge_ledger.get("current_month") == month_key:
        edge_monthly = edge_ledger.get("monthly_calls", 0)
        edge_daily = edge_ledger.get("daily_calls", {}).get(day_key, 0)
        data["monthly_calls"] = max(data.get("monthly_calls", 0), edge_monthly)
        if "daily_calls" not in data or not isinstance(data["daily_calls"], dict):
            data["daily_calls"] = {}
        data["daily_calls"][day_key] = max(data["daily_calls"].get(day_key, 0), edge_daily)

    monthly_calls = data.get("monthly_calls", 0)
    today_calls = data.get("daily_calls", {}).get(day_key, 0)

    if monthly_calls >= MAX_MONTHLY_CALLS or today_calls >= MAX_DAILY_CALLS:
        logger.warning(
            f"🚨 FINLIGHT API SAFETY VALVE TRIPPED! "
            f"Monthly calls: {monthly_calls}/{MAX_MONTHLY_CALLS}, Today: {today_calls}/{MAX_DAILY_CALLS}. "
            f"Blocking HTTP request to preserve free tier quota."
        )
        return False, {
            "allowed": False,
            "monthly_calls": monthly_calls,
            "today_calls": today_calls,
            "max_monthly": MAX_MONTHLY_CALLS,
            "max_daily": MAX_DAILY_CALLS
        }

    # Increment quota
    new_monthly = monthly_calls + 1
    new_today = today_calls + 1
    data["monthly_calls"] = new_monthly
    if "daily_calls" not in data or not isinstance(data["daily_calls"], dict):
        data["daily_calls"] = {}
    data["daily_calls"][day_key] = new_today
    data["last_call"] = now.isoformat()

    try:
        with open(QUOTA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.warning(f"Could not write quota ledger '{QUOTA_FILE}': {e}")

    # Sync to edge cache ledger
    global_cache.update_quota_ledger("finlight", new_monthly, new_today, month_key, day_key)

    return True, {
        "allowed": True,
        "monthly_calls": new_monthly,
        "today_calls": new_today,
        "max_monthly": MAX_MONTHLY_CALLS,
        "max_daily": MAX_DAILY_CALLS
    }


def get_finlight_quota_status() -> dict:
    """Returns current Finlight API quota usage and safety valve status."""
    now = datetime.now()
    month_key = now.strftime("%Y-%m")
    day_key = now.strftime("%Y-%m-%d")
    monthly_calls = 0
    today_calls = 0

    if os.path.exists(QUOTA_FILE):
        try:
            with open(QUOTA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("current_month") == month_key:
                    monthly_calls = data.get("monthly_calls", 0)
                    today_calls = data.get("daily_calls", {}).get(day_key, 0)
        except Exception:
            pass

    edge_ledger = global_cache.get_quota_ledger("finlight")
    if edge_ledger and edge_ledger.get("current_month") == month_key:
        monthly_calls = max(monthly_calls, edge_ledger.get("monthly_calls", 0))
        today_calls = max(today_calls, edge_ledger.get("daily_calls", {}).get(day_key, 0))

    return {
        "month": month_key,
        "monthly_calls": monthly_calls,
        "max_monthly_calls": MAX_MONTHLY_CALLS,
        "monthly_quota_remaining": max(0, MAX_MONTHLY_CALLS - monthly_calls),
        "today_calls": today_calls,
        "max_daily_calls": MAX_DAILY_CALLS,
        "safety_valve_active": (monthly_calls >= MAX_MONTHLY_CALLS or today_calls >= MAX_DAILY_CALLS)
    }


def is_trading_hours(now_dt: datetime = None) -> bool:
    """
    Checks if current time is within US Energy Commodity Trading Hours
    (08:00 AM - 05:00 PM EST, Monday through Friday).
    """
    if now_dt is None:
        now_dt = datetime.now()
    if now_dt.weekday() >= 5:  # Saturday/Sunday
        return False
    hour = now_dt.hour
    return 8 <= hour < 17


def fetch_finlight_on_demand(api_key: str = None, query: str = None) -> list:
    """
    On-demand forced fetch triggered by high-impact anomaly detection events.
    Bypasses disk cache to fetch real-time breaking metadata.
    """
    logger.info("⚡ On-demand Finlight.me API fetch triggered by intraday shock evaluator.")
    return fetch_finlight_articles(api_key=api_key, query=query, force_refresh=True)


# Consolidated single targeted query string covering all energy market intelligence topics
UNIFIED_ENERGY_QUERY = (
    "(oil OR gasoline OR crude OR RBOB OR OPEC OR petroleum OR "
    "refinery OR Cushing OR outage OR inventory OR EIA OR "
    "Hormuz OR Red Sea OR Houthi OR Suez OR tanker OR sanctions OR Venezuela)"
)

# Retained for backwards compatibility (single consolidated query list)
ENERGY_QUERIES = [UNIFIED_ENERGY_QUERY]


def _read_cache(ttl_seconds: int = CACHE_TTL_SECONDS) -> tuple:
    """
    Reads cached articles from global_cache or data/finlight_cache.json if valid and within TTL.
    Returns (articles: list, is_valid: bool).
    """
    # Check multi-tier global_cache first
    cached_edge = global_cache.get("finlight:latest_articles")
    if cached_edge:
        articles = cached_edge.get("articles", [])
        logger.info(f"Loaded {len(articles)} articles from multi-tier lookup cache.")
        return articles, True

    if not os.path.exists(CACHE_FILE):
        return [], False

    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        cache_time = data.get("timestamp", 0)
        cache_age = time.time() - cache_time

        if cache_age < ttl_seconds:
            articles = data.get("articles", [])
            logger.info(f"Loaded {len(articles)} articles from disk cache (cache age: {int(cache_age)}s / TTL: {ttl_seconds}s).")
            return articles, True
        else:
            logger.debug(f"Disk cache expired (cache age: {int(cache_age)}s > TTL: {ttl_seconds}s).")
            return data.get("articles", []), False
    except Exception as e:
        logger.warning(f"Failed to read disk cache '{CACHE_FILE}': {e}")
        return [], False


def _write_cache(articles: list, query: str = UNIFIED_ENERGY_QUERY):
    """
    Writes articles to data/finlight_cache.json and multi-tier global_cache with current timestamp.
    """
    cache_data = {
        "timestamp": time.time(),
        "cached_at": datetime.now().isoformat(),
        "query": query,
        "count": len(articles),
        "articles": articles
    }
    # Save to multi-tier lookup cache
    global_cache.set("finlight:latest_articles", cache_data, ttl_seconds=CACHE_TTL_SECONDS)

    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2)
        logger.debug(f"Saved {len(articles)} articles to disk cache '{CACHE_FILE}'.")
    except Exception as e:
        logger.warning(f"Failed to write disk cache '{CACHE_FILE}': {e}")


def fetch_finlight_articles(
    api_key: str = None,
    query: str = None,
    page_size: int = 40,
    force_refresh: bool = False,
    ttl_seconds: int = CACHE_TTL_SECONDS
) -> list:
    """
    Fetches raw articles from finlight.me POST /v2/articles endpoint with disk caching & rate-limit fallback.
    Intercepted by hard Safety Valve quota ledger to prevent exceeding free tier limits.
    """
    if query is None or query in ENERGY_QUERIES:
        query = UNIFIED_ENERGY_QUERY

    # Check disk cache unless force_refresh is True
    if not force_refresh:
        cached_articles, is_valid = _read_cache(ttl_seconds=ttl_seconds)
        if is_valid:
            return cached_articles

    if api_key is None:
        api_key = os.environ.get("FINLIGHT_API_KEY")

    if not api_key:
        logger.debug("No FINLIGHT_API_KEY set. Checking disk cache or skipping live Finlight fetch.")
        cached_articles, _ = _read_cache(ttl_seconds=86400 * 7)  # allow up to 7-day stale fallback
        return cached_articles

    # Check Hard Quota Safety Valve Ledger
    allowed, quota_status = _check_and_increment_quota()
    if not allowed:
        logger.warning("Finlight API safety valve active (quota cap reached). Falling back to disk cache.")
        cached_articles, _ = _read_cache(ttl_seconds=86400 * 7)
        return cached_articles


    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "X-API-KEY": api_key
    }

    payload = {
        "query": query,
        "pageSize": min(page_size, 50)
    }

    try:
        response = requests.post(FINLIGHT_BASE_URL, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            articles = data.get("articles", [])
            logger.info(f"Successfully fetched {len(articles)} live articles from finlight.me for query '{query[:30]}...'")
            _write_cache(articles, query=query)
            return articles
        elif response.status_code == 429:
            logger.warning("Finlight API rate limit exceeded (HTTP 429). Falling back to disk cache.")
            cached_articles, _ = _read_cache(ttl_seconds=86400 * 7)
            return cached_articles
        elif response.status_code == 403:
            logger.warning("Finlight API quota exceeded or unauthorized (HTTP 403). Falling back to disk cache.")
            cached_articles, _ = _read_cache(ttl_seconds=86400 * 7)
            return cached_articles
        else:
            logger.warning(f"Finlight API returned HTTP {response.status_code}: {response.text[:200]}")
            cached_articles, _ = _read_cache(ttl_seconds=86400 * 7)
            return cached_articles
    except Exception as e:
        logger.warning(f"Failed to fetch articles from finlight.me: {e}. Falling back to disk cache.")
        cached_articles, _ = _read_cache(ttl_seconds=86400 * 7)
        return cached_articles


def get_finlight_energy_events(
    api_key: str = None,
    limit_per_query: int = 30,
    force_refresh: bool = False
) -> pd.DataFrame:
    """
    Retrieves and structures energy news articles across consolidated energy topics.
    Returns a unified DataFrame suitable for LLM event extraction and feature fusion.
    """
    all_articles = []
    seen_links = set()

    arts = fetch_finlight_articles(
        api_key=api_key,
        query=UNIFIED_ENERGY_QUERY,
        page_size=limit_per_query,
        force_refresh=force_refresh
    )

    for art in arts:
        link = art.get("link")
        if link and link not in seen_links:
            seen_links.add(link)
            pub_date = art.get("publishDate")
            try:
                dt = pd.to_datetime(pub_date).strftime("%Y-%m-%d") if pub_date else datetime.now().strftime("%Y-%m-%d")
            except Exception:
                dt = datetime.now().strftime("%Y-%m-%d")

            title = art.get("title", "").strip()
            summary = art.get("summary", "").strip()

            headline = title
            if summary and len(summary) > 10 and not summary.startswith(title):
                headline = f"{title} - {summary[:150]}"

            all_articles.append({
                "date": dt,
                "headline": headline,
                "title": title,
                "summary": summary,
                "source": art.get("source", "Finlight"),
                "category": "Finlight_Energy_News",
                "url": link,
                "categories": art.get("categories", [])
            })

    if not all_articles:
        return pd.DataFrame(columns=["date", "headline", "title", "summary", "source", "category", "url", "categories"])

    df = pd.DataFrame(all_articles)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(by="date", ascending=False).reset_index(drop=True)
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Testing Finlight.me Energy News Feed Module (Optimized)...")
    df = get_finlight_energy_events()
    print(f"Total structured energy news events loaded: {len(df)}")
    if not df.empty:
        print("\nTop 5 Finlight Articles:")
        for idx, row in df.head(5).iterrows():
            print(f"- [{row['date'].strftime('%Y-%m-%d')}] ({row['source']}) {row['title']}")
