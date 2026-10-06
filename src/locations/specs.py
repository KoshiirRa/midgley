"""
Declarative Metro Region Specifications (src/locations/specs.py)

Defines strongly-typed dataclass RegionSpec capturing all regional metadata,
ground truth series mappings, wholesale benchmark columns, statutory tax burdens,
and microstructure cycle behaviors across all 8 metro hubs (Issue #561).
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List


@dataclass(frozen=True)
class RegionSpec:
    region_key: str
    slug: str
    display_name: str
    padd: str
    wholesale_spot_col: str
    eia_retail_series_id: str
    diesel_series_id: str
    baseline_tax_rate: float
    has_edgeworth_cycles: bool = False
    has_carb_compliance: bool = False
    sub_locales: Dict[str, float] = field(default_factory=dict)
    primary_refinery: str = "Regional Refining Complex"
    primary_pipeline: str = "Regional Midstream Corridor"


REGIONAL_SPECS: Dict[str, RegionSpec] = {
    "tulsa": RegionSpec(
        region_key="Tulsa_OK",
        slug="tulsa",
        display_name="Tulsa Metro, OK (PADD 2)",
        padd="PADD 2",
        wholesale_spot_col="spot_group_3",
        eia_retail_series_id="EMM_EPMR_PTE_R20_DPG",
        diesel_series_id="GASDESW",
        baseline_tax_rate=0.20,
        sub_locales={"broken_arrow": -0.02, "owasso": 0.01, "bixby": 0.02},
        primary_refinery="HF Sinclair Tulsa Refinery (125 kbpd)",
        primary_pipeline="Magellan / Explorer Pipeline"
    ),
    "newark": RegionSpec(
        region_key="Newark_DE",
        slug="newark",
        display_name="Newark Metro, DE (PADD 1B)",
        padd="PADD 1B",
        wholesale_spot_col="spot_ny_harbor",
        eia_retail_series_id="EMM_EPMR_PTE_R1Y_DPG",
        diesel_series_id="GASDESW",
        baseline_tax_rate=0.23,
        sub_locales={"wilmington": 0.04, "dover": -0.03},
        primary_refinery="PBF Delaware City Refinery (190 kbpd)",
        primary_pipeline="Colonial Pipeline / Delaware River Barges"
    ),
    "cincinnati": RegionSpec(
        region_key="Cincinnati_OH",
        slug="cincinnati",
        display_name="Cincinnati Tri-State, OH/KY",
        padd="PADD 2",
        wholesale_spot_col="spot_chicago",
        eia_retail_series_id="EMM_EPMR_PTE_SOH_DPG",
        diesel_series_id="GASDESW",
        baseline_tax_rate=0.385,
        has_edgeworth_cycles=True,
        sub_locales={"cincinnati_oh": 0.00, "northern_kentucky_ky": -0.12},
        primary_refinery="Marathon Catlettsburg Refinery (290 kbpd)",
        primary_pipeline="Mid-Valley Pipeline / Ohio River Tows"
    ),
    "greenville": RegionSpec(
        region_key="Greenville_NC",
        slug="greenville",
        display_name="Greenville Metro, NC (PADD 1C)",
        padd="PADD 1C",
        wholesale_spot_col="spot_gulf_coast",
        eia_retail_series_id="EMM_EPMR_PTE_R1Z_DPG",
        diesel_series_id="GASDESW",
        baseline_tax_rate=0.410,
        sub_locales={"selma_terminal": -0.04, "wilson": 0.01, "rocky_mount": 0.02},
        primary_refinery="Gulf Coast Refining Complex (PADD 3)",
        primary_pipeline="Colonial Pipeline Lines 1 & 2 / Plantation Pipeline"
    ),
    "charlotte": RegionSpec(
        region_key="Charlotte_NC",
        slug="charlotte",
        display_name="Charlotte Metro, NC (PADD 1C)",
        padd="PADD 1C",
        wholesale_spot_col="spot_gulf_coast",
        eia_retail_series_id="EMM_EPMR_PTE_R1Z_DPG",
        diesel_series_id="GASDESW",
        baseline_tax_rate=0.410,
        sub_locales={"paw_creek": -0.03, "concord": 0.02, "gastonia": -0.01, "rock_hill_sc": -0.14},
        primary_refinery="Gulf Coast Refining Complex (PADD 3)",
        primary_pipeline="Colonial Pipeline Paw Creek Junction"
    ),
    "bay_area": RegionSpec(
        region_key="BayArea_CA",
        slug="bay_area",
        display_name="SF Bay Area, CA (PADD 5)",
        padd="PADD 5",
        wholesale_spot_col="spot_la_carbob",
        eia_retail_series_id="EMM_EPMR_PTE_Y05SF_DPG",
        diesel_series_id="GASDESW",
        baseline_tax_rate=0.634,
        has_carb_compliance=True,
        sub_locales={"oakland": 0.00, "san_francisco": 0.15, "san_jose": 0.08, "berkeley": 0.05, "richmond": -0.06},
        primary_refinery="Chevron Richmond Refinery (245 kbpd)",
        primary_pipeline="Kinder Morgan SFPP Pacific Northern"
    ),
    "port_st_lucie": RegionSpec(
        region_key="Port_St_Lucie_FL",
        slug="port_st_lucie",
        display_name="Port St. Lucie Metro, FL (PADD 1C)",
        padd="PADD 1C",
        wholesale_spot_col="spot_gulf_coast",
        eia_retail_series_id="EMM_EPMR_PTE_SFL_DPG",
        diesel_series_id="GASDESW",
        baseline_tax_rate=0.352,
        sub_locales={"fort_pierce": -0.02, "stuart": 0.03, "vero_beach": 0.01},
        primary_refinery="Waterborne Jones Act Tankers from Houston/Pascagoula",
        primary_pipeline="Port Everglades & Port Canaveral Waterborne Terminals"
    )
}

# Alias oakland to bay_area spec for seamless backward compatibility
REGIONAL_SPECS["oakland"] = REGIONAL_SPECS["bay_area"]


def get_region_spec(region_id_or_slug: str) -> Optional[RegionSpec]:
    """Retrieves RegionSpec dataclass by slug or region key."""
    if not region_id_or_slug:
        return None
    key = region_id_or_slug.lower().strip()
    if key in ("oakland", "oakland_ca", "bayarea", "bayarea_ca", "bay_area", "sf_bay_area"):
        return REGIONAL_SPECS["bay_area"]
    if key in REGIONAL_SPECS:
        return REGIONAL_SPECS[key]
    for spec in REGIONAL_SPECS.values():
        if spec.region_key.lower() == key or spec.slug.lower() == key:
            return spec
    return None
