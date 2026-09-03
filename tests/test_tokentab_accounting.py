"""
Unit tests for TokenTab Local LLM Token Accounting & Provider Cost Manager (Issue #189).
Verifies:
1. Provider cost calculation for Gemini 2.5 Flash, GPT-4o-mini, Claude-3.5-Haiku, Finlight, and Lexicon.
2. Ledger persistence and retrieval from data/token_usage_ledger.json.
3. Daily usage aggregation and multi-provider cost breakdowns.
4. Budget warning threshold evaluation (warning / critical alerts).
5. REST API endpoint GET /api/v1/system/token-costs integration.
"""

import os
import json
import shutil
import tempfile
import unittest
from fastapi.testclient import TestClient

from src.tokentab_accounting import TokenTabAccountingManager, PROVIDER_PRICING
from src.api_server import app


class TestTokenTabAccounting(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.ledger_path = os.path.join(self.temp_dir, "token_usage_ledger.json")
        self.manager = TokenTabAccountingManager(ledger_path=self.ledger_path)
        self.client = TestClient(app)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_calculate_cost(self):
        """Verify provider rate card cost calculation math."""
        # Gemini 2.5 Flash: $0.075 / 1M input, $0.300 / 1M output
        cost_gemini = self.manager.calculate_cost("gemini-2.5-flash", input_tokens=1_000_000, output_tokens=1_000_000)
        self.assertAlmostEqual(cost_gemini, 0.375, places=4)

        # GPT-4o-mini: $0.150 / 1M input, $0.600 / 1M output
        cost_gpt = self.manager.calculate_cost("gpt-4o-mini", input_tokens=1_000_000, output_tokens=1_000_000)
        self.assertAlmostEqual(cost_gpt, 0.750, places=4)

        # Claude-3.5-Haiku: $0.800 / 1M input, $4.000 / 1M output
        cost_claude = self.manager.calculate_cost("claude-3-5-haiku", input_tokens=1_000_000, output_tokens=1_000_000)
        self.assertAlmostEqual(cost_claude, 4.800, places=4)

        # Finlight & Lexicon ($0 cost)
        cost_finlight = self.manager.calculate_cost("finlight", input_tokens=5000, output_tokens=5000)
        self.assertEqual(cost_finlight, 0.0)
        cost_lexicon = self.manager.calculate_cost("offline_lexicon", input_tokens=0, output_tokens=0)
        self.assertEqual(cost_lexicon, 0.0)

    def test_record_usage_and_persistence(self):
        """Verify usage recording appends records to persistent JSON file."""
        rec1 = self.manager.record_usage(
            provider="gemini-2.5-flash",
            call_type="event_extraction",
            input_tokens=150,
            output_tokens=80,
            status="success"
        )
        self.assertEqual(rec1["provider"], "gemini-2.5-flash")
        self.assertEqual(rec1["total_tokens"], 230)
        self.assertGreater(rec1["cost_usd"], 0.0)

        rec2 = self.manager.record_usage(
            provider="offline_lexicon",
            call_type="event_extraction",
            input_tokens=0,
            output_tokens=0,
            status="fallback"
        )
        self.assertEqual(rec2["status"], "fallback")

        ledger = self.manager.get_ledger()
        self.assertEqual(len(ledger), 2)
        self.assertEqual(ledger[0]["provider"], "gemini-2.5-flash")
        self.assertEqual(ledger[1]["provider"], "offline_lexicon")

    def test_budget_warnings(self):
        """Verify budget warning evaluation for normal, warning, and critical spend."""
        # Low usage: Normal status
        self.manager.record_usage("gemini-2.5-flash", "event_extraction", 100, 50)
        warnings_ok = self.manager.check_budget_warnings(monthly_cost_limit_usd=10.0, daily_token_limit=100000)
        self.assertEqual(warnings_ok[0]["level"], "ok")

        # High usage: Exceed monthly cap
        for _ in range(50):
            self.manager.record_usage("claude-3-5-haiku", "test_run", 100_000, 50_000)
        warnings_crit = self.manager.check_budget_warnings(monthly_cost_limit_usd=1.0, daily_token_limit=100000)
        levels = [w["level"] for w in warnings_crit]
        self.assertIn("critical", levels)

    def test_get_accounting_summary(self):
        """Verify complete summary aggregation logic."""
        self.manager.record_usage("gemini-2.5-flash", "event_extraction", 1000, 500)
        self.manager.record_usage("gpt-4o-mini", "event_extraction", 2000, 1000)
        self.manager.record_usage("finlight", "finlight_feed", 0, 0)

        summary = self.manager.get_accounting_summary()
        self.assertEqual(summary["status"], "success")
        self.assertEqual(summary["summary"]["total_calls"], 3)
        self.assertEqual(summary["summary"]["total_input_tokens"], 3000)
        self.assertEqual(summary["summary"]["total_output_tokens"], 1500)
        self.assertEqual(summary["summary"]["total_tokens"], 4500)

        breakdown = summary["provider_breakdown"]
        self.assertIn("gemini-2.5-flash", breakdown)
        self.assertIn("gpt-4o-mini", breakdown)
        self.assertIn("finlight", breakdown)

    def test_api_endpoint_token_costs(self):
        """Verify GET /api/v1/system/token-costs endpoint response."""
        res = self.client.get("/api/v1/system/token-costs")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("summary", data)
        self.assertIn("provider_breakdown", data)
        self.assertIn("budget_warnings", data)


if __name__ == '__main__':
    unittest.main()
