"""
Master Execution Script (run_all.py)
Sequentially runs all registered location forecasting models using the src.locations registry.
Updates live README.md forecast tables and regenerates the public docs/ index.html web dashboard.
"""

import sys
import logging
import threading
from src.locations import LOCATIONS, run_all_locations
from src.readme_updater import update_readme_forecasts
from src.dashboard_generator import generate_public_dashboard
from src.hindsight_client import HindsightClient

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

    # Step 0: Non-blocking proactive warmup for Hindsight scale-to-zero memory service
    try:
        hindsight = HindsightClient()
        if hindsight.is_configured:
            print("  [STEP 0] Triggering proactive Hindsight Cloud Run memory service warmup...")
            warmup_thread = threading.Thread(
                target=lambda: hindsight.warmup(max_wait_seconds=35.0, retry_interval=2.0),
                name="hindsight-warmup",
                daemon=True
            )
            warmup_thread.start()
    except Exception as e:
        logger.debug(f"Notice initiating Hindsight warmup: {e}")
    
    step_num = 1
    total_steps = len(LOCATIONS) + 1
    
    failed_locations = []
    for loc_id, loc_info in LOCATIONS.items():
        print(f"\n" + "=" * 80)
        print(f"  STEP {step_num}/{total_steps}: RUNNING {loc_info['name'].upper()} MODEL")
        print("=" * 80)
        try:
            loc_info["run_pipeline"](use_llm_api=use_api, model_type=model_choice)
        except Exception as e:
            logger.error(f"Error executing pipeline for location {loc_id}: {e}", exc_info=True)
            failed_locations.append((loc_id, str(e)))
        step_num += 1

    print("\n" + "=" * 80)
    print(f"  STEP {total_steps}/{total_steps}: UPDATING LIVE README TABLE & PUBLIC WEB DASHBOARD (docs/)...")
    print("=" * 80)
    try:
        update_readme_forecasts()
    except Exception as e:
        logger.error(f"Error updating README forecasts: {e}", exc_info=True)
    try:
        generate_public_dashboard()
    except Exception as e:
        logger.error(f"Error generating public dashboard: {e}", exc_info=True)

    # Optional Headline Arena Independent CRPS/Brier Benchmark Submission (Issue #182)
    submit_ha = "--submit-headline-arena" in sys.argv
    live_dev = "--live-dev" in sys.argv or os.environ.get("HEADLINE_ARENA_DEV_SUBMIT") == "1"
    try:
        from src.headline_arena_connector import HeadlineArenaConnector, submit_midgley_energy_forecasts
        from src.data_ingestion import fetch_market_data
        connector = HeadlineArenaConnector()
        if submit_ha or (connector.is_prod and connector.is_configured):
            print("\n" + "=" * 80)
            print("  HEADLINE ARENA BENCHMARK SUBMISSION (RB & CL)")
            print("=" * 80)
            m_df = fetch_market_data(start_date="2024-01-01")
            if not m_df.empty:
                rb_open = float(m_df['gasoline_rbob'].iloc[-1])
                cl_open = float(m_df['crude_wti'].iloc[-1]) if 'crude_wti' in m_df.columns else 75.0
                rb_p50 = rb_open
                try:
                    import pandas as pd
                    import os
                    if os.path.exists("data/prediction_history.csv"):
                        ph_df = pd.read_csv("data/prediction_history.csv")
                        nat_rows = ph_df[ph_df['region'] == 'National']
                        if not nat_rows.empty:
                            rb_p50 = float(nat_rows['predicted_5d_price'].iloc[-1])
                except Exception:
                    pass
                ha_res = submit_midgley_energy_forecasts(
                    rb_open_price=rb_open,
                    rb_p50=rb_p50,
                    cl_open_price=cl_open,
                    cl_p50=cl_open,
                    live_in_dev=live_dev
                )
                print(f"  -> Headline Arena Submission: {ha_res}")
    except Exception as e:
        logger.debug(f"Notice during Headline Arena execution: {e}")
    
    if failed_locations:
        print("\n" + "!" * 80)
        print(f"  WARNING: {len(failed_locations)} location(s) encountered errors during execution:")
        for loc_id, err in failed_locations:
            print(f"    - {loc_id}: {err}")
        print("!" * 80)
        if len(failed_locations) == len(LOCATIONS):
            sys.exit(1)

    print("\n" + "=" * 80)
    print("                      ALL LOCATIONS EXECUTION COMPLETE")
    print("=" * 80)