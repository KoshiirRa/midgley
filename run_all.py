"""
Master Execution Script (run_all.py)
Sequentially runs all registered location forecasting models using the src.locations registry.
Updates live README.md forecast tables and regenerates the public docs/ index.html web dashboard.
"""

import os
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
    dashboard_only = "--dashboard-only" in sys.argv
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
            warmup_timeout = float(os.environ.get("HINDSIGHT_WARMUP_TIMEOUT", "75.0"))
            print(f"  [STEP 0] Triggering proactive Hindsight Cloud Run memory service warmup (max_wait={warmup_timeout:.0f}s)...")
            warmup_thread = threading.Thread(
                target=lambda: hindsight.warmup(max_wait_seconds=warmup_timeout, retry_interval=2.0),
                name="hindsight-warmup",
                daemon=True
            )
            warmup_thread.start()
    except Exception as e:
        logger.debug(f"Notice initiating Hindsight warmup: {e}")
    
    step_num = 1
    total_steps = len(LOCATIONS) + 1
    
    failed_locations = []
    if not dashboard_only:
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
    else:
        print("\n  [INFO] Running in --dashboard-only mode: skipping individual location training pipelines.")

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
    try:
        from src.static_api_exporter import export_all_static_api_endpoints
        export_all_static_api_endpoints()
    except Exception as e:
        logger.error(f"Error exporting static API endpoints: {e}", exc_info=True)

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
                rb_p10 = None
                rb_p90 = None
                rb_res_std = None
                cl_p50 = cl_open
                cl_p10 = None
                cl_p90 = None
                cl_res_std = None
                qualitative_catalysts = {}
                tech_indicators = {"rbob_price": rb_open, "wti_price": cl_open, "crack_spread": (rb_open * 42.0) - cl_open}
                phys_feeds = {}

                # 1. Read latest national prediction records
                try:
                    import pandas as pd
                    if os.path.exists("data/prediction_history.csv"):
                        ph_df = pd.read_csv("data/prediction_history.csv")
                        nat_rows = ph_df[ph_df['region'] == 'National']
                        if not nat_rows.empty:
                            latest_nat = nat_rows.iloc[-1]
                            rb_p50 = float(latest_nat['predicted_5d_price'])
                            if pd.notna(latest_nat.get('prediction_lower_95ci')):
                                rb_p10 = float(latest_nat['prediction_lower_95ci'])
                            if pd.notna(latest_nat.get('prediction_upper_95ci')):
                                rb_p90 = float(latest_nat['prediction_upper_95ci'])
                            qualitative_catalysts["overall_price_pressure"] = float(latest_nat.get('llm_price_pressure', 0.0))
                            qualitative_catalysts["supply_disruption"] = float(latest_nat.get('llm_supply_disruption', 0.0))
                except Exception as e:
                    logger.debug(f"Notice reading prediction history for Headline Arena: {e}")

                # 2. Derive multi-factor Crude Oil WTI forecast from market momentum & crack spreads
                try:
                    if len(m_df) >= 6 and 'crude_wti' in m_df.columns:
                        wti_series = m_df['crude_wti'].dropna()
                        if len(wti_series) >= 6:
                            cl_return_5d = (wti_series.iloc[-1] - wti_series.iloc[-6]) / wti_series.iloc[-6]
                            rb_expected_return = (rb_p50 - rb_open) / rb_open if rb_open > 0 else 0.0
                            # Weighted consensus: 40% WTI momentum + 60% downstream RBOB pull
                            wti_expected_return = (0.40 * cl_return_5d) + (0.60 * rb_expected_return)
                            cl_p50 = round(cl_open * (1.0 + wti_expected_return), 2)
                            cl_res_std = round(0.02 * cl_open, 2)
                            cl_p10 = round(cl_p50 - (1.28 * cl_res_std), 2)
                            cl_p90 = round(cl_p50 + (1.28 * cl_res_std), 2)
                except Exception as e:
                    logger.debug(f"Notice deriving WTI Crude forecast for Headline Arena: {e}")

                # 3. Ingest latest run metadata from docs/runs/latest.json
                try:
                    import json
                    if os.path.exists("docs/runs/latest.json"):
                        with open("docs/runs/latest.json", "r", encoding="utf-8") as f:
                            run_meta = json.load(f)
                            if "geopolitical_risk" in run_meta:
                                qualitative_catalysts["geopolitical_risk"] = float(run_meta["geopolitical_risk"])
                            if "opec_action" in run_meta:
                                qualitative_catalysts["opec_action"] = float(run_meta["opec_action"])
                            if "ovx_volatility" in run_meta:
                                phys_feeds["ovx_volatility"] = float(run_meta["ovx_volatility"])
                            if "rig_count" in run_meta:
                                phys_feeds["rig_count"] = int(run_meta["rig_count"])
                except Exception as e:
                    logger.debug(f"Notice reading latest run metadata for Headline Arena: {e}")

                ha_res = submit_midgley_energy_forecasts(
                    rb_open_price=rb_open,
                    rb_p50=rb_p50,
                    rb_p10=rb_p10,
                    rb_p90=rb_p90,
                    rb_residual_std=rb_res_std,
                    cl_open_price=cl_open,
                    cl_p50=cl_p50,
                    cl_p10=cl_p10,
                    cl_p90=cl_p90,
                    cl_residual_std=cl_res_std,
                    qualitative_catalysts=qualitative_catalysts,
                    technical_indicators=tech_indicators,
                    physical_feeds=phys_feeds,
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