#!/usr/bin/env python3
"""Single entry point for the Flock-Off maintenance pipeline.

Replaces remembering four scripts and their flags:

    python3 scripts/flockoff.py keys check
    python3 scripts/flockoff.py keys backfill
    python3 scripts/flockoff.py fingerprints refresh [--max N] [--max-age-days D] [--keys k1,k2]
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


def cmd_fingerprints(args, _cfg) -> None:
    import source_fingerprints
    argv = ["--refresh"]
    if args.max is not None:
        argv += ["--max", str(args.max)]
    if args.max_age_days is not None:
        argv += ["--max-age-days", str(args.max_age_days)]
    if args.keys:
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

    cl = sub.add_parser("classify", help="source evidence-tier classification")
    cl.add_argument("--check", action="store_true",
                    help="report only, do not modify data files")

    m = sub.add_parser("monitor", help="run the weekly monitor")
    m.add_argument("local_dataset", nargs="?",
                   help="local agencies.json fallback if the GitHub fetch fails")
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
        ("classify", None): cmd_classify,
        ("monitor", None): cmd_monitor,
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
