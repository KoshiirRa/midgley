"""Unit tests for 50-state & local option fuel tax schedules and spatial disambiguation (Issue #623)."""

from fastapi.testclient import TestClient

from src.api_server import app
from src.state_open_data import IFTAFuelTaxConnector, STATE_METADATA
from src.zip_geocoding import (
    compute_tax_breakdown,
    resolve_coordinates,
    resolve_state_from_coordinates,
    resolve_zip_code,
)


def test_50_state_plus_dc_schedule_complete():
    connector = IFTAFuelTaxConnector()
    schedule = connector.fetch_quarterly_matrix()
    assert schedule["status"] == "success"
    assert schedule["states_count"] == 51  # 50 states + DC
    assert set(schedule["states"].keys()) == set(STATE_METADATA.keys())
    assert schedule["states"]["AK"]["state_excise_per_gal"] == 0.0895
    assert schedule["states"]["CA"]["state_excise_per_gal"] == 0.634


def test_ifta_csv_parser_overrides_rates():
    sample_csv = """
    # IFTA Q4 2026 sample
    OR,0.420
    PA,0.585
    XX,9.999
    """
    connector = IFTAFuelTaxConnector()
    schedule = connector.fetch_quarterly_matrix(csv_override=sample_csv)
    assert schedule["source"] == "IFTA_QUARTERLY_MATRIX"
    assert schedule["ifta_overrides_applied"] == 2
    assert schedule["states"]["OR"]["state_excise_per_gal"] == 0.42
    assert schedule["states"]["OR"]["source"] == "IFTA_QUARTERLY_MATRIX"
    assert schedule["states"]["PA"]["state_excise_per_gal"] == 0.585
    assert schedule["states"]["TX"]["source"] == "STATE_METADATA_BASELINE"


def test_coordinate_bounding_box_prevents_california_tax_leakage():
    # Portland, OR should resolve to OR ($0.400/gal), NOT CA ($0.596/gal)
    assert resolve_state_from_coordinates(45.5152, -122.6784) == "OR"
    res = resolve_coordinates(45.5152, -122.6784)
    assert res["state"] == "OR"
    assert res["state_tax_rate_per_gal"] == 0.400
    assert res["tax_breakdown"]["state_excise"] == 0.400

    # Anchorage, AK
    res_ak = resolve_coordinates(61.2181, -149.9003)
    assert res_ak["state"] == "AK"
    assert res_ak["tax_breakdown"]["state_excise"] == 0.0895


def test_local_option_fuel_tax_adders():
    # Chicago, IL (60601): Cook County ($0.06) + City of Chicago ($0.08) = $0.14
    chi = compute_tax_breakdown("IL", zip_code="60601")
    assert chi["federal_excise"] == 0.184
    assert chi["state_excise"] == 0.470
    assert chi["county_municipal_tax"] == 0.140
    assert "Chicago" in (chi["local_jurisdiction"] or "")
    assert chi["total_tax_burden_per_gal"] > 0.90

    # Las Vegas, NV (89101): Clark County FRI
    lv = compute_tax_breakdown("NV", zip_code="89101")
    assert lv["county_municipal_tax"] == 0.270

    # Honolulu, HI (96813)
    hnl = compute_tax_breakdown("HI", zip_code="96813")
    assert hnl["county_municipal_tax"] == 0.165

    # Miami-Dade, FL (33101)
    mia = compute_tax_breakdown("FL", zip_code="33101")
    assert mia["county_municipal_tax"] == 0.100


def test_resolve_zip_code_includes_tax_breakdown():
    res = resolve_zip_code("60601")
    assert res["state"] == "IL"
    assert "tax_breakdown" in res
    assert res["tax_breakdown"]["county_municipal_tax"] == 0.140


def test_api_tax_lookup_and_schedule_endpoints():
    client = TestClient(app)

    resp_lookup = client.get("/api/v1/tax/lookup", params={"zip": "60601"})
    assert resp_lookup.status_code == 200
    body = resp_lookup.json()
    assert body["state"] == "IL"
    assert body["tax_breakdown"]["federal_excise"] == 0.184
    assert body["tax_breakdown"]["county_municipal_tax"] == 0.140

    resp_coords = client.get("/api/v1/tax/lookup", params={"lat": 45.5152, "lon": -122.6784})
    assert resp_coords.status_code == 200
    assert resp_coords.json()["state"] == "OR"

    resp_sched = client.get("/api/v1/tax/schedule")
    assert resp_sched.status_code == 200
    sched = resp_sched.json()
    assert sched["states_count"] == 51
    assert "IL" in sched["local_option_fuel_taxes"]
    assert "FL" in sched["local_option_fuel_taxes"]
