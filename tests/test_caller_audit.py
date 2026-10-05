"""
Production Caller Audit Test Suite (Issue #615)

Verifies that critical mathematical and domain engine modules have non-test production callers:
1. src/metro_nowcast.py -> called by src/locations/runner.py
2. src/volatility_engine.py -> called by src/locations/national/main.py and src/models.py
3. src/locations/specs.py -> called by src/locations/runner.py
4. src/edgeworth_cycle.py -> called by src/locations/cincinnati/regional.py and src/locations/runner.py
5. src/firms_satellite_feed.py -> called by src/feature_engineering.py
"""

import ast
from pathlib import Path
import pytest


def get_production_imports_and_calls(src_dir: Path):
    """Parses all Python files in src/ and returns import targets and referenced modules."""
    module_references = {}
    py_files = [p for p in src_dir.rglob("*.py") if not p.name.startswith("test_")]

    for py_file in py_files:
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except Exception:
            continue

        rel_path = py_file.as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_references.setdefault(alias.name, set()).add(rel_path)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_references.setdefault(node.module, set()).add(rel_path)

    return module_references


def test_production_caller_audit():
    """
    Asserts that the 5 audit target modules are imported and utilized by non-test production files.
    """
    src_dir = Path("src")
    assert src_dir.exists(), "src directory not found"

    refs = get_production_imports_and_calls(src_dir)

    target_modules = {
        "src.metro_nowcast": "Metro nowcasting Kalman filter engine",
        "src.volatility_engine": "Wholesale RBOB volatility distribution engine",
        "src.locations.specs": "Regional market topology specifications",
        "src.edgeworth_cycle": "Edgeworth retail price cycle restoration-hazard model",
        "src.firms_satellite_feed": "NASA FIRMS satellite flaring anomaly connector",
    }

    missing_callers = {}
    for mod, desc in target_modules.items():
        # Find callers excluding the module itself
        mod_file_stem = mod.replace(".", "/")
        callers = [
            caller for caller in refs.get(mod, set())
            if not caller.endswith(f"{mod_file_stem}.py") and not caller.endswith(f"{mod_file_stem}/__init__.py")
        ]
        if not callers:
            # Also check if imported without "src." prefix
            short_mod = mod.replace("src.", "")
            callers = [
                caller for caller in refs.get(short_mod, set())
                if not caller.endswith(f"{mod_file_stem}.py") and not caller.endswith(f"{mod_file_stem}/__init__.py")
            ]

        if not callers:
            missing_callers[mod] = desc

    assert not missing_callers, f"Modules missing production callers in src/: {missing_callers}"
