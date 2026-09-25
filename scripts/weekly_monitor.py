#!/usr/bin/env python3
"""Deterministic weekly checks for the Flock-Off contract tracker.

Fetches data/agencies.json from GitHub main (so a stale local clone cannot
skew results) and prints a markdown digest of items needing human review.
The news sweep and portal spot-checks are done by the monitor worker; this
script covers everything computable from the dataset itself.

Usage: python3 weekly_monitor.py
"""
from __future__ import annotations

import datetime
import json
import sys
import urllib.request

DATASET_URL = "https://raw.githubusercontent.com/PaulinoTech1/Flock-Off/main/data/agencies.json"
STALE_DAYS = 180
RENEWAL_WINDOW_DAYS = 90


def days_until(date_str: str | None, today: datetime.date) -> int | None:
    if not date_str:
        return None
    try:
        d = datetime.date.fromisoformat(date_str)
    except ValueError:
        return None
    return (d - today).days


def days_since(date_str: str | None, today: datetime.date) -> int | None:
    if not date_str:
        return None
    try:
        d = datetime.date.fromisoformat(date_str)
    except ValueError:
        return None
    return (today - d).days


def load_dataset() -> dict:
    """Fetch from GitHub main; fall back to a local path given as argv[1]."""
    try:
        with urllib.request.urlopen(DATASET_URL, timeout=120) as resp:
            data = json.load(resp)
        return data, "github-main"
    except Exception as exc:  # noqa: BLE001 - reported, then fallback
        if len(sys.argv) > 1:
            try:
                with open(sys.argv[1], encoding="utf-8") as f:
                    return json.load(f), f"local-fallback:{sys.argv[1]} (fetch failed: {exc})"
            except OSError:
                pass
        print(f"## Monitor health\n\nFAILED to fetch dataset: {exc}\n")
        sys.exit(1)


def main() -> None:
    today = datetime.date.today()
    data, provenance = load_dataset()

    agencies = data.get("agencies", [])
    lines: list[str] = []
    if provenance != "github-main":
        lines.append("## Monitor health")
        lines.append(f"- Dataset source: {provenance}")
        lines.append("")

    # Pressure windows: active contracts renewing soon.
    renewals = [
        a for a in agencies
        if a.get("status") == "active"
        and (du := days_until(a.get("renewal_date"), today)) is not None
        and 0 <= du <= RENEWAL_WINDOW_DAYS
    ]
    renewals.sort(key=lambda a: a["renewal_date"] or "")
    lines.append("## Pressure windows (active, renewal within 90 days)")
    if renewals:
        for a in renewals:
            lines.append(
                f"- **{a['agency']}** ({a['state']}): renews {a['renewal_date']} "
                f"({days_until(a['renewal_date'], today)} days). "
                f"Proposed: verify renewal date against a primary source."
            )
    else:
        lines.append("- none")
    lines.append("")

    # Active contracts with no known renewal date: the research gap.
    no_renewal = [a for a in agencies if a.get("status") == "active" and not a.get("renewal_date")]
    lines.append("## Active contracts with no renewal date (research gap)")
    lines.append(f"- {len(no_renewal)} of {sum(1 for a in agencies if a.get('status') == 'active')} active records.")
    for a in sorted(no_renewal, key=lambda x: x["agency"])[:15]:
        lines.append(f"  - {a['agency']} ({a['state']})")
    if len(no_renewal) > 15:
        lines.append(f"  - ...and {len(no_renewal) - 15} more")
    lines.append("")

    # Stale records: past the re-verification window, oldest first.
    stale = [
        (days_since(a.get("last_verified"), today), a)
        for a in agencies
        if (ds := days_since(a.get("last_verified"), today)) is not None and ds > STALE_DAYS
    ]
    stale.sort(key=lambda t: t[0] or 0, reverse=True)
    lines.append(f"## Stale records (unverified > {STALE_DAYS} days, oldest first)")
    if stale:
        for ds, a in stale[:10]:
            src = (a.get("sources") or [{}])[0].get("url", "no source")
            lines.append(
                f"- **{a['agency']}** ({a['state']}, {a['status']}): last verified "
                f"{a.get('last_verified')} ({ds} days ago). Re-check: {src}"
            )
    else:
        lines.append("- none")
    lines.append("")

    # Low-confidence leads awaiting corroboration.
    low = [a for a in agencies if a.get("confidence") == "low"]
    lines.append("## Low-confidence leads (single-source, verify before citing)")
    if low:
        for a in sorted(low, key=lambda x: x["agency"])[:15]:
            src = (a.get("sources") or [{}])[0].get("url", "no source")
            lines.append(f"- **{a['agency']}** ({a['state']}, {a['status']}): {src}")
        if len(low) > 15:
            lines.append(f"- ...and {len(low) - 15} more")
    else:
        lines.append("- none")
    lines.append("")

    # Stats.
    from collections import Counter
    status = Counter(a.get("status") for a in agencies)
    conf = Counter(a.get("confidence") for a in agencies)
    lines.append("## Dataset stats")
    lines.append(
        f"- {len(agencies)} records across {len(set(a.get('state') for a in agencies))} states. "
        f"Status: {dict(status)}. Confidence: {dict(conf)}."
    )

    print("\n".join(lines))


if __name__ == "__main__":
    main()
