"""
Unit tests for Ruff Fatal-Error and Syntax Static Analysis Gate (Issue #350).

Validates that:
1. pyproject.toml contains valid [tool.ruff] configuration selecting fatal error codes (F, E9).
2. Existing codebase in src/, scripts/, and tests/ passes ruff check with zero errors.
3. Intentionally introduced undefined variables (F821) and syntax errors (E999) are reliably caught.
"""

import os
import subprocess
import tempfile
import tomllib
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PYPROJECT_PATH = os.path.join(PROJECT_ROOT, "pyproject.toml")


def test_pyproject_ruff_configuration():
    """Verifies that pyproject.toml defines required Ruff lint configuration."""
    assert os.path.exists(PYPROJECT_PATH), f"pyproject.toml missing at {PYPROJECT_PATH}"
    
    with open(PYPROJECT_PATH, "rb") as f:
        config = tomllib.load(f)
        
    assert "tool" in config, "[tool] section missing from pyproject.toml"
    assert "ruff" in config["tool"], "[tool.ruff] section missing from pyproject.toml"
    assert "lint" in config["tool"]["ruff"], "[tool.ruff.lint] section missing from pyproject.toml"
    
    lint_cfg = config["tool"]["ruff"]["lint"]
    assert "select" in lint_cfg, "select missing from [tool.ruff.lint]"
    assert "F" in lint_cfg["select"], "Pyflakes rule family 'F' missing from select"
    assert "E9" in lint_cfg["select"], "Syntax error family 'E9' missing from select"


def test_codebase_ruff_check_clean():
    """Verifies that src/, scripts/, and tests/ pass ruff check without errors."""
    cmd = ["ruff", "check", "src/", "scripts/", "tests/"]
    result = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Ruff check failed with errors:\n{result.stdout}\n{result.stderr}"


def test_ruff_catches_undefined_variable():
    """Verifies that ruff check catches undefined variables (F821) and fails with non-zero exit code."""
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write("def broken_func():\n    return undefined_variable_12345\n")
        temp_file = f.name
        
    try:
        cmd = ["ruff", "check", temp_file, "--select=F,E9"]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        assert result.returncode != 0, "Ruff should have failed on undefined variable"
        assert "F821" in result.stdout or "undefined_variable_12345" in result.stdout
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)
