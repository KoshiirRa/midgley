"""
Centralized Storage Directory Configuration & Lazy Singleton Proxy (Issue #563).

Resolves base data and docs directories dynamically from MIDGLEY_DATA_DIR and
MIDGLEY_DOCS_DIR environment variables, and provides a thread-safe lazy proxy
so module-level singletons do not open SQLite connections or create disk files
at import time.
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from typing import Any, Callable, Generic, Optional, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class StorageConfig:
    """Resolved storage directory paths for Midgley runtime and tests."""

    data_dir: str = "data"
    docs_dir: str = "docs"

    def data_path(self, *parts: str) -> str:
        """Joins path segments under the configured data directory."""
        return os.path.join(self.data_dir, *parts)

    def docs_path(self, *parts: str) -> str:
        """Joins path segments under the configured docs directory."""
        return os.path.join(self.docs_dir, *parts)


def get_storage_config() -> StorageConfig:
    """
    Returns a StorageConfig resolved dynamically from environment variables.
    Defaults to relative ``data`` and ``docs`` directories when unset.
    """
    data_dir = os.environ.get("MIDGLEY_DATA_DIR") or "data"
    docs_dir = os.environ.get("MIDGLEY_DOCS_DIR") or "docs"
    return StorageConfig(data_dir=data_dir, docs_dir=docs_dir)


def resolve_data_path(*parts: str) -> str:
    """Convenience helper resolving a path under MIDGLEY_DATA_DIR."""
    return get_storage_config().data_path(*parts)


def resolve_docs_path(*parts: str) -> str:
    """Convenience helper resolving a path under MIDGLEY_DOCS_DIR."""
    return get_storage_config().docs_path(*parts)


class LazySingletonProxy(Generic[T]):
    """
    Thread-safe lazy proxy that defers instantiating ``factory()`` until first
    attribute access. Eliminates import-time database connections and file I/O
    while preserving full backwards compatibility for module-level singletons.
    """

    def __init__(self, factory: Callable[[], T]) -> None:
        object.__setattr__(self, "_factory", factory)
        object.__setattr__(self, "_instance", None)
        object.__setattr__(self, "_lock", threading.RLock())

    @property
    def is_initialized(self) -> bool:
        return object.__getattribute__(self, "_instance") is not None

    def get_instance(self) -> T:
        inst = object.__getattribute__(self, "_instance")
        if inst is None:
            lock = object.__getattribute__(self, "_lock")
            with lock:
                inst = object.__getattribute__(self, "_instance")
                if inst is None:
                    factory = object.__getattribute__(self, "_factory")
                    inst = factory()
                    object.__setattr__(self, "_instance", inst)
        return inst

    def reset(self, instance: Optional[T] = None) -> None:
        """Resets or injects the underlying singleton instance (useful in tests)."""
        lock = object.__getattribute__(self, "_lock")
        with lock:
            object.__setattr__(self, "_instance", instance)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.get_instance(), name)

    def __setattr__(self, name: str, value: Any) -> None:
        setattr(self.get_instance(), name, value)

    def __repr__(self) -> str:
        inst = object.__getattribute__(self, "_instance")
        if inst is None:
            factory = object.__getattribute__(self, "_factory")
            return f"<LazySingletonProxy({getattr(factory, '__name__', repr(factory))}) [uninitialized]>"
        return repr(inst)
