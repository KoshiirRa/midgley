"""
Unit & Integration Tests for Intraday Event Monitor & Webhook Ingestion (tests/test_intraday_event_monitor.py)
"""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.intraday_event_monitor import IntradayEventMonitor, TRIGGER_KEYWORDS
from src.event_analyzer import extract_event_features_llm


import os
import json

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

    def test_evaluate_headline_edible_oil_suppression(self):
        """Verifies that agricultural and edible cooking oils (Issue #617) are suppressed as false positives."""
        rice_bran_headline = "Supreme Court Dismisses Appeal on Classification of Hydrogenated Rice Bran Oil Due to Retention of Essential Characteristics. Classified under Tariff Item 12 as Vegetable Non-Essential Oil"
        is_anomaly, scores = self.monitor.evaluate_headline_anomaly(rice_bran_headline)
        self.assertFalse(is_anomaly)
        self.assertEqual(scores.get("overall_price_pressure", 0.0), 0.0)

        palm_oil_headline = "Tariff values raised for edible oil and palm oil imports"
        is_anomaly, scores = self.monitor.evaluate_headline_anomaly(palm_oil_headline)
        self.assertFalse(is_anomaly)
        self.assertEqual(scores.get("overall_price_pressure", 0.0), 0.0)

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

    @patch("src.intraday_event_monitor.send_intraday_discord_notification")
    def test_process_incoming_headline_triggers_discord_notification(self, mock_discord):
        mock_discord.return_value = True
        headline = "Canada Announces Retaliatory Tariffs as Trade War Escalates"
        res = self.monitor.process_incoming_headline(headline, source="Test_Suite")
        self.assertTrue(res["is_anomaly"])
        mock_discord.assert_called_once()
        call_arg = mock_discord.call_args[0][0]
        self.assertEqual(call_arg["headline"], headline)
        self.assertTrue(res.get("discord_notified"))

    def test_normalize_headline_strips_publisher_suffixes(self):
        from src.intraday_event_monitor import normalize_headline
        h1 = "House Should Not Transfer More Tariff Authority to the Executive Branch - National Taxpayers Union"
        h2 = "House Should Not Transfer More Tariff Authority to the Executive Branch - NTU"
        h3 = "House Should Not Transfer More Tariff Authority to the Executive Branch | Reuters"
        h4 = "“House Should Not Transfer More Tariff Authority to the Executive Branch”"

        norm1 = normalize_headline(h1)
        norm2 = normalize_headline(h2)
        norm3 = normalize_headline(h3)
        norm4 = normalize_headline(h4)

        self.assertEqual(norm1, "house should not transfer more tariff authority to the executive branch")
        self.assertEqual(norm1, norm2)
        self.assertEqual(norm1, norm3)
        self.assertEqual(norm1, norm4)

    def test_evaluate_headline_non_energy_policy_tariff_exclusion(self):
        # Generic congressional / trade policy articles should be filtered at Stage 1
        h1 = "House Should Not Transfer More Tariff Authority to the Executive Branch - National Taxpayers Union"
        is_anomaly1, scores1 = self.monitor.evaluate_headline_anomaly(h1)
        self.assertFalse(is_anomaly1)
        self.assertEqual(scores1["overall_price_pressure"], 0.0)

        h2 = "White House considers new steel tariff and aluminum tariff under Section 232"
        is_anomaly2, scores2 = self.monitor.evaluate_headline_anomaly(h2)
        self.assertFalse(is_anomaly2)

        # Canola and agricultural cooking oil headlines should be filtered
        h3 = "China threatens retaliatory tariff on Canadian canola oil imports"
        is_anomaly3, scores3 = self.monitor.evaluate_headline_anomaly(h3)
        self.assertFalse(is_anomaly3)
        self.assertEqual(scores3["overall_price_pressure"], 0.0)

    def test_evaluate_headline_energy_tariff_inclusion(self):
        # Energy-specific tariff headlines must still trigger Stage 1 evaluation
        h1 = "Trump threatens 25% tariff on Canadian crude oil imports"
        with patch("src.intraday_event_monitor.extract_event_features_llm", return_value={"overall_price_pressure": 0.50, "supply_disruption": 0.60}) as mock_llm1:
            is_anomaly1, scores1 = self.monitor.evaluate_headline_anomaly(h1)
            mock_llm1.assert_called_once()
            self.assertTrue(is_anomaly1)
            self.assertGreaterEqual(abs(scores1["overall_price_pressure"]), 0.40)

        h2 = "OPEC warns retaliatory energy tariff on crude blendstocks will disrupt refining"
        with patch("src.intraday_event_monitor.extract_event_features_llm", return_value={"overall_price_pressure": 0.50, "supply_disruption": 0.60}) as mock_llm2:
            is_anomaly2, scores2 = self.monitor.evaluate_headline_anomaly(h2)
            mock_llm2.assert_called_once()
            self.assertTrue(is_anomaly2)

    def test_evaluated_cache_deduplication_negative_anomaly(self):
        import tempfile
        from unittest.mock import patch
        import src.intraday_event_monitor as iem

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_eval_file = os.path.join(tmpdir, "evaluated_headlines.json")
            with patch.dict(os.environ, {"TESTING": ""}), \
                 patch.object(iem, "EVALUATED_CACHE_FILE", temp_eval_file), \
                 patch("src.wayback_archiver.archive_url_to_wayback", return_value={"archive_url": "", "canonical_url": ""}):
                monitor = IntradayEventMonitor()
                headline = "Routine quarterly corporate update on retail logistics"
                url = "https://example.com/routine_news_1"

                # 1. First evaluation: should evaluate as non-anomaly and save to evaluated cache
                res1 = monitor.process_incoming_headline(headline, source="Feed_Poller", url=url)
                self.assertFalse(res1["is_anomaly"])
                self.assertFalse(res1.get("duplicate", False))
                self.assertTrue(os.path.exists(temp_eval_file))

                # 2. Second evaluation (simulating next 15-minute polling cycle): should be detected as duplicate
                res2 = monitor.process_incoming_headline(headline, source="Feed_Poller", url=url)
                self.assertTrue(res2.get("duplicate"))
                self.assertFalse(res2["is_anomaly"])

                # 3. Third evaluation with publisher suffix variation: should still match via normalized title
                res3 = monitor.process_incoming_headline(
                    f"{headline} - National Taxpayers Union", 
                    source="Feed_Poller", 
                    url="https://news.google.com/different_tracking_url"
                )
                self.assertTrue(res3.get("duplicate"))

    def test_check_feed_health(self):
        """Verifies feed health diagnostics and latency reporting."""
        with patch.object(self.monitor, "fetch_executive_social_headlines", return_value=[{"headline": "Test Post"}]), \
             patch.object(self.monitor, "fetch_key_movers_headlines", return_value=[{"headline": "Mover statement"}]), \
             patch.object(self.monitor, "fetch_geopolitical_headlines", return_value=[{"headline": "Maritime update"}]):
            health = self.monitor.check_feed_health()
            self.assertIn("overall_healthy", health)
            self.assertIn("feeds_tested", health)
            self.assertGreaterEqual(health["feeds_tested"], 4)
            self.assertIn("feed_details", health)
            for feed in health["feed_details"]:
                self.assertIn("status", feed)
                self.assertIn("latency_ms", feed)

    @patch("src.intraday_event_monitor.feedparser", None)
    @patch("urllib.request.urlopen")
    def test_check_feed_health_rss_fallback_without_feedparser(self, mock_urlopen):
        """Verifies check_feed_health regex counting of <item> elements without feedparser (Issue #347)."""
        rss_content = b"""<?xml version="1.0" encoding="UTF-8" ?>
        <rss version="2.0">
        <channel>
            <title>Energy News</title>
            <item><title>Item 1</title></item>
            <item><title>Item 2</title></item>
            <item><title>Item 3</title></item>
        </channel>
        </rss>"""
        mock_resp = MagicMock()
        mock_resp.getcode.return_value = 200
        mock_resp.read.return_value = rss_content
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        with patch.object(self.monitor, "fetch_executive_social_headlines", return_value=[{"headline": "Test"}]), \
             patch.object(self.monitor, "fetch_key_movers_headlines", return_value=[{"headline": "Mover"}]), \
             patch.object(self.monitor, "fetch_geopolitical_headlines", return_value=[{"headline": "Maritime"}]):
            health = self.monitor.check_feed_health()
            self.assertTrue(health["overall_healthy"])
            rss_feeds = [f for f in health["feed_details"] if f["source"] == "RSS"]
            for f in rss_feeds:
                self.assertEqual(f["status"], "HEALTHY")
                self.assertEqual(f["item_count"], 3)

    @patch("src.intraday_event_monitor.feedparser", None)
    @patch("urllib.request.urlopen")
    def test_check_feed_health_atom_fallback_without_feedparser(self, mock_urlopen):
        """Verifies check_feed_health regex counting of <entry> elements without feedparser (Issue #347)."""
        atom_content = b"""<?xml version="1.0" encoding="utf-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <title>Atom Feed</title>
            <entry><title>Entry 1</title></entry>
            <entry><title>Entry 2</title></entry>
        </feed>"""
        mock_resp = MagicMock()
        mock_resp.getcode.return_value = 200
        mock_resp.read.return_value = atom_content
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        with patch.object(self.monitor, "fetch_executive_social_headlines", return_value=[{"headline": "Test"}]), \
             patch.object(self.monitor, "fetch_key_movers_headlines", return_value=[{"headline": "Mover"}]), \
             patch.object(self.monitor, "fetch_geopolitical_headlines", return_value=[{"headline": "Maritime"}]):
            health = self.monitor.check_feed_health()
            self.assertTrue(health["overall_healthy"])
            rss_feeds = [f for f in health["feed_details"] if f["source"] == "RSS"]
            for f in rss_feeds:
                self.assertEqual(f["status"], "HEALTHY")
                self.assertEqual(f["item_count"], 2)



    @patch("src.intraday_event_monitor.extract_event_features_llm")
    @patch("src.data_ingestion.fetch_market_data")
    def test_evaluate_headline_spectral_context_generation(self, mock_fetch_market_data, mock_extract):
        """Verifies fetch_market_data is invoked and spectral_context is passed to LLM extractor (Issue #327)."""
        import pandas as pd
        import numpy as np
        # Mock market dataframe with gasoline_rbob series
        mock_df = pd.DataFrame({
            "gasoline_rbob": np.linspace(2.20, 2.65, 30)
        })
        mock_fetch_market_data.return_value = mock_df
        mock_extract.return_value = {"overall_price_pressure": 0.50, "supply_disruption": 0.60}

        headline = "OPEC Emergency Meeting Called as Middle East Pipeline Halts"
        is_anomaly, scores = self.monitor.evaluate_headline_anomaly(headline)

        self.assertTrue(is_anomaly)
        mock_fetch_market_data.assert_called_once()
        mock_extract.assert_called_once()
        _, kwargs = mock_extract.call_args
        self.assertIn("spectral_context", kwargs)
        self.assertTrue(len(kwargs["spectral_context"]) > 0)
        self.assertIn("Spectral Regime:", kwargs["spectral_context"])


    def test_false_positive_suppression_sanctions_macro_rhetoric(self):
        """Verifies macro sanctions headlines without petroleum tokens are suppressed (Issues #312, #318)."""
        h_reuters = "Russia sanctions bill gives Trump sweeping new tariff powers - Reuters"
        is_anomaly_reuters, scores_reuters = self.monitor.evaluate_headline_anomaly(h_reuters)
        self.assertFalse(is_anomaly_reuters)
        self.assertEqual(scores_reuters.get("overall_price_pressure", 0.0), 0.0)

        h_cbs = "Trump signs Russia sanctions bill championed by Lindsey Graham - CBS News"
        is_anomaly_cbs, scores_cbs = self.monitor.evaluate_headline_anomaly(h_cbs)
        self.assertFalse(is_anomaly_cbs)
        self.assertEqual(scores_cbs.get("overall_price_pressure", 0.0), 0.0)

        # Petroleum energy sanctions must still be evaluated
        h_crude = "US announces emergency sanctions on Iranian crude oil tanker fleet"
        with patch("src.intraday_event_monitor.extract_event_features_llm", return_value={"overall_price_pressure": 0.50, "supply_disruption": 0.60}) as mock_llm:
            is_anomaly_crude, scores_crude = self.monitor.evaluate_headline_anomaly(h_crude)
            mock_llm.assert_called_once()
            self.assertTrue(is_anomaly_crude)

    def test_false_positive_suppression_local_data_center_spill(self):
        """Verifies minor localized data center / generator spills are suppressed (Issue #317)."""
        headline = "Data Center’s Spill of 5,000 Gallons of Diesel Forces N.J. River Cleanup"
        is_anomaly, scores = self.monitor.evaluate_headline_anomaly(headline)
        self.assertFalse(is_anomaly)
        self.assertEqual(scores.get("overall_price_pressure", 0.0), 0.0)

        # Commercial midstream / pipeline spills must still evaluate
        h_pipeline = "Major pipeline rupture spills 10,000 barrels of diesel in Colonial main line"
        with patch("src.intraday_event_monitor.extract_event_features_llm", return_value={"overall_price_pressure": 0.50, "supply_disruption": 0.60}) as mock_pipe_llm:
            is_anomaly_pipe, _ = self.monitor.evaluate_headline_anomaly(h_pipeline)
            mock_pipe_llm.assert_called_once()
            self.assertTrue(is_anomaly_pipe)

    def test_resolve_target_locales_joliet_and_midcontinent(self):
        """Verifies Joliet (Chicago spot benchmark) and Midcontinent map to regional hubs."""
        locs_joliet = self.monitor.resolve_target_locales("Total power outage forces emergency shutdown of Joliet refinery")
        self.assertIn("Cincinnati", locs_joliet)

        locs_midcont = self.monitor.resolve_target_locales("Midcontinent refinery outage threatens regional fuel stocks")
        self.assertIn("Cincinnati", locs_midcont)
        self.assertIn("Tulsa", locs_midcont)

    @patch("src.intraday_event_monitor.send_duplicate_review_discord_notification")
    def test_duplicate_holding_for_operator_review(self, mock_discord_review):
        """Verifies potential duplicate events sharing the same facility are held for review."""
        from datetime import timezone
        mock_discord_review.return_value = True

        # Pre-seed a prior active event in deduplicator
        prior_event = {
            "headline": "Exxon Joliet refinery outage shuts down capacity",
            "url": "https://example.com/exxon1",
            "hash": "abc12345",
            "is_anomaly": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        with patch.object(self.monitor.deduplicator, "get_recent_active_events", return_value=[prior_event]), \
             patch.object(self.monitor, "evaluate_headline_anomaly", return_value=(True, {"overall_price_pressure": 0.50, "supply_disruption": 0.60})), \
             patch("src.wayback_archiver.archive_url_to_wayback", return_value={"archive_url": "", "canonical_url": ""}):
            incoming = "Exxon Joliet refinery outage continues as units remain offline"
            res = self.monitor.process_incoming_headline(incoming, source="Feed_Poller", url="https://example.com/exxon2")

            self.assertTrue(res.get("pending_review"))
            self.assertEqual(res.get("matched_entity"), "Joliet")
            self.assertEqual(res.get("duplicate_candidate_of"), "abc12345")
            mock_discord_review.assert_called_once()

    def test_hindsight_saas_retention_and_recall_integration(self):
        """Verifies Hindsight SaaS retention, recall, and deduplication logic with mocked network."""
        dedup = self.monitor.deduplicator
        event = {
            "headline": "Fire at Baytown refinery forces unit shutdown",
            "source": "Reuters",
            "url": "https://example.com/baytown_fire",
            "hash": "baytown123",
            "is_anomaly": True,
            "target_locales": ["Houston"]
        }

        # 1. By default under TESTING=1, retention and recall skip remote network
        with patch.dict(os.environ, {"TESTING": "1", "FORCE_HINDSIGHT_SYNC": ""}):
            self.assertFalse(dedup.retain_event_in_hindsight(event))
            self.assertEqual(dedup.query_hindsight_candidates("Baytown fire"), [])

        # 2. When FORCE_HINDSIGHT_SYNC is active, retention posts memory payload to SaaS bank
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__.return_value = mock_resp

        with patch.dict(os.environ, {"TESTING": "1", "FORCE_HINDSIGHT_SYNC": "1", "HINDSIGHT_API_TOKEN": "mock_token"}), \
             patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
            success = dedup.retain_event_in_hindsight(event)
            self.assertTrue(success)
            mock_urlopen.assert_called_once()
            req = mock_urlopen.call_args[0][0]
            self.assertIn("midgley-event-dedupe/memories", req.full_url)
            self.assertEqual(req.get_header("Authorization"), "Bearer mock_token")

        # 3. Recall queries Hindsight SaaS and extracts candidate results
        mock_recall_data = {
            "results": [
                {
                    "text": "Baytown refinery unit shuts down after major fire incident",
                    "entities": ["Baytown"],
                    "document_id": "baytown_cloud_doc",
                    "metadata": {"url": "https://bloomberg.com/baytown_fire_syndicated"}
                }
            ]
        }
        mock_recall_resp = MagicMock()
        mock_recall_resp.status = 200
        mock_recall_resp.read.return_value = json.dumps(mock_recall_data).encode("utf-8")
        mock_recall_resp.__enter__.return_value = mock_recall_resp

        with patch.dict(os.environ, {"TESTING": "1", "FORCE_HINDSIGHT_SYNC": "1", "HINDSIGHT_API_TOKEN": "mock_token"}), \
             patch("urllib.request.urlopen", return_value=mock_recall_resp):
            candidates = dedup.query_hindsight_candidates("Baytown refinery fire")
            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0]["document_id"], "baytown_cloud_doc")

        # 4. Check potential duplicate identifies candidate via Hindsight SaaS fallback
        with patch.object(dedup, "get_recent_active_events", return_value=[]), \
             patch.object(dedup, "query_hindsight_candidates", return_value=mock_recall_data["results"]):
            match = dedup.check_potential_duplicate(
                "Baytown refinery unit shuts down after major fire incident",
                source="Bloomberg",
                url="https://other.com/baytown_incident"
            )
            self.assertIsNotNone(match)
            self.assertTrue(match["is_potential_duplicate"])
            self.assertTrue(match.get("hindsight_saas_matched"))
            self.assertEqual(match["matched_entity"], "Baytown")

    @patch("src.intraday_event_monitor.send_intraday_discord_notification")
    def test_process_incoming_headline_retains_to_hindsight(self, mock_discord):
        """Verifies confirmed non-duplicate anomaly calls retain_event_in_hindsight."""
        mock_discord.return_value = True
        headline = "Emergency shutdown at Baytown refinery after explosion"

        with patch.dict(os.environ, {"TESTING": "0"}), \
             patch.object(self.monitor, "evaluate_headline_anomaly", return_value=(True, {"overall_price_pressure": 0.60, "supply_disruption": 0.70})), \
             patch.object(self.monitor.deduplicator, "check_potential_duplicate", return_value=None), \
             patch.object(self.monitor.deduplicator, "retain_event_in_hindsight") as mock_retain, \
             patch.object(self.monitor, "_save_anomaly_record"), \
             patch.object(self.monitor, "_save_evaluated_record"), \
             patch("src.intraday_event_monitor.clear_lookup_cache"), \
             patch("src.dashboard_generator.generate_public_dashboard"), \
             patch("src.wayback_archiver.archive_url_to_wayback", return_value={"archive_url": "", "canonical_url": ""}):
            res = self.monitor.process_incoming_headline(headline, source="Feed_Poller", url="https://example.com/baytown_new")
            self.assertTrue(res["is_anomaly"])
            self.assertFalse(res.get("pending_review", False))
            mock_retain.assert_called_once_with(res)


if __name__ == "__main__":
    unittest.main()



