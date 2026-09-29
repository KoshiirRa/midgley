"""
Unit Tests for NLP Semantic Deduplication, Rolling Shock Normalization & Local Projections (Issue #446).
"""

import unittest
import numpy as np
import pandas as pd
from src.event_analyzer import cluster_and_deduplicate_headlines, normalize_event_shocks
from src.feature_engineering import estimate_local_projections_impulse_responses


class TestNLPDeduplication(unittest.TestCase):
    def test_semantic_clustering_and_deduplication(self):
        headlines = [
            {"headline": "OPEC announces surprise 500k bpd crude output cut in Vienna meeting", "date": "2026-03-01"},
            {"headline": "OPEC announces surprise 500k bpd crude production cut in Vienna", "date": "2026-03-01"},  # Near duplicate
            {"headline": "OPEC delegates confirm 500k bpd supply reduction in Vienna", "date": "2026-03-01"},       # Wire rephrase
            {"headline": "Severe tornado damages Gulf Coast refinery in Port Arthur Texas", "date": "2026-03-02"},    # Completely different story
        ]

        deduped = cluster_and_deduplicate_headlines(headlines, similarity_threshold=0.50)
        # Should merge the 3 OPEC headlines into 1 cluster and keep the refinery tornado separate
        self.assertEqual(len(deduped), 2)
        opec_entry = deduped[0]
        self.assertEqual(opec_entry["cluster_story_count"], 3)
        self.assertEqual(len(opec_entry["duplicates"]), 2)

    def test_rolling_shock_normalization(self):
        dates = pd.date_range("2026-01-01", periods=100, freq="B")
        events_df = pd.DataFrame({
            "date": dates,
            "supply_disruption": np.random.exponential(0.5, 100),
            "geopolitical_risk": np.random.normal(0, 0.4, 100)
        })

        norm_df = normalize_event_shocks(events_df, window_days=30)
        self.assertIn("supply_disruption_log", norm_df.columns)
        self.assertIn("supply_disruption_zscore", norm_df.columns)
        self.assertIn("geopolitical_risk_log", norm_df.columns)
        self.assertIn("geopolitical_risk_zscore", norm_df.columns)

        # Log compression should ensure non-negative values stay strictly bounded
        self.assertTrue((norm_df["supply_disruption_log"] >= 0.0).all())

    def test_local_projections_impulse_responses(self):
        np.random.seed(42)
        n = 60
        dates = pd.date_range("2026-01-01", periods=n, freq="B")
        
        # Shock on day 5 that drives persistent upward price innovation
        shock = np.zeros(n)
        shock[5] = 1.0
        shock[20] = 1.0
        
        price = np.cumsum(0.05 * shock + np.random.normal(0, 0.01, n)) + 2.50
        
        events_df = pd.DataFrame({"supply_disruption": shock})
        price_series = pd.Series(price)

        irf_res = estimate_local_projections_impulse_responses(events_df, price_series, max_horizon=5)
        self.assertIn("supply_disruption", irf_res)
        self.assertEqual(len(irf_res["supply_disruption"]["horizons"]), 5)
        self.assertEqual(len(irf_res["supply_disruption"]["impulse_response_beta"]), 5)
        self.assertEqual(len(irf_res["supply_disruption"]["newey_west_hac_se"]), 5)


if __name__ == "__main__":
    unittest.main()
