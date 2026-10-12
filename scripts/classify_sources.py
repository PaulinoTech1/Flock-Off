#!/usr/bin/env python3
"""Stamp every source in data/agencies.json with a verified true/false flag.

Classification is an explicit domain map in config/flock-off.yaml
(section "classify"), reviewed in git. Fail-closed: any domain not listed
stamps false. New sources added to the dataset get flagged by the weekly
monitor until classified in the config.

Criteria live in docs/METHODOLOGY.md ("Evidence bar"). In short:
  verified   = primary/official record, or established news outlet with an
               editorial process (bylines, corrections, masthead).
  unverified = advocacy orgs, social/video platforms, aggregators,
               personal blogs, unknown outlets. Usable as leads,
               never as citations toward the evidence bar.
  excluded   = AI-generated summaries. Not citations, not leads, not even
               invalid sources: disregarded entirely (Boss policy
               2026-10-04). A citation on an excluded domain is a hard
               fail, same as a feed-domain citation.

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


def host_of(url: str) -> str:
    """Lowercased host with a single leading www. stripped.

    Uses removeprefix, not replace: replace("www.", "") mangles domains
    that merely contain the substring (e.g. awww.example.com).
    """
    host = urllib.parse.urlparse(url or "").netloc.lower()
    return host.removeprefix("www.")


def VERIFIED_NEWS() -> set[str]:
    return set(_domains()["verified_news"])


def VERIFIED_PRIMARY() -> set[str]:
    return set(_domains()["verified_primary"])


def UNVERIFIED() -> set[str]:
    return set(_domains()["unverified"])


def EXCLUDED() -> set[str]:
    return set(_domains().get("excluded") or [])


def PENDING_CLASSIFY() -> set[str]:
    return set(_domains().get("pending_classify") or [])


def DATA_PATH() -> str:
    return _cfg()["paths"]["data"]


def CLASSIFICATION_PATH() -> str:
    return _cfg()["paths"]["classification"]


def classify(url: str) -> tuple[bool, str]:
    host = host_of(url)
    if host in VERIFIED_NEWS():
        return True, "verified-news"
    if host in VERIFIED_PRIMARY():
        return True, "verified-primary"
    if host in PENDING_CLASSIFY():
        # Quarantine: proposed for a verified tier, not yet approved.
        # Classifies as unverified until domain_approvals.yaml records
        # the promotion with approver, date, and rationale.
        return False, "quarantine-pending"
    if host in EXCLUDED():
        # AI-generated summaries: excluded entirely, not even as leads.
        return False, "excluded"
    if host in UNVERIFIED():
        return False, "unverified-listed"
    return False, "unverified-unlisted"


def promote_domain(domain: str, tier: str, rationale: str,
                   approved_by: str = "Boss",
                   assume_yes: bool = False) -> None:
    """Promote a domain from pending_classify to a verified tier.

    Evidence-then-apply: prints every citation using the domain (count,
    date range, sample titles) BEFORE touching any file, so the reviewer
    sees what they are approving in the same terminal. Requires
    --rationale; aborts unless confirmed (--yes or interactive y).

    Edits are surgical text operations on config/flock-off.yaml and
    config/domain_approvals.yaml so hand-maintained comments survive.
    """
    import datetime as _dt

    domain = (domain or "").lower().strip().removeprefix("www.")
    if tier not in ("verified_news", "verified_primary"):
        sys.exit(f"promote: tier must be verified_news or verified_primary, "
                 f"got {tier!r}")
    if not rationale or not rationale.strip():
        sys.exit("promote: --rationale is required")
    cfg = _cfg()
    pending = set(cfg["classify"].get("pending_classify") or [])
    if domain not in pending:
        sys.exit(f"promote: {domain} is not in classify.pending_classify "
                 f"(quarantine first, then promote)")

    # ---- Evidence phase (read-only) ----
    data_path = cfg["paths"]["data"]
    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)
    hits: list[tuple[str, str, str, str]] = []  # agency, title, date, url
    for agency in data["agencies"]:
        for src in agency.get("sources") or []:
            if host_of(src.get("url", "")) == domain:
                hits.append((agency.get("id", "?"),
                             src.get("title", "(no title)"),
                             src.get("date", "?"),
                             src.get("url", "")))
    print(f"=== promote {domain} -> {tier} ===")
    print(f"citations using this domain: {len(hits)}")
    if hits:
        dates = sorted(h for _, _, h, _ in hits if h and h != "?")
        if dates:
            print(f"date range: {dates[0]} .. {dates[-1]}")
        print("sample titles:")
        for _ag, title, _d, _u in hits[:5]:
            print(f"  - {title[:80]}")
        if len(hits) > 5:
            print(f"  ...and {len(hits) - 5} more")
    else:
        print("(no citations in the dataset currently use this domain)")
    print(f"rationale: {rationale.strip()}")
    print(f"approver: {approved_by}, date: {_dt.date.today().isoformat()}")

    if not assume_yes:
        try:
            ans = input("apply promotion? [y/N] ").strip().lower()
        except EOFError:
            ans = ""
        if ans not in ("y", "yes"):
            print("promote: aborted, no files changed")
            return

    # ---- Apply phase: surgical text edits, comments preserved ----
    repo_root = cfg["_repo_root"]
    flockoff_yaml = os.path.join(repo_root, "config", "flock-off.yaml")
    approvals_yaml = os.path.join(repo_root, "config", "domain_approvals.yaml")

    with open(flockoff_yaml, encoding="utf-8") as f:
        lines = f.readlines()

    def _section_bounds(key: str) -> tuple[int, int]:
        """(start, end) line indices of a `classify:` subsection's body,
        end exclusive. The body is the run of 4+-space-indented lines
        (list items, comments, blank lines) after `  {key}:`; it ends at
        the next 2-space sibling key or end of file."""
        start = -1
        for i, ln in enumerate(lines):
            if ln == f"  {key}:\n":
                start = i + 1
                break
        if start == -1:
            sys.exit(f"promote: section {key!r} not found in "
                     f"config/flock-off.yaml")
        end = len(lines)
        for i in range(start, len(lines)):
            ln = lines[i]
            if ln.strip() == "":
                continue
            # A 2-space-indented non-continuation line is the next key.
            if ln.startswith("  ") and not ln.startswith("   "):
                end = i
                break
            if not ln.startswith(" "):
                end = i
                break
        return start, end

    # 1. Remove from pending_classify.
    ps, pe = _section_bounds("pending_classify")
    removed = False
    kept = []
    for ln in lines[ps:pe]:
        stripped = ln.strip()
        if stripped.startswith("- "):
            item = stripped[2:].split("#")[0].strip()
            if item == domain:
                removed = True
                continue
        kept.append(ln)
    if not removed:
        # pending_classify may be an inline `[]`; handle that too.
        for i in range(ps):
            if lines[i] == "  pending_classify:\n":
                break
        else:
            i = -1
        if i != -1 and ps < len(lines) and lines[ps].strip() == "[]":
            sys.exit(f"promote: {domain} listed in config but section is "
                     f"empty inline list; edit config/flock-off.yaml by hand")
        sys.exit(f"promote: {domain} not found as a list item under "
                 f"pending_classify")
    lines[ps:pe] = kept

    # 2. Insert into the target tier list, sorted.
    ts, te = _section_bounds(tier)
    items = []
    for ln in lines[ts:te]:
        stripped = ln.strip()
        if stripped.startswith("- "):
            items.append(stripped[2:].split("#")[0].strip())
    if domain in items:
        sys.exit(f"promote: {domain} is already in {tier}")
    insert_at = ts
    for i, ln in enumerate(lines[ts:te]):
        stripped = ln.strip()
        if stripped.startswith("- "):
            item = stripped[2:].split("#")[0].strip()
            if item > domain:
                insert_at = ts + i
                break
            insert_at = ts + i + 1
    lines.insert(insert_at, f"    - {domain}\n")

    with open(flockoff_yaml, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"updated config/flock-off.yaml: moved {domain} to {tier}")

    # 3. Append the approval entry.
    today = _dt.date.today().isoformat()
    safe_rationale = rationale.strip().replace('"', "'")
    entry = (f"  {domain}:\n"
             f"    tier: {tier}\n"
             f"    approved_by: {approved_by}\n"
             f"    date: {today}\n"
             f"    rationale: \"{safe_rationale}\"\n")
    with open(approvals_yaml, encoding="utf-8") as f:
        content = f.read()
    if not content.endswith("\n"):
        content += "\n"
    with open(approvals_yaml, "w", encoding="utf-8") as f:
        f.write(content + entry)
    print(f"updated config/domain_approvals.yaml: approval recorded")
    print(f"promote: {domain} -> {tier} complete")


def stamp_source(src: dict, verified: bool) -> None:
    """Set the verified flag, preserving every field in a stable key order.

    The old inline rebuild silently dropped source_key (added by Layer 1
    after this script was written). Unknown fields are appended in their
    original order, never dropped.
    """
    ordered = ["title", "url", "date", "verified", "source_key"]
    rebuilt = {k: src[k] for k in ordered if k in src}
    for k, v in src.items():
        if k not in rebuilt:
            rebuilt[k] = v
    rebuilt["verified"] = verified
    src.clear()
    src.update(rebuilt)


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
        raw_before = f.read()
    data = json.loads(raw_before)

    unlisted: set[str] = set()
    changed = 0
    for agency in data["agencies"]:
        for src in agency.get("sources") or []:
            verified, reason = classify(src.get("url", ""))
            if reason == "unverified-unlisted":
                unlisted.add(host_of(src.get("url", "")))
            if src.get("verified") is not verified:
                changed += 1
            if not check_only:
                stamp_source(src, verified)

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

    # Only touch the dataset when the bytes actually change. An unconditional
    # rewrite (e.g. key reordering by stamp_source) invalidates the integrity
    # manifest and audit tip even when no flag changed.
    new_raw = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if new_raw == raw_before:
        print(f"no changes; {data_path} untouched")
    else:
        with open(data_path, "w", encoding="utf-8") as f:
            f.write(new_raw)
        print(f"stamped {changed} source flags in {data_path}")

    # Publish the classification itself so the site can show it verbatim.
    from datetime import date
    classification = {
        "generated": date.today().isoformat(),
        "criteria": "docs/METHODOLOGY.md#evidence-tiers",
        "classifier": "scripts/flockoff.py classify",
        "verified_news": sorted(VERIFIED_NEWS()),
        "verified_primary": sorted(VERIFIED_PRIMARY()),
        "unverified_listed": sorted(UNVERIFIED()),
        "excluded": sorted(EXCLUDED()),
        "unverified_unlisted_seen": sorted(unlisted),
    }
    with open(cfg["paths"]["classification"], "w", encoding="utf-8") as f:
        json.dump(classification, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"wrote {cfg['paths']['classification']}")


if __name__ == "__main__":
    main()
