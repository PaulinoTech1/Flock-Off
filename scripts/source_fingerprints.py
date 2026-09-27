#!/usr/bin/env python3
"""Content fingerprints for citations (Layers 2 and 3: near-dup + update detection).

For each citation this builds a stable content identity independent of URL:
  - simhash64: 64-bit similarity hash over word 5-shingles. Two pages with
    Hamming distance <= 3 are near-duplicates (same article, different URL).
  - content_hash: sha256 of normalized text. Exact equality = unchanged.
  - text_len, title, fetched_at, fetch_status, final_url.

Legitimate fetching only: one honest user-agent, 1.5s delay between
requests, 12s timeout, 300KB cap. Bot-blocked pages (401/402/403/429) are
recorded as "blocked" and excluded from pairing, never guessed at.
PDFs and non-HTML are recorded as "non_html" (stdlib cannot extract PDF text).

Storage: data/source_fingerprints.json, keyed by source_key (Layer 1), so
identity survives URL cosmetics. The weekly monitor reads this file
read-only from GitHub raw; the baseline advances when a maintainer runs
--refresh and pushes the result.

Known limitation: template-heavy aggregator pages (e.g. newslocker.com)
share so much boilerplate that two different stories can land within the
near-duplicate threshold. Such pairs surface as informational flags for
human review; the threshold is tuned for recall, the human loop is the
precision filter.

Usage:
  python3 scripts/flockoff.py fingerprints refresh [--max N]
      [--max-age-days D] [--keys k1,k2]
    Refresh fingerprints: new keys, entries older than --max-age-days
    (default from config), and non-ok entries. --keys limits to specific
    source_keys (comma-separated). --max caps how many fetches this run
    performs (politeness).

  python3 scripts/flockoff.py fingerprints drift [--keys k1,k2] [--max N]
    Fatal drift gate (pre-push / CI): re-fetch previously fingerprinted
    sources and fail (exit 1) if any shows Hamming distance >=
    fingerprints.update_distance against its stored simhash AND has no
    human re-review recorded in data/fingerprint_reviews.json. Read-only:
    never rewrites the fingerprint baseline. A human reviews drift, then
    either accepts it (records a review + runs refresh to advance the
    baseline) or rejects it (replaces the source).
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from source_keys import canonical_url  # noqa: E402
from flockoff_config import ConfigError, load_config  # noqa: E402

_cfg_cache: dict | None = None


def _cfg() -> dict:
    """Load (once) the validated pipeline config."""
    global _cfg_cache
    if _cfg_cache is None:
        _cfg_cache = load_config()
    return _cfg_cache


# Config-backed tunables (config/flock-off.yaml). Accessors, not constants,
# so a config change takes effect without code edits. Callers in other
# modules must use these, never import ALL-CAPS names.
def data_path() -> str:
    return _cfg()["paths"]["data"]


def fingerprints_path() -> str:
    return _cfg()["paths"]["fingerprints"]


def archive_dir() -> str:
    """Directory holding per-source extracted-text snapshots."""
    return _cfg()["paths"]["archive"]


def archive_filename(key: str) -> str:
    """Stable archive filename for a source key."""
    return hashlib.sha256(key.encode()).hexdigest() + ".txt"


def write_archive(key: str, text: str, directory: str | None = None) -> str:
    """Write the extracted text snapshot for a source key.

    Returns the archive filename. The file holds exactly the text the
    simhash/content_hash were computed from, so git history of the
    archive dir is a permanent evidence record even if the source
    later changes or disappears.
    """
    directory = directory or archive_dir()
    os.makedirs(directory, exist_ok=True)
    filename = archive_filename(key)
    with open(os.path.join(directory, filename), "w", encoding="utf-8") as f:
        f.write(text)
    return filename


def user_agent() -> str:
    return _cfg()["fetch"]["user_agent"]


def fetch_delay() -> float:
    return _cfg()["fetch"]["delay_seconds"]


def fetch_timeout() -> float:
    return _cfg()["fetch"]["timeout_seconds"]


def max_bytes() -> int:
    return _cfg()["fetch"]["max_bytes"]


def min_text_len() -> int:
    return _cfg()["fingerprints"]["min_text_len"]


def pair_min_len() -> int:
    return _cfg()["fingerprints"]["pair_min_len"]


def near_dup_distance() -> int:
    return _cfg()["fingerprints"]["near_dup_distance"]


def update_distance() -> int:
    return _cfg()["fingerprints"]["update_distance"]


def default_max_age_days() -> int:
    return _cfg()["fingerprints"]["max_age_days"]


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.chunks: list[str] = []
        self.article_chunks: list[str] = []
        self.title_chunks: list[str] = []
        self._skip = 0
        self._in_article = 0
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "header", "footer", "nav", "aside"):
            self._skip += 1
        if tag in ("article", "main"):
            self._in_article += 1
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "header", "footer", "nav", "aside"):
            self._skip = max(0, self._skip - 1)
        if tag in ("article", "main"):
            self._in_article = max(0, self._in_article - 1)
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        t = data.strip()
        if not t:
            return
        if self._in_title:
            self.title_chunks.append(t)
            return
        if self._skip:
            return
        self.chunks.append(t)
        if self._in_article:
            self.article_chunks.append(t)


def extract_text(html: str) -> tuple[str, str]:
    ext = _TextExtractor()
    ext.feed(html[:max_bytes()])
    title = re.sub(r"\s+", " ", " ".join(ext.title_chunks)).strip()
    body = ext.article_chunks if len(" ".join(ext.article_chunks)) > 200 else ext.chunks
    text = re.sub(r"\s+", " ", " ".join(body)).strip()
    return title, text


def fetch_page(url: str) -> tuple[str, str | None, str | None]:
    """Return (status, final_url, html). status: ok|blocked|error|non_html."""
    req = urllib.request.Request(url, headers={
        "User-Agent": user_agent(),
        "Accept": "text/html,application/xhtml+xml",
    })
    try:
        with urllib.request.urlopen(req, timeout=fetch_timeout()) as resp:
            ctype = resp.headers.get("Content-Type", "")
            final_url = resp.geturl()
            if "html" not in ctype and "text" not in ctype:
                return "non_html", final_url, None
            raw = resp.read(max_bytes() + 1)
    except urllib.error.HTTPError as e:
        if e.code in (401, 402, 403, 429):
            return "blocked", None, None
        return "error", None, None
    except Exception:
        return "error", None, None
    try:
        html = raw.decode("utf-8", errors="replace")
    except Exception:
        return "error", None, None
    return "ok", final_url, html


def simhash64(text: str) -> int | None:
    words = re.findall(r"[a-z0-9]+", text.lower())
    if len(words) < 20:
        return None
    vec = [0] * 64
    for i in range(len(words) - 4):
        h = int.from_bytes(
            hashlib.md5(" ".join(words[i:i + 5]).encode()).digest()[:8], "big")
        for b in range(64):
            vec[b] += 1 if (h >> b) & 1 else -1
    return sum(1 << b for b in range(64) if vec[b] > 0)


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def fingerprint_url(url: str, today: str,
                    archive_directory: str | None = None,
                    key: str | None = None) -> dict:
    """Fingerprint one URL. Also writes the extracted-text snapshot to the
    source archive under the canonical source key (defaults to the URL).
    archive_directory overrides the configured dir; tests use it to avoid
    touching the real archive.

    A structured JSON snapshot (text + metadata + integrity block) is also
    archived to Vercel Blob via blob_archive, best-effort: a blob failure
    never breaks fingerprinting. The blob pathname is stored as
    snapshot_path.
    """
    status, final_url, html = fetch_page(url)
    rec: dict = {
        "url": url,
        "final_url": final_url,
        "title": None,
        "simhash": None,
        "content_hash": None,
        "text_len": 0,
        "fetched_at": today,
        "fetch_status": status,
        "archive": None,
        "snapshot_path": None,
    }
    if status == "ok" and html:
        title, text = extract_text(html)
        rec["title"] = title or None
        rec["text_len"] = len(text)
        if text:
            rec["archive"] = write_archive(key or url, text,
                                           archive_directory)
        if len(text) >= min_text_len():
            rec["content_hash"] = content_hash(text)
            sh = simhash64(text)
            rec["simhash"] = format(sh, "016x") if sh is not None else None
            # JSON snapshot to blob (forensic copy for drift review).
            # Best-effort: never breaks fingerprinting on failure.
            try:
                import blob_archive as _ba
            except ImportError as _ie:
                import sys as _sys
                print(f"blob_archive: WARNING: cannot import blob_archive: "
                      f"{_ie}", file=_sys.stderr)
                _ba = None
            if _ba is not None:
                try:
                    from datetime import datetime, timezone as _tz
                    _fetched_at = datetime.now(_tz.utc).isoformat()
                    snap = _ba.build_snapshot(
                        source_key=key or url,
                        url=url,
                        text=text,
                        final_url=final_url,
                        title=title or None,
                        content_hash=rec["content_hash"],
                        simhash=rec["simhash"],
                        accurate_to=today,
                        fetched_at=_fetched_at,
                    )
                    rec["snapshot_path"] = _ba.put_snapshot(snap)
                except Exception:
                    pass
        else:
            rec["fetch_status"] = "thin"
    return rec


def iter_citations(data):
    for agency in data["agencies"]:
        for src in agency.get("sources", []):
            key = src.get("source_key") or canonical_url(src["url"])
            yield agency["id"], src.get("title", ""), src["url"], key


def load_fingerprints(path: str | None = None) -> dict:
    path = path or fingerprints_path()
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def save_fingerprints(fps: dict, path: str | None = None) -> None:
    path = path or fingerprints_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(fps, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")


def reviews_path() -> str:
    return os.path.join(os.path.dirname(fingerprints_path()),
                        "fingerprint_reviews.json")


def load_reviews(path: str | None = None) -> dict:
    path = path or reviews_path()
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def save_reviews(reviews: dict, path: str | None = None) -> None:
    path = path or reviews_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(reviews, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")


def is_rereviewed(key: str, fp: dict, reviews: dict) -> bool:
    """A drift is re-reviewed when a human recorded a decision at or after
    the fingerprint baseline it drifted from was captured."""
    rev = reviews.get(key)
    if not rev:
        return False
    try:
        return rev.get("reviewed_at", "") >= fp.get("fetched_at", "")
    except TypeError:
        return False


def drift_check(fps: dict, reviews: dict, keys: set[str] | None = None,
                max_n: int | None = None) -> tuple[list[dict], dict]:
    """Re-fetch previously fingerprinted sources and compare against the
    stored baseline. Read-only: never rewrites fps.

    Returns (drifted, stats). Each drifted entry has key, url, agency_ids,
    distance, and text_len_change. A source counts as drifted when the live
    simhash is at Hamming distance >= fingerprints.update_distance from the
    stored simhash AND no human re-review covers the baseline.
    """
    threshold = update_distance()
    today_s = datetime.date.today().isoformat()
    drifted: list[dict] = []
    stats = {"checked": 0, "drifted": 0, "rereviewed": 0,
             "blocked": 0, "error": 0, "skipped_no_baseline": 0}
    # Map key -> agency ids for reporting (needs the dataset; fps records
    # carry no agency link, so callers pass keys scoped from changed records
    # and the CLI resolves agency ids separately).
    candidates = [k for k, fp in fps.items()
                  if fp.get("fetch_status") == "ok" and fp.get("simhash")
                  and (keys is None or k in keys)]
    for key in candidates:
        if max_n is not None and stats["checked"] >= max_n:
            break
        fp = fps[key]
        stats["checked"] += 1
        if is_rereviewed(key, fp, reviews):
            stats["rereviewed"] += 1
            continue
        time.sleep(fetch_delay())
        status, _final, html = fetch_page(fp.get("url") or key)
        if status == "error":
            # One retry: transient network failures should not block a push,
            # but a persistently unreachable source must not pass silently.
            time.sleep(fetch_delay())
            status, _final, html = fetch_page(fp.get("url") or key)
        if status != "ok" or not html:
            stats["blocked" if status == "blocked" else "error"] += 1
            print(f"  [{status}] {key[:70]}", flush=True)
            continue
        _title, text = extract_text(html)
        new_sh = simhash64(text)
        if new_sh is None:
            stats["error"] += 1
            continue
        dist = hamming(new_sh, int(fp["simhash"], 16))
        if dist >= threshold:
            stats["drifted"] += 1
            old_len = fp.get("text_len") or 0
            drifted.append({
                "key": key,
                "url": fp.get("url") or key,
                "distance": dist,
                "threshold": threshold,
                "baseline_fetched_at": fp.get("fetched_at"),
                "checked_at": today_s,
                "text_len_change": (len(text) - old_len) / old_len if old_len else None,
            })
        print(f"  [{'DRIFT' if dist >= threshold else 'ok'} d={dist}] {key[:70]}",
              flush=True)
    return drifted, stats


def refresh(data: dict, fps: dict, max_n: int | None = None,
            max_age_days: int | None = None,
            only_keys: set[str] | None = None) -> dict:
    if max_age_days is None:
        max_age_days = default_max_age_days()
    today = datetime.date.today()
    today_s = today.isoformat()
    stats = {"fetched": 0, "ok": 0, "blocked": 0, "error": 0,
             "non_html": 0, "thin": 0, "skipped": 0}
    seen: set[str] = set()
    for agency_id, title, url, key in iter_citations(data):
        if only_keys is not None and key not in only_keys:
            continue
        if key in seen:
            stats["skipped"] += 1
            continue
        seen.add(key)
        fp = fps.get(key)
        needs = True
        if fp is not None and only_keys is None:
            try:
                age = (today - datetime.date.fromisoformat(fp["fetched_at"])).days
            except (KeyError, ValueError):
                age = max_age_days + 1
            needs = fp.get("fetch_status") != "ok" or age > max_age_days
        if not needs:
            stats["skipped"] += 1
            continue
        if max_n is not None and stats["fetched"] >= max_n:
            stats["skipped"] += 1
            continue
        time.sleep(fetch_delay())
        rec = fingerprint_url(url, today_s, key=key)
        fps[key] = rec
        stats["fetched"] += 1
        stats[rec["fetch_status"]] = stats.get(rec["fetch_status"], 0) + 1
        print(f"  [{rec['fetch_status']}] {agency_id}: {url[:70]}", flush=True)
    return stats


def read_archive(key: str, directory: str | None = None) -> str | None:
    """Return the archived extracted text for a source key, or None."""
    directory = directory or archive_dir()
    path = os.path.join(directory, archive_filename(key))
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def backfill_archive(data: dict, fps: dict,
                     max_n: int | None = None) -> dict:
    """Populate missing source-archive snapshots.

    For each source key with no archive file, re-fetch and, on a clean
    ok result, write the archive and update the baseline (same
    accept-current-content semantics as refresh()). Non-ok fetches are
    left completely untouched so a backfill can never manufacture a
    drift-gate fatal out of a blocked or errored source.
    Returns stats.
    """
    today_s = datetime.date.today().isoformat()
    stats = {"fetched": 0, "archived": 0, "skipped": 0, "non_ok": 0}
    seen: set[str] = set()
    for agency_id, title, url, key in iter_citations(data):
        if key in seen:
            stats["skipped"] += 1
            continue
        seen.add(key)
        if read_archive(key) is not None:
            stats["skipped"] += 1
            continue
        if max_n is not None and stats["fetched"] >= max_n:
            stats["skipped"] += 1
            continue
        time.sleep(fetch_delay())
        rec = fingerprint_url(url, today_s, key=key)
        stats["fetched"] += 1
        if rec["fetch_status"] == "ok" and rec["archive"]:
            fps[key] = rec
            stats["archived"] += 1
        else:
            stats["non_ok"] += 1
        print(f"  [{rec['fetch_status']}] {agency_id}: {url[:70]}",
              flush=True)
    return stats


def main(argv: list[str]) -> None:
    if "--refresh" not in argv and "--drift" not in argv \
            and "--backfill-archive" not in argv:
        print(__doc__)
        return
    try:
        _cfg()
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(2)
    if "--drift" in argv:
        _main_drift(argv)
        return
    if "--backfill-archive" in argv:
        fps = load_fingerprints()
        with open(data_path(), encoding="utf-8") as f:
            data = json.load(f)
        max_n = None
        for i, a in enumerate(argv):
            if a == "--max" and i + 1 < len(argv):
                max_n = int(argv[i + 1])
        stats = backfill_archive(data, fps, max_n=max_n)
        save_fingerprints(fps)
        print(f"done: {stats['fetched']} fetched, {stats['archived']} "
              f"archived, {stats['non_ok']} non-ok left untouched, "
              f"{stats['skipped']} skipped")
        return
    max_n = None
    max_age = default_max_age_days()
    only_keys = None
    for i, a in enumerate(argv):
        if a == "--max" and i + 1 < len(argv):
            max_n = int(argv[i + 1])
        if a == "--max-age-days" and i + 1 < len(argv):
            max_age = int(argv[i + 1])
        if a == "--keys" and i + 1 < len(argv):
            only_keys = set(argv[i + 1].split(","))
    with open(data_path(), encoding="utf-8") as f:
        data = json.load(f)
    fps = load_fingerprints()
    print(f"refreshing fingerprints ({len(fps)} existing)...")
    stats = refresh(data, fps, max_n=max_n, max_age_days=max_age, only_keys=only_keys)
    save_fingerprints(fps)
    print(f"done: {stats['fetched']} fetched ({stats}), {len(fps)} keys total")


def _main_drift(argv: list[str]) -> None:
    max_n = None
    only_keys = None
    for i, a in enumerate(argv):
        if a == "--max" and i + 1 < len(argv):
            max_n = int(argv[i + 1])
        if a == "--keys" and i + 1 < len(argv):
            only_keys = set(argv[i + 1].split(","))
    fps = load_fingerprints()
    reviews = load_reviews()
    # key -> agency ids, for the failure report
    with open(data_path(), encoding="utf-8") as f:
        data = json.load(f)
    owners: dict[str, list[str]] = {}
    for agency_id, _title, _url, key in iter_citations(data):
        owners.setdefault(key, [])
        if agency_id not in owners[key]:
            owners[key].append(agency_id)
    print(f"drift check: {len(fps)} baselines, "
          f"{len(only_keys) if only_keys else 'all'} scoped...")
    drifted, stats = drift_check(fps, reviews, keys=only_keys, max_n=max_n)
    for d in drifted:
        d["agency_ids"] = owners.get(d["key"], [])
    print(f"done: {stats['checked']} checked, {stats['drifted']} drifted, "
          f"{stats['rereviewed']} re-reviewed, "
          f"{stats['blocked']} blocked, {stats['error']} error")
    unverifiable = stats["blocked"] + stats["error"]
    if unverifiable:
        print(f"\nFATAL: {unverifiable} source(s) could not be re-fetched, so "
              "the gate cannot confirm they still support their citations. "
              "A source that cannot be verified is not a verified source.",
              file=sys.stderr)
        print("Either replace the source, or verify it by another means and "
              "record a review in data/fingerprint_reviews.json with "
              "reviewed_at at or after the baseline's fetched_at.",
              file=sys.stderr)
        sys.exit(1)
    if drifted:
        print("\nFATAL: unreviewed drift detected "
              f"(threshold {update_distance()}):", file=sys.stderr)
        for d in drifted:
            print(f"  - {d['key'][:80]} d={d['distance']} "
                  f"agencies={','.join(d['agency_ids'])}", file=sys.stderr)
        print("Review each drift, then either accept (record a review in "
              "data/fingerprint_reviews.json and refresh the baseline) or "
              "reject (replace the source).", file=sys.stderr)
        sys.exit(1)
    print("no unreviewed drift")


if __name__ == "__main__":
    main(sys.argv[1:])
