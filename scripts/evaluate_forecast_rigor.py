#!/usr/bin/env python3
"""
Automated Statistical Forecast Rigor & Hypothesis Evaluation Script (scripts/evaluate_forecast_rigor.py)
Executes:
1. Pesaran-Timmermann Directional Market Timing Tests
2. Multi-Horizon Newey-West HAC Standard Errors
3. Hansen's Model Confidence Set (MCS at alpha = 0.10)
4. Benjamini-Hochberg False Discovery Rate (FDR at q = 0.05)
(Issue #452)
"""

import os
import json
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List
from src.model_evaluation import (
    pesaran_timmermann_test,
    compute_newey_west_hac_standard_error,
    model_confidence_set,
    benjamini_hochberg_fdr_control,
    FeatureAdmissionGate
)
from src.prediction_logger import HISTORY_CSV_PATH, read_prediction_history

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_statistical_forecast_evaluation() -> Dict[str, Any]:
    """
    Evaluates historical predictions in prediction_history.csv with statistical hypothesis testing.
    """
    logger.info("Executing Automated Statistical Forecast Evaluation Harness...")
    report = {
        "timestamp": pd.Timestamp.now().isoformat(),
        "regional_directional_tests": {},
        "newey_west_standard_errors": {},
        "model_confidence_set": {},
        "fdr_control": {}
    }

    if not os.path.exists(HISTORY_CSV_PATH):
        logger.warning(f"Prediction history log not found at {HISTORY_CSV_PATH}")
        return report

    df = read_prediction_history(HISTORY_CSV_PATH)
    if df.empty or "actual_5d_price" not in df.columns:
        return report

    # Filter evaluated rows
    eval_df = df[df["actual_5d_price"].notna() & (df["actual_5d_price"] > 0)].copy()
    if len(eval_df) < 5:
        logger.info(f"Insufficient evaluated prediction history ({len(eval_df)} rows) for statistical evaluation.")
        return report

    # 1. Regional Directional Tests (Pesaran-Timmermann)
    p_values_dict = {}
    for reg, grp in eval_df.groupby("region"):
        if len(grp) >= 5:
            pt_res = pesaran_timmermann_test(
                y_true=grp["actual_5d_price"].values,
                y_pred=grp["predicted_5d_price"].values,
                y_base=grp["current_base_price"].values if "current_base_price" in grp else None
            )
            report["regional_directional_tests"][reg] = pt_res
            p_values_dict[reg] = pt_res["p_value"]

    # 2. Multi-Horizon Newey-West HAC Standard Errors
    for h in [1, 2, 3, 4, 5]:
        h_df = eval_df[eval_df["forecast_horizon_days"] == h]
        if len(h_df) >= 2:
            resids = (h_df["actual_5d_price"] - h_df["predicted_5d_price"]).values
            se = compute_newey_west_hac_standard_error(resids, horizon=h)
            report["newey_west_standard_errors"][f"horizon_{h}d"] = se

    # 3. Model Confidence Set Comparison (Quant Baseline vs Hybrid)
    if "quant_baseline_5d_price" in eval_df.columns and eval_df["quant_baseline_5d_price"].notna().sum() >= 5:
        sub = eval_df[eval_df["quant_baseline_5d_price"].notna()].copy()
        losses_quant = np.abs(sub["actual_5d_price"] - sub["quant_baseline_5d_price"]).values
        losses_hybrid = np.abs(sub["actual_5d_price"] - sub["predicted_5d_price"]).values
        loss_matrix = np.column_stack([losses_quant, losses_hybrid])
        mcs_res = model_confidence_set(loss_matrix, ["Quant_Technical_Baseline", "Hybrid_MultiAgent_Estimator"], alpha=0.10)
        report["model_confidence_set"] = mcs_res

    # 4. Benjamini-Hochberg FDR Control across regions
    if p_values_dict:
        fdr_res = benjamini_hochberg_fdr_control(p_values_dict, q_threshold=0.05)
        report["fdr_control"] = fdr_res

    logger.info("Statistical Forecast Rigor Evaluation completed successfully.")
    return report


if __name__ == "__main__":
    rep = run_statistical_forecast_evaluation()
    print(json.dumps(rep, indent=2))
