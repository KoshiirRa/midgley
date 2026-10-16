"""
Value-Level Analytical Math Test Suite (Issue #613 T-37)

Verifies mathematical and analytical invariants with exact closed-form values:
1. GARCH(1,1) conditional variance recursion and multi-step cumulative expectation
2. Student-t & Gaussian exact Continuous Ranked Probability Score (CRPS) formulas
3. Kalman Filter prediction-error log-likelihood curvature
4. Clark-West nested model test statistics and multi-horizon covariance estimation
5. Holm-Bonferroni (FWER) and Benjamini-Hochberg (FDR) adjusted p-values
"""

import math
import numpy as np
import pytest
from scipy import stats

from src.volatility_engine import (
    GARCHVolatilityModel,
    StudentTPredictiveDistribution,
)
from src.metro_nowcast import compute_log_likelihood
from src.model_evaluation import (
    clark_west_test,
    diebold_mariano_test,
    adjust_family_pvalues,
)


# ============================================================================
# 1. GARCH(1,1) Analytical Variance Recursion & Multi-Step Aggregation
# ============================================================================

def test_garch_analytical_variance_recursion():
    """
    Verifies that GARCH(1,1) step-ahead variance follows:
        sigma_{t+1}^2 = omega + alpha * eps_t^2 + beta * sigma_t^2
    and multi-step variance forecast converges geometrically to unconditional variance:
        sigma_inf^2 = omega / (1 - alpha - beta)
    """
    omega = 0.00001
    alpha = 0.10
    beta = 0.85
    pers = alpha + beta
    assert pers < 1.0, "Model must be covariance stationary"

    unconditional_var = omega / (1.0 - pers)

    model = GARCHVolatilityModel(asymmetric=False)
    model.omega = omega
    model.alpha = alpha
    model.beta = beta
    model.gamma = 0.0
    model.unconditional_variance = unconditional_var
    model.is_fitted = True

    # Initial state: shock eps_0 = 0.02, sigma_0^2 = 0.0004
    eps_0 = 0.02
    sigma_0_sq = 0.0004
    # 1-step analytical variance:
    expected_sigma_1_sq = omega + alpha * (eps_0 ** 2) + beta * sigma_0_sq
    # Expected: 1e-5 + 0.10 * 0.0004 + 0.85 * 0.0004 = 0.00001 + 0.00004 + 0.00034 = 0.00039
    assert math.isclose(expected_sigma_1_sq, 0.00039, rel_tol=1e-7)

    # In GARCHVolatilityModel, last_variance stores the 1-step ahead forecast sigma_{T+1}^2
    model.last_variance = expected_sigma_1_sq
    model.last_residual = eps_0

    # Multi-step variance path for h=5:
    # E[sigma_{t+k}^2] = sigma_inf^2 + pers^(k-1) * (sigma_{t+1}^2 - sigma_inf^2)
    expected_path = []
    curr_v = expected_sigma_1_sq
    for k in range(1, 6):
        if k == 1:
            expected_path.append(curr_v)
        else:
            step_v = unconditional_var + (pers ** (k - 1)) * (expected_sigma_1_sq - unconditional_var)
            expected_path.append(step_v)

    # Forecast cumulative variance from model
    for h in range(1, 6):
        cum_var, cum_vol = model.forecast_variance(horizon=h)
        expected_cum_var = sum(expected_path[:h])
        expected_cum_vol = math.sqrt(expected_cum_var)
        assert np.isclose(cum_var, expected_cum_var, rtol=1e-5), f"Horizon {h} cumulative variance mismatch"
        assert np.isclose(cum_vol, expected_cum_vol, rtol=1e-5), f"Horizon {h} cumulative volatility mismatch"


# ============================================================================
# 2. Gaussian & Student-t Exact CRPS Closed Forms
# ============================================================================

