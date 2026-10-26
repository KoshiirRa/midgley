"""
NOAA National Hurricane Center (NHC) Advisory & Spatial Cone Connector (src/nhc_hurricane.py)

Ingests active Atlantic/Gulf tropical cyclone advisories and GIS forecast cones/wind radii.
Calculates capacity-weighted physical refinery exposure scores across EIA-820 PADD 3 Gulf
Coast refineries via spatial point-in-polygon containment checks and Colonial Pipeline
Line 1/2 intake terminal risk scores. (Issues #177, #281, #634)
"""

import os
import math
import re
import urllib.request
import defusedxml.ElementTree as ET
import json
import logging
from typing import Dict, Any, List, Optional, Tuple, Sequence, Union
from datetime import datetime
from src.lookup_cache import global_cache
from src.regional_metadata import get_padd3_refineries, get_padd3_total_refinery_capacity_bpd

logger = logging.getLogger(__name__)

NHC_RSS_URL = "https://www.nhc.noaa.gov/index-at.xml"
NHC_GIS_RSS_URL = "https://www.nhc.noaa.gov/gis-at.xml"
USER_AGENT = "(MidgleyGasPriceForecaster, contact@example.com)"
NHC_VINTAGE_FILE = os.path.join("data", "nhc_hurricane_vintages.json")

# Benchmark Spatial Wind / Hazard Polygons for Deterministic Testing and Verification (Issue #634)
# 1. Eastern Gulf / Florida Panhandle (Hurricane Isaias landfall near Destin, FL):
#    Spares Western Gulf & Lower Mississippi River; intersects only MS/AL facilities (Chevron Pascagoula, Vertex Mobile).
EASTERN_GULF_ISAIAS_POLYGON: List[Tuple[float, float]] = [
    (28.0, -89.2),
    (28.0, -85.0),
    (32.0, -85.0),
    (32.0, -89.2)
]

# 2. Western Gulf / Upper Texas Coast & Southwest Louisiana (Sabine Pass / Galveston Bay / Houston landfall):
#    Directly impacts the dense Western Gulf refining epicenter (>4.4M bpd / >50% of PADD 3 capacity).
WESTERN_GULF_HURRICANE_POLYGON: List[Tuple[float, float]] = [
    (28.5, -95.5),
    (28.5, -93.0),
    (31.5, -93.0),
    (31.5, -95.5)
]


def save_nhc_vintage_record(record: dict, filepath: Optional[str] = None) -> None:
    """Appends a point-in-time NOAA NHC hurricane threat vintage record."""
    fp = filepath or NHC_VINTAGE_FILE
    if os.environ.get("TESTING") == "1" and os.path.abspath(fp) == os.path.abspath(os.path.join("data", "nhc_hurricane_vintages.json")) and os.environ.get("TEST_PERSIST_RECORD") != "1":
        return
    try:
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        vintages = []
        if os.path.exists(fp):
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    vintages = json.load(f)
            except Exception:
                vintages = []

        vintage_entry = {
            "as_of": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": record
        }
        vintages.append(vintage_entry)
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(vintages, f, indent=2)
    except Exception as e:
        logger.debug(f"Failed to persist NHC vintage record: {e}")


def get_nhc_vintages_as_of(as_of_date: str, filepath: str = NHC_VINTAGE_FILE) -> Optional[dict]:
    """Retrieves NHC observation recorded on or before as_of_date."""
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            vintages = json.load(f)
        valid = [v for v in vintages if v.get("as_of", "")[:10] <= as_of_date]
        if valid:
            return valid[-1].get("data")
    except Exception as e:
        logger.debug(f"Error reading NHC vintages: {e}")
    return None


