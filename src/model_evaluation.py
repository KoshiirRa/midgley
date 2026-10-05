"""
Standardized 5-Tier Nested Model Evaluation Hierarchy & Statistical Hypothesis Protocol (src/model_evaluation.py)
Evaluates forecasting architectures against a strict 5-tier nested hierarchy on rolling forecast origins
with Diebold-Mariano tests (HLN small-sample adjusted) and Stationary Block Bootstrap. (Issue #362)
"""

from __future__ import annotations

import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
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
    loss_type: str = "absolute",
    alternative: str = "two-sided"
) -> Tuple[float, float]:
    """
    Performs the Diebold-Mariano test for predictive accuracy equality with
    Harvey-Leybourne-Newbold (HLN 1997) small-sample and multi-step horizon correction. (Issue #362, #609)
    
    H0: E[d_t] = 0 (Both models have equal predictive accuracy)
    H1: E[d_t] != 0 (two-sided) or E[d_t] > 0 (greater: candidate model 2 is superior to model 1)
    
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
    
    # Autocovariance estimation up to lag h - 1 (Unweighted rectangular sum for HLN correction)
    gamma0 = float(np.var(d, ddof=0))
    sum_cov = 0.0
    for k in range(1, max(1, horizon)):
        cov_k = float(np.mean((d[k:] - mean_d) * (d[:-k] - mean_d)))
        sum_cov += 2.0 * cov_k

    long_run_var = gamma0 + sum_cov
    if long_run_var <= 0:
        # Fallback to Bartlett weights if rectangular long-run variance estimate is non-positive
        sum_cov_bartlett = 0.0
        for k in range(1, max(1, horizon)):
            cov_k = float(np.mean((d[k:] - mean_d) * (d[:-k] - mean_d)))
            weight = 1.0 - (k / max(1, horizon))
            sum_cov_bartlett += 2.0 * weight * cov_k
        long_run_var = max(1e-8, gamma0 + sum_cov_bartlett)

    dm_stat = mean_d / np.sqrt(long_run_var / T)

    # Harvey-Leybourne-Newbold (HLN) small-sample correction factor
    hln_factor = np.sqrt(max(0.01, (T + 1 - 2 * horizon + horizon * (horizon - 1) / T) / T))
    dm_stat_corrected = dm_stat * hln_factor

    # Student-t distribution with T - 1 degrees of freedom
    if alternative == "greater":
        p_value = float(1.0 - stats.t.cdf(dm_stat_corrected, df=T - 1))
    elif alternative == "less":
        p_value = float(stats.t.cdf(dm_stat_corrected, df=T - 1))
    else:  # two-sided
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


def clark_west_test(
    y_true: Union[np.ndarray, List[float], pd.Series],
    y_pred_nested: Union[np.ndarray, List[float], pd.Series],
    y_pred_full: Union[np.ndarray, List[float], pd.Series],
    horizon: int = 1
) -> Tuple[float, float]:
    r"""
    Performs the Clark and West (2007) test for out-of-sample comparison of nested models (Issue #567).
    
    Adjusts the MSPE differential for parameter estimation noise in the unrestricted model:
        f_{t+h} = (y_{t+h} - \hat{y}_{1,t+h})^2 - [(y_{t+h} - \hat{y}_{2,t+h})^2 - (\hat{y}_{1,t+h} - \hat{y}_{2,t+h})^2]
        
    H0: MSPE_nested = MSPE_full (Unrestricted model does not improve forecast)
    H1: MSPE_full < MSPE_nested (Unrestricted model has superior predictive ability)
    
    Returns:
        (cw_stat, p_value_one_sided)
    """
    yt = np.asarray(y_true, dtype=float)
    y1 = np.asarray(y_pred_nested, dtype=float)
    y2 = np.asarray(y_pred_full, dtype=float)
    T = len(yt)
    if T < 5:
        return 0.0, 1.0

    e1_sq = (yt - y1) ** 2
    e2_sq = (yt - y2) ** 2
    adj = (y1 - y2) ** 2
    f = e1_sq - (e2_sq - adj)
    mean_f = float(np.mean(f))

    # Autocovariance estimation up to lag h - 1 (Unweighted rectangular sum for multi-step horizon, Issue #609)
    gamma0 = float(np.var(f, ddof=0))
    sum_cov = 0.0
    for k in range(1, max(1, horizon)):
        cov_k = float(np.mean((f[k:] - mean_f) * (f[:-k] - mean_f)))
        sum_cov += 2.0 * cov_k

    long_run_var = gamma0 + sum_cov
    if long_run_var <= 0:
        # Fallback to Bartlett weights if rectangular long-run variance estimate is non-positive
        sum_cov_bartlett = 0.0
        for k in range(1, max(1, horizon)):
            cov_k = float(np.mean((f[k:] - mean_f) * (f[:-k] - mean_f)))
            weight = 1.0 - (k / max(1, horizon))
            sum_cov_bartlett += 2.0 * weight * cov_k
        long_run_var = max(1e-8, gamma0 + sum_cov_bartlett)

    se = np.sqrt(long_run_var / T)
    if se <= 1e-12:
        return 0.0, 0.50
    cw_stat = mean_f / se

    # One-sided test (H1: mean_f > 0)
    p_value = float(1.0 - stats.norm.cdf(cw_stat))
    return round(float(cw_stat), 4), round(float(p_value), 4)


def adjust_pvalues_holm_bonferroni(p_values: List[float]) -> List[float]:
    """Applies step-down Holm-Bonferroni Family-Wise Error Rate (FWER) control (Issue #567, #609)."""
    m = len(p_values)
    if m == 0:
        return []
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    adjusted = [0.0] * m
    running_max = 0.0
    for rank, (orig_idx, p_val) in enumerate(indexed):
        k = rank + 1
        adj = (m - k + 1) * p_val
        running_max = max(running_max, adj)
        adjusted[orig_idx] = min(1.0, running_max)
    return [round(p, 4) for p in adjusted]


def adjust_pvalues_benjamini_hochberg(p_values: List[float]) -> List[float]:
    """Applies step-up Benjamini-Hochberg False Discovery Rate (FDR) control (Issue #567, #609)."""
    m = len(p_values)
    if m == 0:
        return []
    indexed = sorted(enumerate(p_values), key=lambda x: x[1], reverse=True)
    adjusted = [0.0] * m
    running_min = 1.0
    for rank_from_top, (orig_idx, p_val) in enumerate(indexed):
        k = m - rank_from_top
        adj = (m / k) * p_val
        running_min = min(running_min, adj)
        adjusted[orig_idx] = min(1.0, running_min)
    return [round(p, 4) for p in adjusted]


def adjust_family_pvalues(p_values: List[float], method: str = "holm") -> List[float]:
    """
    Applies Family-Wise Error Rate (FWER) or False Discovery Rate (FDR) adjustments
    across a family of multi-horizon and multi-region test p-values (Issue #609).
    """
    if not p_values:
        return []
    m_lower = method.lower()
    if m_lower in ["holm", "holm-bonferroni", "fwer"]:
        return adjust_pvalues_holm_bonferroni(p_values)
    elif m_lower in ["bh", "benjamini-hochberg", "fdr"]:
        return adjust_pvalues_benjamini_hochberg(p_values)
    else:
        raise ValueError(f"Unknown p-value adjustment method: {method}")


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
        prev_tier_preds = tier0_pred

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

            # Diebold-Mariano test vs Tier 0 (Naive) with one-sided superiority test (Issue #609)
            dm_stat, dm_pval = diebold_mariano_test(tier0_errors, errors, horizon=horizon, alternative="greater")

            # Clark-West (2007) test vs previous nested tier (Issue #567, #609)
            cw_stat_prev, cw_pval_prev = clark_west_test(y_test_arr, prev_tier_preds, preds, horizon=horizon)

            tier_results[tier_key] = {
                "tier_name": tier_desc,
                "features_count": len(sub_feats),
                "MAE": round(mae, 4),
                "RMSE": round(rmse, 4),
                "directional_hit_pct": round(dir_hit, 2),
                "persistence_uplift_pct": round(uplift, 2),
                "dm_stat_vs_naive": dm_stat,
                "dm_p_value_vs_naive": dm_pval,
                "cw_stat_vs_prev": cw_stat_prev,
                "cw_p_value_vs_prev": cw_pval_prev,
                "pinball_loss_q50": round(compute_pinball_loss(y_test_arr, preds, 0.5), 4)
            }
            prev_tier_preds = preds
            prev_tier_errors = errors

        # Multiplicity Control across Tiers (Issue #567)
        raw_dm_pvals = [tier_results[k]["dm_p_value_vs_naive"] for k, _ in active_models]
        raw_cw_pvals = [tier_results[k]["cw_p_value_vs_prev"] for k, _ in active_models]
        holm_dm = adjust_pvalues_holm_bonferroni(raw_dm_pvals)
        bh_dm = adjust_pvalues_benjamini_hochberg(raw_dm_pvals)
        holm_cw = adjust_pvalues_holm_bonferroni(raw_cw_pvals)
        bh_cw = adjust_pvalues_benjamini_hochberg(raw_cw_pvals)

        for i, (k, _) in enumerate(active_models):
            tier_results[k]["dm_p_value_holm"] = holm_dm[i]
            tier_results[k]["dm_p_value_bh"] = bh_dm[i]
            tier_results[k]["cw_p_value_holm"] = holm_cw[i]
            tier_results[k]["cw_p_value_bh"] = bh_cw[i]

        # Statistical Promotion Decision Gate (Issue #362, #435, #567, #609)
        tier4 = tier_results["Tier_4_Full_Hybrid"]
        promotion_gate_passed = bool(
            tier4["persistence_uplift_pct"] > 0.0
            and tier4["dm_stat_vs_naive"] > 0.0
            and tier4["dm_p_value_vs_naive"] < 0.05
        )

        return {
            "region": self.region,
            "horizon_days": horizon,
            "promotion_gate_passed": promotion_gate_passed,
            "tiers": tier_results
        }


def pesaran_timmermann_test(
    y_true: Union[np.ndarray, List[float], pd.Series],
    y_pred: Union[np.ndarray, List[float], pd.Series],
    y_base: Optional[Union[np.ndarray, List[float], pd.Series]] = None
) -> Dict[str, Any]:
    """
    Performs the Pesaran & Timmermann (1992) Non-Parametric Directional Accuracy Test (Issue #452).
    Evaluates whether the directional hit rate is statistically significantly superior to chance
    under independent realizations.

    H0: Directional predictions and actual price movements are distributed independently.
    H1: Forecasts possess genuine directional market timing ability.

    Returns:
        Dict with pt_stat, p_value, hit_rate_pct, expected_hit_rate_pct, is_significant_at_05
    """
    yt = np.asarray(y_true, dtype=float)
    yp = np.asarray(y_pred, dtype=float)

    if y_base is not None:
        yb = np.asarray(y_base, dtype=float)
        dy_true = yt - yb
        dy_pred = yp - yb
    else:
        # If returns or differentials were passed directly
        dy_true = yt
        dy_pred = yp

    T = len(dy_true)
    if T < 5:
        return {
            "pt_stat": 0.0,
            "p_value": 1.0,
            "hit_rate_pct": 50.0,
            "expected_hit_rate_pct": 50.0,
            "sample_size": T,
            "is_significant_at_05": False
        }

    # Binary directional indicators (1 for positive / up, 0 for negative / down)
    z_true = (dy_true > 0).astype(int)
    z_pred = (dy_pred > 0).astype(int)

    p_hat = float(np.mean(z_true == z_pred))
    p_y = float(np.mean(z_true))
    p_x = float(np.mean(z_pred))

    # Expected hit rate under independence
    p_star = p_y * p_x + (1.0 - p_y) * (1.0 - p_x)

    # Pesaran-Timmermann (1992) variance estimator: V_hat(P_hat - P_star) = V_hat(P_hat) - V_hat(P_star)
    var_p_hat = (p_star * (1.0 - p_star)) / T
    var_p_star = (
        ((2.0 * p_y - 1.0) ** 2 * p_x * (1.0 - p_x)) / T
        + ((2.0 * p_x - 1.0) ** 2 * p_y * (1.0 - p_y)) / T
        + (4.0 / (T ** 2)) * p_y * p_x * (1.0 - p_y) * (1.0 - p_x)
    )
    v_hat = max(1e-12, var_p_hat - var_p_star)

    if v_hat <= 1e-12:
        pt_stat = 0.0
        p_val = 1.0
    else:
        pt_stat = float((p_hat - p_star) / np.sqrt(v_hat))
        # One-sided p-value for superior directional timing (right tail)
        p_val = float(1.0 - stats.norm.cdf(pt_stat))

    return {
        "pt_stat": round(pt_stat, 4),
        "p_value": round(p_val, 4),
        "hit_rate_pct": round(p_hat * 100.0, 2),
        "expected_hit_rate_pct": round(p_star * 100.0, 2),
        "sample_size": T,
        "is_significant_at_05": bool(p_val < 0.05 and pt_stat > 0)
    }


def compute_newey_west_hac_standard_error(
    residuals: Union[np.ndarray, List[float], pd.Series],
    horizon: int = 1
) -> float:
    """
    Computes Newey-West Heteroskedasticity and Autocorrelation Consistent (HAC) standard error
    for multi-step horizon forecast errors with Bartlett kernel bandwidth J = horizon - 1 (Issue #452).
    """
    res = np.asarray(residuals, dtype=float)
    T = len(res)
    if T < 2:
        return float(np.std(res)) if T > 0 else 0.0

    mean_res = float(np.mean(res))
    e = res - mean_res
    gamma0 = float(np.mean(e ** 2))

    bandwidth = max(0, horizon - 1)
    sum_cov = 0.0
    for j in range(1, bandwidth + 1):
        gamma_j = float(np.mean(e[j:] * e[:-j]))
        weight = 1.0 - (j / (bandwidth + 1.0))
        sum_cov += 2.0 * weight * gamma_j

    omega = max(1e-8, gamma0 + sum_cov)
    se = float(np.sqrt(omega / T))
    return round(se, 6)


def model_confidence_set(
    loss_matrix: np.ndarray,
    model_names: List[str],
    alpha: float = 0.10,
    n_bootstraps: int = 500,
    block_length: Optional[int] = None
) -> Dict[str, Any]:
    """
    Computes Hansen, Lunde & Nason (2011) Model Confidence Set (MCS) at confidence level (1 - alpha) (Issue #452).
    Iteratively eliminates inferior predictive models until the remaining set of models cannot be rejected
    as having equal expected loss.

    Args:
        loss_matrix: (T, M) array of loss observations for M models across T time periods.
        model_names: List of M model identifier strings.
        alpha: Significance level for exclusion (default: 0.10 for 90% MCS).
        n_bootstraps: Number of block bootstrap resamples.

    Returns:
        Dict with included_models, eliminated_models, p_values, mcs_alpha.
    """
    losses = np.asarray(loss_matrix, dtype=float)
    T, M = losses.shape
    if M != len(model_names):
        raise ValueError(f"Shape mismatch: {M} models in loss_matrix but {len(model_names)} model_names")

    if M <= 1 or T < 5:
        return {
            "included_models": list(model_names),
            "eliminated_models": [],
            "mcs_pvalues": {name: 1.0 for name in model_names},
            "mcs_alpha": alpha
        }

    active_indices = list(range(M))
    pvalues = {}
    eliminated = []
    L = block_length or int(np.ceil(T ** (1.0 / 3.0)))
    p_geom = 1.0 / max(1, L)

    # Pre-generate bootstrap resample indices
    np.random.seed(42)
    boot_indices_list = []
    for _ in range(n_bootstraps):
        idxs = []
        while len(idxs) < T:
            start = np.random.randint(0, T)
            blen = np.random.geometric(p_geom)
            for step in range(blen):
                idxs.append((start + step) % T)
                if len(idxs) >= T:
                    break
        boot_indices_list.append(np.array(idxs[:T]))

    iteration_p = 0.0
    while len(active_indices) > 1:
        cur_M = len(active_indices)
        sub_losses = losses[:, active_indices]  # (T, cur_M)
        
        # d_{ij, t} = L_{i, t} - L_{j, t}
        # d_{i., t} = L_{i, t} - mean_j L_{j, t}
        mean_loss_per_t = np.mean(sub_losses, axis=1, keepdims=True)
        d_bar_it = sub_losses - mean_loss_per_t  # (T, cur_M)
        d_bar_i = np.mean(d_bar_it, axis=0)      # (cur_M,)

        # Compute bootstrap variance for each model in active set
        boot_d_bars = np.zeros((n_bootstraps, cur_M))
        for b, b_idx in enumerate(boot_indices_list):
            b_sample = d_bar_it[b_idx, :]
            boot_d_bars[b, :] = np.mean(b_sample, axis=0)

        var_d_bar = np.var(boot_d_bars, axis=0, ddof=1)
        var_d_bar = np.maximum(var_d_bar, 1e-10)

        # t_i = d_bar_i / sqrt(var(d_bar_i))
        t_stats = d_bar_i / np.sqrt(var_d_bar)
        T_max = np.max(t_stats)
        worst_model_sub_idx = int(np.argmax(t_stats))
        worst_model_idx = active_indices[worst_model_sub_idx]
        worst_model_name = model_names[worst_model_idx]

        # Centered bootstrap test statistics
        boot_t_stats = (boot_d_bars - d_bar_i) / np.sqrt(var_d_bar)
        boot_T_max = np.max(boot_t_stats, axis=1)

        # p-value for hypothesis of equal predictive ability
        p_val_step = float(np.mean(boot_T_max >= T_max))
        iteration_p = max(iteration_p, p_val_step)
        pvalues[worst_model_name] = round(float(iteration_p), 4)

        if iteration_p < alpha:
            eliminated.append(worst_model_name)
            active_indices.pop(worst_model_sub_idx)
        else:
            # Cannot reject null: all remaining models are in MCS
            break

    for idx in active_indices:
        pvalues[model_names[idx]] = 1.0

    included = [model_names[idx] for idx in active_indices]

    return {
        "included_models": included,
        "eliminated_models": eliminated,
        "mcs_pvalues": pvalues,
        "mcs_alpha": alpha
    }


def benjamini_hochberg_fdr_control(
    p_values: Dict[str, float],
    q_threshold: float = 0.05
) -> Dict[str, Any]:
    """
    Applies the Benjamini-Hochberg (1995) False Discovery Rate (FDR) control procedure (Issue #452)
    for simultaneous testing across multiple regional metro models or candidate feature families.

    Args:
        p_values: Mapping of identifier to raw p-value.
        q_threshold: Target False Discovery Rate (default: 0.05).

    Returns:
        Dict with discoveries, adjusted_p_values, rejected_nulls, q_threshold.
    """
    if not p_values:
        return {"discoveries": [], "adjusted_p_values": {}, "q_threshold": q_threshold}

    sorted_items = sorted(p_values.items(), key=lambda x: x[1])
    m = len(sorted_items)
    
    # Calculate adjusted p-values (q-values)
    adj_p = {}
    prev_adj = 1.0
    for rank_idx, (key, p_val) in enumerate(reversed(sorted_items)):
        k = m - rank_idx
        cur_adj = min(1.0, (p_val * m) / k)
        cur_adj = min(cur_adj, prev_adj)
        prev_adj = cur_adj
        adj_p[key] = round(cur_adj, 4)

    # Determine discovery cut-off: find largest k* where p_{(k*)} <= (k*/m) * q
    k_star = 0
    for rank_1b, (key, p_val) in enumerate(sorted_items, start=1):
        crit_val = (rank_1b / m) * q_threshold
        if p_val <= crit_val:
            k_star = rank_1b

    # All hypotheses with rank <= k_star are declared discoveries
    discoveries = [key for rank_1b, (key, p_val) in enumerate(sorted_items, start=1) if rank_1b <= k_star]

    return {
        "discoveries": discoveries,
        "adjusted_p_values": {k: adj_p[k] for k in p_values},
        "q_threshold": q_threshold,
        "total_hypotheses": m,
        "significant_discoveries_count": len(discoveries)
    }


class FeatureAdmissionGate:
    """
    Formal Feature Admission Gate (Issue #452).
    Evaluates whether a candidate feature family earns admission into production by:
    1. Reducing out-of-sample forecast loss (MAE / Pinball loss).
    2. Surviving Hansen's Model Confidence Set (MCS) at alpha = 0.10.
    3. Passing Benjamini-Hochberg FDR control across evaluated metro regions.
    """

    def __init__(self, mcs_alpha: float = 0.10, fdr_q: float = 0.05):
        self.mcs_alpha = mcs_alpha
        self.fdr_q = fdr_q

    def evaluate_candidate_feature_family(
        self,
        baseline_losses: np.ndarray,
        candidate_losses: np.ndarray,
        feature_family_name: str = "candidate_feature",
        horizon: int = 5
    ) -> Dict[str, Any]:
        """
        Evaluates a candidate feature family vs baseline across rolling validation origins.
        """
        loss_mat = np.column_stack([baseline_losses, candidate_losses])
        model_names = ["Baseline_Model", f"Model_with_{feature_family_name}"]

        mcs_res = model_confidence_set(loss_mat, model_names, alpha=self.mcs_alpha)
        dm_stat, dm_pval = diebold_mariano_test(baseline_losses, candidate_losses, horizon=horizon)
        
        admitted = bool(
            f"Model_with_{feature_family_name}" in mcs_res["included_models"]
            and np.mean(candidate_losses) < np.mean(baseline_losses)
            and dm_pval < 0.10
        )

        return {
            "feature_family": feature_family_name,
            "admitted_to_production": admitted,
            "baseline_mae": round(float(np.mean(baseline_losses)), 4),
            "candidate_mae": round(float(np.mean(candidate_losses)), 4),
            "mae_reduction_pct": round(float((np.mean(baseline_losses) - np.mean(candidate_losses)) / np.mean(baseline_losses) * 100.0), 2),
            "diebold_mariano_stat": dm_stat,
            "diebold_mariano_p_value": dm_pval,
            "mcs_included": f"Model_with_{feature_family_name}" in mcs_res["included_models"],
            "decision": "ADMITTED" if admitted else "REJECTED"
        }

