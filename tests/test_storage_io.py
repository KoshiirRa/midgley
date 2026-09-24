"""
Unit tests for Atomic Storage I/O Utility (src/storage_io.py - Issue #424)
"""

import os
import json
import pytest
import pandas as pd
from unittest.mock import patch

from src.storage_io import atomic_write, atomic_write_json, atomic_write_csv


def test_atomic_write_success(tmp_path):
    target = tmp_path / "test_file.txt"
    content = "Hello, atomic world!"
    
    with atomic_write(target) as f:
        f.write(content)
        
    assert target.exists()
    assert target.read_text(encoding="utf-8") == content
    
    # Assert no temporary partial files remain
    tmp_files = list(tmp_path.glob(".tmp-*.partial"))
    assert len(tmp_files) == 0


def test_atomic_write_same_directory_invariant(tmp_path):
    sub_dir = tmp_path / "nested" / "dir"
    target = sub_dir / "nested_file.txt"
    
    with atomic_write(target) as f:
        f.write("nested content")
        
    assert target.exists()
    assert target.read_text(encoding="utf-8") == "nested content"


def test_atomic_write_exception_rollback(tmp_path):
    target = tmp_path / "target_rollback.txt"
    initial_content = "ORIGINAL BYTE CONTENT"
    target.write_text(initial_content, encoding="utf-8")
    
    # Simulate an unhandled exception or crash during write
    with pytest.raises(RuntimeError):
        with atomic_write(target) as f:
            f.write("CORRUPTED PARTIAL CONTENT")
            raise RuntimeError("Pipeline interrupted mid-write!")
            
    # Target file must remain untouched and byte-identical to pre-write contents
    assert target.exists()
    assert target.read_text(encoding="utf-8") == initial_content
    
    # Assert temporary file was cleaned up on exception
    tmp_files = list(tmp_path.glob(".tmp-*.partial"))
    assert len(tmp_files) == 0


def test_atomic_write_json(tmp_path):
    target = tmp_path / "data.json"
    payload = {"status": "ok", "count": 42, "items": ["a", "b", "c"]}
    
    atomic_write_json(target, payload, indent=2)
    
    assert target.exists()
    with open(target, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded == payload


def test_atomic_write_csv(tmp_path):
    target = tmp_path / "data.csv"
    df = pd.DataFrame({
        "forecast_target_date": ["2026-09-24", "2026-09-25"],
        "region": ["National", "Tulsa_OK"],
        "predicted_5d_price": [2.45, 2.30]
    })
    
    atomic_write_csv(target, df, index=False)
    
    assert target.exists()
    loaded_df = pd.read_csv(target)
    assert len(loaded_df) == 2
    assert list(loaded_df["region"]) == ["National", "Tulsa_OK"]
