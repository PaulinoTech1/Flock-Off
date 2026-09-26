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

    def tearDown(self):
        fp.fetch_page = self._orig

    def test_thin_page(self):
        fp.fetch_page = lambda url: ("ok", url, "<html><body><p>tiny</p></body></html>")
        rec = fp.fingerprint_url("https://example.com/", "2026-01-01")
        self.assertEqual(rec["fetch_status"], "thin")
        self.assertIsNone(rec["simhash"])
        self.assertIsNone(rec["content_hash"])

    def test_ok_page(self):
        body = "<html><body>" + "<p>substantive paragraph of text</p>" * 40 + "</body></html>"
        fp.fetch_page = lambda url: ("ok", url, body)
        rec = fp.fingerprint_url("https://example.com/", "2026-01-01")
        self.assertEqual(rec["fetch_status"], "ok")
        self.assertIsNotNone(rec["simhash"])
        self.assertIsNotNone(rec["content_hash"])
        self.assertGreaterEqual(rec["text_len"], fp.min_text_len())

    def test_blocked_page(self):
        fp.fetch_page = lambda url: ("blocked", url, None)
        rec = fp.fingerprint_url("https://example.com/", "2026-01-01")
        self.assertEqual(rec["fetch_status"], "blocked")
        self.assertIsNone(rec["simhash"])


if __name__ == "__main__":
    unittest.main()
