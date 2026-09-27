"""Tests for the release manifest (data/integrity/manifest.json).

The manifest binds a dataset release to its SHA-256, timestamp, and source
commit. The build and the in-browser "Verify data integrity" widget both
consume it, so these invariants are load-bearing:
  - required keys present
  - agencies_sha256 is the actual SHA-256 of data/agencies.json on disk
"""
import hashlib
import json
import os
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MANIFEST_PATH = os.path.join(REPO_ROOT, "data", "integrity", "manifest.json")
DATA_PATH = os.path.join(REPO_ROOT, "data", "agencies.json")


def _manifest():
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        return json.load(f)


class TestManifest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = _manifest()
        with open(DATA_PATH, "rb") as f:
            cls.actual_sha256 = hashlib.sha256(f.read()).hexdigest()

    def test_required_keys(self):
        for key in ("agencies_sha256", "timestamp", "commit", "signer",
                    "signature"):
            self.assertIn(key, self.manifest, f"manifest missing {key}")

    def test_hash_matches_dataset_on_disk(self):
        self.assertEqual(self.manifest["agencies_sha256"], self.actual_sha256,
                         "manifest hash does not match data/agencies.json; "
                         "regenerate with scripts/sign_manifest.py")

    def test_hash_is_sha256_hex(self):
        h = self.manifest["agencies_sha256"]
        self.assertRegex(h, r"^[0-9a-f]{64}$")

    def test_timestamp_is_iso8601(self):
        from datetime import datetime
        ts = self.manifest["timestamp"]
        self.assertIsNotNone(ts)
        datetime.fromisoformat(ts)  # raises if malformed


class TestSignVerifyRoundTrip(unittest.TestCase):
    """End-to-end sign -> verify with a throwaway key.

    Guards the two historical bugs: the signature covering a different
    timestamp than the one shipped in the manifest, and 'signer' recording
    a key path instead of the public-key fingerprint.
    """

    def test_round_trip(self):
        import shutil
        import subprocess
        import sys
        import tempfile

        script = os.path.join(REPO_ROOT, "scripts", "sign_manifest.py")
        with tempfile.TemporaryDirectory() as td:
            key = os.path.join(td, "key")
            r = subprocess.run(
                ["ssh-keygen", "-t", "ed25519", "-f", key, "-N", "",
                 "-C", "flock-off-test"], capture_output=True, timeout=30)
            self.assertEqual(r.returncode, 0, "ssh-keygen keygen failed")

            backup = os.path.join(td, "manifest.backup.json")
            shutil.copy2(MANIFEST_PATH, backup)
            try:
                r = subprocess.run(
                    [sys.executable, script, "--sign", "--key", key,
                     "--commit", "testcommit"],
                    capture_output=True, text=True, timeout=60)
                self.assertEqual(r.returncode, 0, f"sign failed: {r.stderr}")
                signed = _manifest()
                self.assertTrue(signed["signature"],
                                "signature missing after --sign")
                self.assertRegex(signed["signer"] or "", r"^SHA256:",
                                 "signer must be a key fingerprint, "
                                 "not a key path")

                r = subprocess.run(
                    [sys.executable, script, "--verify",
                     "--pubkey", key + ".pub"],
                    capture_output=True, text=True, timeout=60)
                self.assertEqual(r.returncode, 0,
                                 f"verify failed: {r.stderr or r.stdout}")

                # Tamper with one byte of the payload: verify must fail.
                tampered = dict(signed)
                tampered["timestamp"] = "2000-01-01T00:00:00+00:00"
                with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
                    json.dump(tampered, f)
                r = subprocess.run(
                    [sys.executable, script, "--verify",
                     "--pubkey", key + ".pub"],
                    capture_output=True, text=True, timeout=60)
                self.assertNotEqual(r.returncode, 0,
                                    "verify accepted a tampered manifest")
            finally:
                shutil.copy2(backup, MANIFEST_PATH)


class TestReleasedSignature(unittest.TestCase):
    """Once the maintainer's public key is published at
    data/integrity/pubkey.pub, every manifest must carry a signature that
    verifies against it. Before the key exists (bootstrap mode) this test
    skips: an unsigned manifest is the honest current state, not a failure.
    """

    PUBKEY_PATH = os.path.join(REPO_ROOT, "data", "integrity", "pubkey.pub")

    def test_signature_verifies_when_key_published(self):
        if not os.path.isfile(self.PUBKEY_PATH):
            self.skipTest("no pubkey.pub yet: signing not set up (bootstrap)")
        import subprocess
        import sys

        manifest = _manifest()
        self.assertTrue(manifest.get("signature"),
                        "pubkey.pub exists but the manifest is unsigned; "
                        "complete the signing ceremony in docs/RELEASE_SIGNING.md")
        script = os.path.join(REPO_ROOT, "scripts", "sign_manifest.py")
        r = subprocess.run(
            [sys.executable, script, "--verify", "--pubkey", self.PUBKEY_PATH],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0,
                         f"signed manifest FAILED verification: "
                         f"{r.stderr or r.stdout}")


if __name__ == "__main__":
    unittest.main()
