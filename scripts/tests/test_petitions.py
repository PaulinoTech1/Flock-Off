"""Tests for scripts/petitions.py: the Petitions page registry.

Petitions are citizen speech listed for context, so the registry's job
is to never misstate one: titles and targets are recorded from the
petition page itself, signature counts carry the date they were read,
and a structurally broken entry must fail the build loudly instead of
shipping a bad card.
"""
import json
import os
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import petitions  # noqa: E402


def _agencies():
    with open(os.path.join(REPO_ROOT, "data", "agencies.json"),
              encoding="utf-8") as f:
        return json.load(f)["agencies"]


def _row(**over):
    row = {
        "slug": "test-petition", "title": "Remove the cameras",
        "url": "https://www.change.org/p/test-petition",
        "platform": "Change.org", "place": "Testville, TS", "agency_id": None,
        "target_text": "City Council", "organizer": None,
        "started": None, "status": "open", "signatures": 10,
        "signatures_as_of": "2026-10-18", "note": "Asks the council to act.",
    }
    row.update(over)
    keys = ("slug", "title", "url", "platform", "place", "agency_id",
            "target_text", "organizer", "started", "status", "signatures",
            "signatures_as_of", "note")
    return tuple(row[k] for k in keys)


class TestPetitionsRegistry(unittest.TestCase):
    def test_registry_resolves_against_dataset(self):
        entries = petitions.build_petition_entries(_agencies())
        self.assertEqual(len(entries), len(petitions.REGISTRY))

    def test_entries_carry_required_fields(self):
        for e in petitions.build_petition_entries(_agencies()):
            self.assertIn(e["status"], petitions.STATUSES)
            self.assertEqual(e["status_label"], petitions.STATUS_LABELS[e["status"]])
            self.assertTrue(e["url"].startswith("https://"))
            self.assertTrue(e["title"])
            self.assertTrue(e["platform"])
            self.assertTrue(e["place"])
            self.assertTrue(e["target_text"])
            self.assertTrue(e["note"])
            if e["signatures"] is not None:
                self.assertRegex(e["signatures_as_of"], r"^\d{4}-\d{2}-\d{2}$")

    def test_linked_agency_joins(self):
        agencies = _agencies()
        aid = agencies[0]["id"]
        saved = petitions.REGISTRY
        try:
            petitions.REGISTRY = [_row(agency_id=aid)]
            entries = petitions.build_petition_entries(agencies)
            self.assertEqual(entries[0]["agency"], agencies[0]["agency"])
        finally:
            petitions.REGISTRY = saved

    def test_unknown_agency_fails_closed(self):
        saved = petitions.REGISTRY
        try:
            petitions.REGISTRY = [_row(agency_id="no-such-agency")]
            with self.assertRaises(ValueError):
                petitions.build_petition_entries(_agencies())
        finally:
            petitions.REGISTRY = saved

    def test_duplicate_slug_fails_closed(self):
        saved = petitions.REGISTRY
        try:
            petitions.REGISTRY = [_row(), _row()]
            with self.assertRaises(ValueError):
                petitions.build_petition_entries([])
        finally:
            petitions.REGISTRY = saved

    def test_non_https_fails_closed(self):
        saved = petitions.REGISTRY
        try:
            petitions.REGISTRY = [_row(url="http://example.com/p")]
            with self.assertRaises(ValueError):
                petitions.build_petition_entries([])
        finally:
            petitions.REGISTRY = saved

    def test_sorted_by_signatures_desc(self):
        saved = petitions.REGISTRY
        try:
            petitions.REGISTRY = [
                _row(slug="small", signatures=5),
                _row(slug="big", signatures=500),
                _row(slug="unknown", signatures=None, signatures_as_of=None),
            ]
            entries = petitions.build_petition_entries([])
            self.assertEqual([e["slug"] for e in entries],
                             ["big", "small", "unknown"])
        finally:
            petitions.REGISTRY = saved


if __name__ == "__main__":
    unittest.main()
