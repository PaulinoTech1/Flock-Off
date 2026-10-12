"""Tests for classify_sources.promote_domain (evidence-then-apply)."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import classify_sources as cs


FLOCKOFF_YAML = """classify:
  verified_news:
    - aaa-news.com
    - zzz-news.com
  verified_primary:
    - city.gov
  pending_classify:
    - test-promote.example
    - other-pending.example  # a comment to preserve
  unverified:
    - blog.example
"""

APPROVALS_YAML = """# header comment
approvals:
  aaa-news.com:
    tier: verified_news
    approved_by: grandfather-policy
    date: 2026-09-26
    rationale: "old"
"""


class TestPromote(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="flockoff-promote-test-")
        self.addCleanup(__import__("shutil").rmtree, self.tmp,
                        ignore_errors=True)
        os.makedirs(os.path.join(self.tmp, "config"))
        os.makedirs(os.path.join(self.tmp, "data"))
        with open(os.path.join(self.tmp, "config", "flock-off.yaml"), "w") as f:
            f.write(FLOCKOFF_YAML)
        with open(os.path.join(self.tmp, "config", "domain_approvals.yaml"), "w") as f:
            f.write(APPROVALS_YAML)
        data = {"agencies": [{
            "id": "test-ag",
            "sources": [
                {"title": "Flock story one", "url": "https://test-promote.example/a",
                 "date": "2026-10-01", "verified": False},
                {"title": "Flock story two", "url": "https://test-promote.example/b",
                 "date": "2026-10-05", "verified": False},
            ]}]}
        with open(os.path.join(self.tmp, "data", "agencies.json"), "w") as f:
            json.dump(data, f)
        self._orig_cfg = cs._cfg_cache
        cs._cfg_cache = {
            "_repo_root": self.tmp,
            "paths": {"data": os.path.join(self.tmp, "data", "agencies.json")},
            "classify": {
                "verified_news": ["aaa-news.com", "zzz-news.com"],
                "verified_primary": ["city.gov"],
                "pending_classify": ["test-promote.example",
                                     "other-pending.example"],
                "unverified": ["blog.example"],
            },
        }

    def tearDown(self):
        cs._cfg_cache = self._orig_cfg

    def test_promote_moves_domain_and_records_approval(self):
        cs.promote_domain("test-promote.example", "verified_news",
                          "test rationale", approved_by="Tester",
                          assume_yes=True)
        with open(os.path.join(self.tmp, "config", "flock-off.yaml")) as f:
            content = f.read()
        # Removed from pending, added to verified_news sorted.
        self.assertNotIn("test-promote.example\n", content.split(
            "pending_classify:")[1].split("unverified:")[0].replace(
                "    - test-promote.example", ""))
        self.assertIn("    - test-promote.example\n", content)
        # Comment on the other pending domain survived.
        self.assertIn("# a comment to preserve", content)
        # Sorted position: between aaa-news.com and zzz-news.com.
        news_section = content.split("verified_news:")[1].split(
            "verified_primary:")[0]
        self.assertLess(news_section.index("aaa-news.com"),
                        news_section.index("test-promote.example"))
        self.assertLess(news_section.index("test-promote.example"),
                        news_section.index("zzz-news.com"))
        # Approval recorded.
        with open(os.path.join(self.tmp, "config", "domain_approvals.yaml")) as f:
            approvals = f.read()
        self.assertIn("test-promote.example:", approvals)
        self.assertIn("tier: verified_news", approvals)
        self.assertIn("approved_by: Tester", approvals)
        self.assertIn("test rationale", approvals)

    def test_promote_rejects_non_pending_domain(self):
        with self.assertRaises(SystemExit):
            cs.promote_domain("aaa-news.com", "verified_news",
                              "rationale", assume_yes=True)

    def test_promote_requires_rationale(self):
        with self.assertRaises(SystemExit):
            cs.promote_domain("test-promote.example", "verified_news",
                              "  ", assume_yes=True)

    def test_promote_rejects_bad_tier(self):
        with self.assertRaises(SystemExit):
            cs.promote_domain("test-promote.example", "verified_mars",
                              "rationale", assume_yes=True)


if __name__ == "__main__":
    unittest.main()
