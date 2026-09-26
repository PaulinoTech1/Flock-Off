"""Tests for scripts/flockoff_errors.py: the stable error-code registry.

Rule: any code surfaced by any script must be registered here with a
summary and a remediation. The meta-test below scans every script for
emitted codes and fails if one is missing, so the registry can never
drift out of sync with the code.
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flockoff_errors import fmt, REGISTRY

CODE_RE = re.compile(r"\b([EWI]_[A-Z][A-Z0-9_]{2,})\b")
SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestRegistryIntegrity(unittest.TestCase):
    def test_every_code_has_summary_and_remediation(self):
        for code, (kind, summary, remediation) in REGISTRY.items():
            self.assertTrue(summary, f"{code}: empty summary")
            self.assertTrue(remediation, f"{code}: empty remediation")
            self.assertIn(kind, ("error", "warning", "info"),
                          f"{code}: bad kind {kind!r}")

    def test_code_format(self):
        for code in REGISTRY:
            self.assertRegex(code, r"^[EWI]_[A-Z0-9_]+$")

    def test_fmt_includes_code_detail_remediation(self):
        out = fmt("E_KEY_DUP", "agency ma-boston-pd")
        self.assertIn("E_KEY_DUP", out)
        self.assertIn("agency ma-boston-pd", out)
        self.assertIn("duplicate source_key", out)
        self.assertIn("keys check", out)

    def test_fmt_unknown_code(self):
        out = fmt("E_NOPE", "x")
        self.assertIn("E_NOPE", out)
        self.assertIn("unknown code", out)

    def test_all_emitted_codes_are_registered(self):
        """Scan every script for emitted codes; each must be in REGISTRY."""
        offenders = []
        for fname in sorted(os.listdir(SCRIPTS_DIR)):
            if not fname.endswith(".py"):
                continue
            if fname.startswith("test") or os.sep + "tests" + os.sep in fname:
                continue
            path = os.path.join(SCRIPTS_DIR, fname)
            if os.path.isdir(path):
                continue
            with open(path, encoding="utf-8") as fh:
                src = fh.read()
            for code in set(CODE_RE.findall(src)):
                if code not in REGISTRY:
                    offenders.append(f"{fname}: {code}")
        self.assertEqual(offenders, [],
                         "unregistered error codes: " + "; ".join(offenders))


if __name__ == "__main__":
    unittest.main()
