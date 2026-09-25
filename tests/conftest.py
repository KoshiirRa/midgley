"""
Global Pytest Fixtures and Sandbox Isolation (tests/conftest.py)
Issue #427, #469: Prevents test artifact pollution in data/prediction_history.csv, databases, and working tree.
"""

import os
import pytest


@pytest.fixture(autouse=True)
def isolate_test_environment(tmp_path, monkeypatch):
    """
    Global autouse fixture that isolates prediction history CSV, test caches,
    databases (security.db, agent_memory.sqlite, lookup_cache.sqlite), and vintages to tmp_path.
    """
    monkeypatch.setenv("TESTING", "1")
    
    # 1. Isolate prediction logger HISTORY_CSV_PATH
    test_csv = tmp_path / "prediction_history.csv"
    try:
        import src.prediction_logger as pred_logger
        monkeypatch.setattr(pred_logger, "HISTORY_CSV_PATH", str(test_csv))
    except (ImportError, AttributeError):
        pass

    # 2. Isolate SQLite databases
    test_sec_db = str(tmp_path / "security.db")
    test_mem_db = str(tmp_path / "agent_memory.sqlite")
    test_cache_db = str(tmp_path / "lookup_cache.sqlite")

    try:
        import src.key_manager as km
        monkeypatch.setattr(km, "DEFAULT_DB_PATH", test_sec_db)
    except (ImportError, AttributeError):
        pass

    try:
        import src.agent_memory as am
        monkeypatch.setattr(am, "DEFAULT_SQLITE_PATH", test_mem_db)
    except (ImportError, AttributeError):
        pass

    try:
        import src.lookup_cache as lc
        monkeypatch.setattr(lc, "DEFAULT_CACHE_DB", test_cache_db)
    except (ImportError, AttributeError):
        pass

    try:
        import src.learning_tracker as lt
        monkeypatch.setattr(lt, "AGENT_MEMORY_DB", test_mem_db)
    except (ImportError, AttributeError):
        pass

    yield tmp_path
