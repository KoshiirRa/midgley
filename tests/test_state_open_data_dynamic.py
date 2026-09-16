import pytest
import os
import json
from src.state_open_data import (
    StateEnergyAgencySurveysConnector,
    save_state_surveys_vintage_record,
    get_state_surveys_vintages_as_of,
    UniversalStateOpenDataConnector
)


def test_cec_california_fuel_survey():
    connector = StateEnergyAgencySurveysConnector()
    res = connector.fetch_cec_california_fuel_survey()
    assert isinstance(res, dict)
    assert res["state"] == "CA"
    assert "retail_unleaded_avg" in res
    assert "price_breakdown" in res
    assert "crude_oil_cost" in res["price_breakdown"]
    assert "refining_margin" in res["price_breakdown"]
    assert res["status"] == "SUCCESS"


def test_nyserda_new_york_fuel_survey():
    connector = StateEnergyAgencySurveysConnector()
    res = connector.fetch_nyserda_new_york_fuel_survey()
    assert isinstance(res, dict)
    assert res["state"] == "NY"
    assert "regions" in res
    assert "Statewide" in res["regions"]
    assert "NYC_Metropolitan" in res["regions"]
    assert res["status"] == "SUCCESS"


def test_midwest_biofuel_retail_survey():
    connector = StateEnergyAgencySurveysConnector()
    res = connector.fetch_midwest_biofuel_retail_survey()
    assert isinstance(res, dict)
    assert "e10_unleaded_avg" in res
    assert "e85_flex_fuel_avg" in res
    assert "premium_unleaded_avg" in res
    assert res["status"] == "SUCCESS"


def test_state_surveys_vintage_persistence(tmp_path):
    temp_file = str(tmp_path / "state_surveys_vintages.json")
    record = {
        "state": "CA",
        "retail_unleaded_avg": 5.25
    }
    save_state_surveys_vintage_record("CEC_CA", record, filepath=temp_file)
    assert os.path.exists(temp_file)

    loaded = get_state_surveys_vintages_as_of("CEC_CA", "2099-12-31", filepath=temp_file)
    assert loaded is not None
    assert loaded["retail_unleaded_avg"] == 5.25
