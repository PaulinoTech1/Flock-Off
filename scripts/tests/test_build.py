"""Tests for scripts/vercel_build.py: the Vercel build-time transforms.

The build must pre-render tracker rows + source cards into index.html and
inject the agency-id allowlist into api/report.js, byte-identical to the
dataset. It must fail closed (nonzero exit) when a marker is missing so
Vercel never publishes a degraded site.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BUILD_SCRIPT = os.path.join(REPO_ROOT, "scripts", "vercel_build.py")


def _copy_repo():
    tmp = tempfile.mkdtemp(prefix="flockoff-build-")
    for name in ("index.html", "api", "data", "scripts"):
        src = os.path.join(REPO_ROOT, name)
        dst = os.path.join(tmp, name)
        if os.path.isdir(src):
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(src, dst)
    return tmp


def _run_build(repo_dir):
    script = os.path.join(repo_dir, "scripts", "vercel_build.py")
    return subprocess.run(
        [sys.executable, script], capture_output=True, text=True, timeout=60
    )


class TestVercelBuild(unittest.TestCase):
    def test_markers_present_in_source_tree(self):
        html = open(os.path.join(REPO_ROOT, "index.html"), encoding="utf-8").read()
        self.assertIn("<!--PRE_RENDER_ROWS-->", html)
        self.assertIn("<!--PRE_RENDER_SOURCES-->", html)
        report = open(os.path.join(REPO_ROOT, "api", "report.js"), encoding="utf-8").read()
        self.assertIn("/*__AGENCY_IDS__*/[]", report)

    def test_vercel_json_points_at_build_script(self):
        cfg = json.load(open(os.path.join(REPO_ROOT, "vercel.json"), encoding="utf-8"))
        self.assertEqual(cfg.get("buildCommand"), "python3 scripts/vercel_build.py")

    def test_build_prerenders_all_agencies(self):
        tmp = _copy_repo()
        try:
            proc = _run_build(tmp)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            agencies = json.load(
                open(os.path.join(tmp, "data", "agencies.json"), encoding="utf-8")
            )["agencies"]
            html = open(os.path.join(tmp, "index.html"), encoding="utf-8").read()
            self.assertNotIn("PRE_RENDER_ROWS", html)
            self.assertNotIn("PRE_RENDER_SOURCES", html)
            # One <tr> per agency plus the table header row.
            self.assertEqual(html.count("<tr>"), len(agencies) + 1)
            report = open(os.path.join(tmp, "api", "report.js"), encoding="utf-8").read()
            self.assertNotIn("__AGENCY_IDS__*/[]", report)
            for a in agencies:
                self.assertIn('"%s"' % a["id"], report)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_build_fails_closed_on_missing_marker(self):
        tmp = _copy_repo()
        try:
            html_path = os.path.join(tmp, "index.html")
            html = open(html_path, encoding="utf-8").read()
            open(html_path, "w", encoding="utf-8").write(
                html.replace("<!--PRE_RENDER_ROWS-->", "<!--GONE-->")
            )
            proc = _run_build(tmp)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("marker", proc.stderr + proc.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
