"""Schema tests for the Flock-Off dataset (data/agencies.json).

Hard rule: every agency record's `status` must be one of the five values
documented in docs/METHODOLOGY.md ("Statuses"):

    active, pending, cancelled, rejected, expired

Any other value (e.g. the "terminated" value found on ny-tompkins-county-so
in October 2026) silently escapes the terminal-claim evidence bar in
scripts/evidence.py and the tracker's terminal stats in js/tracker.js, so
unknown statuses fail the build instead of drifting into the dataset.

The test also pins the code's terminal set to the documented taxonomy so
the implementation cannot drift from the methodology in either direction,
cross-checks every JS-side copy of the taxonomy against the canonical
Python set, and validates date-field formats (unescaped dates rendered via
innerHTML would be a stored-XSS vector).
"""
import datetime
import json
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import evidence as ev

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PATH = os.path.join(REPO_ROOT, "data", "agencies.json")

# The documented taxonomy. docs/METHODOLOGY.md ("Statuses") is authoritative;
# this set must be updated there first if it ever changes here.
ALLOWED_STATUSES = frozenset({"active", "pending", "cancelled", "rejected", "expired"})

DATE_FIELDS = ("renewal_date", "contract_start", "contract_end",
               "decision_date", "last_verified")
# Full YYYY-MM-DD preferred; YYYY-MM and YYYY accepted where only coarser
# precision is known (contracts are often reported by month or year).
# Anything else is rejected: unparseable dates break renewal sorting and
# the pressure-window math.
DATE_RE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")


def _agencies():
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data["agencies"] if isinstance(data, dict) else data


def _js_status_literals(path, pattern, keys=False):
    """Extract status literals from a JS `new Set([...])` or label map.

    keys=True extracts unquoted object keys (`active: "Active"`); the
    default extracts quoted string literals (`"active"`).
    """
    src = open(path, encoding="utf-8").read()
    m = re.search(pattern, src, re.S)
    if not m:
        raise AssertionError(f"status literal block not found in {path}")
    if keys:
        return set(re.findall(r"^\s*([a-z_]+)\s*:", m.group(1), re.M))
    return set(re.findall(r"""["']([a-z_]+)["']""", m.group(1)))


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

    def test_canonical_taxonomy_matches_documented(self):
        # scripts/evidence.py is the single source of truth for the taxonomy.
        self.assertEqual(ev.STATUSES, ALLOWED_STATUSES)
        self.assertEqual(set(ev.STATUS_LABELS), ALLOWED_STATUSES)

    def test_no_empty_or_missing_status(self):
        bad = [a.get("id") for a in _agencies() if not a.get("status")]
        self.assertEqual(bad, [], f"records missing status: {bad}")

    def test_js_copies_match_canonical_taxonomy(self):
        # The status set is duplicated in JS (tracker labels, report write
        # path); any divergence reopens the "terminated" class of bug.
        tracker = os.path.join(REPO_ROOT, "js", "tracker.js")
        report = os.path.join(REPO_ROOT, "api", "report.js")
        tracker_labels = _js_status_literals(
            tracker, r"const STATUS_LABEL\s*=\s*\{(.*?)\};", keys=True)
        self.assertEqual(tracker_labels, ALLOWED_STATUSES,
                         "js/tracker.js STATUS_LABEL diverged from taxonomy")
        report_statuses = _js_status_literals(
            report, r"const STATUSES\s*=\s*new Set\(\[(.*?)\]\)")
        self.assertEqual(report_statuses, ALLOWED_STATUSES,
                         "api/report.js STATUSES diverged from taxonomy")

    def test_finding_flock_action_map_targets_are_canonical(self):
        # weekly_monitor translates Finding Flock's action vocabulary into
        # our statuses; every target must be a documented status.
        import weekly_monitor as wm
        for action, status in wm.FF_ACTION_TO_STATUS.items():
            self.assertIn(status, ALLOWED_STATUSES,
                          f"FF_ACTION_TO_STATUS[{action!r}] -> {status!r} "
                          f"is not a documented status")


class TestDateFields(unittest.TestCase):
    def test_date_fields_are_iso_or_null(self):
        bad = []
        for a in _agencies():
            for field in DATE_FIELDS:
                v = a.get(field)
                if v is None:
                    continue
                if not isinstance(v, str) or not DATE_RE.match(v):
                    bad.append((a.get("id"), field, v))
                    continue
                try:
                    # Coarser precisions pad to a valid date for validation.
                    padded = {4: v + "-01-01", 7: v + "-01",
                              10: v}[len(v)]
                    datetime.date.fromisoformat(padded)
                except (ValueError, KeyError):
                    bad.append((a.get("id"), field, v))
        self.assertEqual(bad, [], f"records with malformed dates: {bad[:10]}")


if __name__ == "__main__":
    unittest.main()
