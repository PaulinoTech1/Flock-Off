"""Tests for scripts/source_fingerprints.py: simhash, text extraction, config."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import source_fingerprints as fp


class TestHamming(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(fp.hamming(0, 0), 0)
        self.assertEqual(fp.hamming(0xDEAD, 0xDEAD), 0)

    def test_known(self):
        self.assertEqual(fp.hamming(0b01, 0b10), 2)
        self.assertEqual(fp.hamming(0, (1 << 64) - 1), 64)


class TestSimhash(unittest.TestCase):
    LONG_A = ("the quick brown fox jumps over the lazy dog " * 30).strip()
    LONG_B = ("quantum cryptography research advances rapidly each year " * 30).strip()

    def test_deterministic(self):
        self.assertEqual(fp.simhash64(self.LONG_A), fp.simhash64(self.LONG_A))

    def test_identical_zero_distance(self):
        self.assertEqual(fp.hamming(fp.simhash64(self.LONG_A),
                                    fp.simhash64(self.LONG_A)), 0)

    def test_different_texts_far_apart(self):
        a, b = fp.simhash64(self.LONG_A), fp.simhash64(self.LONG_B)
        self.assertIsNotNone(a)
        self.assertIsNotNone(b)
        self.assertGreater(fp.hamming(a, b), fp.near_dup_distance())

    def test_too_short_returns_none(self):
        self.assertIsNone(fp.simhash64("too short"))


class TestContentHash(unittest.TestCase):
    def test_stable_hex(self):
        h = fp.content_hash("hello")
        self.assertEqual(h, fp.content_hash("hello"))
        self.assertRegex(h, r"^[0-9a-f]{64}$")

    def test_differs_on_change(self):
        self.assertNotEqual(fp.content_hash("a"), fp.content_hash("b"))


class TestExtractText(unittest.TestCase):
    def test_title_and_body(self):
        html = ("<html><head><title>My Title</title></head><body>"
                "<p>Hello world</p></body></html>")
        title, text = fp.extract_text(html)
        self.assertEqual(title, "My Title")
        self.assertIn("Hello world", text)

    def test_script_style_dropped(self):
        html = ("<html><body><p>keep this</p><script>var x = 1;</script>"
                "<style>.a {color:red}</style></body></html>")
        _, text = fp.extract_text(html)
        self.assertIn("keep this", text)
        self.assertNotIn("var x", text)
        self.assertNotIn("color:red", text)


class TestConfigAccessors(unittest.TestCase):
    def test_accessors_follow_yaml(self):
        self.assertEqual(fp.near_dup_distance(), 3)
        self.assertEqual(fp.update_distance(), 8)
        self.assertGreater(fp.update_distance(), fp.near_dup_distance())
        self.assertEqual(fp.min_text_len(), 200)
        self.assertEqual(fp.pair_min_len(), 800)


class TestFingerprintUrl(unittest.TestCase):
    def setUp(self):
        self._orig = fp.fetch_page
        import tempfile
        self._tmp = tempfile.mkdtemp(prefix="flockoff-archive-test-")
        self.addCleanup(__import__("shutil").rmtree, self._tmp,
                        ignore_errors=True)

    def tearDown(self):
        fp.fetch_page = self._orig

    def _fp(self, url, today="2026-01-01", key=None):
        return fp.fingerprint_url(url, today,
                                  archive_directory=self._tmp, key=key)

    def test_thin_page(self):
        fp.fetch_page = lambda url: ("ok", url, "<html><body><p>tiny</p></body></html>")
        rec = self._fp("https://example.com/")
        self.assertEqual(rec["fetch_status"], "thin")
        self.assertIsNone(rec["simhash"])
        self.assertIsNone(rec["content_hash"])

    def test_ok_page(self):
        body = "<html><body>" + "<p>substantive paragraph of text</p>" * 40 + "</body></html>"
        fp.fetch_page = lambda url: ("ok", url, body)
        rec = self._fp("https://example.com/")
        self.assertEqual(rec["fetch_status"], "ok")
        self.assertIsNotNone(rec["simhash"])
        self.assertIsNotNone(rec["content_hash"])
        self.assertGreaterEqual(rec["text_len"], fp.min_text_len())

    def test_blocked_page(self):
        fp.fetch_page = lambda url: ("blocked", url, None)
        rec = self._fp("https://example.com/")
        self.assertEqual(rec["fetch_status"], "blocked")
        self.assertIsNone(rec["simhash"])

    def test_archive_written_on_ok(self):
        body = "<html><head><title>T</title></head><body>" + "<p>substantive paragraph of text</p>" * 40 + "</body></html>"
        fp.fetch_page = lambda url: ("ok", url, body)
        rec = self._fp("https://example.com/canonical-key")
        self.assertIsNotNone(rec["archive"])
        archived = fp.read_archive("https://example.com/canonical-key",
                                   directory=self._tmp)
        self.assertIsNotNone(archived)
        self.assertIn("substantive paragraph of text", archived)
        # archive content is exactly what content_hash covers
        self.assertEqual(fp.content_hash(archived), rec["content_hash"])

    def test_archive_keyed_by_canonical_key(self):
        body = "<html><body>" + "<p>substantive paragraph of text</p>" * 40 + "</body></html>"
        fp.fetch_page = lambda url: ("ok", url, body)
        rec = self._fp("https://example.com/some-url", key="canonical-key")
        self.assertEqual(rec["archive"], fp.archive_filename("canonical-key"))
        self.assertIsNotNone(fp.read_archive("canonical-key",
                                             directory=self._tmp))

    def test_no_archive_on_blocked(self):
        fp.fetch_page = lambda url: ("blocked", url, None)
        rec = self._fp("https://example.com/")
        self.assertIsNone(rec["archive"])
        self.assertIsNone(fp.read_archive("https://example.com/",
                                          directory=self._tmp))

    def test_archive_filename_stable(self):
        self.assertEqual(fp.archive_filename("k"), fp.archive_filename("k"))
        self.assertNotEqual(fp.archive_filename("k"), fp.archive_filename("k2"))
        self.assertTrue(fp.archive_filename("k").endswith(".txt"))


if __name__ == "__main__":
    unittest.main()


class TestRefreshQuarantine(unittest.TestCase):
    """Non-ok fingerprints are quarantined, not retried every run."""

    def setUp(self):
        self._orig_fetch = fp.fetch_page
        self._orig_delay = fp.fetch_delay
        fp.fetch_delay = lambda: 0
        self.calls = 0

    def tearDown(self):
        fp.fetch_page = self._orig_fetch
        fp.fetch_delay = self._orig_delay

    def _data(self, n=3):
        return {"agencies": [{
            "id": "agency-%d" % i,
            "sources": [{"url": "https://example.com/%d" % i,
                         "source_key": "key-%d" % i,
                         "title": "t"}],
        } for i in range(n)]}

    def test_blocked_record_gets_retry_after(self):
        fp.fetch_page = lambda url: ("blocked", url, None)
        rec = fp.fingerprint_url("https://example.com/", "2026-10-04",
                                 key="k")
        self.assertEqual(rec["fetch_status"], "blocked")
        self.assertEqual(rec["retry_after"], "2026-11-03")  # +30d

    def test_error_quarantine_is_shorter(self):
        fp.fetch_page = lambda url: ("error", url, None)
        rec = fp.fingerprint_url("https://example.com/", "2026-10-04",
                                 key="k")
        self.assertEqual(rec["retry_after"], "2026-10-11")  # +7d

    def test_ok_record_has_no_retry_after(self):
        body = "<html><body>" + "<p>substantive paragraph of text</p>" * 40
        fp.fetch_page = lambda url: ("ok", url, body)
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            rec = fp.fingerprint_url("https://example.com/", "2026-10-04",
                                     archive_directory=tmp, key="k")
        self.assertEqual(rec["fetch_status"], "ok")
        self.assertNotIn("retry_after", rec)

    def test_quarantined_sources_are_skipped(self):
        data = self._data(2)
        import datetime as _dt
        _today = _dt.date.today().isoformat()
        fps = {
            "key-0": {"fetch_status": "blocked", "fetched_at": _today,
                      "retry_after": "2099-01-01"},
            "key-1": {"fetch_status": "ok", "fetched_at": _today,
                      "content_hash": "x"},
        }
        fp.fetch_page = lambda url: (_ for _ in ()).throw(
            AssertionError("quarantined source must not be fetched"))
        stats = fp.refresh(data, fps, max_n=25, max_age_days=60)
        # key-0 quarantined (skipped); key-1 fresh-ok (skipped).
        self.assertEqual(stats["fetched"], 0)
        self.assertIn("key-0", fps)

    def test_expired_quarantine_is_retried(self):
        data = self._data(1)
        fps = {"key-0": {"fetch_status": "blocked",
                         "fetched_at": "2026-09-01",
                         "retry_after": "2026-10-01"}}
        fp.fetch_page = lambda url: ("blocked", url, None)
        stats = fp.refresh(data, fps, max_n=25, max_age_days=60)
        self.assertEqual(stats["fetched"], 1)
        self.assertEqual(stats["blocked"], 1)
        # Re-failed source gets a fresh quarantine window.
        self.assertGreater(fps["key-0"]["retry_after"], "2026-10-01")

    def test_legacy_record_without_retry_after_retried_once(self):
        data = self._data(1)
        fps = {"key-0": {"fetch_status": "blocked",
                         "fetched_at": "2026-09-01"}}
        fp.fetch_page = lambda url: ("blocked", url, None)
        stats = fp.refresh(data, fps, max_n=25, max_age_days=60)
        self.assertEqual(stats["fetched"], 1)
        self.assertIn("retry_after", fps["key-0"])


class TestFetchClient(unittest.TestCase):
    def test_challenge_title_detected(self):
        import fetch_client as fc
        html = "<html><head><title>Just a moment...</title></head><body>cloudflare ray</body></html>"
        self.assertTrue(fc._looks_like_challenge(html))

    def test_normal_page_not_challenge(self):
        import fetch_client as fc
        html = "<html><head><title>City votes to end Flock contract</title></head><body>council voted</body></html>"
        self.assertFalse(fc._looks_like_challenge(html))

    def test_blocked_codes(self):
        import fetch_client as fc
        for code in (401, 402, 403, 429):
            self.assertTrue(fc._sniff_blocked(code, "<html></html>"))
        self.assertFalse(fc._sniff_blocked(200, "<html><body>news</body></html>"))
        self.assertFalse(fc._sniff_blocked(404, "<html><body>not found</body></html>"))

    def test_challenge_on_200_is_blocked(self):
        import fetch_client as fc
        html = "<html><head><title>Just a moment...</title></head><body>cloudflare</body></html>"
        self.assertTrue(fc._sniff_blocked(200, html))

    def test_backend_reports(self):
        import fetch_client as fc
        c = fc.FetchClient()
        self.assertIn(c.backend, ("curl_cffi", "urllib"))
