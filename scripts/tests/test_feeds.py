"""Tests for upstream feed isolation.

Finding Flock and the EFF Atlas of Surveillance are approved DISCOVERY feeds
only. Their domains must never appear as citations in data/agencies.json:
every status change must rest on an independently fetched primary or news
source, never on a feed entry. Referenced by docs/METHODOLOGY.md.
"""
import json
import os
import sys
import unittest
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PATH = os.path.join(REPO_ROOT, "data", "agencies.json")

# Discovery-only feed domains. A citation URL on any of these is a hard fail.
FEED_DOMAINS = frozenset({
    "findingflock.com",
    "www.findingflock.com",
    "atlasofsurveillance.org",
    "www.atlasofsurveillance.org",
})


def host_of(url):
    try:
        return urllib.parse.urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        return ""


class TestFeedIsolation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(DATA_PATH, encoding="utf-8") as f:
            cls.data = json.load(f)["agencies"]

    def test_no_citation_on_feed_domains(self):
        bad = []
        for a in self.data:
            for s in a.get("sources", []):
                host = host_of(s.get("url", ""))
                if host in FEED_DOMAINS or host.replace("www.", "") in FEED_DOMAINS:
                    bad.append((a["id"], s.get("url")))
        self.assertEqual(bad, [], f"feed-domain citations (must be discovery-only): {bad}")

    def test_feed_domains_constant_covers_www(self):
        self.assertIn("findingflock.com", FEED_DOMAINS)
        self.assertIn("atlasofsurveillance.org", FEED_DOMAINS)


if __name__ == "__main__":
    unittest.main()
