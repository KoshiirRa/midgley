"""
USGS Earthquake Web Service Telemetry Connector (src/usgs_seismic.py)
Ingests real-time and historical earthquake event telemetry from the USGS Earthquake Web Service API
(earthquake.usgs.gov/fdsnws/event/1/) for real-time seismic fuel market risk scoring. (Issue #55)

Monitors critical energy corridor assets across:
1. PADD 5 Northern California / SF Bay Area (`bay_area`): Chevron Richmond, PBF Martinez, Valero Benicia, Kinder Morgan SFPP.
2. PADD 2 Mid-Continent / Oklahoma (`cushing_ok`): Cushing WTI crude storage hub, HF Sinclair West Tulsa, Phillips 66 Ponca City.
3. PADD 5 Southern California / LA Basin (`socal`): Marathon Carson, Chevron El Segundo, PBF Torrance, Phillips 66 Wilmington.
4. PADD 1B Delaware Valley & Mid-Atlantic (`mid_atlantic`): PBF Delaware City, Phillips 66 Bayway, Buckeye Linden terminal.
5. PADD 2 Central US / New Madrid Corridor (`new_madrid`): Capline & Mid-Valley pipeline river crossings, Valero Memphis.
"""

import os
import math
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List, Tuple
import pandas as pd

from src.lookup_cache import global_cache

logger = logging.getLogger(__name__)

USER_AGENT = "(MidgleyGasPriceForecaster/1.0; contact@example.com)"
DEFAULT_TIMEOUT = 5.0

