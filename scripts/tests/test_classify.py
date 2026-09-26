"""Tests for scripts/classify_sources.py.

Two regression tests lock in bugs found 2026-09-26:
  1. stamp_source must preserve source_key (the old inline rebuild
     silently dropped every key on a write-mode run).
  2. The config domain lists must cover everything the dataset stamps
     verified=true (the first YAML extraction dropped 87 domains).
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import classify_sources as cs


class TestClassify(unittest.TestCase):
    def test_verified_news(self):
        ok, reason = cs.classify("https://www.607newsnow.com/story")
        self.assertEqual((ok, reason), (True, "verified-news"))

    def test_verified_primary(self):
        ok, reason = cs.classify("https://apps.troymi.gov/council")
        self.assertEqual((ok, reason), (True, "verified-primary"))

    def test_unverified_listed(self):
        ok, reason = cs.classify("https://aclu-wi.org/document")
        self.assertEqual((ok, reason), (False, "unverified-listed"))

    def test_unknown_fails_closed(self):
        ok, reason = cs.classify("https://totally-random-blog.example/")
        self.assertEqual((ok, reason), (False, "unverified-unlisted"))

    def test_counts(self):
        self.assertEqual(len(cs.VERIFIED_NEWS()), 115)
        self.assertEqual(len(cs.VERIFIED_PRIMARY()), 33)
        self.assertEqual(len(cs.UNVERIFIED()), 49)


class TestStampSource(unittest.TestCase):
    def test_preserves_source_key_and_unknown_fields(self):
        src = {"title": "T", "url": "https://example.com", "date": "2026-01-01",
               "verified": False, "source_key": "abc123", "notes": "keep me"}
        cs.stamp_source(src, True)
        self.assertTrue(src["verified"])
        self.assertEqual(src["source_key"], "abc123")
        self.assertEqual(src["notes"], "keep me")

    def test_stable_key_order(self):
        src = {"notes": "x", "source_key": "k", "url": "u", "title": "t",
               "date": "d", "verified": False}
        cs.stamp_source(src, True)
        self.assertEqual(list(src)[:5],
                         ["title", "url", "date", "verified", "source_key"])

    def test_can_clear_verified(self):
        src = {"title": "t", "url": "u", "verified": True}
        cs.stamp_source(src, False)
        self.assertFalse(src["verified"])


class TestDatasetConsistency(unittest.TestCase):
    """REGRESSION: config domain lists must cover every verified=true source.

    When the domain lists were first extracted into YAML, 87 domains were
    silently dropped and nothing caught it because the verification reused
    the same broken parser. This test fails if any source stamped
    verified=true in the dataset would now classify as unverified-unlisted.
    """

    def test_no_verified_source_is_unlisted(self):
        data = json.load(open(cs.DATA_PATH(), encoding="utf-8"))
        offenders = []
        for agency in data["agencies"]:
            for src in agency.get("sources") or []:
                if src.get("verified") is True:
                    ok, reason = cs.classify(src.get("url", ""))
                    if not ok and reason == "unverified-unlisted":
                        offenders.append(
                            f"{agency['agency_id']}: {src.get('url')}")
        self.assertEqual(offenders, [],
                         "verified=true sources that classify as unlisted: "
                         + "; ".join(offenders))

    def test_check_mode_passes(self):
        with self.assertRaises(SystemExit) as cm:
            cs.main(["--check"])
        self.assertEqual(cm.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
