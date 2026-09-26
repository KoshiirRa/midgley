"""
Unit Tests for Packaging, Dependency Alignment & Installation Extras (tests/test_packaging_and_extras.py)
Validates Issue #346 and Issue #338.
"""

from __future__ import annotations

import os
import re
import tomllib
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PYPROJECT_PATH = os.path.join(PROJECT_ROOT, "pyproject.toml")
REQUIREMENTS_PATH = os.path.join(PROJECT_ROOT, "requirements.txt")


def test_pyproject_toml_exists_and_valid():
    """Validates that pyproject.toml exists and parses as valid TOML."""
    assert os.path.exists(PYPROJECT_PATH), "pyproject.toml not found in repository root"
    with open(PYPROJECT_PATH, "rb") as f:
        data = tomllib.load(f)

    assert "project" in data
    assert data["project"]["name"] == "midgley"
    assert "dependencies" in data["project"]
    assert "optional-dependencies" in data["project"]


def test_pyproject_dependencies_alignment():
    """Validates that pyproject.toml contains essential runtime dependencies matching requirements.txt."""
    with open(PYPROJECT_PATH, "rb") as f:
        data = tomllib.load(f)

    project_deps = [re.split(r"[><=~]", dep)[0].strip().lower() for dep in data["project"]["dependencies"]]

    essential_packages = [
        "pandas",
        "numpy",
        "scikit-learn",
        "xgboost",
        "yfinance",
        "google-genai",
        "requests",
        "feedparser",
        "fastapi",
        "uvicorn",
        "httpx",
        "py-gasbuddy",
        "networkx",
        "scipy",
        "python-dotenv",
        "pydantic",
        "beautifulsoup4",
        "defusedxml",
    ]

    for pkg in essential_packages:
        assert pkg in project_deps, f"Essential package '{pkg}' missing from pyproject.toml dependencies"


def test_pyproject_optional_extras():
    """Validates that modular extras are defined in pyproject.toml."""
    with open(PYPROJECT_PATH, "rb") as f:
        data = tomllib.load(f)

    extras = data["project"]["optional-dependencies"]
    expected_extras = ["api", "mcp", "feature-store", "research", "dev", "all"]

    for extra in expected_extras:
        assert extra in extras, f"Optional extra '{extra}' missing from pyproject.toml"
        assert len(extras[extra]) > 0, f"Optional extra '{extra}' is empty"


def test_version_discovery_and_semver():
    """Validates dynamic version discovery from src.version."""
    from src.version import get_version, get_model_version

    ver = get_version()
    assert re.match(r"^\d+\.\d+\.\d+", ver), f"Discovered version '{ver}' is not valid semver"

    model_ver = get_model_version()
    assert model_ver, "Model version string should not be empty"


def test_pyproject_setuptools_package_discovery():
    """Validates that setuptools is configured for proper src package discovery and asset packaging (Issue #460)."""
    with open(PYPROJECT_PATH, "rb") as f:
        data = tomllib.load(f)

    assert "tool" in data and "setuptools" in data["tool"]
    st = data["tool"]["setuptools"]
    assert "packages" in st and "find" in st["packages"]
    assert st["packages"]["find"].get("where") == ["."]
    assert "src*" in st["packages"]["find"].get("include", [])
    assert "package-data" in st


def test_core_module_importability():
    """Smoke test validating that core advertised modules import cleanly."""
    import src.version
    import src.models
    import src.prediction_logger
    import src.event_analyzer
    import src.api_server
    import src.mcp_server

    assert hasattr(src.version, "get_version")
    assert hasattr(src.models, "train_and_compare_models")
    assert hasattr(src.models, "build_stacking_ensemble_pipeline")
    assert hasattr(src.prediction_logger, "log_predictions")
    assert hasattr(src.event_analyzer, "extract_event_features_llm")
    assert hasattr(src.api_server, "app")
    assert hasattr(src.mcp_server, "app")



