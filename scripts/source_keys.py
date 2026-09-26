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
  python3 scripts/flockoff.py keys backfill   # fill missing/stale source_key fields
  python3 scripts/flockoff.py keys check      # exit 1 on missing/stale key, or on a
                                             # duplicate key within one agency's sources
  (legacy: python3 scripts/source_keys.py [--check])

Normalization lists (tracking params, host prefixes) come from
config/flock-off.yaml and are validated on load.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flockoff_config import ConfigError, load_config  # noqa: E402
from flockoff_errors import fmt  # noqa: E402

_cfg_cache: dict | None = None


def _cfg() -> dict:
    """Load (once) the validated pipeline config."""
    global _cfg_cache
    if _cfg_cache is None:
        _cfg_cache = load_config()
    return _cfg_cache


def _dedup() -> dict:
    return _cfg()["dedup"]


def _is_tracking(name: str) -> bool:
    d = _dedup()
    n = name.lower()
    return n in d["tracking_params"] or n.startswith(tuple(d["tracking_prefixes"]))


def canonical_url(url: str) -> str:
    parts = urllib.parse.urlsplit(url.strip())
    if parts.scheme not in ("http", "https"):
        raise ValueError(f"unexpected scheme in source URL: {url!r}")
    host = parts.hostname or ""
    host = host.lower()
    for prefix in _dedup()["host_prefixes"]:
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
                problems.append(fmt("E_KEY_BADURL", f"{agency['id']}: {e}"))
                continue
            if src.get("source_key") != expected:
                code = "E_KEY_MISSING" if "source_key" not in src else "E_KEY_STALE"
                problems.append(fmt(
                    code,
                    f"{agency['id']}: key problem for {url[:80]} "
                    f"(expected {expected[:80]})"))
            if expected in seen:
                problems.append(fmt(
                    "E_KEY_DUP",
                    f"{agency['id']}: duplicate source_key {expected[:100]} "
                    f"(also used by {seen[expected][:60]})"))
            else:
                seen[expected] = src.get("title", url)[:60]
    return problems


def main(argv: list[str]) -> None:
    try:
        cfg = _cfg()
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
    data_path = cfg["paths"]["data"]
    with open(data_path, encoding="utf-8") as f:
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
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"backfilled {fixed} source_key fields")


if __name__ == "__main__":
    main(sys.argv[1:])
