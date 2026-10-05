"""
NASA FIRMS Satellite Active Fire & Thermal Flaring Telemetry Connector (src/firms_satellite_feed.py)
Issue #453: Ingests near-real-time VIIRS (375m) Fire Radiative Power (FRP) and thermal anomaly data
from NOAA-20 / NOAA-21 / Suomi-NPP satellites across exact refining hub bounding boxes.

Fuses satellite thermal flaring signatures with state environmental agency filings (TCEQ EEERD,
LDEQ EDMS, USCG NRC) to detect unplanned refinery flaring upsets and catalytic cracker shutdowns.
"""

import os
import math
import json
import logging
import urllib.request
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union
import pandas as pd
import numpy as np

logger = logging.getLogger("midgley.firms_satellite_feed")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
FIRMS_VINTAGES_FILE = os.path.join(DATA_DIR, "firms_satellite_vintages.json")

# NASA FIRMS API Bounding Boxes for Critical U.S. Refining Hubs [min_lon, min_lat, max_lon, max_lat]
FIRMS_REFINING_BBOXES: Dict[str, Dict[str, Any]] = {
    "baytown_houston": {
        "name": "ExxonMobil Baytown & Houston Ship Channel",
        "bbox": [-95.40, 29.65, -94.90, 29.85],
        "refineries": ["ExxonMobil Baytown", "Valero Houston", "LyondellBasell Houston"],
        "baseline_daily_frp_mw": 18.5,
        "primary_padd": "PADD 3"
    },
    "galveston_bay_texas_city": {
        "name": "Marathon Galveston Bay & Texas City Complex",
        "bbox": [-95.00, 29.30, -94.85, 29.45],
        "refineries": ["Marathon Galveston Bay", "Valero Texas City"],
        "baseline_daily_frp_mw": 14.0,
        "primary_padd": "PADD 3"
    },
    "port_arthur_beaumont": {
        "name": "Motiva Port Arthur & TotalEnergies Complex",
        "bbox": [-94.15, 29.80, -93.85, 30.10],
        "refineries": ["Motiva Port Arthur", "TotalEnergies Port Arthur", "ExxonMobil Beaumont"],
        "baseline_daily_frp_mw": 22.0,
        "primary_padd": "PADD 3"
    },
    "garyville_norco_baton_rouge": {
        "name": "Marathon Garyville, Shell Norco & ExxonMobil Baton Rouge",
        "bbox": [-91.30, 29.90, -90.35, 30.60],
        "refineries": ["Marathon Garyville", "Shell Norco", "ExxonMobil Baton Rouge", "Valero St. Charles"],
        "baseline_daily_frp_mw": 25.0,
        "primary_padd": "PADD 3"
    },
    "lake_charles": {
        "name": "Citgo & Phillips 66 Lake Charles Complex",
        "bbox": [-93.35, 30.15, -93.15, 30.30],
        "refineries": ["Citgo Lake Charles", "Phillips 66 Lake Charles"],
        "baseline_daily_frp_mw": 11.0,
        "primary_padd": "PADD 3"
    },
    "west_tulsa_cushing": {
        "name": "HF Sinclair West Tulsa & Cushing Storage Terminal",
        "bbox": [-96.85, 35.95, -95.90, 36.20],
        "refineries": ["HF Sinclair Tulsa East/West"],
        "baseline_daily_frp_mw": 4.5,
        "primary_padd": "PADD 2"
    },
    "catlettsburg_ohio_valley": {
        "name": "Marathon Catlettsburg KY Refining Complex",
        "bbox": [-82.65, 38.35, -82.50, 38.45],
        "refineries": ["Marathon Catlettsburg"],
        "baseline_daily_frp_mw": 6.0,
        "primary_padd": "PADD 2"
    },
    "delaware_city_delmarva": {
        "name": "PBF Delaware City Refinery",
        "bbox": [-75.70, 39.55, -75.50, 39.65],
        "refineries": ["PBF Delaware City"],
        "baseline_daily_frp_mw": 5.0,
        "primary_padd": "PADD 1B"
    },
    "richmond_martinez_bay_area": {
        "name": "Chevron Richmond & Martinez Refining Complex",
        "bbox": [-122.45, 37.85, -122.05, 38.05],
        "refineries": ["Chevron Richmond", "PBF Martinez", "Valero Benicia"],
        "baseline_daily_frp_mw": 12.0,
        "primary_padd": "PADD 5"
    }
}


