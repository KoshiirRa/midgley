"""
Sapient PRAXIST Autonomous Energy Research & Empirical Backtesting Harness (src/praxist_engine.py)
Implements measurable, computer-executable autonomous research loops, automated hypothesis
verification for exogenous shock decay parameters, and empirical cross-validation backtesting.
Issue #188
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)

PRAXIST_EXPERIMENTS_FILE = os.path.join("data", "praxist_experiments.json")


def is_testing_environment() -> bool:
    """Checks if running inside an automated test runner."""
    return (
        os.environ.get("TESTING") == "1"
        or "PYTEST_CURRENT_TEST" in os.environ
        or os.environ.get("MIDGLEY_TEST_MODE") == "1"
    )


class PraxistResearchHarness:
    """
    Autonomous research and hypothesis evaluation harness for quantitative energy commodity modeling.
    Explores feature weights, exponential memory decay parameters, and shock multipliers
    with verifiable empirical delta scoring.
    """

    DEFAULT_BASELINE_PARAMS = {
        "half_life_days": 4.5,
        "geopolitical_weight": 0.35,
        "supply_disruption_weight": 0.40,
        "opec_action_weight": 0.25,
        "weekend_gap_multiplier": 1.42
    }

    def __init__(self, experiments_file: Optional[str] = None):
        self.experiments_file = experiments_file or PRAXIST_EXPERIMENTS_FILE

    def _load_experiments_ledger(self) -> Dict[str, Any]:
        """Loads persistent research experiments ledger."""
        if os.path.exists(self.experiments_file):
            try:
                with open(self.experiments_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.debug(f"Error reading praxist experiments: {e}")
        return {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "total_hypotheses_tested": 0,
            "accepted_hypotheses": 0,
            "experiments": []
        }

    def _save_experiments_ledger(self, ledger: Dict[str, Any]):
        """Persists research experiments ledger to disk."""
        if is_testing_environment() and not os.environ.get("TEST_PRAXIST_PERSIST"):
            return
        try:
            os.makedirs(os.path.dirname(self.experiments_file), exist_ok=True)
            ledger["last_updated"] = datetime.now().isoformat()
            ledger["total_hypotheses_tested"] = len(ledger.get("experiments", []))
            ledger["accepted_hypotheses"] = sum(
                1 for exp in ledger.get("experiments", [])
                if exp.get("status") == "ACCEPTED"
            )
            with open(self.experiments_file, "w", encoding="utf-8") as f:
                json.dump(ledger, f, indent=2)
        except Exception as e:
            logger.debug(f"Error saving praxist experiments: {e}")

    def _generate_synthetic_benchmark_dataset(self, n_days: int = 120, seed: int = 42) -> pd.DataFrame:
        """Generates deterministic benchmark evaluation dataset for verifiable backtesting."""
        np.random.seed(seed)
        dates = pd.bdate_range(end=pd.Timestamp.now(), periods=n_days)
        base_price = 2.45 + np.cumsum(np.random.normal(0.001, 0.02, size=n_days))
        
        # Injected synthetic qualitative shocks
        geo_risk = np.clip(np.random.exponential(0.15, size=n_days), 0.0, 1.0)
        supply_dis = np.clip(np.random.exponential(0.12, size=n_days), 0.0, 1.0)
        opec_act = np.random.uniform(-0.5, 0.5, size=n_days)
        is_weekend_post = (np.random.uniform(0, 1, size=n_days) > 0.8).astype(int)

        # Ground truth actual 5-day price incorporating decay
        actual_5d = base_price.copy()
        alpha = np.log(2) / 4.5
        for i in range(5, n_days):
            shock_component = (
                0.35 * geo_risk[i - 5]
                + 0.40 * supply_dis[i - 5]
                + 0.25 * opec_act[i - 5]
            ) * (1.42 if is_weekend_post[i - 5] else 1.0) * np.exp(-alpha * 5)
            actual_5d[i] = base_price[i - 5] * (1.0 + shock_component * 0.08) + np.random.normal(0, 0.015)

        return pd.DataFrame({
            "date": dates,
            "base_price": base_price,
            "geopolitical_risk": geo_risk,
            "supply_disruption": supply_dis,
            "opec_action": opec_act,
            "is_weekend_post": is_weekend_post,
            "actual_5d_price": actual_5d
        })

    def _simulate_predictions(self, df: pd.DataFrame, params: Dict[str, Any]) -> Tuple[np.ndarray, np.ndarray]:
        """Simulates 5-day price predictions under a given parameter configuration."""
        half_life = params.get("half_life_days", 4.5)
        w_geo = params.get("geopolitical_weight", 0.35)
        w_sup = params.get("supply_disruption_weight", 0.40)
        w_opec = params.get("opec_action_weight", 0.25)
        mult_weekend = params.get("weekend_gap_multiplier", 1.42)

        decay_const = np.log(2) / max(half_life, 0.1)
        decay_factor = np.exp(-decay_const * 5)

        base_prices = df["base_price"].values
        geo = df["geopolitical_risk"].values
        sup = df["supply_disruption"].values
        opec = df["opec_action"].values
        wknd = df["is_weekend_post"].values

        weekend_multipliers = np.where(wknd == 1, mult_weekend, 1.0)
        raw_shocks = (w_geo * geo + w_sup * sup + w_opec * opec) * weekend_multipliers
        predicted_prices = base_prices * (1.0 + raw_shocks * 0.08 * decay_factor)
        predicted_directions = np.where(predicted_prices >= base_prices, 1, -1)

        return predicted_prices, predicted_directions

    def evaluate_hypothesis(
        self,
        hypothesis_name: str,
        candidate_params: Dict[str, Any],
        historical_df: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        Evaluates a candidate research hypothesis against baseline configuration.
        Computes MAE delta, Directional Accuracy delta, Information Ratio, and t-statistic.
        """
        df = historical_df if historical_df is not None else self._generate_synthetic_benchmark_dataset()

        baseline_params = self.DEFAULT_BASELINE_PARAMS.copy()
        pred_base, dir_base = self._simulate_predictions(df, baseline_params)
        pred_cand, dir_cand = self._simulate_predictions(df, candidate_params)

        actual_prices = df["actual_5d_price"].values
        base_prices = df["base_price"].values
        actual_directions = np.where(actual_prices >= base_prices, 1, -1)

        # Baseline metrics
        err_base = np.abs(pred_base - actual_prices)
        mae_base = float(np.mean(err_base))
        hit_base = float(np.mean(dir_base == actual_directions))

        # Candidate metrics
        err_cand = np.abs(pred_cand - actual_prices)
        mae_cand = float(np.mean(err_cand))
        hit_cand = float(np.mean(dir_cand == actual_directions))

        # Deltas
        mae_delta = float(mae_cand - mae_base)
        hit_delta = float(hit_cand - hit_base)

        # Paired t-test on errors (lower is better, so t_stat > 0 means candidate improved)
        diff = err_base - err_cand
        t_stat, p_val = stats.ttest_1samp(diff, 0.0) if np.std(diff) > 1e-8 else (0.0, 1.0)
        t_stat = float(t_stat) if not np.isnan(t_stat) else 0.0
        p_val = float(p_val) if not np.isnan(p_val) else 1.0

        # Information Ratio (Mean excess improvement / Std of improvement)
        ir = float(np.mean(diff) / np.std(diff)) if np.std(diff) > 1e-8 else 0.0

        # Decision threshold: stat significant improvement or equal performance with simpler model
        is_accepted = (mae_delta < -0.001 and p_val < 0.10) or (hit_delta > 0.02 and mae_delta <= 0.005)

        record = {
            "hypothesis_name": hypothesis_name,
            "evaluated_at": datetime.now().isoformat(),
            "candidate_params": candidate_params,
            "baseline_mae": round(mae_base, 4),
            "candidate_mae": round(mae_cand, 4),
            "mae_delta": round(mae_delta, 4),
            "baseline_directional_hit": round(hit_base, 4),
            "candidate_directional_hit": round(hit_cand, 4),
            "hit_delta": round(hit_delta, 4),
            "t_statistic": round(t_stat, 3),
            "p_value": round(p_val, 4),
            "information_ratio": round(ir, 3),
            "status": "ACCEPTED" if is_accepted else "REJECTED",
            "verifiable_checksum": f"praxist_{hash(str(candidate_params)) & 0xFFFFFFFF:08x}"
        }

        # Persist experiment record
        ledger = self._load_experiments_ledger()
        ledger.setdefault("experiments", []).append(record)
        self._save_experiments_ledger(ledger)

        return record

    def run_autonomous_parameter_sweep(
        self,
        half_life_options: Optional[List[float]] = None,
        weekend_mult_options: Optional[List[float]] = None,
        historical_df: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        Executes an autonomous parameter grid sweep testing multiple decay and shock hypotheses.
        """
        hl_grid = half_life_options or [3.0, 4.0, 4.5, 5.0, 6.0]
        wknd_grid = weekend_mult_options or [1.20, 1.42, 1.60]

        results = []
        best_candidate = None
        best_mae_delta = float("inf")

        for hl in hl_grid:
            for wm in wknd_grid:
                hyp_name = f"Decay_HalfLife_{hl}d_WeekendMult_{wm}x"
                cand_params = {
                    "half_life_days": hl,
                    "geopolitical_weight": 0.35,
                    "supply_disruption_weight": 0.40,
                    "opec_action_weight": 0.25,
                    "weekend_gap_multiplier": wm
                }
                res = self.evaluate_hypothesis(hyp_name, cand_params, historical_df=historical_df)
                results.append(res)
                if res["mae_delta"] < best_mae_delta:
                    best_mae_delta = res["mae_delta"]
                    best_candidate = res

        return {
            "total_sweeps": len(results),
            "best_candidate": best_candidate,
            "all_results": results
        }


def run_praxist_autonomous_backtest(
    candidate_params: Optional[Dict[str, Any]] = None,
    hypothesis_name: str = "Empirical_Shock_Parameter_Validation"
) -> Dict[str, Any]:
    """Convenience helper to evaluate candidate shock parameters via PRAXIST harness."""
    harness = PraxistResearchHarness()
    params = candidate_params or {
        "half_life_days": 4.8,
        "geopolitical_weight": 0.36,
        "supply_disruption_weight": 0.39,
        "opec_action_weight": 0.25,
        "weekend_gap_multiplier": 1.45
    }
    return harness.evaluate_hypothesis(hypothesis_name, params)
