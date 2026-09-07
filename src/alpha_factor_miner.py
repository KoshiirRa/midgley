"""
Autonomous LLM Alpha Factor Miner (RD-Agent Pattern)
Uses Gemini 2.5 Flash to formulate economic hypotheses, generate Qlib symbolic factor formulas,
evaluates Information Coefficient (IC, Rank IC, IC_IR), prunes collinear features, and persists top factors.
Inspired by Microsoft Research RD-Agent architecture.
"""

import os
import json
import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple, Optional
from scipy.stats import spearmanr, pearsonr

from src.qlib_symbolic_engine import QlibSymbolicEngine

logger = logging.getLogger(__name__)

# Seed Factor Hypotheses for Offline / Fallback Mining
DEFAULT_SEED_FACTORS = [
    {
        "name": "ovx_crude_volatility_spread",
        "hypothesis": "High crude oil options volatility relative to 20-day mean indicates impending wholesale price breaks.",
        "expression": "ZScore(cboe_ovx, 20)",
        "category": "volatility_momentum"
    },
    {
        "name": "crack_margin_momentum_divergence",
        "hypothesis": "Accelerating 3-2-1 refining crack margin momentum signals supply tightness ahead of RBOB price adjustments.",
        "expression": "Delta(crack_spread_321, 5)",
        "category": "refining_margin"
    },
    {
        "name": "wti_rbob_rolling_correlation_break",
        "hypothesis": "Divergence between WTI crude and RBOB futures correlation highlights refined product supply disruptions.",
        "expression": "Corr(gasoline_rbob, wti_crude, 20)",
        "category": "cross_asset"
    },
    {
        "name": "rig_count_lagged_production_drag",
        "hypothesis": "Multi-week decline in active Baker Hughes drilling rigs exerts upward price pressure on 5-day horizon.",
        "expression": "Roc(baker_hughes_rigs, 14)",
        "category": "physical_supply"
    },
    {
        "name": "geopolitical_shock_volatility_product",
        "hypothesis": "Multiplication of qualitative geopolitical risk score by OVX crude volatility isolates high-impact crisis spikes.",
        "expression": "Mul(geopolitical_risk, cboe_ovx)",
        "category": "qualitative_macro"
    }
]


def calculate_information_coefficient(factor_series: pd.Series, target_returns: pd.Series, rolling_window: int = 20) -> Dict[str, float]:
    """
    Computes Information Coefficient (IC), Rank IC (Spearman), and IC Information Ratio (IC_IR).
    Target returns are aligned point-in-time.
    """
    valid_mask = ~(factor_series.isna() | target_returns.isna() | np.isinf(factor_series) | np.isinf(target_returns))
    f_clean = factor_series[valid_mask]
    t_clean = target_returns[valid_mask]

    if len(f_clean) < 10:
        return {"ic": 0.0, "rank_ic": 0.0, "ic_ir": 0.0, "n_samples": len(f_clean)}

    # Pearson IC
    ic_val, _ = pearsonr(f_clean, t_clean)
    if np.isnan(ic_val):
        ic_val = 0.0

    # Spearman Rank IC
    rank_ic_val, _ = spearmanr(f_clean, t_clean)
    if np.isnan(rank_ic_val):
        rank_ic_val = 0.0

    # Rolling IC for IC_IR
    rolling_df = pd.DataFrame({"factor": f_clean, "target": t_clean})
    rolling_ics = rolling_df["factor"].rolling(window=rolling_window, min_periods=5).corr(rolling_df["target"]).dropna()

    if len(rolling_ics) > 5 and rolling_ics.std() > 1e-6:
        ic_ir = float(rolling_ics.mean() / rolling_ics.std())
    else:
        ic_ir = float(ic_val)

    return {
        "ic": round(float(ic_val), 4),
        "rank_ic": round(float(rank_ic_val), 4),
        "ic_ir": round(float(ic_ir), 4),
        "n_samples": int(len(f_clean))
    }


def prune_redundant_factors(
    candidate_df: pd.DataFrame,
    existing_df: pd.DataFrame = None,
    max_correlation: float = 0.70
) -> List[str]:
    """
    Prunes candidate factor columns that exhibit correlation > max_correlation with existing features
    or previously selected candidate factors.
    """
    selected_cols = []
    
    # Combined feature matrix for correlation audit
    ref_df = existing_df.copy() if existing_df is not None else pd.DataFrame(index=candidate_df.index)

    for col in candidate_df.columns:
        cand_s = candidate_df[col].fillna(0.0)
        if cand_s.std() < 1e-6:
            # Drop zero variance factors
            continue

        is_redundant = False
        # Check against existing features
        if not ref_df.empty:
            for ref_col in ref_df.columns:
                ref_s = ref_df[ref_col].fillna(0.0)
                if ref_s.std() >= 1e-6:
                    corr = abs(cand_s.corr(ref_s))
                    if not np.isnan(corr) and corr > max_correlation:
                        is_redundant = True
                        break

        if not is_redundant:
            selected_cols.append(col)
            ref_df[col] = cand_s

    return selected_cols


