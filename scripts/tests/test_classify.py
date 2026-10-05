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

    def test_ai_summaries_excluded(self):
        # Boss policy 2026-10-04: AI-generated summaries are excluded
        # entirely, not usable even as leads.
        ok, reason = cs.classify("https://citizenportal.ai/articles/123")
        self.assertEqual((ok, reason), (False, "excluded"))
        ok, reason = cs.classify("https://summed.news/article/xyz")
        self.assertEqual((ok, reason), (False, "excluded"))

    def test_counts(self):
        # Updated 2026-09-26: Wave 2 domain triage (TX/CA/CO/AZ/WA/OR/MO/KS/LA/OK
        # research wave) added 62 verified-news, 30 verified-primary, 5 unverified.
        # Updated 2026-09-26: Wave 3 domain triage (AR/IA/ID/MD/MN/MT/NE/NM/NV/UT
        # research wave) added 18 verified-news, 20 verified-primary, 11 unverified.
        # Updated 2026-09-26: territory tier approvals (Boss decision) promoted
        # elnuevodia.com and stjohntradewinds.com to verified-news.
        # Updated 2026-10-04: AI-summary domains (citizenportal.ai, summed.news)
        # moved from unverified to the new excluded tier (Boss policy).
        # Updated 2026-10-04: openutah.org added (AI-generated meeting summaries).
        self.assertEqual(len(cs.VERIFIED_NEWS()), 197)
        self.assertEqual(len(cs.VERIFIED_PRIMARY()), 83)
        self.assertEqual(len(cs.UNVERIFIED()), 63)
        self.assertEqual(len(cs.EXCLUDED()), 3)


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


class TestExcludedDomains(unittest.TestCase):
    """AI-generated summaries are excluded entirely: a citation on an
    excluded domain is a hard fail, same as a feed-domain citation
    (Boss policy 2026-10-04, docs/METHODOLOGY.md)."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(REPO_ROOT := os.path.dirname(
                os.path.dirname(os.path.dirname(
                    os.path.abspath(__file__)))),
                "data", "agencies.json"), encoding="utf-8") as f:
            cls.data = json.load(f)["agencies"]

    @staticmethod
    def _host(url):
        import urllib.parse
        try:
            return urllib.parse.urlparse(url).netloc.lower().replace("www.", "")
        except Exception:
            return ""

    def test_no_excluded_domain_cited(self):
        bad = []
        for a in self.data:
            for s in a.get("sources") or []:
                if self._host(s.get("url", "")) in cs.EXCLUDED():
                    bad.append((a["id"], s["url"]))
        self.assertEqual(bad, [], f"excluded-domain citations: {bad}")
