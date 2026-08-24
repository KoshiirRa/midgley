"""
Master Execution Script (run_all.py)
Runs both the National Wholesale Model and the Tulsa, OK Regional Model sequentially.
Updates live README.md forecast tables and regenerates the public docs/index.html web dashboard.
"""

import sys
import logging
from main import run_pipeline as run_national
from tulsa_main import run_tulsa_pipeline as run_tulsa
from newark_main import run_newark_pipeline as run_newark
from cincinnati_main import run_cincinnati_pipeline as run_cincinnati
from oakland_main import run_oakland_pipeline as run_oakland
from src.readme_updater import update_readme_forecasts
from src.dashboard_generator import generate_public_dashboard

if __name__ == "__main__":
    use_api = "--use-llm-api" in sys.argv
    
    print("=" * 80)
    print("  STEP 1: RUNNING NATIONAL WHOLESALE FORECASTING MODEL")
    print("=" * 80)
    nat_results = run_national(use_llm_api=use_api, model_type="ridge")
    
    print("\n" + "=" * 80)
    print("  STEP 2: RUNNING TULSA, OK METRO RETAIL FORECASTING MODEL")
    print("=" * 80)
    tulsa_results = run_tulsa(use_llm_api=use_api, model_type="ridge")

    print("\n" + "=" * 80)
    print("  STEP 3: RUNNING NEWARK, DE METRO RETAIL FORECASTING MODEL")
    print("=" * 80)
    newark_results = run_newark(use_llm_api=use_api, model_type="ridge")
    
    print("\n" + "=" * 80)
    print("  STEP 4: RUNNING CINCINNATI, OH / NKY METRO RETAIL FORECASTING MODEL")
    print("=" * 80)
    cin_results = run_cincinnati(use_llm_api=use_api, model_type="ridge")

    print("\n" + "=" * 80)
    print("  STEP 5: RUNNING OAKLAND & SF BAY AREA METRO RETAIL FORECASTING MODEL")
    print("=" * 80)
    oakland_results = run_oakland(use_llm_api=use_api, model_type="ridge")

    print("\n" + "=" * 80)
    print("  STEP 6: UPDATING LIVE README TABLE & PUBLIC WEB DASHBOARD (docs/)...")
    print("=" * 80)
    update_readme_forecasts()
    generate_public_dashboard()
    
    print("\n" + "=" * 80)
    print("                      ALL MODELS EXECUTION COMPLETE")
    print("=" * 80)