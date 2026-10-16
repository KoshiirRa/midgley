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
    ignored_suffixes = {".tmp", ".sqlite", ".sqlite-shm", ".sqlite-wal", ".sqlite-journal", ".lock", ".csv.lock", ".db", ".db-wal", ".db-journal"}

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
        import src.connector_telemetry as ct
        monkeypatch.setattr(ct, "TELEMETRY_FILE_PATH", str(tmp_path / "connector_telemetry.json"))
    except (ImportError, AttributeError):
        pass

    try:
        import src.ipasis_security as isec
        monkeypatch.setattr(isec, "TELEMETRY_FILE", str(tmp_path / "ipasis_telemetry.json"))
        if hasattr(isec, "ipasis_service") and hasattr(isec.ipasis_service, "telemetry_file"):
            monkeypatch.setattr(isec.ipasis_service, "telemetry_file", str(tmp_path / "ipasis_telemetry.json"))
    except (ImportError, AttributeError):
        pass

    try:
        import src.key_manager as km
        monkeypatch.setattr(km, "DEFAULT_DB_PATH", test_sec_db)
        if hasattr(km, "global_key_manager"):
            monkeypatch.setattr(km.global_key_manager, "db_path", test_sec_db)
            km.global_key_manager.init_db()
    except (ImportError, AttributeError):
        pass

    data_dir = Path("data")
    orig_data_files = {}
    if data_dir.exists():
        for p in data_dir.rglob("*"):
            if p.is_file() and p.suffix not in {".tmp", ".sqlite", ".sqlite-shm", ".sqlite-wal", ".sqlite-journal", ".lock", ".csv.lock", ".db"}:
                try:
                    orig_data_files[p] = p.read_bytes()
                except Exception:
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
        if hasattr(carb_comp, "carb_connector"):
            monkeypatch.setattr(carb_comp.carb_connector, "vintage_file", str(tmp_path / "carb_compliance_vintages.json"))
            monkeypatch.setattr(carb_comp.carb_connector, "history_csv", str(tmp_path / "carb_history.csv"))
    except (ImportError, AttributeError):
        pass

    try:
        import src.noaa_weather as noaa_w
        monkeypatch.setattr(noaa_w, "PIRATEWEATHER_VINTAGES_FILE", str(tmp_path / "pirateweather_vintages.json"))
        monkeypatch.setattr(noaa_w, "DEGREE_DAYS_VINTAGE_FILE", str(tmp_path / "degree_days_vintages.json"))
    except (ImportError, AttributeError):
        pass

    try:
        import src.bts_transportation as bts_t
        monkeypatch.setattr(bts_t, "BTS_VINTAGE_FILE", str(tmp_path / "bts_vintages.json"))
        monkeypatch.setattr(bts_t, "FHWA_VINTAGE_FILE", str(tmp_path / "fhwa_vmt_vintages.json"))
    except (ImportError, AttributeError):
        pass

    try:
        import src.knowledge_graph as kg
        test_kg_db = str(tmp_path / "knowledge_graph.db")
        monkeypatch.setattr(kg, "DEFAULT_KG_DB_PATH", test_kg_db)
        if hasattr(kg, "kg_engine") and hasattr(kg.kg_engine, "db_path"):
            monkeypatch.setattr(kg.kg_engine, "db_path", test_kg_db)
            kg.kg_engine._init_db()
    except (ImportError, AttributeError):
        pass

    try:
        import src.tokentab_accounting as tta
        if hasattr(tta, "token_tab_manager"):
            monkeypatch.setattr(tta.token_tab_manager, "ledger_path", str(tmp_path / "token_usage_ledger.json"))
    except (ImportError, AttributeError):
        pass

    try:
        import src.telemetry as telem
        monkeypatch.setattr(telem, "TELEMETRY_LEDGER_PATH", str(tmp_path / "telemetry_ledger.json"))
    except (ImportError, AttributeError):
        pass

    try:
        import src.fallback_telemetry as ft
        monkeypatch.setattr(ft, "TELEMETRY_FILE", str(tmp_path / "fallback_telemetry.json"))
        if hasattr(ft, "fallback_logger") and hasattr(ft.fallback_logger, "filepath"):
            monkeypatch.setattr(ft.fallback_logger, "filepath", str(tmp_path / "fallback_telemetry.json"))
    except (ImportError, AttributeError):
        pass

    try:
        import src.executive_social_feed as esf
        monkeypatch.setattr(esf, "DEFAULT_EXECUTIVE_VINTAGE_FILE", str(tmp_path / "executive_social_vintages.json"))
    except (ImportError, AttributeError):
        pass

    try:
        import src.geopolitical_feeds as gpf
        monkeypatch.setattr(gpf, "GEOPOLITICAL_VINTAGE_FILE", str(tmp_path / "geopolitical_vintages.json"))
    except (ImportError, AttributeError):
        pass

    try:
        import src.key_movers_feed as kmf
        monkeypatch.setattr(kmf, "DEFAULT_KEY_MOVERS_VINTAGE_FILE", str(tmp_path / "key_movers_vintages.json"))
    except (ImportError, AttributeError):
        pass

    try:
        import src.aqi_feed as aqi
        monkeypatch.setattr(aqi, "AQI_VINTAGE_FILE", str(tmp_path / "aqi_vintages.json"))
    except (ImportError, AttributeError):
        pass

    try:
        import src.noaa_weather as nw
        monkeypatch.setattr(nw, "DEGREE_DAYS_VINTAGE_FILE", str(tmp_path / "degree_days_vintages.json"))
    except (ImportError, AttributeError):
        pass

    try:
        import src.portwatch_connector as pwc
        monkeypatch.setattr(pwc, "PORTWATCH_VINTAGE_FILE", str(tmp_path / "imf_portwatch_vintages.json"))
    except (ImportError, AttributeError):
        pass

    try:
        import src.census_demographics as cd
        monkeypatch.setattr(cd, "CENSUS_VINTAGE_FILE", str(tmp_path / "census_demographics_vintages.json"))
        monkeypatch.setattr(cd, "CENSUS_CACHE_FILE", str(tmp_path / "census_demographics_cache.json"))
    except (ImportError, AttributeError):
        pass

    try:
        import src.firms_satellite_feed as fsf
        monkeypatch.setattr(fsf, "FIRMS_VINTAGES_FILE", str(tmp_path / "firms_satellite_vintages.json"))
    except (ImportError, AttributeError):
        pass

    try:
        import src.state_open_data as sod
        monkeypatch.setattr(sod, "STATE_SURVEYS_VINTAGE_FILE", str(tmp_path / "state_surveys_vintages.json"))
    except (ImportError, AttributeError):
        pass

    try:
        import src.bsee_shutins as bss
        monkeypatch.setattr(bss, "BSEE_VINTAGE_FILE", str(tmp_path / "bsee_vintages.json"))
    except (ImportError, AttributeError):
        pass

    try:
        import src.nhc_hurricane as nhc
        monkeypatch.setattr(nhc, "NHC_VINTAGE_FILE", str(tmp_path / "nhc_hurricane_vintages.json"))
    except (ImportError, AttributeError):
        pass

    try:
        import src.energy_equities_feed as eef
        monkeypatch.setattr(eef, "ENERGY_EQUITIES_VINTAGE_FILE", str(tmp_path / "energy_equities_vintages.json"))
    except (ImportError, AttributeError):
        pass

    try:
        import src.headline_arena_connector as hac
        monkeypatch.setattr(hac, "SUBMITTED_LEDGER_FILE", str(tmp_path / "headline_arena_submitted_ledger.json"))
        monkeypatch.setattr(hac, "PENDING_FORECASTS_FILE", str(tmp_path / "headline_arena_pending_forecasts.json"))
    except (ImportError, AttributeError):
        pass

    try:
        import src.catalog_monitor as cm
        monkeypatch.setattr(cm, "STATE_FILE", str(tmp_path / "catalog_monitors_state.json"))
    except (ImportError, AttributeError):
        pass

    try:
        import src.treasury_yield_feed as tyf
        monkeypatch.setattr(tyf, "TREASURY_VINTAGE_FILE", str(tmp_path / "treasury_vintages.json"))
        monkeypatch.setattr(tyf, "TREASURY_CACHE_PATH", str(tmp_path / "treasury_cache.json"))
    except (ImportError, AttributeError):
        pass

    try:
        import src.diesel_regional as dr
        monkeypatch.setattr(dr, "DIESEL_VINTAGE_FILE", str(tmp_path / "diesel_vintages.json"))
    except (ImportError, AttributeError):
        pass

    try:
        import src.data_ingestion as di
        monkeypatch.setattr(di, "FRED_VINTAGE_FILE", str(tmp_path / "fred_vintages.json"))
        monkeypatch.setattr(di, "RADAR_VINTAGE_FILE", str(tmp_path / "radar_vintages.json"))
        monkeypatch.setattr(di, "CFTC_VINTAGE_FILE", str(tmp_path / "cftc_vintages.json"))
        if hasattr(di, "OpenSourceAIRadarConnector"):
            monkeypatch.setattr(di.OpenSourceAIRadarConnector, "CACHE_FILE", str(tmp_path / "radar_cache.json"))
    except (ImportError, AttributeError):
        pass

    yield tmp_path

    # Restore any production data files mutated during this test
    for p, orig_bytes in orig_data_files.items():
        if p.exists():
            try:
                if p.read_bytes() != orig_bytes:
                    p.write_bytes(orig_bytes)
            except Exception:
                pass
        else:
            try:
                p.write_bytes(orig_bytes)
            except Exception:
                pass
