"""
Finlight.me Real-Time Energy News Data Module (src/finlight_feed.py)
Ingests real-time financial news articles regarding oil, gasoline, refining, OPEC,
and global maritime energy chokepoints using finlight.me REST API.
"""

import os
import requests
import json
import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

FINLIGHT_BASE_URL = "https://api.finlight.me/v2/articles"

# Default targeted query strings for energy market intelligence
ENERGY_QUERIES = [
    "oil OR gasoline OR crude OR RBOB OR OPEC OR petroleum",
    "refinery OR Cushing OR outage OR inventory OR EIA",
    "Hormuz OR Red Sea OR Houthi OR Suez OR tanker OR sanctions"
]

def fetch_finlight_articles(api_key: str = None, query: str = None, page_size: int = 20) -> list:
    """
    Fetches raw articles from finlight.me POST /v2/articles endpoint.
    """
    if api_key is None:
        api_key = os.environ.get("FINLIGHT_API_KEY")
        
    if not api_key:
        logger.debug("No FINLIGHT_API_KEY set. Skipping live Finlight news fetch.")
        return []
        
    if query is None:
        query = ENERGY_QUERIES[0]

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
            logger.info(f"Successfully fetched {len(articles)} articles from finlight.me for query '{query[:30]}...'")
            return articles
        else:
            logger.warning(f"Finlight API returned HTTP {response.status_code}: {response.text[:200]}")
            return []
    except Exception as e:
        logger.warning(f"Failed to fetch articles from finlight.me: {e}")
        return []


def get_finlight_energy_events(api_key: str = None, limit_per_query: int = 15) -> pd.DataFrame:
    """
    Retrieves and structures energy news articles across all target topics.
    Returns a unified DataFrame suitable for LLM event extraction and feature fusion.
    """
    all_articles = []
    seen_links = set()

    for q in ENERGY_QUERIES:
        arts = fetch_finlight_articles(api_key=api_key, query=q, page_size=limit_per_query)
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
    print("Testing Finlight.me Energy News Feed Module...")
    df = get_finlight_energy_events()
    print(f"Total structured energy news events loaded: {len(df)}")
    if not df.empty:
        print("\nTop 5 Finlight Real-Time Articles:")
        for idx, row in df.head(5).iterrows():
            print(f"- [{row['date'].strftime('%Y-%m-%d')}] ({row['source']}) {row['title']}")
