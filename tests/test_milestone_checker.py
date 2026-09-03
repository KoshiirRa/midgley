"""
Unit Tests for src/milestone_checker.py
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock
from src.milestone_checker import (
    get_milestones,
    close_milestone,
    update_codebase_model_version,
    check_and_promote_model
)

@pytest.fixture
def mock_milestones_data():
    return [
        {
            "number": 3,
            "title": 'Model v1.5 "Houdry"',
            "open_issues": 0,
            "closed_issues": 24,
            "state": "open"
        },
        {
            "number": 4,
            "title": 'Model v1.6 "Ipatieff"',
            "open_issues": 13,
            "closed_issues": 0,
            "state": "open"
        }
    ]

def test_get_milestones():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout=json.dumps([{"number": 3, "title": "Model v1.5"}]),
            returncode=0
        )
        milestones = get_milestones("KoshiirRa/midgley")
        assert len(milestones) == 1
        assert milestones[0]["number"] == 3

def test_close_milestone():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        success = close_milestone("KoshiirRa/midgley", 3)
        assert success is True

def test_check_and_promote_model(mock_milestones_data):
    with patch("src.milestone_checker.get_milestones", return_value=mock_milestones_data), \
         patch("src.milestone_checker.close_milestone", return_value=True), \
         patch("src.milestone_checker.update_codebase_model_version", return_value=["src/__init__.py"]):
        
        promoted = check_and_promote_model("KoshiirRa/midgley")
        assert promoted is not None
        assert promoted["version"] == "v1.5"
        assert promoted["codename"] == "Houdry"
        assert promoted["milestone_number"] == 3

def test_check_and_promote_model_incomplete():
    incomplete_data = [
        {
            "number": 3,
            "title": 'Model v1.5 "Houdry"',
            "open_issues": 5,
            "closed_issues": 19,
            "state": "open"
        }
    ]
    with patch("src.milestone_checker.get_milestones", return_value=incomplete_data):
        promoted = check_and_promote_model("KoshiirRa/midgley")
        assert promoted is None
