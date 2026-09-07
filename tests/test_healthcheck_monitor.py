"""
Unit Tests for Healthchecks Cron & Pipeline Monitoring Engine (tests/test_healthcheck_monitor.py)
"""

import os
import unittest
from unittest.mock import patch, MagicMock
import urllib.error

from src.healthcheck_monitor import (
    resolve_healthcheck_url,
    send_healthcheck_ping,
    ping_healthcheck_start,
    ping_healthcheck_success,
    ping_healthcheck_failure,
    is_testing_environment,
)


class TestHealthcheckMonitor(unittest.TestCase):
    def test_resolve_healthcheck_url_from_explicit_arg(self):
        url = resolve_healthcheck_url("https://hc-ping.com/12ab7587-e0ed-40ac-83ad-822f9eb56a3b")
        self.assertEqual(url, "https://hc-ping.com/12ab7587-e0ed-40ac-83ad-822f9eb56a3b")

    def test_resolve_healthcheck_url_from_bare_uuid(self):
        url = resolve_healthcheck_url("12ab7587-e0ed-40ac-83ad-822f9eb56a3b")
        self.assertEqual(url, "https://hc-ping.com/12ab7587-e0ed-40ac-83ad-822f9eb56a3b")

    def test_resolve_healthcheck_url_from_env(self):
        with patch.dict(os.environ, {"HEALTHCHECKS_PING_URL": "https://hc-ping.com/custom-uuid"}):
            url = resolve_healthcheck_url()
            self.assertEqual(url, "https://hc-ping.com/custom-uuid")

    def test_resolve_healthcheck_url_none(self):
        with patch.dict(os.environ, {}, clear=True):
            url = resolve_healthcheck_url()
            self.assertIsNone(url)

    def test_test_environment_suppression(self):
        with patch.dict(os.environ, {"TESTING": "1"}):
            self.assertTrue(is_testing_environment())
            res = send_healthcheck_ping("https://hc-ping.com/test-uuid", state="success")
            self.assertTrue(res)

    @patch("urllib.request.urlopen")
    def test_send_healthcheck_ping_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.getcode.return_value = 200
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        res = send_healthcheck_ping(
            "https://hc-ping.com/test-uuid",
            state="success",
            force_send=True
        )
        self.assertTrue(res)
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.full_url, "https://hc-ping.com/test-uuid")

    @patch("urllib.request.urlopen")
    def test_send_healthcheck_ping_start(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.getcode.return_value = 200
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        res = ping_healthcheck_start("test-uuid", force_send=True)
        self.assertTrue(res)
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.full_url, "https://hc-ping.com/test-uuid/start")

    @patch("urllib.request.urlopen")
    def test_send_healthcheck_ping_fail_with_log(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.getcode.return_value = 200
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        res = ping_healthcheck_failure("test-uuid", log_message="Pipeline failed on missing feature", force_send=True)
        self.assertTrue(res)
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.full_url, "https://hc-ping.com/test-uuid/fail")
        self.assertEqual(req.data, b"Pipeline failed on missing feature")

    @patch("urllib.request.urlopen")
    def test_send_healthcheck_ping_http_error_fail_open(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://hc-ping.com/test-uuid",
            code=500,
            msg="Internal Error",
            hdrs={},
            fp=None
        )
        res = send_healthcheck_ping("test-uuid", state="success", force_send=True)
        self.assertFalse(res)

    @patch("urllib.request.urlopen")
    def test_send_healthcheck_ping_network_exception_fail_open(self, mock_urlopen):
        mock_urlopen.side_effect = TimeoutError("Connection timed out")
        res = send_healthcheck_ping("test-uuid", state="success", force_send=True)
        self.assertFalse(res)


if __name__ == "__main__":
    unittest.main()
