"""
Unit Test Suite for Unified Historical Benchmark & Fallback Refresh Orchestrator (Issue #297)
Tests src/benchmark_updater.py and verifies tiered fallback integration across all feeds.
"""

import os
import json
import pytest
import tempfile
from unittest.mock import patch, MagicMock
from src.benchmark_updater import (
    save_historical_benchmark,
    load_historical_benchmark,
    HistoricalBenchmarkManager,
    refresh_all_historical_benchmarks,
    BENCHMARK_STORAGE_DIR
)


class TestBenchmarkUpdater:

    def test_save_and_load_historical_benchmark(self):
        """Verify saving and loading benchmarks to a temporary JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test_feed_historical.json")
            sample_data = [{"date": "2026-09-12", "metric": 42.5}, {"date": "2026-09-05", "metric": 41.8}]
            
            # Save
            saved_path = save_historical_benchmark("test_feed", sample_data, filename=test_file)
            assert os.path.exists(saved_path)
            
            # Inspect raw JSON schema
            with open(saved_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            assert payload["benchmark_key"] == "test_feed"
            assert "last_refreshed_utc" in payload
            assert payload["records_count"] == 2
            assert payload["data"] == sample_data
            
            # Load
            loaded_data = load_historical_benchmark("test_feed", filename=test_file)
            assert loaded_data == sample_data

    def test_load_nonexistent_benchmark(self):
        """Verify load returns None gracefully for missing files."""
        result = load_historical_benchmark("non_existent_key_xyz", filename="data/non_existent_xyz.json")
        assert result is None

    def test_load_corrupted_benchmark(self):
        """Verify load handles corrupted JSON gracefully."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json content {{{")
            tmp_path = f.name
        try:
            result = load_historical_benchmark("corrupt_feed", filename=tmp_path)
            assert result is None
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    @patch("src.alternative_data_feeds.BakerHughesDataConnector.fetch_rig_counts")
    def test_refresh_baker_hughes(self, mock_fetch):
        """Verify Baker Hughes refresh persists records correctly."""
        import pandas as pd
        mock_df = pd.DataFrame([
            {"date": pd.Timestamp("2026-09-11"), "total_rigs": 585, "oil_rigs": 480, "gas_rigs": 105, "source": "FRED"}
        ])
        mock_fetch.return_value = mock_df
        
        with tempfile.TemporaryDirectory() as tmpdir:
            target_file = os.path.join(tmpdir, "baker_hughes_historical.json")
            with patch("src.benchmark_updater.BENCHMARK_STORAGE_DIR", tmpdir):
                res = HistoricalBenchmarkManager.refresh_baker_hughes()
                assert res["status"] == "SUCCESS"
                assert res["records"] == 1
                assert os.path.exists(target_file)

    @patch("src.executive_social_feed.ExecutiveSocialFeedConnector.fetch_executive_social_headlines")
    def test_refresh_executive_social(self, mock_fetch):
        """Verify executive social refresh persists records correctly."""
        mock_fetch.return_value = [
            {"date": "2026-09-12", "timestamp": "2026-09-12T14:30:00Z", "source": "Truth Social", "sentiment": "Dovish", "price_pressure": -0.45}
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.benchmark_updater.BENCHMARK_STORAGE_DIR", tmpdir):
                res = HistoricalBenchmarkManager.refresh_executive_social()
                assert res["status"] == "SUCCESS"
                assert res["records"] == 1

    @patch("src.geopolitical_feeds.GeopoliticalFeedConnector.fetch_geopolitical_headlines")
    def test_refresh_geopolitical(self, mock_fetch):
        """Verify geopolitical refresh persists records correctly."""
        mock_fetch.return_value = [
            {"date": "2026-09-10", "chokepoint": "Hormuz", "disruption_score": 0.35}
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.benchmark_updater.BENCHMARK_STORAGE_DIR", tmpdir):
                res = HistoricalBenchmarkManager.refresh_geopolitical()
                assert res["status"] == "SUCCESS"
                assert res["records"] == 1

    @patch("src.key_movers_feed.KeyMoversFeedConnector.fetch_key_movers_headlines")
    def test_refresh_key_movers(self, mock_fetch):
        """Verify key movers refresh persists records correctly."""
        mock_fetch.return_value = [
            {"date": "2026-09-11", "speaker": "Jerome Powell", "topic": "Interest Rates"}
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.benchmark_updater.BENCHMARK_STORAGE_DIR", tmpdir):
                res = HistoricalBenchmarkManager.refresh_key_movers()
                assert res["status"] == "SUCCESS"
                assert res["records"] == 1

    @patch("src.diesel_regional.get_live_or_anchor_diesel_prices")
    def test_refresh_diesel_regional(self, mock_fetch):
        """Verify regional diesel refresh persists records correctly."""
        mock_fetch.return_value = {
            "National": 3.65,
            "PADD_1B_Central_Atlantic": 3.75,
            "PADD_2_Midwest": 3.55
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.benchmark_updater.BENCHMARK_STORAGE_DIR", tmpdir):
                res = HistoricalBenchmarkManager.refresh_diesel_regional()
                assert res["status"] == "SUCCESS"
                assert res["records"] == 3

    @patch("src.treasury_yield_feed.TreasuryYieldConnector.fetch_treasury_yield_dataset")
    def test_refresh_treasury_yields(self, mock_fetch):
        """Verify treasury yields refresh persists records correctly."""
        import pandas as pd
        mock_df = pd.DataFrame([
            {"date": pd.Timestamp("2026-09-11"), "10Y": 4.15, "2Y": 3.85, "spread_10y_2y": 0.30}
        ])
        mock_fetch.return_value = mock_df
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.benchmark_updater.BENCHMARK_STORAGE_DIR", tmpdir):
                res = HistoricalBenchmarkManager.refresh_treasury_yields()
                assert res["status"] == "SUCCESS"
                assert res["records"] == 1

    @patch("src.usgs_water_feed.USGSWaterFeedConnector.fetch_live_water_telemetry")
    def test_refresh_usgs_water(self, mock_fetch):
        """Verify USGS water refresh persists records correctly."""
        mock_fetch.return_value = {
            "stations": [
                {"site_code": "03255000", "name": "Ohio River at Cincinnati", "stage_ft": 28.5}
            ]
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.benchmark_updater.BENCHMARK_STORAGE_DIR", tmpdir):
                res = HistoricalBenchmarkManager.refresh_usgs_water()
                assert res["status"] == "SUCCESS"
                assert res["records"] == 1

    @patch("src.usgs_seismic.USGSSeismicConnector.fetch_live_seismic_telemetry")
    def test_refresh_usgs_seismic(self, mock_fetch):
        """Verify USGS seismic refresh persists records correctly."""
        mock_fetch.return_value = {
            "corridors": ["cushing_ok", "san_francisco_refinery_corridor"],
            "events": [{"id": "us6000test", "mag": 2.8, "place": "Cushing, OK"}]
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.benchmark_updater.BENCHMARK_STORAGE_DIR", tmpdir):
                res = HistoricalBenchmarkManager.refresh_usgs_seismic()
                assert res["status"] == "SUCCESS"
                assert res["records"] == 1

    @patch("src.census_demographics.CensusDemographicsConnector.get_all_metro_demographics")
    def test_refresh_census_demographics(self, mock_fetch):
        """Verify Census demographics refresh persists records correctly."""
        mock_fetch.return_value = {
            "metro_areas": {
                "tulsa_ok": {"population": 1023000, "median_income": 62500}
            }
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.benchmark_updater.BENCHMARK_STORAGE_DIR", tmpdir):
                res = HistoricalBenchmarkManager.refresh_census_demographics()
                assert res["status"] == "SUCCESS"
                assert res["records"] == 1

    @patch("src.data_ingestion.fetch_oilpriceapi_prices")
    def test_refresh_commodity_spot_prices(self, mock_fetch):
        """Verify OilpriceAPI commodity spot prices refresh persists records correctly."""
        mock_fetch.return_value = {
            "WTI": 78.50,
            "BRENT": 82.30,
            "RBOB": 2.45
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.benchmark_updater.BENCHMARK_STORAGE_DIR", tmpdir):
                res = HistoricalBenchmarkManager.refresh_commodity_spot_prices()
                assert res["status"] == "SUCCESS"
                assert res["records"] == 3

    def test_refresh_all_orchestration(self):
        """Verify refresh_all executes all registered benchmarks and returns summary."""
        with patch.object(HistoricalBenchmarkManager, "refresh_baker_hughes", return_value={"status": "SUCCESS", "records": 10}), \
             patch.object(HistoricalBenchmarkManager, "refresh_executive_social", return_value={"status": "SUCCESS", "records": 5}), \
             patch.object(HistoricalBenchmarkManager, "refresh_geopolitical", return_value={"status": "SUCCESS", "records": 8}), \
             patch.object(HistoricalBenchmarkManager, "refresh_key_movers", return_value={"status": "SUCCESS", "records": 6}), \
             patch.object(HistoricalBenchmarkManager, "refresh_diesel_regional", return_value={"status": "SUCCESS", "records": 7}), \
             patch.object(HistoricalBenchmarkManager, "refresh_treasury_yields", return_value={"status": "SUCCESS", "records": 4}), \
             patch.object(HistoricalBenchmarkManager, "refresh_usgs_water", return_value={"status": "SUCCESS", "records": 4}), \
             patch.object(HistoricalBenchmarkManager, "refresh_usgs_seismic", return_value={"status": "SUCCESS", "records": 3}), \
             patch.object(HistoricalBenchmarkManager, "refresh_census_demographics", return_value={"status": "SUCCESS", "records": 7}), \
             patch.object(HistoricalBenchmarkManager, "refresh_commodity_spot_prices", return_value={"status": "SUCCESS", "records": 5}):
            
            summary = refresh_all_historical_benchmarks()
            assert "timestamp_utc" in summary
            assert summary["benchmarks_refreshed"] == "10/10"
            assert len(summary["details"]) == 10
            for key, val in summary["details"].items():
                assert val["status"] == "SUCCESS"
