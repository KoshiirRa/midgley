"""
Unified Historical Benchmark & Fallback Refresh Orchestrator (src/benchmark_updater.py)
Automates the weekly refresh and persistent storage of historical baseline datasets
and offline fallbacks across all Midgley data ingestion feeds and quantitative modules (Issue #297).

Runs during the automated Saturday morning weekly model performance review workflow
(.github/workflows/weekly_model_review.yml) to ensure offline fallbacks reflect fresh
Friday market closes without requiring manual code edits.
"""

import os
import json
import logging
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

BENCHMARK_STORAGE_DIR = "data"


def save_historical_benchmark(key: str, data: Any, filename: Optional[str] = None) -> str:
    """
    Persists a structured dataset to data/<key>_historical.json with metadata timestamps.
    """
    os.makedirs(BENCHMARK_STORAGE_DIR, exist_ok=True)
    target_file = filename or os.path.join(BENCHMARK_STORAGE_DIR, f"{key}_historical.json")
    
    payload = {
        "benchmark_key": key,
        "last_refreshed_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "records_count": len(data) if isinstance(data, (list, dict)) else 1,
        "data": data
    }
    
    try:
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)
        logger.info(f"Persisted historical benchmark '{key}' to {target_file}")
    except Exception as e:
        logger.error(f"Failed to persist historical benchmark '{key}': {e}")
    return target_file


def load_historical_benchmark(key: str, filename: Optional[str] = None) -> Optional[Any]:
    """
    Loads a persisted benchmark dataset from data/<key>_historical.json if present.
    """
    target_file = filename or os.path.join(BENCHMARK_STORAGE_DIR, f"{key}_historical.json")
    if not os.path.exists(target_file):
        return None
    try:
        with open(target_file, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, dict) and "data" in payload:
            return payload["data"]
        return payload
    except Exception as e:
        logger.warning(f"Failed to read historical benchmark '{key}' from {target_file}: {e}")
        return None


