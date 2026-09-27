"""Raw HTML snapshot archive in Vercel Blob.

Stores the exact, undoctored HTML of fetched sources so that when drift
is detected, the original page can be pulled up for forensic comparison.
The git archive (data/source_archive/) holds extracted text; this holds
the raw bytes.

Design:
  - Content-addressed: snapshots/<sha256-of-raw-html>.html
  - Identical content is never uploaded twice (checked before PUT)
  - Private blobs: retrieval requires ARCHIVE_BLOB_READ_WRITE_TOKEN
  - Fail-open with loud logging: a blob outage must not break the monitor.
    The git text archive is the primary record; this is the forensic backup.

Env:
  ARCHIVE_BLOB_READ_WRITE_TOKEN: token for the source-archive blob store.
    Must be set for uploads/downloads. Absence disables archiving silently
    (with a stderr warning) rather than failing.
"""

import hashlib
import json
import os
import sys
import urllib.request
import urllib.parse

BLOB_API = "https://vercel.com/api/blob"
API_VERSION = "12"  # pinned to the @vercel/blob protocol version verified 2026-09-25
TOKEN_ENV = "ARCHIVE_BLOB_READ_WRITE_TOKEN"
MAX_SNAPSHOT_BYTES = 10 * 1024 * 1024  # 10 MB cap per raw snapshot


def _token():
    return os.environ.get(TOKEN_ENV)


def _warn(msg):
    print(f"blob_archive: WARNING: {msg}", file=sys.stderr)


def snapshot_hash(html: str) -> str:
    """SHA256 of the raw HTML. Used as the content-addressed blob key."""
    return hashlib.sha256(html.encode("utf-8")).hexdigest()


def snapshot_pathname(content_hash: str) -> str:
    return f"snapshots/{content_hash}.html"


def _api_request(method, path, token, data=None, headers=None):
    req_headers = {
        "authorization": f"Bearer {token}",
        "x-api-version": API_VERSION,
    }
    if headers:
        req_headers.update(headers)
    body = None
    if data is not None:
        body = data.encode("utf-8") if isinstance(data, str) else data
    req = urllib.request.Request(
        BLOB_API + path, data=body, headers=req_headers, method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:
        return None, str(e)


def snapshot_exists(content_hash: str, token=None) -> bool:
    """Check whether a snapshot is already stored. Never raises."""
    token = token or _token()
    if not token:
        return False
    pathname = snapshot_pathname(content_hash)
    params = urllib.parse.urlencode({"prefix": pathname, "limit": "1"})
    try:
        status, body = _api_request("GET", f"/?{params}", token)
        if status != 200:
            return False
        data = json.loads(body)
        blobs = data.get("blobs", [])
        return any(b.get("pathname") == pathname for b in blobs)
    except Exception:
        return False


def put_snapshot(html: str, url: str, fetched_at: str, token=None) -> str | None:
    """Upload raw HTML to the blob archive. Returns the content hash, or
    None if archiving was skipped or failed. Never raises: failures are
    logged to stderr and the caller continues without the snapshot.

    Skips upload when:
      - ARCHIVE_BLOB_READ_WRITE_TOKEN is not set
      - the HTML exceeds MAX_SNAPSHOT_BYTES
      - an identical snapshot already exists (deduplication)
    """
    token = token or _token()
    if not token:
        _warn(f"{TOKEN_ENV} not set; skipping raw snapshot for {url}")
        return None
    if len(html.encode("utf-8")) > MAX_SNAPSHOT_BYTES:
        _warn(f"raw HTML too large ({len(html)} chars); skipping snapshot for {url}")
        return None

    chash = snapshot_hash(html)
    if snapshot_exists(chash, token):
        return chash  # already archived; deduplication

    pathname = snapshot_pathname(chash)
    params = urllib.parse.urlencode({"pathname": pathname})
    headers = {
        "x-vercel-blob-access": "private",
        "x-content-type": "text/html; charset=utf-8",
        "x-add-random-suffix": "0",
        # Provenance metadata, retrievable via blob head/list
        "x-source-url": url[:500],
        "x-fetched-at": fetched_at,
    }
    try:
        status, body = _api_request(
            "PUT", f"/?{params}", token, data=html, headers=headers
        )
        if status != 200:
            _warn(f"blob PUT failed for {url}: HTTP {status}: {body[:200]}")
            return None
        return chash
    except Exception as e:
        _warn(f"blob PUT exception for {url}: {e}")
        return None


def get_snapshot(content_hash: str, token=None) -> str | None:
    """Download a raw HTML snapshot by content hash. Returns the HTML string,
    or None if not found or on error. Raises ValueError on malformed hash."""
    if not content_hash or not isinstance(content_hash, str):
        raise ValueError("content_hash must be a non-empty string")
    if len(content_hash) != 64 or not all(
        c in "0123456789abcdef" for c in content_hash
    ):
        raise ValueError("content_hash must be a 64-char lowercase hex sha256")
    token = token or _token()
    if not token:
        raise ValueError(f"{TOKEN_ENV} is not set")

    pathname = snapshot_pathname(content_hash)
    params = urllib.parse.urlencode({"prefix": pathname, "limit": "1"})
    status, body = _api_request("GET", f"/?{params}", token)
    if status != 200:
        raise RuntimeError(f"blob list failed: HTTP {status}")
    data = json.loads(body)
    blobs = data.get("blobs", [])
    hit = next((b for b in blobs if b.get("pathname") == pathname), None)
    if not hit or not hit.get("url"):
        return None  # not archived

    # Private blob: fetch with the token
    req = urllib.request.Request(
        hit["url"], headers={"authorization": f"Bearer {token}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read(MAX_SNAPSHOT_BYTES + 1)
            if len(raw) > MAX_SNAPSHOT_BYTES:
                raise RuntimeError("snapshot exceeds size cap")
            return raw.decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise RuntimeError(f"snapshot download failed: HTTP {e.code}")


def main():
    """CLI: python3 scripts/blob_archive.py get <content_hash> [output_file]"""
    if len(sys.argv) < 3 or sys.argv[1] != "get":
        print("usage: python3 scripts/blob_archive.py get <content_hash> [output_file]")
        sys.exit(2)
    chash = sys.argv[2]
    try:
        html = get_snapshot(chash)
    except (ValueError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
    if html is None:
        print(f"snapshot not found: {chash}", file=sys.stderr)
        sys.exit(1)
    if len(sys.argv) > 3:
        with open(sys.argv[3], "w", encoding="utf-8") as f:
            f.write(html)
        print(f"wrote {len(html)} chars to {sys.argv[3]}")
    else:
        sys.stdout.write(html)


if __name__ == "__main__":
    main()
