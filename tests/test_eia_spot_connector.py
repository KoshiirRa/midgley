"""
Unit & Integration Tests for Zero-Cost EIA Daily Regional Spot Price Connector (Issue #363).
"""

import unittest
from unittest.mock import patch, MagicMock
import tempfile
import os
import json

from src.data_ingestion import EIARegionalSpotConnector


class TestEIARegionalSpotConnector(unittest.TestCase):
    def setUp(self):
        self.connector = EIARegionalSpotConnector()

    def test_fetch_daily_regional_spot_prices_baseline(self):
        """Verifies default physical spot prices and basis calculations."""
        with patch.dict(os.environ, {"TESTING": "1"}):
            res = self.connector.fetch_daily_regional_spot_prices()
            self.assertIn(res["status"], ["SUCCESS", "FALLBACK_SYNTHETIC"])
            self.assertIn("spot_prices", res)
            self.assertIn("spot_basis", res)
            
            spot = res["spot_prices"]
            self.assertIn("gulf_coast_spot_per_gal", spot)
            self.assertIn("ny_harbor_spot_per_gal", spot)
            self.assertIn("los_angeles_spot_per_gal", spot)
            self.assertIn("group3_tulsa_spot_per_gal", spot)
            self.assertIn("chicago_spot_per_gal", spot)
            self.assertGreater(spot["gulf_coast_spot_per_gal"], 1.0)
            self.assertGreater(spot["ny_harbor_spot_per_gal"], 1.0)
            self.assertGreater(spot["los_angeles_spot_per_gal"], 1.0)
            self.assertGreater(spot["group3_tulsa_spot_per_gal"], 1.0)
            self.assertGreater(spot["chicago_spot_per_gal"], 1.0)

            basis = res["spot_basis"]
            self.assertIn("gulf_coast_basis", basis)
            self.assertIn("ny_harbor_basis", basis)
            self.assertIn("los_angeles_basis", basis)
            self.assertIn("group3_tulsa_basis", basis)
            self.assertIn("chicago_basis", basis)

            # Phase 3: ULSD spot & physical 3:2:1 cash crack spreads
            self.assertIn("ulsd_spot_prices", res)
            self.assertIn("physical_crack_321_bbl", res)
            cracks = res["physical_crack_321_bbl"]
            self.assertIn("gulf_coast_321_crack_bbl", cracks)
            self.assertIn("ny_harbor_321_crack_bbl", cracks)
            self.assertIn("los_angeles_321_crack_bbl", cracks)

    def test_eia_v2_spot_series_and_t_plus_1_lag(self):
        """Verifies EIA API v2 petroleum/pri/spt/ parsing and T+1 business-day publication lag (Issue #649)."""
        from src.eia_api_client import EIAClientV2, EIA_SERIES_PROVENANCE

        self.assertIn("EER_EPMRU_PF4_RGP_DPG", EIA_SERIES_PROVENANCE)
        self.assertIn("EER_EPMRU_PF4_RCH_DPG", EIA_SERIES_PROVENANCE)

        # Thursday -> Friday (+1), Friday -> Monday (+3)
        self.assertEqual(EIAClientV2._spot_publication_timestamp("2026-10-01"), "2026-10-02T15:00:00Z")
        self.assertEqual(EIAClientV2._spot_publication_timestamp("2026-10-02"), "2026-10-05T15:00:00Z")

        client = EIAClientV2(api_key="test-key")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "response": {
                "data": [
                    {"period": "2026-10-01", "value": "2.315"},
                    {"period": "2026-10-02", "value": "2.340"}
                ]
            }
        }
        client.session = MagicMock()
        client.session.get.return_value = mock_resp
        client.vintage_store = MagicMock()

        with patch.dict(os.environ, {"TESTING": "1"}):
            hist = client.fetch_spot_price_series("EER_EPMRU_PF4_RGP_DPG", record_vintages=True)

        self.assertEqual(hist["2026-10-01"], 2.315)
        self.assertEqual(hist["2026-10-02"], 2.340)
        self.assertEqual(client.vintage_store.record_observation.call_count, 2)
        last_call = client.vintage_store.record_observation.call_args.kwargs
        self.assertEqual(last_call["feed"], "eia_spot")
        self.assertEqual(last_call["published_at"], "2026-10-05T15:00:00Z")

    def test_bitemporal_vintage_persistence(self):
        """Verifies point-in-time observation persistence and retrieval as of target date."""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_vintage = os.path.join(tmpdir, "eia_spot_vintages.json")
            
            rec1 = {
                "source": "EIA Spot Test",
                "as_of": "2026-09-01 10:00:00",
                "valid_date": "2026-09-01",
                "spot_prices": {"gulf_coast_spot_per_gal": 2.20}
            }
            rec2 = {
                "source": "EIA Spot Test",
                "as_of": "2026-09-15 10:00:00",
                "valid_date": "2026-09-15",
                "spot_prices": {"gulf_coast_spot_per_gal": 2.35}
            }

            EIARegionalSpotConnector.save_eia_spot_vintage_record(rec1, filepath=temp_vintage)
            EIARegionalSpotConnector.save_eia_spot_vintage_record(rec2, filepath=temp_vintage)

            # Query as of Sep 10 -> should only return rec1
            v_early = EIARegionalSpotConnector.get_eia_spot_vintages_as_of("2026-09-10", filepath=temp_vintage)
            self.assertEqual(len(v_early), 1)
            self.assertEqual(v_early[0]["spot_prices"]["gulf_coast_spot_per_gal"], 2.20)

            # Query as of Sep 20 -> should return both
            v_all = EIARegionalSpotConnector.get_eia_spot_vintages_as_of("2026-09-20", filepath=temp_vintage)
            self.assertEqual(len(v_all), 2)


if __name__ == "__main__":
    unittest.main()