def save_firms_vintage_record(record: dict, filepath: str = FIRMS_VINTAGES_FILE) -> None:
    """Persists a bitemporal point-in-time NASA FIRMS observation (Issue #453)."""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        vintages = []
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    vintages = json.load(f)
            except Exception:
                vintages = []

        now_str = record.get("recorded_at", datetime.now(timezone.utc).isoformat())
        day_key = str(record.get("date", record.get("timestamp", now_str)))[:10]
        hub = record.get("hub_code", "custom")

        # Deduplicate per hub and day
        vintages = [v for v in vintages if not (v.get("hub_code") == hub and str(v.get("date", ""))[:10] == day_key)]

        entry = {
            "hub_code": hub,
            "recorded_at": now_str,
            "date": day_key,
            "data": record
        }
        vintages.append(entry)

        from src.storage_io import atomic_write_json
        atomic_write_json(filepath, vintages)
    except Exception as e:
        logger.warning(f"Could not persist NASA FIRMS vintage record: {e}")


class FirmsSatelliteFeedConnector:
    """
    NASA FIRMS Satellite Active Fire / Flaring Telemetry Connector.
    Queries VIIRS 375m NRT thermal detection feeds across refining corridors.
    """

    def __init__(self, map_key: Optional[str] = None):
        if not map_key:
            try:
                from dotenv import load_dotenv
                load_dotenv()
            except ImportError:
                pass
            if not os.getenv("NASA_FIRMS_MAP_KEY") and not os.getenv("FIRMS_MAP_KEY"):
                env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
                if os.path.exists(env_path):
                    try:
                        with open(env_path, "r", encoding="utf-8") as f:
                            for line in f:
                                if "=" in line and not line.strip().startswith("#"):
                                    k, v = line.strip().split("=", 1)
                                    os.environ.setdefault(k.strip(), v.strip("\"'"))
                    except Exception:
                        pass
        self.map_key = map_key or os.getenv("NASA_FIRMS_MAP_KEY") or os.getenv("FIRMS_MAP_KEY")
        self.hubs = FIRMS_REFINING_BBOXES
        self.base_url = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

    def fetch_hub_firms_telemetry(self, hub_code: str, days: int = 1) -> Dict[str, Any]:
        """
        Fetches satellite active fire / thermal flaring observations for a refining corridor.
        """
        if hub_code not in self.hubs:
            logger.warning(f"Unknown FIRMS refining hub code: {hub_code}")
            return self._build_nominal_fallback(hub_code)

        hub_info = self.hubs[hub_code]
        min_lon, min_lat, max_lon, max_lat = hub_info["bbox"]
        bbox_str = f"{min_lon:.2f},{min_lat:.2f},{max_lon:.2f},{max_lat:.2f}"
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        cache_key = f"firms_satellite:{hub_code}:{today_str}:{days}"
        try:
            from src.lookup_cache import global_cache
            cached = global_cache.get(cache_key)
            if cached and isinstance(cached, dict):
                return cached
        except Exception:
            pass

        if self.map_key:
            # Query VIIRS NOAA-20 NRT (375m active thermal)
            url = f"{self.base_url}/{self.map_key}/VIIRS_NOAA20_NRT/{bbox_str}/{days}"
            try:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "MidgleyGasPriceForecaster/0.8 (contact@example.com)"}
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    if response.status == 200:
                        csv_data = response.read().decode("utf-8")
                        lines = [l.strip() for l in csv_data.strip().split("\n") if l.strip()]
                        if len(lines) >= 1:
                            if len(lines) > 1:
                                df = pd.read_csv(pd.io.common.StringIO(csv_data))
                                total_frp = float(df["frp"].sum()) if "frp" in df.columns else 0.0
                                pixel_count = int(len(df))
                                max_bright = float(df["bright_ti4"].max()) if "bright_ti4" in df.columns else 300.0
                            else:
                                # 0 detections is authentic zero flaring (Issue #612)
                                total_frp = 0.0
                                pixel_count = 0
                                max_bright = 295.0

                            baseline = hub_info["baseline_daily_frp_mw"]

                            # Compute rolling 7-day vs 30-day baseline anomaly if historical vintages exist (Issue #612)
                            recent_frps = self._get_recent_vintage_frp(hub_code, days=30)
                            if len(recent_frps) >= 14:
                                mu_30 = float(np.mean(recent_frps))
                                std_30 = float(max(np.std(recent_frps), 2.0))
                                mean_7d = float(np.mean(recent_frps[-7:] + [total_frp]))
                                anomaly_z = (mean_7d - mu_30) / std_30
                            else:
                                anomaly_z = (total_frp - baseline) / max(baseline * 0.4, 2.0)

                            is_major_upset = anomaly_z >= 2.5 and total_frp >= (baseline * 2.0)

                            res = {
                                "hub_code": hub_code,
                                "name": hub_info["name"],
                                "date": today_str,
                                "total_frp_mw": round(total_frp, 2),
                                "thermal_pixel_count": pixel_count,
                                "max_brightness_temp_kelvin": round(max_bright, 1),
                                "baseline_frp_mw": baseline,
                                "flaring_anomaly_z_score": round(anomaly_z, 2),
                                "is_major_flaring_upset": is_major_upset,
                                "source": "NASA FIRMS VIIRS (NOAA-20 NRT 375m)",
                                "is_live": True,
                                "recorded_at": datetime.now(timezone.utc).isoformat()
                            }
                            try:
                                from src.lookup_cache import global_cache
                                global_cache.set(cache_key, res, ttl_seconds=14400)  # 4 hour cache
                            except Exception:
                                pass
                            save_firms_vintage_record(res)
                            return res
            except Exception as e:
                logger.debug(f"NASA FIRMS query notice for {hub_code}: {e}; falling back to nominal baseline.")

        # Fallback to nominal operational baseline
        return self._build_nominal_fallback(hub_code, today_str)

    def _get_recent_vintage_frp(self, hub_code: str, days: int = 30) -> List[float]:
        """Loads trailing authentic FRP observations from vintage store (Issue #612)."""
        if not os.path.exists(FIRMS_VINTAGES_FILE):
            return []
        try:
            with open(FIRMS_VINTAGES_FILE, "r", encoding="utf-8") as f:
                vintages = json.load(f)
            frps = []
            for v in vintages:
                data = v.get("data", {})
                if data.get("hub_code") == hub_code and data.get("is_live", False):
                    frp = data.get("total_frp_mw")
                    if frp is not None:
                        frps.append(float(frp))
            return frps[-days:]
        except Exception:
            return []

    def _build_nominal_fallback(self, hub_code: str, date_str: Optional[str] = None) -> Dict[str, Any]:
        today_str = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        hub_info = self.hubs.get(hub_code, {"name": hub_code, "baseline_daily_frp_mw": 10.0})
        baseline = hub_info.get("baseline_daily_frp_mw", 10.0)

        # Do NOT save test fallback mocks into persistent vintage store (Issue #612, #613)
        res = {
            "hub_code": hub_code,
            "name": hub_info.get("name", hub_code),
            "date": today_str,
            "total_frp_mw": baseline,
            "thermal_pixel_count": 0,
            "max_brightness_temp_kelvin": 300.0,
            "baseline_frp_mw": baseline,
            "flaring_anomaly_z_score": 0.0,
            "is_major_flaring_upset": False,
            "source": "NASA FIRMS Baseline Physical Anchor",
            "is_live": False,
            "recorded_at": datetime.now(timezone.utc).isoformat()
        }
        return res

    def fetch_all_refining_corridors(self) -> Dict[str, Any]:
        """Fetches thermal flaring telemetry across all monitored U.S. refining corridors."""
        results = {}
        total_frp = 0.0
        active_upsets = []

        for code in self.hubs:
            telemetry = self.fetch_hub_firms_telemetry(code)
            results[code] = telemetry
            total_frp += telemetry.get("total_frp_mw", 0.0)
            if telemetry.get("is_major_flaring_upset", False):
                active_upsets.append(code)

        return {
            "status": "SUCCESS",
            "as_of": datetime.now(timezone.utc).isoformat(),
            "total_monitored_hubs": len(self.hubs),
            "aggregate_frp_mw": round(total_frp, 2),
            "active_flaring_upset_corridors": active_upsets,
            "corridors": results
        }
