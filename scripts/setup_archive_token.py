#!/usr/bin/env python3
"""Set up ARCHIVE_BLOB_READ_WRITE_TOKEN for the Flock-Off pipeline.

Prompts securely for the token (no echo), validates the format,
and stores it in ~/.config/flock-off/archive.env with 0600 permissions.
Source that file in your shell profile, or export the variable directly.

Usage:
    python3 scripts/setup_archive_token.py
"""

import getpass
import os
import stat
import sys

CONFIG_DIR = os.path.expanduser("~/.config/flock-off")
ENV_FILE = os.path.join(CONFIG_DIR, "archive.env")
TOKEN_VAR = "ARCHIVE_BLOB_READ_WRITE_TOKEN"


def main():
    print(f"{TOKEN_VAR} setup")
    print(f"Target file: {ENV_FILE}")
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
        print("error: empty token, nothing written.", file=sys.stderr)
        sys.exit(1)
    if len(token) < 20:
        print("error: token looks too short to be valid.", file=sys.stderr)
        sys.exit(1)
    if any(c.isspace() for c in token):
        print("error: token contains whitespace; check for copy/paste errors.",
              file=sys.stderr)
        sys.exit(1)

    os.makedirs(CONFIG_DIR, mode=0o700, exist_ok=True)
    # Write with 0600: owner read/write only
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write(f'export {TOKEN_VAR}="{token}"\n')
    os.chmod(ENV_FILE, stat.S_IRUSR | stat.S_IWUSR)

    print()
    print(f"Wrote {ENV_FILE} (0600).")
    print()
    print("To use it in your current shell:")
    print(f"    source {ENV_FILE}")
    print()
    print("To persist across sessions, add to ~/.profile or ~/.bashrc:")
    print(f"    echo 'source {ENV_FILE}' >> ~/.profile")
    print()
    print("Then verify with:")
    print("    python3 scripts/flockoff.py fingerprints refresh --max 5")
    print("No blob_archive WARNING lines means snapshots are uploading.")


if __name__ == "__main__":
    main()
