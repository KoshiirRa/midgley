"""
Unit Tests for Declarative RegionSpec & Universal Regional Runner (Issue #561)
"""

import pytest
from src.locations.specs import get_region_spec, REGIONAL_SPECS, RegionSpec


def test_get_region_spec_all_metros():
    expected_slugs = ["tulsa", "newark", "cincinnati", "greenville", "charlotte", "bay_area", "port_st_lucie", "chicago", "houston", "los_angeles"]
    for slug in expected_slugs:
        spec = get_region_spec(slug)
        assert spec is not None
        assert isinstance(spec, RegionSpec)
        assert spec.slug == slug
        assert len(spec.padd) > 0
        assert len(spec.wholesale_spot_col) > 0
        assert len(spec.eia_retail_series_id) > 0

    # Ensure oakland alias resolves cleanly to canonical bay_area spec
    oak_spec = get_region_spec("oakland")
    assert oak_spec is not None
    assert oak_spec.slug == "bay_area"

    # Ensure chicago_il alias resolves cleanly to chicago spec
    chi_spec = get_region_spec("chicago_il")
    assert chi_spec is not None
    assert chi_spec.slug == "chicago"

    # Ensure houston_tx alias resolves cleanly to houston spec
    hou_spec = get_region_spec("houston_tx")
    assert hou_spec is not None
    assert hou_spec.slug == "houston"

    # Ensure los_angeles_ca and la aliases resolve cleanly to los_angeles spec
    for la_alias in ("los_angeles_ca", "la", "la_basin", "socal"):
        la_spec = get_region_spec(la_alias)
        assert la_spec is not None
        assert la_spec.slug == "los_angeles"


def test_get_region_spec_by_region_key():
    spec = get_region_spec("Tulsa_OK")
    assert spec is not None
    assert spec.region_key == "Tulsa_OK"
    assert spec.slug == "tulsa"
    assert spec.wholesale_spot_col == "spot_group_3"

    chi_spec = get_region_spec("Chicago_IL")
    assert chi_spec is not None
    assert chi_spec.region_key == "Chicago_IL"
    assert chi_spec.slug == "chicago"
    assert chi_spec.wholesale_spot_col == "spot_chicago"

    hou_spec = get_region_spec("Houston_TX")
    assert hou_spec is not None
    assert hou_spec.region_key == "Houston_TX"
    assert hou_spec.slug == "houston"
    assert hou_spec.wholesale_spot_col == "spot_gulf_coast"

    la_spec = get_region_spec("Los_Angeles_CA")
    assert la_spec is not None
    assert la_spec.region_key == "Los_Angeles_CA"
    assert la_spec.slug == "los_angeles"
    assert la_spec.wholesale_spot_col == "spot_los_angeles"


def test_region_spec_microstructure_flags():
    cincy = get_region_spec("cincinnati")
    assert cincy.has_edgeworth_cycles is True

    chicago = get_region_spec("chicago")
    assert chicago.has_edgeworth_cycles is True
    assert chicago.baseline_tax_rate >= 0.50

    houston = get_region_spec("houston")
    assert houston.baseline_tax_rate == 0.200
    assert houston.padd == "PADD 3"

    los_angeles = get_region_spec("los_angeles")
    assert los_angeles.has_carb_compliance is True
    assert los_angeles.baseline_tax_rate == 0.953
    assert los_angeles.padd == "PADD 5"
    
    oakland = get_region_spec("oakland")
    assert oakland.has_carb_compliance is True
    assert oakland.baseline_tax_rate >= 0.50

