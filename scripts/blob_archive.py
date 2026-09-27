"""Source snapshot archive in Vercel Blob.

Stores structured JSON snapshots of fetched sources: extracted text plus
discoverability metadata plus integrity validation. When drift is detected,
the original snapshot can be pulled up and cryptographically verified
against tampering.

Snapshot schema (v1):
  {
    "schema_version": 1,
    "source_key": "<canonical source key>",
    "agency_id": "<agency slug or null>",
    "url": "<requested URL>",
    "final_url": "<URL after redirects>",
    "fetched_at": "<ISO 8601 UTC>",
    "accurate_to": "<YYYY-MM-DD the data represents>",
    "title": "<page title or null>",
    "text": "<extracted text, no images or binary>",
    "content_hash": "<sha256 of text>",
    "simhash": "<16-hex simhash or null>",
    "fetch_status": "ok",
    "meta": {
      "content_type": "text/html",
      "text_len": 1234,
      "word_count": 200
    },
    "integrity": {
      "algorithm": "sha256",
      "payload_hash": "<sha256 of canonical JSON of all fields above>"
    }
  }

Integrity model:
  payload_hash covers every field except the integrity block itself,
  serialized as canonical JSON (sorted keys, no whitespace). To verify:
  re-serialize, re-hash, compare. A mismatch means the snapshot was
  altered after capture. This validates the archive copy, not the live
  source: drift (live source changing) is detected separately by the
  fingerprint pipeline.

Storage:
  snapshots/<accurate_to>/<payload_hash>.json
  Date-prefixed for discoverability; content-addressed for deduplication.
  Private blobs. No images, no binary, text only.

Env:
  ARCHIVE_BLOB_READ_WRITE_TOKEN: token for the source-archive blob store.
    Absence disables archiving with a stderr warning, never a failure.
"""

import hashlib
import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timezone

BLOB_API = "https://vercel.com/api/blob"
API_VERSION = "12"  # pinned to the @vercel/blob protocol version verified 2026-09-25
TOKEN_ENV = "ARCHIVE_BLOB_READ_WRITE_TOKEN"
SCHEMA_VERSION = 1
MAX_TEXT_CHARS = 500_000  # 500K char cap on extracted text per snapshot


def _token():
    return os.environ.get(TOKEN_ENV)


def _warn(msg):
    print(f"blob_archive: WARNING: {msg}", file=sys.stderr)


def _utcnow_iso():
    return datetime.now(timezone.utc).isoformat()


