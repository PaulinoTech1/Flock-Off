#!/usr/bin/env python3
"""Evidence-tier computation for Flock-Off terminal claims.

Single source of truth for the rule documented in docs/METHODOLOGY.md
("Evidence tiers"):

  A terminal status (cancelled / rejected / expired) is shown as
  "verified" only when it cites BOTH
    - >= 1 verified-primary source (government / procurement document,
      court record, official agency or vendor statement, transparency
      portal), AND
    - >= 2 verified-news sources on independent domains.
  Anything else shows "pending validation*" until corroborated.

Stale records (last_verified older than STALE_DAYS) are auto-downgraded to
"pending validation*" at display time; the underlying citations are kept.

Used by scripts/vercel_build.py (pre-render + public derived field) and
scripts/tests/test_evidence.py.

Stdlib only.
"""
from __future__ import annotations

import datetime
import urllib.parse

TERMINAL_STATUSES = frozenset({"cancelled", "rejected", "expired"})
STALE_DAYS = 180


def host_of(url: str) -> str:
    try:
        host = urllib.parse.urlparse(url or "").netloc.lower()
    except Exception:
        return ""
    return host[4:] if host.startswith("www.") else host


def load_classify_lists(config_path) -> tuple[set[str], set[str], set[str]]:
    """Read verified_primary / verified_news domain sets from flock-off.yaml.

    Minimal line parser (no PyYAML) so build-time code stays stdlib-only.
    """
    primary: set[str] = set()
    news: set[str] = set()
    pending: set[str] = set()
    section = None
    with open(config_path, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s in ("verified_news:", "verified_primary:", "unverified:",
                     "pending_classify:"):
                section = s[:-1]
                continue
            if line.startswith("    - ") and section in (
                    "verified_news", "verified_primary", "pending_classify"):
                dom = line.split("#", 1)[0].split("-", 1)[1].strip()
                if section == "verified_primary":
                    primary.add(dom)
                elif section == "verified_news":
                    news.add(dom)
                else:
                    pending.add(dom)
    return primary, news, pending


def is_stale(last_verified: str | None, today: datetime.date | None = None) -> bool:
    if not last_verified:
        return True
    try:
        d = datetime.date.fromisoformat(str(last_verified)[:10])
    except ValueError:
        return True
    today = today or datetime.date.today()
    return (today - d).days > STALE_DAYS


def compute(record: dict, verified_primary: set[str], verified_news: set[str],
            today: datetime.date | None = None) -> dict:
    """Return the evidence assessment for one agency record.

    Keys: terminal (bool), primary (int distinct primary hosts),
    news_independent (int distinct news hosts), meets_bar (bool),
    acknowledged_pending (bool), stale (bool), tier ("verified" |
    "pending" | "na").
    """
    primary_hosts: set[str] = set()
    news_hosts: set[str] = set()
    for src in record.get("sources") or []:
        if not src.get("verified"):
            continue
        host = host_of(src.get("url", ""))
        if not host:
            continue
        if host in verified_primary:
            primary_hosts.add(host)
        elif host in verified_news:
            news_hosts.add(host)
    terminal = record.get("status") in TERMINAL_STATUSES
    meets_bar = len(primary_hosts) >= 1 and len(news_hosts) >= 2
    acknowledged_pending = record.get("validation") == "pending"
    stale = is_stale(record.get("last_verified"), today)
    if not terminal:
        tier = "na"
    elif acknowledged_pending or not meets_bar:
        tier = "pending"
    elif stale:
        tier = "pending"  # auto-downgrade at display time; citations kept
    else:
        tier = "verified"
    return {
        "terminal": terminal,
        "primary": len(primary_hosts),
        "news_independent": len(news_hosts),
        "meets_bar": meets_bar,
        "acknowledged_pending": acknowledged_pending,
        "stale": stale,
        "stale_downgraded": terminal and meets_bar and not acknowledged_pending and stale,
        "tier": tier,
    }
