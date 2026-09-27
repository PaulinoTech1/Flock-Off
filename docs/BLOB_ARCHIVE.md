# Source archive blob (Vercel Blob) — raw HTML snapshots

Forensic backup of the exact, undoctored HTML of every fetched source.
When drift is detected, the original page can be pulled up for comparison.

## Two-tier archive

| Tier | Location | Content | Purpose |
|------|----------|---------|---------|
| Primary | `data/source_archive/` (git) | Extracted text (`.txt`) | Fingerprint input, signed in release manifest |
| Forensic | Vercel Blob `snapshots/` (private) | Raw HTML | Exact original for drift review |

The git text archive is what fingerprints are computed from. The blob holds
the raw bytes the text was extracted from. Both are written on every
successful fetch.

## Blob layout

```
snapshots/<sha256-of-raw-html>.html
```

Content-addressed: identical HTML is stored once, never re-uploaded.
Blobs are private. Provenance (source URL, fetch date) is stored as blob
metadata headers.

## Wiring

- `scripts/blob_archive.py`: put/get/exists operations against the blob API.
  Uses `ARCHIVE_BLOB_READ_WRITE_TOKEN`. Fail-open with stderr warnings:
  a blob outage must never break the monitor.
- `scripts/source_fingerprints.py`: `fingerprint_url()` calls
  `blob_archive.put_snapshot()` after each successful fetch. The content
  hash is stored in the fingerprint record as `raw_snapshot_hash`.
- `python3 scripts/flockoff.py snapshot`: retrieval CLI for drift review.

## Retrieval

By source key (looks up `raw_snapshot_hash` in `data/source_fingerprints.json`):

```bash
python3 scripts/flockoff.py snapshot --key <source_key> -o original.html
```

By content hash directly:

```bash
python3 scripts/flockoff.py snapshot --hash <64-char-hex> -o original.html
```

Or pipe to stdout (omit `-o`).

## Setup

1. Create a blob store in the Vercel dashboard (this one is separate from
   the reports store).
2. Copy its Read-Write Token.
3. Set `ARCHIVE_BLOB_READ_WRITE_TOKEN` in the environment where the
   monitor/fingerprint scripts run. This is a local/CI variable, not a
   Vercel function env var: the archiving happens in the Python pipeline,
   not in serverless functions.
4. Without the token, snapshotting is skipped with a warning. Fingerprinting
   continues normally.

## Limits

- 10 MB cap per snapshot (larger pages are skipped with a warning).
- Deduplication is automatic via content hashing.
- The blob store is private. There is no public URL for any snapshot.
