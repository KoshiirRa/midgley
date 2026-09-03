"""
Regional Metadata Loader & Storage Specification Module (src/regional_metadata.py)

Decouples regional econometric descriptions, refining logistics, tax structures,
and delivery hub dynamics from web UI presentation code by reading structured JSON
profiles under data/regional_metadata/.
"""

import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Base directory for regional JSON profiles
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REGIONAL_METADATA_DIR = os.path.join(PROJECT_ROOT, "data", "regional_metadata")

# Cache in-memory for fast lookup
_METADATA_CACHE: Dict[str, Dict[str, Any]] = {}


def get_regional_metadata(region_id: str) -> Dict[str, Any]:
    """
    Loads and returns the metadata profile dictionary for a given region_id
    (e.g., 'tulsa_ok', 'newark_de', 'cincinnati_oh', 'greenville_nc', 'charlotte_nc',
    'oakland_ca', 'bayarea_ca').
    """
    region_id = region_id.lower()
    if region_id in _METADATA_CACHE:
        return _METADATA_CACHE[region_id]

    json_path = os.path.join(REGIONAL_METADATA_DIR, f"{region_id}.json")
    if not os.path.exists(json_path):
        logger.warning(f"Regional metadata file not found at {json_path}. Returning fallback dict.")
        return _generate_fallback_metadata(region_id)

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            _METADATA_CACHE[region_id] = data
            return data
    except Exception as e:
        logger.error(f"Error reading regional metadata file {json_path}: {e}")
        return _generate_fallback_metadata(region_id)


def list_all_regional_metadata() -> Dict[str, Dict[str, Any]]:
    """
    Scans data/regional_metadata/ and returns a dictionary mapping region_id -> metadata profile.
    """
    result = {}
    if not os.path.exists(REGIONAL_METADATA_DIR):
        return result

    for fname in os.listdir(REGIONAL_METADATA_DIR):
        if fname.endswith(".json"):
            region_id = fname[:-5]
            result[region_id] = get_regional_metadata(region_id)
    return result


def render_regional_driver_cards_html(region_id: str) -> str:
    """
    Renders standardized Tailwind CSS visual cards detailing unique regional econometric drivers,
    refining logistics, tax structure, and physical infrastructure delivery dynamics for region_id.
    """
    meta = get_regional_metadata(region_id)
    theme_color = meta.get("theme_color", "emerald")
    icon_class = meta.get("icon_class", "fa-warehouse")

    eco = meta.get("econometric_drivers", {})
    ref = meta.get("refining_logistics", {})
    tax = meta.get("tax_structure", {})
    inf = meta.get("infrastructure_delivery", {})

    eco_title = eco.get("title", "Regional Econometric Drivers")
    eco_desc = eco.get("description", "")

    ref_title = ref.get("title", "Refining & Supply Logistics")
    ref_desc = ref.get("description", "")

    tax_title = tax.get("title", "Tax Structure & Statutory Overhead")
    tax_desc = tax.get("description", "")

    inf_title = inf.get("title", "Delivery Hub & Rack Margin")
    inf_desc = inf.get("description", "")
    latex_eq = inf.get("equation_latex", "")

    if latex_eq:
        inf_body = f"""<p>$${latex_eq}$$</p>
                    <p class="text-slate-400 pt-1">{inf_desc}</p>"""
    else:
        inf_body = f"<p>{inf_desc}</p>"

    html = f"""        <!-- Regional Econometric Drivers & Physical Infrastructure Factors -->
        <div class="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
            <h3 class="text-lg font-bold text-white flex items-center gap-2">
                <i class="fa-solid {icon_class} text-{theme_color}-400"></i> Regional Econometric Drivers & Physical Infrastructure Factors
            </h3>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-slate-300">
                <div class="p-4 rounded-xl bg-slate-950 border border-slate-800/80 space-y-2">
                    <h4 class="font-bold text-{theme_color}-300 uppercase tracking-wider">{eco_title}</h4>
                    <p>{eco_desc}</p>
                </div>
                <div class="p-4 rounded-xl bg-slate-950 border border-slate-800/80 space-y-2">
                    <h4 class="font-bold text-blue-300 uppercase tracking-wider">{ref_title}</h4>
                    <p>{ref_desc}</p>
                </div>
                <div class="p-4 rounded-xl bg-slate-950 border border-slate-800/80 space-y-2">
                    <h4 class="font-bold text-amber-300 uppercase tracking-wider">{tax_title}</h4>
                    <p>{tax_desc}</p>
                </div>
                <div class="p-4 rounded-xl bg-slate-950 border border-slate-800/80 space-y-2 overflow-x-auto max-w-full">
                    <h4 class="font-bold text-purple-300 uppercase tracking-wider">{inf_title}</h4>
                    {inf_body}
                </div>
            </div>
        </div>"""
    return html


def _generate_fallback_metadata(region_id: str) -> Dict[str, Any]:
    return {
        "region_id": region_id,
        "display_name": region_id.replace("_", " ").title(),
        "theme_color": "emerald",
        "icon_class": "fa-warehouse",
        "econometric_drivers": {
            "title": "Regional Econometric Drivers",
            "description": f"Localized market dynamics calibrated for {region_id}."
        },
        "refining_logistics": {
            "title": "Refining & Supply Logistics",
            "description": "Regional refining infrastructure and distribution pipeline networks."
        },
        "tax_structure": {
            "title": "Tax Structure & Statutory Overhead",
            "description": "State motor fuel taxes, federal excise tax, and local environmental fees."
        },
        "infrastructure_delivery": {
            "title": "Delivery Hub & Rack Margins",
            "description": "Physical terminal dispatch and rack margin equations."
        },
        "shock_scenarios": []
    }
