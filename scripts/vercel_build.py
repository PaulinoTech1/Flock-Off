#!/usr/bin/env python3
"""Vercel build step for Flock-Off.

Runs at build time (see vercel.json buildCommand) and performs the same
deploy-time transforms the old direct-upload helper used to do:

- index.html: pre-render tracker table rows and source cards from
  data/agencies.json so crawlers and no-JS readers see the data
  (the JS render() replaces them on load).
  Markers: <!--PRE_RENDER_ROWS--> and <!--PRE_RENDER_SOURCES-->.
- api/report.js: inject the valid agency_id list for write-path validation.
  Marker: /*__AGENCY_IDS__*/[]

Stdlib only. Fail-closed: any missing marker or data problem exits nonzero
so Vercel fails the build instead of publishing a degraded site.
"""
from __future__ import annotations

import json
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STATUS_LABEL = {
    "active": "Active",
    "pending": "Under debate",
    "cancelled": "Cancelled",
    "rejected": "Proposal rejected",
    "expired": "Expired",
}


def _esc(s: str) -> str:
    return (
        s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _usd(n) -> str:
    return "—" if n is None else f"${n:,.0f}"


def _publisher(url: str) -> str:
    host = urllib.parse.urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def _prerender_sources(agencies: list) -> str:
    by_url = {}
    for a in agencies:
        for s in a.get("sources") or []:
            url = s.get("url")
            if not url:
                continue
            e = by_url.get(url)
            if e is None:
                e = {
                    "url": url,
                    "title": s.get("title") or url,
                    "date": s.get("date"),
                    "verified": bool(s.get("verified")),
                    "publisher": _publisher(url),
                    "agencies": [],
                }
                by_url[url] = e
            if not e["title"] or e["title"] == url:
                e["title"] = s.get("title") or e["title"]
            if s.get("verified"):
                e["verified"] = True
            e["agencies"].append(f"{a.get('agency', '')} ({a.get('state', '')})")
    entries = sorted(
        by_url.values(),
        key=lambda e: (not e["verified"], e["publisher"], e["title"]),
    )
    cards = []
    for e in entries:
        badge = (
            '<span class="badge ok">Verified citation</span>'
            if e["verified"]
            else '<span class="badge lead">Lead</span>'
        )
        meta = " · ".join(p for p in (e["publisher"], e["date"] or "undated") if p)
        cards.append(
            '<article class="source-card">{badge}'
            '<h3><a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a></h3>'
            '<p class="source-meta">{meta}</p>'
            '<p class="cited-by">Cited by: {cited}</p></article>'.format(
                badge=badge,
                url=_esc(e["url"]),
                title=_esc(e["title"]),
                meta=_esc(meta),
                cited=_esc(", ".join(e["agencies"])),
            )
        )
    return "\n".join(cards)


def _render_rows(agencies: list) -> str:
    rows = []
    for a in agencies:
        renewal = a.get("renewal_date") or a.get("decision_date") or a.get("contract_end") or "—"
        rows.append(
            "<tr><td><strong>{agency}</strong><br><span class=\"muted\">{city}</span></td>"
            "<td>{state}</td><td>{status}</td><td>{cameras}</td><td>{cost}</td><td>{renewal}</td></tr>".format(
                agency=_esc(a.get("agency", "")),
                city=_esc(a.get("city") or ""),
                state=_esc(a.get("state", "")),
                status=_esc(STATUS_LABEL.get(a.get("status"), a.get("status") or "")),
                cameras="—" if a.get("cameras") is None else _esc(str(a["cameras"])),
                cost=_usd(a.get("annual_cost_usd")),
                renewal=_esc(renewal),
            )
        )
    return "\n".join(rows)


def main() -> None:
    data_path = ROOT / "data" / "agencies.json"
    try:
        agencies = json.loads(data_path.read_text(encoding="utf-8"))["agencies"]
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        sys.exit(f"build failed: cannot read agencies.json: {exc}")
    if not agencies:
        sys.exit("build failed: agencies.json contains no agencies")

    index_path = ROOT / "index.html"
    html = index_path.read_text(encoding="utf-8")
    rows_marker = "<!--PRE_RENDER_ROWS-->"
    src_marker = "<!--PRE_RENDER_SOURCES-->"
    if rows_marker not in html:
        sys.exit("build failed: pre-render rows marker missing from index.html")
    if src_marker not in html:
        sys.exit("build failed: pre-render sources marker missing from index.html")
    html = html.replace(rows_marker, _render_rows(agencies))
    html = html.replace(src_marker, _prerender_sources(agencies))
    index_path.write_text(html, encoding="utf-8")

    report_path = ROOT / "api" / "report.js"
    src = report_path.read_text(encoding="utf-8")
    ids_marker = "/*__AGENCY_IDS__*/[]"
    if ids_marker not in src:
        sys.exit("build failed: agency-id marker missing from api/report.js")
    ids = sorted(a["id"] for a in agencies)
    if any(not i for i in ids):
        sys.exit("build failed: agency record missing id")
    report_path.write_text(src.replace(ids_marker, json.dumps(ids)), encoding="utf-8")

    print(f"build ok: pre-rendered {len(agencies)} agencies, injected {len(ids)} agency ids")


if __name__ == "__main__":
    main()
