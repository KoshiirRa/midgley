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
    ),
    "chicago": RegionSpec(
        region_key="Chicago_IL",
        slug="chicago",
        display_name="Greater Chicago Metro, IL & IN (PADD 2)",
        padd="PADD 2",
        wholesale_spot_col="spot_chicago",
        eia_retail_series_id="EMM_EPMR_PTE_Y03CH_DPG",
        diesel_series_id="GASDESWMW",
        baseline_tax_rate=0.550,
        has_edgeworth_cycles=True,
        sub_locales={"cook_county": 0.08, "chicago_city": 0.15, "dupage": -0.04, "will_county": -0.06, "nw_indiana": -0.38},
        primary_refinery="BP Whiting Refinery (435 kbpd) & CITGO Lemont (177 kbpd)",
        primary_pipeline="Explorer / Wolverine / West Shore / Badger Pipelines"
    ),
    "houston": RegionSpec(
        region_key="Houston_TX",
        slug="houston",
        display_name="Houston Metro, TX (PADD 3)",
        padd="PADD 3",
        wholesale_spot_col="spot_gulf_coast",
        eia_retail_series_id="EMM_EPMR_PTE_Y44HO_DPG",
        diesel_series_id="GASDESWGC",
        baseline_tax_rate=0.200,
        has_edgeworth_cycles=False,
        sub_locales={"houston_city": 0.00, "galveston": 0.04, "baytown": -0.03, "pasadena": -0.02, "sugar_land": 0.02, "the_woodlands": 0.03, "beaumont_port_arthur": -0.04},
        primary_refinery="ExxonMobil Baytown (560 kbpd) & Motiva Port Arthur (630 kbpd)",
        primary_pipeline="Colonial Pipeline Lines 1 & 2 / Explorer Pipeline"
    ),
    "los_angeles": RegionSpec(
        region_key="Los_Angeles_CA",
        slug="los_angeles",
        display_name="Los Angeles Basin, CA (PADD 5)",
        padd="PADD 5",
        wholesale_spot_col="spot_los_angeles",
        eia_retail_series_id="EMM_EPMR_PTE_Y05LA_DPG",
        diesel_series_id="GASDESWCA",
        baseline_tax_rate=0.953,
        has_edgeworth_cycles=False,
        has_carb_compliance=True,
        sub_locales={"los_angeles_city": 0.04, "westside_santa_monica": 0.16, "south_bay_torrance": -0.05, "long_beach_harbor": -0.04, "orange_county": -0.06, "inland_empire": -0.10, "san_fernando_valley": 0.02},
        primary_refinery="Marathon Carson/Wilmington (363 kbpd), Chevron El Segundo (269 kbpd) & PBF Torrance (166 kbpd)",
        primary_pipeline="Kinder Morgan SFPP West/South Lines & San Pedro Bay Marine Terminals"
    ),
    "denver": RegionSpec(
        region_key="Denver_CO",
        slug="denver",
        display_name="Denver Metro & Rocky Mountain Hub, CO (PADD 4)",
        padd="PADD 4",
        wholesale_spot_col="spot_denver_rack",
        eia_retail_series_id="EMM_EPMR_PTE_Y35DE_DPG",
        diesel_series_id="GASDESWRM",
        baseline_tax_rate=0.280,
        has_edgeworth_cycles=False,
        has_carb_compliance=False,
        sub_locales={"denver_city": 0.00, "aurora": -0.02, "lakewood": 0.01, "boulder": 0.08, "commerce_city": -0.04, "fort_collins": -0.02, "colorado_springs": -0.03},
        primary_refinery="Suncor Commerce City Refinery (103 kbpd)",
        primary_pipeline="Rocky Mountain Refined Product Midstream / Magellan Corridor"
    ),
    "new_york": RegionSpec(
        region_key="New_York_NY",
        slug="new_york",
        display_name="New York Harbor & NY State Hub, NY (PADD 1B)",
        padd="PADD 1B",
        wholesale_spot_col="spot_ny_harbor",
        eia_retail_series_id="EMM_EPMR_PTE_Y35NY_DPG",
        diesel_series_id="GASDESW01B",
        baseline_tax_rate=0.472,
        has_edgeworth_cycles=False,
        has_carb_compliance=False,
        sub_locales={"nyc_manhattan": 0.14, "brooklyn_queens": 0.04, "long_island_nassau": 0.02, "westchester": 0.06, "albany_capital": -0.05, "buffalo_erie": -0.08, "adirondacks_essex": 0.18},
        primary_refinery="Phillips 66 Bayway Refinery (258 kbpd) & NY Harbor Barges",
        primary_pipeline="Buckeye Pipeline System & Colonial Pipeline Terminus"
    ),
    "seattle": RegionSpec(
        region_key="Seattle_WA",
        slug="seattle",
        display_name="Seattle-Tacoma & Puget Sound, WA (PADD 5B)",
        padd="PADD 5B",
        wholesale_spot_col="spot_pnw_rack",
        eia_retail_series_id="EMM_EPMR_PTE_Y48SE_DPG",
        diesel_series_id="GASDESW5XCA",
        baseline_tax_rate=0.494,
        has_edgeworth_cycles=False,
        has_carb_compliance=False,
        sub_locales={"seattle_city": 0.05, "tacoma": -0.04, "bellevue": 0.08, "everett": -0.02, "olympia": -0.01, "portland_or": -0.06},
        primary_refinery="bp Cherry Point (242 kbpd) & Phillips 66 Ferndale (105 kbpd)",
        primary_pipeline="Olympic Pipeline System"
    ),
    "phoenix": RegionSpec(
        region_key="Phoenix_AZ",
        slug="phoenix",
        display_name="Phoenix Metro & Desert Southwest, AZ (PADD 5C)",
        padd="PADD 5C",
        wholesale_spot_col="spot_phoenix_pipe",
        eia_retail_series_id="EMM_EPMR_PTE_SAZ_DPG",
        diesel_series_id="GASDESW5XCA",
        baseline_tax_rate=0.180,
        has_edgeworth_cycles=False,
        has_carb_compliance=False,
        sub_locales={"phoenix_city": 0.02, "scottsdale": 0.09, "mesa": -0.03, "chandler": -0.01, "glendale": -0.02, "tucson": -0.08, "las_vegas_nv": 0.42},
        primary_refinery="Import Hub via Kinder Morgan SFPP West/East Lines",
        primary_pipeline="Kinder Morgan SFPP West Line (LA) & East Line (El Paso)"
    ),
    "anchorage": RegionSpec(
        region_key="Anchorage_AK",
        slug="anchorage",
        display_name="Anchorage & Southcentral Alaska Hub, AK (PADD 5D)",
        padd="PADD 5D",
        wholesale_spot_col="spot_ans_rack",
        eia_retail_series_id="EMM_EPMR_PTE_SAK_DPG",
        diesel_series_id="GASDESW5XCA",
        baseline_tax_rate=0.0895,
        has_edgeworth_cycles=False,
        has_carb_compliance=False,
        sub_locales={"anchorage_bowl": 0.00, "mat_su_valley": -0.05, "kenai_soldotna": -0.08, "fairbanks_interior": 0.28, "juneau_se": 0.35, "bush_villages": 1.75},
        primary_refinery="Marathon Kenai Refinery (68 kbpd)",
        primary_pipeline="Cook Inlet Marine Barges & Alaska Railroad Tank Cars"
    ),
    "honolulu": RegionSpec(
        region_key="Honolulu_HI",
        slug="honolulu",
        display_name="Honolulu & Oahu Island Hub, HI (PADD 5D)",
        padd="PADD 5D",
        wholesale_spot_col="spot_oahu_rack",
        eia_retail_series_id="EMM_EPMR_PTE_SHI_DPG",
        diesel_series_id="GASDESW5XCA",
        baseline_tax_rate=0.330,
        has_edgeworth_cycles=False,
        has_carb_compliance=False,
        sub_locales={"honolulu_urban": 0.00, "waikiki": 0.12, "leeward_oahu": -0.06, "maui_county": 0.45, "hawaii_island": 0.38, "kauai": 0.52},
        primary_refinery="Par Hawaii Kapolei Refinery (94 kbpd)",
        primary_pipeline="Young Brothers Inter-Island Ocean Fuel Barges"
    )
}

