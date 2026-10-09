"""Freshness test for the derived dataset metadata.

docs/METHODOLOGY.md's headline numbers must be computed, not hand-edited:
data/agencies.json's `meta` block used to say "322 records" and
"last_updated": "2026-09-26" weeks after the dataset moved on. Run
`python3 scripts/generate_meta.py` before committing dataset changes;
this test fails if the committed meta disagrees with a fresh computation.
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import evidence as ev
from generate_meta import compute_meta

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PATH = os.path.join(REPO_ROOT, "data", "agencies.json")
CONFIG_PATH = os.path.join(REPO_ROOT, "config", "flock-off.yaml")

# Derived fields that must match a fresh computation exactly.
DERIVED_KEYS = ("last_updated", "record_count", "jurisdiction_count",
                "jurisdictions", "status_counts", "terminal_verified",
                "terminal_pending_validation", "records_with_renewal_date",
                "records_with_contract_end", "coverage_note")


class TestMetaFresh(unittest.TestCase):
    def test_committed_meta_matches_recomputation(self):
        with open(DATA_PATH, encoding="utf-8") as f:
            data = json.load(f)
        agencies = data["agencies"]
        primary, news, _ = ev.load_classify_lists(CONFIG_PATH)
        ev_by_id = {a["id"]: ev.compute(a, primary, news) for a in agencies}
        fresh = compute_meta(agencies, ev_by_id)
        stored = data.get("meta") or {}
        stale = [k for k in DERIVED_KEYS if stored.get(k) != fresh[k]]
        self.assertEqual(
            stale, [],
            "stale dataset meta (run python3 scripts/generate_meta.py): "
            + ", ".join(
                f"{k} (stored={stored.get(k)!r} computed={fresh[k]!r})"
                for k in stale))


if __name__ == "__main__":
    unittest.main()