def point_in_polygon(lat: float, lon: float, polygon: Sequence[Tuple[float, float]]) -> bool:
    """
    Determines if a geographic coordinate (lat, lon) lies inside or on the boundary of
    a polygon using the ray-casting algorithm (Jordan curve theorem).

    Args:
        lat: Latitude of query point.
        lon: Longitude of query point.
        polygon: Sequence of (lat, lon) coordinates defining the closed polygon vertices.

    Returns:
        True if the point is strictly inside or on the polygon perimeter, False otherwise.
    """
    n = len(polygon)
    if n < 3:
        return False

    # Normalize polygon by trimming redundant trailing closure vertex if present
    poly = list(polygon)
    if n > 3 and poly[0][0] == poly[-1][0] and poly[0][1] == poly[-1][1]:
        poly = poly[:-1]
        n = len(poly)

    inside = False
    j = n - 1
    for i in range(n):
        lat_i, lon_i = poly[i]
        lat_j, lon_j = poly[j]

        # Check if ray pointing north intersects line segment between vertices i and j
        if (lon_i > lon) != (lon_j > lon):
            denom = lon_j - lon_i
            if abs(denom) > 1e-12:
                intersect_lat = (lat_j - lat_i) * (lon - lon_i) / denom + lat_i
                if lat < intersect_lat:
                    inside = not inside
        j = i

    return inside


