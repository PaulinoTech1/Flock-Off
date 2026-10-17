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

import datetime
import json
import shutil
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import contracts as contracts_mod  # noqa: E402
import evidence as evidence_mod  # noqa: E402

# Display labels come from the canonical taxonomy in scripts/evidence.py;
# do not redefine the status set here.
STATUS_LABEL = evidence_mod.STATUS_LABELS


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


def _contract_facts(e: dict) -> str:
    """One-line fact summary for a contract card; omits unknown fields."""
    facts = []
    place = ", ".join(p for p in (e.get("city"), e.get("state")) if p)
    if place:
        facts.append(place)
    if e.get("status"):
        facts.append(STATUS_LABEL.get(e["status"], e["status"]))
    if e.get("contract_start") or e.get("contract_end"):
        facts.append(
            f"Term: {e.get('contract_start') or '?'} to "
            f"{e.get('contract_end') or 'open'}")
    if e.get("renewal_date"):
        facts.append(f"Renewal: {e['renewal_date']}")
    if e.get("annual_cost_usd") is not None:
        facts.append(f"Annual cost: {_usd(e['annual_cost_usd'])}")
    if e.get("cameras") is not None:
        facts.append(f"Cameras: {e['cameras']}")
    return " · ".join(facts)


def _prerender_contracts(entries: list) -> str:
    """Contract cards; markup mirrors js/contracts.js card()."""
    cards = []
    for e in entries:
        badge_cls = "ok" if e["kind"] == "signed_agreement" else "lead"
        badge = f'<span class="badge {badge_cls}">{_esc(e["kind_label"])}</span>'
        if e.get("accurate_as_of"):
            asof = f'Record accurate as of {_esc(e["accurate_as_of"])}'
        else:
            asof = "Record not yet re-verified"
        meta = " · ".join(
            p for p in (_publisher(e["doc_url"]),
                        e.get("doc_date") or "undated", asof) if p)
        cards.append(
            '<article class="source-card">{badge}'
            '<h3><a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a></h3>'
            '<p class="source-meta">{meta}</p>'
            '<p class="contract-facts">{facts}</p>'
            '<p class="cited-by">{note}</p></article>'.format(
                badge=badge,
                url=_esc(e["doc_url"]),
                title=_esc(e["doc_title"]),
                meta=_esc(meta),
                facts=_esc(_contract_facts(e)),
                note=_esc(e["doc_note"]),
            )
        )
    return "\n".join(cards)


