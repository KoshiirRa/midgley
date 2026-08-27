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

    @patch("src.intraday_event_monitor.feedparser")
    def test_rss_date_filtering_stale_articles(self, mock_feedparser):
        import time
        # Create mock entries: one fresh (now) and one old (3 days ago)
        now_struct = time.gmtime()
        old_struct = time.gmtime(time.time() - 3 * 86400)

        mock_feed = MagicMock()
        mock_feed.entries = [
            {"title": "Fresh Refinery Outage", "published_parsed": now_struct, "link": "https://news.com/fresh"},
            {"title": "Old Refinery Explosion 2025", "published_parsed": old_struct, "link": "https://news.com/old"}
        ]
        mock_feedparser.parse.return_value = mock_feed

        headlines = self.monitor.fetch_rss_headlines(max_age_hours=24.0)
        titles = [h["headline"] for h in headlines]

        self.assertIn("Fresh Refinery Outage", titles)
        self.assertNotIn("Old Refinery Explosion 2025", titles)

    @patch("src.intraday_event_monitor.IntradayEventMonitor.fetch_rss_headlines")
    def test_run_polling_cycle_preserves_url(self, mock_fetch):
        mock_fetch.return_value = [{
            "headline": "Canada Announces Retaliatory Tariffs as Trade War Escalates",
            "published": "2026-08-27T10:00:00",
            "url": "https://news.google.com/articles/tariffs_test",
            "source": "RSS_Feed"
        }]

        with patch.object(self.monitor, "process_incoming_headline") as mock_process:
            mock_process.return_value = {"is_anomaly": True}
            self.monitor.run_polling_cycle()

            mock_process.assert_called_once_with(
                "Canada Announces Retaliatory Tariffs as Trade War Escalates",
                source="RSS_Feed",
                url="https://news.google.com/articles/tariffs_test"
            )


    @patch("src.intraday_event_monitor.IntradayEventMonitor.is_headline_already_processed")
    def test_headline_deduplication_24h(self, mock_is_processed):
        mock_is_processed.return_value = True
        res = self.monitor.process_incoming_headline("Major Pipeline Explosion", source="RSS_Feed", url="https://news.com/exp")
        self.assertFalse(res["is_anomaly"])
        self.assertTrue(res.get("duplicate"))


if __name__ == "__main__":
    unittest.main()

