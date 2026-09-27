"""Tests for the fatal fingerprint-drift gate (scripts/source_fingerprints.py).

drift_check() must fail a push when a previously fingerprinted source shows
Hamming distance >= fingerprints.update_distance against its stored simhash
and no human re-review covers that baseline. Re-reviewed drift passes.
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import source_fingerprints as sf


def _fp_for(text, fetched_at="2026-01-01"):
    sh = sf.simhash64(text)
    return {
        "url": "http://example.invalid/article",
        "fetch_status": "ok",
        "simhash": format(sh, "016x"),
        "fetched_at": fetched_at,
        "text_len": len(text),
    }


TEXT_A = ("the city council voted to renew the flock safety contract " * 40).strip()
TEXT_B = ("quantum cryptography research advances rapidly each year " * 40).strip()


class TestIsRereviewed(unittest.TestCase):
    def test_no_review(self):
        self.assertFalse(sf.is_rereviewed("k", _fp_for(TEXT_A), {}))

    def test_review_after_baseline(self):
        rev = {"k": {"reviewed_at": "2026-02-01", "reviewed_by": "T",
                     "decision": "accepted", "note": "drift is a site redesign"}}
        self.assertTrue(sf.is_rereviewed("k", _fp_for(TEXT_A), rev))

    def test_review_before_baseline_stale(self):
        # Baseline advanced after the review (refresh ran); the review no
        # longer covers the current baseline.
        rev = {"k": {"reviewed_at": "2026-01-01", "reviewed_by": "T",
                     "decision": "accepted", "note": ""}}
        self.assertFalse(sf.is_rereviewed("k", _fp_for(TEXT_A, "2026-03-01"), rev))


class TestDriftCheck(unittest.TestCase):
    def _run(self, fps, reviews, live_text):
        def fake_fetch(url):
            html = ("<html><head><title>t</title></head><body><p>"
                    + live_text + "</p></body></html>")
            return "ok", url, html
        with mock.patch.object(sf, "fetch_page", fake_fetch), \
             mock.patch.object(sf.time, "sleep", lambda s: None):
            return sf.drift_check(fps, reviews)

    def test_no_drift_identical(self):
        fps = {"k": _fp_for(TEXT_A)}
        drifted, stats = self._run(fps, {}, TEXT_A)
        self.assertEqual(drifted, [])
        self.assertEqual(stats["checked"], 1)

    def test_drift_fatal(self):
        fps = {"k": _fp_for(TEXT_A)}
        drifted, stats = self._run(fps, {}, TEXT_B)
        self.assertEqual(len(drifted), 1)
        self.assertEqual(drifted[0]["key"], "k")
        self.assertGreaterEqual(drifted[0]["distance"], sf.update_distance())
        self.assertEqual(stats["drifted"], 1)

    def test_rereviewed_drift_passes(self):
        fps = {"k": _fp_for(TEXT_A)}
        rev = {"k": {"reviewed_at": "2026-05-01", "reviewed_by": "T",
                     "decision": "accepted", "note": "redesign, content same"}}
        drifted, stats = self._run(fps, rev, TEXT_B)
        self.assertEqual(drifted, [])
        self.assertEqual(stats["rereviewed"], 1)

    def test_non_ok_baseline_skipped(self):
        fps = {"k": {"url": "http://example.invalid/x", "fetch_status": "blocked",
                     "simhash": None, "fetched_at": "2026-01-01"}}
        drifted, stats = self._run(fps, {}, TEXT_B)
        self.assertEqual(drifted, [])
        self.assertEqual(stats["checked"], 0)

    def test_keys_scoping(self):
        fps = {"k1": _fp_for(TEXT_A), "k2": _fp_for(TEXT_A)}
        with mock.patch.object(sf, "fetch_page",
                               lambda u: ("ok", u, "<html><body><p>" + TEXT_B + "</p></body></html>")), \
             mock.patch.object(sf.time, "sleep", lambda s: None):
            drifted, stats = sf.drift_check(fps, {}, keys={"k1"})
        self.assertEqual(stats["checked"], 1)
        self.assertEqual(len(drifted), 1)
        self.assertEqual(drifted[0]["key"], "k1")

    def test_blocked_live_fetch_counted_not_drifted(self):
        # A source the gate cannot re-fetch is unverifiable, not clean:
        # it must be counted, never silently treated as "no drift".
        fps = {"k": _fp_for(TEXT_A)}
        with mock.patch.object(sf, "fetch_page", lambda u: ("blocked", None, None)), \
             mock.patch.object(sf.time, "sleep", lambda s: None):
            drifted, stats = sf.drift_check(fps, {})
        self.assertEqual(drifted, [])
        self.assertEqual(stats["blocked"], 1)
        self.assertEqual(stats["checked"], 1)

    def test_error_retries_once_then_counts(self):
        fps = {"k": _fp_for(TEXT_A)}
        calls = []
        def flaky(url):
            calls.append(url)
            return ("error", None, None)
        with mock.patch.object(sf, "fetch_page", flaky), \
             mock.patch.object(sf.time, "sleep", lambda s: None):
            drifted, stats = sf.drift_check(fps, {})
        self.assertEqual(len(calls), 2)  # initial + one retry
        self.assertEqual(stats["error"], 1)
        self.assertEqual(drifted, [])

    def test_error_retry_recovers(self):
        fps = {"k": _fp_for(TEXT_A)}
        html = ("<html><head><title>t</title></head><body><p>" + TEXT_A + "</p></body></html>")
        seq = [("error", None, None), ("ok", "http://example.invalid/article", html)]
        with mock.patch.object(sf, "fetch_page", lambda u: seq.pop(0)), \
             mock.patch.object(sf.time, "sleep", lambda s: None):
            drifted, stats = sf.drift_check(fps, {})
        self.assertEqual(stats["error"], 0)
        self.assertEqual(drifted, [])

    def test_main_drift_fatal_on_unverifiable(self):
        # _main_drift must exit nonzero when a scoped source cannot be
        # re-fetched: unverifiable is not verified.
        fps = {"k": _fp_for(TEXT_A)}
        with mock.patch.object(sf, "load_fingerprints", lambda: fps), \
             mock.patch.object(sf, "load_reviews", lambda: {}), \
             mock.patch.object(sf, "data_path", lambda: "/dev/null"), \
             mock.patch.object(sf, "iter_citations", lambda data: []), \
             mock.patch.object(sf, "fetch_page", lambda u: ("blocked", None, None)), \
             mock.patch.object(sf.time, "sleep", lambda s: None), \
             mock.patch("builtins.open", mock.mock_open(read_data='{"agencies": []}')), \
             self.assertRaises(SystemExit) as cm:
            sf._main_drift(["--drift", "--keys", "k"])
        self.assertNotEqual(cm.exception.code, 0)


class TestReviewsRoundTrip(unittest.TestCase):
    def test_save_load(self):
        import tempfile
        rev = {"k": {"reviewed_at": "2026-09-26", "reviewed_by": "T",
                     "decision": "accepted", "note": "n"}}
        with tempfile.NamedTemporaryFile("w", suffix=".json",
                                         delete=False) as f:
            path = f.name
        try:
            sf.save_reviews(rev, path)
            self.assertEqual(sf.load_reviews(path), rev)
        finally:
            os.unlink(path)

    def test_load_missing(self):
        self.assertEqual(sf.load_reviews("/nonexistent/path.json"), {})


if __name__ == "__main__":
    unittest.main()
