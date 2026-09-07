import os
import json
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock


class TestEDGAR8KRelevanceFilter(unittest.TestCase):
    """Tests for the EDGAR8KMonitor.is_relevant() keyword gate."""

    def setUp(self):
        os.environ.setdefault("SEC_USER_AGENT", "TestSuite test@example.com")
        from src.edgar_8k_monitor import EDGAR8KMonitor
        self.monitor_cls = EDGAR8KMonitor

    def test_relevant_fcc_outage(self):
        text = (
            "PBF Energy announces unplanned outage of the FCC unit at its "
            "Delaware City refinery due to an unexpected mechanical failure. "
            "The company has declared force majeure on product deliveries."
        )
        self.assertTrue(self.monitor_cls.is_relevant(text))

    def test_relevant_refinery_fire(self):
        text = (
            "Marathon Petroleum reports a fire at its Catlettsburg, Kentucky "
            "refinery hydrocracker unit. Operations have been temporarily shut down "
            "pending safety inspection."
        )
        self.assertTrue(self.monitor_cls.is_relevant(text))

    def test_relevant_capacity_reduction(self):
        text = (
            "HF Sinclair discloses a capacity reduction of approximately 30,000 bpd "
            "at its El Dorado refinery due to a coker unit turnaround expected 45 days."
        )
        self.assertTrue(self.monitor_cls.is_relevant(text))

    def test_noise_earnings_release(self):
        text = (
            "PBF Energy reports fourth quarter and full year 2025 financial results. "
            "The company announces appointment of a new Chief Financial Officer "
            "effective January 1, 2026. Quarterly dividend of 0.25 per share declared."
        )
        self.assertFalse(self.monitor_cls.is_relevant(text))

    def test_noise_debt_issuance(self):
        text = (
            "Valero Energy announces pricing of 750 million aggregate principal amount "
            "of 5.125 percent senior notes due 2034. Net proceeds will be used to repay "
            "outstanding commercial paper and for general corporate purposes."
        )
        self.assertFalse(self.monitor_cls.is_relevant(text))

    def test_integration_gate_supply_disruption_score(self):
        """
        Routing a relevant 8-K through _route_to_pipeline must call
        process_incoming_headline and return supply_disruption >= 0.40.
        Uses sys.modules stub to avoid heavy transitive imports (networkx etc.).
        """
        relevant_headline = (
            "PBF Energy 8-K: Unplanned FCC unit outage at Delaware City refinery -- "
            "force majeure declared on gasoline deliveries"
        )
        mock_result = {
            "supply_disruption": 0.72,
            "target_locales": ["Newark"],
            "is_anomaly": True,
            "overall_price_pressure": 0.65,
        }

        # Stub out the heavy intraday_event_monitor dependency
        mock_monitor_instance = MagicMock()
        mock_monitor_instance.process_incoming_headline.return_value = mock_result
        mock_monitor_cls = MagicMock(return_value=mock_monitor_instance)
        mock_iem_module = MagicMock()
        mock_iem_module.IntradayEventMonitor = mock_monitor_cls

        with patch.dict(sys.modules, {"src.intraday_event_monitor": mock_iem_module}):
            from src.edgar_8k_monitor import EDGAR8KMonitor
            with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as tmp:
                json.dump({}, tmp)
                tmp_cache = tmp.name
            monitor = EDGAR8KMonitor(cache_file=tmp_cache)
            filing = {
                "ticker": "PBF",
                "accession_id": "test-accession-001",
                "filed_at": "2026-09-06T12:00:00Z",
                "headline": relevant_headline,
                "body_text": "Unplanned FCC unit outage at Delaware City refinery...",
                "url": "https://www.sec.gov/Archives/edgar/data/test/000001.htm",
                "cache_key": "PBF:test-accession-001",
            }
            monitor._route_to_pipeline(filing)
            mock_monitor_instance.process_incoming_headline.assert_called_once_with(
                headline=relevant_headline,
                source="EDGAR_8K",
                url=filing["url"],
            )
            result = mock_monitor_instance.process_incoming_headline.return_value
            self.assertGreaterEqual(result["supply_disruption"], 0.40)
            self.assertIn("Newark", result["target_locales"])
            os.unlink(tmp_cache)


class TestEDGAR8KCachePersistence(unittest.TestCase):
    """Tests for the EDGAR8KMonitor accession-number deduplication cache."""

    def test_seen_accession_not_reprocessed(self):
        from src.edgar_8k_monitor import EDGAR8KMonitor
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as tmp:
            json.dump({"PBF:0001234567-26-000001": "2026-09-01T00:00:00Z"}, tmp)
            tmp_cache = tmp.name
        monitor = EDGAR8KMonitor(cache_file=tmp_cache)
        self.assertTrue(monitor._is_seen("PBF:0001234567-26-000001"))
        self.assertFalse(monitor._is_seen("PBF:0001234567-26-999999"))
        os.unlink(tmp_cache)


if __name__ == "__main__":
    unittest.main()