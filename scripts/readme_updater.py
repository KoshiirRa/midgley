#!/usr/bin/env python3
"""
README Live Forecast Updater CLI (scripts/readme_updater.py)
Reads latest prediction history and injects updated live forecast summary table into README.md (Issue #398).
"""

import os
import sys
import argparse
import logging

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.readme_updater import update_readme_forecasts

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Update live forecast summary table in README.md")
    parser.add_argument("--readme", type=str, default="README.md", help="Path to README.md file (default: README.md)")
    parser.add_argument("--history", type=str, default=os.path.join("data", "prediction_history.csv"), help="Path to prediction history CSV")
    args = parser.parse_args()

    logger.info(f"Updating live forecast summary table in {args.readme} from {args.history}...")
    update_readme_forecasts(readme_path=args.readme, history_csv_path=args.history)
    logger.info("README live forecast table update completed successfully.")


if __name__ == "__main__":
    main()
