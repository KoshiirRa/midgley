"""
GeoPandas Spatial Refinery Distance Buffering Engine (src/spatial_refinery.py)

Provides geospatial distance-decay calculations, refinery buffer polygon generation,
and spatial shock attenuation modeling for regional metro calibration agents.
"""

import math
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
import pandas as pd

logger = logging.getLogger(__name__)

# Check if GeoPandas and Shapely are available
try:
    import geopandas as gpd
    from shapely.geometry import Point, Polygon
    HAS_GEOPANDAS = True
except ImportError:
    HAS_GEOPANDAS = False
    gpd = None
    Point = None
    Polygon = None
    logger.info("GeoPandas or Shapely not installed. Falling back to spherical Haversine geospatial engine.")

# Authoritative Refining Assets, Pipelines, and Petroleum Marine Terminals
REFINERY_DATA: Dict[str, Dict[str, Any]] = {
    "HF_Sinclair_West_Tulsa": {
        "name": "West Tulsa HF Sinclair Refinery",
        "lat": 36.1428,
        "lon": -96.0078,
        "capacity_bpd": 125000,
        "padd": "PADD 2",
        "primary_locales": ["Tulsa_OK"]
    },
    "PBF_Delaware_City": {
        "name": "PBF Delaware City Refinery",
        "lat": 39.5786,
        "lon": -75.6263,
        "capacity_bpd": 180000,
        "padd": "PADD 1B",
        "primary_locales": ["Newark_DE"]
    },
    "Marathon_Catlettsburg": {
        "name": "Marathon Catlettsburg Refinery",
        "lat": 38.3842,
        "lon": -82.6006,
        "capacity_bpd": 291000,
        "padd": "PADD 2",
        "primary_locales": ["Cincinnati_OH"]
    },
    "Chevron_Richmond": {
        "name": "Chevron Richmond Refinery",
        "lat": 37.9358,
        "lon": -122.3858,
        "capacity_bpd": 245000,
        "padd": "PADD 5",
        "primary_locales": ["Oakland_CA", "SanFrancisco_CA", "BayArea_CA"]
    },
    "Valero_Benicia": {
        "name": "Valero Benicia Refinery",
        "lat": 38.0583,
        "lon": -122.1436,
        "capacity_bpd": 145000,
        "padd": "PADD 5",
        "primary_locales": ["NorthBay_CA", "Oakland_CA"]
    },
    "Shell_PBF_Martinez": {
        "name": "Shell / PBF Martinez Refinery",
        "lat": 38.0192,
        "lon": -122.1242,
        "capacity_bpd": 156000,
        "padd": "PADD 5",
        "primary_locales": ["Oakland_CA", "BayArea_CA"]
    },
    "Colonial_Pipeline_Selma": {
        "name": "Colonial Pipeline Selma Junction",
        "lat": 35.5374,
        "lon": -78.2839,
        "capacity_bpd": 1000000,
        "padd": "PADD 1C",
        "primary_locales": ["Greenville_NC"]
    },
    "Colonial_Pipeline_Paw_Creek": {
        "name": "Colonial Pipeline Paw Creek Terminal",
        "lat": 35.2635,
        "lon": -80.9328,
        "capacity_bpd": 1000000,
        "padd": "PADD 1C",
        "primary_locales": ["Charlotte_NC"]
    },
    "Port_Everglades_Terminal": {
        "name": "Port Everglades Petroleum Terminal",
        "lat": 26.0847,
        "lon": -80.1164,
        "capacity_bpd": 500000,
        "padd": "PADD 1C",
        "primary_locales": ["PortStLucie_FL"]
    },
    "Port_Canaveral_Terminal": {
        "name": "Port Canaveral Petroleum Terminal",
        "lat": 28.4114,
        "lon": -80.6087,
        "capacity_bpd": 300000,
        "padd": "PADD 1C",
        "primary_locales": ["PortStLucie_FL"]
    },
    "Wood_River_Refinery": {
        "name": "Wood River Refinery (Phillips 66)",
        "lat": 38.8353,
        "lon": -90.0768,
        "capacity_bpd": 356000,
        "padd": "PADD 2",
        "primary_locales": ["Midwest_Region"]
    }
}

