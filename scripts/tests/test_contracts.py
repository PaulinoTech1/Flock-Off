"""Tests for scripts/contracts.py: the Contracts page registry.

The page claims to show the actual contract documents, so the registry
join must be exact: every curated source_key must resolve against the
live dataset, every entry must carry an explicit kind, and a missing
citation must fail loudly (the build calls the same function and exits
nonzero) instead of silently dropping a contract from the page.
"""
import json
import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import contracts  # noqa: E402


def _agencies():
    with open(os.path.join(REPO_ROOT, "data", "agencies.json"),
              encoding="utf-8") as f:
        return json.load(f)["agencies"]


class TestContractsRegistry(unittest.TestCase):
    def test_registry_resolves_against_dataset(self):
        entries = contracts.build_contract_entries(_agencies())
        self.assertEqual(len(entries), len(contracts.REGISTRY))
        self.assertGreater(len(entries), 0)

    def test_entries_carry_required_fields(self):
        for e in contracts.build_contract_entries(_agencies()):
            self.assertIn(e["kind"], contracts.KINDS)
            self.assertEqual(e["kind_label"], contracts.KIND_LABELS[e["kind"]])
            self.assertTrue(e["doc_url"].startswith(("http://", "https://")))
            self.assertTrue(e["doc_title"])
            self.assertTrue(e["doc_note"])
            self.assertTrue(e["agency"])
            # accurate_as_of is the record's last_verified or None;
            # when present it must be an ISO date.
            if e["accurate_as_of"] is not None:
                self.assertRegex(e["accurate_as_of"], r"^\d{4}-\d{2}-\d{2}$")

    def test_registry_has_both_kinds(self):
        kinds = {row[2] for row in contracts.REGISTRY}
        self.assertEqual(kinds, contracts.KINDS)

    def test_missing_agency_fails_closed(self):
        with self.assertRaises(ValueError):
            contracts.build_contract_entries([])

    def test_missing_source_key_fails_closed(self):
        agencies = _agencies()
        target_id, target_key = contracts.REGISTRY[0][0], contracts.REGISTRY[0][1]
        for a in agencies:
            if a["id"] == target_id:
                a["sources"] = [s for s in a["sources"]
                                if s.get("source_key") != target_key]
        with self.assertRaises(ValueError):
            contracts.build_contract_entries(agencies)


if __name__ == "__main__":
    unittest.main()