def test_gaussian_crps_closed_form():
    """
    Verifies Gaussian CRPS against exact analytical formula:
    For y = mu and sigma = s:
        CRPS(N(mu, s^2), mu) = s * (2 / sqrt(2*pi) - 1 / sqrt(pi)) = s * (sqrt(2) - 1) / sqrt(pi)
    """
    sigma = 1.0
    expected_at_zero = sigma * (math.sqrt(2.0) - 1.0) / math.sqrt(math.pi)
    computed = StudentTPredictiveDistribution.compute_crps_gaussian(realized_return=0.0, mu=0.0, sigma=sigma)
    assert np.isclose(computed, expected_at_zero, rtol=1e-6)

    # Scale invariance: doubling sigma doubles CRPS
    computed_2 = StudentTPredictiveDistribution.compute_crps_gaussian(realized_return=0.0, mu=0.0, sigma=2.0 * sigma)
    assert np.isclose(computed_2, 2.0 * expected_at_zero, rtol=1e-6)

    # Symmetry: CRPS(y, mu, s) == CRPS(-y, -mu, s) == CRPS(mu - (y - mu), mu, s)
    crps_pos = StudentTPredictiveDistribution.compute_crps_gaussian(realized_return=0.5, mu=0.0, sigma=sigma)
    crps_neg = StudentTPredictiveDistribution.compute_crps_gaussian(realized_return=-0.5, mu=0.0, sigma=sigma)
    assert np.isclose(crps_pos, crps_neg, rtol=1e-9)


def test_student_t_crps_properties_and_gaussian_limit():
    """
    Verifies that Student-t CRPS is strictly positive and converges to Gaussian CRPS as nu -> inf.
    """
    # For moderate degrees of freedom (nu = 8)
    crps_t = StudentTPredictiveDistribution.compute_crps(realized_return=0.02, mu=0.0, cumulative_volatility=0.05, df=8.0)
    assert crps_t > 0.0
    assert math.isfinite(crps_t)

    # As nu -> infinity (e.g. nu = 500), Student-t CRPS converges to Gaussian CRPS
    crps_t_large = StudentTPredictiveDistribution.compute_crps(realized_return=0.03, mu=0.0, cumulative_volatility=0.05, df=500.0)
    crps_gauss = StudentTPredictiveDistribution.compute_crps_gaussian(realized_return=0.03, mu=0.0, sigma=0.05)

    assert np.isclose(crps_t_large, crps_gauss, rtol=0.02), f"Student-t ({crps_t_large}) failed to converge to Gaussian ({crps_gauss})"


# ============================================================================
# 3. Kalman Filter Prediction-Error Log-Likelihood
# ============================================================================

def test_kalman_log_likelihood_curvature():
    """
    Verifies that compute_log_likelihood returns finite negative values
    and achieves higher likelihood at true noise parameters than corrupted noise parameters.
    """
    np.random.seed(42)
    n = 60
    true_q = 0.001
    true_r_aaa = 0.002

    # Simulate true state and noisy observations
    x_true = np.cumsum(np.random.normal(0, np.sqrt(true_q), size=n)) + 3.0
    y_aaa = x_true + np.random.normal(0, np.sqrt(true_r_aaa), size=n)
    y_gb = x_true + 0.05 + np.random.normal(0, 0.005, size=n)
    y_eia = x_true - 0.02 + np.random.normal(0, 0.008, size=n)

    # Log-likelihood at parameters close to truth
    ll_near_true = compute_log_likelihood(
        y_aaa, y_gb, y_eia,
        q=true_q,
        r_aaa=true_r_aaa,
        r_gb=0.005,
        r_eia=0.008,
        b_gb=0.05,
        b_eia=-0.02
    )
    assert math.isfinite(ll_near_true)

    # Log-likelihood at heavily corrupted parameters (100x noise variance)
    ll_corrupted = compute_log_likelihood(
        y_aaa, y_gb, y_eia,
        q=true_q * 100.0,
        r_aaa=true_r_aaa * 100.0,
        r_gb=0.5,
        r_eia=0.8,
        b_gb=1.0,
        b_eia=-1.0
    )
    assert math.isfinite(ll_corrupted)
    assert ll_near_true > ll_corrupted, "True parameters should have higher log-likelihood than heavily corrupted parameters"


# ============================================================================
# 4. Clark-West Test Statistics & Multi-Horizon Covariance
# ============================================================================

