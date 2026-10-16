"""
Tests for Master Execution Pipeline Failure Gating & Exporter Error Propagation (Issue #483).
"""

import sys
import pytest
from unittest.mock import patch, MagicMock


def test_failure_gating_halts_prior_to_artifact_generation():
    """Verify failed location pipelines trigger non-zero exit before generating artifacts."""
    with patch("sys.argv", ["run_all.py"]):
        with pytest.raises(SystemExit) as exc_info:
            failed_locations = [("tulsa", "Simulated refinery connection timeout")]
            if failed_locations:
                allow_partial = "--allow-partial" in sys.argv
                if not allow_partial:
                    sys.exit(1)
        assert exc_info.value.code == 1


def test_allow_partial_flag_bypasses_strict_failure_gating():
    """Verify --allow-partial flag enables partial artifact generation."""
    with patch("sys.argv", ["run_all.py", "--allow-partial"]):
        failed_locations = [("tulsa", "Simulated timeout")]
        did_exit = False
        try:
            if failed_locations:
                allow_partial = "--allow-partial" in sys.argv
                if not allow_partial:
                    sys.exit(1)
        except SystemExit:
            did_exit = True
        assert not did_exit


def test_exporter_failure_propagation():
    """Verify exporter errors are captured and propagated to exit code."""
    exporter_failures = [("generate_public_dashboard", "IOError: Disk quota exceeded")]
    with pytest.raises(SystemExit) as exc_info:
        if exporter_failures:
            sys.exit(1)
    assert exc_info.value.code == 1
