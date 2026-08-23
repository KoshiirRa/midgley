"""
Master Execution Script (run_all.py)
Runs both the National Wholesale Model and the Tulsa, OK Regional Model sequentially.
"""

import sys
from main import run_pipeline as run_national
from tulsa_main import run_tulsa_pipeline as run_tulsa

if __name__ == "__main__":
    use_api = "--use-llm-api" in sys.argv
    
    print("=" * 80)
    print("  STEP 1: RUNNING NATIONAL WHOLESALE FORECASTING MODEL")
    print("=" * 80)
    nat_results = run_national(use_llm_api=use_api, model_type="ridge")
    
    print("\n" + "=" * 80)
    print("  STEP 2: RUNNING TULSA, OK METRO RETAIL FORECASTING MODEL")
    print("=" * 80)
    tulsa_results = run_tulsa(live_pump_price=3.89, use_llm_api=use_api, model_type="ridge")
    
    print("\n" + "=" * 80)
    print("                      ALL MODELS EXECUTION COMPLETE")
    print("=" * 80)