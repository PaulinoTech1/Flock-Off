"""Tests for the one-command release (scripts/flockoff.py release).

Exercises `release --dry-run` end to end (pre-flight, sign, verify, stop
before push) with a throwaway key, so the repo's real pipeline key and
pubkey.pub are never touched: both are swapped out and restored.

Recursion note: `release` runs the test suite as a pre-flight step, and
this test runs `release`. The FLOCKOFF_RELEASE_SELFTEST guard makes the
inner release skip its own test step; without it the two would recurse
forever. See cmd_release in scripts/flockoff.py.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FLOCKOFF = os.path.join(REPO_ROOT, "scripts", "flockoff.py")
MANIFEST_PATH = os.path.join(REPO_ROOT, "data", "integrity", "manifest.json")
PUBKEY_PATH = os.path.join(REPO_ROOT, "data", "integrity", "pubkey.pub")


class TestReleaseDryRun(unittest.TestCase):
    def test_dry_run_signs_and_verifies(self):
        with tempfile.TemporaryDirectory() as td:
            key = os.path.join(td, "key")
            r = subprocess.run(
                ["ssh-keygen", "-t", "ed25519", "-f", key, "-N", "",
                 "-C", "release-test"], capture_output=True, timeout=30)
            self.assertEqual(r.returncode, 0, "ssh-keygen keygen failed")

            manifest_backup = os.path.join(td, "manifest.backup.json")
            shutil.copy2(MANIFEST_PATH, manifest_backup)
            pubkey_backup = os.path.join(td, "pubkey.backup.pub")
            pubkey_existed = os.path.isfile(PUBKEY_PATH)
            if pubkey_existed:
                shutil.copy2(PUBKEY_PATH, pubkey_backup)
            try:
                shutil.copy2(key + ".pub", PUBKEY_PATH)
                env = dict(os.environ)
                env["FLOCK_OFF_SIGNING_KEY"] = key
                env["FLOCKOFF_RELEASE_SELFTEST"] = "1"
                r = subprocess.run(
                    [sys.executable, FLOCKOFF, "release",
                     "--dry-run", "--message", "self-test"],
                    capture_output=True, text=True, timeout=300,
                    cwd=REPO_ROOT, env=env)
                out = (r.stdout or "") + (r.stderr or "")
                self.assertEqual(r.returncode, 0,
                                 f"release --dry-run failed:\n{out[-2000:]}")
                self.assertIn("release: pre-flight checks passed", out)
                self.assertIn("release: manifest signed and verified", out)
                self.assertIn("stopping before push", out)

                # The manifest left behind must verify against the
                # throwaway pubkey: the sign step produced a real signature.
                r = subprocess.run(
                    [sys.executable,
                     os.path.join(REPO_ROOT, "scripts", "sign_manifest.py"),
                     "--verify", "--pubkey", key + ".pub"],
                    capture_output=True, text=True, timeout=60)
                self.assertEqual(r.returncode, 0,
                                 "signed manifest failed verification")
            finally:
                shutil.copy2(manifest_backup, MANIFEST_PATH)
                if pubkey_existed:
                    shutil.copy2(pubkey_backup, PUBKEY_PATH)
                elif os.path.isfile(PUBKEY_PATH):
                    os.remove(PUBKEY_PATH)


if __name__ == "__main__":
    unittest.main()