def _render_rows(agencies: list, ev_by_id: dict) -> str:
    rows = []
    for a in agencies:
        renewal = a.get("renewal_date") or a.get("decision_date") or a.get("contract_end") or "—"
        ev = ev_by_id.get(a.get("id"), {})
        tier = ev.get("tier", "na")
        if tier == "verified":
            badge = ' <span class="badge badge-ok">verified</span>'
        elif tier == "pending":
            badge = ' <span class="badge badge-evpending">pending validation*</span>'
        else:
            badge = ""
        rows.append(
            "<tr><td><button class=\"row-open\" aria-label=\"Details for {agency}\"><strong>{agency}</strong></button><br><span class=\"muted\">{city}</span></td>"
            "<td>{state}</td><td>{status}{badge}</td><td>{cameras}</td><td>{cost}</td><td>{renewal}</td></tr>".format(
                agency=_esc(a.get("agency", "")),
                city=_esc(a.get("city") or ""),
                state=_esc(a.get("state", "")),
                status=_esc(STATUS_LABEL.get(a.get("status"), a.get("status") or "")),
                badge=badge,
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

    # Evidence tiers (docs/METHODOLOGY.md): computed once here so the
    # pre-render, the public evidence.json, and the test suite all share
    # one implementation (scripts/evidence.py).
    try:
        primary, news, _ = evidence_mod.load_classify_lists(
            ROOT / "config" / "flock-off.yaml")
    except OSError as exc:
        sys.exit(f"build failed: cannot read config/flock-off.yaml: {exc}")
    ev_by_id = {a["id"]: evidence_mod.compute(a, primary, news) for a in agencies}

    # Contracts page entries: the curated registry in
    # scripts/contracts.py joined against the dataset. Fail-closed: a
    # registry citation that no longer resolves aborts the build rather
    # than silently dropping a contract from the page.
    try:
        contract_entries = contracts_mod.build_contract_entries(agencies)
    except ValueError as exc:
        sys.exit(f"build failed: {exc}")

    index_path = ROOT / "index.html"
    html = index_path.read_text(encoding="utf-8")
    rows_marker = "<!--PRE_RENDER_ROWS-->"
    src_marker = "<!--PRE_RENDER_SOURCES-->"
    contracts_marker = "<!--PRE_RENDER_CONTRACTS-->"
    if rows_marker not in html:
        sys.exit("build failed: pre-render rows marker missing from index.html")
    if src_marker not in html:
        sys.exit("build failed: pre-render sources marker missing from index.html")
    if contracts_marker not in html:
        sys.exit("build failed: pre-render contracts marker missing from index.html")
    html = html.replace(rows_marker, _render_rows(agencies, ev_by_id))
    html = html.replace(src_marker, _prerender_sources(agencies))
    html = html.replace(contracts_marker, _prerender_contracts(contract_entries))
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

    # Stage the servable site into public/: everything except dev-only
    # paths. Vercel serves static files from outputDirectory (public/);
    # api/ functions are collected from the repo-root api/ dir, so the
    # transformed api/report.js above is what gets bundled.
    public = ROOT / "public"
    if public.exists():
        shutil.rmtree(public)
    ignore = shutil.ignore_patterns(
        ".git", ".github", "__pycache__", ".venv", "node_modules",
        "research", "scripts", "docs", "config", "api", "public",
        "vercel.json",
    )
    shutil.copytree(ROOT, public, ignore=ignore)

    # Public derived evidence file: per-agency tier + counts, so the client
    # and the pre-render share the build's computation instead of
    # reimplementing the rule in JS. data/agencies.json itself is untouched
    # (the release manifest hashes it byte-identical).
    #
    # last_verified rides along so the client can re-apply the stale
    # downgrade at display time: a "verified" tier baked at build time must
    # not survive past STALE_DAYS without a rebuild.
    by_id = {a["id"]: a for a in agencies}
    ev_public = {}
    for aid, ev in ev_by_id.items():
        rec = {k: ev[k] for k in ("tier", "terminal", "primary",
                                 "news_independent", "meets_bar",
                                 "acknowledged_pending", "stale",
                                 "stale_downgraded")}
        rec["last_verified"] = by_id.get(aid, {}).get("last_verified")
        ev_public[aid] = rec
    ev_doc = {
        "computed_at": datetime.date.today().isoformat(),
        "stale_days": evidence_mod.STALE_DAYS,
        "agencies": ev_public,
    }
    (public / "data" / "evidence.json").write_text(
        json.dumps(ev_doc, indent=2) + "\n", encoding="utf-8")

    # Public contracts file: the Contracts tab reads the same entries
    # the pre-render used, so the no-JS page and the JS render cannot
    # disagree about which documents are the actual contracts.
    contracts_doc = {
        "generated_at": datetime.date.today().isoformat(),
        "dataset_last_updated": json.loads(
            data_path.read_text(encoding="utf-8")).get("meta", {}).get(
                "last_updated"),
        "entries": contract_entries,
    }
    (public / "data" / "contracts.json").write_text(
        json.dumps(contracts_doc, indent=2) + "\n", encoding="utf-8")

    n_verified = sum(1 for ev in ev_by_id.values() if ev["tier"] == "verified")
    n_pending = sum(1 for ev in ev_by_id.values() if ev["tier"] == "pending")
    print(f"build ok: pre-rendered {len(agencies)} agencies, injected {len(ids)} agency ids, "
          f"contracts: {len(contract_entries)} documents, "
          f"evidence: {n_verified} verified / {n_pending} pending validation*")


if __name__ == "__main__":
    main()
