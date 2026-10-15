"""
Master Locations Subpackage Registry (src/locations)
Provides a unified interface for all location models (National Wholesale & Regional Metro Areas).
"""

from typing import Dict, Any, List
import logging

from src.locations.runner import run_regional_pipeline
from src.locations.national import run_national_pipeline, build_national_notebook
from src.locations.tulsa import run_tulsa_pipeline, build_tulsa_notebook
from src.locations.newark import run_newark_pipeline, build_newark_notebook
from src.locations.cincinnati import run_cincinnati_pipeline, build_cincinnati_notebook
from src.locations.greenville import run_greenville_pipeline, build_greenville_notebook
from src.locations.charlotte import run_charlotte_pipeline, build_charlotte_notebook
from src.locations.oakland import run_oakland_pipeline, build_oakland_notebook
from src.locations.port_st_lucie import run_port_st_lucie_pipeline, build_port_st_lucie_notebook
from src.locations.chicago import run_chicago_pipeline, build_chicago_notebook
from src.locations.houston import run_houston_pipeline, build_houston_notebook
from src.locations.los_angeles import run_los_angeles_pipeline, build_los_angeles_notebook
from src.locations.denver import run_denver_pipeline, build_denver_notebook
from src.locations.new_york import run_new_york_pipeline, build_new_york_notebook
from src.locations.seattle import run_seattle_pipeline, build_seattle_notebook
from src.locations.phoenix import run_phoenix_pipeline, build_phoenix_notebook
from src.locations.anchorage import run_anchorage_pipeline, build_anchorage_notebook
from src.locations.honolulu import run_honolulu_pipeline, build_honolulu_notebook
from src.locations.guam import run_guam_pipeline, build_guam_notebook
from src.locations.san_juan import run_san_juan_pipeline, build_san_juan_notebook
from src.locations.boston import run_boston_pipeline, build_boston_notebook

logger = logging.getLogger(__name__)

