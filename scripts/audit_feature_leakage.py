#!/usr/bin/env python3
"""
CLI Tool: Quantitative Feature Leakage & Factor Decay Auditor (Issue #146)
Runs point-in-time leakage checks, multi-horizon Spearman Rank IC decay audits,
and Combinatorial Symmetric Cross-Validation (CSCV) Probability of Backtest Overfitting (PBO).

Usage:
    python scripts/audit_feature_leakage.py [--region Tulsa_OK] [--horizons 1,3,5,10,14,20] [--output data/feature_audit_report.json]
"""

import os
import sys
import argparse
import logging
import numpy as np
import pandas as pd

# Add repository root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.feature_auditor import FeatureAuditor
from src.feature_engineering import create_feature_matrix
from src.data_ingestion import fetch_market_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def build_audit_dataset(region: str = "Tulsa_OK", days: int = 180) -> pd.DataFrame:
    """
    Constructs a unified feature matrix for auditing.
    """
    logger.info(f"Fetching market data and building feature matrix for {region} ({days} days)...")
    try:
        start_date = (pd.Timestamp.now() - pd.Timedelta(days=days)).strftime("%Y-%m-%d")
        market_df = fetch_market_data(start_date=start_date)
        feature_df = create_feature_matrix(market_df=market_df, region=region, forecast_horizon=5)
        return feature_df
    except Exception as e:
        logger.warning(f"Live data fetch failed ({e}), generating synthetic benchmark feature matrix...")
        # Fallback synthetic matrix for testing and isolated dev environments
        np.random.seed(42)
        n_samples = 120
        dates = pd.date_range(end=pd.Timestamp.now(), periods=n_samples, freq="D")
        base_price = 2.45 + np.cumsum(np.random.normal(0.001, 0.02, n_samples))
        
        df = pd.DataFrame({
            "date": dates,
            "gasoline_rbob": base_price,
            "target_rbob_5d": pd.Series(base_price).shift(-5),
            "wti_crude": 75.0 + np.random.normal(0, 2.0, n_samples),
            "brent_crude": 79.0 + np.random.normal(0, 2.0, n_samples),
            "cboe_ovx": 32.0 + np.random.normal(0, 3.0, n_samples),
            "geopolitical_risk_score": np.random.uniform(0.1, 0.9, n_samples),
            "weather_freeze_risk": np.random.uniform(0.0, 0.5, n_samples),
            "refinery_outage_shock": np.random.uniform(0.0, 0.8, n_samples),
            "tweet_sentiment_shock": np.random.uniform(-0.5, 0.5, n_samples),
            "eia_stocks_change_lagged": np.random.normal(0, 1.5, n_samples)
        })
        return df


def main():
    parser = argparse.ArgumentParser(description="Midgley Quantitative Feature Leakage & Factor Decay Auditor")
    parser.add_argument("--region", type=str, default="Tulsa_OK", help="Target regional metro profile")
    parser.add_argument("--horizons", type=str, default="1,3,5,10,14,20", help="Comma-separated forward horizons in days")
    parser.add_argument("--nominal-half-life", type=float, default=4.5, help="Nominal prior half-life in days")
    parser.add_argument("--output", type=str, default="data/feature_audit_report.json", help="Path to save JSON audit report")
    parser.add_argument("--export-md", type=str, default=None, help="Optional path to save Markdown report")
    args = parser.parse_args()

    horizons = [int(h.strip()) for h in args.horizons.split(",") if h.strip().isdigit()]

    feature_df = build_audit_dataset(region=args.region)
    logger.info(f"Loaded feature matrix: {feature_df.shape[0]} rows x {feature_df.shape[1]} columns")

    auditor = FeatureAuditor(nominal_decay_half_life=args.nominal_half_life)
    report = auditor.audit_feature_matrix(
        feature_df=feature_df,
        target_col="target_rbob_5d",
        price_col="gasoline_rbob",
        horizons=horizons
    )

    # Output to JSON
    report.to_json(args.output)
    logger.info(f"Audit report saved to: {args.output}")

    if args.export_md:
        with open(args.export_md, "w", encoding="utf-8") as f:
            f.write(report.to_markdown())
        logger.info(f"Markdown report saved to: {args.export_md}")

    # Print summary to console
    print("\n" + "=" * 80)
    print(report.to_markdown())
    print("=" * 80 + "\n")

    summary = report.to_dict().get("summary", {})
    if summary.get("fail_count", 0) > 0:
        logger.warning(f"Audit identified {summary.get('fail_count')} FAIL condition(s).")
        sys.exit(1)
    else:
        logger.info("Audit completed successfully with zero FAIL conditions.")
        sys.exit(0)


if __name__ == "__main__":
    main()
