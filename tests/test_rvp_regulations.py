import unittest
import os
import tempfile
import pandas as pd
from datetime import datetime
from src.rvp_regulations import RVPRegulatoryEngine


class TestRVPRegulations(unittest.TestCase):
    def setUp(self):
        self.engine = RVPRegulatoryEngine()

    def test_zero_cost_metadata(self):
        self.assertTrue(self.engine.is_free_alternative)
        self.assertEqual(self.engine.cost_per_query, 0.0)

    def test_regional_rvp_limits_and_jurisdictions(self):
        # National baseline
        nat_spec = self.engine.get_regional_rvp_spec("National", "2026-07-04")
        self.assertEqual(nat_spec["rvp_summer_limit_psi"], 9.0)
        self.assertEqual(nat_spec["rvp_max_allowable_psi"], 9.0)
        self.assertTrue(nat_spec["rvp_is_summer_active"])

        # Tulsa OK (EPA Non-Attainment 7.8 psi)
        tulsa_spec = self.engine.get_regional_rvp_spec("Tulsa_OK", "2026-07-04")
        self.assertEqual(tulsa_spec["rvp_summer_limit_psi"], 7.8)
        self.assertEqual(tulsa_spec["rvp_max_allowable_psi"], 7.8)
        self.assertTrue(tulsa_spec["rvp_is_summer_active"])

        # Newark NJ (RFG 7.4 psi)
        newark_spec = self.engine.get_regional_rvp_spec("Newark_NJ", "2026-07-04")
        self.assertEqual(newark_spec["rvp_summer_limit_psi"], 7.4)
        self.assertEqual(newark_spec["rvp_max_allowable_psi"], 7.4)
        self.assertTrue(newark_spec["is_rfg"])

        # Oakland CA (CARB 6.99 psi)
        oak_spec = self.engine.get_regional_rvp_spec("Oakland_CA", "2026-07-04")
        self.assertEqual(oak_spec["rvp_summer_limit_psi"], 6.99)
        self.assertEqual(oak_spec["rvp_max_allowable_psi"], 6.99)
        self.assertTrue(oak_spec["is_carb"])

    def test_seasonal_transition_dates(self):
        # Winter season (January 15)
        winter_spec = self.engine.get_regional_rvp_spec("Tulsa_OK", "2026-01-15")
        self.assertFalse(winter_spec["rvp_is_summer_active"])
        self.assertFalse(winter_spec["rvp_is_spring_ramp"])
        self.assertEqual(winter_spec["rvp_max_allowable_psi"], 13.5)
        self.assertEqual(winter_spec["rvp_seasonal_compliance_premium"], 0.0)
        self.assertGreater(winter_spec["rvp_summer_transition_days_remaining"], 100)

        # Spring ramp-up (April 15)
        spring_spec = self.engine.get_regional_rvp_spec("Tulsa_OK", "2026-04-15")
        self.assertFalse(spring_spec["rvp_is_summer_active"])
        self.assertTrue(spring_spec["rvp_is_spring_ramp"])
        self.assertGreater(spring_spec["rvp_spring_ramp_factor"], 0.0)
        self.assertGreater(spring_spec["rvp_seasonal_compliance_premium"], 0.0)
        self.assertEqual(spring_spec["rvp_summer_transition_days_remaining"], 47)
        self.assertEqual(spring_spec["rvp_terminal_deadline_days_remaining"], 16)

        # Terminal delivery window (May 15)
        terminal_spec = self.engine.get_regional_rvp_spec("Tulsa_OK", "2026-05-15")
        self.assertFalse(terminal_spec["rvp_is_summer_active"])
        self.assertTrue(terminal_spec["rvp_is_terminal_transition"])
        self.assertEqual(terminal_spec["rvp_terminal_deadline_days_remaining"], 0)
        self.assertEqual(terminal_spec["rvp_summer_transition_days_remaining"], 17)

    def test_compute_rvp_feature_dataframe(self):
        dates = pd.date_range("2026-04-01", periods=10, freq="D")
        df = self.engine.compute_rvp_feature_dataframe(dates, region="Oakland_CA")
        self.assertEqual(len(df), 10)
        self.assertIn("rvp_max_allowable_psi", df.columns)
        self.assertIn("rvp_summer_transition_days_remaining", df.columns)
        self.assertIn("rvp_seasonal_compliance_premium", df.columns)

    def test_emergency_waiver(self):
        temp_dir = tempfile.TemporaryDirectory()
        temp_rules_file = os.path.join(temp_dir.name, "test_rules.json")
        engine = RVPRegulatoryEngine(rules_path=temp_rules_file)

        engine.apply_emergency_waiver(
            region="Tulsa_OK",
            temporary_psi=9.0,
            start_date="2026-07-01",
            end_date="2026-07-15",
            reason="Hurricane Supply Emergency Waiver"
        )

        waiver_spec = engine.get_regional_rvp_spec("Tulsa_OK", "2026-07-04")
        self.assertTrue(waiver_spec["emergency_waiver_active"])
        self.assertEqual(waiver_spec["rvp_max_allowable_psi"], 9.0)
        self.assertEqual(waiver_spec["emergency_waiver_reason"], "Hurricane Supply Emergency Waiver")
        temp_dir.cleanup()


if __name__ == "__main__":
    unittest.main()
