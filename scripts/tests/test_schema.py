"""Schema tests for the Flock-Off dataset (data/agencies.json).

Hard rule: every agency record's `status` must be one of the five values
documented in docs/METHODOLOGY.md ("Statuses"):

    active, pending, cancelled, rejected, expired

Any other value (e.g. the "terminated" value found on ny-tompkins-county-so
in October 2026) silently escapes the terminal-claim evidence bar in
scripts/evidence.py and the tracker's terminal stats in js/tracker.js, so
unknown statuses fail the build instead of drifting into the dataset.

The test also pins the code's terminal set to the documented taxonomy so
the implementation cannot drift from the methodology in either direction.
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import evidence as ev

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PATH = os.path.join(REPO_ROOT, "data", "agencies.json")

# The documented taxonomy. docs/METHODOLOGY.md ("Statuses") is authoritative;
# this set must be updated there first if it ever changes here.
ALLOWED_STATUSES = frozenset({"active", "pending", "cancelled", "rejected", "expired"})


def _agencies():
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data["agencies"] if isinstance(data, dict) else data


class TestStatusSchema(unittest.TestCase):
    def test_every_record_has_a_documented_status(self):
        bad = [(a.get("id"), a.get("status")) for a in _agencies()
               if a.get("status") not in ALLOWED_STATUSES]
        self.assertEqual(bad, [], f"records with undocumented status: {bad}")

    def test_terminal_set_matches_documented_taxonomy(self):
        # evidence.py must recognize exactly the documented terminal statuses:
        # cancelled, rejected, expired. Anything else is a code/methodology
        # drift that corrupts the verification statistics.
        self.assertEqual(ev.TERMINAL_STATUSES,
                         frozenset({"cancelled", "rejected", "expired"}))
        self.assertTrue(ev.TERMINAL_STATUSES <= ALLOWED_STATUSES)

    def test_no_empty_or_missing_status(self):
        bad = [a.get("id") for a in _agencies() if not a.get("status")]
        self.assertEqual(bad, [], f"records missing status: {bad}")


if __name__ == "__main__":
    unittest.main()
