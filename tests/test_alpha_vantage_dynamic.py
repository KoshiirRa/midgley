import os
import json
import pytest
from unittest.mock import patch
import pandas as pd
import numpy as np
from src.data_ingestion import (
    AlphaVantageDataConnector,
    save_alpha_vantage_vintage_record,
    get_alpha_vantage_vintages_as_of
)

def test_alpha_vantage_dynamic_rsi_vwap():
    connector = AlphaVantageDataConnector(api_key=None)
    connector.is_trading_hours = lambda now_dt=None: True
    
    # Generate 60 days of synthetic price data with Close, Volume, High, Low
    dates = pd.date_range("2026-01-01", periods=60)
    closes = np.linspace(80.0, 90.0, 60)
    highs = closes + 1.0
    lows = closes - 1.0
    volumes = np.full(60, 1000000)
    
    mock_df = pd.DataFrame({
        "Close": closes,
        "High": highs,
        "Low": lows,
        "Volume": volumes
    }, index=dates)
    
    with patch("yfinance.Ticker") as mock_ticker:
        mock_ticker.return_value.history.return_value = mock_df
        rsi_res = connector.fetch_technical_indicator("XLE", "RSI", 14)
        assert rsi_res["symbol"] == "XLE"
        assert rsi_res["indicator"] == "RSI"
        assert rsi_res["value"] > 0
        assert "yfinance" in rsi_res["source"] or "Dynamic" in rsi_res["source"]

        vwap_res = connector.fetch_technical_indicator("XLE", "VWAP", 14)
        assert vwap_res["indicator"] == "VWAP"
        assert vwap_res["value"] > 0

def test_alpha_vantage_bitemporal_vintage_tracking(tmp_path):
    v_file = str(tmp_path / "alpha_vantage_vintages.json")
    record = {
        "symbol": "XLE",
        "value": 62.4,
        "as_of": "2026-03-15 12:00:00",
        "valid_date": "2026-03-15",
        "source": "Alpha Vantage Dynamic yfinance Technical Benchmark (XLE - RSI)"
    }
    
    save_alpha_vantage_vintage_record(record, filepath=v_file)
    assert os.path.exists(v_file)
    
    vintages = get_alpha_vantage_vintages_as_of("2026-03-16", symbol="XLE", filepath=v_file)
    assert len(vintages) == 1
    assert vintages[0]["symbol"] == "XLE"
    assert vintages[0]["value"] == 62.4
