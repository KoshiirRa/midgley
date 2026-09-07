"""
Unit Tests for ArchiveBox Historical News & Event Preservation Engine (tests/test_archive_service.py)
Issue #97
"""

import os
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from src.archive_service import (
    ArchiveBoxClient,
    submit_url_to_archive,
    is_testing_environment,
)


class TestArchiveService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.client = ArchiveBoxClient()
        self.client.ledger_file = os.path.join(self.temp_dir.name, "test_ledger.json")
        self.client.archives_dir = os.path.join(self.temp_dir.name, "archives")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_invalid_url_skipped(self):
        res = self.client.submit_url("not-a-valid-url")
        self.assertEqual(res.get("status"), "SKIPPED")

    def test_local_fallback_snapshot_and_ledger(self):
        with patch.dict(os.environ, {"TEST_ARCHIVE_PERSIST": "1"}):
            res = self.client.submit_url(
                url="https://www.reuters.com/business/energy/test-refinery-outage-2026",
                title="Test Refinery Outage Notice",
                tags=["refinery", "padd1b"],
                content_snapshot="Breaking: Catlettsburg FCCU offline due to unexpected power fluctuation.",
                async_dispatch=False
            )
            self.assertEqual(res.get("status"), "SUCCESS")
            self.assertEqual(res.get("server_status"), "LOCAL_ONLY")
            self.assertTrue(self.client.is_url_archived("https://www.reuters.com/business/energy/test-refinery-outage-2026"))

            # Verify ledger on disk
            self.assertTrue(os.path.exists(self.client.ledger_file))
            with open(self.client.ledger_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data.get("total_archived"), 1)

    def test_archivebox_server_dispatch_mock(self):
        mock_resp = MagicMock()
        mock_resp.getcode.return_value = 200

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value = mock_resp
            with patch.object(self.client, "archivebox_url", "http://dev-vm:8000"):
                with patch("src.archive_service.is_testing_environment", return_value=False):
                    res = self.client.submit_url(
                        url="https://www.reuters.com/business/energy/opec-meeting-september",
                        title="OPEC+ Meeting Statement",
                        async_dispatch=False
                    )
                    self.assertEqual(res.get("status"), "SUCCESS")
                    self.assertEqual(res.get("server_status"), "SUBMITTED_TO_ARCHIVEBOX")

    def test_async_dispatch_returns_immediately(self):
        res = self.client.submit_url(
            url="https://www.eia.gov/petroleum/supply/weekly/",
            title="EIA Weekly Petroleum Report",
            async_dispatch=True
        )
        self.assertEqual(res.get("status"), "QUEUED_ASYNC")


if __name__ == "__main__":
    unittest.main()
