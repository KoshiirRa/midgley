"""Regression tests for universal uv.lock and requirements.lock packaging (Issue #572)."""

import os
import tomllib

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def test_pyproject_requires_python_311_plus():
    pyproject_path = os.path.join(REPO_ROOT, "pyproject.toml")
    with open(pyproject_path, "rb") as fh:
        data = tomllib.load(fh)
    assert data["project"]["requires-python"].startswith(">=3.11")
    assert len(data["project"]["dependencies"]) >= 15


def test_uv_lock_and_universal_requirements_lock_exist():
    uv_lock_path = os.path.join(REPO_ROOT, "uv.lock")
    req_lock_path = os.path.join(REPO_ROOT, "requirements.lock")
    assert os.path.exists(uv_lock_path), "uv.lock must exist at repository root"
    assert os.path.exists(req_lock_path), "requirements.lock must exist at repository root"

    with open(req_lock_path, "r", encoding="utf-8") as fh:
        content = fh.read()
    assert "--universal" in content, "requirements.lock must be generated with uv pip compile --universal"
    assert "python_full_version" in content, "universal requirements.lock should contain Python version markers"
