#!/usr/bin/env python3
"""Single entry point for the Flock-Off maintenance pipeline.

Replaces remembering four scripts and their flags:

    python3 scripts/flockoff.py keys check
    python3 scripts/flockoff.py keys backfill
    python3 scripts/flockoff.py fingerprints refresh [--max N] [--max-age-days D] [--keys k1,k2]
    python3 scripts/flockoff.py fingerprints drift [--max N] [--keys k1,k2]
    python3 scripts/flockoff.py classify [--check]
    python3 scripts/flockoff.py monitor [local-dataset-fallback]
    python3 scripts/flockoff.py config validate

Global options:
    --config PATH   use a different config file (also: FLOCKOFF_CONFIG env)

All behavior is driven by config/flock-off.yaml (validated on load).
Error codes are documented in docs/ERRORS.md.
Run from anywhere; the dispatcher cds to the repo root for you.
"""
from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from flockoff_config import ConfigError, load_config  # noqa: E402


def _bootstrap(config_path: str | None) -> dict:
    """Load config, export it for submodules, cd to repo root."""
    if config_path:
        os.environ["FLOCKOFF_CONFIG"] = os.path.abspath(config_path)
    try:
        cfg = load_config()
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
    os.chdir(cfg["_repo_root"])
    return cfg


def cmd_config_validate(_args, cfg) -> None:
    print(f"config OK: {cfg['_config_path']}")


def cmd_keys(args, _cfg) -> None:
    import source_keys
    source_keys.main(["--check"] if args.check else [])


def cmd_snapshot(args, _cfg) -> None:
    """Retrieve a raw HTML snapshot from the blob archive by source key or
    content hash. Used in drift review to pull up the exact original page."""
    import blob_archive
    import json as _json

    chash = args.hash
    if not chash:
        # Look up the source key in the fingerprint database
        fp_path = os.path.join("data", "source_fingerprints.json")
        try:
            with open(fp_path, encoding="utf-8") as f:
                fps = _json.load(f)
        except (OSError, _json.JSONDecodeError) as e:
            print(f"error: cannot read {fp_path}: {e}", file=sys.stderr)
            sys.exit(1)
        rec = (fps.get("sources") or {}).get(args.key)
        if not rec:
            print(f"error: no fingerprint record for key: {args.key}",
                  file=sys.stderr)
            sys.exit(1)
        chash = rec.get("raw_snapshot_hash")
        if not chash:
            print(f"error: no raw snapshot archived for key: {args.key} "
                  f"(fetch_status={rec.get('fetch_status')})", file=sys.stderr)
            sys.exit(1)
        print(f"snapshot hash: {chash}", file=sys.stderr)

    try:
        html = blob_archive.get_snapshot(chash)
    except (ValueError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
    if html is None:
        print(f"snapshot not found in blob archive: {chash}", file=sys.stderr)
        sys.exit(1)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"wrote {len(html)} chars to {args.output}")
    else:
        sys.stdout.write(html)


def cmd_fingerprints(args, _cfg) -> None:
    import source_fingerprints
    if getattr(args, "fp_cmd", None) == "drift":
        argv = ["--drift"]
    elif getattr(args, "fp_cmd", None) == "backfill-archive":
        argv = ["--backfill-archive"]
    else:
        argv = ["--refresh"]
        if getattr(args, "max_age_days", None) is not None:
            argv += ["--max-age-days", str(args.max_age_days)]
    if getattr(args, "max", None) is not None:
        argv += ["--max", str(args.max)]
    if getattr(args, "keys", None):
        argv += ["--keys", args.keys]
    source_fingerprints.main(argv)


def cmd_classify(args, _cfg) -> None:
    import classify_sources
    classify_sources.main(["--check"] if args.check else [])


def cmd_monitor(args, _cfg) -> None:
    import weekly_monitor
    # weekly_monitor.main() reads sys.argv[1] as an optional local dataset
    # fallback when the GitHub fetch fails.
    sys.argv = ["weekly_monitor.py"] + ([args.local_dataset] if args.local_dataset else [])
    weekly_monitor.main()


