# Source Archive Blob: Storage Template

How JSON snapshots are stored in the source-archive blob store.
Schema version 1. Companion to `scripts/blob_archive.py`.

## Blob Path Convention

```
snapshots/<YYYY-MM-DD>/<payload_hash>.json
```

- `<YYYY-MM-DD>`: the `accurate_to` date (when the content was fetched).
- `<payload_hash>`: SHA-256 hex digest of the canonical snapshot payload
  (all fields except `integrity`). Content-addressed: identical snapshots
  produce identical paths, enabling deduplication.
- Blob access: **private**. No public URLs.
- No random suffix (`x-add-random-suffix: 0`).
- Content-Type: `application/json; charset=utf-8`.

### Custom metadata headers (set on upload)

| Header | Value |
|--------|-------|
| `x-source-key` | ASCII-sanitized `source_key`, max 200 chars |
| `x-accurate-to` | `accurate_to` date (YYYY-MM-DD) |

## Snapshot JSON Template

```json
{
  "schema_version": 1,
  "source_key": "ma-boston-pd",
  "agency_id": "ma-boston-pd",
  "url": "https://example.gov/flock-contract",
  "final_url": "https://example.gov/flock-contract?v=2",
  "fetched_at": "2026-09-27T10:30:00+00:00",
  "accurate_to": "2026-09-27",
  "title": "City Council Approves Flock Camera Contract",
  "text": "<extracted plain text, up to 500,000 characters>",
  "content_hash": "57f22b449ffaf8ae...",
  "simhash": "a3f9c2e1...",
  "fetch_status": "ok",
  "meta": {
    "content_type": "text/html",
    "text_len": 58837,
    "word_count": 9204
  },
  "integrity": {
    "algorithm": "sha256",
    "payload_hash": "9d4e1a2b..."
  }
}
```

## Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | int | yes | Currently `1`. Bump on breaking changes. |
| `source_key` | string | yes | Canonical dedup key for the source (Layer 1). |
| `agency_id` | string/null | no | Agency this source belongs to. May be `null` if not supplied by the caller. |
| `url` | string | yes | Requested URL. |
| `final_url` | string | yes | URL after redirects. Defaults to `url` if no redirect. |
| `fetched_at` | string | yes | ISO 8601 UTC timestamp of the fetch (e.g. `2026-09-27T10:30:00+00:00`). |
| `accurate_to` | string | yes | Date the snapshot is accurate to, `YYYY-MM-DD`. Defaults to the date portion of `fetched_at`. This is the fetch date, not a publication or contract effective date. |
| `title` | string/null | no | Page `<title>` if extracted. |
| `text` | string | yes | Extracted plain text. No HTML, no images, no binary. Max 500,000 characters; larger pages raise `ValueError` and are not archived. |
| `content_hash` | string/null | no | SHA-256 of the extracted text (from the fingerprint pipeline). |
| `simhash` | string/null | no | Simhash fingerprint (from the fingerprint pipeline). |
| `fetch_status` | string | yes | Always `"ok"` for archived snapshots. Snapshots are only built on successful fetches. |
| `meta.content_type` | string | yes | HTTP content type, defaults to `"text/html"`. |
| `meta.text_len` | int | yes | Character count of `text`. |
| `meta.word_count` | int | yes | Whitespace-split word count of `text`. |
| `integrity.algorithm` | string | yes | Always `"sha256"`. |
| `integrity.payload_hash` | string | yes | SHA-256 hex digest over the canonical JSON of all fields except `integrity` itself. See Integrity below. |

## Integrity

The `integrity.payload_hash` is computed as follows:

1. Take all snapshot fields **except** `integrity`.
2. Serialize to canonical JSON: keys sorted, `separators=(",", ":")`,
   `ensure_ascii=True`.
3. SHA-256 hex digest of the UTF-8 bytes.

This proves the archived JSON has not been modified since construction.
It does **not** prove the extracted text is a complete or faithful
representation of the live source page. Raw response bytes are not retained.

Verification:

```bash
python3 scripts/blob_archive.py verify snapshot.json
python3 scripts/blob_archive.py get snapshots/2026-09-27/<hash>.json out.json
```

`get` downloads from the blob and verifies integrity automatically,
refusing to write the file on mismatch.

## What Is NOT Stored

- No images, video, or binary assets.
- No raw HTML or HTTP response bytes.
- No cookies, headers, or session data.
- No embedded scripts or stylesheets (text extraction strips markup).

## Limits

- 500,000 characters max per snapshot (`text` field).
- Snapshots are only built when the fetch succeeds (`fetch_status == "ok"`)
  and extracted text meets the pipeline minimum length.
- Failed blob operations never break fingerprinting (fail-open with
  `blob_archive: WARNING` on stderr).
- Duplicate detection: `snapshot_exists()` HEAD-checks the computed
  pathname before upload; identical content is not re-uploaded.

## Retention

No automated deletion. Snapshots accumulate under `snapshots/<date>/`.
Deduplication via content-addressed paths keeps storage proportional
to unique content, not fetch count.