class HistoricalBenchmarkManager:
    """
    Orchestrates weekly automated refresh passes across all registered data feeds.
    """

    @classmethod
    def refresh_baker_hughes(cls) -> Dict[str, Any]:
        """Refreshes Baker Hughes rotary rig count benchmark from live FRED series."""
        try:
            from src.alternative_data_feeds import BakerHughesDataConnector
            connector = BakerHughesDataConnector()
            df = connector.fetch_rig_counts()
            if df is not None and not df.empty:
                records = df.assign(date=df['date'].dt.strftime("%Y-%m-%d")).to_dict(orient="records")
                save_historical_benchmark("baker_hughes", records)
                return {"status": "SUCCESS", "records": len(records)}
        except Exception as e:
            logger.warning(f"Baker Hughes benchmark refresh error: {e}")
        return {"status": "FAILED", "records": 0}

    @classmethod
    def refresh_executive_social(cls) -> Dict[str, Any]:
        """Refreshes executive social media posts benchmark."""
        try:
            from src.executive_social_feed import ExecutiveSocialFeedConnector
            connector = ExecutiveSocialFeedConnector()
            posts = connector.fetch_executive_social_headlines(force_refresh=True)
            if posts:
                save_historical_benchmark("executive_social", posts)
                return {"status": "SUCCESS", "records": len(posts)}
        except Exception as e:
            logger.warning(f"Executive social benchmark refresh error: {e}")
        return {"status": "FAILED", "records": 0}

    @classmethod
    def refresh_geopolitical(cls) -> Dict[str, Any]:
        """Refreshes geopolitical chokepoint events benchmark."""
        try:
            from src.geopolitical_feeds import GeopoliticalFeedConnector
            connector = GeopoliticalFeedConnector()
            events = connector.fetch_geopolitical_headlines(force_refresh=True)
            if events:
                save_historical_benchmark("geopolitical", events)
                return {"status": "SUCCESS", "records": len(events)}
        except Exception as e:
            logger.warning(f"Geopolitical benchmark refresh error: {e}")
        return {"status": "FAILED", "records": 0}

    @classmethod
    def refresh_key_movers(cls) -> Dict[str, Any]:
        """Refreshes key market movers statements benchmark."""
        try:
            from src.key_movers_feed import KeyMoversFeedConnector
            connector = KeyMoversFeedConnector()
            events = connector.fetch_key_movers_headlines(force_refresh=True)
            if events:
                save_historical_benchmark("key_movers", events)
                return {"status": "SUCCESS", "records": len(events)}
        except Exception as e:
            logger.warning(f"Key movers benchmark refresh error: {e}")
        return {"status": "FAILED", "records": 0}

    @classmethod
    def refresh_diesel_regional(cls) -> Dict[str, Any]:
        """Refreshes regional retail diesel price anchors."""
        try:
            from src.diesel_regional import get_live_or_anchor_diesel_prices
            prices = get_live_or_anchor_diesel_prices(use_live_feed=True)
            if prices:
                save_historical_benchmark("diesel", prices)
                return {"status": "SUCCESS", "records": len(prices)}
        except Exception as e:
            logger.warning(f"Diesel regional benchmark refresh error: {e}")
        return {"status": "FAILED", "records": 0}

    @classmethod
    def refresh_treasury_yields(cls) -> Dict[str, Any]:
        """Refreshes U.S. Treasury yield dataset."""
        try:
            from src.treasury_yield_feed import TreasuryYieldConnector
            connector = TreasuryYieldConnector()
            df = connector.fetch_treasury_yield_dataset()
            if df is not None and not df.empty:
                records = df.assign(date=df['date'].dt.strftime("%Y-%m-%d")).to_dict(orient="records")
                save_historical_benchmark("treasury", records)
                return {"status": "SUCCESS", "records": len(records)}
        except Exception as e:
            logger.warning(f"Treasury yield benchmark refresh error: {e}")
        return {"status": "FAILED", "records": 0}

    @classmethod
    def refresh_usgs_water(cls) -> Dict[str, Any]:
        """Refreshes USGS water streamflow and stage telemetry."""
        try:
            from src.usgs_water_feed import USGSWaterFeedConnector
            connector = USGSWaterFeedConnector()
            telemetry = connector.fetch_live_water_telemetry()
            if telemetry and "stations" in telemetry:
                save_historical_benchmark("usgs_water", telemetry)
                return {"status": "SUCCESS", "records": len(telemetry["stations"])}
        except Exception as e:
            logger.warning(f"USGS water benchmark refresh error: {e}")
        return {"status": "FAILED", "records": 0}

    @classmethod
    def refresh_usgs_seismic(cls) -> Dict[str, Any]:
        """Refreshes USGS earthquake hazard telemetry."""
        try:
            from src.usgs_seismic import USGSSeismicConnector
            connector = USGSSeismicConnector()
            telemetry = connector.fetch_live_seismic_telemetry(corridor="all")
            if telemetry and "corridors" in telemetry:
                save_historical_benchmark("usgs_seismic", telemetry)
                return {"status": "SUCCESS", "records": len(telemetry.get("events", []))}
        except Exception as e:
            logger.warning(f"USGS seismic benchmark refresh error: {e}")
        return {"status": "FAILED", "records": 0}

    @classmethod
    def refresh_census_demographics(cls) -> Dict[str, Any]:
        """Refreshes U.S. Census ACS demographic profiles across metro hubs."""
        try:
            from src.census_demographics import CensusDemographicsConnector
            connector = CensusDemographicsConnector()
            profiles = connector.get_all_metro_demographics()
            if profiles and "metro_areas" in profiles:
                save_historical_benchmark("census_demographics", profiles)
                return {"status": "SUCCESS", "records": len(profiles["metro_areas"])}
        except Exception as e:
            logger.warning(f"Census demographics benchmark refresh error: {e}")
        return {"status": "FAILED", "records": 0}

    @classmethod
    def refresh_commodity_spot_prices(cls) -> Dict[str, Any]:
        """Refreshes OilpriceAPI commodity spot prices."""
        try:
            from src.data_ingestion import fetch_oilpriceapi_prices
            prices = fetch_oilpriceapi_prices()
            if prices:
                save_historical_benchmark("oilpriceapi", prices)
                return {"status": "SUCCESS", "records": len(prices)}
        except Exception as e:
            logger.warning(f"Commodity spot price benchmark refresh error: {e}")
        return {"status": "FAILED", "records": 0}

    @classmethod
    def refresh_all(cls) -> Dict[str, Any]:
        """
        Executes a complete weekly refresh pass across all registered benchmarks.
        """
        logger.info("Starting automated weekly historical benchmark refresh pass...")
        start_time = datetime.now(timezone.utc)
        results = {
            "baker_hughes": cls.refresh_baker_hughes(),
            "executive_social": cls.refresh_executive_social(),
            "geopolitical": cls.refresh_geopolitical(),
            "key_movers": cls.refresh_key_movers(),
            "diesel_regional": cls.refresh_diesel_regional(),
            "treasury_yields": cls.refresh_treasury_yields(),
            "usgs_water": cls.refresh_usgs_water(),
            "usgs_seismic": cls.refresh_usgs_seismic(),
            "census_demographics": cls.refresh_census_demographics(),
            "commodity_spot_prices": cls.refresh_commodity_spot_prices()
        }

        successful = sum(1 for v in results.values() if v.get("status") == "SUCCESS")
        total = len(results)

        summary = {
            "timestamp_utc": start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "benchmarks_refreshed": f"{successful}/{total}",
            "details": results
        }
        logger.info(f"Completed weekly benchmark refresh pass: {successful}/{total} successful.")
        return summary


def refresh_all_historical_benchmarks() -> Dict[str, Any]:
    """Convenience functional interface for weekly workflow runners."""
    return HistoricalBenchmarkManager.refresh_all()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    res = refresh_all_historical_benchmarks()
    print(json.dumps(res, indent=2))
