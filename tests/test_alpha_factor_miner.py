"""
Unit Tests for LLM Alpha Factor Miner (tests/test_alpha_factor_miner.py)
Tests prompt generation, modern/legacy Google GenAI client pathways, response parsing, and error fallbacks.
"""

import json
import unittest
from unittest.mock import patch, MagicMock

from src.alpha_factor_miner import AlphaFactorMiner, DEFAULT_SEED_FACTORS


class TestAlphaFactorMinerLLM(unittest.TestCase):
    def setUp(self):
        self.available_cols = ["gasoline_rbob", "wti_crude", "cboe_ovx", "crack_spread_321"]

    def test_missing_api_key_returns_default_seed_factors(self):
        miner = AlphaFactorMiner(api_key=None)
        res = miner.generate_llm_hypotheses(self.available_cols, count=3)
        self.assertEqual(len(res), 3)
        self.assertEqual(res[0]["name"], DEFAULT_SEED_FACTORS[0]["name"])

    def test_modern_google_genai_success(self):
        mock_response = MagicMock()
        mock_response.text = json.dumps([
            {
                "name": "crack_momentum_5d",
                "expression": "Delta(crack_spread_321, 5)",
                "hypothesis": "Refining crack acceleration leads RBOB price breaks.",
                "category": "refining_margin"
            },
            {
                "name": "ovx_zscore_10d",
                "expression": "ZScore(cboe_ovx, 10)",
                "hypothesis": "Elevated option volatility predicts spot return shocks.",
                "category": "volatility_momentum"
            }
        ])

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        miner = AlphaFactorMiner(api_key="test_api_key")

        with patch("google.genai.Client", return_value=mock_client):
            res = miner.generate_llm_hypotheses(self.available_cols, count=2)
            self.assertEqual(len(res), 2)
            self.assertEqual(res[0]["name"], "crack_momentum_5d")
            self.assertEqual(res[0]["expression"], "Delta(crack_spread_321, 5)")
            self.assertEqual(res[1]["name"], "ovx_zscore_10d")

            # Verify prompt content
            call_kwargs = mock_client.models.generate_content.call_args[1]
            contents_str = call_kwargs["contents"]
            self.assertIn("gasoline_rbob", contents_str)
            self.assertIn("cboe_ovx", contents_str)
            self.assertIn("Qlib symbolic expression", contents_str)

    def test_legacy_google_generativeai_fallback(self):
        mock_legacy_response = MagicMock()
        mock_legacy_response.text = "```json\n" + json.dumps([
            {
                "name": "wti_rbob_corr_break",
                "formula": "Corr(gasoline_rbob, wti_crude, 15)",
                "hypothesis": "Decoupling between crude and gasoline signals localized bottleneck.",
                "category": "cross_asset"
            }
        ]) + "\n```"

        mock_legacy_model = MagicMock()
        mock_legacy_model.generate_content.return_value = mock_legacy_response

        mock_genai_legacy = MagicMock()
        mock_genai_legacy.GenerativeModel.return_value = mock_legacy_model

        miner = AlphaFactorMiner(api_key="test_api_key")

        with patch("google.genai.Client", side_effect=ImportError("No module named 'google.genai'")), \
             patch.dict("sys.modules", {"google.generativeai": mock_genai_legacy}):

            res = miner.generate_llm_hypotheses(self.available_cols, count=1)
            self.assertEqual(len(res), 1)
            self.assertEqual(res[0]["name"], "wti_rbob_corr_break")
            self.assertEqual(res[0]["expression"], "Corr(gasoline_rbob, wti_crude, 15)")

    def test_json_parse_error_falls_back_to_seed_factors(self):
        mock_response = MagicMock()
        mock_response.text = "NOT_VALID_JSON"

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        miner = AlphaFactorMiner(api_key="test_api_key")

        with patch("google.genai.Client", return_value=mock_client):
            res = miner.generate_llm_hypotheses(self.available_cols, count=2)
            self.assertEqual(len(res), 2)
            self.assertEqual(res[0]["name"], DEFAULT_SEED_FACTORS[0]["name"])

    def test_empty_or_malformed_list_falls_back_to_seed_factors(self):
        mock_response = MagicMock()
        mock_response.text = json.dumps([])

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        miner = AlphaFactorMiner(api_key="test_api_key")

        with patch("google.genai.Client", return_value=mock_client):
            res = miner.generate_llm_hypotheses(self.available_cols, count=2)
            self.assertEqual(len(res), 2)
            self.assertEqual(res[0]["name"], DEFAULT_SEED_FACTORS[0]["name"])


if __name__ == "__main__":
    unittest.main()
