#!/usr/bin/env python3
"""Release-integrity manifest for the Flock-Off dataset.

Produces data/integrity/manifest.json:

    {
      "agencies_sha256": "<sha256 of data/agencies.json>",
      "timestamp": "<UTC ISO time of generation>",
      "commit": "<git HEAD the hash was taken at>",
      "signer": "<key fingerprint or null>",
      "signature": "<ssh-keygen -Y sign armor or null>"
    }

Usage:
    python3 scripts/sign_manifest.py              # regenerate (unsigned)
    python3 scripts/sign_manifest.py --sign --key ~/.ssh/id_ed25519
                                                 # regenerate + SSH-sign
    python3 scripts/sign_manifest.py --verify --pubkey data/integrity/pubkey.pub
                                                 # verify a signed manifest

Offline signing ceremony (the private key never leaves the signer's
machine, and no agent in the release pipeline ever sees it):

    1. Pipeline: python3 scripts/sign_manifest.py --payload-out /tmp/payload.bin
       # writes the unsigned manifest AND the exact canonical bytes to sign.
    2. Signer (their own machine, their own key):
         ssh-keygen -Y sign -f ~/.ssh/id_ed25519 -n flock-off-dataset \
           < /tmp/payload.bin > /tmp/manifest.sig
       # /tmp/manifest.sig is public signature armor; safe to send back.
    3. Pipeline: python3 scripts/sign_manifest.py --embed-sig /tmp/manifest.sig \
                     --pubkey data/integrity/pubkey.pub
       # embeds the armor, records the signer's key fingerprint, verifies,
       # and writes the manifest. Refuses to write if verification fails.

The maintainer's public key lives at data/integrity/pubkey.pub once
published. Until it exists, the push gate treats releases as unsigned
(bootstrap mode); once it exists, pushing a data change with an unsigned
or badly signed manifest is refused.

Streamlined mode: set FLOCK_OFF_SIGNING_KEY to the private key path and
`--sign` needs no arguments; the key is passed straight to ssh-keygen and
never appears in logs or output. See docs/RELEASE_SIGNING.md for the
trade-off between a pipeline-held signing key and the manual ceremony
above.

Signing model: the signature is a detached SSH signature (ssh-keygen -Y sign,
namespace "flock-off-dataset") over the CANONICAL UNSIGNED payload, i.e. the
manifest JSON with "signer" and "signature" set to null, dumped with
sort_keys=True and separators=(",", ":"). To verify by hand:

    python3 -c "
    import json
    m = json.load(open('data/integrity/manifest.json'))
    sig = m.pop('signature'); m['signer'] = None; m['signature'] = None
    open('/tmp/payload','wb').write(json.dumps(m, sort_keys=True,
        separators=(',',':')).encode())
    open('/tmp/sig.asc','w').write(sig)"
    printf 'flock-off-maintainer %s\n' "$(cat data/integrity/pubkey.pub)" \
        > /tmp/allowed_signers
    ssh-keygen -Y verify -f /tmp/allowed_signers -I flock-off-maintainer \
        -n flock-off-dataset -s /tmp/sig.asc < /tmp/payload

The maintainer's public key lives at data/integrity/pubkey.pub once published.
Key material never leaves the signer's machine: --key is only ever passed as
a path to ssh-keygen, which reads it directly.

The manifest binds a dataset hash to a point in time. The Tools tab on the
site ("Verify data integrity") recomputes the hash client-side and compares
it, so anyone can confirm the published JSON matches what the maintainer
released. What the hash does NOT prove: that the hosting origin itself is
uncompromised (a compromised host could serve a matching pair). The
signature, when present, additionally binds the manifest to the
maintainer's key.

Regenerate on every data change; scripts/tests/test_manifest.py fails if
the manifest hash does not match data/agencies.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "agencies.json"
OUT_DIR = ROOT / "data" / "integrity"
MANIFEST = OUT_DIR / "manifest.json"
NAMESPACE = "flock-off-dataset"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def git_head() -> str | None:
    try:
        p = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True,
            cwd=ROOT, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return p.stdout.strip() or None if p.returncode == 0 else None


def ssh_sign(payload: bytes, key_path: str) -> str:
    """Detached SSH signature via ssh-keygen -Y sign (never handles key material
    beyond passing the path to ssh-keygen, which uses the local agent/file)."""
    p = subprocess.run(
        ["ssh-keygen", "-Y", "sign", "-f", key_path, "-n", NAMESPACE],
        input=payload, capture_output=True, timeout=30,
    )
    if p.returncode != 0:
        sys.exit(f"signing failed: {p.stderr.decode(errors='replace')[:300]}")
    return p.stdout.decode()


def ssh_pubkey_fingerprint(key_path: str, pubkey_path: str | None) -> str:
    """SHA256 fingerprint of the public key (what 'signer' records)."""
    pub = pubkey_path or (key_path + ".pub")
    p = subprocess.run(["ssh-keygen", "-lf", pub],
                       capture_output=True, text=True, timeout=10)
    if p.returncode != 0:
        sys.exit(f"cannot read public key {pub}: "
                 f"{p.stderr.strip()[:200]} (pass --pubkey PATH)")
    # "256 SHA256:AbC... user@host (ED25519)"
    return p.stdout.split()[1]


def canonical_unsigned(manifest: dict) -> bytes:
    """The exact bytes the signature covers: signer/signature nulled."""
    m = dict(manifest)
    m["signer"] = None
    m["signature"] = None
    return json.dumps(m, sort_keys=True, separators=(",", ":")).encode()


def verify_manifest(manifest: dict, pubkey_path: str) -> bool:
    """Verify manifest['signature'] against the canonical unsigned payload."""
    import tempfile
    if not manifest.get("signature"):
        print("manifest is not signed")
        return False
    pub = Path(pubkey_path).read_text(encoding="utf-8").strip().split()
    if len(pub) < 2:
        sys.exit(f"malformed public key in {pubkey_path}")
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        (tdp / "payload").write_bytes(canonical_unsigned(manifest))
        (tdp / "sig.asc").write_text(manifest["signature"], encoding="utf-8")
        (tdp / "allowed").write_text(
            f"flock-off-maintainer {pub[0]} {pub[1]}\n", encoding="utf-8")
        p = subprocess.run(
            ["ssh-keygen", "-Y", "verify", "-f", str(tdp / "allowed"),
             "-I", "flock-off-maintainer", "-n", NAMESPACE,
             "-s", str(tdp / "sig.asc")],
            input=(tdp / "payload").read_text(encoding="utf-8"),
            capture_output=True, text=True, timeout=30)
    print(p.stderr.strip() or p.stdout.strip())
    return p.returncode == 0


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Generate the dataset release manifest.")
    ap.add_argument("--sign", action="store_true",
                    help="SSH-sign the manifest with --key")
    ap.add_argument("--key", default=None,
                    help="private key path for ssh-keygen -Y sign "
                         "(default: $FLOCK_OFF_SIGNING_KEY)")
    ap.add_argument("--pubkey", default=None,
                    help="public key path (default: --key + '.pub')")
    ap.add_argument("--verify", action="store_true",
                    help="verify an existing signed manifest against --pubkey")
    ap.add_argument("--payload-out", default=None, metavar="PATH",
                    help="also write the canonical unsigned payload bytes to "
                         "PATH for offline signing (step 1 of the ceremony)")
    ap.add_argument("--embed-sig", default=None, metavar="SIGFILE",
                    help="embed detached signature armor from SIGFILE, set "
                         "the signer fingerprint from --pubkey, verify, and "
                         "write (step 3 of the ceremony; refuses to write on "
                         "verification failure)")
    ap.add_argument("--commit", default=None,
                    help="commit SHA to record (defaults to local git HEAD, "
                         "if any; this tree has no local .git, so pass the "
                         "GitHub HEAD explicitly)")
    args = ap.parse_args(argv)

    if args.verify:
        if not MANIFEST.is_file():
            sys.exit(f"no manifest: {MANIFEST}")
        if not args.pubkey:
            sys.exit("--verify requires --pubkey PATH")
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        ok = verify_manifest(manifest, args.pubkey)
        sys.exit(0 if ok else 1)

    if args.embed_sig:
        # Ceremony step 3: embed a detached signature produced offline.
        if args.sign:
            sys.exit("--embed-sig cannot be combined with --sign")
        if not args.pubkey:
            sys.exit("--embed-sig requires --pubkey PATH")
        if not MANIFEST.is_file():
            sys.exit(f"no manifest: {MANIFEST} (run without --embed-sig first)")
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        sig_path = Path(args.embed_sig)
        if not sig_path.is_file():
            sys.exit(f"signature file not found: {sig_path}")
        armor = sig_path.read_text(encoding="utf-8")
        if "SIGNATURE" not in armor:
            sys.exit(f"{sig_path} does not look like ssh-keygen -Y sign armor")
        manifest["signature"] = armor
        manifest["signer"] = ssh_pubkey_fingerprint(None, args.pubkey)
        if not verify_manifest(manifest, args.pubkey):
            sys.exit("refusing to write: embedded signature FAILED verification")
        MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n",
                            encoding="utf-8")
        print(f"signed manifest written: {MANIFEST}")
        print(f"  signer: {manifest['signer']}")
        return

    if not DATA_PATH.is_file():
        sys.exit(f"missing dataset: {DATA_PATH}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Build the unsigned payload ONCE: the signature must cover exactly the
    # timestamp that ships in the manifest, so both are derived here.
    manifest = {
        "agencies_sha256": sha256_file(DATA_PATH),
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "commit": args.commit if args.commit else git_head(),
        "signer": None,
        "signature": None,
    }
    if args.sign:
        key_path = args.key or os.environ.get("FLOCK_OFF_SIGNING_KEY")
        if not key_path:
            sys.exit("--sign requires --key PATH or $FLOCK_OFF_SIGNING_KEY")
        manifest["signature"] = ssh_sign(canonical_unsigned(manifest), key_path)
        manifest["signer"] = ssh_pubkey_fingerprint(key_path, args.pubkey)

    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"manifest written: {MANIFEST}")
    print(f"  sha256: {manifest['agencies_sha256']}")
    print(f"  commit: {manifest['commit']}")
    print(f"  signed: {'yes' if manifest['signature'] else 'no (run with --sign --key to sign)'}"
          + (f"\n  signer: {manifest['signer']}" if manifest["signer"] else ""))
    if args.payload_out:
        # Ceremony step 1: the exact bytes the signer must sign.
        Path(args.payload_out).write_bytes(canonical_unsigned(manifest))
        print(f"  signing payload: {args.payload_out} "
              f"({len(canonical_unsigned(manifest))} bytes)")


if __name__ == "__main__":
    main()
