"""
Unit Tests for Sapient PRAXIST Autonomous Energy Research Engine (tests/test_praxist_research.py)
Issue #188
"""

import os
import json
import tempfile
import unittest
import numpy as np
import pandas as pd

from unittest.mock import patch

from src.praxist_engine import (
    PraxistResearchHarness,
    run_praxist_autonomous_backtest,
    is_testing_environment,
)
from src.models import (
    evaluate_praxist_shock_hypothesis,
    run_praxist_research_sweep,
)
from src.weekly_issue_reporter import format_praxist_research_markdown_section


class TestPraxistResearchHarness(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.exp_file = os.path.join(self.temp_dir.name, "test_experiments.json")
        self.harness = PraxistResearchHarness(experiments_file=self.exp_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_synthetic_dataset_generation(self):
        df = self.harness._generate_synthetic_benchmark_dataset(n_days=60, seed=123)
        self.assertEqual(len(df), 60)
        self.assertIn("base_price", df.columns)
        self.assertIn("geopolitical_risk", df.columns)
        self.assertIn("supply_disruption", df.columns)
        self.assertIn("actual_5d_price", df.columns)

    def test_evaluate_hypothesis_baseline_equivalence(self):
        # When candidate params match baseline, mae_delta should be ~0.0
        res = self.harness.evaluate_hypothesis(
            hypothesis_name="Baseline_Equivalence_Test",
            candidate_params=self.harness.DEFAULT_BASELINE_PARAMS.copy()
        )
        self.assertIn("mae_delta", res)
        self.assertAlmostEqual(res["mae_delta"], 0.0, places=4)
        self.assertAlmostEqual(res["hit_delta"], 0.0, places=4)
        self.assertIn("verifiable_checksum", res)

    def test_evaluate_hypothesis_stat_scoring(self):
        candidate_params = {
            "half_life_days": 4.5,
            "geopolitical_weight": 0.35,
            "supply_disruption_weight": 0.40,
            "opec_action_weight": 0.25,
            "weekend_gap_multiplier": 1.42
        }
        res = self.harness.evaluate_hypothesis(
            hypothesis_name="Test_Hypothesis_A",
            candidate_params=candidate_params
        )
        self.assertIn("baseline_mae", res)
        self.assertIn("candidate_mae", res)
        self.assertIn("t_statistic", res)
        self.assertIn("p_value", res)
        self.assertIn("information_ratio", res)
        self.assertIn(res["status"], ["ACCEPTED", "REJECTED"])

    def test_experiments_ledger_persistence(self):
        with patch.dict(os.environ, {"TEST_PRAXIST_PERSIST": "1"}):
            self.harness.evaluate_hypothesis(
                hypothesis_name="Persisted_Hypothesis_1",
                candidate_params={"half_life_days": 5.0}
            )
            self.assertTrue(os.path.exists(self.exp_file))
            with open(self.exp_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data.get("total_hypotheses_tested"), 1)

    def test_autonomous_parameter_sweep(self):
        sweep_res = self.harness.run_autonomous_parameter_sweep(
            half_life_options=[3.5, 4.5],
            weekend_mult_options=[1.30, 1.42]
        )
        self.assertEqual(sweep_res["total_sweeps"], 4)
        self.assertIsNotNone(sweep_res["best_candidate"])
        self.assertEqual(len(sweep_res["all_results"]), 4)

    def test_models_integration_helpers(self):
        res = evaluate_praxist_shock_hypothesis("Candidate_Integration_Test")
        self.assertIn("mae_delta", res)
        self.assertIn("verifiable_checksum", res)

        sweep = run_praxist_research_sweep(half_life_options=[4.0, 5.0], weekend_mult_options=[1.42])
        self.assertEqual(sweep["total_sweeps"], 2)

    def test_format_praxist_research_markdown_section(self):
        md = format_praxist_research_markdown_section()
        self.assertIn("### 🔬 Sapient PRAXIST Autonomous Hypothesis & Shock Parameter Audit", md)
        self.assertIn("Rolling MAE", md)
        self.assertIn("Directional Accuracy", md)
        self.assertIn("Sapient PRAXIST", md)


if __name__ == "__main__":
    unittest.main()
