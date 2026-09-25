# Historical reports (Vercel Blob) — quarantine model

Text-only, heavily regulated archive of historical Flock contract reports,
stored as canonical JSON blobs. **Nothing untrusted reaches the public
archive directly**: submissions land in a quarantine prefix and are published
only after human review.

## Flow

```
submitter ──POST /api/report (REPORT_WRITE_KEY)──> reports-pending/<agency>/<stamp>-<rand>.json
reviewer  ──GET  /api/pending (REPORT_ADMIN_KEY)──> queue of submissions with full records
reviewer  ──POST /api/promote (REPORT_ADMIN_KEY)──> reports/<agency>/<file>.json  (status: approved)
                                                         + pending blob deleted
public    ──GET  /api/history ──> lists reports/ only (approved records)
```

- `REPORT_WRITE_KEY` gates **submission**. Share only with trusted submitters.
- `REPORT_ADMIN_KEY` gates **review and promotion**. Keep it to yourself; it
  must differ from the write key so submitters cannot approve their own reports.
- Both keys are mandatory. If either is unset, its endpoint fails closed
  (503/401).

## POST /api/report

- `Content-Type: application/json` only; max body 32 KB.
- Rate limit: 10 writes / IP / hour, 500 writes / day globally (in-memory per
  function instance: best-effort on serverless, a spam speed bump, not a
  guarantee).
- Strict schema validation: allowlisted fields, correct types, `agency_id`
  must be a known tracker record (list injected at deploy time).
- `source_url` (http/https) and `downloaded_at` (ISO date, not in the future)
  are mandatory.
- The stored blob is re-serialized server-side from validated fields only
  (`status`, `agency_id`, `source_url`, `downloaded_at`, `received_at`,
  `report`). No raw request bytes are ever persisted.
- Response: `201 { ok, status: "pending_review", pathname, url, received_at }`.

Required JSON body:

```json
{
  "agency_id": "staunton-va-police",
  "source_url": "https://example.gov/council-minutes-2024-05.pdf",
  "downloaded_at": "2026-09-20",
  "report": {
    "status": "active",
    "cameras": 12,
    "annual_cost_usd": 30000,
    "renewal_date": "2027-05-01",
    "notes": "Council approved renewal, 5-2 vote."
  }
}
```

## GET /api/pending

Admin-key protected reviewer queue. Returns up to 50 pending submissions with
their full records (`pathname`, `url`, `size`, `uploadedAt`, `record`).

## POST /api/promote

Admin-key protected. Body: `{ "url": "<pending blob public URL>" }`.

1. Validates the URL is an https `reports-pending/` blob on
   `*.blob.vercel-storage.com` (rejects anything else: this is the anti-SSRF
   boundary).
2. Fetches the blob and confirms `status === "pending"` with the required
   report fields.
3. Writes an approved copy to `reports/<agency>/<same filename>` with
   `status: "approved"`, `approved_at`, `approved_by`.
4. Deletes the pending blob.

If step 4 fails after step 3 succeeded, the endpoint returns 200 with a
`warning`: the public archive is correct; delete the orphaned pending blob
from the Vercel dashboard.

## GET /api/history

Unchanged public read path: lists `reports/` metadata (up to 20, newest
first). The drawer renders these; it never sees the quarantine prefix.

## Environment (Vercel dashboard, Production)

| Variable              | Purpose                                  |
|-----------------------|------------------------------------------|
| `BLOB_READ_WRITE_TOKEN` | Blob store access (read/write/delete)  |
| `REPORT_WRITE_KEY`    | Shared submitter secret                  |
| `REPORT_ADMIN_KEY`    | Reviewer secret (promotion + queue)       |

## Invariants

- Append-only archive: no update endpoint; approved copies are never mutated.
- Text only: JSON in, canonical JSON out.
- Untrusted input never lands in `reports/` except via `POST /api/promote`
  with the admin key.
- Blobs are public JSON by store design; do not submit non-public material.
