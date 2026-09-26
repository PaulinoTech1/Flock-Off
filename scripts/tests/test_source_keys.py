"""Tests for scripts/source_keys.py: canonical URL -> stable source_key."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import source_keys as sk


class TestCanonicalUrl(unittest.TestCase):
    def test_strips_scheme_case_and_www(self):
        self.assertEqual(sk.canonical_url("HTTP://WWW.Example.com/"),
                         "https://example.com/")

    def test_strips_fragment(self):
        self.assertEqual(sk.canonical_url("https://example.com/a#b"),
                         "https://example.com/a")

    def test_strips_trailing_slash(self):
        self.assertEqual(sk.canonical_url("https://example.com/a/"),
                         "https://example.com/a")

    def test_strips_tracking_params(self):
        out = sk.canonical_url(
            "https://example.com/a?utm_source=x&fbclid=zzz&b=2")
        self.assertEqual(out, "https://example.com/a?b=2")

    def test_keeps_significant_params(self):
        out = sk.canonical_url("https://example.com/a?id=123&utm_medium=y")
        self.assertEqual(out, "https://example.com/a?id=123")

    def test_amp_variants(self):
        self.assertEqual(sk.canonical_url("https://m.example.com/a/amp/"),
                         "https://example.com/a")
        self.assertEqual(sk.canonical_url("https://example.com/a/amp"),
                         "https://example.com/a")

    def test_rejects_non_http(self):
        with self.assertRaises(ValueError):
            sk.canonical_url("ftp://example.com/a")

    def test_deterministic(self):
        url = "https://www.example.com/a?utm_source=x"
        self.assertEqual(sk.canonical_url(url), sk.canonical_url(url))


def _agency(agency_id, sources):
    return {"id": agency_id, "sources": sources}


class TestCheck(unittest.TestCase):
    def test_missing_key(self):
        data = {"agencies": [_agency("a1", [{"url": "https://example.com/x"}])]}
        problems = sk.check(data)
        self.assertTrue(any("[E_KEY_MISSING]" in p for p in problems), problems)

    def test_stale_key(self):
        data = {"agencies": [_agency("a1", [{
            "url": "https://example.com/x", "source_key": "deadbeef"}])]}
        problems = sk.check(data)
        self.assertTrue(any("[E_KEY_STALE]" in p for p in problems), problems)

    def test_duplicate_within_agency(self):
        url = "https://example.com/x?utm_source=y"
        src = {"url": url, "source_key": sk.canonical_url(url)}
        data = {"agencies": [_agency("a1", [dict(src), dict(src)])]}
        problems = sk.check(data)
        self.assertTrue(any("[E_KEY_DUP]" in p for p in problems), problems)

    def test_same_key_across_agencies_is_fine(self):
        url = "https://example.com/x"
        src = {"url": url, "source_key": sk.canonical_url(url)}
        data = {"agencies": [_agency("a1", [dict(src)]),
                             _agency("a2", [dict(src)])]}
        self.assertEqual(sk.check(data), [])

    def test_bad_url_scheme(self):
        data = {"agencies": [_agency("a1", [{"url": "ftp://example.com/x"}])]}
        problems = sk.check(data)
        self.assertTrue(any("[E_KEY_BADURL]" in p for p in problems), problems)

    def test_clean_passes(self):
        url = "https://example.com/x"
        data = {"agencies": [_agency("a1", [
            {"url": url, "source_key": sk.canonical_url(url)}])]}
        self.assertEqual(sk.check(data), [])


class TestBackfill(unittest.TestCase):
    def test_fills_missing_and_fixes_stale(self):
        url1, url2 = "https://example.com/a", "https://example.com/b"
        data = {"agencies": [_agency("a1", [
            {"url": url1},
            {"url": url2, "source_key": "stale"},
        ])]}
        changed = sk.backfill(data)
        self.assertEqual(changed, 2)
        srcs = data["agencies"][0]["sources"]
        self.assertEqual(srcs[0]["source_key"], sk.canonical_url(url1))
        self.assertEqual(srcs[1]["source_key"], sk.canonical_url(url2))
        self.assertEqual(sk.check(data), [])

    def test_noop(self):
        url = "https://example.com/a"
        data = {"agencies": [_agency("a1", [
            {"url": url, "source_key": sk.canonical_url(url)}])]}
        self.assertEqual(sk.backfill(data), 0)


if __name__ == "__main__":
    unittest.main()