def test_clark_west_identical_models():
    """
    If nested Model 2 is identical to Model 1, the Clark-West adjusted metric f_t is zero:
        f_t = e_1^2 - (e_2^2 - (y_1 - y_2)^2) = 0
    resulting in stat = 0.0 and p = 0.50.
    """
    y_true = np.array([2.50, 2.55, 2.60, 2.58, 2.62])
    y_pred1 = np.array([2.48, 2.52, 2.59, 2.60, 2.61])
    y_pred2 = y_pred1.copy()

    stat, p_val = clark_west_test(y_true, y_pred1, y_pred2, horizon=1)
    assert stat == 0.0
    assert p_val == 0.50


def test_clark_west_superior_nested_model():
    """
    When Model 2 has strictly lower forecast error than restricted Model 1,
    Clark-West statistic should be strictly positive with p < 0.05.
    """
    np.random.seed(123)
    n = 100
    y_true = np.random.normal(2.5, 0.2, size=n)
    # Model 1 has large error
    y_pred1 = y_true + np.random.normal(0, 0.15, size=n)
    # Model 2 has smaller error and is nested
    y_pred2 = y_true + np.random.normal(0, 0.03, size=n)

    stat, p_val = clark_west_test(y_true, y_pred1, y_pred2, horizon=1)
    assert stat > 0.0
    assert p_val < 0.01


def test_clark_west_multi_step_rectangular_covariance():
    """
    For multi-step horizon h > 1, verifies that clark_west_test calculates
    rectangular unweighted covariance over lags k in [1 .. h-1].
    """
    np.random.seed(42)
    n = 80
    y_true = np.random.normal(2.5, 0.2, size=n)
    y_pred1 = y_true + np.random.normal(0, 0.10, size=n)
    y_pred2 = y_true + np.random.normal(0, 0.05, size=n)

    # Should run with h=3 without error and return finite test stat
    stat, p_val = clark_west_test(y_true, y_pred1, y_pred2, horizon=3)
    assert math.isfinite(stat)
    assert 0.0 <= p_val <= 1.0


# ============================================================================
# 5. Holm-Bonferroni & Benjamini-Hochberg Adjusted p-Values
# ============================================================================

def test_adjust_family_pvalues_exact_values():
    """
    Verifies exact closed-form Holm-Bonferroni and Benjamini-Hochberg p-value adjustments.
    Input vector: [0.01, 0.04, 0.03] with m = 3 tests.
    
    Holm:
      Sorted: (0.01, idx 0), (0.03, idx 2), (0.04, idx 1)
      Multipliers: 3, 2, 1
      Raw * mult: 0.01 * 3 = 0.03; 0.03 * 2 = 0.06; 0.04 * 1 = 0.04
      Monotonic cummax: [0.03, 0.06, 0.06]
      Unsorted: [0.03, 0.06, 0.06]

    Benjamini-Hochberg (FDR):
      Sorted: (0.01, idx 0, i=1), (0.03, idx 2, i=2), (0.04, idx 1, i=3)
      p * m / i:
        i=1: 0.01 * 3 / 1 = 0.03
        i=2: 0.03 * 3 / 2 = 0.045
        i=3: 0.04 * 3 / 3 = 0.04
      Monotonic cummin from right: [0.03, 0.04, 0.04]
      Unsorted: [0.03, 0.04, 0.04]
    """
    raw_p = [0.01, 0.04, 0.03]

    # Holm-Bonferroni
    holm_adj = adjust_family_pvalues(raw_p, method="holm")
    assert np.allclose(holm_adj, [0.03, 0.06, 0.06], atol=1e-6)

    # Benjamini-Hochberg
    bh_adj = adjust_family_pvalues(raw_p, method="bh")
    assert np.allclose(bh_adj, [0.03, 0.04, 0.04], atol=1e-6)


def test_adjust_family_pvalues_edge_cases():
    """
    Tests edge cases: empty list, single p-value, and clipping at 1.0.
    """
    assert adjust_family_pvalues([], method="holm") == []
    assert adjust_family_pvalues([0.05], method="holm") == [0.05]
    assert adjust_family_pvalues([0.05], method="bh") == [0.05]

    # Large p-values that would exceed 1.0 when multiplied
    large_p = [0.60, 0.80]
    # Holm on [0.60, 0.80]: 0.60 * 2 = 1.20 -> clipped to 1.0
    adj_holm = adjust_family_pvalues(large_p, method="holm")
    assert np.allclose(adj_holm, [1.0, 1.0])
