"""
Unit Tests for Dynamic Region Calibration Engine (tests/test_dynamic_region.py)
"""

import os
import pytest
from src.dynamic_region import DynamicRegionRunner, run_dynamic_region_pipeline
from src.regional_metadata import get_regional_metadata


def test_dynamic_region_runner_init():
    """Test initialized runner with existing region ID."""
    runner = DynamicRegionRunner("tulsa_ok")
    assert runner.region_id == "tulsa_ok"
    assert runner.display_name == "Tulsa, OK Metro Retail"
    assert runner.zip_code == "74101"


def test_dynamic_region_runner_custom_dict():
    """Test initializing runner with custom profile dictionary."""
    custom_profile = {
        "region_id": "test_city",
        "display_name": "Test City, US",
        "padd_region": "PADD_2",
        "zip_code": "99999",
        "base_price_anchor": 3.650,
        "statutory_tax_gal": 0.350,
        "rack_margin_offset": 0.400,
        "logger_region_key": "Test_City"
    }
    runner = DynamicRegionRunner(custom_profile)
    assert runner.region_id == "test_city"
    assert runner.display_name == "Test City, US"
    assert runner.base_price_anchor == 3.650

    res = runner.run_pipeline(live_pump_price=3.700, use_llm_api=False, model_type="ridge")
    assert "current_base_price" in res
    assert res["current_base_price"] == 3.700
    assert "predicted_5d_price" in res
    assert "feature_attributions" in res
