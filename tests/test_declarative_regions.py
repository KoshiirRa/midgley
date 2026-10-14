"""
Unit Tests for Declarative RegionSpec & Universal Regional Runner (Issue #561)
"""

import pytest
from src.locations.specs import get_region_spec, REGIONAL_SPECS, RegionSpec


def test_get_region_spec_all_metros():
    expected_slugs = [
        "tulsa", "newark", "cincinnati", "greenville", "charlotte", "bay_area",
        "port_st_lucie", "chicago", "houston", "los_angeles", "denver", "new_york",
        "seattle", "phoenix", "anchorage", "honolulu", "guam", "san_juan"
    ]
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

    # Ensure denver_co and rocky_mountain aliases resolve cleanly to denver spec
    for den_alias in ("denver_co", "rocky_mountain", "padd4"):
        den_spec = get_region_spec(den_alias)
        assert den_spec is not None
        assert den_spec.slug == "denver"

    # Ensure new_york_ny, nyc, and ny_harbor aliases resolve cleanly to new_york spec
    for ny_alias in ("new_york_ny", "nyc", "ny_harbor", "new_york_metro"):
        ny_spec = get_region_spec(ny_alias)
        assert ny_spec is not None
        assert ny_spec.slug == "new_york"

    # Ensure seattle aliases resolve cleanly to seattle spec
    for sea_alias in ("seattle_wa", "puget_sound", "pnw"):
        sea_spec = get_region_spec(sea_alias)
        assert sea_spec is not None
        assert sea_spec.slug == "seattle"

    # Ensure phoenix aliases resolve cleanly to phoenix spec
    for phx_alias in ("phoenix_az", "phx", "desert_southwest"):
        phx_spec = get_region_spec(phx_alias)
        assert phx_spec is not None
        assert phx_spec.slug == "phoenix"

    # Ensure anchorage aliases resolve cleanly to anchorage spec
    for anc_alias in ("anchorage_ak", "kenai", "alaska"):
        anc_spec = get_region_spec(anc_alias)
        assert anc_spec is not None
        assert anc_spec.slug == "anchorage"

    # Ensure honolulu aliases resolve cleanly to honolulu spec
    for hnl_alias in ("honolulu_hi", "oahu", "hawaii"):
        hnl_spec = get_region_spec(hnl_alias)
        assert hnl_spec is not None
        assert hnl_spec.slug == "honolulu"

    # Ensure guam aliases resolve cleanly to guam spec
    for gum_alias in ("guam_gu", "padd7", "padd_7", "hagatna", "apra_harbor", "marianas"):
        gum_spec = get_region_spec(gum_alias)
        assert gum_spec is not None
        assert gum_spec.slug == "guam"

    # Ensure san_juan aliases resolve cleanly to san_juan spec
    for sj_alias in ("san_juan_pr", "puerto_rico", "pr", "padd6", "padd_6", "sju", "caribbean", "daco"):
        sj_spec = get_region_spec(sj_alias)
        assert sj_spec is not None
        assert sj_spec.slug == "san_juan"


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

    den_spec = get_region_spec("Denver_CO")
    assert den_spec is not None
    assert den_spec.region_key == "Denver_CO"
    assert den_spec.slug == "denver"
    assert den_spec.wholesale_spot_col == "spot_denver_rack"

    ny_spec = get_region_spec("New_York_NY")
    assert ny_spec is not None
    assert ny_spec.region_key == "New_York_NY"
    assert ny_spec.slug == "new_york"
    assert ny_spec.wholesale_spot_col == "spot_ny_harbor"

    sea_spec = get_region_spec("Seattle_WA")
    assert sea_spec is not None
    assert sea_spec.region_key == "Seattle_WA"
    assert sea_spec.slug == "seattle"
    assert sea_spec.wholesale_spot_col == "spot_pnw_rack"

    phx_spec = get_region_spec("Phoenix_AZ")
    assert phx_spec is not None
    assert phx_spec.region_key == "Phoenix_AZ"
    assert phx_spec.slug == "phoenix"
    assert phx_spec.wholesale_spot_col == "spot_phoenix_pipe"

    anc_spec = get_region_spec("Anchorage_AK")
    assert anc_spec is not None
    assert anc_spec.region_key == "Anchorage_AK"
    assert anc_spec.slug == "anchorage"
    assert anc_spec.wholesale_spot_col == "spot_ans_rack"

    hnl_spec = get_region_spec("Honolulu_HI")
    assert hnl_spec is not None
    assert hnl_spec.region_key == "Honolulu_HI"
    assert hnl_spec.slug == "honolulu"
    assert hnl_spec.wholesale_spot_col == "spot_oahu_rack"

    gum_spec = get_region_spec("Guam_GU")
    assert gum_spec is not None
    assert gum_spec.region_key == "Guam_GU"
    assert gum_spec.slug == "guam"
    assert gum_spec.wholesale_spot_col == "spot_mops_92_rack"

    sj_spec = get_region_spec("San_Juan_PR")
    assert sj_spec is not None
    assert sj_spec.region_key == "San_Juan_PR"
    assert sj_spec.slug == "san_juan"
    assert sj_spec.wholesale_spot_col == "spot_gulf_coast"


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

    denver = get_region_spec("denver")
    assert denver.baseline_tax_rate == 0.280
    assert denver.padd == "PADD 4"

    ny = get_region_spec("new_york")
    assert ny.baseline_tax_rate == 0.472
    assert ny.padd == "PADD 1B"

    oakland = get_region_spec("oakland")
    assert oakland.has_carb_compliance is True
    assert oakland.baseline_tax_rate >= 0.50

    seattle = get_region_spec("seattle")
    assert seattle.has_carb_compliance is False
    assert seattle.baseline_tax_rate == 0.494
    assert seattle.padd == "PADD 5B"

    phoenix = get_region_spec("phoenix")
    assert phoenix.has_carb_compliance is False
    assert phoenix.baseline_tax_rate == 0.180
    assert phoenix.padd == "PADD 5C"

    anchorage = get_region_spec("anchorage")
    assert anchorage.has_carb_compliance is False
    assert anchorage.baseline_tax_rate == 0.0895
    assert anchorage.padd == "PADD 5D"

    honolulu = get_region_spec("honolulu")
    assert honolulu.has_carb_compliance is False
    assert honolulu.baseline_tax_rate == 0.330
    assert honolulu.padd == "PADD 5D"

    guam = get_region_spec("guam")
    assert guam.has_carb_compliance is False
    assert guam.baseline_tax_rate == 0.190
    assert guam.padd == "PADD 7"

    san_juan = get_region_spec("san_juan")
    assert san_juan.has_carb_compliance is False
    assert san_juan.baseline_tax_rate == 0.160
    assert san_juan.padd == "PADD 6"

