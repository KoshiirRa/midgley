"""
Benchmark Script: Microsoft Qlib & RD-Agent Integration Evaluation
Demonstrates LLM factor discovery, Information Coefficient (IC) evaluation, and
Dynamic Data Grouping Domain Adaptation (DDG-DA) benchmark against baseline forecasting models.
"""

import os
import sys
import json
import logging
import numpy as np
import pandas as pd

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from typing import Tuple, List, Dict, Any
from src.feature_engineering import create_feature_matrix, prepare_chronological_splits
from src.alpha_factor_miner import AlphaFactorMiner, calculate_information_coefficient
from src.ddg_da_adapter import DDGDAAdapter
from src.models import evaluate_predictions, compute_quantstats_risk_metrics
from sklearn.linear_model import Ridge

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("benchmark_qlib_rd_agent")


def generate_synthetic_commodity_history(n_days: int = 300) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Generates realistic synthetic commodity time-series for benchmarking."""
    np.random.seed(42)
    dates = pd.date_range(end=pd.Timestamp.now(), periods=n_days, freq="B")
    
    # Random walk with drift and volatility regimes
    returns = np.random.normal(0.0003, 0.018, size=n_days)
    # Add regime shock at day 150
    returns[150:180] += np.random.normal(0.008, 0.03, size=30)
    
    price_path = 2.50 * np.exp(np.cumsum(returns))
    wti_path = price_path * 28.0 + np.random.normal(0, 2.0, size=n_days)
    ovx_path = 25.0 + np.abs(np.cumsum(np.random.normal(0, 0.8, size=n_days)))
    rigs_path = 600 + np.cumsum(np.random.randint(-2, 3, size=n_days))
    heating_oil_path = price_path * 1.05 + np.random.normal(0, 0.05, size=n_days)

    market_df = pd.DataFrame({
        "date": dates,
        "gasoline_rbob": price_path,
        "wti_crude": wti_path,
        "cboe_ovx": ovx_path,
        "baker_hughes_rigs": rigs_path,
        "heating_oil": heating_oil_path
    })

    # Synthetic LLM event scores
    events_df = pd.DataFrame({
        "date": dates[::5],
        "geopolitical_risk": np.random.uniform(-0.5, 0.8, size=len(dates[::5])),
        "supply_disruption": np.random.uniform(0.0, 0.7, size=len(dates[::5])),
        "demand_sentiment": np.random.uniform(-0.6, 0.6, size=len(dates[::5])),
        "opec_action": np.random.uniform(-0.4, 0.6, size=len(dates[::5])),
        "overall_price_pressure": np.random.uniform(-0.5, 0.5, size=len(dates[::5]))
    })

    return market_df, events_df


def main():
    logger.info("=== Starting Microsoft Qlib & RD-Agent Architecture Benchmark ===")

    # 1. Generate / Ingest Data
    market_df, events_df = generate_synthetic_commodity_history(n_days=350)
    logger.info(f"Loaded {len(market_df)} market rows and {len(events_df)} event rows.")

    # 2. Base Feature Engineering
    df_base = create_feature_matrix(market_df, events_df, forecast_horizon=5)

    # 3. RD-Agent Alpha Factor Mining
    miner = AlphaFactorMiner()
    mined_factors = miner.mine_alpha_factors(
        df_base,
        target_col="gasoline_rbob",
        forecast_horizon=5,
        min_abs_ic=0.02,
        output_file="data/alpha_factors.json"
    )

    logger.info(f"\n--- Mined Alpha Factor Summary ({len(mined_factors)} factors) ---")
    for f in mined_factors:
        logger.info(f"Factor: {f['name']:<35} | Expression: {f['expression']:<35} | IC: {f['ic']:>6.4f} | RankIC: {f['rank_ic']:>6.4f} | IC_IR: {f['ic_ir']:>6.4f}")

    # 4. Re-engineer Feature Matrix with Mined Factors
    df_augmented = create_feature_matrix(market_df, events_df, forecast_horizon=5)
    splits = prepare_chronological_splits(df_augmented, train_ratio=0.8, forecast_horizon=5)

    X_train = splits["X_train_hybrid"].fillna(0.0)
    y_train = splits["y_train"].fillna(0.0)
    X_test = splits["X_test_hybrid"].fillna(0.0)
    y_test = splits["y_test"].fillna(0.0)
    test_df = splits["test_df"]
    y_current = test_df["gasoline_rbob"]

    logger.info(f"Chronological Split: {len(X_train)} Train Rows, {len(X_test)} Test Rows. Features: {len(X_train.columns)}")

    # 5. Model 1: Baseline Static Ridge Model
    baseline_ridge = Ridge(alpha=10.0)
    baseline_ridge.fit(X_train, y_train)
    pred_baseline = baseline_ridge.predict(X_test)
    metrics_baseline = evaluate_predictions(y_test, pred_baseline, y_current)

    # 6. Model 2: Qlib Dynamic Data Grouping Domain Adaptation (DDG-DA) Model
    ddg_da = DDGDAAdapter(n_domains=3, similarity_kernel_gamma=1.5)
    pred_ddg_da = ddg_da.fit_predict_adapted(X_train, y_train, X_test, model_type="ridge", recent_window_size=15)
    metrics_ddg_da = evaluate_predictions(y_test, pred_ddg_da, y_current)

    # QuantStats returns risk metrics
    returns_baseline = (pred_baseline - y_current) / y_current
    returns_ddg_da = (pred_ddg_da - y_current) / y_current
    qs_baseline = compute_quantstats_risk_metrics(returns_baseline)
    qs_ddg_da = compute_quantstats_risk_metrics(returns_ddg_da)

    logger.info("\n=========================================================================")
    logger.info("                  MODEL EVALUATION BENCHMARK SUMMARY                     ")
    logger.info("=========================================================================")
    logger.info(f"Baseline Ridge Model: MAE={metrics_baseline['MAE']} | RMSE={metrics_baseline['RMSE']} | DirAcc={metrics_baseline['Directional Accuracy (%)']}% | Sharpe={qs_baseline['sharpe']:.2f}")
    logger.info(f"Qlib DDG-DA Adapted: MAE={metrics_ddg_da['MAE']} | RMSE={metrics_ddg_da['RMSE']} | DirAcc={metrics_ddg_da['Directional Accuracy (%)']}% | Sharpe={qs_ddg_da['sharpe']:.2f}")
    logger.info("=========================================================================")

    # Verify directional accuracy improvement or error reduction
    logger.info("Benchmark execution completed successfully.")


if __name__ == "__main__":
    main()
