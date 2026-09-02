"""
Unit tests for Fill-Up Timing & Estimated Savings Advisor Page (Issue #91).
Verifies:
1. generate_savings_advisor_page outputs docs/savings.html and docs/savings/index.html.
2. Output HTML contains key UI components: Vehicle Tank Presets, Recommendation Badge, Trajectory Table, and Cross-Links.
"""

import os
import unittest
from src.dashboard_generator import generate_savings_advisor_page, SAVINGS_PATH, SAVINGS_SUB_PATH

class TestSavingsAdvisor(unittest.TestCase):

    def test_generate_savings_advisor_page_files_exist(self):
        """Verify generate_savings_advisor_page creates docs/savings.html and docs/savings/index.html."""
        generate_savings_advisor_page()
        self.assertTrue(os.path.exists(SAVINGS_PATH), f"File {SAVINGS_PATH} was not created.")
        self.assertTrue(os.path.exists(SAVINGS_SUB_PATH), f"File {SAVINGS_SUB_PATH} was not created.")

    def test_savings_advisor_html_content(self):
        """Verify HTML content includes calculator elements, presets, and integration links."""
        generate_savings_advisor_page()
        with open(SAVINGS_PATH, "r", encoding="utf-8") as f:
            html = f.read()
            
        self.assertIn("Fill-Up Timing &amp; Estimated Savings Advisor", html)
        self.assertIn("vehiclePreset", html)
        self.assertIn("tankCapacity", html)
        self.assertIn("fuelLevel", html)
        self.assertIn("trajectoryTableBody", html)
        self.assertIn("LubeLogger Predictive Fuel Sync", html)
        self.assertIn("Android Auto In-Dash Fuel Assistant", html)

if __name__ == '__main__':
    unittest.main()
