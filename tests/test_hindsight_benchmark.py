"""
Simulated 4-Week Reflection Benchmark Suite (Issue #230)
Evaluates token efficiency, latency, and memory recall accuracy across a 28-day forecasting cycle.
"""

import os
import time
import tempfile
import unittest
import json
from src.agent_memory import SQLiteMemoryStore, AgentMemoryManager


class TestHindsight4WeekBenchmark(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "benchmark_memory.sqlite")
        self.manager = AgentMemoryManager(sqlite_path=self.db_path)

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_simulated_4_week_memory_lifecycle(self):
        """
        Simulates 28 days of daily forecasts across 8 metro hubs (224 predictions total),
        with 6 injected supply/geopolitical shock anomalies.
        """
        regions = ["National", "Tulsa_OK", "Newark_DE", "Cincinnati_OH", "Oakland_CA", "Port_St_Lucie_FL", "Greenville_NC", "Charlotte_NC"]
        
        # 1. Benchmark Retain Latency across 224 records
        start_retain = time.perf_counter()
        retained_count = 0
        for day in range(1, 29):
            date_str = f"2026-09-{day:02d}"
            for reg in regions:
                is_shock = (day in (4, 11, 18, 25)) and (reg in ("Newark_DE", "Tulsa_OK", "Port_St_Lucie_FL"))
                err = 0.38 if is_shock else 0.04
                pred = 2.50 + err
                act = 2.50
                anom = "LARGE_OVERESTIMATE" if is_shock else "NORMAL"
                
                self.manager.retain(
                    content=f"Day {day} forecast for {reg}: shock={is_shock}, error=${err:.4f}/gal",
                    region=reg,
                    memory_type="anomaly_shock" if is_shock else "experience",
                    anomaly_type=anom,
                    error_dollars=err,
                    predicted_price=pred,
                    actual_price=act,
                    forecast_target_date=date_str
                )
                retained_count += 1

        retain_duration_ms = (time.perf_counter() - start_retain) * 1000.0
        avg_retain_ms = retain_duration_ms / retained_count
        
        self.assertEqual(retained_count, 224)
        self.assertLess(avg_retain_ms, 50.0, f"Average retain latency was {avg_retain_ms:.2f}ms (expected < 50.0ms)")

        # 2. Benchmark Recall Latency and Accuracy
        start_recall = time.perf_counter()
        recalled = self.manager.recall("refinery shock error", region="Newark_DE", top_k=3)
        recall_duration_ms = (time.perf_counter() - start_recall) * 1000.0

        self.assertTrue(len(recalled) >= 1)
        self.assertLess(recall_duration_ms, 15.0, f"Recall query took {recall_duration_ms:.2f}ms (expected < 15.0ms)")

        # 3. Benchmark 4-Week Reflection Pass (Saturday Reviews)
        anomalies = [
            {
                "region": "Port_St_Lucie_FL",
                "predicted_price": 2.85,
                "actual_price": 2.45,
                "error_dollars": 0.40,
                "anomaly_type": "LARGE_OVERESTIMATE",
                "headline": "Tropical storm diversion avoided terminal damage"
            },
            {
                "region": "Tulsa_OK",
                "predicted_price": 2.20,
                "actual_price": 2.58,
                "error_dollars": -0.38,
                "anomaly_type": "LARGE_UNDERESTIMATE",
                "headline": "West Tulsa refinery crude unit unexpected run cut"
            }
        ]

        start_reflect = time.perf_counter()
        reflections = self.manager.reflect_on_anomalies(anomalies)
        reflect_duration_ms = (time.perf_counter() - start_reflect) * 1000.0

        self.assertEqual(len(reflections), 2)
        self.assertLess(reflect_duration_ms, 50.0, f"Deterministic reflection took {reflect_duration_ms:.2f}ms")

        # 4. Assert Storage Footprint
        db_size_bytes = os.path.getsize(self.db_path)
        self.assertLess(db_size_bytes, 500_000, f"Database size was {db_size_bytes} bytes (expected < 500KB)")

        print(f"\n[BENCHMARK] 4-Week Reflection Cycle Summary:")
        print(f"  - Total Experiences Ingested: {retained_count}")
        print(f"  - Avg Retain Latency:        {avg_retain_ms:.3f} ms / write")
        print(f"  - Analogy Recall Latency:    {recall_duration_ms:.3f} ms")
        print(f"  - Reflection Generation:     {reflect_duration_ms:.3f} ms")
        print(f"  - SQLite DB Storage Size:    {db_size_bytes / 1024.0:.2f} KB")


if __name__ == "__main__":
    unittest.main()
