"""
Unit Tests for Static API Exporter (tests/test_static_api_exporter.py)
Validates that docs/api/v1/ static endpoints are correctly exported and consistent with model forecasts.
"""

import os
import json
import tempfile
import pytest
from src.static_api_exporter import export_all_static_api_endpoints, SUPPORTED_LOCALES


def test_export_all_static_api_endpoints_structure():
    with tempfile.TemporaryDirectory() as tmp_dir:
        res = export_all_static_api_endpoints(docs_dir=tmp_dir)
        assert res["status"] == "success"
        assert res["exported_locales_count"] == len(SUPPORTED_LOCALES)

        api_dir = os.path.join(tmp_dir, "api", "v1")
        assert os.path.exists(api_dir)

        # Check combined.json master index
        master_file = os.path.join(api_dir, "combined.json")
        assert os.path.exists(master_file)
        with open(master_file, "r", encoding="utf-8") as f:
            master_data = json.load(f)
            assert master_data["status"] == "success"
            assert "locales" in master_data
            assert "tulsa" in master_data["locales"]
            assert "national" in master_data["locales"]

        # Check individual locale endpoints
        for loc in SUPPORTED_LOCALES:
            flat_file = os.path.join(api_dir, f"{loc}.json")
            combined_flat = os.path.join(api_dir, f"combined_{loc}.json")
            nested_file = os.path.join(api_dir, "combined", f"{loc}.json")

            assert os.path.exists(flat_file), f"Missing {flat_file}"
            assert os.path.exists(combined_flat), f"Missing {combined_flat}"
            assert os.path.exists(nested_file), f"Missing {nested_file}"

            with open(flat_file, "r", encoding="utf-8") as f:
                payload = json.load(f)
                assert payload["status"] == "success"
                assert "live_lookup" in payload
                assert "forecast" in payload
                assert payload["live_lookup"]["current_price_per_gal"] > 0
                assert payload["forecast"]["predicted_price_per_gal"] > 0
                assert "day_1_price" in payload["forecast"]
                assert "day_5_price" in payload["forecast"]


def test_tulsa_endpoint_data_alignment():
    with tempfile.TemporaryDirectory() as tmp_dir:
        export_all_static_api_endpoints(docs_dir=tmp_dir)
        tulsa_path = os.path.join(tmp_dir, "api", "v1", "tulsa.json")
        with open(tulsa_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert data["locale"]["code"] == "tulsa"
            assert data["locale"]["region_id"] == "Tulsa_OK"
            assert data["live_lookup"]["current_price_per_gal"] >= 3.50
            assert data["forecast"]["current_base_price"] >= 3.50
            assert "day_3_price" in data["forecast"]
