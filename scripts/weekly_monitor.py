#!/usr/bin/env python3
"""Deterministic weekly checks for the Flock-Off contract tracker.

Fetches data/agencies.json from GitHub main (so a stale local clone cannot
skew results) and prints a markdown digest of items needing human review.
The news sweep and portal spot-checks are done by the monitor worker; this
script covers everything computable from the dataset itself.

Usage: python3 scripts/flockoff.py monitor [local-dataset-fallback]
"""
from __future__ import annotations

import csv
import datetime
import io
import json
import os
import re
import sys
import time
import urllib.request
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flockoff_config import ConfigError, load_config  # noqa: E402
from flockoff_errors import fmt  # noqa: E402
from source_keys import check as check_source_keys  # noqa: E402
from source_keys import canonical_url  # noqa: E402
import source_fingerprints as sfp  # noqa: E402

_cfg_cache: dict | None = None


def _cfg() -> dict:
    """Load (once) the validated pipeline config."""
    global _cfg_cache
    if _cfg_cache is None:
        _cfg_cache = load_config()
    return _cfg_cache

# --- Upstream discovery feeds: 100% free, no key, no account, no recurring
# cost. Anything paywalled (e.g. GovSpend) is out by policy; see
# docs/DATA_SOURCES.md. These feeds find candidates; the underlying linked
# primary/news source is what gets cited, never the feed page itself.
COVERED_STATES = {
    "CT", "DC", "DE", "FL", "GA", "MA", "ME", "NC",
    "NH", "NJ", "NY", "PA", "RI", "SC", "VA", "VT",
    # Wave 1 (westward expansion, in progress):
    "OH", "MI", "IN", "IL", "WI",
    "WV", "KY", "TN", "AL", "MS",
}
FF_ACTION_TO_STATUS = {
    "canceled": "cancelled",
    "non-renewal": "cancelled",
    "paused": "pending",
    "rejected": "rejected",
    "deactivated": "cancelled",
}
_NAME_STOPWORDS = {
    "police", "department", "dept", "sheriff", "sheriffs", "office", "county",
    "city", "of", "the", "bureau", "metro", "metropolitan", "town",
    "township", "village", "borough", "public", "safety",
}


def norm_name(s: str | None) -> str:
    words = re.sub(r"[^a-z0-9 ]", " ", (s or "").lower()).split()
    return " ".join(w for w in words if w not in _NAME_STOPWORDS)


def fetch_text(url: str, timeout: int, max_bytes: int) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "FlockOff-monitor/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(max_bytes + 1)[:max_bytes].decode("utf-8", "replace")


