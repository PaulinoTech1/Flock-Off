#!/usr/bin/env python3
"""Stamp every source in data/agencies.json with a verified true/false flag.

Classification is an explicit domain map in config/flock-off.yaml
(section "classify"), reviewed in git. Fail-closed: any domain not listed
stamps false. New sources added to the dataset get flagged by the weekly
monitor until classified in the config.

Criteria live in docs/METHODOLOGY.md ("Evidence bar"). In short:
  verified   = primary/official record, or established news outlet with an
               editorial process (bylines, corrections, masthead).
  unverified = advocacy orgs, social/video platforms, aggregators, AI
               summaries, personal blogs, unknown outlets. Usable as leads,
               never as citations toward the evidence bar.

Usage: python3 scripts/flockoff.py classify [--check]
  --check: exit 1 if any source lacks a verified flag (CI / monitor use).
"""
from __future__ import annotations

import json
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flockoff_config import ConfigError, load_config  # noqa: E402

_cfg_cache: dict | None = None


def _cfg() -> dict:
    """Load (once) the validated pipeline config."""
    global _cfg_cache
    if _cfg_cache is None:
        _cfg_cache = load_config()
    return _cfg_cache


def _domains() -> dict:
    return _cfg()["classify"]


def VERIFIED_NEWS() -> set[str]:
    return set(_domains()["verified_news"])


def VERIFIED_PRIMARY() -> set[str]:
    return set(_domains()["verified_primary"])


def UNVERIFIED() -> set[str]:
    return set(_domains()["unverified"])


def DATA_PATH() -> str:
    return _cfg()["paths"]["data"]


def CLASSIFICATION_PATH() -> str:
    return _cfg()["paths"]["classification"]


def classify(url: str) -> tuple[bool, str]:
    host = urllib.parse.urlparse(url).netloc.lower().replace("www.", "")
    if host in VERIFIED_NEWS():
        return True, "verified-news"
    if host in VERIFIED_PRIMARY():
        return True, "verified-primary"
    if host in UNVERIFIED():
        return False, "unverified-listed"
    return False, "unverified-unlisted"


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    check_only = "--check" in argv
    try:
        cfg = _cfg()
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
    data_path = cfg["paths"]["data"]
    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)

    unlisted: set[str] = set()
    changed = 0
    for agency in data["agencies"]:
        for src in agency.get("sources") or []:
            verified, reason = classify(src.get("url", ""))
            if reason == "unverified-unlisted":
                host = urllib.parse.urlparse(src.get("url", "")).netloc.lower().replace("www.", "")
                unlisted.add(host)
            if src.get("verified") is not verified:
                changed += 1
            if not check_only:
                # Rebuild for a stable key order, but preserve every field:
                # the old rebuild silently dropped source_key (added by
                # Layer 1 after this script was written). Unknown fields are
                # appended in their original order, never dropped.
                ordered = ["title", "url", "date", "verified", "source_key"]
                rebuilt = {k: src[k] for k in ordered if k in src}
                for k, v in src.items():
                    if k not in rebuilt:
                        rebuilt[k] = v
                rebuilt["verified"] = verified
                src.clear()
                src.update(rebuilt)

    if unlisted:
        print("Unlisted domains (stamped false, review needed):")
        for h in sorted(unlisted):
            print(f"  {h}")

    if check_only:
        missing = sum(
            1 for a in data["agencies"] for s in (a.get("sources") or [])
            if "verified" not in s
        )
        print(f"sources missing verified flag: {missing}")
        sys.exit(1 if missing else 0)

    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    # Publish the classification itself so the site can show it verbatim.
    from datetime import date
    classification = {
        "generated": date.today().isoformat(),
        "criteria": "docs/METHODOLOGY.md#evidence-tiers",
        "classifier": "scripts/flockoff.py classify",
        "verified_news": sorted(VERIFIED_NEWS()),
        "verified_primary": sorted(VERIFIED_PRIMARY()),
        "unverified_listed": sorted(UNVERIFIED()),
        "unverified_unlisted_seen": sorted(unlisted),
    }
    with open(cfg["paths"]["classification"], "w", encoding="utf-8") as f:
        json.dump(classification, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"stamped {changed} source flags in {data_path}")
    print(f"wrote {cfg['paths']['classification']}")


if __name__ == "__main__":
    main()
