#!/usr/bin/env python3
"""Regenerate the derived `meta` block in data/agencies.json.

The meta block (record counts, jurisdiction coverage, status distribution,
terminal verification tiers, renewal-date coverage) used to be maintained by
hand and drifted stale: it still said "322 records" and "last_updated":
"2026-09-26" weeks after the dataset moved on. Every derived field here is
recomputed from the data, so the metadata can never disagree with the
dataset again. Idempotent; stdlib only.

Run explicitly before committing dataset changes:
    python3 scripts/generate_meta.py

scripts/tests/test_meta.py fails if the committed meta is stale.

Fields `project`, `focus`, `states_planned`, and `methodology` are kept
from the existing block: they describe plans and pointers, not the data,
so they stay hand-maintained. Everything else is derived.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import evidence  # noqa: E402


def compute_meta(agencies: list, ev_by_id: dict) -> dict:
    """Build the derived meta block from the dataset."""
    states = sorted({a.get("state") for a in agencies if a.get("state")})
    status_counts = dict(sorted(Counter(a.get("status") for a in agencies).items()))
    tiers = Counter(ev_by_id[a["id"]]["tier"] for a in agencies)
    last_verified = sorted(a.get("last_verified") or "" for a in agencies)
    renewal = sum(1 for a in agencies if a.get("renewal_date"))
    contract_end = sum(1 for a in agencies if a.get("contract_end"))
    n = len(agencies)
    verified = tiers.get("verified", 0)
    pending = tiers.get("pending", 0)
    note = (
        f"{n} sourced records across {len(states)} jurisdictions. "
        "Coverage is USA-wide, expanding in 10-state waves. "
        "A missing agency means not yet researched, not confirmed absent. "
        f"{verified} terminal claims verified, {pending} pending validation*. "
        f"{renewal} records carry a renewal date and {contract_end} a contract "
        "end date; exact renewal dates remain thin and are the top research "
        "priority."
    )
    return {
        "last_updated": last_verified[-1] if last_verified else None,
        "record_count": n,
        "jurisdiction_count": len(states),
        "jurisdictions": states,
        "status_counts": status_counts,
        "terminal_verified": verified,
        "terminal_pending_validation": pending,
        "records_with_renewal_date": renewal,
        "records_with_contract_end": contract_end,
        "coverage_note": note,
    }


def main() -> None:
    data_path = ROOT / "data" / "agencies.json"
    try:
        data = json.loads(data_path.read_text(encoding="utf-8"))
        agencies = data["agencies"]
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        sys.exit(f"generate_meta failed: cannot read agencies.json: {exc}")
    try:
        primary, news, _ = evidence.load_classify_lists(
            ROOT / "config" / "flock-off.yaml")
    except OSError as exc:
        sys.exit(f"generate_meta failed: cannot read config/flock-off.yaml: {exc}")
    ev_by_id = {a["id"]: evidence.compute(a, primary, news) for a in agencies}

    derived = compute_meta(agencies, ev_by_id)
    meta = data.get("meta") or {}
    # Preserve hand-maintained plan/pointer fields; derive everything else.
    for key in ("project", "focus", "states_planned", "methodology"):
        if key in meta:
            derived[key] = meta[key]
    derived["generated_by"] = "scripts/generate_meta.py"
    # Keep a stable, readable key order: manual fields first, then derived.
    ordered = {}
    for key in ("project", "focus", "states_planned", "methodology",
                "generated_by"):
        if key in derived:
            ordered[key] = derived.pop(key)
    ordered.update(derived)
    data["meta"] = ordered
    data_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"meta regenerated: {derived['record_count']} records, "
          f"{derived['jurisdiction_count']} jurisdictions, "
          f"last_updated={derived['last_updated']}")


if __name__ == "__main__":
    main()
