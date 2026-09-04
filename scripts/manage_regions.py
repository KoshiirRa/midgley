#!/usr/bin/env python3
"""
CLI Region Manager Script (scripts/manage_regions.py)

Provides CLI commands for self-hosters to create, list, test, and register
custom regional metro profiles for the Midgley forecasting engine.

Usage:
    python scripts/manage_regions.py list
    python scripts/manage_regions.py create --region-id chicago_il --name "Chicago Metro, IL" --zip 60601
    python scripts/manage_regions.py test --region-id chicago_il
"""

import os
import sys
import json
import argparse
import logging

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.regional_metadata import list_all_regional_metadata, get_regional_metadata
from src.dynamic_region import DynamicRegionRunner

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

REGIONAL_METADATA_DIR = os.path.join(PROJECT_ROOT, "data", "regional_metadata")


def list_regions():
    """Lists all active registered regional metadata profiles."""
    profiles = list_all_regional_metadata()
    print("\n=================================================================")
    print("📍 MIDGLEY REGISTERED REGIONAL METRO PROFILES")
    print("=================================================================")
    if not profiles:
        print("No custom regional profiles found in data/regional_metadata/.")
    else:
        for rid, meta in profiles.items():
            disp = meta.get("display_name", rid)
            padd = meta.get("padd_region", "N/A")
            tax = meta.get("statutory_tax_gal", 0.0)
            print(f"  • {rid:<20} | {disp:<35} | PADD: {padd:<8} | Tax: ${tax:.3f}/gal")
    print("=================================================================\n")


def create_region(args):
    """Creates a new regional JSON metadata profile."""
    os.makedirs(REGIONAL_METADATA_DIR, exist_ok=True)
    region_id = args.region_id.lower().strip().replace(" ", "_")
    target_path = os.path.join(REGIONAL_METADATA_DIR, f"{region_id}.json")

    profile = {
        "region_id": region_id,
        "display_name": args.name or region_id.replace("_", " ").title(),
        "theme_color": args.color or "emerald",
        "icon_class": "fa-gas-pump",
        "padd_region": args.padd or "PADD_2",
        "zip_code": args.zip or "60601",
        "base_price_anchor": float(args.base_price or 3.750),
        "statutory_tax_gal": float(args.tax or 0.450),
        "rack_margin_offset": float(args.rack_margin or 0.500),
        "logger_region_key": region_id.title(),
        "econometric_drivers": {
            "title": "Regional Econometric Drivers",
            "description": f"Localized market dynamics calibrated for {region_id}."
        },
        "refining_logistics": {
            "title": "Refining Capacity & Logistics",
            "description": f"Regional supply infrastructure and pipeline corridors serving {region_id}."
        },
        "tax_structure": {
            "title": "Statutory Fuel Tax Structure",
            "description": f"State motor fuel excise tax (${args.tax or 0.450:.3f}/gal) and regulatory overhead."
        },
        "infrastructure_delivery": {
            "title": "Delivery Hub & Rack Margin Equation",
            "description": f"Terminal delivery hub dynamics for {region_id}.",
            "equation_latex": "P_{\\text{Retail}} = P_{\\text{RBOB}} + \\text{RackMargin}"
        },
        "shock_scenarios": [
            {
                "id": "unplanned_refinery_outage",
                "name": "Local Unplanned Refinery Outage",
                "impact_gal": 0.150,
                "description": f"Simulates a 150,000 bpd refinery unit trips near {region_id}."
            }
        ]
    }

    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)

    logger.info(f"✅ Successfully created new regional metadata profile: {target_path}")
    print(f"\nCreated profile '{region_id}' at: {target_path}\n")


def test_region(args):
    """Executes a test forecast run for a given regional profile."""
    region_id = args.region_id.lower().strip()
    logger.info(f"Testing pipeline for region: {region_id}")
    runner = DynamicRegionRunner(region_id)
    res = runner.run_pipeline(use_llm_api=False, model_type="ridge")

    print("\n=================================================================")
    print(f"📊 FORECAST TEST RESULTS FOR '{res['display_name']}'")
    print("=================================================================")
    print(f"  • Current Base Price:  ${res['current_base_price']:.3f}/gal")
    print(f"  • 5-Day Forecast Price: ${res['predicted_5d_price']:.3f}/gal ({res['projected_direction']})")
    print(f"  • Statutory Tax:       ${res['statutory_tax_gal']:.3f}/gal")
    print(f"  • Feature Attributions: {json.dumps(res['feature_attributions'], indent=4)}")
    print("=================================================================\n")


def main():
    parser = argparse.ArgumentParser(description="Midgley Regional Metro CLI Manager")
    subparsers = parser.add_subparsers(dest="command")

    # List command
    subparsers.add_parser("list", help="List all registered regional metadata profiles")

    # Create command
    parser_create = subparsers.add_parser("create", help="Create a new regional metadata profile")
    parser_create.add_argument("--region-id", required=True, help="Region ID (e.g. chicago_il)")
    parser_create.add_argument("--name", help="Display name (e.g. 'Chicago Metro, IL')")
    parser_create.add_argument("--zip", help="Default ZIP code (e.g. 60601)")
    parser_create.add_argument("--base-price", type=float, help="Base retail pump price anchor ($/gal)")
    parser_create.add_argument("--tax", type=float, help="Statutory state tax ($/gal)")
    parser_create.add_argument("--rack-margin", type=float, help="Rack margin offset ($/gal)")
    parser_create.add_argument("--padd", help="PADD region (PADD_1, PADD_2, PADD_3, PADD_4, PADD_5)")
    parser_create.add_argument("--color", help="Theme color (emerald, blue, amber, etc.)")

    # Test command
    parser_test = subparsers.add_parser("test", help="Test forecast pipeline for a regional profile")
    parser_test.add_argument("--region-id", required=True, help="Region ID (e.g. chicago_il)")

    args = parser.parse_args()

    if args.command == "list":
        list_regions()
    elif args.command == "create":
        create_region(args)
    elif args.command == "test":
        test_region(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
