"""
NASA POWER Integration Module (src/nasa_power.py)
Ingests global satellite solar, meteorological, and agroclimatological data from
NASA POWER (Prediction Of Worldwide Energy Resources) API (https://power.larc.nasa.gov/).

Modeling Applications:
1. Heating Degree Day (HDD) & Cooling Degree Day (CDD) normalization for Heating Oil /
   ULSD Distillate modeling (HO=F crack spreads in PADD 1).
2. Growing Degree Days (GDD), solar irradiance, and precipitation feature extraction for
   Midwest (PADD 2) corn yields, ethanol crush margins, and finished E10/E85 blendstock basis.

Issues Addressed:
- Issue #420: [Feature Request] Ingest NASA POWER (Energy & Petroleum Data Feed)
- Issue #370: NASA POWER Integration for Distillate HDD/CDD & Midwest Biofuel/Ethanol Agroclimatology
"""

import os
import json
import time
import hashlib
import logging
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

from src.connector_telemetry import log_connector_event

logger = logging.getLogger(__name__)

NASA_POWER_BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
DEFAULT_CACHE_FILE = os.path.join("data", "nasa_power_cache.json")
CACHE_TTL_HOURS = 24.0

# 1. PADD 1 Distillate & Heating Oil Marine/Rack Terminal Coordinates
DISTILLATE_TERMINAL_HUBS: Dict[str, Dict[str, Any]] = {
    "NewYorkHarbor": {
        "lat": 40.7357,
        "lon": -74.1724,
        "padd": "1B",
        "name": "New York Harbor / Newark"
    },
    "DelawareCity": {
        "lat": 39.5604,
        "lon": -75.5905,
        "padd": "1B",
        "name": "Delaware City Refinery Terminal"
    },
    "Boston": {
        "lat": 42.3601,
        "lon": -71.0589,
        "padd": "1A",
        "name": "Boston Harbor Terminal"
    }
}

# 2. PADD 2 Midwest Ethanol / Biofuel Agroclimatology Coordinates (Corn Belt)
BIOFUEL_CORN_HUBS: Dict[str, Dict[str, Any]] = {
    "DesMoines_IA": {
        "lat": 41.5868,
        "lon": -93.6250,
        "padd": "2",
        "name": "Central Iowa Corn Belt"
    },
    "Peoria_IL": {
        "lat": 40.6936,
        "lon": -89.5890,
        "padd": "2",
        "name": "Illinois River Corn Belt"
    },
    "Omaha_NE": {
        "lat": 41.2565,
        "lon": -95.9345,
        "padd": "2",
        "name": "Eastern Nebraska Corn Belt"
    }
}


def celsius_to_fahrenheit(c_temp: float) -> float:
    """Converts Celsius temperature to Fahrenheit."""
    return (float(c_temp) * 9.0 / 5.0) + 32.0


def calculate_hdd(t_mean_f: float, base_temp_f: float = 65.0) -> float:
    """
    Calculates Heating Degree Days (HDD) for a single day.
    HDD = max(0, base_temp - T_mean)
    """
    return max(0.0, base_temp_f - float(t_mean_f))


def calculate_cdd(t_mean_f: float, base_temp_f: float = 65.0) -> float:
    """
    Calculates Cooling Degree Days (CDD) for a single day.
    CDD = max(0, T_mean - base_temp)
    """
    return max(0.0, float(t_mean_f) - base_temp_f)


def calculate_gdd(
    t_max_f: float,
    t_min_f: float,
    base_temp_f: float = 50.0,
    cap_temp_f: float = 86.0
) -> float:
    """
    Calculates standard Agricultural Growing Degree Days (GDD) for corn/grain feedstocks.
    Formula:
      T_adj_max = min(cap_temp, max(base_temp, T_max))
      T_adj_min = max(base_temp, min(cap_temp, T_min))
      GDD = max(0, (T_adj_max + T_adj_min) / 2 - base_temp)
    """
    t_max_adj = min(cap_temp_f, max(base_temp_f, float(t_max_f)))
    t_min_adj = max(base_temp_f, min(cap_temp_f, float(t_min_f)))
    t_mean_adj = (t_max_adj + t_min_adj) / 2.0
    return max(0.0, t_mean_adj - base_temp_f)


