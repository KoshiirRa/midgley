"""
Unit & Integration Tests for MiroFish Multi-Agent Financial Simulation Engine (tests/test_scenario_simulator.py)
Issue #307: Multi-Agent Financial Simulation & Scenario Decision Graphs.
"""

import os
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.scenario_simulator import (
    is_multi_agent_sim_enabled,
    simulate_market_cohort,
    export_scenario_decision_graph_mermaid,
    _classify_scenario_category,
    _evaluate_tier3_deterministic_cohort,
    ENV_ENABLE_MULTI_AGENT_SIM
)
from src.dashboard_generator import get_multi_agent_sim_badge
from src.api_server import app, SCENARIOS_CATALOG, SimulateRequest


class TestScenarioSimulator(unittest.TestCase):

    def setUp(self):
        os.environ["TESTING"] = "1"
        self.client = TestClient(app)

    def test_feature_flag_evaluation(self):
        # Default behavior with env unset or 0
        if ENV_ENABLE_MULTI_AGENT_SIM in os.environ:
            del os.environ[ENV_ENABLE_MULTI_AGENT_SIM]
        self.assertFalse(is_multi_agent_sim_enabled())

        # Override precedence
        self.assertTrue(is_multi_agent_sim_enabled(override=True))
        self.assertFalse(is_multi_agent_sim_enabled(override=False))

        # Environment variable settings
        for val in ["1", "true", "True", "YES", "on"]:
            os.environ[ENV_ENABLE_MULTI_AGENT_SIM] = val
            self.assertTrue(is_multi_agent_sim_enabled())

        for val in ["0", "false", "False", "no", "off"]:
            os.environ[ENV_ENABLE_MULTI_AGENT_SIM] = val
            self.assertFalse(is_multi_agent_sim_enabled())

        # Clean up
        if ENV_ENABLE_MULTI_AGENT_SIM in os.environ:
            del os.environ[ENV_ENABLE_MULTI_AGENT_SIM]

    def test_scenario_classification(self):
        self.assertEqual(_classify_scenario_category("greenville_hurricane"), "meteorological")
        self.assertEqual(_classify_scenario_category("polar_vortex_freeze"), "meteorological")
        self.assertEqual(_classify_scenario_category("summer_refinery_thermal_cutback"), "hydrological")
        self.assertEqual(_classify_scenario_category("colonial_outage"), "pipeline_disruption")
        self.assertEqual(_classify_scenario_category("marathon_outage"), "refinery_outage")
        self.assertEqual(_classify_scenario_category("carb_transition"), "regulatory_spec")
        self.assertEqual(_classify_scenario_category("hormuz_blockade"), "geopolitical")

    def test_tier3_deterministic_cohort_simulation(self):
        res = simulate_market_cohort(
            scenario_id="hormuz_blockade",
            locale="national",
            base_price=3.200,
            base_shock_pct=0.05,
            use_llm=False
        )

        self.assertEqual(res["status"], "success")
        self.assertEqual(res["provider_used"], "tier_3_deterministic_matrix")
        self.assertTrue(res["is_multi_agent_mode"])
        self.assertIn("personas", res)
        self.assertIn("consensus", res)
        self.assertIn("decision_graph_mermaid", res)

        personas = res["personas"]
        self.assertEqual(len(personas), 4)
        for p_name in ["Agent_Refiner", "Agent_Logistics", "Agent_Consumer", "Agent_Macro"]:
            self.assertIn(p_name, personas)
            self.assertIn("stance", personas[p_name])
            self.assertIn("price_shock_pct", personas[p_name])
            self.assertIn("confidence", personas[p_name])
            self.assertGreater(personas[p_name]["confidence"], 0.5)
            self.assertGreater(len(personas[p_name]["key_catalysts"]), 0)

        # Cross-commodity and divergence
        consensus = res["consensus"]
        self.assertGreater(consensus["price_shock_pct"], 0.0)
        self.assertGreater(consensus["divergence_index"], 0.0)
        self.assertGreater(consensus["rbob_shock_dollars_per_gal"], 0.0)
        self.assertGreater(consensus["ho_distillate_shock_dollars_per_gal"], 0.0)
        self.assertGreater(consensus["regional_freight_basis_delta_cents"], 0.0)

    def test_mermaid_decision_graph_syntax(self):
        res = simulate_market_cohort(
            scenario_id="tulsa_tornado",
            locale="tulsa",
            base_price=3.100,
            base_shock_pct=0.045,
            use_llm=False
        )

        mermaid_code = export_scenario_decision_graph_mermaid(res)
        self.assertTrue(mermaid_code.startswith("flowchart TD"))
        self.assertIn("Agent_Refiner", mermaid_code)
        self.assertIn("Agent_Logistics", mermaid_code)
        self.assertIn("Agent_Consumer", mermaid_code)
        self.assertIn("Agent_Macro", mermaid_code)
        self.assertIn("Equilibrium Consensus", mermaid_code)
        self.assertIn("RBOB Delta", mermaid_code)
        self.assertIn("ULSD/HO Delta", mermaid_code)

    def test_dashboard_generator_status_badge(self):
        # Badge when flag is OFF
        os.environ[ENV_ENABLE_MULTI_AGENT_SIM] = "0"
        badge_off = get_multi_agent_sim_badge()
        self.assertIn("Multi-Agent Cohort: OFF", badge_off)
        self.assertIn("bg-slate-500/20", badge_off)

        # Badge when flag is ON
        os.environ[ENV_ENABLE_MULTI_AGENT_SIM] = "1"
        badge_on = get_multi_agent_sim_badge()
        self.assertIn("Multi-Agent Cohort: ON", badge_on)
        self.assertIn("bg-purple-500/20", badge_on)

        # Cleanup
        os.environ[ENV_ENABLE_MULTI_AGENT_SIM] = "0"

    def test_api_simulate_endpoint_toggle(self):
        # 1. Flag OFF by default: standard simulation response without cohort_simulation
        os.environ[ENV_ENABLE_MULTI_AGENT_SIM] = "0"
        resp_off = self.client.post("/api/v1/forecast/simulate", json={
            "scenario_id": "hormuz_blockade",
            "locale": "national"
        })
        self.assertEqual(resp_off.status_code, 200)
        data_off = resp_off.json()
        self.assertNotIn("cohort_simulation", data_off)
        self.assertIn("simulation", data_off)

        # 2. Request Override ON: returns enriched cohort_simulation payload
        resp_override = self.client.post("/api/v1/forecast/simulate", json={
            "scenario_id": "hormuz_blockade",
            "locale": "national",
            "enable_cohort_simulation": True
        })
        self.assertEqual(resp_override.status_code, 200)
        data_override = resp_override.json()
        self.assertIn("cohort_simulation", data_override)
        cohort = data_override["cohort_simulation"]
        self.assertEqual(len(cohort["personas"]), 4)
        self.assertIn("decision_graph_mermaid", cohort)
        self.assertIn("divergence_index", cohort["consensus"])

        # 3. Environment Variable ON: returns cohort_simulation automatically
        os.environ[ENV_ENABLE_MULTI_AGENT_SIM] = "1"
        resp_env_on = self.client.post("/api/v1/forecast/simulate", json={
            "scenario_id": "colonial_outage",
            "locale": "newark"
        })
        self.assertEqual(resp_env_on.status_code, 200)
        data_env_on = resp_env_on.json()
        self.assertIn("cohort_simulation", data_env_on)
        self.assertEqual(data_env_on["cohort_simulation"]["locale"], "Newark_DE")

        # Cleanup
        os.environ[ENV_ENABLE_MULTI_AGENT_SIM] = "0"


if __name__ == "__main__":
    unittest.main()