# Authoritative Regional Metro Cluster Centroids
METRO_CLUSTER_DATA: Dict[str, Dict[str, Any]] = {
    "Tulsa_OK": {
        "name": "Tulsa Metro, OK",
        "lat": 36.1540,
        "lon": -95.9928,
        "zip": "74101"
    },
    "Newark_DE": {
        "name": "Newark Metro, DE",
        "lat": 39.6837,
        "lon": -75.7497,
        "zip": "19711"
    },
    "Cincinnati_OH": {
        "name": "Cincinnati Tri-State, OH/KY",
        "lat": 39.1031,
        "lon": -84.5120,
        "zip": "45202"
    },
    "Greenville_NC": {
        "name": "Greenville Metro, NC",
        "lat": 35.6127,
        "lon": -77.3665,
        "zip": "27834"
    },
    "Charlotte_NC": {
        "name": "Charlotte Metro, NC",
        "lat": 35.2271,
        "lon": -80.8431,
        "zip": "28202"
    },
    "Oakland_CA": {
        "name": "Oakland / East Bay, CA",
        "lat": 37.8044,
        "lon": -122.2712,
        "zip": "94612"
    },
    "SanFrancisco_CA": {
        "name": "San Francisco Metro, CA",
        "lat": 37.7749,
        "lon": -122.4194,
        "zip": "94102"
    },
    "SanJose_CA": {
        "name": "San Jose / Silicon Valley, CA",
        "lat": 37.3382,
        "lon": -121.8863,
        "zip": "95113"
    },
    "PortStLucie_FL": {
        "name": "Port St. Lucie Metro, FL",
        "lat": 27.2730,
        "lon": -80.3582,
        "zip": "34952"
    }
}


