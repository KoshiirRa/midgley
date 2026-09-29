import os
import sys
import pytest

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.regional_metadata import (
    get_regional_metadata,
    list_all_regional_metadata,
    render_regional_driver_cards_html,
    REGIONAL_METADATA_DIR,
)

EXPECTED_REGIONS = [
    "tulsa_ok",
    "newark_de",
    "cincinnati_oh",
    "greenville_nc",
    "charlotte_nc",
    "oakland_ca",
    "bayarea_ca",
]


def test_regional_metadata_dir_exists():
    """Verify data/regional_metadata directory exists and contains JSON files."""
    assert os.path.exists(REGIONAL_METADATA_DIR), f"Directory missing: {REGIONAL_METADATA_DIR}"
    json_files = [f for f in os.listdir(REGIONAL_METADATA_DIR) if f.endswith(".json")]
    assert len(json_files) >= 7, f"Expected at least 7 regional JSON files, found {len(json_files)}"


def test_all_expected_regional_json_profiles_exist():
    """Verify that each expected regional metro profile JSON exists and has valid schema keys."""
    required_keys = [
        "region_id",
        "display_name",
        "padd_region",
        "primary_city",
        "counties",
        "baseline_price",
        "econometric_drivers",
        "refining_logistics",
        "tax_structure",
        "infrastructure_delivery",
        "shock_scenarios",
    ]

    for reg_id in EXPECTED_REGIONS:
        data = get_regional_metadata(reg_id)
        assert data["region_id"] == reg_id, f"region_id mismatch in {reg_id}"
        for key in required_keys:
            assert key in data, f"Required key '{key}' missing from regional profile {reg_id}"

        # Verify 4 core dimensions have non-empty titles and descriptions
        for dim in ["econometric_drivers", "refining_logistics", "tax_structure", "infrastructure_delivery"]:
            dim_data = data[dim]
            assert "title" in dim_data and len(dim_data["title"]) > 0, f"Empty title in {dim} for {reg_id}"
            assert "description" in dim_data and len(dim_data["description"]) > 0, f"Empty description in {dim} for {reg_id}"


def test_list_all_regional_metadata():
    """Verify list_all_regional_metadata discovers all profiles."""
    all_meta = list_all_regional_metadata()
    for reg_id in EXPECTED_REGIONS:
        assert reg_id in all_meta, f"Region '{reg_id}' missing from list_all_regional_metadata"


def test_render_regional_driver_cards_html():
    """Verify render_regional_driver_cards_html renders valid Tailwind HTML cards."""
    for reg_id in EXPECTED_REGIONS:
        html_out = render_regional_driver_cards_html(reg_id)
        assert "Regional Econometric Drivers & Physical Infrastructure Factors" in html_out
        meta = get_regional_metadata(reg_id)
        assert meta["econometric_drivers"]["title"] in html_out
        assert meta["refining_logistics"]["title"] in html_out
        assert meta["tax_structure"]["title"] in html_out
        assert meta["infrastructure_delivery"]["title"] in html_out


def test_fallback_metadata_handling():
    """Verify graceful fallback for non-existent region_id."""
    fallback_data = get_regional_metadata("non_existent_metro_xyz")
    assert fallback_data["region_id"] == "non_existent_metro_xyz"
    assert "Regional Econometric Drivers" in fallback_data["econometric_drivers"]["title"]
    fallback_html = render_regional_driver_cards_html("non_existent_metro_xyz")
    assert "Regional Econometric Drivers & Physical Infrastructure Factors" in fallback_html
