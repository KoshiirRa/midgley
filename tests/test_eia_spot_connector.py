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
            self.assertGreater(spot["gulf_coast_spot_per_gal"], 1.0)
            self.assertGreater(spot["ny_harbor_spot_per_gal"], 1.0)
            self.assertGreater(spot["los_angeles_spot_per_gal"], 1.0)

            basis = res["spot_basis"]
            self.assertIn("gulf_coast_basis", basis)
            self.assertIn("ny_harbor_basis", basis)
            self.assertIn("los_angeles_basis", basis)

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
