"""Tests for scripts/weekly_monitor.py: the pure helpers.

Network-touching checks are exercised by the weekly run itself; these
tests pin the deterministic helpers and the HTML table parser so
refactors cannot silently change their behavior.
"""
import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import weekly_monitor as wm


class TestNormName(unittest.TestCase):
    def test_strips_stopwords_and_punct(self):
        self.assertEqual(wm.norm_name("Springfield Police Department"),
                         "springfield")
        self.assertEqual(wm.norm_name("City of Boston PD"), "boston pd")

    def test_none_and_empty(self):
        self.assertEqual(wm.norm_name(None), "")
        self.assertEqual(wm.norm_name(""), "")

    def test_lowercases(self):
        self.assertEqual(wm.norm_name("ITHACA"), "ithaca")


class TestDateMath(unittest.TestCase):
    TODAY = datetime.date(2026, 9, 26)

    def test_days_until(self):
        self.assertEqual(wm.days_until("2026-12-31", self.TODAY), 96)
        self.assertEqual(wm.days_until("2026-09-26", self.TODAY), 0)
        self.assertEqual(wm.days_until("2026-01-01", self.TODAY), -268)

    def test_days_since(self):
        self.assertEqual(wm.days_since("2026-09-26", self.TODAY), 0)
        self.assertEqual(wm.days_since("2026-01-01", self.TODAY), 268)

    def test_bad_input(self):
        self.assertIsNone(wm.days_until(None, self.TODAY))
        self.assertIsNone(wm.days_until("not-a-date", self.TODAY))
        self.assertIsNone(wm.days_since("", self.TODAY))


class TestTrackerTableParser(unittest.TestCase):
    HTML = """
    <html><body>
    <table>
      <tr><th>Place</th><th>State</th><th>Date</th><th>Action</th>
          <th>Detail</th><th>Source</th></tr>
      <tr><td>Ithaca</td><td>NY</td><td>2026-03-04</td><td>cancelled</td>
          <td>council vote</td><td><a href="https://example.com/s1">link</a></td></tr>
      <tr><td>Harrisonburg</td><td>VA</td><td>2026-07-28</td><td>cancelled</td>
          <td>res 26-005</td><td><a href="https://example.com/s2">link</a></td></tr>
    </table>
    </body></html>"""

    def test_rows_extracted(self):
        p = wm._TrackerTableParser()
        p.feed(self.HTML)
        self.assertEqual(len(p.rows), 2)
        self.assertEqual(p.rows[0][:4],
                         ("Ithaca", "NY", "2026-03-04", "cancelled"))
        self.assertEqual(p.rows[0][4], "https://example.com/s1")

    def test_non_tracker_table_ignored(self):
        p = wm._TrackerTableParser()
        p.feed("<table><tr><th>Name</th></tr>"
               "<tr><td>x</td></tr></table>")
        self.assertEqual(p.rows, [])


class TestConfigThresholds(unittest.TestCase):
    def test_thresholds_follow_yaml(self):
        mon = wm._cfg()["monitor"]
        self.assertEqual(mon["stale_days"], 180)
        self.assertEqual(mon["renewal_window_days"], 90)
        self.assertEqual(mon["update_probe_sample"], 20)
        self.assertEqual(mon["update_probe_delay"], 1.5)


if __name__ == "__main__":
    unittest.main()
