"""
Unit & Integration Tests for Intraday Event Monitor & Webhook Ingestion (tests/test_intraday_event_monitor.py)
"""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.intraday_event_monitor import IntradayEventMonitor, TRIGGER_KEYWORDS
from src.event_analyzer import extract_event_features_llm


import os

class TestIntradayEventMonitor(unittest.TestCase):
    def setUp(self):
        os.environ["TESTING"] = "1"
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

    def test_resolve_target_locales(self):
        # Test Tulsa locale routing
        t_tulsa = self.monitor.resolve_target_locales("HF Sinclair West Tulsa Refinery Unit Trip Causes Flaring")
        self.assertEqual(t_tulsa, ["Tulsa"])

        # Test Newark locale routing
        t_newark = self.monitor.resolve_target_locales("Delaware City Refinery Outage Forces PADD 1B Fuel Rerouting")
        self.assertEqual(t_newark, ["Newark"])

        # Test Cincinnati locale routing
        t_cincy = self.monitor.resolve_target_locales("Catlettsburg KY Refinery Trip & Ohio River Lock Delays")
        self.assertEqual(t_cincy, ["Cincinnati"])

        # Test Greenville & Charlotte locale routing
        t_carolinas = self.monitor.resolve_target_locales("Colonial Pipeline Line 1 Intake Halt at Selma Terminal")
        self.assertEqual(t_carolinas, ["Charlotte", "Greenville"])

        # Test Oakland locale routing
        t_oakland = self.monitor.resolve_target_locales("Chevron Richmond Refinery Flaring Triggers CARB Compliance Warning")
        self.assertEqual(t_oakland, ["Oakland"])

        # Test Default National routing
        t_nat = self.monitor.resolve_target_locales("OPEC Announces Emergency Production Quota Cut")
        self.assertEqual(t_nat, ["National"])

    def test_expanded_trigger_keywords(self):
        # Technical trigger
        self.assertTrue(any(kw in "3-2-1 crack spread spikes to $35/bbl".lower() for kw in TRIGGER_KEYWORDS))
        # Policy trigger
        self.assertTrue(any(kw in "President Signs Executive Order for Energy Tariff".lower() for kw in TRIGGER_KEYWORDS))

    @patch("sys.argv", ["intraday_event_monitor", "--headline", "Emergency Tariff Announcement", "--source", "Cloudflare_Worker", "--url", "https://example.com/tariff"])
    @patch("src.intraday_event_monitor.IntradayEventMonitor.process_incoming_headline")
    def test_cli_headline_dispatch_processing(self, mock_process):
        from src.intraday_event_monitor import main
        mock_process.return_value = {"is_anomaly": True}
        res = main()
        mock_process.assert_called_once_with(
            headline="Emergency Tariff Announcement",
            source="Cloudflare_Worker",
            url="https://example.com/tariff",
            skip_dedup=False
        )
        self.assertTrue(res["is_anomaly"])

    @patch("sys.argv", ["intraday_event_monitor"])
    @patch("src.intraday_event_monitor.IntradayEventMonitor.run_polling_cycle")
    def test_cli_default_polling_cycle(self, mock_polling):
        from src.intraday_event_monitor import main
        mock_polling.return_value = {"status": "success", "anomalies_detected": 0}
        res = main()
        mock_polling.assert_called_once()
        self.assertEqual(res["status"], "success")


    def test_evaluate_headline_non_energy_outage_exclusion(self):
        headline = "Access Restored to Wikipedia in Russia After Overnight Outage"
        is_anomaly, scores = self.monitor.evaluate_headline_anomaly(headline)
        self.assertFalse(is_anomaly)

    @patch("src.intraday_event_monitor.IntradayEventMonitor.fetch_rss_headlines")
    def test_run_polling_cycle_batches_primary_anomaly(self, mock_fetch):
        mock_fetch.return_value = [
            {
                "headline": "Canada Announces Retaliatory Tariffs as Trade War Escalates",
                "published": "2026-08-27T10:00:00",
                "url": "https://news.google.com/articles/tariffs_test1",
                "source": "RSS_Feed"
            },
            {
                "headline": "Gulf Coast Refinery Outage Halts Fuel Shipments",
                "published": "2026-08-27T10:05:00",
                "url": "https://news.google.com/articles/tariffs_test2",
                "source": "RSS_Feed"
            }
        ]

        res = self.monitor.run_polling_cycle()
        # Should detect exactly 1 anomaly per cycle to avoid multiple sequential dashboard builds
        self.assertEqual(res["anomalies_detected"], 1)


if __name__ == "__main__":
    unittest.main()


