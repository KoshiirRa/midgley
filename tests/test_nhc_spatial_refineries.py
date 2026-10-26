"""
Unit & Regression Tests for NHC Tropical Cyclone Spatial Wind Swaths & EIA-820 Refinery Intersect
(tests/test_nhc_spatial_refineries.py - Issue #634)

Verifies:
1. EIA-820 PADD 3 Gulf Coast refinery geographic coordinates, capacities, and subregion metadata.
2. Point-in-polygon ray casting algorithm correctness across various polygon geometries.
3. NOAA NHC GeoJSON & KML forecast cone / wind swath parsers.
4. Capacity-weighted refinery exposure score:
       Exposure Score = sum(Capacity_i in Hazard Zone) / sum(Total PADD 3 Capacity)
5. Acceptance Criteria:
   - Eastern Gulf / Florida Panhandle landfall (Hurricane Isaias) yields low (<15%) exposure.
   - Western Gulf landfall (Upper Texas Coast & SW Louisiana) yields high (>50%) exposure.
   - Quiescent basin yields 0% exposure.
6. Offline deterministic execution under TESTING=1 using synthetic fixtures.
"""

import json
import pytest
from src.regional_metadata import (
    get_padd3_refineries,
    get_padd3_total_refinery_capacity_bpd
)
from src.nhc_hurricane import (
    point_in_polygon,
    haversine_distance_nm,
    destination_point,
    wind_radii_to_polygon,
    parse_nhc_geojson_cone,
    parse_nhc_kml_cone,
    calculate_refinery_exposure,
    NHCHurricaneConnector,
    EASTERN_GULF_ISAIAS_POLYGON,
    WESTERN_GULF_HURRICANE_POLYGON,
    save_nhc_vintage_record,
    get_nhc_vintages_as_of
)
from src.narrative_generator import (
    generate_metro_narrative,
    generate_national_wholesale_narrative,
    generate_macro_synthesis_narrative
)


def test_eia820_padd3_refinery_catalog_integrity():
    """Verify EIA-820 PADD 3 refinery catalog is loaded, schema-valid, and covers major hubs."""
    refineries = get_padd3_refineries()
    assert len(refineries) >= 20, f"Expected at least 20 major Gulf refineries, found {len(refineries)}"

    total_cap = get_padd3_total_refinery_capacity_bpd()
    assert total_cap > 7_000_000, f"Expected >7M bpd total PADD 3 capacity, got {total_cap}"

    required_keys = [
        "refinery_id", "company", "facility", "city", "state",
        "subregion", "latitude", "longitude", "operable_capacity_bpd"
    ]

    for ref in refineries:
        for k in required_keys:
            assert k in ref, f"Refinery missing key '{k}': {ref}"

        assert ref["state"] in ("TX", "LA", "MS", "AL"), f"Unexpected state: {ref['state']}"
        assert 25.0 <= ref["latitude"] <= 35.0, f"Latitude out of USGC bounds: {ref['latitude']}"
        assert -105.0 <= ref["longitude"] <= -80.0, f"Longitude out of USGC bounds: {ref['longitude']}"
        assert ref["operable_capacity_bpd"] > 0, f"Invalid capacity: {ref['operable_capacity_bpd']}"

    # Verify key refining anchors are present
    ref_ids = {r["refinery_id"] for r in refineries}
    assert "motiva_port_arthur" in ref_ids
    assert "marathon_galveston_bay" in ref_ids
    assert "exxonmobil_baytown" in ref_ids
    assert "marathon_garyville" in ref_ids
    assert "chevron_pascagoula" in ref_ids
    assert "vertex_mobile" in ref_ids


