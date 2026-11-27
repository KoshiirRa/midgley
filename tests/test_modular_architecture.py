"""Regression tests for modularized API routers, FeatureFamily pipelines, and dashboard components (Issue #562)."""

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from src.api_server import app
from src.dashboard import (
    get_analytics_script,
    get_carto_basemap_url,
    get_model_badge,
    get_multi_agent_sim_badge,
    get_release_badge,
)
from src.dashboard_generator import (
    get_analytics_script as dg_get_analytics_script,
    get_carto_basemap_url as dg_get_carto_basemap_url,
    get_model_badge as dg_get_model_badge,
    get_multi_agent_sim_badge as dg_get_multi_agent_sim_badge,
    get_release_badge as dg_get_release_badge,
)
from src.features import FeaturePipeline, TechnicalMomentumFeatureFamily


def test_api_routers_mounted_and_serving():
    client = TestClient(app)

    r_loc = client.get("/api/v1/locations/resolve", params={"zip_code": "60601"})
    assert r_loc.status_code == 200
    assert r_loc.json()["state"] == "IL"

    r_tax = client.get("/api/v1/tax/lookup", params={"zip": "60601"})
    assert r_tax.status_code == 200
    assert r_tax.json()["tax_breakdown"]["county_municipal_tax"] == 0.140

    r_sched = client.get("/api/v1/tax/schedule")
    assert r_sched.status_code == 200
    assert r_sched.json()["states_count"] == 51


def test_feature_pipeline_technical_family():
    idx = pd.date_range("2026-01-01", periods=40, freq="B")
    rng = np.random.default_rng(7)
    close = 2.30 + np.cumsum(rng.normal(0.0, 0.03, size=len(idx)))
    df = pd.DataFrame(
        {
            "gasoline_rbob": close,
            "wti_crude": close * 30.0,
        },
        index=idx,
    )
    pipeline = FeaturePipeline([TechnicalMomentumFeatureFamily()])
    out = pipeline.run(df.copy())
    assert len(out) == len(df)
    assert "rbob_rsi_14" in out.columns


def test_dashboard_badge_helpers_reexported():
    assert get_release_badge is dg_get_release_badge
    assert get_model_badge is dg_get_model_badge
    assert get_multi_agent_sim_badge is dg_get_multi_agent_sim_badge
    assert get_analytics_script is dg_get_analytics_script
    assert get_carto_basemap_url is dg_get_carto_basemap_url
    assert "Model" in get_model_badge()
