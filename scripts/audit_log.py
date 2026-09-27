#!/usr/bin/env python3
"""Public audit log for the Flock-Off dataset.

Every change to data/agencies.json gets a machine-readable entry in
data/audit/log.jsonl:

    {"ts": ..., "actor": ..., "parent_hash": "<sha256 of previous agencies.json>",
     "new_hash": "<sha256 of current agencies.json>", "commit": ...,
     "changes": [{"agency_id": ..., "fields_changed": [...],
                  "sources_added": [...], "sources_removed": [...],
                  "status_change": ["active", "cancelled"] | null}]}

Entries hash-chain: each entry's parent_hash must equal the previous
entry's new_hash, so silent history rewrites are detectable. External
parties can watch the log for anomalous patterns.

Scope: the log begins at the 2026-09-26 genesis entry, which baselines the
dataset as it stood after the trust migrations. Changes made before genesis
are not individually recorded; the chain is complete and tamper-evident only
from genesis forward. Do not present the log as the project's full history.

Usage:
    python3 scripts/audit_log.py append --base /tmp/agencies.before.json \\
        --actor "wave-4-apply" [--commit <sha>]

The genesis entry is created with --genesis. scripts/tests/test_audit.py
verifies the chain and that the tip matches the current dataset hash.

Stdlib only. Run from the repo root.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "agencies.json"
LOG_PATH = ROOT / "data" / "audit" / "log.jsonl"

FIELD_IGNORE = {"validation"}  # bookkeeping, reported separately if changed


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _src_key(s: dict) -> str:
    return s.get("source_key") or s.get("url") or json.dumps(s, sort_keys=True)


def diff_agencies(old: dict, new: dict) -> list[dict]:
    old_by = {a["id"]: a for a in old.get("agencies", [])}
    new_by = {a["id"]: a for a in new.get("agencies", [])}
    changes: list[dict] = []
    for aid in sorted(set(old_by) | set(new_by)):
        o, n = old_by.get(aid), new_by.get(aid)
        if o is None:
            changes.append({"agency_id": aid, "added": True, "fields_changed": [],
                            "sources_added": [], "sources_removed": [],
                            "status_change": [None, n.get("status")]})
            continue
        if n is None:
            changes.append({"agency_id": aid, "removed": True, "fields_changed": [],
                            "sources_added": [], "sources_removed": [],
                            "status_change": [o.get("status"), None]})
            continue
        fields = sorted(
            k for k in set(o) | set(n)
            if k not in ("sources",) and k not in FIELD_IGNORE
            and json.dumps(o.get(k), sort_keys=True) != json.dumps(n.get(k), sort_keys=True)
        )
        if "validation" in set(o) | set(n) and o.get("validation") != n.get("validation"):
            fields.append("validation")
            fields.sort()
        o_src = {_src_key(s): s for s in o.get("sources") or []}
        n_src = {_src_key(s): s for s in n.get("sources") or []}
        added = sorted((n_src[k].get("url") or k) for k in n_src.keys() - o_src.keys())
        removed = sorted((o_src[k].get("url") or k) for k in o_src.keys() - n_src.keys())
        status_change = None
        if o.get("status") != n.get("status"):
            status_change = [o.get("status"), n.get("status")]
        if fields or added or removed or status_change:
            changes.append({"agency_id": aid, "fields_changed": fields,
                            "sources_added": added, "sources_removed": removed,
                            "status_change": status_change})
    return changes


def read_log() -> list[dict]:
    if not LOG_PATH.is_file():
        return []
    entries = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            entries.append(json.loads(line))
    return entries


def append_entry(base_path: Path, actor: str, commit: str | None) -> dict:
    old = json.loads(base_path.read_text(encoding="utf-8"))
    new = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    entries = read_log()
    parent_hash = sha256_file(base_path)
    if entries and entries[-1]["new_hash"] != parent_hash:
        sys.exit(
            f"audit chain broken: base file hash {parent_hash[:12]} does not match "
            f"last entry's new_hash {entries[-1]['new_hash'][:12]}. "
            "Diff against the dataset state the last entry describes."
        )
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "actor": actor,
        "parent_hash": parent_hash,
        "new_hash": sha256_file(DATA_PATH),
        "commit": commit,
        "changes": diff_agencies(old, new),
    }
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry


def genesis(actor: str) -> dict:
    if read_log():
        sys.exit("audit log already has entries; refusing to rewrite genesis")
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "actor": actor,
        "parent_hash": None,
        "new_hash": sha256_file(DATA_PATH),
        "commit": None,
        "note": "genesis: baseline after trust migrations "
                "(validation stamps, content-hash backfill)",
        "changes": [],
    }
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Append to the dataset audit log.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("genesis", help="write the first audit entry")
    g.add_argument("--actor", required=True)
    a = sub.add_parser("append", help="diff --base against current data and append")
    a.add_argument("--base", required=True, help="agencies.json before the change")
    a.add_argument("--actor", required=True)
    a.add_argument("--commit", default=None)
    args = ap.parse_args(argv)
    if args.cmd == "genesis":
        e = genesis(args.actor)
    else:
        e = append_entry(Path(args.base), args.actor, args.commit)
    print(f"audit entry: {e['parent_hash'] and e['parent_hash'][:12]} -> {e['new_hash'][:12]} "
          f"({len(e['changes'])} agency change(s))")


if __name__ == "__main__":
    main()
