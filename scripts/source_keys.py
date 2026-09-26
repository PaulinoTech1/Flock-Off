#!/usr/bin/env python3
"""Stable dedup keys for citations (Layer 1: URL identity).

Every source in data/agencies.json gets a `source_key`: the canonical form
of its URL with cosmetic differences normalized away, so the same article
cited as https://example.com/a/?utm_source=x and
https://www.example.com/a gets one key.

Normalization (stdlib only, explicit and conservative):
  - scheme forced to https; host lowercased; default ports stripped
  - leading www./m./amp. host prefixes stripped
  - trailing /amp path segment stripped; trailing slash stripped; fragments dropped
  - query params sorted; known tracking params dropped (utm_*, fbclid, gclid,
    msclkid, mc_cid/mc_eid, _hsenc/_hsmi, igshid, yclid, srsltid, pk_/piwik_/matomo_*)
    All other params are significant and kept (pagination, article IDs, ...).

Deliberately NOT handled here (Layers 2/3 territory):
  - same article syndicated across different domains (needs content simhash)
  - articles whose content changed after citation (needs content re-fetch)

Usage:
  python3 scripts/source_keys.py          # backfill missing/stale source_key fields
  python3 scripts/source_keys.py --check  # exit 1 on missing/stale key, or on a
                                          # duplicate key within one agency's sources
"""
from __future__ import annotations

import json
import sys
import urllib.parse

DATA_PATH = "data/agencies.json"

# Exact tracking params to drop; plus any param starting with these prefixes.
TRACKING_PARAMS = {
    "fbclid", "gclid", "gclsrc", "msclkid", "mc_cid", "mc_eid",
    "_hsenc", "_hsmi", "igshid", "yclid", "srsltid",
    "vero_conv", "vero_id",
}
TRACKING_PREFIXES = ("utm_", "pk_", "piwik_", "matomo_")

HOST_PREFIXES = ("www.", "m.", "amp.")


def _is_tracking(name: str) -> bool:
    n = name.lower()
    return n in TRACKING_PARAMS or n.startswith(TRACKING_PREFIXES)


def canonical_url(url: str) -> str:
    parts = urllib.parse.urlsplit(url.strip())
    if parts.scheme not in ("http", "https"):
        raise ValueError(f"unexpected scheme in source URL: {url!r}")
    host = parts.hostname or ""
    host = host.lower()
    for prefix in HOST_PREFIXES:
        if host.startswith(prefix):
            host = host[len(prefix):]
            break
    # Drop default ports; keep non-default ones (they address different content).
    port = parts.port
    netloc = host if port in (None, 80, 443) else f"{host}:{port}"
    path = parts.path or ""
    # Collapse /amp variants: ".../amp", ".../amp/".
    if path == "/amp" or path.endswith("/amp/"):
        path = path[: -len("/amp/")] or "/"
    elif path.endswith("/amp"):
        path = path[: -len("/amp")] or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    params = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    kept = sorted((k, v) for k, v in params if not _is_tracking(k))
    query = urllib.parse.urlencode(kept)
    out = f"https://{netloc}{path}"
    if query:
        out += f"?{query}"
    return out


def iter_sources(data):
    for agency in data["agencies"]:
        for i, src in enumerate(agency.get("sources", [])):
            yield agency, i, src


def backfill(data) -> int:
    fixed = 0
    for _, _, src in iter_sources(data):
        key = canonical_url(src["url"])
        if src.get("source_key") != key:
            src["source_key"] = key
            fixed += 1
    return fixed


def check(data) -> list[str]:
    problems: list[str] = []
    for agency in data["agencies"]:
        seen: dict[str, str] = {}
        for src in agency.get("sources", []):
            url = src.get("url", "")
            try:
                expected = canonical_url(url)
            except ValueError as e:
                problems.append(f"{agency['id']}: {e}")
                continue
            if src.get("source_key") != expected:
                problems.append(
                    f"{agency['id']}: source_key missing/stale for {url[:80]} "
                    f"(expected {expected[:80]})"
                )
            if expected in seen:
                problems.append(
                    f"{agency['id']}: duplicate source_key {expected[:100]} "
                    f"(also used by {seen[expected][:60]})"
                )
            else:
                seen[expected] = src.get("title", url)[:60]
    return problems


def main(argv: list[str]) -> None:
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    if "--check" in argv:
        problems = check(data)
        if problems:
            print(f"{len(problems)} source_key problem(s):")
            for p in problems:
                print(" -", p)
            sys.exit(1)
        n = sum(len(a.get("sources", [])) for a in data["agencies"])
        print(f"OK: {n} citations, keys valid, no intra-agency duplicates")
        return
    fixed = backfill(data)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"backfilled {fixed} source_key fields")


if __name__ == "__main__":
    main(sys.argv[1:])
