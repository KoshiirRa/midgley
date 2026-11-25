"""Regression tests for Issue #563: StorageConfig and lazy singleton initialization."""

import os
import subprocess
import sys

from src.storage_config import (
    LazySingletonProxy,
    StorageConfig,
    get_storage_config,
    resolve_data_path,
    resolve_docs_path,
)


def test_storage_config_resolves_env_vars_dynamically(monkeypatch, tmp_path):
    data_dir = str(tmp_path / "custom_data")
    docs_dir = str(tmp_path / "custom_docs")
    monkeypatch.setenv("MIDGLEY_DATA_DIR", data_dir)
    monkeypatch.setenv("MIDGLEY_DOCS_DIR", docs_dir)

    cfg = get_storage_config()
    assert cfg == StorageConfig(data_dir=data_dir, docs_dir=docs_dir)
    assert resolve_data_path("lookup_cache.sqlite") == os.path.join(data_dir, "lookup_cache.sqlite")
    assert resolve_docs_path("index.html") == os.path.join(docs_dir, "index.html")


def test_storage_config_defaults_when_env_unset(monkeypatch):
    monkeypatch.delenv("MIDGLEY_DATA_DIR", raising=False)
    monkeypatch.delenv("MIDGLEY_DOCS_DIR", raising=False)

    cfg = get_storage_config()
    assert cfg.data_dir == "data"
    assert cfg.docs_dir == "docs"


def test_lazy_singleton_proxy_defers_factory_and_supports_reset():
    created = []

    class Dummy:
        def __init__(self):
            created.append(1)
            self.value = 42

    proxy = LazySingletonProxy(Dummy)
    assert proxy.is_initialized is False
    assert len(created) == 0

    assert proxy.value == 42
    assert proxy.is_initialized is True
    assert len(created) == 1

    proxy.reset()
    assert proxy.is_initialized is False
    assert proxy.value == 42
    assert len(created) == 2


def test_module_imports_have_zero_disk_side_effects(tmp_path):
    """Importing lookup_cache, key_manager, and knowledge_graph must not create SQLite files."""
    isolated_data = tmp_path / "isolated_data"
    isolated_data.mkdir()

    env = os.environ.copy()
    env["TESTING"] = "1"
    env["MIDGLEY_DATA_DIR"] = str(isolated_data)

    script = (
        "import src.lookup_cache as lc, src.key_manager as km, src.knowledge_graph as kg; "
        "assert not lc.global_cache.is_initialized; "
        "assert not km.global_key_manager.is_initialized; "
        "assert not kg.kg_engine.is_initialized; "
        "print(\"ZERO_IMPORT_SIDE_EFFECTS_OK\")"
    )
    proc = subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "ZERO_IMPORT_SIDE_EFFECTS_OK" in proc.stdout
    assert list(isolated_data.iterdir()) == []


def test_lazy_singletons_initialize_into_midgley_data_dir_on_first_use(tmp_path):
    """First access lazily creates SQLite DBs inside MIDGLEY_DATA_DIR."""
    isolated_data = tmp_path / "lazy_data"
    isolated_data.mkdir()

    env = os.environ.copy()
    env["TESTING"] = "1"
    env["MIDGLEY_DATA_DIR"] = str(isolated_data)

    script = (
        "import os; "
        "from src.lookup_cache import global_cache, reset_global_cache; "
        "from src.key_manager import global_key_manager, reset_global_key_manager; "
        "assert global_cache.db_path == os.path.join(os.environ[\"MIDGLEY_DATA_DIR\"], \"lookup_cache.sqlite\"); "
        "assert global_key_manager.db_path == os.path.join(os.environ[\"MIDGLEY_DATA_DIR\"], \"security.db\"); "
        "reset_global_cache(); reset_global_key_manager(); "
        "print(\"LAZY_INIT_OK\")"
    )
    proc = subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "LAZY_INIT_OK" in proc.stdout
    assert (isolated_data / "lookup_cache.sqlite").exists()
    assert (isolated_data / "security.db").exists()
