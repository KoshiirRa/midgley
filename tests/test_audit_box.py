"""
Unit tests for Last Run Intelligence & Impact Audit Box Component (Issue #105).
Verifies:
1. parse_last_run_intelligence returns structured audit dictionary.
2. build_last_run_audit_card_html renders valid HTML card containing expected audit sections.
"""

import unittest
from src.dashboard_generator import parse_last_run_intelligence, build_last_run_audit_card_html

class TestAuditBox(unittest.TestCase):

    def test_parse_last_run_intelligence(self):
        """Verify parse_last_run_intelligence returns valid audit dictionary structure."""
        data = parse_last_run_intelligence()
        self.assertIsInstance(data, dict)
        self.assertIn("run_type", data)
        self.assertIn("scores", data)
        self.assertIn("decay_half_life", data)
        self.assertIn("region_deltas", data)

    def test_build_last_run_audit_card_html(self):
        """Verify build_last_run_audit_card_html returns valid HTML with quick links & audit metrics."""
        data = parse_last_run_intelligence()
        card_html = build_last_run_audit_card_html(data)
        
        self.assertIn("Last Run Intelligence", card_html)
        self.assertIn("QuantStats", card_html)
        self.assertIn("Savings", card_html)
        self.assertIn("Trigger Context", card_html)
        self.assertIn("Mathematical Impact", card_html)
        self.assertIn("Prediction Revisions Delta", card_html)

if __name__ == '__main__':
    unittest.main()