class _TrackerTableParser(HTMLParser):
    """Extract (place, state, date, action, source_url) rows from the first
    table whose header mentions Place and Action."""

    def __init__(self) -> None:
        super().__init__()
        self._in_table = False
        self._in_th = False
        self._in_td = False
        self._headers: list[str] = []
        self._row: list[str] = []
        self._row_link: str | None = None
        self._cell_link: str | None = None
        self._buf: list[str] = []
        self._is_tracker_table = False
        self.rows: list[tuple[str, str, str, str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self._in_table = True
            self._headers = []
            self._is_tracker_table = False
        elif self._in_table and tag == "th":
            self._in_th = True
            self._buf = []
        elif self._in_table and tag == "td":
            self._in_td = True
            self._buf = []
            self._cell_link = None
        elif self._in_table and tag == "a":
            for k, v in attrs:
                if k == "href" and v:
                    self._cell_link = v
                    break

    def handle_endtag(self, tag: str) -> None:
        if tag == "table":
            self._in_table = False
        elif tag == "th" and self._in_th:
            self._in_th = False
            self._headers.append("".join(self._buf).strip().lower())
            if "place" in self._headers and "action" in self._headers:
                self._is_tracker_table = True
        elif tag == "td" and self._in_td:
            self._in_td = False
            self._row.append("".join(self._buf).strip())
            if len(self._row) == 6:
                self._row_link = self._cell_link  # source cell is last
            if len(self._row) > 6:
                self._row = self._row[:6]
        elif tag == "tr" and self._in_table:
            if self._is_tracker_table and len(self._row) >= 4:
                place, state, date, action = self._row[0], self._row[1], self._row[2], self._row[3]
                if place and state:
                    self.rows.append((place, state, date, action, self._row_link))
            self._row = []
            self._row_link = None

    def handle_data(self, data: str) -> None:
        if self._in_th or self._in_td:
            self._buf.append(data)


def check_finding_flock_tracker(agencies: list[dict]) -> tuple[list[str], list[str]]:
    """Compare the Finding Flock cancellation tracker against the dataset.

    Returns (candidate_lines, mismatch_lines); raises on fetch/parse failure.
    """
    html = fetch_text(_cfg()["urls"]["finding_flock_tracker"], timeout=60, max_bytes=2_000_000)
    parser = _TrackerTableParser()
    parser.feed(html)
    if not parser.rows:
        raise RuntimeError("tracker table not found (page structure changed?)")

    index: dict[tuple[str, str], list[dict]] = {}
    for a in agencies:
        index.setdefault((norm_name(a.get("agency")), a.get("state")), []).append(a)

    candidates, mismatches = [], []
    for place, state, date, action, source_url in parser.rows:
        state = state.strip().upper()
        if state not in COVERED_STATES:
            continue
        key = (norm_name(place), state)
        matched = []
        for (nname, nstate), records in index.items():
            if nstate != state:
                continue
            if key[0] and nname and (key[0] in nname or nname in key[0]):
                matched.extend(records)
        if not matched:
            candidates.append(
                f"- **{place}** ({state}): {action} on {date}. "
                f"Research: confirm Flock vendor, find primary record. "
                f"Tracker source: {source_url or _cfg()['urls']['finding_flock_tracker']}"
            )
            continue
        expected = FF_ACTION_TO_STATUS.get(action.strip().lower())
        for m in matched:
            if expected and m.get("status") != expected:
                mismatches.append(
                    f"- **{m['agency']}** ({state}): dataset says "
                    f"{m.get('status')}, Finding Flock reports {action} on {date}. "
                    f"Source: {source_url or _cfg()['urls']['finding_flock_tracker']}"
                )
    return candidates, mismatches


def check_atlas_csv(agencies: list[dict]) -> list[str]:
    """Find covered-state Atlas of Surveillance agencies missing from the dataset.

    Returns candidate lines; raises on fetch/parse failure.
    """
    text = fetch_text(_cfg()["urls"]["atlas_csv"], timeout=120, max_bytes=15_000_000)
    reader = csv.DictReader(io.StringIO(text))
    known = {(norm_name(a.get("agency")), a.get("state")) for a in agencies}
    seen: set[tuple[str, str]] = set()
    candidates = []
    for row in reader:
        state = (row.get("State") or "").strip().upper()
        if state not in COVERED_STATES:
            continue
        agency = (row.get("Agency") or "").strip()
        key = (norm_name(agency), state)
        if not key[0] or key in known or key in seen:
            continue
        # Atlas vendor filter is imperfect; flag for human vendor confirmation.
        seen.add(key)
        link = (row.get("Link 1") or "").strip()
        candidates.append(
            f"- **{agency}** ({row.get('City', '').strip()}, {state}): "
            f"{(row.get('Summary') or '').strip()[:120]} "
            f"Confirm Flock vendor. Lead: {link or 'atlasofsurveillance.org'}"
        )
    return candidates


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
        with urllib.request.urlopen(_cfg()["urls"]["dataset"], timeout=120) as resp:
            data = json.load(resp)
        return data, "github-main"
    except Exception as exc:  # noqa: BLE001 - reported, then fallback
        if len(sys.argv) > 1:
            try:
                with open(sys.argv[1], encoding="utf-8") as f:
                    return json.load(f), f"local-fallback:{sys.argv[1]} (fetch failed: {exc})"
            except OSError:
                pass
        print(f"## Monitor health\n\n{fmt('E_DS_FETCH', str(exc))}\n")
        sys.exit(1)


def main() -> None:
    try:
        _cfg()
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
    today = datetime.date.today()
    data, provenance = load_dataset()

    agencies = data.get("agencies", [])
    lines: list[str] = []
    if provenance != "github-main":
        lines.append("## Monitor health")
        lines.append(f"- Dataset source: {provenance}")
        lines.append("")

    # (upstream health notes are collected below and appended here at the end)

    # Pressure windows: active contracts renewing soon.
    renewals = [
        a for a in agencies
        if a.get("status") == "active"
        and (du := days_until(a.get("renewal_date"), today)) is not None
        and 0 <= du <= _cfg()["monitor"]["renewal_window_days"]
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
        if (ds := days_since(a.get("last_verified"), today)) is not None and ds > _cfg()["monitor"]["stale_days"]
    ]
    stale.sort(key=lambda t: t[0] or 0, reverse=True)
    lines.append(f"## Stale records (unverified > {_cfg()['monitor']['stale_days']} days, oldest first)")
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

    # Upstream discovery feeds (free, keyless). Failures are reported, never fatal.
    health_notes: list[str] = []
    try:
        ff_candidates, ff_mismatches = check_finding_flock_tracker(agencies)
    except Exception as exc:  # noqa: BLE001 - reported under Monitor health
        ff_candidates, ff_mismatches = [], []
        health_notes.append(fmt("W_UPSTREAM_FF", str(exc)))
    try:
        atlas_candidates = check_atlas_csv(agencies)
    except Exception as exc:  # noqa: BLE001 - reported under Monitor health
        atlas_candidates = []
        health_notes.append(fmt("W_UPSTREAM_ATLAS", str(exc)))

    lines.append("## Upstream candidates: Finding Flock cancellation tracker")
    if ff_candidates:
        lines.extend(ff_candidates[:15])
        if len(ff_candidates) > 15:
            lines.append(f"- ...and {len(ff_candidates) - 15} more")
    else:
        lines.append("- none new in scope")
    lines.append("")
    if ff_mismatches:
        lines.append("## Status mismatches vs Finding Flock tracker")
        lines.extend(ff_mismatches[:15])
        if len(ff_mismatches) > 15:
            lines.append(f"- ...and {len(ff_mismatches) - 15} more")
        lines.append("")
    lines.append("## Upstream candidates: Atlas of Surveillance (active deployments)")
    if atlas_candidates:
        lines.extend(atlas_candidates[:15])
        if len(atlas_candidates) > 15:
            lines.append(f"- ...and {len(atlas_candidates) - 15} more")
    else:
        lines.append("- none new in scope")
    lines.append("")

    # Stats.
    from collections import Counter
    import urllib.parse
    status = Counter(a.get("status") for a in agencies)
    conf = Counter(a.get("confidence") for a in agencies)
    terminal = [a for a in agencies if a.get("status") in ("cancelled", "rejected", "expired")]

    def independent_citations(a: dict) -> int:
        return len({
            urllib.parse.urlparse(s["url"]).netloc.replace("www.", "")
            for s in a.get("sources", []) if s.get("verified")
        })

    # Source key hygiene: missing/stale dedup keys, intra-agency duplicates.
    key_problems = check_source_keys(data)
    lines.append("## Source key hygiene (dedup)")
    if key_problems:
        lines.append(f"- {len(key_problems)} problem(s):")
        for p in key_problems[:15]:
            lines.append(f"  - {p}")
        if len(key_problems) > 15:
            lines.append(f"  - ...and {len(key_problems) - 15} more")
    else:
        lines.append("- none: all citations carry valid keys, no intra-agency duplicates")
    lines.append("")

    # Layers 2+3: content fingerprints (read-only; baseline advances via
    # python3 scripts/flockoff.py fingerprints refresh + push).
    fps = None
    try:
        with urllib.request.urlopen(_cfg()["urls"]["fingerprints"], timeout=120) as resp:
            fps = json.load(resp)
    except Exception as exc:  # noqa: BLE001 - reported below
        fps = None
        health_notes.append(fmt("E_FP_FETCH", str(exc)))
    else:
        def _fp_for(src):
            try:
                key = src.get("source_key") or canonical_url(src["url"])
            except ValueError:
                return None, None
            return key, fps.get(key)

        # Layer 2: pairwise near-duplicate detection across URLs.
        cands = []
        for agency in agencies:
            for src in agency.get("sources", []):
                key, fp = _fp_for(src)
                if not fp or fp.get("fetch_status") != "ok" or not fp.get("simhash"):
                    continue
                if fp.get("text_len", 0) < sfp.pair_min_len():
                    continue
                cands.append((agency["id"], src.get("title", ""), src["url"],
                              key, int(fp["simhash"], 16)))
        pairs = []
        for i in range(len(cands)):
            for j in range(i + 1, len(cands)):
                if cands[i][3] == cands[j][3]:
                    continue  # same canonical URL: legitimate reuse, not a dup
                if sfp.hamming(cands[i][4], cands[j][4]) <= sfp.near_dup_distance():
                    pairs.append((cands[i], cands[j]))
        lines.append("## Possible duplicate sources (cross-URL)")
        if pairs:
            for (a1, t1, u1, k1, _), (a2, t2, u2, k2, _) in pairs[:12]:
                scope = "SAME AGENCY" if a1 == a2 else "cross-agency"
                lines.append(f"- [{scope}] {a1} <-> {a2} (simhash near-duplicate)")
                lines.append(f"  - {t1[:70]}: {u1[:90]}")
                lines.append(f"  - {t2[:70]}: {u2[:90]}")
                if a1 == a2:
                    lines.append("  - Proposed: drop the redundant citation, keep one URL.")
            if len(pairs) > 12:
                lines.append(f"  - ...and {len(pairs) - 12} more pairs")
        else:
            lines.append("- none")
        lines.append("")

        # Layer 3: rotating probe; has the cited article materially changed?
        ok_entries = []
        for agency in agencies:
            for src in agency.get("sources", []):
                key, fp = _fp_for(src)
                if not fp or fp.get("fetch_status") != "ok" or not fp.get("simhash"):
                    continue
                ok_entries.append((agency["id"], src.get("title", ""),
                                   src["url"], key, fp))
        ok_entries.sort(key=lambda t: t[3])
        week = int(today.strftime("%V"))
        start = (week * _cfg()["monitor"]["update_probe_sample"]) % len(ok_entries) if ok_entries else 0
        sample = [ok_entries[(start + i) % len(ok_entries)]
                  for i in range(min(_cfg()["monitor"]["update_probe_sample"], len(ok_entries)))]
        changed, probe_blocked, probe_err = [], 0, 0
        for agency_id, title, url, key, fp in sample:
            time.sleep(_cfg()["monitor"]["update_probe_delay"])
            fetch_status, _, html = sfp.fetch_page(url)
            if fetch_status != "ok" or not html:
                if fetch_status == "blocked":
                    probe_blocked += 1
                else:
                    probe_err += 1
                continue
            _, text = sfp.extract_text(html)
            if len(text) < sfp.min_text_len():
                continue
            new_hash = sfp.content_hash(text)
            if new_hash == fp.get("content_hash"):
                continue
            new_sh = sfp.simhash64(text)
            dist = sfp.hamming(new_sh, int(fp["simhash"], 16)) if new_sh else 64
            old_len = fp.get("text_len", 0) or 1
            len_change = abs(len(text) - old_len) / old_len
            if dist >= sfp.update_distance() or len_change > 0.5:
                changed.append((agency_id, title, url, fp.get("fetched_at"), dist))
        lines.append("## Sources changed since citation")
        if changed:
            for agency_id, title, url, fetched_at, dist in changed:
                lines.append(
                    f"- **{agency_id}**: {title[:70]} materially changed since "
                    f"fingerprinted {fetched_at} (simhash distance {dist}). "
                    f"Proposed: re-verify the citation; refresh the fingerprint "
                    f"baseline after review. {url[:90]}"
                )
        else:
            lines.append(f"- none in this week's probe sample ({len(sample)} checked)")
        lines.append("")
        if probe_blocked:
            health_notes.append(fmt("W_PROBE_BLOCKED", f"{probe_blocked} of {len(sample)} sampled"))
        if probe_err:
            health_notes.append(fmt("W_PROBE_ERROR", f"{probe_err} of {len(sample)} sampled"))
        missing_fp = 0
        for agency in agencies:
            for src in agency.get("sources", []):
                _, fp = _fp_for(src)
                if fp is None:
                    missing_fp += 1
        if missing_fp:
            health_notes.append(fmt("W_FP_MISSING_KEYS", f"{missing_fp} citations"))

    bar_met = sum(1 for a in terminal if independent_citations(a) >= 3)
    lines.append("## Dataset stats")
    lines.append(
        f"- {len(agencies)} records across {len(set(a.get('state') for a in agencies))} states. "
        f"Status: {dict(status)}. Confidence: {dict(conf)}."
    )
    lines.append(
        f"- Evidence: {bar_met} verified claims (3+ independent verified citations), "
        f"{len(terminal) - bar_met} pending validation* (fewer than 3)."
    )
    if health_notes:
        lines.append("")
        lines.append("## Monitor health")
        for note in health_notes:
            lines.append(f"- {note}")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
