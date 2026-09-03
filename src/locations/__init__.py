"""
Master Locations Subpackage Registry (src/locations)
Provides a unified interface for all location models (National Wholesale & Regional Metro Areas).
"""

from typing import Dict, Any, List
import logging

from src.locations.national import run_national_pipeline, build_national_notebook
from src.locations.tulsa import run_tulsa_pipeline, build_tulsa_notebook
from src.locations.newark import run_newark_pipeline, build_newark_notebook
from src.locations.cincinnati import run_cincinnati_pipeline, build_cincinnati_notebook
from src.locations.greenville import run_greenville_pipeline, build_greenville_notebook
from src.locations.charlotte import run_charlotte_pipeline, build_charlotte_notebook
from src.locations.oakland import run_oakland_pipeline, build_oakland_notebook
from src.locations.port_st_lucie import run_port_st_lucie_pipeline, build_port_st_lucie_notebook

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
    }
}

def list_locations() -> List[str]:
    """Returns a list of all registered location IDs."""
    return list(LOCATIONS.keys())

def get_location(loc_id: str) -> Dict[str, Any]:
    """Retrieves location metadata and execution handlers by location ID."""
    loc_id = loc_id.lower().strip()
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
    "run_port_st_lucie_pipeline"
]
