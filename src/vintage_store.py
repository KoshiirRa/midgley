"""
Bitemporal Vintage Store Module (src/vintage_store.py)

Unifies all 21 external data feed snapshots (EIA, CFTC, FERC, NOAA, AQI, USGS, Baker Hughes, Census, etc.)
into the centralized database `data_vintages` table.
Guarantees point-in-time querying, zero lookahead leakage, and data quality classification.
"""

import os
import json
import hashlib
import logging
from datetime import datetime, date, timedelta, timezone
from typing import Dict, Any, Optional, List, Tuple, Union
from src.db.client import get_db

logger = logging.getLogger(__name__)

QUALITY_LIVE = "LIVE"
QUALITY_CACHED = "CACHED"
QUALITY_BENCHMARK = "BENCHMARK"
QUALITY_STALE = "STALE"
QUALITY_SYNTHETIC = "SYNTHETIC"


class VintageStore:
    """
    Standardized Bitemporal Vintage Store.
    """

    def __init__(self, db=None):
        self.db = db or get_db()

    def generate_vintage_id(self, feed: str, entity: str, obs_date: str, published_at: str) -> str:
        """Generates deterministic SHA-256 primary key for observation vintage."""
        raw = f"{feed.strip().lower()}_{entity.strip().lower()}_{obs_date.strip()}_{published_at.strip()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]

    def record_observation(
        self,
        feed: str,
        entity: str,
        obs_date: Union[str, date, datetime],
        values: Dict[str, Any],
        published_at: Optional[Union[str, datetime]] = None,
        fetched_at: Optional[Union[str, datetime]] = None,
        quality: str = QUALITY_LIVE
    ) -> str:
        """
        Records or updates an observation vintage in the database.
        """
        obs_str = obs_date.strftime("%Y-%m-%d") if isinstance(obs_date, (date, datetime)) else str(obs_date)[:10]
        
        now_utc = datetime.now(timezone.utc).isoformat()
        pub_str = published_at.isoformat() if isinstance(published_at, datetime) else (str(published_at) if published_at else now_utc)
        fetch_str = fetched_at.isoformat() if isinstance(fetched_at, datetime) else (str(fetched_at) if fetched_at else now_utc)

        v_id = self.generate_vintage_id(feed, entity, obs_str, pub_str)
        values_json = json.dumps(values)

        sql = """
        INSERT INTO data_vintages (vintage_id, feed, entity, obs_date, published_at, fetched_at, quality, values_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(vintage_id) DO UPDATE SET
            values_json = excluded.values_json,
            fetched_at = excluded.fetched_at,
            quality = excluded.quality;
        """
        self.db.execute(sql, (v_id, feed, entity, obs_str, pub_str, fetch_str, quality, values_json))
        return v_id

    def query_as_of(
        self,
        feed: str,
        entity: str,
        target_date: Union[str, date, datetime],
        as_of_time: Optional[Union[str, datetime]] = None,
        allow_quality: Tuple[str, ...] = (QUALITY_LIVE, QUALITY_CACHED, QUALITY_BENCHMARK),
        publication_lag_days: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Point-in-Time Query: Returns the most recent observation state published on or before as_of_time
        for the given observation date.
        """
        target_str = target_date.strftime("%Y-%m-%d") if isinstance(target_date, (date, datetime)) else str(target_date)[:10]
        
        now_utc = datetime.now(timezone.utc).isoformat()
        as_of_str = as_of_time.isoformat() if isinstance(as_of_time, datetime) else (str(as_of_time) if as_of_time else now_utc)

        # Apply publication lag if configured
        if publication_lag_days > 0 and as_of_time:
            if isinstance(as_of_time, str):
                try:
                    dt = datetime.fromisoformat(as_of_time.replace("Z", "+00:00"))
                    as_of_str = (dt - timedelta(days=publication_lag_days)).isoformat()
                except Exception:
                    pass
            elif isinstance(as_of_time, datetime):
                as_of_str = (as_of_time - timedelta(days=publication_lag_days)).isoformat()

        placeholders = ",".join(["?"] * len(allow_quality))
        sql = f"""
        SELECT values_json, quality, published_at, obs_date
        FROM data_vintages
        WHERE feed = ?
          AND entity = ?
          AND obs_date <= ?
          AND published_at <= ?
          AND quality IN ({placeholders})
        ORDER BY obs_date DESC, published_at DESC
        LIMIT 1;
        """
        params = [feed, entity, target_str, as_of_str] + list(allow_quality)
        rows = self.db.execute(sql, tuple(params))
        if not rows:
            return None

        row = rows[0]
        try:
            val_dict = json.loads(row["values_json"])
            if isinstance(val_dict, dict):
                val_dict["_provenance_quality"] = row["quality"]
                val_dict["_provenance_published_at"] = row["published_at"]
                val_dict["_provenance_obs_date"] = row["obs_date"]
            return val_dict
        except Exception as e:
            logger.error(f"Failed to parse vintage values_json: {e}")
            return None

    def get_all_vintages(self, feed: str, entity: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns all recorded vintages for a feed."""
        if entity:
            sql = "SELECT * FROM data_vintages WHERE feed = ? AND entity = ? ORDER BY obs_date ASC;"
            return self.db.execute(sql, (feed, entity))
        sql = "SELECT * FROM data_vintages WHERE feed = ? ORDER BY obs_date ASC;"
        return self.db.execute(sql, (feed,))


# Global VintageStore Singleton
vintage_store = VintageStore()
