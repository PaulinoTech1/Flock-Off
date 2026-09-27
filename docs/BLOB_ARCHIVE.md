# Source archive blob (Vercel Blob) — JSON snapshots

Forensic backup of fetched sources as structured JSON: extracted text
plus discoverability metadata plus cryptographic integrity validation.
When drift is detected, the original snapshot can be pulled up and
verified as unaltered since capture.

Text only. No images, no binary, no raw HTML.

## Two-tier archive

| Tier | Location | Content | Purpose |
|------|----------|---------|---------|
| Primary | `data/source_archive/` (git) | Extracted text (`.txt`) | Fingerprint input, signed in release manifest |
| Forensic | Vercel Blob `snapshots/` (private) | JSON snapshots | Verifiable originals for drift review |

## Snapshot schema (v1)

```json
{
  "schema_version": 1,
  "source_key": "<canonical source key>",
  "agency_id": "<agency slug or null>",
  "url": "<requested URL>",
  "final_url": "<URL after redirects>",
  "fetched_at": "<ISO 8601 UTC>",
  "accurate_to": "<YYYY-MM-DD the data represents>",
  "title": "<page title or null>",
  "text": "<extracted text>",
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
```

## Integrity model

`payload_hash` covers every field except the `integrity` block itself,
serialized as canonical JSON (sorted keys, compact separators). To verify:
re-serialize, re-hash, compare. A mismatch means the snapshot was altered
after capture.

This validates the **archive copy**, not the live source. Drift (the live
source changing after capture) is detected separately by the fingerprint
pipeline comparing `content_hash`/`simhash` against stored baselines.

Snapshots that fail their own verification are refused upload.

## Discoverability

Blob layout:

```
snapshots/<accurate_to YYYY-MM-DD>/<payload_hash>.json
```

- Date prefix: list all snapshots accurate to a given day.
- Content-addressed filename: identical content stored once, deduplicated.
- Blob metadata headers carry `source_key` and `accurate_to` for listing.
- The fingerprint record in `data/source_fingerprints.json` stores the
  blob pathname as `snapshot_path`, linking each source to its snapshot.

List snapshots for a date:

```bash
python3 scripts/blob_archive.py list --date 2026-09-27
```

## Wiring

- `scripts/blob_archive.py`: build/verify/put/get/list operations.
  Uses `ARCHIVE_BLOB_READ_WRITE_TOKEN`. Fail-open with stderr warnings:
  a blob outage never breaks the monitor.
- `scripts/source_fingerprints.py`: `fingerprint_url()` builds and uploads
  a JSON snapshot after each successful fetch. The blob pathname is stored
  as `snapshot_path` in the fingerprint record.
- `python3 scripts/flockoff.py snapshot`: retrieval CLI for drift review.

## Retrieval

By source key (looks up `snapshot_path` in fingerprints):

```bash
python3 scripts/flockoff.py snapshot --key <source_key> -o original.json
```

By blob pathname directly:

```bash
python3 scripts/flockoff.py snapshot \
  --path snapshots/2026-09-27/<hash>.json -o original.json
```

Downloads are integrity-verified before being returned. A failed check
raises instead of returning corrupt data.

Verify a local snapshot file:

```bash
python3 scripts/blob_archive.py verify original.json
```

## Setup

1. Create a blob store in the Vercel dashboard (separate from the reports
   store).
2. Copy its Read-Write Token.
3. Set `ARCHIVE_BLOB_READ_WRITE_TOKEN` in the environment where the
   monitor/fingerprint scripts run. This is a local/CI variable, not a
   Vercel function env var: archiving happens in the Python pipeline.
4. Without the token, snapshotting is skipped with a warning. Fingerprinting
   continues normally.

## Limits

- 500K character cap on extracted text per snapshot (larger pages are
  rejected at build time with `ValueError`, caught by the pipeline).
- 2 MB cap on snapshot download.
- Deduplication is automatic via content hashing.
- The blob store is private. There is no public URL for any snapshot.