# Alias oakland to bay_area spec for seamless backward compatibility
REGIONAL_SPECS["oakland"] = REGIONAL_SPECS["bay_area"]
REGIONAL_SPECS["chicago_il"] = REGIONAL_SPECS["chicago"]
REGIONAL_SPECS["houston_tx"] = REGIONAL_SPECS["houston"]
REGIONAL_SPECS["los_angeles_ca"] = REGIONAL_SPECS["los_angeles"]
REGIONAL_SPECS["denver_co"] = REGIONAL_SPECS["denver"]
REGIONAL_SPECS["new_york_ny"] = REGIONAL_SPECS["new_york"]
REGIONAL_SPECS["nyc"] = REGIONAL_SPECS["new_york"]
REGIONAL_SPECS["seattle_wa"] = REGIONAL_SPECS["seattle"]
REGIONAL_SPECS["puget_sound"] = REGIONAL_SPECS["seattle"]
REGIONAL_SPECS["pnw"] = REGIONAL_SPECS["seattle"]
REGIONAL_SPECS["phoenix_az"] = REGIONAL_SPECS["phoenix"]
REGIONAL_SPECS["desert_southwest"] = REGIONAL_SPECS["phoenix"]
REGIONAL_SPECS["phx"] = REGIONAL_SPECS["phoenix"]
REGIONAL_SPECS["anchorage_ak"] = REGIONAL_SPECS["anchorage"]
REGIONAL_SPECS["alaska"] = REGIONAL_SPECS["anchorage"]
REGIONAL_SPECS["kenai"] = REGIONAL_SPECS["anchorage"]
REGIONAL_SPECS["honolulu_hi"] = REGIONAL_SPECS["honolulu"]
REGIONAL_SPECS["hawaii"] = REGIONAL_SPECS["honolulu"]
REGIONAL_SPECS["oahu"] = REGIONAL_SPECS["honolulu"]


