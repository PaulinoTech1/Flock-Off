"""Tests for the terminal-claim evidence bar (scripts/evidence.py).

Hard rule: a terminal claim (cancelled / rejected / expired) displays
"verified" ONLY with >= 1 distinct verified-primary host AND >= 2 distinct
verified-news hosts. Anything else must be "pending", either by meeting the
bar's negation or by explicit validation:"pending" acknowledgment. Records
not re-verified within 180 days auto-downgrade to pending at display time.
"""
import datetime
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import evidence as ev

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PATH = os.path.join(REPO_ROOT, "data", "agencies.json")
CONFIG_PATH = os.path.join(REPO_ROOT, "config", "flock-off.yaml")


def _rec(status="cancelled", sources=(), validation=None,
         last_verified="2026-09-26"):
    r = {"id": "t", "status": status, "sources": list(sources),
         "last_verified": last_verified}
    if validation is not None:
        r["validation"] = validation
    return r


def _src(host, verified=True):
    return {"url": f"https://{host}/story", "verified": verified}


PRIMARY = {"city.gov"}
NEWS = {"paperone.com", "papertwo.com", "paperthree.com"}


class TestBar(unittest.TestCase):
    def test_verified_needs_one_primary_two_news(self):
        r = _rec(sources=[_src("city.gov"), _src("paperone.com"),
                          _src("papertwo.com")])
        c = ev.compute(r, PRIMARY, NEWS)
        self.assertTrue(c["meets_bar"])
        self.assertEqual(c["tier"], "verified")

    def test_news_only_never_verified(self):
        r = _rec(sources=[_src("paperone.com"), _src("papertwo.com"),
                          _src("paperthree.com")])
        c = ev.compute(r, PRIMARY, NEWS)
        self.assertFalse(c["meets_bar"])
        self.assertEqual(c["tier"], "pending")

    def test_primary_only_never_verified(self):
        r = _rec(sources=[_src("city.gov")])
        self.assertEqual(ev.compute(r, PRIMARY, NEWS)["tier"], "pending")

    def test_one_news_not_enough(self):
        r = _rec(sources=[_src("city.gov"), _src("paperone.com")])
        self.assertEqual(ev.compute(r, PRIMARY, NEWS)["tier"], "pending")

    def test_explicit_pending_acknowledgment_wins(self):
        r = _rec(sources=[_src("city.gov"), _src("paperone.com"),
                          _src("papertwo.com")], validation="pending")
        c = ev.compute(r, PRIMARY, NEWS)
        self.assertTrue(c["meets_bar"])
        self.assertTrue(c["acknowledged_pending"])
        self.assertEqual(c["tier"], "pending")

    def test_unverified_sources_do_not_count(self):
        r = _rec(sources=[_src("city.gov"), _src("paperone.com"),
                          _src("papertwo.com", verified=False)])
        c = ev.compute(r, PRIMARY, NEWS)
        self.assertEqual(c["news_independent"], 1)
        self.assertEqual(c["tier"], "pending")

    def test_same_outlet_twice_counts_once(self):
        r = _rec(sources=[_src("city.gov"), _src("paperone.com"),
                          _src("paperone.com/deeper")])
        c = ev.compute(r, PRIMARY, NEWS)
        self.assertEqual(c["news_independent"], 1)
        self.assertEqual(c["tier"], "pending")

    def test_non_terminal_tier_na(self):
        r = _rec(status="active", sources=[_src("city.gov")])
        self.assertEqual(ev.compute(r, PRIMARY, NEWS)["tier"], "na")


class TestStaleDowngrade(unittest.TestCase):
    def test_stale_downgrades_verified_to_pending(self):
        r = _rec(sources=[_src("city.gov"), _src("paperone.com"),
                          _src("papertwo.com")], last_verified="2025-01-01")
        c = ev.compute(r, PRIMARY, NEWS,
                       today=datetime.date(2026, 9, 26))
        self.assertTrue(c["stale"])
        self.assertTrue(c["stale_downgraded"])
        self.assertEqual(c["tier"], "pending")

    def test_fresh_stays_verified(self):
        r = _rec(sources=[_src("city.gov"), _src("paperone.com"),
                          _src("papertwo.com")], last_verified="2026-09-01")
        c = ev.compute(r, PRIMARY, NEWS,
                       today=datetime.date(2026, 9, 26))
        self.assertFalse(c["stale"])
        self.assertEqual(c["tier"], "verified")

    def test_missing_last_verified_is_stale(self):
        r = _rec(sources=[_src("city.gov"), _src("paperone.com"),
                          _src("papertwo.com")], last_verified=None)
        self.assertTrue(ev.compute(r, PRIMARY, NEWS)["stale"])


class TestDatasetInvariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(DATA_PATH, encoding="utf-8") as f:
            cls.data = json.load(f)["agencies"]
        cls.primary, cls.news, _ = ev.load_classify_lists(CONFIG_PATH)

    def test_no_terminal_record_displays_verified_without_bar(self):
        bad = []
        for a in self.data:
            c = ev.compute(a, self.primary, self.news)
            if c["terminal"] and c["tier"] == "verified" and not c["meets_bar"]:
                bad.append(a["id"])
        self.assertEqual(bad, [], f"verified without meeting the bar: {bad}")

    def test_every_non_bar_terminal_record_is_acknowledged_pending(self):
        bad = [a["id"] for a in self.data
               if ev.compute(a, self.primary, self.news)["terminal"]
               and not ev.compute(a, self.primary, self.news)["meets_bar"]
               and a.get("validation") != "pending"]
        self.assertEqual(bad, [], f"terminal records missing validation:pending: {bad}")

    def test_verified_tier_is_small_and_auditable(self):
        verified = [a["id"] for a in self.data
                    if ev.compute(a, self.primary, self.news)["tier"] == "verified"]
        # Sanity: the bar is strict; if this number explodes something changed.
        self.assertLess(len(verified), 50, f"suspicious verified count: {len(verified)}")


if __name__ == "__main__":
    unittest.main()
