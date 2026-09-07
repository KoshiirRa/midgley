"""
U.S. Census Bureau Demographics & Commuter Metrics Connector Module (src/census_demographics.py)

Provides zero-cost MSA- and county-level demographic indicators:
- Household vehicle availability (B08201)
- Means of transportation to work / commute mode split (B08301)
- Mean travel time to work / commute duration (B08013 / B08303)
- Derived captive fuel demand inelasticity scores

Features an Adaptive Annual Release Window Caching Engine:
- Actively polls during the annual September release window (Sept 1 – Sept 30) for new ACS-1 vintages.
- Locks long-term cache forward (~335+ days until next August 31st) once the new vintage is confirmed.
- 100% free public government API (api.census.gov) with deterministic offline fallback profiles.
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, date
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CENSUS_CACHE_FILE = os.path.join(PROJECT_ROOT, "data", "census_demographics_cache.json")

# Target Metro Area to Census Geography Mappings (MSA / CBSA & County FIPS)
METRO_CENSUS_MAPPINGS: Dict[str, Dict[str, Any]] = {
    "tulsa_ok": {
        "display_name": "Tulsa, OK Metro",
        "msa_fips": "46140",  # Tulsa, OK Metro Area
        "state_fips": "40",
        "county_fips": "143", # Tulsa County
        "default_baseline": {
            "vintage_year": 2024,
            "total_households": 420500,
            "zero_vehicle_pct": 5.4,
            "vehicles_per_household": 1.95,
            "drive_alone_share": 0.825,
            "carpool_share": 0.092,
            "public_transit_share": 0.007,
            "work_from_home_share": 0.062,
            "mean_commute_minutes": 21.8,
            "vehicle_dependency_ratio": 0.917,
            "transit_alternative_index": 0.038,
            "inelastic_demand_score": 0.885
        }
    },
    "newark_de": {
        "display_name": "Newark, DE / Philly Corridor",
        "msa_fips": "37980",  # Philadelphia-Camden-Wilmington, PA-NJ-DE-MD
        "state_fips": "10",
        "county_fips": "003", # New Castle County
        "default_baseline": {
            "vintage_year": 2024,
            "total_households": 225000,
            "zero_vehicle_pct": 7.8,
            "vehicles_per_household": 1.74,
            "drive_alone_share": 0.742,
            "carpool_share": 0.078,
            "public_transit_share": 0.045,
            "work_from_home_share": 0.118,
            "mean_commute_minutes": 26.4,
            "vehicle_dependency_ratio": 0.820,
            "transit_alternative_index": 0.104,
            "inelastic_demand_score": 0.732
        }
    },
    "cincinnati_oh": {
        "display_name": "Cincinnati, OH Tri-State",
        "msa_fips": "17140",  # Cincinnati, OH-KY-IN
        "state_fips": "39",
        "county_fips": "061", # Hamilton County
        "default_baseline": {
            "vintage_year": 2024,
            "total_households": 905000,
            "zero_vehicle_pct": 6.2,
            "vehicles_per_household": 1.86,
            "drive_alone_share": 0.795,
            "carpool_share": 0.075,
            "public_transit_share": 0.024,
            "work_from_home_share": 0.092,
            "mean_commute_minutes": 25.1,
            "vehicle_dependency_ratio": 0.870,
            "transit_alternative_index": 0.070,
            "inelastic_demand_score": 0.814
        }
    },
    "greenville_nc": {
        "display_name": "Greenville, NC Metro",
        "msa_fips": "24780",  # Greenville, NC Metro Area
        "state_fips": "37",
        "county_fips": "147", # Pitt County
        "default_baseline": {
            "vintage_year": 2024,
            "total_households": 76500,
            "zero_vehicle_pct": 6.8,
            "vehicles_per_household": 1.88,
            "drive_alone_share": 0.831,
            "carpool_share": 0.088,
            "public_transit_share": 0.011,
            "work_from_home_share": 0.058,
            "mean_commute_minutes": 21.2,
            "vehicle_dependency_ratio": 0.919,
            "transit_alternative_index": 0.040,
            "inelastic_demand_score": 0.879
        }
    },
    "oakland_ca": {
        "display_name": "Oakland / SF Bay Area, CA",
        "msa_fips": "41860",  # San Francisco-Oakland-Berkeley, CA
        "state_fips": "06",
        "county_fips": "001", # Alameda County
        "default_baseline": {
            "vintage_year": 2024,
            "total_households": 1820000,
            "zero_vehicle_pct": 11.5,
            "vehicles_per_household": 1.62,
            "drive_alone_share": 0.585,
            "carpool_share": 0.085,
            "public_transit_share": 0.125,
            "work_from_home_share": 0.185,
            "mean_commute_minutes": 32.5,
            "vehicle_dependency_ratio": 0.670,
            "transit_alternative_index": 0.218,
            "inelastic_demand_score": 0.548
        }
    },
    "charlotte_nc": {
        "display_name": "Charlotte, NC Metro",
        "msa_fips": "16740",  # Charlotte-Concord-Gastonia, NC-SC
        "state_fips": "37",
        "county_fips": "119", # Mecklenburg County
        "default_baseline": {
            "vintage_year": 2024,
            "total_households": 1100000,
            "zero_vehicle_pct": 4.9,
            "vehicles_per_household": 1.91,
            "drive_alone_share": 0.778,
            "carpool_share": 0.082,
            "public_transit_share": 0.021,
            "work_from_home_share": 0.105,
            "mean_commute_minutes": 27.8,
            "vehicle_dependency_ratio": 0.860,
            "transit_alternative_index": 0.074,
            "inelastic_demand_score": 0.821
        }
    },
    "port_st_lucie_fl": {
        "display_name": "Port St. Lucie, FL Metro",
        "msa_fips": "38940",  # Port St. Lucie, FL Metro Area
        "state_fips": "12",
        "county_fips": "111", # St. Lucie County
        "default_baseline": {
            "vintage_year": 2024,
            "total_households": 215000,
            "zero_vehicle_pct": 4.1,
            "vehicles_per_household": 1.94,
            "drive_alone_share": 0.812,
            "carpool_share": 0.080,
            "public_transit_share": 0.006,
            "work_from_home_share": 0.088,
            "mean_commute_minutes": 28.5,
            "vehicle_dependency_ratio": 0.892,
            "transit_alternative_index": 0.050,
            "inelastic_demand_score": 0.868
        }
    }
}


def get_census_release_window_status(current_date: Optional[date] = None) -> Dict[str, Any]:
    """
    Evaluates whether the given date falls inside the annual ACS 1-Year Release Window (Sept 1 – Sept 30).
    Computes expected vintage and dynamic cache TTL.
    """
    if current_date is None:
        now_dt = datetime.now()
        current_date = now_dt.date()
    elif isinstance(current_date, datetime):
        current_date = current_date.date()

    year = current_date.year
    month = current_date.month
    day = current_date.day

    # Annual September release window
    is_in_release_window = (month == 9)

    # Expected latest published vintage:
    # Before September release of year Y, latest available is Y-2.
    # During or after September of year Y, latest expected is Y-1.
    if month < 9:
        expected_vintage = year - 2
        next_window_start = date(year, 9, 1)
    elif month == 9:
        expected_vintage = year - 1
        next_window_start = date(year, 9, 1)
    else:
        expected_vintage = year - 1
        next_window_start = date(year + 1, 9, 1)

    # Calculate remaining days until next August 31st (end of locked period)
    if month <= 8:
        locked_until_date = date(year, 8, 31)
    else:
        locked_until_date = date(year + 1, 8, 31)

    seconds_until_locked_end = max(86400, int((datetime.combine(locked_until_date, datetime.min.time()) - datetime.combine(current_date, datetime.min.time())).total_seconds()))

    if is_in_release_window:
        status_mode = "WINDOW_ACTIVE_CHECKING"
        ttl_seconds = 86400  # 24 hours daily polling within release month
        status_desc = f"Inside annual ACS release window (Sept 1-30). Checking daily for {expected_vintage} vintage release."
    else:
        status_mode = "LOCKED_ANNUAL_CACHE"
        ttl_seconds = seconds_until_locked_end
        status_desc = f"Outside release window. Locked on {expected_vintage} vintage until {locked_until_date.isoformat()}."

    return {
        "current_date": current_date.isoformat(),
        "is_in_release_window": is_in_release_window,
        "release_window_name": f"ACS 1-Year Annual Window ({year})",
        "expected_vintage": expected_vintage,
        "status_mode": status_mode,
        "recommended_ttl_seconds": ttl_seconds,
        "locked_until": locked_until_date.isoformat(),
        "description": status_desc
    }


def compute_derived_commuter_metrics(raw_acs: Dict[str, Any], vintage_year: int) -> Dict[str, Any]:
    """
    Computes standardized econometric commuter indicators and captive demand inelasticity score
    from raw ACS variables.
    """
    total_hh = max(1, raw_acs.get("B08201_001E", 100000))
    no_veh = raw_acs.get("B08201_002E", 0)
    one_veh = raw_acs.get("B08201_003E", 0)
    two_veh = raw_acs.get("B08201_004E", 0)
    three_veh = raw_acs.get("B08201_005E", 0)
    four_plus_veh = raw_acs.get("B08201_006E", 0)

    # Average vehicles per household
    weighted_veh = (0 * no_veh + 1 * one_veh + 2 * two_veh + 3 * three_veh + 4 * four_plus_veh)
    veh_per_hh = round(weighted_veh / total_hh, 2) if total_hh > 0 else 1.85
    zero_veh_pct = round((no_veh / total_hh) * 100.0, 1)

    total_workers = max(1, raw_acs.get("B08301_001E", 100000))
    drove_alone = raw_acs.get("B08301_003E", 0)
    carpooled = raw_acs.get("B08301_004E", 0)
    transit = raw_acs.get("B08301_010E", 0)
    wfh = raw_acs.get("B08301_021E", 0)

    drive_alone_share = round(drove_alone / total_workers, 4)
    carpool_share = round(carpooled / total_workers, 4)
    transit_share = round(transit / total_workers, 4)
    wfh_share = round(wfh / total_workers, 4)

    vehicle_dep_ratio = round((drove_alone + carpooled) / total_workers, 4)
    transit_alt_index = round(transit_share + (0.5 * wfh_share), 4)

    # Mean commute duration (minutes)
    agg_travel_time = raw_acs.get("B08013_001E", 0)
    commuting_workers = max(1, total_workers - wfh)
    mean_commute = round(agg_travel_time / commuting_workers, 1) if agg_travel_time > 0 else 24.5

    # Composite Inelastic Captive Gasoline Demand Score (0.0 to 1.0)
    # Higher score = more captive driving demand = lower price elasticity
    raw_inelasticity = (
        (0.50 * vehicle_dep_ratio) +
        (0.25 * min(1.2, veh_per_hh / 2.0)) +
        (0.25 * min(1.2, mean_commute / 30.0)) -
        (0.20 * min(1.0, transit_alt_index * 2.5))
    )
    inelastic_score = round(max(0.10, min(0.99, raw_inelasticity)), 3)

    return {
        "vintage_year": vintage_year,
        "total_households": total_hh,
        "zero_vehicle_pct": zero_veh_pct,
        "vehicles_per_household": veh_per_hh,
        "drive_alone_share": drive_alone_share,
        "carpool_share": carpool_share,
        "public_transit_share": transit_share,
        "work_from_home_share": wfh_share,
        "mean_commute_minutes": mean_commute,
        "vehicle_dependency_ratio": vehicle_dep_ratio,
        "transit_alternative_index": transit_alt_index,
        "inelastic_demand_score": inelastic_score
    }


class CensusDemographicsConnector:
    """
    Zero-Cost U.S. Census Bureau Demographics & Commuter Metrics Client.
    Integrates ACS-1 and ACS-5 surveys with adaptive annual release window caching.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("CENSUS_API_KEY")
        self.is_free_alternative = True
        self.cost_per_query = 0.0
        self._disk_cache = self._load_disk_cache()

    def _load_disk_cache(self) -> Dict[str, Any]:
        if os.path.exists(CENSUS_CACHE_FILE):
            try:
                with open(CENSUS_CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not read Census disk cache: {e}")
        return {}

    def _save_disk_cache(self):
        try:
            os.makedirs(os.path.dirname(CENSUS_CACHE_FILE), exist_ok=True)
            with open(CENSUS_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self._disk_cache, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not write Census disk cache: {e}")

    def fetch_live_census_acs(
        self,
        msa_fips: str,
        state_fips: str,
        county_fips: str,
        target_vintage: int
    ) -> Optional[Dict[str, Any]]:
        """
        Queries api.census.gov for ACS 1-Year variables. Falls back to ACS 5-Year if 1-Year is 404.
        """
        variables = [
            "B08201_001E", "B08201_002E", "B08201_003E", "B08201_004E", "B08201_005E", "B08201_006E",
            "B08301_001E", "B08301_003E", "B08301_004E", "B08301_010E", "B08301_021E",
            "B08013_001E"
        ]
        var_str = ",".join(variables)

        # Try MSA first, fallback to County
        endpoints = [
            f"https://api.census.gov/data/{target_vintage}/acs/acs1?get={var_str}&for=metropolitan%20statistical%20area/micropolitan%20statistical%20area:{msa_fips}",
            f"https://api.census.gov/data/{target_vintage}/acs/acs1?get={var_str}&for=county:{county_fips}&in=state:{state_fips}",
            f"https://api.census.gov/data/{target_vintage}/acs/acs5?get={var_str}&for=county:{county_fips}&in=state:{state_fips}"
        ]

        for url in endpoints:
            if self.api_key:
                url += f"&key={self.api_key}"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Midgley-EnergyAnalytics/1.0"})
                with urllib.request.urlopen(req, timeout=4) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode('utf-8'))
                        if len(data) >= 2:
                            headers = data[0]
                            row = data[1]
                            parsed = {}
                            for h, val in zip(headers, row):
                                if h in variables:
                                    try:
                                        parsed[h] = int(val) if val is not None else 0
                                    except ValueError:
                                        parsed[h] = 0
                            return parsed
            except urllib.error.HTTPError as he:
                if he.code == 404:
                    logger.debug(f"Census ACS {target_vintage} endpoint not yet released or 404: {url}")
                else:
                    logger.debug(f"Census API HTTP error {he.code}: {he}")
            except Exception as ex:
                logger.debug(f"Census API network lookup exception: {ex}")

        return None

    def get_metro_demographics(
        self,
        region_id: str,
        current_date: Optional[date] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Retrieves commuter and vehicle availability demographics for region_id.
        Manages the adaptive annual release window lifecycle and tiered caching.
        """
        reg_clean = region_id.lower().strip()
        mapping = METRO_CENSUS_MAPPINGS.get(reg_clean, METRO_CENSUS_MAPPINGS["tulsa_ok"])
        
        window_status = get_census_release_window_status(current_date)
        target_vintage = window_status["expected_vintage"]
        cache_key = f"census_demographics_{reg_clean}"

        # 1. Check in-memory / disk cache if not forcing refresh
        cached_entry = self._disk_cache.get(cache_key)
        if cached_entry and not force_refresh:
            cached_vintage = cached_entry.get("demographics", {}).get("vintage_year", 0)
            
            # If not in release window and we already have a cached record, serve it immediately
            if not window_status["is_in_release_window"] and cached_vintage > 0:
                return {
                    "region_id": reg_clean,
                    "display_name": mapping["display_name"],
                    "window_lifecycle": window_status,
                    "demographics": cached_entry["demographics"],
                    "cache_status": "HIT_LOCKED_ANNUAL",
                    "provenance": "Census_ACS_DiskCache",
                    "is_free_alternative": True,
                    "cost_per_query": 0.0
                }

            # If in release window and we already confirmed the expected vintage, serve it
            if window_status["is_in_release_window"] and cached_vintage >= target_vintage:
                return {
                    "region_id": reg_clean,
                    "display_name": mapping["display_name"],
                    "window_lifecycle": window_status,
                    "demographics": cached_entry["demographics"],
                    "cache_status": "HIT_NEW_VINTAGE_LOCKED",
                    "provenance": "Census_ACS_DiskCache",
                    "is_free_alternative": True,
                    "cost_per_query": 0.0
                }

        # 2. Attempt Live Census API Ingestion for expected vintage
        live_raw = self.fetch_live_census_acs(
            msa_fips=mapping["msa_fips"],
            state_fips=mapping["state_fips"],
            county_fips=mapping["county_fips"],
            target_vintage=target_vintage
        )

        if live_raw:
            metrics = compute_derived_commuter_metrics(live_raw, vintage_year=target_vintage)
            cache_status = "LIVE_VINTAGE_UPGRADE_FETCHED"
            provenance = f"US_Census_Bureau_ACS_{target_vintage}_Live"
        else:
            # If expected vintage not yet released or offline, check if we have prior cached vintage
            if cached_entry and "demographics" in cached_entry:
                metrics = cached_entry["demographics"]
                cache_status = "WINDOW_POLLING_SERVED_PRIOR_VINTAGE"
                provenance = "Census_ACS_Prior_Vintage_Cache"
            else:
                # Deterministic fallback baseline
                metrics = mapping["default_baseline"]
                cache_status = "DETERMINISTIC_BASELINE_FALLBACK"
                provenance = "Census_Deterministic_Baseline_Profile"

        # Update cache entry
        result_record = {
            "demographics": metrics,
            "last_checked": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "target_vintage": target_vintage,
            "status_mode": window_status["status_mode"]
        }
        self._disk_cache[cache_key] = result_record
        self._save_disk_cache()

        return {
            "region_id": reg_clean,
            "display_name": mapping["display_name"],
            "window_lifecycle": window_status,
            "demographics": metrics,
            "cache_status": cache_status,
            "provenance": provenance,
            "is_free_alternative": True,
            "cost_per_query": 0.0
        }

    def get_all_metro_demographics(self, current_date: Optional[date] = None) -> Dict[str, Any]:
        """Returns demographic profiles across all supported metro areas."""
        results = {}
        for reg in METRO_CENSUS_MAPPINGS:
            results[reg] = self.get_metro_demographics(reg, current_date=current_date)
        return {
            "connector": "U.S. Census Bureau ACS Demographics Connector",
            "is_free_alternative": True,
            "cost_per_query": 0.0,
            "supported_metros_count": len(results),
            "metros": results,
            "status": "SUCCESS"
        }
