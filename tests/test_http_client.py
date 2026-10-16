"""
Unit Tests for Unified HTTP Client & Session Factory (src/http_client.py)
"""

import pytest
import requests
from unittest.mock import patch, MagicMock
from src.http_client import get_session, get_global_session, http_get, http_post, DEFAULT_USER_AGENT, DEFAULT_TIMEOUT


def test_get_session_configuration():
    session = get_session(user_agent="Custom-Agent/1.0")
    assert session.headers.get("User-Agent") == "Custom-Agent/1.0"
    assert "https://" in session.adapters
    assert "http://" in session.adapters


def test_get_global_session_singleton():
    s1 = get_global_session()
    s2 = get_global_session()
    assert s1 is s2
    assert "Midgley" in s1.headers.get("User-Agent", "")


def test_http_get_wrapper():
    with patch.object(requests.Session, "get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp
        
        resp = http_get("https://api.example.com/data", params={"limit": 10})
        assert resp.status_code == 200
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert args[0] == "https://api.example.com/data"
        assert kwargs["params"] == {"limit": 10}
        assert kwargs["timeout"] == DEFAULT_TIMEOUT


def test_http_post_wrapper():
    with patch.object(requests.Session, "post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_post.return_value = mock_resp
        
        resp = http_post("https://api.example.com/submit", json={"key": "val"})
        assert resp.status_code == 201
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "https://api.example.com/submit"
        assert kwargs["json"] == {"key": "val"}
