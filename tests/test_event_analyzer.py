"""
Unit tests for LLM Event Analyzer Module (src/event_analyzer.py)
Tests single and batch headline extraction, SHA-256 deduplication, and lookup cache hits.
"""

import os
import unittest
from unittest.mock import patch, MagicMock

from src.event_analyzer import (
    extract_event_features_llm,
    extract_batch_event_features_llm,
    extract_event_features_rule_based,
    _get_headline_sha256,
    _LLM_SCORE_CACHE
)
from src.lookup_cache import global_cache


class TestEventAnalyzer(unittest.TestCase):

    def setUp(self):
        global_cache.clear()
        _LLM_SCORE_CACHE.clear()

    def tearDown(self):
        global_cache.clear()
        _LLM_SCORE_CACHE.clear()

    def test_headline_sha256_hashing(self):
        h1 = "OPEC Announces Sudden 1M Barrel Supply Cut"
        h2 = "OPEC Announces Sudden 1M Barrel Supply Cut"
        self.assertEqual(_get_headline_sha256(h1), _get_headline_sha256(h2))

    def test_single_headline_caching(self):
        headline = "Refinery Outage in Texas Gulf Coast Spikes Gasoline Prices"
        # First extraction (rule-based fallback when no API key)
        scores1 = extract_event_features_llm(headline)
        self.assertIsNotNone(scores1)
        self.assertIn("overall_price_pressure", scores1)

        # Verify key exists in lookup cache
        sha_key = f"llm_score:{_get_headline_sha256(headline)}"
        cached = global_cache.get(sha_key)
        self.assertIsNotNone(cached)
        self.assertEqual(cached["overall_price_pressure"], scores1["overall_price_pressure"])

        # Second extraction should hit cache instantly
        scores2 = extract_event_features_llm(headline)
        self.assertEqual(scores2["overall_price_pressure"], scores1["overall_price_pressure"])

    def test_batch_headline_caching(self):
        headlines = [
            "Hurricane Threatens Gulf Oil Rigs",
            "Tornado Damages West Tulsa Refinery Pipeline"
        ]
        results1 = extract_batch_event_features_llm(headlines)
        self.assertEqual(len(results1), 2)

        # Second batch run hits cache
        results2 = extract_batch_event_features_llm(headlines)
        self.assertEqual(len(results2), 2)
        self.assertEqual(results1[0]["overall_price_pressure"], results2[0]["overall_price_pressure"])

    @patch("src.event_analyzer.extract_event_features_llm")
    def test_batch_size_mismatch_itemized_fallback(self, mock_extract_llm):
        """Verifies that when LLM returns a batch length mismatch, itemized extract_event_features_llm is invoked (Issue #334)."""
        mock_extract_llm.side_effect = lambda h, **kwargs: {
            "geopolitical_risk": 0.5,
            "supply_disruption": 0.6,
            "demand_sentiment": 0.0,
            "opec_action": 0.0,
            "overall_price_pressure": 0.36
        }

        headlines = [
            "Unexpected refinery fire in Delaware City",
            "Pipeline valve leak halts Colonial Line 1",
            "OPEC delegates signal rollover"
        ]

        # Simulate Gemini returning only 1 item for a 3-item batch
        with patch("google.genai.Client") as mock_genai_client:
            mock_client_instance = MagicMock()
            mock_resp = MagicMock()
            # Only 1 item returned instead of 3
            mock_resp.text = '[{"geopolitical_risk": 0.1, "supply_disruption": 0.2, "demand_sentiment": 0.0, "opec_action": 0.0, "overall_price_pressure": 0.1}]'
            mock_client_instance.models.generate_content.return_value = mock_resp
            mock_genai_client.return_value = mock_client_instance

            results = extract_batch_event_features_llm(headlines, api_key="test_api_key")
            self.assertEqual(len(results), 3)
            # Itemized LLM extractor should have been called for all 3 uncached headlines
            self.assertEqual(mock_extract_llm.call_count, 3)


if __name__ == "__main__":
    unittest.main()