# Critical Infrastructure Coordinates & Corridors
SEISMIC_CORRIDORS: Dict[str, Dict[str, Any]] = {
    "bay_area": {
        "name": "SF Bay Area Refining & Pipeline Corridor (PADD 5)",
        "bbox": {
            "minlatitude": 36.5,
            "maxlatitude": 38.8,
            "minlongitude": -123.5,
            "maxlongitude": -121.5
        },
        "default_min_mag": 4.0,
        "m_base": 4.2,
        "assets": {
            "chevron_richmond": {
                "name": "Chevron Richmond Refinery",
                "lat": 37.9358,
                "lon": -122.3963,
                "capacity_bpd": 245000,
                "criticality": 1.0
            },
            "pbf_martinez": {
                "name": "PBF Martinez Refinery",
                "lat": 38.0069,
                "lon": -122.1155,
                "capacity_bpd": 157000,
                "criticality": 0.85
            },
            "valero_benicia": {
                "name": "Valero Benicia Refinery",
                "lat": 38.0705,
                "lon": -122.1469,
                "capacity_bpd": 145000,
                "criticality": 0.80
            },
            "km_sfpp_terminal": {
                "name": "Kinder Morgan SFPP Terminal System",
                "lat": 37.6833,
                "lon": -122.4000,
                "capacity_bpd": 200000,
                "criticality": 0.90
            },
            "carquinez_marine_gate": {
                "name": "Carquinez Strait Marine Tanker Channel",
                "lat": 38.0550,
                "lon": -122.1800,
                "capacity_bpd": 300000,
                "criticality": 0.75
            }
        }
    },
    "cushing_ok": {
        "name": "Cushing WTI Hub & Oklahoma Induced Seismicity Corridor (PADD 2)",
        "bbox": {
            "minlatitude": 35.0,
            "maxlatitude": 37.5,
            "minlongitude": -98.5,
            "maxlongitude": -95.5
        },
        "default_min_mag": 3.8,
        "m_base": 3.6,  # Lower base threshold due to shallow focal depth of induced quakes
        "assets": {
            "cushing_terminal": {
                "name": "Cushing Crude Oil Storage Terminal (WTI Delivery Point)",
                "lat": 35.9806,
                "lon": -96.7678,
                "capacity_bpd": 1500000,
                "criticality": 1.0
            },
            "hf_sinclair_tulsa": {
                "name": "HF Sinclair West Tulsa Refinery",
                "lat": 36.1417,
                "lon": -96.0125,
                "capacity_bpd": 85000,
                "criticality": 0.75
            },
            "phillips66_ponca": {
                "name": "Phillips 66 Ponca City Refinery",
                "lat": 36.6975,
                "lon": -97.0867,
                "capacity_bpd": 200000,
                "criticality": 0.80
            },
            "explorer_pipeline_glenpool": {
                "name": "Explorer Pipeline Glenpool Pump Station",
                "lat": 35.9525,
                "lon": -95.9961,
                "capacity_bpd": 660000,
                "criticality": 0.85
            }
        }
    },
    "socal": {
        "name": "Southern California / LA Basin Refining Corridor (PADD 5)",
        "bbox": {
            "minlatitude": 33.3,
            "maxlatitude": 34.7,
            "minlongitude": -118.8,
            "maxlongitude": -117.5
        },
        "default_min_mag": 4.0,
        "m_base": 4.2,
        "assets": {
            "marathon_carson": {
                "name": "Marathon Carson/Wilmington Refinery",
                "lat": 33.8294,
                "lon": -118.2392,
                "capacity_bpd": 363000,
                "criticality": 1.0
            },
            "chevron_el_segundo": {
                "name": "Chevron El Segundo Refinery",
                "lat": 33.9056,
                "lon": -118.4239,
                "capacity_bpd": 269000,
                "criticality": 0.95
            },
            "pbf_torrance": {
                "name": "PBF Torrance Refinery",
                "lat": 33.8408,
                "lon": -118.3303,
                "capacity_bpd": 166000,
                "criticality": 0.80
            },
            "phillips66_wilmington": {
                "name": "Phillips 66 Wilmington Refinery",
                "lat": 33.7844,
                "lon": -118.2714,
                "capacity_bpd": 139000,
                "criticality": 0.75
            }
        }
    },
    "mid_atlantic": {
        "name": "Mid-Atlantic / Delaware Valley Refining Corridor (PADD 1B)",
        "bbox": {
            "minlatitude": 39.0,
            "maxlatitude": 41.5,
            "minlongitude": -76.0,
            "maxlongitude": -73.5
        },
        "default_min_mag": 3.8,
        "m_base": 4.0,
        "assets": {
            "pbf_delaware_city": {
                "name": "PBF Delaware City Refinery",
                "lat": 39.5889,
                "lon": -75.6264,
                "capacity_bpd": 190000,
                "criticality": 1.0
            },
            "p66_bayway_linden": {
                "name": "Phillips 66 Bayway Refinery (Linden NJ)",
                "lat": 40.6389,
                "lon": -74.2250,
                "capacity_bpd": 258000,
                "criticality": 1.0
            },
            "buckeye_terminal_linden": {
                "name": "Buckeye Pipeline Linden Terminal",
                "lat": 40.6300,
                "lon": -74.2200,
                "capacity_bpd": 350000,
                "criticality": 0.85
            }
        }
    },
    "new_madrid": {
        "name": "New Madrid Seismic Zone / Cross-Mississippi Corridors (PADD 2)",
        "bbox": {
            "minlatitude": 35.0,
            "maxlatitude": 38.0,
            "minlongitude": -91.0,
            "maxlongitude": -88.0
        },
        "default_min_mag": 3.8,
        "m_base": 4.0,
        "assets": {
            "capline_crossing": {
                "name": "Capline Pipeline Mississippi River Crossing",
                "lat": 36.5000,
                "lon": -89.5000,
                "capacity_bpd": 1200000,
                "criticality": 1.0
            },
            "mid_valley_crossing": {
                "name": "Mid-Valley Pipeline Ohio River Crossing",
                "lat": 37.0000,
                "lon": -88.7500,
                "capacity_bpd": 280000,
                "criticality": 0.85
            },
            "valero_memphis": {
                "name": "Valero Memphis Refinery",
                "lat": 35.1200,
                "lon": -90.0700,
                "capacity_bpd": 195000,
                "criticality": 0.90
            }
        }
    }
}


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great-circle distance between two geographic coordinates in kilometers."""
    r = 6371.0  # Earth radius in kilometers
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def calculate_hypocentral_distance_km(epicentral_dist_km: float, depth_km: Optional[float] = None) -> float:
    """Computes straight-line 3D distance to hypocenter given depth."""
    d = max(1.0, depth_km or 10.0)
    return math.sqrt(epicentral_dist_km ** 2 + d ** 2)


def calculate_asset_seismic_shock(
    mag: float,
    hypocenter_dist_km: float,
    m_base: float = 4.2,
    alpha: float = 0.55,
    beta: float = 1.25,
    criticality: float = 1.0
) -> float:
    """
    Computes normalized asset-level ground shaking and structural threat intensity in [0.0, 1.0].
    Attenuates with hypocentral distance and scales with magnitude above baseline.
    """
    if mag < (m_base - 0.5):
        return 0.0

    numerator = 10.0 ** (alpha * (mag - m_base))
    denominator = max(10.0, hypocenter_dist_km) ** beta
    raw_shock = (numerator / denominator) * criticality
    return float(max(0.0, min(1.0, raw_shock)))


class USGSSeismicConnector:
    """
    Zero-Cost USGS Earthquake Web Service API Telemetry Connector (earthquake.usgs.gov/fdsnws/event/1/).
    Ingests live GeoJSON earthquake features, evaluates proximity to critical refining & delivery infrastructure,
    and computes standardized physical seismic hazard indices. (Issue #55)
    """

    def __init__(self):
        self.is_free_alternative = True
        self.cost_per_query = 0.0

    def fetch_live_seismic_telemetry(
        self,
        corridor: Optional[str] = "bay_area",
        days: int = 30,
        min_mag: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Fetches live or cached USGS earthquake telemetry for a specific corridor or across all corridors.
        Returns parsed seismic events, facility-level impacts, and composite risk indices.
        """
        minute_bucket = datetime.now().strftime("%Y-%m-%d-%H-%M")
        minute_quarter = f"{minute_bucket[:-1]}{int(minute_bucket[-1]) // 5 * 5:01d}"
        cache_key = f"usgs_seismic_telemetry:{corridor or 'all'}:{days}:{min_mag or 'def'}:{minute_quarter}"

        cached = global_cache.get(cache_key)
        if cached:
            logger.info(f"Loaded USGS seismic telemetry from lookup cache for corridor '{corridor}'.")
            return cached

        # Determine corridors to query
        corridors_to_process = (
            [corridor] if corridor and corridor in SEISMIC_CORRIDORS
            else list(SEISMIC_CORRIDORS.keys())
        )

        all_events: List[Dict[str, Any]] = []
        indices: Dict[str, Any] = {
            "bay_area_seismic_risk_index": 0.0,
            "cushing_storage_seismic_risk_index": 0.0,
            "socal_refining_seismic_risk_index": 0.0,
            "mid_atlantic_seismic_risk_index": 0.0,
            "new_madrid_seismic_risk_index": 0.0,
            "composite_seismic_risk_index": 0.0,
            "is_pipeline_emergency_shutdown_risk": False,
            "is_refinery_inspection_advisory": False,
            "max_magnitude": 0.0,
            "total_significant_quakes": 0
        }

        start_time = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S")
        end_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

        status = "SUCCESS"
        corridor_data: Dict[str, Any] = {}

        for corr_id in corridors_to_process:
            corr_cfg = SEISMIC_CORRIDORS[corr_id]
            effective_min_mag = min_mag if min_mag is not None else corr_cfg["default_min_mag"]
            bbox = corr_cfg["bbox"]

            url = (
                f"https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson"
                f"&starttime={start_time}&endtime={end_time}"
                f"&minmagnitude={effective_min_mag}"
                f"&minlatitude={bbox['minlatitude']}&maxlatitude={bbox['maxlatitude']}"
                f"&minlongitude={bbox['minlongitude']}&maxlongitude={bbox['maxlongitude']}"
            )

            try:
                req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as response:
                    if response.status == 200:
                        raw_json = json.loads(response.read().decode("utf-8"))
                        parsed_events = self._parse_usgs_features(raw_json, corr_id)
                        all_events.extend(parsed_events)
                        c_metrics = self._compute_corridor_indices(corr_id, parsed_events)
                        corridor_data[corr_id] = c_metrics
                    else:
                        status = "PARTIAL_FALLBACK"
                        corridor_data[corr_id] = self._generate_synthetic_baseline(corr_id)
            except Exception as e:
                logger.warning(f"Could not fetch live USGS seismic data for '{corr_id}': {e}. Using synthetic baseline.")
                status = "FALLBACK_BASELINE"
                corridor_data[corr_id] = self._generate_synthetic_baseline(corr_id)

        # Aggregate composite indices across all evaluated corridors
        composite_max = 0.0
        max_mag = 0.0
        total_quakes = len(all_events)

        for corr_id, c_data in corridor_data.items():
            corr_idx = c_data.get("corridor_risk_index", 0.0)
            composite_max = max(composite_max, corr_idx)
            max_mag = max(max_mag, c_data.get("max_magnitude", 0.0))

            if corr_id == "bay_area":
                indices["bay_area_seismic_risk_index"] = corr_idx
            elif corr_id == "cushing_ok":
                indices["cushing_storage_seismic_risk_index"] = corr_idx
            elif corr_id == "socal":
                indices["socal_refining_seismic_risk_index"] = corr_idx
            elif corr_id == "mid_atlantic":
                indices["mid_atlantic_seismic_risk_index"] = corr_idx
            elif corr_id == "new_madrid":
                indices["new_madrid_seismic_risk_index"] = corr_idx

        indices["composite_seismic_risk_index"] = round(composite_max, 4)
        indices["max_magnitude"] = round(max_mag, 2)
        indices["total_significant_quakes"] = total_quakes
        indices["is_refinery_inspection_advisory"] = bool(composite_max >= 0.25)
        indices["is_pipeline_emergency_shutdown_risk"] = bool(composite_max >= 0.50)

        result = {
            "status": status,
            "source": "USGS Earthquake Hazards Program (earthquake.usgs.gov)",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "filtered_corridor": corridor,
            "temporal_window_days": days,
            "events": all_events,
            "corridors": corridor_data,
            "indices": indices
        }

        global_cache.set(cache_key, result)
        return result

    def _parse_usgs_features(self, geojson_data: Dict[str, Any], corridor_id: str) -> List[Dict[str, Any]]:
        """Parses raw USGS GeoJSON features into structured impact events."""
        features = geojson_data.get("features", [])
        parsed = []
        corr_cfg = SEISMIC_CORRIDORS.get(corridor_id, {})
        assets = corr_cfg.get("assets", {})
        m_base = corr_cfg.get("m_base", 4.2)

        for feat in features:
            props = feat.get("properties", {})
            geom = feat.get("geometry", {})
            coords = geom.get("coordinates", [0, 0, 10.0])
            lon = coords[0]
            lat = coords[1]
            depth_km = coords[2] if len(coords) > 2 else 10.0

            mag = float(props.get("mag") or 0.0)
            place = props.get("place", "Unknown Location")
            epoch_time_ms = props.get("time", 0)
            dt_val = datetime.fromtimestamp(epoch_time_ms / 1000.0, tz=timezone.utc)
            date_str = dt_val.strftime("%Y-%m-%d")
            time_iso = dt_val.strftime("%Y-%m-%dT%H:%M:%SZ")

            # Compute facility proximity and shaking intensity
            asset_impacts = {}
            max_facility_shock = 0.0
            closest_facility = None
            min_dist_km = float("inf")

            for asset_key, asset in assets.items():
                d_km = haversine_distance_km(lat, lon, asset["lat"], asset["lon"])
                hypo_dist = calculate_hypocentral_distance_km(d_km, depth_km)
                shock = calculate_asset_seismic_shock(
                    mag=mag,
                    hypocenter_dist_km=hypo_dist,
                    m_base=m_base,
                    criticality=asset.get("criticality", 1.0)
                )
                asset_impacts[asset_key] = {
                    "asset_name": asset["name"],
                    "distance_km": round(d_km, 2),
                    "hypocenter_dist_km": round(hypo_dist, 2),
                    "shock_intensity": round(shock, 4)
                }
                if shock > max_facility_shock:
                    max_facility_shock = shock
                if d_km < min_dist_km:
                    min_dist_km = d_km
                    closest_facility = asset["name"]

            parsed.append({
                "id": feat.get("id", ""),
                "corridor": corridor_id,
                "magnitude": mag,
                "place": place,
                "date": date_str,
                "timestamp_utc": time_iso,
                "latitude": round(lat, 4),
                "longitude": round(lon, 4),
                "depth_km": round(depth_km, 2),
                "mmi": props.get("mmi"),
                "alert": props.get("alert"),
                "felt": props.get("felt"),
                "max_facility_shock": round(max_facility_shock, 4),
                "closest_facility": closest_facility,
                "closest_distance_km": round(min_dist_km, 2),
                "asset_impacts": asset_impacts
            })

        # Sort descending by facility shock then magnitude
        parsed.sort(key=lambda x: (x["max_facility_shock"], x["magnitude"]), reverse=True)
        return parsed

    def _compute_corridor_indices(self, corridor_id: str, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculates normalized aggregate risk indices for a single corridor."""
        if not events:
            return {
                "corridor_risk_index": 0.0,
                "max_magnitude": 0.0,
                "active_events_count": 0,
                "highest_impact_event": None
            }

        max_shock = max(e["max_facility_shock"] for e in events)
        max_mag = max(e["magnitude"] for e in events)

        # Decay historical shocks over the 30-day window
        now_dt = datetime.now(timezone.utc)
        decayed_shocks = []
        for e in events:
            ev_dt = datetime.strptime(e["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            days_ago = max(0, (now_dt - ev_dt).days)
            # Half-life of 4.5 days for physical inspection recovery
            decay = math.exp(-0.693 * days_ago / 4.5)
            decayed_shocks.append(e["max_facility_shock"] * decay)

        corridor_risk = min(1.0, max(decayed_shocks) if decayed_shocks else 0.0)

        return {
            "corridor_risk_index": round(corridor_risk, 4),
            "max_magnitude": round(max_mag, 2),
            "active_events_count": len(events),
            "highest_impact_event": events[0] if events else None
        }

    def _generate_synthetic_baseline(self, corridor_id: str) -> Dict[str, Any]:
        """Generates a nominal baseline (zero hazard) when offline or no events exist."""
        return {
            "corridor_risk_index": 0.0,
            "max_magnitude": 0.0,
            "active_events_count": 0,
            "highest_impact_event": None,
            "synthetic": True
        }

    def generate_seismic_event_headline(
        self,
        corridor: str = "bay_area",
        telemetry: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Formats a standardized macro event headline from active USGS telemetry
        for insertion into regional event dataframes (e.g. src/locations/oakland/regional.py).
        """
        data = telemetry or self.fetch_live_seismic_telemetry(corridor=corridor)
        corr_data = data.get("corridors", {}).get(corridor, {})
        risk_idx = corr_data.get("corridor_risk_index", 0.0)

        if risk_idx < 0.20:
            return None

        highest = corr_data.get("highest_impact_event")
        if not highest:
            return None

        mag = highest.get("magnitude", 0.0)
        place = highest.get("place", "Regional Corridor")
        facility = highest.get("closest_facility", "Critical Refining Infrastructure")
        dist = highest.get("closest_distance_km", 0.0)
        date_str = highest.get("date", datetime.now().strftime("%Y-%m-%d"))

        headline = (
            f"USGS reports M{mag:.1f} earthquake near {place} ({dist:.1f} km from {facility}; "
            f"Seismic Risk Index: {risk_idx:.2f}); precautionary refinery hydrocracker inspections "
            f"and pipeline emergency shutoff protocols activated."
        )

        return {
            "date": pd.to_datetime(date_str),
            "headline": headline,
            "category": f"USGS Seismic ({corridor.upper()})",
            "seismic_risk_index": risk_idx
        }