def haversine_distance_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates great-circle distance between two geographic coordinates in nautical miles (nm).
    1 nautical mile = 1.852 km; Earth radius ~ 3440.065 nm.
    """
    R_NM = 3440.065
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R_NM * c


def compass_bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates initial compass bearing (azimuth 0° to 360°) from point 1 to point 2.
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)

    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
    bearing = math.degrees(math.atan2(y, x))
    return (bearing + 360.0) % 360.0


def destination_point(lat: float, lon: float, distance_nm: float, bearing_deg: float) -> Tuple[float, float]:
    """
    Calculates destination coordinate (lat, lon) given start point, distance in nm, and bearing in degrees.
    """
    R_NM = 3440.065
    delta = distance_nm / R_NM
    theta = math.radians(bearing_deg)
    phi1 = math.radians(lat)
    lambda1 = math.radians(lon)

    phi2 = math.asin(math.sin(phi1) * math.cos(delta) + math.cos(phi1) * math.sin(delta) * math.cos(theta))
    lambda2 = lambda1 + math.atan2(
        math.sin(theta) * math.sin(delta) * math.cos(phi1),
        math.cos(delta) - math.sin(phi1) * math.sin(phi2)
    )
    return math.degrees(phi2), (math.degrees(lambda2) + 540.0) % 360.0 - 180.0


def wind_radii_to_polygon(
    center_lat: float,
    center_lon: float,
    radii_nm: Dict[str, float],
    points_per_quadrant: int = 4
) -> List[Tuple[float, float]]:
    """
    Converts 4-quadrant tropical cyclone wind radii (NE, SE, SW, NW in nautical miles)
    into a closed polygon of (lat, lon) coordinates.
    """
    quadrants = [
        ("NE", 0.0, 90.0),
        ("SE", 90.0, 180.0),
        ("SW", 180.0, 270.0),
        ("NW", 270.0, 360.0)
    ]
    vertices: List[Tuple[float, float]] = []
    for quad_key, start_deg, end_deg in quadrants:
        radius = float(radii_nm.get(quad_key, 0.0))
        if radius <= 0.0:
            vertices.append((center_lat, center_lon))
            continue
        step = (end_deg - start_deg) / points_per_quadrant
        for step_idx in range(points_per_quadrant):
            bearing = start_deg + step_idx * step
            dest = destination_point(center_lat, center_lon, radius, bearing)
            vertices.append(dest)

    if vertices:
        vertices.append(vertices[0])
    return vertices


def parse_nhc_geojson_cone(geojson_data: Union[str, dict]) -> List[List[Tuple[float, float]]]:
    """
    Parses NOAA NHC tropical cyclone forecast cone GeoJSON features into (lat, lon) polygon lists.
    Standard GeoJSON uses [longitude, latitude] coordinate ordering, which is flipped to (lat, lon).
    """
    if isinstance(geojson_data, str):
        try:
            data = json.loads(geojson_data)
        except Exception as e:
            logger.warning(f"Failed to parse GeoJSON string: {e}")
            return []
    else:
        data = geojson_data

    polygons: List[List[Tuple[float, float]]] = []
    features = data.get("features", [])
    if not features and data.get("type") in ("Polygon", "MultiPolygon"):
        features = [{"geometry": data}]

    for feat in features:
        geom = feat.get("geometry", {})
        gtype = geom.get("type")
        coords = geom.get("coordinates", [])

        if gtype == "Polygon":
            for ring in coords:
                poly = [(float(pt[1]), float(pt[0])) for pt in ring if len(pt) >= 2]
                if len(poly) >= 3:
                    polygons.append(poly)
        elif gtype == "MultiPolygon":
            for poly_coords in coords:
                for ring in poly_coords:
                    poly = [(float(pt[1]), float(pt[0])) for pt in ring if len(pt) >= 2]
                    if len(poly) >= 3:
                        polygons.append(poly)

    return polygons


def parse_nhc_kml_cone(kml_content: Union[str, bytes]) -> List[List[Tuple[float, float]]]:
    """
    Parses NOAA NHC tropical cyclone forecast cone KML into (lat, lon) polygon lists.
    Extracts coordinate strings from <coordinates> tags formatted as 'lon,lat,alt'.
    """
    if isinstance(kml_content, bytes):
        raw_text = kml_content.decode("utf-8", errors="ignore")
    else:
        raw_text = kml_content

    polygons: List[List[Tuple[float, float]]] = []
    coord_matches = re.findall(r"<coordinates>(.*?)</coordinates>", raw_text, re.DOTALL)
    for block in coord_matches:
        poly: List[Tuple[float, float]] = []
        tokens = block.strip().split()
        for tok in tokens:
            parts = tok.split(",")
            if len(parts) >= 2:
                try:
                    lon_val = float(parts[0])
                    lat_val = float(parts[1])
                    poly.append((lat_val, lon_val))
                except ValueError:
                    continue
        if len(poly) >= 3:
            polygons.append(poly)

    return polygons


def calculate_refinery_exposure(
    hazard_polygons: Optional[List[Sequence[Tuple[float, float]]]] = None,
    hazard_radii: Optional[List[Dict[str, Any]]] = None,
    refineries: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Calculates the capacity-weighted PADD 3 Gulf Coast refinery exposure score:
        Exposure Score = sum(Capacity_i in Hazard Zone) / sum(Total PADD 3 Capacity)

    Args:
        hazard_polygons: List of polygons, each defined as a list of (lat, lon) tuples.
        hazard_radii: Optional list of storm centers with quadrant radii dicts.
        refineries: Optional list of refinery specs. Defaults to EIA-820 PADD 3 registry.

    Returns:
        Dict detailing exposure score, impacted capacity, refinery breakdown, and subregion stats.
    """
    refinery_list = refineries if refineries is not None else get_padd3_refineries()
    total_capacity = get_padd3_total_refinery_capacity_bpd() if refineries is None else sum(
        r.get("operable_capacity_bpd", 0) for r in refinery_list
    )

    if not refinery_list or total_capacity <= 0:
        return {
            "exposure_score": 0.0,
            "impacted_capacity_bpd": 0,
            "total_padd3_capacity_bpd": total_capacity,
            "impacted_refinery_ids": [],
            "impacted_refineries": [],
            "subregion_exposure": {}
        }

    # Aggregate all active hazard polygons
    all_polys: List[Sequence[Tuple[float, float]]] = list(hazard_polygons or [])
    if hazard_radii:
        for hr in hazard_radii:
            c_lat = float(hr.get("latitude", 0.0))
            c_lon = float(hr.get("longitude", 0.0))
            radii = hr.get("radii_nm", {})
            if c_lat != 0.0 and c_lon != 0.0 and radii:
                all_polys.append(wind_radii_to_polygon(c_lat, c_lon, radii))

    if not all_polys:
        return {
            "exposure_score": 0.0,
            "impacted_capacity_bpd": 0,
            "total_padd3_capacity_bpd": total_capacity,
            "impacted_refinery_ids": [],
            "impacted_refineries": [],
            "subregion_exposure": {}
        }

    impacted_refineries: List[Dict[str, Any]] = []
    impacted_capacity = 0
    subregion_stats: Dict[str, Dict[str, Any]] = {}

    for ref in refinery_list:
        subreg = ref.get("subregion", "Other PADD 3")
        cap = int(ref.get("operable_capacity_bpd", 0))

        if subreg not in subregion_stats:
            subregion_stats[subreg] = {"total_bpd": 0, "impacted_bpd": 0, "refineries": []}
        subregion_stats[subreg]["total_bpd"] += cap

        r_lat = float(ref.get("latitude", 0.0))
        r_lon = float(ref.get("longitude", 0.0))

        # Check intersection against any hazard zone polygon
        is_hit = False
        for poly in all_polys:
            if point_in_polygon(r_lat, r_lon, poly):
                is_hit = True
                break

        if is_hit:
            impacted_capacity += cap
            subregion_stats[subreg]["impacted_bpd"] += cap
            subregion_stats[subreg]["refineries"].append(ref.get("refinery_id"))
            impacted_refineries.append({
                "refinery_id": ref.get("refinery_id"),
                "company": ref.get("company"),
                "facility": ref.get("facility"),
                "city": ref.get("city"),
                "state": ref.get("state"),
                "subregion": subreg,
                "latitude": r_lat,
                "longitude": r_lon,
                "operable_capacity_bpd": cap
            })

    exposure_score = round(impacted_capacity / total_capacity, 4) if total_capacity > 0 else 0.0

    # Calculate subregion percentages
    for subreg, sdata in subregion_stats.items():
        tot = sdata["total_bpd"]
        imp = sdata["impacted_bpd"]
        sdata["exposure_pct"] = round((imp / tot) * 100.0, 2) if tot > 0 else 0.0

    return {
        "exposure_score": exposure_score,
        "impacted_capacity_bpd": impacted_capacity,
        "total_padd3_capacity_bpd": total_capacity,
        "impacted_refinery_ids": [r["refinery_id"] for r in impacted_refineries],
        "impacted_refineries": impacted_refineries,
        "subregion_exposure": subregion_stats
    }


