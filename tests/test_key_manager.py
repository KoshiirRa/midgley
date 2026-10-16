"""
Unit test suite for SQLite KeyManager, Method A CLI (scripts/manage_keys.py),
and Access Control Engine (src/key_manager.py).
"""

import os
import sys
import tempfile
import unittest

from src.key_manager import KeyManager


class TestKeyManager(unittest.TestCase):

    def setUp(self):
        self.tmp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp_file.name
        self.tmp_file.close()
        self.km = KeyManager(db_path=self.db_path)

    def tearDown(self):
        try:
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
        except Exception:
            pass

    def test_init_db(self):
        """Verifies SQLite tables and indices are created cleanly."""
        self.assertTrue(os.path.exists(self.db_path))
        keys = self.km.list_keys()
        self.assertEqual(len(keys), 0)

    def test_create_and_verify_key(self):
        """Verifies API key creation, plaintext token generation, and PBKDF2 verification."""
        res = self.km.create_key(
            user_id="alice",
            tier="privileged",
            rate_limit_rpm=30,
            environment="prod"
        )
        self.assertEqual(res["user_id"], "alice")
        self.assertEqual(res["tier"], "privileged")
        self.assertEqual(res["environment"], "prod")
        self.assertEqual(res["rate_limit_rpm"], 30)
        self.assertTrue(res["token"].startswith("mg_prod_"))

        # Verify key
        is_valid, key_info, err = self.km.verify_key(res["token"])
        self.assertTrue(is_valid)
        self.assertIsNotNone(key_info)
        self.assertIsNone(err)
        self.assertEqual(key_info["user_id"], "alice")
        self.assertEqual(key_info["tier"], "privileged")
        self.assertEqual(key_info["rate_limit_rpm"], 30)

    def test_basic_tier_key(self):
        """Verifies basic tier key provisioning."""
        res = self.km.create_key(
            user_id="bob",
            tier="basic",
            rate_limit_rpm=30,
            environment="dev"
        )
        self.assertEqual(res["tier"], "basic")
        self.assertTrue(res["token"].startswith("mg_dev_"))

        is_valid, key_info, _ = self.km.verify_key(res["token"])
        self.assertTrue(is_valid)
        self.assertEqual(key_info["tier"], "basic")

    def test_invalid_token(self):
        """Verifies verification failure for bogus token strings."""
        is_valid, key_info, err = self.km.verify_key("shorttoken")
        self.assertFalse(is_valid)
        self.assertIsNone(key_info)
        self.assertIn("invalid", err.lower())

        is_valid, key_info, err = self.km.verify_key("mg_dev_nonexistent_1234567890")
        self.assertFalse(is_valid)
        self.assertIsNone(key_info)
        self.assertIn("not found", err.lower())

    def test_revocation(self):
        """Verifies revoking an API key prevents authentication."""
        res = self.km.create_key(user_id="charlie", environment="dev")
        prefix = res["key_prefix"]

        is_valid, _, _ = self.km.verify_key(res["token"])
        self.assertTrue(is_valid)

        # Revoke key
        success = self.km.revoke_key(prefix)
        self.assertTrue(success)

        is_valid, key_info, err = self.km.verify_key(res["token"])
        self.assertFalse(is_valid)
        self.assertIsNone(key_info)
        self.assertIn("revoked", err)

    def test_rate_limiting(self):
        """Verifies 30 RPM rate limiting sliding-window enforcement."""
        res = self.km.create_key(user_id="dave", rate_limit_rpm=5)
        prefix = res["key_prefix"]

        # Make 5 allowed requests
        for _ in range(5):
            allowed, retry_after, remaining, reset_ts = self.km.check_rate_limit(prefix, rate_limit_rpm=5)
            self.assertTrue(allowed)
            self.assertEqual(retry_after, 0)

        # 6th request should be rate-limited (allowed=False)
        allowed, retry_after, remaining, reset_ts = self.km.check_rate_limit(prefix, rate_limit_rpm=5)
        self.assertFalse(allowed)
        self.assertGreater(retry_after, 0)

    def test_list_keys_environment_filter(self):
        """Verifies key listing and filtering by environment."""
        self.km.create_key(user_id="u1", environment="dev")
        self.km.create_key(user_id="u2", environment="prod")
        self.km.create_key(user_id="u3", environment="prod")

        dev_keys = self.km.list_keys(environment="dev")
        prod_keys = self.km.list_keys(environment="prod")
        all_keys = self.km.list_keys()

        self.assertEqual(len(dev_keys), 1)
        self.assertEqual(len(prod_keys), 2)
        self.assertEqual(len(all_keys), 3)

    def test_concurrent_rate_limiting(self):
        """Verifies multi-threaded concurrent rate limiting requests never trigger UNIQUE constraint race conditions (Issue #329)."""
        import concurrent.futures

        res = self.km.create_key(user_id="concurrent_user", rate_limit_rpm=50)
        prefix = res["key_prefix"]

        def send_req(_):
            return self.km.check_rate_limit(prefix, rate_limit_rpm=50)

        # Fire 25 concurrent threads simultaneously
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(send_req, range(25)))

        # All 25 should succeed without sqlite3.IntegrityError
        for allowed, retry_after, remaining, reset_ts in results:
            self.assertTrue(allowed)
            self.assertEqual(retry_after, 0)

        # Inspect recorded count in SQLite
        with self.km._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT request_count FROM rate_limits WHERE key_prefix = ?", (prefix,))
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["request_count"], 25)

    def test_secret_redaction_patterns(self):
        """Verifies healthcheck ping URLs, Discord webhooks, and JWT tokens are masked (Issue #614 T-27)."""
        from src.key_manager import redact_secrets
        raw_msg = (
            "Ping sent to https://hc-ping.com/abc12345-6789-abcd-ef01-23456789abcd "
            "and webhook https://discord.com/api/webhooks/1234567890/tokenABC_123-xyz "
            "with token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.doNotLeakThisToken123456"
        )
        redacted = redact_secrets(raw_msg)
        self.assertNotIn("hc-ping.com/abc12345", redacted)
        self.assertNotIn("discord.com/api/webhooks", redacted)
        self.assertNotIn("eyJhbGci", redacted)
        self.assertIn("[REDACTED]", redacted)

    def test_redacting_logging_filter(self):
        """Verifies RedactingLoggingFilter intercepts and redacts records."""
        import logging
        from src.key_manager import RedactingLoggingFilter
        filt = RedactingLoggingFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname=__file__, lineno=1,
            msg="Notifying https://hc-ping.com/deadbeef-1234-5678-9abc-def012345678",
            args=(), exc_info=None
        )
        self.assertTrue(filt.filter(record))
        self.assertNotIn("deadbeef", record.msg)
        self.assertIn("[REDACTED]", record.msg)

    def test_verification_cache_hit_and_invalidation(self):
        """Verifies 60s in-memory token verification caching and revocation invalidation (Issue #614 T-26)."""
        res = self.km.create_key(user_id="cached_user", environment="dev")
        token = res["token"]
        prefix = res["key_prefix"]

        # First verify fills cache
        is_valid, key_info, _ = self.km.verify_key(token)
        self.assertTrue(is_valid)
        self.assertEqual(len(self.km._verification_cache), 1)

        # Second verify hits cache
        is_valid2, key_info2, _ = self.km.verify_key(token)
        self.assertTrue(is_valid2)
        self.assertEqual(key_info["key_prefix"], key_info2["key_prefix"])

        # Revoking clears cache
        self.km.revoke_key(prefix)
        self.assertEqual(len(self.km._verification_cache), 0)

        # Subsequent verify fails
        is_valid3, _, err = self.km.verify_key(token)
        self.assertFalse(is_valid3)
        self.assertIn("revoked", err)


if __name__ == "__main__":
    unittest.main()
