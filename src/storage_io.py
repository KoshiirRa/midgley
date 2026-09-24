"""
Storage I/O Utility (src/storage_io.py)

Provides atomic file write helpers for CSV, JSON, and raw text files.
Guarantees that files are written to a temporary file in the same directory,
synced to disk with fsync, and atomically replaced onto the destination path via
os.replace. This prevents file corruption, 0-byte truncation, and partial writes
during process termination, signal delivery (SIGTERM/SIGKILL), or system interruption.
"""

import os
import json
import tempfile
import logging
from contextlib import contextmanager
from typing import Any, Optional, Dict, Union
import time

try:
    import pandas as pd
except ImportError:
    pd = Any  # type: ignore

try:
    import fcntl
except ImportError:
    fcntl = None  # type: ignore

logger = logging.getLogger(__name__)


@contextmanager
def file_lock(path: Union[str, os.PathLike], timeout: float = 30.0):
    """
    Cross-process advisory file lock context manager using fcntl.flock on POSIX
    with non-blocking retry loops.
    """
    lock_file_path = f"{str(path)}.lock"
    lock_dir = os.path.dirname(os.path.abspath(lock_file_path))
    os.makedirs(lock_dir, exist_ok=True)

    lock_fd = None
    try:
        lock_fd = os.open(lock_file_path, os.O_CREAT | os.O_RDWR)
        start_time = time.time()
        locked = False
        while time.time() - start_time < timeout:
            try:
                try:
                    import fcntl
                    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    locked = True
                    break
                except (ImportError, AttributeError):
                    locked = True
                    break
            except (BlockingIOError, OSError):
                time.sleep(0.05)
        if not locked:
            logger.warning(f"Advisory file lock timed out for {path} after {timeout}s.")
        yield
    finally:
        if lock_fd is not None:
            try:
                try:
                    import fcntl
                    fcntl.flock(lock_fd, fcntl.LOCK_UN)
                except Exception:
                    pass
                os.close(lock_fd)
            except Exception:
                pass



@contextmanager
def atomic_write(
    path: Union[str, os.PathLike],
    mode: str = "w",
    encoding: Optional[str] = "utf-8",
    newline: Optional[str] = None,
    **kwargs
):
    """
    Context manager for atomic file writes.

    Writes to a temporary file in the SAME directory as the destination path,
    flushes and fsyncs the buffer, and atomically swaps it onto the target
    using os.replace().

    Same-directory placement is strictly required because os.replace() is only
    guaranteed to be atomic within a single filesystem.

    Args:
        path: Target file path.
        mode: Open mode (e.g. "w", "wb").
        encoding: File encoding (default "utf-8", None if binary mode).
        newline: Controls how universal newlines work.
        **kwargs: Additional arguments passed to open().
    """
    target_path = os.path.abspath(path)
    directory = os.path.dirname(target_path) or "."
    os.makedirs(directory, exist_ok=True)

    is_binary = "b" in mode
    open_encoding = None if is_binary else encoding

    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".tmp-", suffix=".partial")
    os.close(fd)

    try:
        with open(
            tmp_path,
            mode=mode,
            encoding=open_encoding,
            newline=newline,
            **kwargs
        ) as handle:
            yield handle
            handle.flush()
            os.fsync(handle.fileno())

        # Attempt atomic replace with brief backoff for OS file lock contention (e.g. Windows)
        max_retries = 15
        for attempt in range(max_retries):
            try:
                os.replace(tmp_path, target_path)
                break
            except (PermissionError, OSError) as e:
                if attempt == max_retries - 1:
                    raise
                import time
                time.sleep(0.005 * (attempt + 1))
    except BaseException:
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        raise


def atomic_write_json(
    path: Union[str, os.PathLike],
    data: Any,
    indent: int = 2,
    sort_keys: bool = False,
    ensure_ascii: bool = False,
    **kwargs
) -> None:
    """
    Atomically serializes data as JSON to the destination path.
    """
    with atomic_write(path, mode="w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=indent, sort_keys=sort_keys, ensure_ascii=ensure_ascii, **kwargs)
        handle.write("\n")


def atomic_write_csv(
    path: Union[str, os.PathLike],
    df: pd.DataFrame,
    index: bool = False,
    **kwargs
) -> None:
    """
    Atomically serializes a pandas DataFrame as CSV to the destination path.
    """
    with atomic_write(path, mode="w", encoding="utf-8", newline="") as handle:
        df.to_csv(handle, index=index, **kwargs)
