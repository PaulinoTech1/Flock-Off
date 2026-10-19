#!/usr/bin/env python3
"""Set up ARCHIVE_BLOB_READ_WRITE_TOKEN for the Flock-Off pipeline.

Prompts securely for the token (no echo), validates the format, and
stores it in the operating system keyring (macOS Keychain, Windows
Credential Locker, or a Linux Secret Service keyring) via the
`keyring` package. The token is never written to a file in clear text
(CodeQL py/clear-text-storage-sensitive-data, alert #1, fixed
2026-10-19).

blob_archive.py resolves the token from the environment variable
first (CI sets it from GitHub Secrets), then from the keyring.

Earlier versions of this script wrote the token in clear text to
~/.config/flock-off/archive.env (0600). Nothing reads that file; after
a successful keyring store this script removes it.

Usage:
    pip install keyring
    python3 scripts/setup_archive_token.py
"""

import getpass
import os
import sys

TOKEN_VAR = "ARCHIVE_BLOB_READ_WRITE_TOKEN"
# Keep in sync with KEYRING_SERVICE in scripts/blob_archive.py.
KEYRING_SERVICE = "flock-off"
LEGACY_ENV_FILE = os.path.expanduser("~/.config/flock-off/archive.env")


def _load_keyring():
    """Return the keyring module, or None if unavailable or backendless.

    A machine with no usable keyring backend (for example a headless
    Linux box with no Secret Service) counts as unavailable: storing
    there would fail or, worse, silently go nowhere.
    """
    try:
        import keyring
        import keyring.backends.fail
        if isinstance(keyring.get_keyring(), keyring.backends.fail.Keyring):
            return None
        return keyring
    except Exception:
        return None


def store_token(token):
    """Store the token in the OS keyring and verify the round-trip.

    Returns True on success. Returns False when no usable keyring is
    available; the caller must then fail closed (no clear-text file
    is ever written as a fallback).
    """
    keyring = _load_keyring()
    if keyring is None:
        return False
    try:
        keyring.set_password(KEYRING_SERVICE, TOKEN_VAR, token)
        return keyring.get_password(KEYRING_SERVICE, TOKEN_VAR) == token
    except Exception:
        return False


def remove_legacy_file():
    """Delete the legacy clear-text archive.env, if present.

    Returns the path when a file was removed, else None.
    """
    if os.path.exists(LEGACY_ENV_FILE):
        os.remove(LEGACY_ENV_FILE)
        return LEGACY_ENV_FILE
    return None


def main():
    print(f"{TOKEN_VAR} setup")
    print("Storage: operating system keyring (no clear-text file).")
    print()
    print("Paste the Read-Write token from your Vercel blob store dashboard.")
    print("Input is hidden. The value is never printed or logged.")
    print()

    try:
        token = getpass.getpass(f"{TOKEN_VAR}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.", file=sys.stderr)
        sys.exit(1)

    if not token:
        print("error: empty token, nothing stored.", file=sys.stderr)
        sys.exit(1)
    if len(token) < 20:
        print("error: token looks too short to be valid.", file=sys.stderr)
        sys.exit(1)
    if any(c.isspace() for c in token):
        print("error: token contains whitespace; check for copy/paste errors.",
              file=sys.stderr)
        sys.exit(1)

    if not store_token(token):
        print("error: no usable OS keyring available; nothing stored.",
              file=sys.stderr)
        print("Install one (`pip install keyring` plus a Secret Service "
              "provider such as gnome-keyring on Linux), or set "
              f"{TOKEN_VAR} in the environment from your secret manager "
              "instead. CI reads it from GitHub Secrets.",
              file=sys.stderr)
        sys.exit(1)

    removed = remove_legacy_file()
    print()
    print(f"Stored {TOKEN_VAR} in the OS keyring "
          f"(service {KEYRING_SERVICE!r}).")
    if removed:
        print(f"Removed legacy clear-text file {removed} "
              "(no longer read by anything).")
    print()
    print("blob_archive.py picks the token up automatically: the "
          "environment variable wins when set, the keyring is the "
          "local fallback.")
    print()
    print("Verify with:")
    print("    python3 scripts/flockoff.py fingerprints refresh --max 5")
    print("No blob_archive WARNING lines means snapshots are uploading.")


if __name__ == "__main__":
    main()