def test_point_in_polygon_ray_casting():
    """Verify point_in_polygon correctly handles interior, exterior, and edge coordinates."""
    # Simple bounding box: lat in [20, 30], lon in [-90, -80]
    box = [(20.0, -90.0), (20.0, -80.0), (30.0, -80.0), (30.0, -90.0)]

    # Point clearly inside
    assert point_in_polygon(25.0, -85.0, box) is True

    # Points clearly outside
    assert point_in_polygon(15.0, -85.0, box) is False  # South
    assert point_in_polygon(35.0, -85.0, box) is False  # North
    assert point_in_polygon(25.0, -95.0, box) is False  # West
    assert point_in_polygon(25.0, -75.0, box) is False  # East

    # Non-convex L-shaped polygon
    l_poly = [
        (0.0, 0.0),
        (0.0, 4.0),
        (2.0, 4.0),
        (2.0, 2.0),
        (4.0, 2.0),
        (4.0, 0.0)
    ]
    assert point_in_polygon(1.0, 1.0, l_poly) is True   # Inside lower portion
    assert point_in_polygon(1.0, 3.0, l_poly) is True   # Inside left arm
    assert point_in_polygon(3.0, 1.0, l_poly) is True   # Inside bottom arm
    assert point_in_polygon(3.0, 3.0, l_poly) is False  # In the 'cutout' corner


def test_haversine_distance_and_destination():
    """Verify great circle distance and destination point calculations."""
    # Houston (29.76, -95.36) to Galveston (29.30, -94.79) is approx 41-45 nautical miles
    dist_nm = haversine_distance_nm(29.76, -95.36, 29.30, -94.79)
    assert 35.0 < dist_nm < 55.0

    # Moving 60 nm due North (bearing 0) should increase latitude by ~1.0 degree
    dest_lat, dest_lon = destination_point(29.0, -90.0, 60.0, 0.0)
    assert abs(dest_lat - 30.0) < 0.05
    assert abs(dest_lon - (-90.0)) < 0.05


def test_wind_radii_to_polygon():
    """Verify 4-quadrant wind radii conversion to polygon vertices."""
    center_lat = 28.0
    center_lon = -90.0
    radii_nm = {"NE": 120.0, "SE": 100.0, "SW": 60.0, "NW": 80.0}

    poly = wind_radii_to_polygon(center_lat, center_lon, radii_nm, points_per_quadrant=4)
    assert len(poly) >= 16

    # Test point within NE quadrant at 60 nm
    dest_ne = destination_point(center_lat, center_lon, 60.0, 45.0)
    assert point_in_polygon(dest_ne[0], dest_ne[1], poly) is True

    # Test point beyond NE quadrant at 180 nm
    dest_far = destination_point(center_lat, center_lon, 180.0, 45.0)
    assert point_in_polygon(dest_far[0], dest_far[1], poly) is False


def test_parse_nhc_geojson_cone():
    """Verify parsing GeoJSON forecast cone feature into polygon vertices."""
    mock_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[-94.0, 29.0], [-93.0, 29.0], [-93.0, 30.5], [-94.0, 30.5], [-94.0, 29.0]]
                    ]
                },
                "properties": {"STORMNAME": "TEST_STORM"}
            }
        ]
    }
    polys = parse_nhc_geojson_cone(mock_geojson)
    assert len(polys) == 1
    # Check [lon, lat] was converted to (lat, lon)
    assert polys[0][0] == (29.0, -94.0)
    assert polys[0][1] == (29.0, -93.0)


def test_parse_nhc_kml_cone():
    """Verify parsing KML forecast cone string into polygon vertices."""
    mock_kml = """<?xml version="1.0" encoding="UTF-8"?>
    <kml xmlns="http://www.opengis.net/kml/2.2">
      <Placemark>
        <name>Forecast Cone</name>
        <Polygon>
          <outerBoundaryIs>
            <LinearRing>
              <coordinates>
                -95.0,29.0,0.0 -93.5,29.0,0.0 -93.5,30.5,0.0 -95.0,30.5,0.0 -95.0,29.0,0.0
              </coordinates>
            </LinearRing>
          </outerBoundaryIs>
        </Polygon>
      </Placemark>
    </kml>"""
    polys = parse_nhc_kml_cone(mock_kml)
    assert len(polys) == 1
    assert len(polys[0]) == 5
    assert polys[0][0] == (29.0, -95.0)


