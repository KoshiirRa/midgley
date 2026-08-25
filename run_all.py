"""
Master Execution Script (run_all.py)
Sequentially runs all registered location forecasting models using the src.locations registry.
Updates live README.md forecast tables and regenerates the public docs/ index.html web dashboard.
"""

import sys
import logging
from src.locations import LOCATIONS, run_all_locations
from src.readme_updater import update_readme_forecasts
from src.dashboard_generator import generate_public_dashboard

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    use_api = "--use-llm-api" in sys.argv
    model_choice = "ridge"
    for arg in sys.argv:
        if arg.startswith("--model="):
            model_choice = arg.split("=")[1].lower()
            
    print("=" * 80)
    print("      MIDGLEY MASTER FORECASTING ENGINE - ALL LOCATIONS PIPELINE")
    print("=" * 80)
    
    step_num = 1
    total_steps = len(LOCATIONS) + 1
    
    for loc_id, loc_info in LOCATIONS.items():
        print(f"\n" + "=" * 80)
        print(f"  STEP {step_num}/{total_steps}: RUNNING {loc_info['name'].upper()} MODEL")
        print("=" * 80)
        loc_info["run_pipeline"](use_llm_api=use_api, model_type=model_choice)
        step_num += 1

    print("\n" + "=" * 80)
    print(f"  STEP {total_steps}/{total_steps}: UPDATING LIVE README TABLE & PUBLIC WEB DASHBOARD (docs/)...")
    print("=" * 80)
    update_readme_forecasts()
    generate_public_dashboard()
    
    print("\n" + "=" * 80)
    print("                      ALL LOCATIONS EXECUTION COMPLETE")
    print("=" * 80)