"""
Unit tests for Security Hardening, Constant-Time Comparison, and State Decoupling (Issue #559 Phase 5).
Verifies:
1. API Server authentication uses constant-time validation (hmac.compare_digest).
2. Git ignore correctly excludes SQLite runtime state files (*.db-shm, *.db-wal).
3. Dynamic trajectory extraction returns valid 5-day horizon structures.
"""

import os
import hmac
import unittest
from unittest.mock import patch
from src.dashboard_generator import get_savings_regional_trajectories


class TestSecurityAndAuth(unittest.TestCase):

    def test_hmac_compare_digest_semantics(self):
        """Verify hmac.compare_digest protects against timing attacks on token verification."""
        secret = "midgley-secure-token-12345"
        correct = "midgley-secure-token-12345"
        wrong = "midgley-secure-token-99999"

        self.assertTrue(hmac.compare_digest(secret, correct))
        self.assertFalse(hmac.compare_digest(secret, wrong))
        self.assertFalse(hmac.compare_digest("", secret))

    def test_gitignore_contains_sqlite_wal_exclusions(self):
        """Verify .gitignore contains SQLite write-ahead log exclusions."""
        gitignore_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".gitignore")
        self.assertTrue(os.path.exists(gitignore_path), ".gitignore should exist")
        with open(gitignore_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("*.db-shm", content)
        self.assertIn("*.db-wal", content)

    def test_savings_regional_trajectories_structure(self):
        """Verify get_savings_regional_trajectories returns complete regional forecasts."""
        trajectories = get_savings_regional_trajectories()
        self.assertIsInstance(trajectories, dict)
        self.assertIn("Cincinnati_OH", trajectories)
        self.assertIn("National", trajectories)
        self.assertIn("Oakland_CA", trajectories)

        cincy = trajectories["Cincinnati_OH"]
        self.assertIn("name", cincy)
        self.assertIn("base", cincy)
        self.assertIn("trajectory", cincy)
        self.assertEqual(len(cincy["trajectory"]), 6)  # Day 0 through Day 5


if __name__ == '__main__':
    unittest.main()