def test_acceptance_criteria_eastern_gulf_isaias_low_exposure():
    """
    Acceptance Criterion 1:
    Eastern Gulf / Florida Panhandle storms (e.g. Hurricane Isaias Destin FL landfall)
    yield low (<15%) PADD 3 refining exposure scores because they spare the Western
    Gulf mega-refining hubs in Texas and Southwest Louisiana.
    """
    exposure = calculate_refinery_exposure(hazard_polygons=[EASTERN_GULF_ISAIAS_POLYGON])
    score = exposure["exposure_score"]

    # Must be strictly under 15% (0.15)
    assert score < 0.15, f"Eastern Gulf exposure score {score} was >= 0.15!"
    assert score > 0.0, f"Expected non-zero exposure for Eastern Gulf facilities, got {score}"

    # Verify only Mississippi/Alabama facilities are impacted
    impacted_ids = set(exposure["impacted_refinery_ids"])
    assert "chevron_pascagoula" in impacted_ids
    assert "vertex_mobile" in impacted_ids

    # Verify Western Gulf and Lower Mississippi River facilities are untouched
    assert "motiva_port_arthur" not in impacted_ids
    assert "marathon_galveston_bay" not in impacted_ids
    assert "exxonmobil_baytown" not in impacted_ids
    assert "marathon_garyville" not in impacted_ids
    assert "citgo_lake_charles" not in impacted_ids

    # Expected capacity: Chevron Pascagoula (356.4k) + Vertex Mobile (75k) = 431,400 bpd
    assert exposure["impacted_capacity_bpd"] == 431_400
    assert abs(score - (431_400 / exposure["total_padd3_capacity_bpd"])) < 0.001


def test_acceptance_criteria_western_gulf_high_exposure():
    """
    Acceptance Criterion 2:
    Western Gulf storms targeting the Upper Texas Coast / SW Louisiana yield
    proportional high (>50%) refining exposure scores because they directly
    threaten the dense refining epicenter (>4.4M bpd).
    """
    exposure = calculate_refinery_exposure(hazard_polygons=[WESTERN_GULF_HURRICANE_POLYGON])
    score = exposure["exposure_score"]

    # Must be strictly over 50% (0.50)
    assert score > 0.50, f"Western Gulf exposure score {score} was <= 0.50!"

    impacted_ids = set(exposure["impacted_refinery_ids"])
    # Key Western Gulf assets MUST be captured
    assert "motiva_port_arthur" in impacted_ids
    assert "marathon_galveston_bay" in impacted_ids
    assert "exxonmobil_baytown" in impacted_ids
    assert "valero_port_arthur" in impacted_ids
    assert "citgo_lake_charles" in impacted_ids
    assert "pemex_deer_park" in impacted_ids

    # Eastern Gulf assets should NOT be captured
    assert "chevron_pascagoula" not in impacted_ids
    assert "vertex_mobile" not in impacted_ids

    assert exposure["impacted_capacity_bpd"] > 4_000_000
    assert abs(score - (4_478_200 / exposure["total_padd3_capacity_bpd"])) < 0.001


def test_quiescent_basin_zero_exposure():
    """Verify quiescent basin with no hazard polygons produces 0 exposure."""
    exposure = calculate_refinery_exposure(hazard_polygons=[])
    assert exposure["exposure_score"] == 0.0
    assert exposure["impacted_capacity_bpd"] == 0
    assert len(exposure["impacted_refineries"]) == 0


def test_connector_synthetic_fixtures_under_testing():
    """Verify NHCHurricaneConnector returns offline deterministic fixtures matching criteria."""
    connector = NHCHurricaneConnector()

    # Scenario: Eastern Gulf / Isaias
    data_east = connector.fetch_active_hurricane_threats(test_scenario="eastern_gulf")
    assert data_east["gulf_hurricane_active"] is True
    assert data_east["nhc_gulf_refinery_exposure_score"] < 0.15
    assert len(data_east["impacted_refineries"]) == 2

    # Scenario: Western Gulf
    data_west = connector.fetch_active_hurricane_threats(test_scenario="western_gulf")
    assert data_west["gulf_hurricane_active"] is True
    assert data_west["nhc_gulf_refinery_exposure_score"] > 0.50
    assert len(data_west["impacted_refineries"]) >= 10

    # Scenario: Quiescent
    data_quiet = connector.fetch_active_hurricane_threats(test_scenario="quiescent")
    assert data_quiet["gulf_hurricane_active"] is False
    assert data_quiet["nhc_gulf_refinery_exposure_score"] == 0.0
    assert data_quiet["active_storms_count"] == 0


