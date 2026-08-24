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
import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

FINLIGHT_BASE_URL = "https://api.finlight.me/v2/articles"
CACHE_FILE = os.path.join("data", "finlight_cache.json")
CACHE_TTL_SECONDS = 1800  # 30-minute disk cache TTL

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
    Reads cached articles from data/finlight_cache.json if valid and within TTL.
    Returns (articles: list, is_valid: bool).
    """
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
    Writes articles to data/finlight_cache.json with current timestamp.
    """
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        cache_data = {
            "timestamp": time.time(),
            "cached_at": datetime.now().isoformat(),
            "query": query,
            "count": len(articles),
            "articles": articles
        }
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
