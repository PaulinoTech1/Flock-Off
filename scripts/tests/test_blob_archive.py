"""Tests for scripts/blob_archive.py (offline: no network, no token)."""

import copy
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import blob_archive as ba


def _snap(**kw):
    base = dict(
        source_key="test-key",
        url="https://example.com/article",
        text="Extracted article text for testing.",
    )
    base.update(kw)
    return ba.build_snapshot(**base)


class TestBuildSnapshot(unittest.TestCase):
    def test_build_and_verify(self):
        snap = _snap()
        ok, msg = ba.verify_snapshot(snap)
        self.assertTrue(ok, msg)
        self.assertEqual(snap["schema_version"], 1)
        self.assertEqual(snap["integrity"]["algorithm"], "sha256")
        self.assertEqual(len(snap["integrity"]["payload_hash"]), 64)

    def test_deterministic_hash(self):
        a = _snap(accurate_to="2026-09-27", fetched_at="2026-09-27T00:00:00+00:00")
        b = _snap(accurate_to="2026-09-27", fetched_at="2026-09-27T00:00:00+00:00")
        self.assertEqual(a["integrity"]["payload_hash"],
                         b["integrity"]["payload_hash"])

    def test_accurate_to_defaults_to_fetch_date(self):
        snap = _snap(fetched_at="2026-09-27T12:00:00+00:00")
        self.assertEqual(snap["accurate_to"], "2026-09-27")

    def test_accurate_to_explicit(self):
        snap = _snap(accurate_to="2025-01-15")
        self.assertEqual(snap["accurate_to"], "2025-01-15")

    def test_rejects_bad_accurate_to(self):
        with self.assertRaises(ValueError):
            _snap(accurate_to="not-a-date")

    def test_rejects_missing_key(self):
        with self.assertRaises(ValueError):
            ba.build_snapshot(source_key="", url="https://x.com", text="t")

    def test_rejects_missing_url(self):
        with self.assertRaises(ValueError):
            ba.build_snapshot(source_key="k", url="", text="t")

    def test_rejects_oversized_text(self):
        with self.assertRaises(ValueError):
            ba.build_snapshot(source_key="k", url="https://x.com",
                              text="x" * (ba.MAX_TEXT_CHARS + 1))

    def test_metadata_present(self):
        snap = _snap(agency_id="ag1", title="T")
        self.assertEqual(snap["agency_id"], "ag1")
        self.assertEqual(snap["title"], "T")
        self.assertIn("word_count", snap["meta"])
        self.assertIn("text_len", snap["meta"])


class TestVerifySnapshot(unittest.TestCase):
    def test_detects_text_tamper(self):
        snap = _snap()
        evil = copy.deepcopy(snap)
        evil["text"] = "TAMPERED"
        ok, msg = ba.verify_snapshot(evil)
        self.assertFalse(ok)
        self.assertIn("mismatch", msg)

    def test_detects_metadata_tamper(self):
        snap = _snap()
        evil = copy.deepcopy(snap)
        evil["accurate_to"] = "2020-01-01"
        ok, _ = ba.verify_snapshot(evil)
        self.assertFalse(ok)

    def test_detects_missing_integrity(self):
        snap = _snap()
        del snap["integrity"]
        ok, msg = ba.verify_snapshot(snap)
        self.assertFalse(ok)
        self.assertIn("integrity", msg)

    def test_rejects_wrong_schema(self):
        snap = _snap()
        snap["schema_version"] = 999
        ok, _ = ba.verify_snapshot(snap)
        self.assertFalse(ok)

    def test_rejects_non_dict(self):
        ok, _ = ba.verify_snapshot("not a dict")
        self.assertFalse(ok)
        ok, _ = ba.verify_snapshot(None)
        self.assertFalse(ok)


class TestPathname(unittest.TestCase):
    def test_date_prefixed_content_addressed(self):
        snap = _snap(accurate_to="2026-09-27")
        p = ba.snapshot_pathname(snap)
        self.assertTrue(p.startswith("snapshots/2026-09-27/"))
        self.assertTrue(p.endswith(".json"))
        self.assertIn(snap["integrity"]["payload_hash"], p)


class TestFailOpen(unittest.TestCase):
    def test_put_without_token_returns_none(self):
        snap = _snap()
        old = sys.stderr
        sys.stderr = io.StringIO()
        try:
            result = ba.put_snapshot(snap, token=None)
        finally:
            sys.stderr = old
        # Token env is unset in test env; must not raise
        self.assertIsNone(result)

    def test_put_refuses_unverifiable(self):
        snap = _snap()
        snap["text"] = "tampered after build"
        old = sys.stderr
        sys.stderr = io.StringIO()
        try:
            result = ba.put_snapshot(snap, token="fake-token")
        finally:
            sys.stderr = old
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
