"""Tests for the public audit log (data/audit/log.jsonl).

Every dataset change must append a hash-chained entry. Invariants:
  - each line is valid JSON with the required fields
  - the chain links: entry.parent_hash == previous entry.new_hash
    (genesis has parent_hash null)
  - the tip entry's new_hash equals the SHA-256 of data/agencies.json,
    so an unlogged change is detectable
"""
import hashlib
import json
import os
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_PATH = os.path.join(REPO_ROOT, "data", "audit", "log.jsonl")
DATA_PATH = os.path.join(REPO_ROOT, "data", "agencies.json")

REQUIRED_FIELDS = frozenset({
    "ts", "actor", "parent_hash", "new_hash", "commit", "changes",
})


def _entries():
    out = []
    with open(LOG_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


class TestAuditLog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entries = _entries()
        with open(DATA_PATH, "rb") as f:
            cls.dataset_hash = hashlib.sha256(f.read()).hexdigest()

    def test_log_is_nonempty(self):
        self.assertGreater(len(self.entries), 0, "audit log is empty")

    def test_required_fields(self):
        for i, e in enumerate(self.entries):
            missing = REQUIRED_FIELDS - set(e.keys())
            self.assertEqual(missing, set(), f"entry {i} missing {missing}")

    def test_chain_links(self):
        prev = None
        for i, e in enumerate(self.entries):
            if i == 0:
                self.assertIsNone(e["parent_hash"],
                                  "first entry must be genesis (parent_hash null)")
            else:
                self.assertEqual(e["parent_hash"], prev,
                                 f"entry {i} breaks the hash chain")
            prev = e["new_hash"]

    def test_hashes_are_sha256_hex(self):
        for i, e in enumerate(self.entries):
            self.assertRegex(e["new_hash"], r"^[0-9a-f]{64}$",
                             f"entry {i} new_hash malformed")
            if e["parent_hash"] is not None:
                self.assertRegex(e["parent_hash"], r"^[0-9a-f]{64}$",
                                 f"entry {i} parent_hash malformed")

    def test_tip_matches_current_dataset(self):
        tip = self.entries[-1]["new_hash"]
        self.assertEqual(tip, self.dataset_hash,
                         "audit tip does not match data/agencies.json: "
                         "a dataset change was made without an audit entry; "
                         "append one with scripts/audit_log.py")


if __name__ == "__main__":
    unittest.main()