class NHCHurricaneConnector:
    """
    Zero-Cost NOAA NHC Tropical Cyclone Advisory & Spatial Cone Connector.
    Parses active Atlantic & Gulf tropical storm/hurricane advisories, wind radii swaths,
    and forecast cone polygons to calculate spatial refining exposure scores across PADD 3.
    (Issues #177, #281, #634)
    """
    def __init__(self):
        self.is_free_alternative = True
        self.cost_per_query = 0.0

    def get_synthetic_fixture(self, scenario: str = "default") -> Dict[str, Any]:
        """
        Returns deterministic synthetic hurricane threat fixtures for offline deterministic testing.
        Supported scenarios:
          - 'eastern_gulf' / 'isaias': Hurricane Isaias Destin FL landfall affecting MS/AL facilities (<15% exposure).
          - 'western_gulf': Upper Texas Coast / SW Louisiana landfall affecting refining epicenter (>50% exposure).
          - 'quiescent': 0 active storms, 0 threat index, 0 refinery exposure.
          - 'default': Standard baseline response with valid schema.
        """
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if scenario in ("eastern_gulf", "isaias", "florida_panhandle"):
            exposure = calculate_refinery_exposure(hazard_polygons=[EASTERN_GULF_ISAIAS_POLYGON])
            return {
                "source": "NOAA National Hurricane Center (Synthetic Fixture: Hurricane Isaias Eastern Gulf)",
                "timestamp": timestamp_str,
                "active_storms_count": 1,
                "gulf_hurricane_active": True,
                "nhc_hurricane_threat_index": 0.65,
                "nhc_gulf_refinery_exposure_score": exposure["exposure_score"],
                "nhc_colonial_pipeline_risk_score": 0.15,
                "impacted_capacity_bpd": exposure["impacted_capacity_bpd"],
                "total_padd3_capacity_bpd": exposure["total_padd3_capacity_bpd"],
                "impacted_refineries": exposure["impacted_refineries"],
                "subregion_exposure": exposure["subregion_exposure"],
                "active_advisories": [
                    {
                        "title": "Hurricane ISAIAS Advisory Number 18",
                        "description": "Category 2 Hurricane Isaias makes landfall near Destin, FL. Outer tropical storm force winds brush Mississippi Sound and Mobile Bay."
                    }
                ],
                "status": "SUCCESS"
            }

        if scenario in ("western_gulf", "upper_texas", "texas_louisiana"):
            exposure = calculate_refinery_exposure(hazard_polygons=[WESTERN_GULF_HURRICANE_POLYGON])
            return {
                "source": "NOAA National Hurricane Center (Synthetic Fixture: Western Gulf Refining Epicenter)",
                "timestamp": timestamp_str,
                "active_storms_count": 1,
                "gulf_hurricane_active": True,
                "nhc_hurricane_threat_index": 0.85,
                "nhc_gulf_refinery_exposure_score": exposure["exposure_score"],
                "nhc_colonial_pipeline_risk_score": 0.90,
                "impacted_capacity_bpd": exposure["impacted_capacity_bpd"],
                "total_padd3_capacity_bpd": exposure["total_padd3_capacity_bpd"],
                "impacted_refineries": exposure["impacted_refineries"],
                "subregion_exposure": exposure["subregion_exposure"],
                "active_advisories": [
                    {
                        "title": "Hurricane BERYL Advisory Number 24",
                        "description": "Major Hurricane tracking into Upper Texas Coast and Southwest Louisiana with catastrophic storm surge and hurricane-force winds across Houston, Galveston, and Port Arthur."
                    }
                ],
                "status": "SUCCESS"
            }

        if scenario in ("quiescent", "no_storm"):
            return {
                "source": "NOAA National Hurricane Center (Synthetic Fixture: Quiescent Basin)",
                "timestamp": timestamp_str,
                "active_storms_count": 0,
                "gulf_hurricane_active": False,
                "nhc_hurricane_threat_index": 0.0,
                "nhc_gulf_refinery_exposure_score": 0.0,
                "nhc_colonial_pipeline_risk_score": 0.0,
                "impacted_capacity_bpd": 0,
                "total_padd3_capacity_bpd": get_padd3_total_refinery_capacity_bpd(),
                "impacted_refineries": [],
                "subregion_exposure": {},
                "active_advisories": [],
                "status": "SUCCESS"
            }

        # Default fixture
        return {
            "source": "NOAA National Hurricane Center (Synthetic Test Fixture)",
            "timestamp": timestamp_str,
            "active_storms_count": 0,
            "gulf_hurricane_active": False,
            "nhc_hurricane_threat_index": 0.0,
            "nhc_gulf_refinery_exposure_score": 0.0,
            "nhc_colonial_pipeline_risk_score": 0.0,
            "impacted_capacity_bpd": 0,
            "total_padd3_capacity_bpd": get_padd3_total_refinery_capacity_bpd(),
            "impacted_refineries": [],
            "subregion_exposure": {},
            "active_advisories": [],
            "status": "SUCCESS"
        }

    def fetch_active_hurricane_threats(
        self,
        spatial_zones: Optional[List[Sequence[Tuple[float, float]]]] = None,
        test_scenario: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetches active NHC advisories and calculates spatial refining exposure scores.
        Under TESTING=1 (without live network permissions or when monkeypatched), provides
        deterministic offline synthetic fixtures.
        """
        # Explicit test scenario requested or configured via environment
        scenario = test_scenario or os.environ.get("TEST_NHC_SCENARIO")
        if scenario:
            return self.get_synthetic_fixture(scenario)

        # Fast path under TESTING=1 if urllib.request.urlopen is not monkeypatched and network is suppressed
        is_mocked_urlopen = getattr(urllib.request.urlopen, "__module__", "") != "urllib.request"
        if os.environ.get("TESTING") == "1" and not is_mocked_urlopen and os.environ.get("TEST_ALLOW_NETWORK") != "1":
            return self.get_synthetic_fixture("default")

        hour_bucket = datetime.now().strftime("%Y-%m-%d-%H")
        cache_key = f"nhc_hurricane_threats:{hour_bucket}"
        cached = global_cache.get(cache_key)
        if cached and isinstance(cached, dict) and not is_mocked_urlopen:
            logger.info("Loaded NHC hurricane advisory data from lookup cache.")
            return cached

        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total_padd3_cap = get_padd3_total_refinery_capacity_bpd()
        result = {
            "source": "NOAA National Hurricane Center (Zero-Cost Public Feed)",
            "timestamp": timestamp_str,
            "active_storms_count": 0,
            "gulf_hurricane_active": False,
            "nhc_hurricane_threat_index": 0.0,
            "nhc_gulf_refinery_exposure_score": 0.0,
            "nhc_colonial_pipeline_risk_score": 0.0,
            "impacted_capacity_bpd": 0,
            "total_padd3_capacity_bpd": total_padd3_cap,
            "impacted_refineries": [],
            "subregion_exposure": {},
            "active_advisories": [],
            "status": "SUCCESS"
        }

        try:
            req = urllib.request.Request(NHC_RSS_URL, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=5) as response:
                xml_bytes = response.read()
                items = []
                try:
                    root = ET.fromstring(xml_bytes)
                    for item in root.findall(".//item"):
                        items.append((item.findtext("title", ""), item.findtext("description", "")))
                except Exception:
                    raw_text = xml_bytes.decode('utf-8', errors='ignore')
                    item_blocks = re.findall(r'<item>(.*?)</item>', raw_text, re.DOTALL)
                    for block in item_blocks:
                        t_match = re.search(r'<title>(.*?)</title>', block, re.DOTALL)
                        d_match = re.search(r'<description>(.*?)</description>', block, re.DOTALL)
                        title_val = t_match.group(1).strip() if t_match else ""
                        desc_val = d_match.group(1).strip() if d_match else ""
                        items.append((title_val, desc_val))

                advisories = []
                threat_score = 0.0
                gulf_active = False

                for title, description in items:
                    title_lower = title.lower()
                    if any(kw in title_lower for kw in ["tropical storm", "hurricane", "tropical depression"]):
                        advisories.append({"title": title, "description": description[:200]})

                        # Score threat levels
                        if "hurricane" in title_lower:
                            threat_score += 0.40
                        elif "tropical storm" in title_lower:
                            threat_score += 0.20

                        # Check for Gulf of Mexico or Caribbean location mentions
                        desc_lower = description.lower()
                        if any(loc in desc_lower or loc in title_lower for loc in ["gulf of mexico", "gulf coast", "louisiana", "texas", "florida"]):
                            gulf_active = True
                            threat_score += 0.30

                threat_score = min(threat_score, 1.0)
                result["active_storms_count"] = len(advisories)
                result["gulf_hurricane_active"] = gulf_active
                result["nhc_hurricane_threat_index"] = round(threat_score, 4)

                # Spatial refinery exposure calculation
                hazard_polys = list(spatial_zones or [])
                if hazard_polys:
                    exposure = calculate_refinery_exposure(hazard_polygons=hazard_polys)
                    result["nhc_gulf_refinery_exposure_score"] = exposure["exposure_score"]
                    result["impacted_capacity_bpd"] = exposure["impacted_capacity_bpd"]
                    result["impacted_refineries"] = exposure["impacted_refineries"]
                    result["subregion_exposure"] = exposure["subregion_exposure"]
                    # Colonial Pipeline intake risk aligns with Western Gulf / Upper Texas exposure
                    west_gulf_imp = exposure["subregion_exposure"].get("Western Gulf (Houston Ship Channel)", {}).get("impacted_bpd", 0) + \
                                    exposure["subregion_exposure"].get("Western Gulf (Galveston Bay)", {}).get("impacted_bpd", 0) + \
                                    exposure["subregion_exposure"].get("Western Gulf (Upper Texas Coast)", {}).get("impacted_bpd", 0)
                    if west_gulf_imp > 0:
                        result["nhc_colonial_pipeline_risk_score"] = min(1.0, round(exposure["exposure_score"] * 1.5, 4))
                    else:
                        result["nhc_colonial_pipeline_risk_score"] = round(exposure["exposure_score"] * 0.8, 4)
                elif gulf_active:
                    # In absence of direct GIS polygons, use proportional baseline calibrated by threat index
                    exposure_score = round(threat_score * 0.5, 4)
                    result["nhc_gulf_refinery_exposure_score"] = exposure_score
                    result["nhc_colonial_pipeline_risk_score"] = round(threat_score * 0.6, 4)
                else:
                    result["nhc_gulf_refinery_exposure_score"] = 0.0
                    result["nhc_colonial_pipeline_risk_score"] = 0.0

                result["active_advisories"] = advisories
        except Exception as e:
            logger.warning(f"Could not fetch live NHC hurricane advisories: {e}")
            result["status"] = f"PARTIAL_FALLBACK: {e}"

        save_nhc_vintage_record(result)
        global_cache.set(cache_key, result, ttl_seconds=10800)
        return result