def haversine_distance_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes exact spherical geodesic distance in miles using the Haversine formula.
    """
    r_miles = 3958.8  # Earth radius in miles
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r_miles * c


def get_refineries_gdf() -> Union[pd.DataFrame, Any]:
    """
    Returns a GeoPandas GeoDataFrame (or pandas DataFrame fallback) containing all
    refinery and petroleum terminal points in EPSG:4326 (WGS84).
    """
    records = []
    for key, info in REFINERY_DATA.items():
        rec = {"refinery_id": key, **info}
        if HAS_GEOPANDAS:
            rec["geometry"] = Point(info["lon"], info["lat"])
        records.append(rec)

    df = pd.DataFrame(records)
    if HAS_GEOPANDAS:
        return gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")
    return df


def get_metro_clusters_gdf() -> Union[pd.DataFrame, Any]:
    """
    Returns a GeoPandas GeoDataFrame (or pandas DataFrame fallback) containing all
    metro cluster centroids in EPSG:4326 (WGS84).
    """
    records = []
    for key, info in METRO_CLUSTER_DATA.items():
        rec = {"metro_id": key, **info}
        if HAS_GEOPANDAS:
            rec["geometry"] = Point(info["lon"], info["lat"])
        records.append(rec)

    df = pd.DataFrame(records)
    if HAS_GEOPANDAS:
        return gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")
    return df


def generate_refinery_buffers_gdf(buffer_miles_list: Optional[List[float]] = None) -> Union[pd.DataFrame, Any]:
    """
    Generates spatial buffer polygons around all refineries for specified radii in miles.
    Utilizes planar Web Mercator (EPSG:3857) projection for distance calculations.
    """
    if buffer_miles_list is None:
        buffer_miles_list = [25.0, 50.0, 100.0, 250.0, 500.0]

    refineries = get_refineries_gdf()

    if not HAS_GEOPANDAS:
        # Fallback dataframe structure
        records = []
        for _, row in refineries.iterrows():
            for miles in buffer_miles_list:
                records.append({
                    "refinery_id": row["refinery_id"],
                    "name": row["name"],
                    "buffer_miles": miles,
                    "lat": row["lat"],
                    "lon": row["lon"]
                })
        return pd.DataFrame(records)

    # Project to Web Mercator (EPSG:3857) where units are meters
    refineries_3857 = refineries.to_crs(epsg=3857)
    buffer_records = []

    for _, row in refineries_3857.iterrows():
        point_geom = row["geometry"]
        for miles in buffer_miles_list:
            meters = miles * 1609.344
            poly_geom = point_geom.buffer(meters)
            buffer_records.append({
                "refinery_id": row["refinery_id"],
                "name": row["name"],
                "buffer_miles": miles,
                "geometry": poly_geom
            })

    buffer_gdf_3857 = gpd.GeoDataFrame(buffer_records, geometry="geometry", crs="EPSG:3857")
    return buffer_gdf_3857.to_crs(epsg=4326)


def compute_refinery_metro_distance_miles(refinery_id: str, metro_id: str) -> float:
    """
    Calculates spatial distance in miles between a refinery and a metro cluster.
    Utilizes GeoPandas EPSG:3857 projected geometry when available, falling back
    to Haversine geodesic calculation.
    """
    if refinery_id not in REFINERY_DATA:
        raise ValueError(f"Unknown refinery_id: {refinery_id}")
    if metro_id not in METRO_CLUSTER_DATA:
        raise ValueError(f"Unknown metro_id: {metro_id}")

    ref = REFINERY_DATA[refinery_id]
    met = METRO_CLUSTER_DATA[metro_id]

    if HAS_GEOPANDAS:
        try:
            pt_ref = Point(ref["lon"], ref["lat"])
            pt_met = Point(met["lon"], met["lat"])

            gdf_ref = gpd.GeoSeries([pt_ref], crs="EPSG:4326").to_crs(epsg=3857)
            gdf_met = gpd.GeoSeries([pt_met], crs="EPSG:4326").to_crs(epsg=3857)

            dist_meters = gdf_ref.iloc[0].distance(gdf_met.iloc[0])
            return dist_meters / 1609.344
        except Exception as e:
            logger.warning(f"GeoPandas projection failed: {e}. Falling back to Haversine.")

    return haversine_distance_miles(ref["lat"], ref["lon"], met["lat"], met["lon"])


def compute_spatial_distance_decay(distance_miles: float, half_decay_miles: float = 150.0) -> float:
    """
    Calculates exponential spatial decay attenuation weight:
    w(d) = exp(-d / d_0)
    """
    if distance_miles < 0:
        return 1.0
    return math.exp(-distance_miles / half_decay_miles)


def get_buffer_tier(distance_miles: float) -> str:
    """
    Categorizes spatial distance into discrete buffer tier rings.
    """
    if distance_miles <= 25.0:
        return "Fence-Line Rack Proximity (0-25 mi)"
    elif distance_miles <= 100.0:
        return "Primary Distribution Corridor (25-100 mi)"
    elif distance_miles <= 250.0:
        return "Regional Supply Zone (100-250 mi)"
    elif distance_miles <= 500.0:
        return "Inter-State Corridor (250-500 mi)"
    else:
        return "Macro Distant Outlier (>500 mi)"


def compute_refinery_outage_shock_multiplier(
    refinery_id: str,
    metro_id: str,
    outage_severity: float = 1.0,
    base_shock_scale: float = 0.25
) -> float:
    """
    Computes retail price shock adjustment ($/gal) for a metro area given a refinery outage.
    Scales with refinery capacity, outage severity, and spatial distance-decay weight.
    """
    dist_miles = compute_refinery_metro_distance_miles(refinery_id, metro_id)
    w_decay = compute_spatial_distance_decay(dist_miles, half_decay_miles=150.0)

    capacity = REFINERY_DATA[refinery_id]["capacity_bpd"]
    capacity_scale = math.sqrt(capacity / 150000.0)

    shock_delta = outage_severity * capacity_scale * w_decay * base_shock_scale
    return round(shock_delta, 4)


def get_metro_spatial_refinery_summary(metro_id: str) -> Dict[str, Any]:
    """
    Audits spatial proximity and distance decay across all refining assets for a given metro.
    """
    if metro_id not in METRO_CLUSTER_DATA:
        raise ValueError(f"Unknown metro_id: {metro_id}")

    metro = METRO_CLUSTER_DATA[metro_id]
    summary_list = []
    nearest_ref = None
    min_dist = float("inf")

    for ref_id, ref_info in REFINERY_DATA.items():
        dist = compute_refinery_metro_distance_miles(ref_id, metro_id)
        w_decay = compute_spatial_distance_decay(dist)
        tier = get_buffer_tier(dist)
        shock = compute_refinery_outage_shock_multiplier(ref_id, metro_id, outage_severity=1.0)

        item = {
            "refinery_id": ref_id,
            "name": ref_info["name"],
            "distance_miles": round(dist, 2),
            "decay_weight": round(w_decay, 4),
            "buffer_tier": tier,
            "capacity_bpd": ref_info["capacity_bpd"],
            "unit_outage_shock_gal": shock
        }
        summary_list.append(item)

        if dist < min_dist:
            min_dist = dist
            nearest_ref = item

    # Sort by distance
    summary_list.sort(key=lambda x: x["distance_miles"])

    return {
        "metro_id": metro_id,
        "metro_name": metro["name"],
        "zip_code": metro["zip"],
        "is_geopandas_enabled": HAS_GEOPANDAS,
        "nearest_refinery": nearest_ref,
        "refinery_proximate_audit": summary_list
    }
