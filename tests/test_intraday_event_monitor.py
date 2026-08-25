"""
Unit & Integration Tests for Intraday Event Monitor & Webhook Ingestion (tests/test_intraday_event_monitor.py)
"""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.intraday_event_monitor import IntradayEventMonitor, TRIGGER_KEYWORDS
from src.event_analyzer import extract_event_features_llm


class TestIntradayEventMonitor(unittest.TestCase):
    def setUp(self):
        self.monitor = IntradayEventMonitor(shock_threshold=0.40)

    def test_evaluate_headline_routine_news(self):
        headline = "US Crude Oil Inventories Rise 1.2 Million Barrels Last Week"
        is_anomaly, scores = self.monitor.evaluate_headline_anomaly(headline)
        self.assertFalse(is_anomaly)

    def test_evaluate_headline_tariff_anomaly(self):
        headline = "Canada Announces Retaliatory Tariffs as Trade War Escalates"
        is_anomaly, scores = self.monitor.evaluate_headline_anomaly(headline)
        self.assertTrue(is_anomaly)
        self.assertGreaterEqual(abs(scores["overall_price_pressure"]), 0.40)

    def test_process_incoming_headline_structure(self):
        headline = "Houthi Missile Strike Halts Tanker Traffic in Strait of Hormuz"
        res = self.monitor.process_incoming_headline(headline, source="Test_Suite")
        self.assertEqual(res["headline"], headline)
        self.assertEqual(res["source"], "Test_Suite")
        self.assertTrue(res["is_anomaly"])
        self.assertIn("overall_price_pressure", res["scores"])

    @patch("src.event_analyzer._try_openai_single")
    @patch("src.event_analyzer._try_anthropic_single")
    def test_multi_provider_failover(self, mock_anthropic, mock_openai):
        mock_openai.return_value = None
        mock_anthropic.return_value = None
        # Simulate missing Gemini API key to trigger failover
        with patch.dict("os.environ", {}, clear=True):
            headline = "Refinery Explosion Causes Massive Outage"
            scores = extract_event_features_llm(headline)
            # Should seamlessly fall back to rule-based lexicon without throwing errors
            self.assertIn("overall_price_pressure", scores)
            self.assertGreaterEqual(scores["supply_disruption"], 0.50)



if __name__ == "__main__":
    unittest.main()