class NASAPowerClient:
    """
    Client for NASA POWER Point Daily Temporal API with local disk caching and
    energy/climatology feature extractors.
    """

    def __init__(
        self,
        base_url: str = NASA_POWER_BASE_URL,
        cache_file: str = DEFAULT_CACHE_FILE,
        cache_ttl_hours: float = CACHE_TTL_HOURS,
        timeout: float = 15.0
    ):
        self.base_url = base_url.rstrip("/")
        self.cache_file = cache_file
        self.cache_ttl_hours = cache_ttl_hours
        self.timeout = timeout
        self._disk_cache = self._load_cache()

    def _load_cache(self) -> Dict[str, Any]:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.debug(f"Failed to load NASA POWER cache from {self.cache_file}: {e}")
        return {}

    def _save_cache(self) -> None:
        if os.environ.get("TESTING") == "1":
            return
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self._disk_cache, f, indent=2)
        except Exception as e:
            logger.debug(f"Failed to save NASA POWER cache to {self.cache_file}: {e}")

    def _get_cache_key(self, lat: float, lon: float, start: str, end: str, params: str) -> str:
        raw_key = f"{lat:.4f}_{lon:.4f}_{start}_{end}_{params}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def fetch_point_daily(
        self,
        lat: float,
        lon: float,
        start_date: str,
        end_date: str,
        parameters: Optional[List[str]] = None,
        community: str = "RE"
    ) -> Dict[str, Any]:
        """
        Fetches daily time-series meteorology and solar data for a single latitude/longitude.
        Dates formatted as 'YYYYMMDD'.
        Default parameters: T2M, T2M_MAX, T2M_MIN, ALLSKY_SFC_SW_DWN, PRECTOTCORR.
        """
        if parameters is None:
            parameters = ["T2M", "T2M_MAX", "T2M_MIN", "ALLSKY_SFC_SW_DWN", "PRECTOTCORR"]

        param_str = ",".join(sorted(parameters))
        cache_key = self._get_cache_key(lat, lon, start_date, end_date, param_str)

        # Check in-memory/disk cache
        now_ts = time.time()
        cached_entry = self._disk_cache.get(cache_key)
        if cached_entry:
            exp_ts = cached_entry.get("cached_at", 0) + (self.cache_ttl_hours * 3600.0)
            if now_ts < exp_ts:
                logger.debug(f"NASA POWER cache hit for ({lat:.2f}, {lon:.2f})")
                return cached_entry.get("data", {})

        # Testing mode mock response
        if os.environ.get("TESTING") == "1" and os.environ.get("TEST_NASA_POWER_FORCE") != "1":
            mock_data = self._generate_mock_response(lat, lon, start_date, end_date, parameters)
            return mock_data

        # Construct live HTTP request
        params = {
            "parameters": param_str,
            "community": community,
            "longitude": f"{lon:.4f}",
            "latitude": f"{lat:.4f}",
            "start": start_date,
            "end": end_date,
            "format": "JSON",
            "header": "true"
        }
        query_string = urllib.parse.urlencode(params)
        request_url = f"{self.base_url}?{query_string}"

        start_time = time.time()
        target_tag = f"{lat:.2f},{lon:.2f}"
        try:
            req = urllib.request.Request(
                request_url,
                headers={"User-Agent": "Midgley-Energy-Forecaster/2.0"},
                method="GET"
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status == 200:
                    raw_json = json.loads(resp.read().decode("utf-8"))
                    data = raw_json.get("properties", {}).get("parameter", {})
                    latency_ms = (time.time() - start_time) * 1000.0

                    # Store in disk cache
                    self._disk_cache[cache_key] = {
                        "cached_at": now_ts,
                        "data": data,
                        "lat": lat,
                        "lon": lon,
                        "start": start_date,
                        "end": end_date
                    }
                    self._save_cache()

                    log_connector_event(
                        connector_name="NASAPower",
                        target=target_tag,
                        status="SUCCESS",
                        latency_ms=latency_ms,
                        details=f"Retrieved {len(data)} parameters over {start_date}-{end_date}"
                    )
                    return data
                else:
                    latency_ms = (time.time() - start_time) * 1000.0
                    log_connector_event(
                        connector_name="NASAPower",
                        target=target_tag,
                        status=f"HTTP_{resp.status}",
                        latency_ms=latency_ms
                    )
                    return {}
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000.0
            log_connector_event(
                connector_name="NASAPower",
                target=target_tag,
                status="ERROR",
                latency_ms=latency_ms,
                details=str(e)
            )
            logger.warning(f"Failed to query NASA POWER for ({lat:.2f}, {lon:.2f}): {e}")
            return {}

    def _generate_mock_response(
        self,
        lat: float,
        lon: float,
        start_date: str,
        end_date: str,
        parameters: List[str]
    ) -> Dict[str, Any]:
        """Generates realistic deterministic mock response for testing."""
        mock_data: Dict[str, Dict[str, float]] = {p: {} for p in parameters}
        try:
            start_dt = datetime.strptime(start_date, "%Y%m%d")
            end_dt = datetime.strptime(end_date, "%Y%m%d")
        except Exception:
            start_dt = datetime(2026, 9, 15)
            end_dt = datetime(2026, 9, 21)

        cur_dt = start_dt
        while cur_dt <= end_dt:
            date_key = cur_dt.strftime("%Y%m%d")
            day_offset = (cur_dt - start_dt).days

            # Baseline temperature ~15C (59F) with spatial latitude modulation
            base_t = 22.0 - (lat - 35.0) * 0.8 + (day_offset * 0.3)
            if "T2M" in parameters:
                mock_data["T2M"][date_key] = round(base_t, 2)
            if "T2M_MAX" in parameters:
                mock_data["T2M_MAX"][date_key] = round(base_t + 5.0, 2)
            if "T2M_MIN" in parameters:
                mock_data["T2M_MIN"][date_key] = round(base_t - 4.5, 2)
            if "ALLSKY_SFC_SW_DWN" in parameters:
                mock_data["ALLSKY_SFC_SW_DWN"][date_key] = round(16.5 + (day_offset % 3), 2)
            if "PRECTOTCORR" in parameters:
                mock_data["PRECTOTCORR"][date_key] = round(1.2 if day_offset == 2 else 0.0, 2)

            cur_dt += timedelta(days=1)

        return mock_data

    def get_distillate_weather_features(
        self,
        days_back: int = 7,
        end_date_str: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extracts heating/cooling degree day demand normalization features across
        PADD 1 distillate and heating oil hubs (New York Harbor, Delaware City, Boston).
        """
        if end_date_str:
            end_dt = datetime.strptime(end_date_str, "%Y%m%d")
        else:
            end_dt = datetime.now(timezone.utc) - timedelta(days=2)  # NASA POWER has ~2-day latency
        start_dt = end_dt - timedelta(days=days_back)

        start_str = start_dt.strftime("%Y%m%d")
        end_str = end_dt.strftime("%Y%m%d")

        hub_results = {}
        total_padd1_hdd = 0.0
        total_padd1_cdd = 0.0
        total_padd1_tmean_f = 0.0
        valid_hubs = 0

        for hub_key, hub_info in DISTILLATE_TERMINAL_HUBS.items():
            lat = hub_info["lat"]
            lon = hub_info["lon"]
            data = self.fetch_point_daily(
                lat=lat,
                lon=lon,
                start_date=start_str,
                end_date=end_str,
                parameters=["T2M", "T2M_MAX", "T2M_MIN"]
            )
            t2m_series = data.get("T2M", {})
            if not t2m_series:
                continue

            hub_hdd = 0.0
            hub_cdd = 0.0
            hub_temps_f = []

            for date_k, t_celsius in t2m_series.items():
                if t_celsius is None or t_celsius <= -999.0:
                    continue
                t_f = celsius_to_fahrenheit(t_celsius)
                hub_temps_f.append(t_f)
                hub_hdd += calculate_hdd(t_f)
                hub_cdd += calculate_cdd(t_f)

            avg_temp_f = sum(hub_temps_f) / len(hub_temps_f) if hub_temps_f else 65.0
            hub_results[hub_key] = {
                "name": hub_info["name"],
                "padd": hub_info["padd"],
                "hdd_sum": round(hub_hdd, 2),
                "cdd_sum": round(hub_cdd, 2),
                "avg_temp_f": round(avg_temp_f, 2),
                "days_evaluated": len(hub_temps_f)
            }
            total_padd1_hdd += hub_hdd
            total_padd1_cdd += hub_cdd
            total_padd1_tmean_f += avg_temp_f
            valid_hubs += 1

        avg_padd1_hdd = (total_padd1_hdd / valid_hubs) if valid_hubs > 0 else 0.0
        avg_padd1_cdd = (total_padd1_cdd / valid_hubs) if valid_hubs > 0 else 0.0
        avg_padd1_temp = (total_padd1_tmean_f / valid_hubs) if valid_hubs > 0 else 65.0

        # Heating oil structural consumption draw index: ~0.15% incremental draw per HDD above 10
        distillate_demand_draw_index = max(0.0, (avg_padd1_hdd - 10.0) * 0.015)

        return {
            "start_date": start_str,
            "end_date": end_str,
            "hubs_evaluated": valid_hubs,
            "padd1_distillate_avg_hdd": round(avg_padd1_hdd, 2),
            "padd1_distillate_avg_cdd": round(avg_padd1_cdd, 2),
            "padd1_distillate_avg_temp_f": round(avg_padd1_temp, 2),
            "padd1_distillate_demand_draw_index": round(distillate_demand_draw_index, 4),
            "terminal_breakdown": hub_results
        }

    def get_ethanol_agro_features(
        self,
        days_back: int = 7,
        end_date_str: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extracts agroclimatological features (Growing Degree Days, Solar Irradiance, Precipitation)
        across PADD 2 Midwest corn belt hubs for ethanol feedstock and blendstock economics.
        """
        if end_date_str:
            end_dt = datetime.strptime(end_date_str, "%Y%m%d")
        else:
            end_dt = datetime.now(timezone.utc) - timedelta(days=2)
        start_dt = end_dt - timedelta(days=days_back)

        start_str = start_dt.strftime("%Y%m%d")
        end_str = end_dt.strftime("%Y%m%d")

        hub_results = {}
        total_padd2_gdd = 0.0
        total_padd2_solar = 0.0
        total_padd2_precip = 0.0
        valid_hubs = 0

        for hub_key, hub_info in BIOFUEL_CORN_HUBS.items():
            lat = hub_info["lat"]
            lon = hub_info["lon"]
            data = self.fetch_point_daily(
                lat=lat,
                lon=lon,
                start_date=start_str,
                end_date=end_str,
                parameters=["T2M_MAX", "T2M_MIN", "ALLSKY_SFC_SW_DWN", "PRECTOTCORR"]
            )
            tmax_series = data.get("T2M_MAX", {})
            tmin_series = data.get("T2M_MIN", {})
            solar_series = data.get("ALLSKY_SFC_SW_DWN", {})
            precip_series = data.get("PRECTOTCORR", {})

            if not tmax_series or not tmin_series:
                continue

            hub_gdd = 0.0
            hub_solar = []
            hub_precip = 0.0
            days_count = 0

            for date_k, tmax_c in tmax_series.items():
                tmin_c = tmin_series.get(date_k)
                if tmax_c is None or tmin_c is None or tmax_c <= -999.0 or tmin_c <= -999.0:
                    continue
                tmax_f = celsius_to_fahrenheit(tmax_c)
                tmin_f = celsius_to_fahrenheit(tmin_c)
                hub_gdd += calculate_gdd(tmax_f, tmin_f)

                sol = solar_series.get(date_k)
                if sol is not None and sol >= 0.0:
                    hub_solar.append(sol)

                pr = precip_series.get(date_k)
                if pr is not None and pr >= 0.0:
                    hub_precip += pr

                days_count += 1

            avg_solar = (sum(hub_solar) / len(hub_solar)) if hub_solar else 15.0
            hub_results[hub_key] = {
                "name": hub_info["name"],
                "gdd_sum": round(hub_gdd, 2),
                "avg_solar_irradiance_mj_m2": round(avg_solar, 2),
                "total_precipitation_mm": round(hub_precip, 2),
                "days_evaluated": days_count
            }
            total_padd2_gdd += hub_gdd
            total_padd2_solar += avg_solar
            total_padd2_precip += hub_precip
            valid_hubs += 1

        avg_padd2_gdd = (total_padd2_gdd / valid_hubs) if valid_hubs > 0 else 0.0
        avg_padd2_solar = (total_padd2_solar / valid_hubs) if valid_hubs > 0 else 15.0
        avg_padd2_precip = (total_padd2_precip / valid_hubs) if valid_hubs > 0 else 0.0

        # Ethanol corn feedstock pressure factor (higher GDD & favorable rain -> ample yield -> cheaper ethanol)
        feedstock_yield_pressure = round((avg_padd2_gdd / 100.0) * 0.02, 4)

        return {
            "start_date": start_str,
            "end_date": end_str,
            "hubs_evaluated": valid_hubs,
            "padd2_corn_avg_gdd": round(avg_padd2_gdd, 2),
            "padd2_corn_avg_solar_mj_m2": round(avg_padd2_solar, 2),
            "padd2_corn_avg_precip_mm": round(avg_padd2_precip, 2),
            "ethanol_feedstock_yield_pressure": feedstock_yield_pressure,
            "corn_belt_breakdown": hub_results
        }

    def get_combined_nasa_power_features(self) -> Dict[str, Any]:
        """
        Unified high-level extractor returning both Distillate HDD/CDD and Biofuel/Ethanol features.
        """
        distillate_feats = self.get_distillate_weather_features()
        ethanol_feats = self.get_ethanol_agro_features()

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "distillate_features": distillate_feats,
            "ethanol_features": ethanol_feats,
            "padd1_distillate_avg_hdd": distillate_feats.get("padd1_distillate_avg_hdd", 0.0),
            "padd1_distillate_demand_draw_index": distillate_feats.get("padd1_distillate_demand_draw_index", 0.0),
            "padd2_corn_avg_gdd": ethanol_feats.get("padd2_corn_avg_gdd", 0.0),
            "ethanol_feedstock_yield_pressure": ethanol_feats.get("ethanol_feedstock_yield_pressure", 0.0)
        }
