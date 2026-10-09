#!/usr/bin/env python3
"""Research coverage dashboard for Flock-Off date fields.

Tracks the completeness of contract/renewal dates across the dataset,
so research throughput can be measured round over round.

Usage:
    python3 scripts/coverage_report.py
    python3 scripts/coverage_report.py --json > /tmp/coverage.json
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "agencies.json"

DATE_FIELDS = ("contract_start", "contract_end", "renewal_date", "decision_date")


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))["agencies"]
    active = [a for a in data if a.get("status") == "active"]

    def score(a):
        return sum(1 for k in DATE_FIELDS if a.get(k))

    report = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_records": len(data),
        "active_records": len(active),
        "active_by_date_count": {str(k): v for k, v in sorted(Counter(score(a) for a in active).items())},
        "active_zero_dates": sum(1 for a in active if score(a) == 0),
        "field_coverage_active": {
            k: sum(1 for a in active if a.get(k)) for k in DATE_FIELDS
        },
        "field_coverage_all": {
            k: sum(1 for a in data if a.get(k)) for k in DATE_FIELDS
        },
    }
    # Renewal pressure: active contracts with a renewal_date within 180 days
    today = datetime.now(timezone.utc).date().isoformat()
    upcoming = 0
    for a in active:
        rd = a.get("renewal_date")
        if rd and len(rd) >= 10:
            try:
                delta = (datetime.fromisoformat(rd[:10]).date() -
                         datetime.now(timezone.utc).date()).days
                if 0 <= delta <= 180:
                    upcoming += 1
            except ValueError:
                pass
    report["renewals_within_180d"] = upcoming

    if "--json" in sys.argv:
        print(json.dumps(report, indent=2))
    else:
        print(f"Coverage report {report['generated_at']}")
        print(f"  Active records: {report['active_records']}")
        print(f"  Active with zero dates: {report['active_zero_dates']} "
              f"({100*report['active_zero_dates']/max(1,report['active_records']):.0f}%)")
        print("  Field coverage (active):")
        for k, v in report["field_coverage_active"].items():
            pct = 100 * v / max(1, report["active_records"])
            print(f"    {k}: {v} ({pct:.1f}%)")
        print(f"  Renewals within 180d: {report['renewals_within_180d']}")


if __name__ == "__main__":
    main()