def cmd_test(args, _cfg) -> None:
    import unittest
    loader = unittest.TestLoader()
    suite = loader.discover(os.path.join(HERE, "tests"), pattern=args.pattern)
    verbosity = 2 if args.verbose else 1
    result = unittest.TextTestRunner(verbosity=verbosity).run(suite)
    if not result.wasSuccessful():
        sys.exit(1)


def cmd_release(args, cfg) -> None:
    """One-command release: pre-flight checks, sign the manifest, push.

    Streamlined path for the weekly review: after quarantined items are
    approved and applied, this validates the tree, signs the release
    manifest with the pipeline key ($FLOCK_OFF_SIGNING_KEY), and pushes.
    The push helper re-runs the full release gate (including signature
    verification) before anything leaves the machine.

    --dry-run does everything except the push, for rehearsal.
    """
    import subprocess

    # The signing key lives outside the repo; pick it up from the standard
    # env file when it is not already in the environment.
    if not os.environ.get("FLOCK_OFF_SIGNING_KEY"):
        env_file = os.path.expanduser("~/.config/flock-off/release.env")
        if os.path.isfile(env_file):
            for line in open(env_file, encoding="utf-8"):
                line = line.strip()
                if line.startswith("export FLOCK_OFF_SIGNING_KEY="):
                    val = line.split("=", 1)[1].strip().strip("\"'")
                    val = val.replace("$HOME", os.path.expanduser("~"))
                    os.environ["FLOCK_OFF_SIGNING_KEY"] = val

    # 1. Pre-flight: same checks the push gate enforces, failed fast here
    #    so a broken tree never reaches the signing step. The subcommands
    #    signal via sys.exit; a zero exit means "passed", anything else
    #    aborts the release.
    def _preflight(fn, p_args, name):
        # Recursion guard: test_release.py exercises `release --dry-run`
        # via subprocess; without this, the inner release would re-run the
        # suite that is already running it.
        if name == "test" and os.environ.get("FLOCKOFF_RELEASE_SELFTEST"):
            print("release: pre-flight test step skipped (self-test)")
            return
        try:
            fn(p_args, cfg)
        except SystemExit as e:
            if e.code not in (0, None):
                raise SystemExit(
                    f"release: pre-flight {name} failed (exit {e.code})")
    _preflight(cmd_test,
               argparse.Namespace(pattern="test_*.py", verbose=False), "test")
    _preflight(cmd_keys, argparse.Namespace(check=True), "keys check")
    _preflight(cmd_classify, argparse.Namespace(check=True), "classify check")
    print("release: pre-flight checks passed")

    # 2. Sign the manifest with the pipeline key.
    import sign_manifest
    sign_argv = ["--sign"]
    if args.key:
        sign_argv += ["--key", args.key]
    sign_manifest.main(sign_argv)

    # 3. Verify the signature we just produced, against the published key.
    #    sign_manifest signals via sys.exit; swallow the zero exit.
    pubkey = os.path.join(cfg["_repo_root"], "data", "integrity", "pubkey.pub")
    if not os.path.isfile(pubkey):
        sys.exit("release: refusing to continue: data/integrity/pubkey.pub "
                 "is not published; see docs/RELEASE_SIGNING.md")
    try:
        sign_manifest.main(["--verify", "--pubkey", pubkey])
    except SystemExit as e:
        if e.code not in (0, None):
            raise SystemExit(f"release: signature verification failed "
                             f"(exit {e.code})")
    print("release: manifest signed and verified")

    if args.dry_run:
        print("release: --dry-run, stopping before push "
              f"(message would be: {args.message!r})")
        return

    # 4. Push. The helper runs release_gate() again (fail-closed) first.
    helper = os.path.expanduser("~/workspace/flock-off-deploy/github_push.py")
    if not os.path.isfile(helper):
        sys.exit(f"release: push helper not found: {helper}")
    r = subprocess.run([sys.executable, helper, args.message])
    if r.returncode != 0:
        sys.exit(f"release: push failed (exit {r.returncode})")
    print("release: pushed")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="flockoff.py",
        description="Flock-Off maintenance pipeline (config: config/flock-off.yaml).",
    )
    p.add_argument("--config", default=None,
                   help="config file path (overrides FLOCKOFF_CONFIG)")
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("config", help="config utilities")
    csub = c.add_subparsers(dest="config_cmd", required=True)
    csub.add_parser("validate", help="load and validate the config file")

    k = sub.add_parser("keys", help="Layer 1: source_key hygiene")
    ksub = k.add_subparsers(dest="keys_cmd", required=True)
    ksub.add_parser("check", help="fail on missing/stale/duplicate keys")
    ksub.add_parser("backfill", help="fill in missing or stale keys")

    f = sub.add_parser("fingerprints", help="Layers 2+3: content fingerprints")
    fsub = f.add_subparsers(dest="fp_cmd", required=True)
    r = fsub.add_parser("refresh", help="fetch missing/stale fingerprints")
    r.add_argument("--max", type=int, default=None)
    r.add_argument("--max-age-days", type=int, default=None)
    r.add_argument("--keys", default=None,
                   help="comma-separated source_keys to refresh")
    d = fsub.add_parser("drift",
                        help="fatal pre-push gate: fail on unreviewed drift")
    d.add_argument("--max", type=int, default=None,
                   help="cap how many sources to re-fetch")
    d.add_argument("--keys", default=None,
                   help="comma-separated source_keys to check")
    b = fsub.add_parser("backfill-archive",
                        help="snapshot extracted text for sources missing "
                             "an archive file")
    b.add_argument("--max", type=int, default=None,
                   help="cap how many sources to fetch")

    cl = sub.add_parser("classify", help="source evidence-tier classification")
    cl.add_argument("--check", action="store_true",
                    help="report only, do not modify data files")

    m = sub.add_parser("monitor", help="run the weekly monitor")
    m.add_argument("local_dataset", nargs="?",
                   help="local agencies.json fallback if the GitHub fetch fails")

    s = sub.add_parser("snapshot",
                       help="retrieve a raw HTML snapshot from the blob archive")
    s.add_argument("--key", default=None,
                   help="source key: look up its raw_snapshot_hash in "
                        "data/source_fingerprints.json")
    s.add_argument("--hash", default=None,
                   help="raw snapshot content hash directly (64-char hex)")
    s.add_argument("-o", "--output", default=None,
                   help="write to file instead of stdout")

    t = sub.add_parser("test", help="run the stdlib test suite (scripts/tests/)")
    t.add_argument("--pattern", default="test_*.py",
                   help="unittest discovery pattern")
    t.add_argument("-v", "--verbose", action="store_true",
                   help="verbose test output")

    r = sub.add_parser("release",
                       help="one-command release: pre-flight, sign, push")
    r.add_argument("--message", default="Update Flock-Off dataset",
                   help="commit message for the push")
    r.add_argument("--key", default=None,
                   help="signing key path (default: $FLOCK_OFF_SIGNING_KEY)")
    r.add_argument("--dry-run", action="store_true",
                   help="validate and sign, but do not push")
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    cfg = _bootstrap(args.config)

    handlers = {
        ("config", "validate"): cmd_config_validate,
        ("keys", "check"): lambda a, c: cmd_keys(argparse.Namespace(check=True), c),
        ("keys", "backfill"): lambda a, c: cmd_keys(argparse.Namespace(check=False), c),
        ("fingerprints", "refresh"): cmd_fingerprints,
        ("fingerprints", "drift"): cmd_fingerprints,
        ("fingerprints", "backfill-archive"): cmd_fingerprints,
        ("classify", None): cmd_classify,
        ("monitor", None): cmd_monitor,
        ("snapshot", None): cmd_snapshot,
        ("test", None): cmd_test,
        ("release", None): cmd_release,
    }
    key = (args.command,
           getattr(args, "config_cmd", None)
           or getattr(args, "keys_cmd", None)
           or getattr(args, "fp_cmd", None))
    handler = handlers.get(key)
    if handler is None:
        parser.error(f"unknown command path: {key}")
    handler(args, cfg)


if __name__ == "__main__":
    main()
