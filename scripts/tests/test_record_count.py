"""Regression tests for Finding F1: the Contracts tab record count must be
build-derived, never a hard-coded literal.

The count in the Contracts tab intro ("of N records") drifted from the
dataset (343 vs 344). scripts/vercel_build.py now injects it from the
agencies list it already loads, fail-closed on a missing marker. These
tests prove the rendered number follows the fixture: mutating the fixture
changes the output, which a hard-coded literal would not do.
"""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _load_build_module():
    path = os.path.join(REPO_ROOT, "scripts", "vercel_build.py")
    spec = importlib.util.spec_from_file_location("vercel_build_f1", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _copy_repo():
    tmp = tempfile.mkdtemp(prefix="flockoff-count-")
    for name in ("index.html", "api", "data", "scripts", "js", "css",
                 "config", "vendor"):
        src = os.path.join(REPO_ROOT, name)
        dst = os.path.join(tmp, name)
        if os.path.isdir(src):
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(src, dst)
    return tmp


class TestRecordCountInjection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build = _load_build_module()

    def test_count_follows_fixture(self):
        # Mutating the fixture must change the rendered count. A stale
        # hard-coded literal would render identically for both fixtures.
        html = "<p>of <!--RECORD_COUNT--> records, only the documents below.</p>"
        three = [{"id": "aa-test-1"}, {"id": "bb-test-2"}, {"id": "cc-test-3"}]
        out3 = self.build._inject_record_count(html, len(three))
        self.assertIn("of 3 records", out3)
        self.assertNotIn("RECORD_COUNT", out3)
        four = three + [{"id": "dd-test-4"}]
        out4 = self.build._inject_record_count(html, len(four))
        self.assertIn("of 4 records", out4)
        self.assertNotIn("of 3 records", out4)

    def test_missing_marker_is_left_alone_by_helper(self):
        # The helper only substitutes; main() fails closed on the missing
        # marker before this is reached (covered below).
        html = "<p>of many records</p>"
        self.assertEqual(self.build._inject_record_count(html, 99), html)

    def test_marker_present_in_source_tree(self):
        with open(os.path.join(REPO_ROOT, "index.html"), encoding="utf-8") as f:
            html = f.read()
        self.assertIn("<!--RECORD_COUNT-->", html)

    def test_no_hardcoded_record_count_literal(self):
        with open(os.path.join(REPO_ROOT, "index.html"), encoding="utf-8") as f:
            html = f.read()
        for m in re.finditer(r"of (\d+) records", html):
            self.fail("hard-coded record-count literal in index.html: %r" % m.group(0))

    def test_full_build_renders_dataset_count(self):
        tmp = _copy_repo()
        try:
            proc = subprocess.run(
                [sys.executable, os.path.join(tmp, "scripts", "vercel_build.py")],
                capture_output=True, text=True, timeout=120)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            agencies = json.load(
                open(os.path.join(tmp, "data", "agencies.json"), encoding="utf-8")
            )["agencies"]
            n = len(agencies)
            html = open(os.path.join(tmp, "index.html"), encoding="utf-8").read()
            self.assertIn("of %d records" % n, html)
            self.assertNotIn("RECORD_COUNT", html)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_full_build_count_tracks_mutated_dataset(self):
        # Remove one registry-free agency from the fixture dataset and
        # rebuild: the rendered count must drop by exactly one.
        tmp = _copy_repo()
        try:
            sys.path.insert(0, os.path.join(tmp, "scripts"))
            import contracts as contracts_mod
            import petitions as petitions_mod
            used = {row[0] for row in contracts_mod.REGISTRY}
            used |= {row[5] for row in petitions_mod.REGISTRY if row[5]}
            data_path = os.path.join(tmp, "data", "agencies.json")
            doc = json.load(open(data_path, encoding="utf-8"))
            agencies = doc["agencies"]
            victim = next(a for a in reversed(agencies) if a["id"] not in used)
            doc["agencies"] = [a for a in agencies if a["id"] != victim["id"]]
            json.dump(doc, open(data_path, "w", encoding="utf-8"))
            proc = subprocess.run(
                [sys.executable, os.path.join(tmp, "scripts", "vercel_build.py")],
                capture_output=True, text=True, timeout=120)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            html = open(os.path.join(tmp, "index.html"), encoding="utf-8").read()
            self.assertIn("of %d records" % (len(agencies) - 1), html)
        finally:
            for m in ("contracts", "petitions"):
                sys.modules.pop(m, None)
            if os.path.join(tmp, "scripts") in sys.path:
                sys.path.remove(os.path.join(tmp, "scripts"))
            shutil.rmtree(tmp, ignore_errors=True)

    def test_build_fails_closed_on_missing_count_marker(self):
        tmp = _copy_repo()
        try:
            html_path = os.path.join(tmp, "index.html")
            html = open(html_path, encoding="utf-8").read()
            open(html_path, "w", encoding="utf-8").write(
                html.replace("<!--RECORD_COUNT-->", "<!--GONE-->"))
            proc = subprocess.run(
                [sys.executable, os.path.join(tmp, "scripts", "vercel_build.py")],
                capture_output=True, text=True, timeout=120)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("marker", proc.stderr + proc.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
