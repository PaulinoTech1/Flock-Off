#!/usr/bin/env python3
"""One-time trust migrations for the Flock-Off dataset.

Actions (run explicitly; each prints what it changed):

  stamp-validation   Set validation:"pending" on terminal-status records
                     that do not meet the evidence bar (docs/METHODOLOGY.md).
  backfill-hashes    Copy content_hash from data/source_fingerprints.json
                     onto each citation (matched by normalized URL), binding
                     the record to the content seen at acceptance time.

Both are idempotent. Stdlib only. Run from the repo root.
"""
from __future__ import annotations

import copy
import json
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import evidence  # noqa: E402


def _norm_url(u: str) -> str:
    try:
        p = urllib.parse.urlparse((u or "").strip())
    except Exception:
        return ""
    host = p.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = p.path.rstrip("/") or "/"
    return f"{p.scheme.lower()}://{host}{path}" + (f"?{p.query}" if p.query else "")


def _load():
    data_path = ROOT / "data" / "agencies.json"
    data = json.loads(data_path.read_text(encoding="utf-8"))
    primary, news, _ = evidence.load_classify_lists(ROOT / "config" / "flock-off.yaml")
    return data_path, data, primary, news


def stamp_validation() -> int:
    data_path, data, primary, news = _load()
    changed = 0
    for a in data["agencies"]:
        ev = evidence.compute(a, primary, news)
        if ev["terminal"] and not ev["meets_bar"] and a.get("validation") != "pending":
            a["validation"] = "pending"
            changed += 1
    if changed:
        data_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"stamp-validation: {changed} terminal record(s) stamped pending")
    return changed


def backfill_hashes() -> int:
    data_path, data, _, _ = _load()
    fps = json.loads((ROOT / "data" / "source_fingerprints.json").read_text(encoding="utf-8"))
    by_url = {_norm_url(k): v for k, v in fps.items()}
    changed = 0
    missing = 0
    for a in data["agencies"]:
        for s in a.get("sources") or []:
            if s.get("content_hash"):
                continue
            fp = by_url.get(_norm_url(s.get("url", "")))
            h = (fp or {}).get("content_hash")
            if h:
                s["content_hash"] = h
                changed += 1
            else:
                missing += 1
    if changed:
        data_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"backfill-hashes: {changed} citation(s) bound, {missing} without a fingerprint (unfetched or blocked)")
    return changed


def main(argv: list[str]) -> None:
    if len(argv) != 2 or argv[1] not in ("stamp-validation", "backfill-hashes"):
        sys.exit("usage: migrate_trust.py [stamp-validation|backfill-hashes]")
    if argv[1] == "stamp-validation":
        stamp_validation()
    else:
        backfill_hashes()


if __name__ == "__main__":
    main(sys.argv)
