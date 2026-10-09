#!/usr/bin/env python3
"""Browser-like HTTP fetch client for Flock-Off source fetching.

The old fetcher (bare urllib, two headers, Python TLS fingerprint) is a
well-known bot signal: many news sites 403 it on sight even though they
serve normal browsers fine. This module presents as an ordinary Chrome
client instead:

  - curl_cffi with Chrome TLS impersonation (JA3 / HTTP-2 fingerprint),
  - full browser header set (sec-ch-ua, sec-fetch-*, Accept-Language),
  - persistent cookie jar per client instance,
  - same polite pacing knobs the pipeline already uses (caller sleeps
    between fetches; timeout and byte caps from config).

Fail-open dependency: if curl_cffi is not installed, falls back to a
stdlib urllib client with the same browser header set. The fallback has a
Python TLS fingerprint, so it will still be blocked more often; it exists
so CI and minimal environments keep working.

What this does NOT do (standing rule, unchanged):
  - It does not solve Cloudflare Turnstile / CAPTCHA / "Just a moment"
    challenges. A presented challenge is recorded as "blocked":
    unverifiable, never evaded.
  - It does not rotate IPs, use proxies, or disguise request rate. One
    shared identity, honest delays, same as before.

Return contract matches source_fingerprints.fetch_page:
  (status, final_url, html) with status in ok|blocked|error|non_html.
"""
from __future__ import annotations

import gzip
import re
import urllib.request
import zlib

# Markers that mean "bot challenge page", even on HTTP 200.
_CHALLENGE_MARKERS = (
    "just a moment",
    "attention required",
    "cf-chl",
    "cf_chl",
    "why did this happen",
    "verifying you are human",
    "verify you are human",
    "captcha",
)

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "sec-ch-ua": '"Chromium";v="126", "Google Chrome";v="126", "Not-A.Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}

_BLOCKED_CODES = frozenset({401, 402, 403, 429})


def _looks_like_challenge(html: str) -> bool:
    if not html:
        return False
    # Cheap check on the head of the document; challenge pages are small.
    head = html[:8000].lower()
    title = re.search(r"<title>(.*?)</title>", head, re.S)
    if title and any(m in title.group(1) for m in _CHALLENGE_MARKERS):
        return True
    return "just a moment" in head and "cloudflare" in head


def _sniff_blocked(status_code: int, html: str | None) -> bool:
    if status_code in _BLOCKED_CODES:
        return True
    return _looks_like_challenge(html or "")


def _decompress_body(raw: bytes, content_encoding: str | None) -> bytes:
    """Undo Content-Encoding so callers always see plain bytes.

    Regression guard: the stdlib urllib backend used to advertise
    "Accept-Encoding: gzip, deflate, br" but never decoded the response,
    so a gzipping server produced binary garbage that was fingerprinted
    as page text (false drift). curl_cffi decodes transparently; this
    keeps the fallback honest too. Unknown or undecodable encodings fall
    back to the raw bytes rather than failing the fetch.
    """
    enc = (content_encoding or "").lower()
    try:
        if "gzip" in enc:
            return gzip.decompress(raw)
        if "deflate" in enc:
            return zlib.decompress(raw)
    except Exception:
        return raw
    return raw


class FetchClient:
    """One browser-like session. Create per pipeline run, not per fetch."""

    def __init__(self, timeout: int = 12, max_bytes: int = 300_000,
                 impersonate: str = "chrome"):
        self.timeout = timeout
        self.max_bytes = max_bytes
        self._curl = None
        try:
            from curl_cffi import requests as _cr  # type: ignore
            self._sess = _cr.Session(impersonate=impersonate)
            self._curl = True
        except ImportError:
            self._sess = None
            self._curl = False

    @property
    def backend(self) -> str:
        return "curl_cffi" if self._curl else "urllib"

    def fetch(self, url: str) -> tuple[str, str | None, str | None]:
        if self._curl:
            return self._fetch_curl(url)
        return self._fetch_urllib(url)

    def _fetch_curl(self, url: str):
        try:
            resp = self._sess.get(url, headers=_BROWSER_HEADERS,
                                  timeout=self.timeout)
        except Exception:
            return "error", None, None
        body = resp.content[: self.max_bytes + 1]
        # curl_cffi normally decodes transparently; unpack defensively in
        # case a response arrives still encoded (see _decompress_body).
        body = _decompress_body(body, resp.headers.get("Content-Encoding"))
        html = body.decode("utf-8", errors="replace")
        if _sniff_blocked(resp.status_code, html):
            return "blocked", None, None
        if resp.status_code >= 400:
            return "error", None, None
        ctype = resp.headers.get("Content-Type", "")
        if "html" not in ctype and "text" not in ctype:
            return "non_html", resp.url, None
        return "ok", resp.url, html

    def _fetch_urllib(self, url: str):
        # The stdlib backend can only decode gzip/deflate: advertise just
        # those so a server never answers with brotli we cannot unpack.
        headers = dict(_BROWSER_HEADERS)
        headers["Accept-Encoding"] = "gzip, deflate"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                code = resp.status
                ctype = resp.headers.get("Content-Type", "")
                final_url = resp.geturl()
                raw = resp.read(self.max_bytes + 1)
                encoding = resp.headers.get("Content-Encoding")
        except urllib.request.HTTPError as e:
            if e.code in _BLOCKED_CODES:
                return "blocked", None, None
            return "error", None, None
        except Exception:
            return "error", None, None
        try:
            html = _decompress_body(raw, encoding).decode("utf-8", errors="replace")
        except Exception:
            return "error", None, None
        if _sniff_blocked(code, html):
            return "blocked", None, None
        if "html" not in ctype and "text" not in ctype:
            return "non_html", final_url, None
        return "ok", final_url, html
