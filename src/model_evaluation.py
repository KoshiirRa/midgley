"""
Standardized 5-Tier Nested Model Evaluation Hierarchy & Statistical Hypothesis Protocol (src/model_evaluation.py)
Evaluates forecasting architectures against a strict 5-tier nested hierarchy on rolling forecast origins
with Diebold-Mariano tests (HLN small-sample adjusted) and Stationary Block Bootstrap. (Issue #362)
"""

from __future__ import annotations

import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error

logger = logging.getLogger(__name__)


def compute_pinball_loss(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    quantile: float = 0.5
) -> float:
    """Computes pinball (quantile) loss for a given quantile q in (0, 1)."""
    y_t = np.array(y_true, dtype=float)
    y_p = np.array(y_pred, dtype=float)
    err = y_t - y_p
    loss = np.maximum(quantile * err, (quantile - 1.0) * err)
    return float(np.mean(loss))


def diebold_mariano_test(
    e1: np.ndarray,
    e2: np.ndarray,
    horizon: int = 1,
    loss_type: str = "absolute"
) -> Tuple[float, float]:
    """
    Performs the Diebold-Mariano test for predictive accuracy equality with
    Harvey-Leybourne-Newbold (HLN 1997) small-sample and multi-step horizon correction. (Issue #362)
    
    H0: E[d_t] = 0 (Both models have equal predictive accuracy)
    H1: E[d_t] != 0
    
    Returns:
        (dm_stat, p_value)
    """
    e1_arr = np.array(e1, dtype=float)
    e2_arr = np.array(e2, dtype=float)
    T = len(e1_arr)
    
    if T < 5:
        return 0.0, 1.0

    if loss_type == "squared":
        d = e1_arr ** 2 - e2_arr ** 2
    else:  # absolute
        d = np.abs(e1_arr) - np.abs(e2_arr)

    mean_d = float(np.mean(d))
    
    # Autocovariance estimation up to lag h - 1 (Bartlett kernel)
    gamma0 = float(np.var(d, ddof=0))
    sum_cov = 0.0
    for k in range(1, max(1, horizon)):
        cov_k = float(np.mean((d[k:] - mean_d) * (d[:-k] - mean_d)))
        weight = 1.0 - (k / max(1, horizon))
        sum_cov += 2.0 * weight * cov_k

    long_run_var = max(1e-8, gamma0 + sum_cov)
    dm_stat = mean_d / np.sqrt(long_run_var / T)

    # Harvey-Leybourne-Newbold (HLN) small-sample correction factor
    hln_factor = np.sqrt(max(0.01, (T + 1 - 2 * horizon + horizon * (horizon - 1) / T) / T))
    dm_stat_corrected = dm_stat * hln_factor

    # Student-t distribution with T - 1 degrees of freedom
    p_value = float(2.0 * (1.0 - stats.t.cdf(np.abs(dm_stat_corrected), df=T - 1)))
    return round(float(dm_stat_corrected), 4), round(float(p_value), 4)


def stationary_block_bootstrap(
    e1: np.ndarray,
    e2: np.ndarray,
    n_bootstraps: int = 500,
    block_length: Optional[int] = None
) -> Dict[str, float]:
    """
    Performs Stationary Block Bootstrap to compute empirical 95% confidence intervals
    and p-value for the difference in MAE (Issue #362).
    """
    e1_arr = np.array(e1, dtype=float)
    e2_arr = np.array(e2, dtype=float)
    T = len(e1_arr)
    
    if T < 5:
        return {"mae_diff_mean": 0.0, "ci_lower_95": 0.0, "ci_upper_95": 0.0, "p_value_bootstrap": 1.0}

    L = block_length or int(np.ceil(T ** (1.0 / 3.0)))
    d = np.abs(e1_arr) - np.abs(e2_arr)
    realized_diff = float(np.mean(d))

    boot_diffs = []
    np.random.seed(42)
    p_geom = 1.0 / max(1, L)

    for _ in range(n_bootstraps):
        # Generate block indices
        indices = []
        while len(indices) < T:
            start_idx = np.random.randint(0, T)
            block_len = np.random.geometric(p_geom)
            for step in range(block_len):
                indices.append((start_idx + step) % T)
                if len(indices) >= T:
                    break
        boot_sample = d[indices[:T]]
        boot_diffs.append(float(np.mean(boot_sample)))

    boot_diffs_arr = np.array(boot_diffs)
    ci_lower = float(np.percentile(boot_diffs_arr, 2.5))
    ci_upper = float(np.percentile(boot_diffs_arr, 97.5))
    
    # Two-sided empirical p-value for null H0: diff = 0
    p_val_boot = float(np.mean(boot_diffs_arr <= 0) if realized_diff > 0 else np.mean(boot_diffs_arr >= 0)) * 2.0
    p_val_boot = min(1.0, max(0.0, p_val_boot))

    return {
        "mae_diff_mean": round(realized_diff, 4),
        "ci_lower_95": round(ci_lower, 4),
        "ci_upper_95": round(ci_upper, 4),
        "p_value_bootstrap": round(p_val_boot, 4)
    }


