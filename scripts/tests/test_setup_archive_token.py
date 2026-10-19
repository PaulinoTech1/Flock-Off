"""Tests for scripts/setup_archive_token.py (offline, fake keyring).

Regression coverage for CodeQL alert #1
(py/clear-text-storage-sensitive-data): the setup script must store
the token in the OS keyring, fail closed when no keyring is usable,
and never write the token to a file again.
"""

import os
import sys
import tempfile
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import setup_archive_token as sat


def _install_fake_keyring(store=None, fail_backend=False):
    """Install a fake `keyring` package into sys.modules.

    Returns the backing store dict. With fail_backend=True the active
    backend is the keyring fail backend, which _load_keyring must
    treat as unavailable.
    """
    if store is None:
        store = {}
    keyring = types.ModuleType("keyring")
    backends = types.ModuleType("keyring.backends")
    fail = types.ModuleType("keyring.backends.fail")

    class FailKeyring:
        pass

    class MemoryKeyring:
        pass

    fail.Keyring = FailKeyring
    backends.fail = fail
    keyring.backends = backends
    keyring.get_keyring = lambda: FailKeyring() if fail_backend else MemoryKeyring()
    keyring.set_password = lambda svc, var, val: store.__setitem__((svc, var), val)
    keyring.get_password = lambda svc, var: store.get((svc, var))
    sys.modules["keyring"] = keyring
    sys.modules["keyring.backends"] = backends
    sys.modules["keyring.backends.fail"] = fail
    return store


class TestStoreToken(unittest.TestCase):
    def setUp(self):
        self._saved = {k: sys.modules.get(k) for k in
                       ("keyring", "keyring.backends", "keyring.backends.fail")}

    def tearDown(self):
        for name, mod in self._saved.items():
            if mod is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = mod

    def test_store_round_trips_through_keyring(self):
        store = _install_fake_keyring()
        self.assertTrue(sat.store_token("vercel_blob_rw_testtoken"))
        self.assertEqual(store[(sat.KEYRING_SERVICE, sat.TOKEN_VAR)],
                         "vercel_blob_rw_testtoken")

    def test_fail_backend_is_unusable(self):
        _install_fake_keyring(fail_backend=True)
        self.assertFalse(sat.store_token("vercel_blob_rw_testtoken"))

    def test_missing_keyring_module_is_unusable(self):
        # sys.modules[name] = None makes the imports raise ImportError,
        # simulating keyring not being installed.
        for name in self._saved:
            sys.modules[name] = None
        self.assertFalse(sat.store_token("vercel_blob_rw_testtoken"))


class TestLegacyFile(unittest.TestCase):
    def test_remove_legacy_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "archive.env")
            old = sat.LEGACY_ENV_FILE
            sat.LEGACY_ENV_FILE = path
            try:
                self.assertIsNone(sat.remove_legacy_file())
                with open(path, "w", encoding="utf-8") as f:
                    f.write('export ARCHIVE_BLOB_READ_WRITE_TOKEN="x"\n')
                self.assertEqual(sat.remove_legacy_file(), path)
                self.assertFalse(os.path.exists(path))
                self.assertIsNone(sat.remove_legacy_file())
            finally:
                sat.LEGACY_ENV_FILE = old


class TestNoClearTextStorage(unittest.TestCase):
    def test_script_never_opens_a_file(self):
        # Tripwire for the alert: storing the token must go through the
        # keyring API only. The script has no legitimate reason to open
        # any file (the legacy file is removed via os.remove).
        src_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "setup_archive_token.py")
        with open(src_path, encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn("open(", src)


if __name__ == "__main__":
    unittest.main()
