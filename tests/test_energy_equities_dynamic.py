import pytest
import os
import json
import pandas as pd
from src.energy_equities_feed import (
    fetch_energy_equities_data,
    save_energy_equities_vintage_record,
    get_energy_equities_vintages_as_of,
    compute_commodity_equity_correlations,
    ENERGY_EQUITY_TICKERS
)
from src.retail_gas_correlations import compute_retail_gas_correlations


def test_energy_equities_schema():
    df = fetch_energy_equities_data(start_date="2024-01-01", end_date="2024-02-01")
    assert isinstance(df, pd.DataFrame)
    if not df.empty:
        assert "date" in df.columns
        for ticker in ENERGY_EQUITY_TICKERS.keys():
            if ticker in df.columns:
                assert df[ticker].dtype in [float, 'float64']


def test_energy_equities_vintage_persistence(tmp_path):
    temp_file = str(tmp_path / "energy_equities_vintages.json")
    record = {
        "level_correlations_with_retail_gas": {
            "RBOB_Gasoline_Futures_(RB=F)": 0.88
        }
    }
    save_energy_equities_vintage_record(record, filepath=temp_file)
    assert os.path.exists(temp_file)

    loaded = get_energy_equities_vintages_as_of("2099-12-31", filepath=temp_file)
    assert loaded is not None
    assert loaded["level_correlations_with_retail_gas"]["RBOB_Gasoline_Futures_(RB=F)"] == 0.88


def test_retail_gas_correlations_dynamic():
    res = compute_retail_gas_correlations(live_price=3.45)
    assert isinstance(res, dict)
    assert "level_correlations_with_retail_gas" in res
    assert "lead_lag_analysis" in res
