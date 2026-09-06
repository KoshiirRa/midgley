"""
Unit Tests for GeoPandas Spatial Refinery Distance Buffering Engine (tests/test_spatial_refinery.py)
"""

import pytest
import pandas as pd

from src.spatial_refinery import (
    haversine_distance_miles,
    get_refineries_gdf,
    get_metro_clusters_gdf,
    generate_refinery_buffers_gdf,
    compute_refinery_metro_distance_miles,
    compute_spatial_distance_decay,
    compute_refinery_outage_shock_multiplier,
    get_metro_spatial_refinery_summary,
    get_buffer_tier,
    REFINERY_DATA,
    METRO_CLUSTER_DATA
)

# Regional spatial helper tests via get_metro_spatial_refinery_summary


def test_haversine_distance_miles():
    """Verify Haversine distance math on known benchmark points."""
    # Distance from Tulsa OK to Newark DE is ~1,100 - 1,200 miles
    dist = haversine_distance_miles(36.1540, -95.9928, 39.6837, -75.7497)
    assert 1100.0 < dist < 1300.0

    # Distance to same point is 0
    assert haversine_distance_miles(36.1540, -95.9928, 36.1540, -95.9928) == 0.0


def test_get_refineries_gdf():
    """Verify refineries GeoDataFrame / DataFrame generation."""
    gdf = get_refineries_gdf()
    assert len(gdf) >= 10
    assert "refinery_id" in gdf.columns
    assert "name" in gdf.columns
    assert "capacity_bpd" in gdf.columns
    assert "lat" in gdf.columns
    assert "lon" in gdf.columns


def test_get_metro_clusters_gdf():
    """Verify metro clusters GeoDataFrame / DataFrame generation."""
    gdf = get_metro_clusters_gdf()
    assert len(gdf) >= 7
    assert "metro_id" in gdf.columns
    assert "zip" in gdf.columns


def test_generate_refinery_buffers_gdf():
    """Verify buffer polygon / record generation across radii."""
    buffers_df = generate_refinery_buffers_gdf(buffer_miles_list=[25.0, 100.0, 250.0])
    assert not buffers_df.empty
    assert "refinery_id" in buffers_df.columns
    assert "buffer_miles" in buffers_df.columns


def test_compute_refinery_metro_distance_miles():
    """Verify accurate distance calculations between specific refineries and metro centers."""
    # West Tulsa Refinery to Tulsa OK metro center should be < 5 miles
    tul_dist = compute_refinery_metro_distance_miles("HF_Sinclair_West_Tulsa", "Tulsa_OK")
    assert 0.0 < tul_dist < 5.0

    # Chevron Richmond Refinery to Oakland CA should be < 15 miles
    oak_dist = compute_refinery_metro_distance_miles("Chevron_Richmond", "Oakland_CA")
    assert 0.0 < oak_dist < 15.0

    # PBF Delaware City Refinery to Newark DE should be < 15 miles
    new_dist = compute_refinery_metro_distance_miles("PBF_Delaware_City", "Newark_DE")
    assert 0.0 < new_dist < 15.0

    # Invalid IDs raise ValueError
    with pytest.raises(ValueError):
        compute_refinery_metro_distance_miles("Invalid_Refinery", "Tulsa_OK")


def test_compute_spatial_distance_decay():
    """Verify exponential spatial distance decay behavior."""
    w0 = compute_spatial_distance_decay(0.0, half_decay_miles=150.0)
    w150 = compute_spatial_distance_decay(150.0, half_decay_miles=150.0)
    w300 = compute_spatial_distance_decay(300.0, half_decay_miles=150.0)

    assert w0 == 1.0
    assert pytest.approx(w150, abs=0.01) == 0.3679
    assert w300 < w150 < w0


def test_compute_refinery_outage_shock_multiplier():
    """Verify refinery outage shock calculation."""
    # Direct local outage has strong shock multiplier
    local_shock = compute_refinery_outage_shock_multiplier("HF_Sinclair_West_Tulsa", "Tulsa_OK", outage_severity=1.0)
    assert local_shock > 0.15

    # Distant outage (e.g. Richmond CA to Tulsa OK) has negligible shock multiplier
    distant_shock = compute_refinery_outage_shock_multiplier("Chevron_Richmond", "Tulsa_OK", outage_severity=1.0)
    assert distant_shock < 0.01

    assert local_shock > distant_shock


def test_get_metro_spatial_refinery_summary():
    """Verify full metro spatial summary structure."""
    summary = get_metro_spatial_refinery_summary("Tulsa_OK")
    assert summary["metro_id"] == "Tulsa_OK"
    assert summary["nearest_refinery"]["refinery_id"] == "HF_Sinclair_West_Tulsa"
    assert len(summary["refinery_proximate_audit"]) == len(REFINERY_DATA)


def test_get_buffer_tier():
    """Verify buffer tier string categorization."""
    assert "Fence-Line" in get_buffer_tier(10.0)
    assert "Primary Distribution" in get_buffer_tier(50.0)
    assert "Regional Supply" in get_buffer_tier(150.0)
    assert "Inter-State" in get_buffer_tier(350.0)
    assert "Outlier" in get_buffer_tier(800.0)


def test_regional_agent_spatial_helpers():
    """Verify all regional agent spatial decay helper summaries."""
    tulsa_decay = get_metro_spatial_refinery_summary("Tulsa_OK")
    assert tulsa_decay["metro_id"] == "Tulsa_OK"

    newark_decay = get_metro_spatial_refinery_summary("Newark_DE")
    assert newark_decay["metro_id"] == "Newark_DE"

    cin_decay = get_metro_spatial_refinery_summary("Cincinnati_OH")
    assert cin_decay["metro_id"] == "Cincinnati_OH"

    grn_decay = get_metro_spatial_refinery_summary("Greenville_NC")
    assert grn_decay["metro_id"] == "Greenville_NC"

    clt_decay = get_metro_spatial_refinery_summary("Charlotte_NC")
    assert clt_decay["metro_id"] == "Charlotte_NC"

    oak_decay = get_metro_spatial_refinery_summary("Oakland_CA")
    assert oak_decay["metro_id"] == "Oakland_CA"

    psl_decay = get_metro_spatial_refinery_summary("PortStLucie_FL")
    assert psl_decay["metro_id"] == "PortStLucie_FL"


def test_haversine_fallback_behavior(monkeypatch):
    """Verify that forcing HAS_GEOPANDAS = False works without errors."""
    import src.spatial_refinery as sr
    monkeypatch.setattr(sr, "HAS_GEOPANDAS", False)

    # Test functions under Haversine fallback mode
    gdf_ref = sr.get_refineries_gdf()
    assert isinstance(gdf_ref, pd.DataFrame)

    gdf_met = sr.get_metro_clusters_gdf()
    assert isinstance(gdf_met, pd.DataFrame)

    dist = sr.compute_refinery_metro_distance_miles("HF_Sinclair_West_Tulsa", "Tulsa_OK")
    assert 0.0 < dist < 5.0

    buffers = sr.generate_refinery_buffers_gdf([25.0, 50.0])
    assert not buffers.empty

    summary = sr.get_metro_spatial_refinery_summary("Tulsa_OK")
    assert summary["is_geopandas_enabled"] is False
