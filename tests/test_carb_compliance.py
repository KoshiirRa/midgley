"""
Unit Tests for CARB LCFS & Cap-and-Trade Regulatory Engine (tests/test_carb_compliance.py)
Validates CARB compliance connector, dimensional $/MT to $/gal conversion formulas,
historical vintage resolution, and Oakland regional model integration. (Issue #383)
"""

import os
import pytest
import pandas as pd
import numpy as np

from src.carb_compliance import (
    CARBComplianceConnector,
    get_dynamic_carb_compliance_breakdown,
    CA_STATE_EXCISE_TAX,
    CA_LOCAL_SALES_UST_FEE,
    BASELINE_GASOLINE_CI,
    TARGET_LCFS_CI_2026,
    ENERGY_DENSITY_GASOLINE_MJ_GAL,
    EMISSION_FACTOR_GASOLINE_MT_GAL
)
from src.data_ingestion import (
    get_carb_compliance_connector,
    fetch_carb_compliance_breakdown
)


@pytest.fixture(autouse=True)
def setup_testing_env(monkeypatch):
    monkeypatch.setenv("TESTING", "1")


def test_carb_compliance_dimensional_formulas():
    """Validates mathematical conversion of $/MT carbon prices into per-gallon fees."""
    connector = CARBComplianceConnector()

    # 1. LCFS formula check:
    # At $100.00/MT, deficit = (100.82 - 88.25) = 12.57 gCO2e/MJ
    # Fee = 100 * (12.57 / 1,000,000) * 121.78 = 0.153077 $/gal -> 0.1531
    lcfs_fee = connector.calculate_lcfs_gasoline_fee(100.0, target_ci=88.25, baseline_ci=100.82)
    expected_lcfs = round(100.0 * ((100.82 - 88.25) / 1e6) * 121.78, 4)
    assert lcfs_fee == expected_lcfs
    assert 0.15 <= lcfs_fee <= 0.16

    # 2. Cap-and-Trade formula check:
    # At $40.00/MT, emission factor = 0.008887 MT/gal
    # Fee = 40.0 * 0.008887 = 0.35548 -> 0.3555 $/gal
    cap_trade_fee = connector.calculate_cap_and_trade_gasoline_fee(40.0)
    expected_ct = round(40.0 * 0.008887, 4)
    assert cap_trade_fee == expected_ct
    assert 0.35 <= cap_trade_fee <= 0.36


def test_carb_compliance_get_compliance_for_date():
    """Validates point-in-time compliance lookup and dynamic total tax burden calculation."""
    connector = CARBComplianceConnector()

    res_2024 = connector.get_compliance_for_date("2024-03-01")
    assert res_2024["as_of_date"] == "2024-03-01"
    assert res_2024["lcfs_credit_price_mt"] > 0
    assert res_2024["cap_trade_allowance_price_mt"] > 0
    assert res_2024["carb_state_excise_tax"] == CA_STATE_EXCISE_TAX
    assert res_2024["local_sales_ust_fee"] == CA_LOCAL_SALES_UST_FEE

    # Verify sum: total = excise + cap_trade + lcfs + local_ust
    expected_total = round(
        res_2024["carb_state_excise_tax"] +
        res_2024["cap_and_trade_fee_per_gal"] +
        res_2024["lcfs_credit_fee_per_gal"] +
        res_2024["local_sales_ust_fee"],
        4
    )
    assert res_2024["total_carb_tax_burden"] == expected_total
    assert 0.90 <= res_2024["total_carb_tax_burden"] <= 1.20


def test_carb_compliance_factory_helpers():
    """Validates data_ingestion module exports for CARB compliance."""
    connector = get_carb_compliance_connector()
    assert isinstance(connector, CARBComplianceConnector)

    breakdown = fetch_carb_compliance_breakdown()
    assert "total_carb_tax_burden" in breakdown
    assert "provenance" in breakdown


def test_oakland_regional_imports_dynamic_carb():
    """Validates that src/locations/oakland/regional.py uses dynamic CARB calculations."""
    from src.locations.oakland.regional import TOTAL_CARB_TAX_BURDEN, CARB_EXCISE_TAX, CAP_AND_TRADE_FEE, LCFS_CREDIT_FEE
    assert CARB_EXCISE_TAX == 0.596
    assert CAP_AND_TRADE_FEE > 0.0
    assert LCFS_CREDIT_FEE > 0.0
    assert TOTAL_CARB_TAX_BURDEN >= 0.90
