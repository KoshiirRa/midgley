"""
Unit tests for QuantStats Performance Tear Sheets & Risk Metrics (Issue #120).
Verifies:
1. compute_quantstats_risk_metrics calculates Sharpe Ratio, Sortino Ratio, Max Drawdown, Calmar Ratio, Tail Ratio, Win Rate, and Profit Factor.
2. generate_quantstats_tearsheet_page creates docs/quantstats_tearsheet.html and docs/quantstats/index.html.
"""

import os
import unittest
import numpy as np
from src.models import compute_quantstats_risk_metrics
from src.dashboard_generator import generate_quantstats_tearsheet_page

class TestQuantStatsTearsheet(unittest.TestCase):

    def test_compute_quantstats_risk_metrics(self):
        """Verify compute_quantstats_risk_metrics calculates expected metric keys."""
        np.random.seed(42)
        returns = np.random.normal(0.002, 0.015, 50)
        metrics = compute_quantstats_risk_metrics(returns)
        
        self.assertIn("sharpe", metrics)
        self.assertIn("sortino", metrics)
        self.assertIn("max_drawdown_pct", metrics)
        self.assertIn("calmar", metrics)
        self.assertIn("tail_ratio", metrics)
        self.assertIn("win_rate_pct", metrics)
        self.assertIn("profit_factor", metrics)
        
        self.assertGreater(metrics["win_rate_pct"], 0.0)
        self.assertLessEqual(metrics["win_rate_pct"], 100.0)

    def test_generate_quantstats_tearsheet_page_files_exist(self):
        """Verify generate_quantstats_tearsheet_page creates target HTML files."""
        generate_quantstats_tearsheet_page(output_dir="docs")
        
        path1 = os.path.join("docs", "quantstats_tearsheet.html")
        path2 = os.path.join("docs", "quantstats", "index.html")
        
        self.assertTrue(os.path.exists(path1))
        self.assertTrue(os.path.exists(path2))
        
        with open(path1, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("QuantStats Performance Tear Sheet", content)
            self.assertIn("Sharpe Ratio", content)

if __name__ == '__main__':
    unittest.main()
