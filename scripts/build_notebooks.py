"""
Unified Programmatic Notebook Builder CLI (scripts/build_notebooks.py)
Generates Jupyter notebooks for all registered locations or a specified location.

Usage:
    python scripts/build_notebooks.py [--location ALL|national|tulsa|newark|cincinnati|greenville|charlotte|oakland]
"""

import os
import sys
import argparse
import logging

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.locations import LOCATIONS, build_all_notebooks, get_location

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Midgley Notebook Generator CLI")
    parser.add_argument(
        "--location", "-l",
        default="ALL",
        help="Target location ID (ALL, national, tulsa, newark, cincinnati, greenville, charlotte, oakland)"
    )
    args = parser.parse_args()
    
    target_loc = args.location.strip().lower()
    
    if target_loc == "all":
        print("=" * 80)
        print("  GENERATING JUPYTER NOTEBOOKS FOR ALL REGISTERED LOCATIONS")
        print("=" * 80)
        paths = build_all_notebooks()
        for loc_id, path in paths.items():
            print(f"  [✓] {LOCATIONS[loc_id]['name']:<35} -> {path}")
        print("=" * 80)
        print("All location notebooks successfully built!")
    else:
        try:
            loc_info = get_location(target_loc)
            print(f"Building Jupyter notebook for location: {loc_info['name']} ({loc_info['id']})...")
            path = loc_info["build_notebook"]()
            print(f"  [✓] Successfully generated notebook at {path}")
        except KeyError as e:
            print(f"Error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