def canonical_json(obj) -> str:
    """Deterministic serialization for hashing: sorted keys, compact."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True)


def payload_hash(snapshot: dict) -> str:
    """SHA256 of the canonical JSON of all fields except 'integrity'."""
    body = {k: v for k, v in snapshot.items() if k != "integrity"}
    return hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()


def build_snapshot(source_key: str, url: str, text: str,
                   agency_id: str | None = None,
                   final_url: str | None = None,
                   title: str | None = None,
                   content_hash: str | None = None,
                   simhash: str | None = None,
                   content_type: str | None = None,
                   accurate_to: str | None = None,
                   fetched_at: str | None = None) -> dict:
    """Build a v1 snapshot dict with integrity block. Raises ValueError
    on missing required fields or oversized text."""
    if not source_key or not isinstance(source_key, str):
        raise ValueError("source_key is required")
    if not url or not isinstance(url, str):
        raise ValueError("url is required")
    if not isinstance(text, str):
        raise ValueError("text must be a string")
    if len(text) > MAX_TEXT_CHARS:
        raise ValueError(
            f"text too large: {len(text)} chars exceeds {MAX_TEXT_CHARS}")
    if accurate_to is not None:
        # Validate YYYY-MM-DD
        try:
            datetime.strptime(accurate_to, "%Y-%m-%d")
        except ValueError:
            raise ValueError("accurate_to must be YYYY-MM-DD")

    fetched_at = fetched_at or _utcnow_iso()
    accurate_to = accurate_to or fetched_at[:10]
    words = text.split()

    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "source_key": source_key,
        "agency_id": agency_id,
        "url": url,
        "final_url": final_url or url,
        "fetched_at": fetched_at,
        "accurate_to": accurate_to,
        "title": title,
        "text": text,
        "content_hash": content_hash,
        "simhash": simhash,
        "fetch_status": "ok",
        "meta": {
            "content_type": content_type or "text/html",
            "text_len": len(text),
            "word_count": len(words),
        },
    }
    snapshot["integrity"] = {
        "algorithm": "sha256",
        "payload_hash": payload_hash(snapshot),
    }
    return snapshot


def verify_snapshot(snapshot: dict) -> tuple[bool, str]:
    """Verify a snapshot's integrity block. Returns (ok, message).
    Never raises on malformed input: returns (False, reason)."""
    if not isinstance(snapshot, dict):
        return False, "snapshot is not a JSON object"
    if snapshot.get("schema_version") != SCHEMA_VERSION:
        return False, (f"unsupported schema_version: "
                       f"{snapshot.get('schema_version')}")
    integ = snapshot.get("integrity")
    if not isinstance(integ, dict):
        return False, "missing integrity block"
    if integ.get("algorithm") != "sha256":
        return False, f"unsupported algorithm: {integ.get('algorithm')}"
    expected = integ.get("payload_hash")
    if not isinstance(expected, str) or len(expected) != 64:
        return False, "malformed payload_hash"
    actual = payload_hash(snapshot)
    if actual != expected:
        return False, (f"payload_hash mismatch: expected {expected[:16]}..., "
                       f"computed {actual[:16]}... (snapshot was altered)")
    return True, "integrity OK"


def snapshot_pathname(snapshot: dict) -> str:
    """Blob path: snapshots/<accurate_to>/<payload_hash>.json"""
    phash = snapshot["integrity"]["payload_hash"]
    date = snapshot["accurate_to"]
    return f"snapshots/{date}/{phash}.json"


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


def snapshot_exists(pathname: str, token=None) -> bool:
    """Check whether a snapshot path is already stored. Never raises."""
    token = token or _token()
    if not token:
        return False
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


def _ascii_header(value: str, max_len: int = 200) -> str:
    """Sanitize a string for use as an HTTP header value: ASCII only,
    truncated, no control characters. Prevents encoding failures on
    non-ASCII source keys."""
    cleaned = "".join(c for c in value if 32 <= ord(c) < 127)
    return cleaned[:max_len] or "unknown"


def put_snapshot(snapshot: dict, token=None) -> str | None:
    """Upload a built snapshot to the blob archive. Returns the blob
    pathname, or None if skipped/failed. Never raises: failures are
    logged to stderr and the caller continues.

    The snapshot is integrity-verified before upload. Refuses to store
    a snapshot that fails its own verification.
    """
    ok, msg = verify_snapshot(snapshot)
    if not ok:
        _warn(f"refusing to upload snapshot that fails verification: {msg}")
        return None
    token = token or _token()
    if not token:
        _warn(f"{TOKEN_ENV} not set; skipping snapshot for "
              f"{snapshot.get('source_key')}")
        return None

    pathname = snapshot_pathname(snapshot)
    if snapshot_exists(pathname, token):
        return pathname  # already archived; deduplication

    params = urllib.parse.urlencode({"pathname": pathname})
    headers = {
        "x-vercel-blob-access": "private",
        "x-content-type": "application/json; charset=utf-8",
        "x-add-random-suffix": "0",
        "x-source-key": _ascii_header(snapshot["source_key"]),
        "x-accurate-to": _ascii_header(snapshot["accurate_to"], 10),
    }
    body = canonical_json(snapshot)
    try:
        status, resp_body = _api_request(
            "PUT", f"/?{params}", token, data=body, headers=headers
        )
        if status != 200:
            _warn(f"blob PUT failed for {snapshot.get('source_key')}: "
                  f"HTTP {status}: {resp_body[:200]}")
            return None
        return pathname
    except Exception as e:
        _warn(f"blob PUT exception for {snapshot.get('source_key')}: {e}")
        return None


def _valid_hash(s: str) -> bool:
    return (isinstance(s, str) and len(s) == 64
            and all(c in "0123456789abcdef" for c in s))


def get_snapshot_by_path(pathname: str, token=None) -> dict | None:
    """Download and integrity-verify a snapshot by blob pathname.
    Returns the snapshot dict, or None if not found. Raises on
    integrity failure, missing token, or transport errors."""
    token = token or _token()
    if not token:
        raise ValueError(f"{TOKEN_ENV} is not set")
    params = urllib.parse.urlencode({"prefix": pathname, "limit": "1"})
    status, body = _api_request("GET", f"/?{params}", token)
    if status != 200:
        raise RuntimeError(f"blob list failed: HTTP {status}")
    data = json.loads(body)
    blobs = data.get("blobs", [])
    hit = next((b for b in blobs if b.get("pathname") == pathname), None)
    if not hit or not hit.get("url"):
        return None

    req = urllib.request.Request(
        hit["url"], headers={"authorization": f"Bearer {token}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read(2 * 1024 * 1024)  # 2 MB cap on download
            snapshot = json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise RuntimeError(f"snapshot download failed: HTTP {e.code}")
    ok, msg = verify_snapshot(snapshot)
    if not ok:
        raise RuntimeError(f"snapshot integrity check failed: {msg}")
    return snapshot


def list_snapshots(date: str | None = None, limit: int = 100,
                   cursor: str | None = None, token=None) -> dict:
    """List snapshot pathnames, optionally filtered by accurate_to date.
    Returns the raw blob list response dict."""
    token = token or _token()
    if not token:
        raise ValueError(f"{TOKEN_ENV} is not set")
    prefix = f"snapshots/{date}/" if date else "snapshots/"
    params = urllib.parse.urlencode(
        {"prefix": prefix, "limit": str(min(limit, 1000))})
    if cursor:
        params += "&" + urllib.parse.urlencode({"cursor": cursor})
    status, body = _api_request("GET", f"/?{params}", token)
    if status != 200:
        raise RuntimeError(f"blob list failed: HTTP {status}")
    return json.loads(body)


def main():
    """CLI:
      get <pathname> [output_file]   download + verify a snapshot
      verify <file>                  verify a local snapshot file
      list [--date YYYY-MM-DD]        list snapshot pathnames
    """
    if len(sys.argv) < 2:
        print("usage: blob_archive.py {get|verify|list} ...", file=sys.stderr)
        sys.exit(2)
    cmd = sys.argv[1]
    try:
        if cmd == "get" and len(sys.argv) >= 3:
            snap = get_snapshot_by_path(sys.argv[2])
            if snap is None:
                print(f"snapshot not found: {sys.argv[2]}", file=sys.stderr)
                sys.exit(1)
            out = (canonical_json(snap) if len(sys.argv) == 3
                   else None)
            if out is None:
                with open(sys.argv[3], "w", encoding="utf-8") as f:
                    f.write(canonical_json(snap))
                print(f"wrote snapshot to {sys.argv[3]} "
                      f"(integrity verified)")
            else:
                sys.stdout.write(out)
        elif cmd == "verify" and len(sys.argv) >= 3:
            with open(sys.argv[2], encoding="utf-8") as f:
                snap = json.load(f)
            ok, msg = verify_snapshot(snap)
            print(f"{'OK' if ok else 'FAIL'}: {msg}")
            sys.exit(0 if ok else 1)
        elif cmd == "list":
            date = None
            if "--date" in sys.argv:
                date = sys.argv[sys.argv.index("--date") + 1]
            data = list_snapshots(date=date)
            for b in data.get("blobs", []):
                print(b.get("pathname"))
            if data.get("hasMore"):
                print(f"... more available (cursor: {data.get('cursor')})",
                      file=sys.stderr)
        else:
            print(f"unknown command: {cmd}", file=sys.stderr)
            sys.exit(2)
    except (ValueError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
