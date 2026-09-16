import os
import json
import pytest
from unittest.mock import patch
import pandas as pd
from src.data_ingestion import (
    OilPriceAPIDataConnector,
    fetch_oilpriceapi_prices,
    save_oilpriceapi_vintage_record,
    get_oilpriceapi_vintages_as_of
)

def test_oilpriceapi_fallback_benchmark_dynamic_yfinance():
    connector = OilPriceAPIDataConnector(api_key=None)
    
    # Mock yfinance Ticker history
    mock_hist = pd.DataFrame({"Close": [72.50, 74.20, 75.80]}, index=pd.date_range("2026-03-01", periods=3))
    with patch("yfinance.Ticker") as mock_ticker, \
         patch.object(connector, "_get_cached_response", return_value=None):
        mock_ticker.return_value.history.return_value = mock_hist
        res = connector.fetch_latest_price("WTI_USD")
        assert res["code"] == "WTI_USD"
        assert res["price"] == 75.80
        assert "yfinance" in res["source"]
        assert res["status"] == "FALLBACK"
        assert res["is_free_alternative"] is True

def test_oilpriceapi_bitemporal_vintage_tracking(tmp_path):
    v_file = str(tmp_path / "oilpriceapi_vintages.json")
    record = {
        "code": "RBOB_USD",
        "price": 2.455,
        "as_of": "2026-03-15 12:00:00",
        "created_at": "2026-03-15",
        "source": "OilpriceAPI Dynamic yfinance Fallback (RBOB_USD -> RB=F)"
    }
    
    save_oilpriceapi_vintage_record(record, filepath=v_file)
    assert os.path.exists(v_file)
    
    vintages = get_oilpriceapi_vintages_as_of("2026-03-16", by_code="RBOB_USD", filepath=v_file)
    assert len(vintages) == 1
    assert vintages[0]["code"] == "RBOB_USD"
    assert vintages[0]["price"] == 2.455

    # Check filtering by non-matching code
    empty = get_oilpriceapi_vintages_as_of("2026-03-16", by_code="NG_USD", filepath=v_file)
    assert len(empty) == 0