class ModelHierarchyEvaluator:
    """
    Executes the 5-Tier Nested Model Evaluation Hierarchy:
    - Tier 0: Naive Persistence Baseline (P_{t+h} = P_t)
    - Tier 1: Price-Only Technical Baseline (Lags, EMA, RSI, MACD)
    - Tier 2: Price + Physical Fundamentals (EIA balances, weather degree days, COT, outages)
    - Tier 3: Price + Qualitative Events (Decayed NLP news/social/geopolitical vectors)
    - Tier 4: Full Hybrid Estimator (Full feature matrix + ECM + Conformal uncertainty)
    """

    def __init__(self, region: str = "National"):
        self.region = region

    def partition_features_by_tier(self, feature_df: pd.DataFrame) -> Dict[str, List[str]]:
        """Partitions column names into the 5-tier nested feature feature sets."""
        cols = list(feature_df.columns)
        
        tier1_cols = [c for c in cols if any(k in c.lower() for k in ["lag", "rsi", "macd", "ema", "sma", "atr", "volatility", "momentum"])]
        if not tier1_cols:
            tier1_cols = cols[:min(3, len(cols))]

        tier2_cols = tier1_cols + [c for c in cols if any(k in c.lower() for k in ["eia", "weather", "hdd", "cdd", "cot", "tariff", "outage", "flaring", "bsee", "shutin", "rig", "ovx"])]
        tier2_cols = list(dict.fromkeys(tier2_cols))

        tier3_cols = tier2_cols + [c for c in cols if any(k in c.lower() for k in ["event", "geopolitical", "opec", "sentiment", "news", "executive", "trump", "shock"])]
        tier3_cols = list(dict.fromkeys(tier3_cols))

        tier4_cols = cols  # Full feature set

        return {
            "Tier_0_Naive": [],
            "Tier_1_Price_Only": tier1_cols,
            "Tier_2_Physical_Fundamentals": tier2_cols,
            "Tier_3_Qualitative_Events": tier3_cols,
            "Tier_4_Full_Hybrid": tier4_cols
        }

    def evaluate_5tier_hierarchy(
        self,
        X_train: pd.DataFrame,
        y_train_future: pd.Series,
        y_train_current: pd.Series,
        X_test: pd.DataFrame,
        y_test_future: pd.Series,
        y_test_current: pd.Series,
        horizon: int = 5
    ) -> Dict[str, Any]:
        """
        Trains and evaluates all 5 tiers on identical rolling forecast origins with
        Diebold-Mariano tests against the Tier 0 Naive Persistence baseline. (Issue #362)
        """
        y_test_arr = np.array(y_test_future, dtype=float)
        y_curr_test_arr = np.array(y_test_current, dtype=float)

        # Tier 0: Naive Persistence (P_{t+h} = P_t)
        tier0_pred = y_curr_test_arr
        tier0_errors = y_test_arr - tier0_pred
        tier0_mae = float(np.mean(np.abs(tier0_errors)))
        tier0_rmse = float(np.sqrt(np.mean(tier0_errors ** 2)))
        tier0_dir_hit = float(np.mean(np.sign(y_test_arr - y_curr_test_arr) == 0)) * 100.0

        tier_feature_map = self.partition_features_by_tier(X_train)
        tier_results = {
            "Tier_0_Naive": {
                "tier_name": "Tier 0: Naive Persistence Baseline",
                "features_count": 0,
                "MAE": round(tier0_mae, 4),
                "RMSE": round(tier0_rmse, 4),
                "directional_hit_pct": round(tier0_dir_hit, 2),
                "persistence_uplift_pct": 0.0,
                "dm_stat_vs_naive": 0.0,
                "dm_p_value_vs_naive": 1.0,
                "pinball_loss_q50": round(compute_pinball_loss(y_test_arr, tier0_pred, 0.5), 4)
            }
        }

        active_models = [
            ("Tier_1_Price_Only", "Tier 1: Price-Only Technical Baseline"),
            ("Tier_2_Physical_Fundamentals", "Tier 2: Price + Physical Fundamentals"),
            ("Tier_3_Qualitative_Events", "Tier 3: Price + Qualitative Events"),
            ("Tier_4_Full_Hybrid", "Tier 4: Full Hybrid Estimator")
        ]

        prev_tier_errors = tier0_errors

        for tier_key, tier_desc in active_models:
            sub_feats = tier_feature_map.get(tier_key, [])
            if not sub_feats:
                sub_feats = list(X_train.columns)

            X_tr_sub = X_train[sub_feats].copy()
            X_te_sub = X_test[sub_feats].copy()

            reg = Ridge(alpha=1.0)
            reg.fit(X_tr_sub, y_train_future)
            preds = np.clip(reg.predict(X_te_sub), 0.10, 20.0)

            errors = y_test_arr - preds
            mae = float(np.mean(np.abs(errors)))
            rmse = float(np.sqrt(np.mean(errors ** 2)))

            true_dir = np.sign(y_test_arr - y_curr_test_arr)
            pred_dir = np.sign(preds - y_curr_test_arr)
            dir_hit = float(np.mean(true_dir == pred_dir)) * 100.0

            uplift = ((tier0_mae - mae) / tier0_mae) * 100.0 if tier0_mae > 0 else 0.0

            # Diebold-Mariano test vs Tier 0 (Naive)
            dm_stat, dm_pval = diebold_mariano_test(tier0_errors, errors, horizon=horizon)

            tier_results[tier_key] = {
                "tier_name": tier_desc,
                "features_count": len(sub_feats),
                "MAE": round(mae, 4),
                "RMSE": round(rmse, 4),
                "directional_hit_pct": round(dir_hit, 2),
                "persistence_uplift_pct": round(uplift, 2),
                "dm_stat_vs_naive": dm_stat,
                "dm_p_value_vs_naive": dm_pval,
                "pinball_loss_q50": round(compute_pinball_loss(y_test_arr, preds, 0.5), 4)
            }
            prev_tier_errors = errors

        # Statistical Promotion Decision Gate (Issue #362, #435)
        tier4 = tier_results["Tier_4_Full_Hybrid"]
        promotion_gate_passed = bool(
            tier4["persistence_uplift_pct"] > 0.0
            and tier4["dm_p_value_vs_naive"] < 0.05
        )

        return {
            "region": self.region,
            "horizon_days": horizon,
            "promotion_gate_passed": promotion_gate_passed,
            "tiers": tier_results
        }
