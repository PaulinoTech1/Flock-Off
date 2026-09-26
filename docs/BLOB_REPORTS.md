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
- Rate limit: 10 writes / subnet-bucket / hour, 500 writes / day globally
  (in-memory per function instance: best-effort on serverless, a spam speed
  bump, not a guarantee). Buckets are keyed by a daily-rotated salted hash of
  the submitter's /24 (IPv4) or /48 (IPv6) subnet; raw IPs are never stored
  anywhere (see "Submission signals" below).
- Strict schema validation: allowlisted fields, correct types, `agency_id`
  must be a known tracker record (list injected at deploy time).
- `source_url` (http/https) and `downloaded_at` (ISO date, not in the future)
  are mandatory.
- The stored blob is re-serialized server-side from validated fields only
  (`status`, `agency_id`, `source_url`, `downloaded_at`, `received_at`,
  `report`, plus the internal `_signals` block). No raw request bytes are
  ever persisted.
- Response: `201 { ok, status: "pending_review", pathname, url, received_at }`.

## Submission signals (privacy-preserving rate/reputation)

`api/_signals.js` implements two signals used by the tip pipeline. Both are
keyed by `SHA-256("flockoff-tip-v1" | UTC-day | subnet)` where subnet is the
/24 (IPv4) or /48 (IPv6) prefix. The day component rotates the key daily, so
buckets cannot be joined across days.

What is stored:
- Rate-limit counters: in-memory only, per function instance, dropped on day
  rollover.
- Reputation counters: `signals-rep/<day>/<bucket>.json` in the blob store,
  holding `{ submitted, approved, rejected }` counts. Incremented at intake
  (`submitted`) and at review decision (`approved` / `rejected`).

What is NOT stored: raw IP addresses, anywhere, ever. Not in memory, not in
the blob store, not in logs.

Reviewer aid, not automation: when a bucket has >= 3 rejections and a >= 60%
rejection rate among decided submissions (today + yesterday), the quarantined
tip gets `_signals.reputation_flag: true` so the human reviewer looks closer.
Flagged tips are still stored and still reviewed; nothing is auto-rejected.

Honest limitation: a /24 has only 2^24 values, so the bucket hash is
brute-forceable by anyone holding the blob read token. This is
pseudonymization with daily rotation, not anonymization. What it guarantees:
no IP database accumulates, and a compromised day-bucket cannot be linked to
any other day's traffic.

POST /api/promote takes `{ "url": ..., "action": "approve" }` or
`{ "url": ..., "action": "reject" }` (admin key required). `"reject"` deletes
the pending blob without approving it and records the rejection against the
submitter's bucket. The action is mandatory and exact: a missing, misspelled,
or wrongly typed value is a 400 with no state change, so a malformed review
request can never fall through to approval.

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

Admin-key protected. Body: `{ "url": "<pending blob public URL>", "action": "approve" | "reject" }`.

0. Validates `action` is exactly `"approve"` or `"reject"`; anything else is
   a 400 with no state change. There is no default path.
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
