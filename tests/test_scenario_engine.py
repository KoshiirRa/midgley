"""
Unit & Integration Tests for Seasonal Plausibility Gating Engine (tests/test_scenario_engine.py)
Issue #300: Seasonal & Climatological Plausibility Gating for Shock Scenarios with Weekly Review Feedback Loop.
"""

import os
import unittest
from datetime import date, datetime
from fastapi.testclient import TestClient

from src.scenario_engine import (
    PlausibilityStatus,
    SCENARIO_CLIMATOLOGY_REGISTRY,
    evaluate_scenario_plausibility,
    synthesize_prospective_forward_scenarios,
    get_all_scenarios_with_plausibility,
    _is_date_in_window,
    _days_until_window
)
from src.api_server import app, SCENARIOS_CATALOG


class TestScenarioEngine(unittest.TestCase):

    def setUp(self):
        os.environ["TESTING"] = "1"
        self.client = TestClient(app)

    def test_climatological_date_windows(self):
        # 1. Hurricane Season (Jun 01 - Nov 30, Peak Aug 15 - Oct 15)
        res_sep = evaluate_scenario_plausibility("port_st_lucie_hurricane", target_date=date(2026, 9, 15), live_telemetry=False)
        self.assertEqual(res_sep["plausibility_status"], PlausibilityStatus.SEASONALLY_PLAUSIBLE.value)
        self.assertTrue(res_sep["is_in_season"])
        self.assertTrue(res_sep["is_in_peak"])
        self.assertGreaterEqual(res_sep["plausibility_score"], 0.85)
        self.assertIsNone(res_sep["warning_message"])

        res_jan = evaluate_scenario_plausibility("port_st_lucie_hurricane", target_date=date(2026, 1, 15), live_telemetry=False)
        self.assertEqual(res_jan["plausibility_status"], PlausibilityStatus.SEASONALLY_DORMANT.value)
        self.assertFalse(res_jan["is_in_season"])
        self.assertFalse(res_jan["is_in_peak"])
        self.assertEqual(res_jan["plausibility_score"], 0.10)
        self.assertIsNotNone(res_jan["warning_message"])
        self.assertIn("counterfactual", res_jan["warning_message"].lower())

        # 2. Polar Vortex Freeze (Dec 01 - Feb 28, Peak Jan 01 - Feb 15)
        res_freeze_jan = evaluate_scenario_plausibility("polar_vortex_freeze", target_date=date(2026, 1, 20), live_telemetry=False)
        self.assertEqual(res_freeze_jan["plausibility_status"], PlausibilityStatus.SEASONALLY_PLAUSIBLE.value)
        self.assertTrue(res_freeze_jan["is_in_season"])
        self.assertTrue(res_freeze_jan["is_in_peak"])

        res_freeze_jul = evaluate_scenario_plausibility("polar_vortex_freeze", target_date=date(2026, 7, 15), live_telemetry=False)
        self.assertEqual(res_freeze_jul["plausibility_status"], PlausibilityStatus.SEASONALLY_DORMANT.value)
        self.assertFalse(res_freeze_jul["is_in_season"])
        self.assertEqual(res_freeze_jul["plausibility_score"], 0.10)

        # 3. Summer Refinery Thermal Cutback (Jun 15 - Sep 15, Peak Jul 01 - Aug 31)
        res_therm_jul = evaluate_scenario_plausibility("summer_refinery_thermal_cutback", target_date=date(2026, 7, 20), live_telemetry=False)
        self.assertEqual(res_therm_jul["plausibility_status"], PlausibilityStatus.SEASONALLY_PLAUSIBLE.value)
        self.assertTrue(res_therm_jul["is_in_season"])
        self.assertTrue(res_therm_jul["is_in_peak"])

        res_therm_dec = evaluate_scenario_plausibility("summer_refinery_thermal_cutback", target_date=date(2026, 12, 10), live_telemetry=False)
        self.assertEqual(res_therm_dec["plausibility_status"], PlausibilityStatus.SEASONALLY_DORMANT.value)
        self.assertFalse(res_therm_dec["is_in_season"])

        # 4. CARB CaRFG Transition (Feb 15 - May 01, Peak Mar 01 - Apr 15)
        res_carb_mar = evaluate_scenario_plausibility("carb_transition", target_date=date(2026, 3, 20), live_telemetry=False)
        self.assertEqual(res_carb_mar["plausibility_status"], PlausibilityStatus.SEASONALLY_PLAUSIBLE.value)
        self.assertTrue(res_carb_mar["is_in_season"])
        self.assertTrue(res_carb_mar["is_in_peak"])

        res_carb_nov = evaluate_scenario_plausibility("carb_transition", target_date=date(2026, 11, 5), live_telemetry=False)
        self.assertEqual(res_carb_nov["plausibility_status"], PlausibilityStatus.SEASONALLY_DORMANT.value)
        self.assertFalse(res_carb_nov["is_in_season"])

        # 5. Carquinez Atmospheric River (Nov 01 - Apr 01)
        res_ar_jan = evaluate_scenario_plausibility("carquinez_atmospheric_river", target_date=date(2026, 1, 10), live_telemetry=False)
        self.assertEqual(res_ar_jan["plausibility_status"], PlausibilityStatus.SEASONALLY_PLAUSIBLE.value)
        self.assertTrue(res_ar_jan["is_in_season"])

        res_ar_aug = evaluate_scenario_plausibility("carquinez_atmospheric_river", target_date=date(2026, 8, 10), live_telemetry=False)
        self.assertEqual(res_ar_aug["plausibility_status"], PlausibilityStatus.SEASONALLY_DORMANT.value)
        self.assertFalse(res_ar_aug["is_in_season"])

    def test_evergreen_scenarios(self):
        evergreen_ids = [
            "hormuz_blockade", "suez_rerouting", "colonial_outage",
            "marathon_outage", "chevron_hydrocracker", "hayward_quake",
            "weekend_opec_post", "weekend_tariff_declaration"
        ]
        for eid in evergreen_ids:
            res_summer = evaluate_scenario_plausibility(eid, target_date=date(2026, 7, 4), live_telemetry=False)
            self.assertEqual(res_summer["plausibility_status"], PlausibilityStatus.EVERGREEN.value)
            self.assertEqual(res_summer["plausibility_score"], 0.80)
            self.assertTrue(res_summer["is_in_season"])
            self.assertTrue(res_summer["is_evergreen"])

            res_winter = evaluate_scenario_plausibility(eid, target_date=date(2026, 1, 1), live_telemetry=False)
            self.assertEqual(res_winter["plausibility_status"], PlausibilityStatus.EVERGREEN.value)
            self.assertEqual(res_winter["plausibility_score"], 0.80)

    def test_prospective_forward_scenarios(self):
        # 1. CARB Spec switchover countdown (approx Feb 01 -> 14 days countdown to Feb 15)
        fwd_carb = synthesize_prospective_forward_scenarios(target_date=date(2026, 2, 1), live_telemetry=False)
        fwd_ids = [s["scenario_id"] for s in fwd_carb]
        self.assertIn("forward_carb_summer_rvp_switchover", fwd_ids)

        # 2. Polar Vortex arctic surge countdown (approx Nov 20 -> 11 days countdown to Dec 01)
        fwd_polar = synthesize_prospective_forward_scenarios(target_date=date(2026, 11, 20), live_telemetry=False)
        fwd_polar_ids = [s["scenario_id"] for s in fwd_polar]
        self.assertIn("forward_polar_vortex_arctic_surge", fwd_polar_ids)

        # 3. Peak Hurricane prospective synthesis (Sep 05)
        fwd_hurr = synthesize_prospective_forward_scenarios(target_date=date(2026, 9, 5), live_telemetry=False)
        fwd_hurr_ids = [s["scenario_id"] for s in fwd_hurr]
        self.assertIn("forward_atlantic_major_cyclone_landfall", fwd_hurr_ids)

        # 4. Hydrological low water trend (Sep 20)
        fwd_water = synthesize_prospective_forward_scenarios(target_date=date(2026, 9, 20), live_telemetry=False)
        fwd_water_ids = [s["scenario_id"] for s in fwd_water]
        self.assertIn("forward_mississippi_draft_restriction", fwd_water_ids)

    def test_get_all_scenarios_with_plausibility(self):
        # All scenarios
        all_res = get_all_scenarios_with_plausibility(target_date=date(2026, 9, 18), active_only=False)
        self.assertGreater(all_res["count"], 15)

        # Active only in September (should exclude polar_vortex_freeze, carb_transition, carquinez_atmospheric_river)
        active_res = get_all_scenarios_with_plausibility(target_date=date(2026, 9, 18), active_only=True)
        active_ids = [s["scenario_id"] for s in active_res["scenarios"]]
        self.assertNotIn("polar_vortex_freeze", active_ids)
        self.assertNotIn("carb_transition", active_ids)
        self.assertIn("port_st_lucie_hurricane", active_ids)
        self.assertIn("hormuz_blockade", active_ids)

        # Locale filter: Oakland
        oak_res = get_all_scenarios_with_plausibility(target_date=date(2026, 9, 18), locale="oakland")
        oak_ids = [s["scenario_id"] for s in oak_res["scenarios"]]
        self.assertIn("chevron_hydrocracker", oak_ids)
        self.assertIn("hayward_quake", oak_ids)
        self.assertIn("pge_psps_shutoff", oak_ids)

    def test_rest_api_scenarios_endpoint(self):
        # GET /api/v1/forecast/scenarios
        res = self.client.get("/api/v1/forecast/scenarios")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("scenarios", data)
        self.assertGreater(data["total_scenarios"], 0)

        # Filter active only
        res_act = self.client.get("/api/v1/forecast/scenarios?active_only=true&target_date=2026-09-18")
        self.assertEqual(res_act.status_code, 200)
        data_act = res_act.json()
        act_ids = [s["scenario_id"] for s in data_act["scenarios"]]
        self.assertNotIn("polar_vortex_freeze", act_ids)

    def test_rest_api_simulate_with_plausibility_warning(self):
        # Simulate in-season hurricane in September
        payload_in = {
            "scenario_id": "port_st_lucie_hurricane",
            "locale": "port_st_lucie",
            "target_date": "2026-09-15"
        }
        res_in = self.client.post("/api/v1/forecast/simulate", json=payload_in)
        self.assertEqual(res_in.status_code, 200)
        data_in = res_in.json()
        self.assertEqual(data_in["plausibility"]["status"], "SEASONALLY_PLAUSIBLE")
        self.assertTrue(data_in["plausibility"]["is_in_season"])
        self.assertIsNone(data_in["plausibility"]["warning_message"])

        # Simulate off-season hurricane in January
        payload_off = {
            "scenario_id": "port_st_lucie_hurricane",
            "locale": "port_st_lucie",
            "target_date": "2026-01-15"
        }
        res_off = self.client.post("/api/v1/forecast/simulate", json=payload_off)
        self.assertEqual(res_off.status_code, 200)
        data_off = res_off.json()
        self.assertEqual(data_off["plausibility"]["status"], "SEASONALLY_DORMANT")
        self.assertFalse(data_off["plausibility"]["is_in_season"])
        self.assertIsNotNone(data_off["plausibility"]["warning_message"])
        self.assertIn("counterfactual", data_off["plausibility"]["warning_message"].lower())


if __name__ == "__main__":
    unittest.main()
