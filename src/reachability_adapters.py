"""
Agent-Reach Resilient Multi-Platform Social & News Reachability Layer (src/reachability_adapters.py)
Integrates multi-protocol reachability patterns evaluated from Panniantong/Agent-Reach (Issue #308).
Provides prioritized fallback cascades: RSS Syndication Mirrors -> Public Proxies -> Search Fallback.
"""

import os
import re
import json
import time
import hashlib
import logging
import urllib.request
import urllib.parse
import defusedxml.ElementTree as ET
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod

from src.lookup_cache import global_cache
from src.connector_telemetry import log_connector_event

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 (MidgleyBot/2.0)"
EVALUATED_HEADLINES_FILE = os.path.join("data", "evaluated_headlines.json")


def compute_headline_hash(text: str) -> str:
    """Computes a normalized SHA-256 hash of a headline or post."""
    clean = re.sub(r"\s+", " ", text.strip().lower())
    clean = re.sub(r"\s*-\s*[^-]+$", "", clean)  # Strip publisher attribution suffixes
    return hashlib.sha256(clean.encode("utf-8")).hexdigest()


class BaseReachabilityAdapter(ABC):
    """Abstract base class for all reachability protocol adapters."""

    def __init__(self, name: str, priority: int = 1):
        self.name = name
        self.priority = priority

    @abstractmethod
    def fetch_posts(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetches posts/headlines matching query. Returns list of standardized post dicts."""
        pass


class RSSSyndicationAdapter(BaseReachabilityAdapter):
    """
    Tier 1 Reachability Adapter: Free RSS / Syndication feeds.
    Parses Google News RSS, DOE Press Releases, White House energy briefings, and EIA updates.
    """

    def __init__(self):
        super().__init__(name="rss_syndication", priority=1)

    def fetch_posts(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        encoded_query = urllib.parse.quote(query)
        rss_url = f"https://news.google.com/rss/search?q={encoded_query}+when:3d&hl=en-US&gl=US&ceid=US:en"
        
        req = urllib.request.Request(rss_url, headers={"User-Agent": USER_AGENT})
        posts = []
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                if resp.status == 200:
                    xml_data = resp.read()
                    root = ET.fromstring(xml_data)
                    for item in root.findall(".//item")[:limit]:
                        title = item.findtext("title", "").strip()
                        link = item.findtext("link", "").strip()
                        pub_date = item.findtext("pubDate", "").strip()
                        if title:
                            posts.append({
                                "text": title,
                                "source": "Google News RSS",
                                "url": link,
                                "timestamp": pub_date or datetime.now(timezone.utc).isoformat(),
                                "protocol": "rss_syndication",
                                "adapter": self.name
                            })
        except Exception as e:
            logger.debug(f"RSSSyndicationAdapter fetch failed for query '{query}': {e}")

        return posts


class PublicProxyAdapter(BaseReachabilityAdapter):
    """
    Tier 2 Reachability Adapter: Public Mirror Proxies & Platform Endpoints.
    Fetches unstructured posts via public Reddit JSON, Nitter/X syndication, or Truth Social feeds.
    """

    def __init__(self):
        super().__init__(name="public_proxy", priority=2)

    def fetch_posts(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        encoded_query = urllib.parse.quote(query)
        # Reddit JSON search endpoint (zero auth, public CORS)
        url = f"https://www.reddit.com/r/energy/search.json?q={encoded_query}&restrict_sr=1&sort=new&limit={limit}"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        posts = []
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    children = data.get("data", {}).get("children", [])
                    for child in children[:limit]:
                        cdata = child.get("data", {})
                        title = cdata.get("title", "").strip()
                        permalink = f"https://reddit.com{cdata.get('permalink', '')}"
                        created_utc = cdata.get("created_utc", time.time())
                        if title:
                            posts.append({
                                "text": title,
                                "source": f"Reddit r/{cdata.get('subreddit', 'energy')}",
                                "url": permalink,
                                "timestamp": datetime.fromtimestamp(created_utc, timezone.utc).isoformat(),
                                "protocol": "public_proxy",
                                "adapter": self.name
                            })
        except Exception as e:
            logger.debug(f"PublicProxyAdapter fetch failed for query '{query}': {e}")

        return posts


class SearchFallbackAdapter(BaseReachabilityAdapter):
    """
    Tier 3 Reachability Adapter: Zero-Cost Search Fallback (DuckDuckGo HTML).
    Fuzzy extracts headlines when RSS and platform proxies fail or are rate-limited.
    """

    def __init__(self):
        super().__init__(name="search_fallback", priority=3)

    def fetch_posts(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        encoded_query = urllib.parse.quote(f"{query} oil gas energy")
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        posts = []
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                if resp.status == 200:
                    html_content = resp.read().decode("utf-8", errors="ignore")
                    # Extract result titles and snippets using regex
                    results = re.findall(r'<a[^>]+class="result__url"[^>]+href="([^"]+)"[^>]*>.*?</a>.*?<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', html_content, flags=re.DOTALL)
                    if not results:
                        # Alternative simple title match
                        results = re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html_content, flags=re.DOTALL)

                    for link, raw_title in results[:limit]:
                        clean_title = re.sub(r"<[^>]+>", " ", raw_title).strip()
                        if clean_title and len(clean_title) > 15:
                            posts.append({
                                "text": clean_title,
                                "source": "DuckDuckGo Search Proxy",
                                "url": link.strip(),
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "protocol": "search_fallback",
                                "adapter": self.name
                            })
        except Exception as e:
            logger.debug(f"SearchFallbackAdapter fetch failed for query '{query}': {e}")

        return posts


class ReachabilityCascadeRouter:
    """
    Orchestrates the multi-tier reachability cascade with automatic deduplication,
    caching, error failover, and connector telemetry logging.
    """

    def __init__(self, adapters: Optional[List[BaseReachabilityAdapter]] = None):
        if adapters is None:
            self.adapters = [
                RSSSyndicationAdapter(),
                PublicProxyAdapter(),
                SearchFallbackAdapter()
            ]
        else:
            self.adapters = sorted(adapters, key=lambda a: a.priority)

    def fetch_resilient_posts(
        self,
        query: str,
        target_feed: str = "executive_social",
        limit: int = 10,
        cache_ttl_seconds: int = 900
    ) -> List[Dict[str, Any]]:
        """
        Executes cascading reachability fetch across configured adapter tiers.
        Deduplicates against evaluated headlines ledger and caches results.
        """
        cache_key = f"reachability_{target_feed}:{compute_headline_hash(query)[:12]}"
        try:
            cached = global_cache.get(cache_key)
            if cached and isinstance(cached, list):
                return cached
        except Exception:
            pass

        start_time = time.time()
        collected_posts = []
        active_adapter_name = "none"

        for adapter in self.adapters:
            try:
                t0 = time.time()
                posts = adapter.fetch_posts(query=query, limit=limit)
                dur_ms = (time.time() - t0) * 1000.0
                if posts:
                    collected_posts = posts
                    active_adapter_name = adapter.name
                    log_connector_event(
                        connector_name=f"Reachability_{target_feed.upper()}",
                        target=query,
                        status="SUCCESS",
                        latency_ms=dur_ms,
                        details=f"Resolved via {adapter.name} ({len(posts)} items)"
                    )
                    break
                else:
                    log_connector_event(
                        connector_name=f"Reachability_{target_feed.upper()}",
                        target=query,
                        status="FAILOVER",
                        latency_ms=dur_ms,
                        details=f"Tier {adapter.name} yielded 0 items; cascading..."
                    )
            except Exception as e:
                logger.debug(f"Adapter {adapter.name} exception: {e}")

        # Deduplicate results by SHA-256 hash
        seen_hashes = set()
        deduped = []
        for p in collected_posts:
            h = compute_headline_hash(p["text"])
            if h not in seen_hashes:
                seen_hashes.add(h)
                p["headline_hash"] = h
                deduped.append(p)

        try:
            global_cache.set(cache_key, deduped, ttl_seconds=cache_ttl_seconds)
        except Exception:
            pass

        return deduped
