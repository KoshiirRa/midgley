"""
Unit Tests for IPASIS API Gateway Security & Telemetry Accounting (tests/test_ipasis_security.py)
"""

import os
import json
import unittest
from unittest.mock import patch, MagicMock

from src.ipasis_security import IPASISSecurityVerifier, get_ipasis_telemetry, TELEMETRY_FILE, _IP_CACHE


class TestIPASISSecurity(unittest.TestCase):
    def setUp(self):
        _IP_CACHE.clear()
        self.verifier = IPASISSecurityVerifier(daily_allowance=100, timeout=1.0)

    def test_private_ip_bypass(self):
        # Local loopback
        self.assertTrue(self.verifier.is_private_or_local_ip("127.0.0.1"))
        self.assertTrue(self.verifier.is_private_or_local_ip("::1"))
        # RFC 1918 private subnets
        self.assertTrue(self.verifier.is_private_or_local_ip("10.42.42.54"))
        self.assertTrue(self.verifier.is_private_or_local_ip("192.168.1.100"))
        self.assertTrue(self.verifier.is_private_or_local_ip("172.16.0.5"))
        # Test client hostnames
        self.assertTrue(self.verifier.is_private_or_local_ip("testclient"))
        self.assertTrue(self.verifier.is_private_or_local_ip("localhost"))

        # Public IP should not be classified as private
        self.assertFalse(self.verifier.is_private_or_local_ip("8.8.8.8"))
        self.assertFalse(self.verifier.is_private_or_local_ip("87.118.116.103"))

    def test_check_ip_reputation_private_bypass_result(self):
        res = self.verifier.check_ip_reputation("127.0.0.1")
        self.assertFalse(res["is_blocked"])
        self.assertEqual(res["provider"], "IPASIS_Bypass")
        self.assertEqual(res["reason"], "Private/Local IP Bypass")

    @patch("urllib.request.urlopen")
    def test_check_ip_reputation_clean_public_ip(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({
            "ip": "93.184.216.34",
            "privacy": {"Tor": False, "Proxy": False, "VPN": False, "Abuse": False}
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        res = self.verifier.check_ip_reputation("93.184.216.34")
        self.assertFalse(res["is_blocked"])
        self.assertEqual(res["provider"], "IPASIS")
        self.assertEqual(res["reason"], "Clean Origin")

    @patch("urllib.request.urlopen")
    def test_check_ip_reputation_blocked_tor_ip(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({
            "ip": "87.118.116.103",
            "privacy": {"Tor": True, "Proxy": False, "VPN": True, "Abuse": True}
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        res = self.verifier.check_ip_reputation("87.118.116.103")
        self.assertTrue(res["is_blocked"])
        self.assertEqual(res["reason"], "High-Risk Tor/Abuse Origin")

    @patch("urllib.request.urlopen")
    def test_check_ip_reputation_fail_open_fallback(self, mock_urlopen):
        # Simulate network timeout / unreachable service
        mock_urlopen.side_effect = Exception("Connection timed out")

        res = self.verifier.check_ip_reputation("93.184.216.34")
        # Should fail open so legitimate traffic is never blocked by API outages
        self.assertFalse(res["is_blocked"])
        self.assertEqual(res["provider"], "IPASIS_FailOpen")
        self.assertIn("Fail-Open Fallback", res["reason"])

    def test_get_ipasis_telemetry_structure(self):
        tele = get_ipasis_telemetry()
        self.assertIn("daily_requests_used", tele)
        self.assertIn("daily_allowance", tele)
        self.assertIn("quota_remaining", tele)
        self.assertEqual(tele["daily_allowance"], 100)
        self.assertIn("status", tele)
        self.assertIn("private_bypasses", tele)


if __name__ == "__main__":
    unittest.main()
