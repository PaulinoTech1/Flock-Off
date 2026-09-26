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
  python3 scripts/source_fingerprints.py --refresh [--max N]
      [--max-age-days 60] [--keys k1,k2]
    Refresh fingerprints: new keys, entries older than --max-age-days, and
    non-ok entries. --keys limits to specific source_keys (comma-separated).
    --max caps how many fetches this run performs (politeness).
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

DATA_PATH = "data/agencies.json"
FINGERPRINTS_PATH = "data/source_fingerprints.json"

USER_AGENT = "Flock-Off/1.0 (+https://flock-off.vercel.app) citation-audit"
FETCH_DELAY = 1.5
FETCH_TIMEOUT = 12
MAX_BYTES = 300_000
MIN_TEXT_LEN = 200      # below this the fingerprint is "thin", excluded from pairing
PAIR_MIN_LEN = 800      # simhash pairing needs enough text to be meaningful
NEAR_DUP_DISTANCE = 3   # Hamming distance (of 64) for near-duplicate
UPDATE_DISTANCE = 8     # Hamming distance that counts as a material rewrite


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
    ext.feed(html[:MAX_BYTES])
    title = re.sub(r"\s+", " ", " ".join(ext.title_chunks)).strip()
    body = ext.article_chunks if len(" ".join(ext.article_chunks)) > 200 else ext.chunks
    text = re.sub(r"\s+", " ", " ".join(body)).strip()
    return title, text


def fetch_page(url: str) -> tuple[str, str | None, str | None]:
    """Return (status, final_url, html). status: ok|blocked|error|non_html."""
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
    })
    try:
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
            ctype = resp.headers.get("Content-Type", "")
            final_url = resp.geturl()
            if "html" not in ctype and "text" not in ctype:
                return "non_html", final_url, None
            raw = resp.read(MAX_BYTES + 1)
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


def fingerprint_url(url: str, today: str) -> dict:
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
    }
    if status == "ok" and html:
        title, text = extract_text(html)
        rec["title"] = title or None
        rec["text_len"] = len(text)
        if len(text) >= MIN_TEXT_LEN:
            rec["content_hash"] = content_hash(text)
            sh = simhash64(text)
            rec["simhash"] = format(sh, "016x") if sh is not None else None
        else:
            rec["fetch_status"] = "thin"
    return rec


def iter_citations(data):
    for agency in data["agencies"]:
        for src in agency.get("sources", []):
            key = src.get("source_key") or canonical_url(src["url"])
            yield agency["id"], src.get("title", ""), src["url"], key


def load_fingerprints(path: str = FINGERPRINTS_PATH) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def save_fingerprints(fps: dict, path: str = FINGERPRINTS_PATH) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(fps, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")


def refresh(data: dict, fps: dict, max_n: int | None = None,
            max_age_days: int = 60, only_keys: set[str] | None = None) -> dict:
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
        time.sleep(FETCH_DELAY)
        rec = fingerprint_url(url, today_s)
        fps[key] = rec
        stats["fetched"] += 1
        stats[rec["fetch_status"]] = stats.get(rec["fetch_status"], 0) + 1
        print(f"  [{rec['fetch_status']}] {agency_id}: {url[:70]}", flush=True)
    return stats


def main(argv: list[str]) -> None:
    if "--refresh" not in argv:
        print(__doc__)
        return
    max_n = None
    max_age = 60
    only_keys = None
    for i, a in enumerate(argv):
        if a == "--max" and i + 1 < len(argv):
            max_n = int(argv[i + 1])
        if a == "--max-age-days" and i + 1 < len(argv):
            max_age = int(argv[i + 1])
        if a == "--keys" and i + 1 < len(argv):
            only_keys = set(argv[i + 1].split(","))
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    fps = load_fingerprints()
    print(f"refreshing fingerprints ({len(fps)} existing)...")
    stats = refresh(data, fps, max_n=max_n, max_age_days=max_age, only_keys=only_keys)
    save_fingerprints(fps)
    print(f"done: {stats['fetched']} fetched ({stats}), {len(fps)} keys total")


if __name__ == "__main__":
    main(sys.argv[1:])