def test_spatial_exposure_vintage_persistence(tmp_path):
    """Verify that spatial refinery exposure fields persist correctly in vintage logs."""
    temp_file = str(tmp_path / "test_nhc_vintages.json")
    record = {
        "active_storms_count": 1,
        "gulf_hurricane_active": True,
        "nhc_hurricane_threat_index": 0.80,
        "nhc_gulf_refinery_exposure_score": 0.5773,
        "impacted_capacity_bpd": 4478200,
        "total_padd3_capacity_bpd": 7757600
    }
    save_nhc_vintage_record(record, filepath=temp_file)

    loaded = get_nhc_vintages_as_of("2099-12-31", filepath=temp_file)
    assert loaded is not None
    assert loaded["nhc_gulf_refinery_exposure_score"] == 0.5773
    assert loaded["impacted_capacity_bpd"] == 4478200


def test_narrative_generator_accounts_for_western_gulf_refining_exposure():
    """Verify narrative generator synthesizes Western Gulf refining hazard cone exposure (Issue #634)."""
    res = generate_metro_narrative(
        region_id="Houston_TX",
        current_price=2.85,
        predicted_5d_price=2.98,
        outage_exposure=0.5728,
        logistics_hub="Houston Ship Channel & Port Arthur Refining Complex"
    )
    # Check badge
    assert any("USGC Hazard Cone" in b for b in res["badges"]), f"Expected USGC Hazard Cone badge, got {res['badges']}"
    # Check narrative prose
    assert "Western Gulf refining epicenter" in res["narrative"]
    assert "57.3%" in res["narrative"] or "57.28%" in res["narrative"]


def test_narrative_generator_accounts_for_eastern_gulf_asymmetry():
    """Verify narrative generator synthesizes Eastern Gulf low-exposure track sparing Texas hubs (Issue #634)."""
    res = generate_metro_narrative(
        region_id="Houston_TX",
        current_price=2.85,
        predicted_5d_price=2.86,
        outage_exposure=0.0552,
        logistics_hub="Houston Ship Channel & Port Arthur Refining Complex"
    )
    # Check badge
    assert any("Eastern Gulf Track" in b for b in res["badges"]), f"Expected Eastern Gulf Track badge, got {res['badges']}"
    # Check narrative prose mentions sparing Western Gulf
    assert "sparing Western Gulf" in res["narrative"]
    assert "5.5%" in res["narrative"] or "5.52%" in res["narrative"]


def test_national_wholesale_narrative_spatial_exposure():
    """Verify national wholesale RBOB narrative incorporates spatial refining exposure (Issue #634)."""
    res_west = generate_national_wholesale_narrative(
        current_price=2.45,
        forecast_price=2.55,
        outage_exposure=0.5728
    )
    assert any("USGC Hazard Cone" in b for b in res_west["badges"])
    assert "Western Gulf refining epicenter" in res_west["narrative"]

    res_east = generate_national_wholesale_narrative(
        current_price=2.45,
        forecast_price=2.47,
        outage_exposure=0.0552
    )
    assert any("Eastern Gulf Track" in b for b in res_east["badges"])
    assert "Eastern Gulf" in res_east["narrative"]


def test_macro_synthesis_narrative_spatial_exposure():
    """Verify macro executive summary narrative reflects PADD 3 spatial exposure divergence (Issue #634)."""
    prices_map = {
        "National": {"base": 3.40, "pred": 3.45},
        "Houston_TX": {"base": 2.85, "pred": 2.95}
    }
    res_macro = generate_macro_synthesis_narrative(
        prices_map=prices_map,
        outage_exposure=0.5728
    )
    assert any("USGC Hazard Cone" in b for b in res_macro["badges"])
    assert "Western Gulf refining epicenter" in res_macro["narrative"]