LOCATIONS: Dict[str, Dict[str, Any]] = {
    "national": {
        "id": "national",
        "name": "National Wholesale RBOB Futures",
        "type": "national",
        "module": "src.locations.national",
        "run_pipeline": run_national_pipeline,
        "build_notebook": build_national_notebook,
        "notebook_filename": "gas_price_llm_forecasting.ipynb"
    },
    "tulsa": {
        "id": "tulsa",
        "name": "Tulsa Metro, OK",
        "type": "regional",
        "module": "src.locations.tulsa",
        "run_pipeline": run_tulsa_pipeline,
        "build_notebook": build_tulsa_notebook,
        "notebook_filename": "tulsa_gas_price_llm_forecasting.ipynb"
    },
    "newark": {
        "id": "newark",
        "name": "Newark Metro, DE (PADD 1B)",
        "type": "regional",
        "module": "src.locations.newark",
        "run_pipeline": run_newark_pipeline,
        "build_notebook": build_newark_notebook,
        "notebook_filename": "newark_gas_price_llm_forecasting.ipynb"
    },
    "cincinnati": {
        "id": "cincinnati",
        "name": "Cincinnati Tri-State, OH/KY",
        "type": "regional",
        "module": "src.locations.cincinnati",
        "run_pipeline": run_cincinnati_pipeline,
        "build_notebook": build_cincinnati_notebook,
        "notebook_filename": "cincinnati_gas_price_llm_forecasting.ipynb"
    },
    "greenville": {
        "id": "greenville",
        "name": "Greenville Metro, NC (PADD 1C)",
        "type": "regional",
        "module": "src.locations.greenville",
        "run_pipeline": run_greenville_pipeline,
        "build_notebook": build_greenville_notebook,
        "notebook_filename": "greenville_gas_price_llm_forecasting.ipynb"
    },
    "charlotte": {
        "id": "charlotte",
        "name": "Charlotte Metro, NC (PADD 1C)",
        "type": "regional",
        "module": "src.locations.charlotte",
        "run_pipeline": run_charlotte_pipeline,
        "build_notebook": build_charlotte_notebook,
        "notebook_filename": "charlotte_gas_price_llm_forecasting.ipynb"
    },
    "oakland": {
        "id": "oakland",
        "name": "Oakland & SF Bay Area, CA (PADD 5)",
        "type": "regional",
        "module": "src.locations.oakland",
        "run_pipeline": run_oakland_pipeline,
        "build_notebook": build_oakland_notebook,
        "notebook_filename": "oakland_gas_price_llm_forecasting.ipynb"
    },
    "port_st_lucie": {
        "id": "port_st_lucie",
        "name": "Port St. Lucie Metro, FL (PADD 1C)",
        "type": "regional",
        "module": "src.locations.port_st_lucie",
        "run_pipeline": run_port_st_lucie_pipeline,
        "build_notebook": build_port_st_lucie_notebook,
        "notebook_filename": "port_st_lucie_gas_price_llm_forecasting.ipynb"
    },
    "chicago": {
        "id": "chicago",
        "name": "Greater Chicago Metro, IL & IN",
        "type": "regional",
        "module": "src.locations.chicago",
        "run_pipeline": run_chicago_pipeline,
        "build_notebook": build_chicago_notebook,
        "notebook_filename": "chicago_gas_price_llm_forecasting.ipynb"
    },
    "houston": {
        "id": "houston",
        "name": "Houston & USGC Refining Complex, TX",
        "type": "regional",
        "module": "src.locations.houston",
        "run_pipeline": run_houston_pipeline,
        "build_notebook": build_houston_notebook,
        "notebook_filename": "houston_gas_price_llm_forecasting.ipynb"
    },
    "los_angeles": {
        "id": "los_angeles",
        "name": "Los Angeles Basin, CA (PADD 5)",
        "type": "regional",
        "module": "src.locations.los_angeles",
        "run_pipeline": run_los_angeles_pipeline,
        "build_notebook": build_los_angeles_notebook,
        "notebook_filename": "los_angeles_gas_price_llm_forecasting.ipynb"
    },
    "denver": {
        "id": "denver",
        "name": "Denver Metro & Rocky Mountain Hub, CO (PADD 4)",
        "type": "regional",
        "module": "src.locations.denver",
        "run_pipeline": run_denver_pipeline,
        "build_notebook": build_denver_notebook,
        "notebook_filename": "denver_gas_price_llm_forecasting.ipynb"
    },
    "new_york": {
        "id": "new_york",
        "name": "New York Harbor & NY State Hub, NY (PADD 1B)",
        "type": "regional",
        "module": "src.locations.new_york",
        "run_pipeline": run_new_york_pipeline,
        "build_notebook": build_new_york_notebook,
        "notebook_filename": "new_york_gas_price_llm_forecasting.ipynb"
    },
    "seattle": {
        "id": "seattle",
        "name": "Seattle-Tacoma & Puget Sound, WA (PADD 5B)",
        "type": "regional",
        "module": "src.locations.seattle",
        "run_pipeline": run_seattle_pipeline,
        "build_notebook": build_seattle_notebook,
        "notebook_filename": "seattle_gas_price_llm_forecasting.ipynb"
    },
    "phoenix": {
        "id": "phoenix",
        "name": "Phoenix Metro & Desert Southwest, AZ (PADD 5C)",
        "type": "regional",
        "module": "src.locations.phoenix",
        "run_pipeline": run_phoenix_pipeline,
        "build_notebook": build_phoenix_notebook,
        "notebook_filename": "phoenix_gas_price_llm_forecasting.ipynb"
    },
    "anchorage": {
        "id": "anchorage",
        "name": "Anchorage & Southcentral Alaska Hub, AK (PADD 5D)",
        "type": "regional",
        "module": "src.locations.anchorage",
        "run_pipeline": run_anchorage_pipeline,
        "build_notebook": build_anchorage_notebook,
        "notebook_filename": "anchorage_gas_price_llm_forecasting.ipynb"
    },
    "honolulu": {
        "id": "honolulu",
        "name": "Honolulu & Oahu Island Hub, HI (PADD 5D)",
        "type": "regional",
        "module": "src.locations.honolulu",
        "run_pipeline": run_honolulu_pipeline,
        "build_notebook": build_honolulu_notebook,
        "notebook_filename": "honolulu_gas_price_llm_forecasting.ipynb"
    },
    "guam": {
        "id": "guam",
        "name": "Hagåtña & Apra Harbor, Guam (PADD 7)",
        "type": "regional",
        "module": "src.locations.guam",
        "run_pipeline": run_guam_pipeline,
        "build_notebook": build_guam_notebook,
        "notebook_filename": "guam_gas_price_llm_forecasting.ipynb"
    },
    "san_juan": {
        "id": "san_juan",
        "name": "San Juan Metro & U.S. Caribbean Territories Hub, PR (PADD 6)",
        "type": "regional",
        "module": "src.locations.san_juan",
        "run_pipeline": run_san_juan_pipeline,
        "build_notebook": build_san_juan_notebook,
        "notebook_filename": "san_juan_gas_price_llm_forecasting.ipynb"
    },
    "boston": {
        "id": "boston",
        "name": "Boston Metro & New England Hub, MA (PADD 1A)",
        "type": "regional",
        "module": "src.locations.boston",
        "run_pipeline": run_boston_pipeline,
        "build_notebook": build_boston_notebook,
        "notebook_filename": "boston_gas_price_llm_forecasting.ipynb"
    }
}

