"""
Unit Tests for Declarative RegionSpec & Universal Regional Runner (Issue #561)
"""

import pytest
from src.locations.specs import get_region_spec, REGIONAL_SPECS, RegionSpec


def test_get_region_spec_all_metros():
    expected_slugs = ["tulsa", "newark", "cincinnati", "greenville", "charlotte", "bay_area", "port_st_lucie"]
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


def test_get_region_spec_by_region_key():
    spec = get_region_spec("Tulsa_OK")
    assert spec is not None
    assert spec.region_key == "Tulsa_OK"
    assert spec.slug == "tulsa"
    assert spec.wholesale_spot_col == "spot_group_3"


def test_region_spec_microstructure_flags():
    cincy = get_region_spec("cincinnati")
    assert cincy.has_edgeworth_cycles is True
    
    oakland = get_region_spec("oakland")
    assert oakland.has_carb_compliance is True
    assert oakland.baseline_tax_rate >= 0.50