def get_region_spec(region_id_or_slug: str) -> Optional[RegionSpec]:
    """Retrieves RegionSpec dataclass by slug or region key."""
    if not region_id_or_slug:
        return None
    key = region_id_or_slug.lower().strip()
    if key in ("oakland", "oakland_ca", "bayarea", "bayarea_ca", "bay_area", "sf_bay_area"):
        return REGIONAL_SPECS["bay_area"]
    if key in ("chicago", "chicago_il", "greater_chicago"):
        return REGIONAL_SPECS["chicago"]
    if key in ("houston", "houston_tx", "houston_metro"):
        return REGIONAL_SPECS["houston"]
    if key in ("los_angeles", "los_angeles_ca", "la", "la_basin", "socal"):
        return REGIONAL_SPECS["los_angeles"]
    if key in ("denver", "denver_co", "rocky_mountain", "padd4", "padd_4", "front_range"):
        return REGIONAL_SPECS["denver"]
    if key in ("new_york", "new_york_ny", "nyc", "ny_harbor", "ny_state", "newyork", "new_york_metro"):
        return REGIONAL_SPECS["new_york"]
    if key in ("seattle", "seattle_wa", "puget_sound", "pnw", "olympic"):
        return REGIONAL_SPECS["seattle"]
    if key in ("phoenix", "phoenix_az", "desert_southwest", "phx", "maricopa"):
        return REGIONAL_SPECS["phoenix"]
    if key in ("anchorage", "anchorage_ak", "alaska", "kenai", "cook_inlet"):
        return REGIONAL_SPECS["anchorage"]
    if key in ("honolulu", "honolulu_hi", "hawaii", "oahu", "kapolei"):
        return REGIONAL_SPECS["honolulu"]
    if key in REGIONAL_SPECS:
        return REGIONAL_SPECS[key]
    for spec in REGIONAL_SPECS.values():
        if spec.region_key.lower() == key or spec.slug.lower() == key:
            return spec
    return None