def list_locations() -> List[str]:
    """Returns a list of all registered location IDs."""
    return list(LOCATIONS.keys())

def get_location(loc_id: str) -> Dict[str, Any]:
    """Retrieves location metadata and execution handlers by location ID."""
    loc_id = loc_id.lower().strip()
    if loc_id in ("bay_area", "bayarea", "bayarea_ca", "oakland_ca"):
        loc_id = "oakland"
    if loc_id in ("chicago_il", "greater_chicago"):
        loc_id = "chicago"
    if loc_id in ("houston_tx", "houston_metro"):
        loc_id = "houston"
    if loc_id in ("los_angeles_ca", "la", "la_basin", "socal"):
        loc_id = "los_angeles"
    if loc_id in ("denver_co", "rocky_mountain"):
        loc_id = "denver"
    if loc_id in ("new_york_ny", "nyc", "ny_harbor", "ny_state", "newyork"):
        loc_id = "new_york"
    if loc_id in ("seattle_wa", "puget_sound", "pnw"):
        loc_id = "seattle"
    if loc_id in ("phoenix_az", "desert_southwest", "phx"):
        loc_id = "phoenix"
    if loc_id in ("anchorage_ak", "alaska", "kenai"):
        loc_id = "anchorage"
    if loc_id in ("honolulu_hi", "hawaii", "oahu"):
        loc_id = "honolulu"
    if loc_id in ("guam_gu", "padd7", "padd_7", "hagatna", "apra_harbor", "marianas"):
        loc_id = "guam"
    if loc_id in ("san_juan_pr", "puerto_rico", "pr", "padd6", "padd_6", "sju", "caribbean"):
        loc_id = "san_juan"
    if loc_id in ("boston_ma", "new_england", "bos", "padd1a", "padd_1a", "massachusetts"):
        loc_id = "boston"
    if loc_id not in LOCATIONS:
        raise KeyError(f"Unknown location '{loc_id}'. Registered locations: {list_locations()}")
    return LOCATIONS[loc_id]

def run_all_locations(use_llm_api: bool = False, model_type: str = "ridge") -> Dict[str, Any]:
    """Executes prediction pipelines for all registered locations sequentially."""
    results = {}
    for loc_id, info in LOCATIONS.items():
        logger.info(f"Running pipeline for location: {info['name']} ({loc_id})")
        res = info["run_pipeline"](use_llm_api=use_llm_api, model_type=model_type)
        results[loc_id] = res
    return results

def build_all_notebooks() -> Dict[str, str]:
    """Generates Jupyter notebooks for all registered locations."""
    paths = {}
    for loc_id, info in LOCATIONS.items():
        logger.info(f"Building notebook for location: {info['name']} ({loc_id})")
        path = info["build_notebook"]()
        paths[loc_id] = path
    return paths

# Aliases for consolidated Bay Area regional pipeline
run_bay_area_pipeline = run_oakland_pipeline
build_bay_area_notebook = build_oakland_notebook

__all__ = [
    "LOCATIONS",
    "list_locations",
    "get_location",
    "run_all_locations",
    "build_all_notebooks",
    "run_national_pipeline",
    "run_tulsa_pipeline",
    "run_newark_pipeline",
    "run_cincinnati_pipeline",
    "run_greenville_pipeline",
    "run_charlotte_pipeline",
    "run_oakland_pipeline",
    "run_bay_area_pipeline",
    "run_port_st_lucie_pipeline",
    "run_chicago_pipeline",
    "build_chicago_notebook",
    "run_houston_pipeline",
    "build_houston_notebook",
    "run_los_angeles_pipeline",
    "build_los_angeles_notebook",
    "run_denver_pipeline",
    "build_denver_notebook",
    "run_new_york_pipeline",
    "build_new_york_notebook",
    "run_seattle_pipeline",
    "build_seattle_notebook",
    "run_phoenix_pipeline",
    "build_phoenix_notebook",
    "run_anchorage_pipeline",
    "build_anchorage_notebook",
    "run_honolulu_pipeline",
    "build_honolulu_notebook",
    "run_guam_pipeline",
    "build_guam_notebook",
    "run_san_juan_pipeline",
    "build_san_juan_notebook",
    "run_boston_pipeline",
    "build_boston_notebook"
]
