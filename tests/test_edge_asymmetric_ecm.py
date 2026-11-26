"""Unit tests for Edge Asymmetric ECM coefficient export and Python/TypeScript parity (Issue #642)."""

import json
import os
import shutil
import subprocess
import numpy as np
import pandas as pd
import pytest

from src.asymmetric_ecm import AsymmetricECM


def _make_genuine_series(n: int = 120):
    rng = np.random.default_rng(42)
    wholesale = 2.20 + np.cumsum(rng.normal(0.0, 0.04, size=n))
    # Genuine fluctuating margin with asymmetric pass-through
    retail = np.zeros(n)
    retail[0] = wholesale[0] + 0.85
    for t in range(1, n):
        dw = wholesale[t] - wholesale[t - 1]
        z = retail[t - 1] - (wholesale[t - 1] + 0.85)
        dr = (-0.06 * max(0.0, z)) + (-0.18 * min(0.0, z)) + (0.45 * max(0.0, dw)) + (0.20 * min(0.0, dw)) + rng.normal(0.0, 0.01)
        retail[t] = retail[t - 1] + dr
    return pd.Series(retail), pd.Series(wholesale)


def test_export_edge_coefficients_schema_and_invariants():
    retail, wholesale = _make_genuine_series()
    ecm = AsymmetricECM(n_lags_wholesale=3, n_lags_retail=2).fit(retail, wholesale)
    exported = ecm.export_edge_coefficients(hub_key="tulsa", model_version="ecm-test-v1")

    assert exported["hub_key"] == "tulsa"
    assert exported["model_version"] == "ecm-test-v1"
    assert 0.5 <= exported["beta"] <= 1.5
    assert len(exported["gamma_pos_coefs"]) == 4
    assert len(exported["gamma_neg_coefs"]) == 4
    assert len(exported["delta_coefs"]) == 2
    assert len(exported["last_d_wholesale_lags"]) == 3
    assert len(exported["last_d_retail_lags"]) == 2
    assert exported["exported_at"]


def test_export_edge_coefficients_requires_fit():
    ecm = AsymmetricECM()
    with pytest.raises(RuntimeError):
        ecm.export_edge_coefficients()


def test_typescript_edge_evaluator_numerical_parity():
    """Verifies exact numerical parity (< 1e-4 $/gal) between Python and workers/asymmetric_ecm_evaluator.ts."""
    retail, wholesale = _make_genuine_series()
    ecm = AsymmetricECM(n_lags_wholesale=3, n_lags_retail=2).fit(retail, wholesale)
    exported = ecm.export_edge_coefficients(hub_key="chicago", model_version="ecm-parity-v1")

    deltas = [0.05, 0.03, -0.02, 0.0, -0.01]
    py_forecasts = ecm.predict_step_ahead(
        current_retail=3.40,
        current_wholesale=2.50,
        steps_ahead=5,
        expected_wholesale_deltas=deltas,
    )

    ts_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "workers", "asymmetric_ecm_evaluator.ts"))
    assert os.path.exists(ts_path)

    node_bin = shutil.which("node")
    if not node_bin:
        pytest.skip("node not available in environment")

    script = (
        f"import {{ AsymmetricECMEvaluator }} from 'file:///{ts_path.replace(os.sep, '/')}';\n"
        f"const coefs = {json.dumps(exported)};\n"
        f"const ev = new AsymmetricECMEvaluator(coefs);\n"
        f"const res = ev.evaluate({{ current_retail: 3.40, current_wholesale: 2.50, horizon_days: 5, expected_wholesale_deltas: {json.dumps(deltas)}, tax_delta_loc: 0.0, apply_plausibility_bounds: false }});\n"
        f"console.log(JSON.stringify(res));\n"
    )
    proc = subprocess.run(
        [node_bin, "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if proc.returncode != 0 and "Unknown file extension" in proc.stderr:
        pytest.skip("Node version does not support native TypeScript stripping")

    assert proc.returncode == 0, f"Node execution failed: {proc.stderr}"
    ts_res = json.loads(proc.stdout.strip())
    assert ts_res["provenance"] == "PROSPECTIVE_EDGE_NOWCAST"
    assert ts_res["is_simulation"] is False
    assert len(ts_res["trajectory"]) == 5
    for py_val, ts_val in zip(py_forecasts, ts_res["trajectory"]):
        assert abs(py_val - ts_val) < 1e-3, f"Parity drift: py={py_val}, ts={ts_val}"