class AlphaFactorMiner:
    """
    RD-Agent Autonomous Alpha Factor Miner.
    Generates, evaluates, and manages quantitative factors using LLM hypotheses and Qlib symbolic expressions.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.symbolic_engine = QlibSymbolicEngine()

    def generate_llm_hypotheses(self, available_columns: List[str], count: int = 5) -> List[Dict[str, str]]:
        """
        Uses Gemini 2.5 Flash to formulate economic hypotheses and Qlib symbolic expressions.
        """
        if not self.api_key:
            logger.info("GEMINI_API_KEY absent. Using RD-Agent default seed factors.")
            return DEFAULT_SEED_FACTORS[:count]

        try:
            text_out = None
            try:
                from google import genai
                client = genai.Client(api_key=self.api_key)
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config={"temperature": 0.2, "response_mime_type": "application/json"}
                )
                text_out = response.text.strip()
            except Exception:
                import google.generativeai as genai_legacy
                genai_legacy.configure(api_key=self.api_key)
                model = genai_legacy.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(prompt)
                text_out = response.text.strip()
                if "```json" in text_out:
                    text_out = text_out.split("```json")[1].split("```")[0].strip()
                elif "```" in text_out:
                    text_out = text_out.split("```")[1].split("```")[0].strip()

            if text_out:
                parsed = json.loads(text_out)
                if isinstance(parsed, list) and len(parsed) > 0:
                    logger.info(f"Successfully generated {len(parsed)} factor hypotheses via Gemini.")
                    return parsed
        except Exception as e:
            logger.warning(f"LLM factor hypothesis generation failed ({e}). Falling back to seed factors.")

        return DEFAULT_SEED_FACTORS[:count]

    def mine_alpha_factors(
        self,
        df: pd.DataFrame,
        target_col: str = "gasoline_rbob",
        forecast_horizon: int = 5,
        min_abs_ic: float = 0.03,
        max_correlation: float = 0.70,
        output_file: str = "data/alpha_factors.json"
    ) -> List[Dict[str, Any]]:
        """
        Runs complete RD-Agent factor discovery loop:
        1. Formulates hypotheses & symbolic expressions.
        2. Evaluates symbolic expressions over historical DataFrame.
        3. Computes IC, Rank IC, and IC_IR against forward returns.
        4. Prunes redundant factors.
        5. Persists high-performing factors.
        """
        logger.info(f"Initiating Alpha Factor Mining on {len(df)} rows for target '{target_col}' ({forecast_horizon}d horizon)...")

        # Compute point-in-time target forward return for offline IC evaluation ONLY
        # Forward return: (P_{t+h} - P_t) / P_t
        target_series = df[target_col] if target_col in df.columns else df.iloc[:, 0]
        forward_returns = (target_series.shift(-forecast_horizon) - target_series) / (target_series.abs() + 1e-8)

        # Obtain candidates
        avail_cols = [c for c in df.columns if c not in ["date", "event_timestamp"]]
        candidates = self.generate_llm_hypotheses(avail_cols, count=6)

        evaluated_factors = []
        candidate_series_dict = {}

        for cand in candidates:
            expr = cand.get("expression", "")
            name = cand.get("name", "unnamed_factor")

            try:
                s = self.symbolic_engine.evaluate_expression(expr, df)
                ic_metrics = calculate_information_coefficient(s, forward_returns, rolling_window=20)

                factor_record = {
                    "name": name,
                    "expression": expr,
                    "hypothesis": cand.get("hypothesis", ""),
                    "category": cand.get("category", "general"),
                    "ic": ic_metrics["ic"],
                    "rank_ic": ic_metrics["rank_ic"],
                    "ic_ir": ic_metrics["ic_ir"],
                    "n_samples": ic_metrics["n_samples"]
                }

                if abs(factor_record["ic"]) >= min_abs_ic:
                    candidate_series_dict[name] = s
                    evaluated_factors.append(factor_record)
                    logger.info(f"Accepted candidate '{name}' (IC={factor_record['ic']}, RankIC={factor_record['rank_ic']})")
                else:
                    logger.info(f"Rejected candidate '{name}' due to low IC ({factor_record['ic']} < {min_abs_ic})")
            except Exception as e:
                logger.warning(f"Error evaluating candidate '{name}' ({expr}): {e}")

        # Prune redundant candidate factors
        if candidate_series_dict:
            cand_df = pd.DataFrame(candidate_series_dict, index=df.index)
            base_df = df[avail_cols].select_dtypes(include=[np.number])
            pruned_names = prune_redundant_factors(cand_df, base_df, max_correlation=max_correlation)

            final_factors = [f for f in evaluated_factors if f["name"] in pruned_names]
        else:
            final_factors = []

        # Sort by absolute IC descending
        final_factors.sort(key=lambda x: abs(x["ic"]), reverse=True)

        # Persist factors to JSON
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w") as f:
            json.dump({
                "mined_at": pd.Timestamp.now().isoformat(),
                "target_col": target_col,
                "forecast_horizon": forecast_horizon,
                "factors": final_factors
            }, f, indent=2)

        logger.info(f"Alpha Factor Mining complete. Persisted {len(final_factors)} factors to {output_file}.")
        return final_factors
