"""Tests for the domain-promotion quarantine.

Every domain in classify.verified_news / classify.verified_primary must have
an entry in config/domain_approvals.yaml naming the approver, date, and
rationale. New domains enter via classify.pending_classify (one full weekly
monitor cycle minimum) and classify as "quarantine-pending" (unverified)
until the approval entry exists. The human side (second-person review,
waiting the cycle) is the maintainer's responsibility; this suite enforces
that the approval RECORD exists and that quarantine classifies fail-closed.
"""
import os
import sys
import unittest

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import classify_sources as cs
from flockoff_config import load_config

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APPROVALS_PATH = os.path.join(REPO_ROOT, "config", "domain_approvals.yaml")


def _approvals():
    with open(APPROVALS_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)["approvals"]


class TestDomainApprovals(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = load_config()
        cls.approvals = _approvals()

    def test_every_verified_domain_has_approval(self):
        domains = (set(self.cfg["classify"]["verified_news"])
                   | set(self.cfg["classify"]["verified_primary"]))
        missing = sorted(d for d in domains if d not in self.approvals)
        self.assertEqual(missing, [],
                         f"verified domains without approval record: {missing}")

    def test_approval_entries_have_required_fields(self):
        bad = []
        for dom, entry in self.approvals.items():
            for field in ("tier", "approved_by", "date", "rationale"):
                if not entry.get(field):
                    bad.append((dom, field))
            if entry.get("tier") not in ("verified_news", "verified_primary"):
                bad.append((dom, "tier value"))
        self.assertEqual(bad, [], f"malformed approval entries: {bad}")

    def test_no_approval_for_unverified_tier(self):
        unverified = set(self.cfg["classify"]["unverified"])
        overlap = sorted(d for d in unverified if d in self.approvals)
        self.assertEqual(overlap, [],
                         f"unverified domains must not hold approvals: {overlap}")

    def test_no_duplicate_domain_across_tiers(self):
        news = set(self.cfg["classify"]["verified_news"])
        primary = set(self.cfg["classify"]["verified_primary"])
        self.assertEqual(news & primary, set())

    def test_pending_classify_is_list(self):
        pending = self.cfg["classify"].get("pending_classify")
        self.assertIsInstance(pending, list)

    def test_pending_classify_not_in_verified_tiers(self):
        pending = set(self.cfg["classify"].get("pending_classify") or [])
        verified = (set(self.cfg["classify"]["verified_news"])
                    | set(self.cfg["classify"]["verified_primary"]))
        self.assertEqual(pending & verified, set(),
                         "quarantined domains must not also be verified")


class TestQuarantineClassification(unittest.TestCase):
    def test_quarantine_domain_classifies_unverified(self):
        # Temporarily quarantine a known-verified domain and confirm the
        # classifier fails closed while it is quarantined.
        real = cs._domains
        cfg = load_config()
        patched = {k: v for k, v in cfg["classify"].items()}
        patched["pending_classify"] = ["example-news.com"]
        patched["verified_news"] = [d for d in patched["verified_news"]
                                    if d != "example-news.com"]
        cs._cfg_cache = {"classify": patched}
        try:
            verified, reason = cs.classify("https://example-news.com/story")
            self.assertFalse(verified)
            self.assertEqual(reason, "quarantine-pending")
        finally:
            cs._cfg_cache = None
            cs._domains = real


if __name__ == "__main__":
    unittest.main()
