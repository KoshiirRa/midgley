"""
Global Pytest Fixtures and Sandbox Isolation (tests/conftest.py)
Issue #427, #469: Prevents test artifact pollution in data/prediction_history.csv, databases, and working tree.
"""

import hashlib
import os
from pathlib import Path
import pytest


@pytest.fixture(scope="session", autouse=True)
def verify_data_directory_unpolluted():
    """
    Session fixture that snapshots file checksums of tracked production data
    in data/ and docs/ to verify zero pollution occurs during test execution.
    """
    dirs_to_guard = [Path("data")]
    initial_hashes = {}
    ignored_suffixes = {".tmp", ".sqlite", ".sqlite-shm", ".sqlite-wal", ".sqlite-journal", ".lock", ".csv.lock"}

    for d in dirs_to_guard:
        if d.exists():
            for p in d.rglob("*"):
                if (
                    p.is_file()
                    and p.suffix not in ignored_suffixes
                    and not any(p.name.endswith(sfx) for sfx in ignored_suffixes)
                ):
                    try:
                        initial_hashes[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
                    except Exception:
                        pass

    yield

    mutated_files = []
    for path_str, orig_hash in initial_hashes.items():
        p = Path(path_str)
        if not p.exists():
            mutated_files.append(f"Deleted: {path_str}")
        else:
            try:
                curr_hash = hashlib.sha256(p.read_bytes()).hexdigest()
                if curr_hash != orig_hash:
                    mutated_files.append(f"Modified: {path_str}")
            except Exception:
                pass

    assert not mutated_files, f"Production data files mutated during test run: {mutated_files}"


@pytest.fixture(autouse=True)
def isolate_test_environment(tmp_path, monkeypatch):
    """
    Global autouse fixture that isolates prediction history CSV, test caches,
    databases (security.db, agent_memory.sqlite, lookup_cache.sqlite), and vintages to tmp_path.
    """
    monkeypatch.setenv("TESTING", "1")
    monkeypatch.setenv("MIDGLEY_DATA_DIR", str(tmp_path / "data"))
    
    # 1. Isolate prediction logger HISTORY_CSV_PATH
    test_csv = tmp_path / "prediction_history.csv"
    try:
        import src.prediction_logger as pred_logger
        monkeypatch.setattr(pred_logger, "HISTORY_CSV_PATH", str(test_csv))
    except (ImportError, AttributeError):
        pass

    # 2. Isolate SQLite databases and Turso cloud env
    test_sec_db = str(tmp_path / "security.db")
    test_mem_db = str(tmp_path / "agent_memory.sqlite")
    test_cache_db = str(tmp_path / "lookup_cache.sqlite")
    test_midgley_db = str(tmp_path / "midgley.db")

    monkeypatch.setenv("MIDGLEY_DB_PATH", test_midgley_db)
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("TURSO_AUTH_TOKEN", raising=False)

    try:
        import src.db.client as db_client
        monkeypatch.setattr(db_client, "DEFAULT_SQLITE_PATH", test_midgley_db)
        if hasattr(db_client, "_global_db_client"):
            monkeypatch.setattr(db_client, "_global_db_client", None)
    except (ImportError, AttributeError):
        pass

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

    try:
        import src.zip_geocoding as zg
        monkeypatch.setattr(zg, "TELEMETRY_FILE", str(tmp_path / "unmapped_zip_telemetry.json"))
    except (ImportError, AttributeError):
        pass

    try:
        import src.intraday_event_monitor as iem
        monkeypatch.setattr(iem, "EVALUATED_CACHE_FILE", str(tmp_path / "evaluated_headlines.json"))
        monkeypatch.setattr(iem, "ANOMALY_LOG_FILE", str(tmp_path / "intraday_events.json"))
    except (ImportError, AttributeError):
        pass

    try:
        import src.reachability_adapters as ra
        monkeypatch.setattr(ra, "EVALUATED_HEADLINES_FILE", str(tmp_path / "evaluated_headlines.json"))
    except (ImportError, AttributeError):
        pass

    try:
        import src.wayback_archiver as wa
        monkeypatch.setattr(wa, "CACHE_PATH", str(tmp_path / "wayback_archive_cache.json"))
    except (ImportError, AttributeError):
        pass

    try:
        import src.agent_memory as am
        monkeypatch.setattr(am, "DEFAULT_VINTAGES_PATH", str(tmp_path / "agent_memory_vintages.json"))
    except (ImportError, AttributeError):
        pass

    try:
        import src.benchmark_updater as bu
        monkeypatch.setattr(bu, "BENCHMARK_STORAGE_DIR", str(tmp_path / "data"))
    except (ImportError, AttributeError):
        pass

    try:
        import src.usgs_seismic as u_seis
        monkeypatch.setattr(u_seis, "USGS_SEISMIC_VINTAGE_FILE", str(tmp_path / "usgs_seismic_vintages.json"))
    except (ImportError, AttributeError):
        pass

    try:
        import src.carb_compliance as carb_comp
        monkeypatch.setattr(carb_comp, "CARB_VINTAGE_FILE", str(tmp_path / "carb_compliance_vintages.json"))
    except (ImportError, AttributeError):
        pass

    try:
        import src.noaa_weather as noaa_w
        monkeypatch.setattr(noaa_w, "PIRATEWEATHER_VINTAGES_FILE", str(tmp_path / "pirateweather_vintages.json"))
    except (ImportError, AttributeError):
        pass

    yield tmp_path
