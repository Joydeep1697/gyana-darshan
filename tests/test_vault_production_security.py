"""Regression checks for authenticated, tenant-isolated document storage."""

import tempfile
import unittest
from pathlib import Path

from app.database import Database


class VaultDatabaseSecurityTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.directory.name) / "vault.sqlite3")

    def tearDown(self):
        self.directory.cleanup()

    def test_document_owner_is_persisted_and_listing_is_isolated(self):
        first_id = self.database.create_document("first.pdf", 10, "/tmp/first.pdf", owner_id="first-user")
        self.database.create_document("second.pdf", 10, "/tmp/second.pdf", owner_id="second-user")
        first_documents = self.database.list_documents(owner_id="first-user")
        self.assertEqual([document["id"] for document in first_documents], [first_id])
        self.assertEqual(first_documents[0]["owner_id"], "first-user")
        self.assertEqual(self.database.get_document_stats(owner_id="first-user")["total_documents"], 1)
        self.assertEqual(self.database.get_upload_trends(owner_id="second-user")[0]["count"], 1)

    def test_dynamic_update_rejects_untrusted_column_names(self):
        document_id = self.database.create_document("safe.pdf", 10, "/tmp/safe.pdf", owner_id="owner")
        with self.assertRaises(ValueError):
            self.database.update_document(document_id, **{"status = 'indexed' --": "ignored"})
        with self.assertRaises(ValueError):
            self.database.update_document(document_id, owner_id="other-user")
        self.assertEqual(self.database.get_document(document_id)["owner_id"], "owner")

    def test_analytics_and_graph_compatibility_methods_are_available(self):
        document_id = self.database.create_document("safe.pdf", 10, "/tmp/safe.pdf", owner_id="owner")
        self.database.update_document_classification(document_id, "Judgment", "Criminal")
        self.assertEqual(self.database.get_domain_counts()[0]["domain"], "Criminal")
        self.assertEqual(self.database.get_risk_heatmap()[0]["domain"], "Criminal")
        self.assertEqual(self.database.get_upload_trends()[0]["count"], 1)
        self.assertEqual(self.database.get_related_documents(document_id), [])
        self.assertEqual(self.database.get_docs_by_section("302"), [])
        self.assertEqual(self.database.get_section_impact("302"), [])
        self.assertEqual(self.database.check_staleness(), [])
        self.assertEqual(self.database.get_compliance_gaps(gap_type="contradiction"), [])


if __name__ == "__main__":
    unittest.main()
