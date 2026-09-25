# Historical reports (Vercel Blob)

Append-only archive of historical Flock contract reports. Each report is a
small JSON text blob tied to its **source** and the **date the source was
downloaded**. The curated dataset in `data/agencies.json` remains the source
of truth; this store is the audit trail underneath it.

## Setup

The site expects one env var on the Vercel project (Dashboard → Project →
Settings → Environment Variables, all environments):

- `BLOB_READ_WRITE_TOKEN` — read/write token for the Blob store. Without it,
  both endpoints answer `503 history store not configured` and the drawer
  history section shows "unavailable".

Optional hardening:

- `REPORT_WRITE_KEY` — if set, `POST /api/report` requires the same value in
  the `x-report-key` header (compared in constant time). Recommended once more
  than one person submits reports.

The serverless functions call the Blob control plane directly
(`PUT https://vercel.com/api/blob/?pathname=…`,
`GET https://vercel.com/api/blob/?prefix=…`) using the protocol pinned from
`@vercel/blob` (api-version 12, verified 2026-09-25). No SDK is bundled.

## Write path: POST /api/report

Text only. Rejects anything that is not `application/json`, anything over
32 KB, and anything that fails schema validation. The stored blob is
re-serialized server-side from the validated fields; there is no raw
passthrough.

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

Rules:

- `agency_id` must be a known tracker record id (the valid list is injected
  into the function at deploy time from `data/agencies.json`).
- `source_url` must be http(s), ≤ 500 chars.
- `downloaded_at` must be an ISO date not in the future: when the source was
  fetched.
- `report` fields are all optional but strictly typed; unknown fields are
  rejected at every level.
- Blob path: `reports/<agency_id>/<received_at>-<rand>.json`. Immutable:
  there is no update or delete endpoint.

Rate limits: 10 writes per IP per hour, 500 per day globally. These are
enforced with in-memory buckets per function instance, which is best-effort
on serverless (instances do not share state). Treat it as a spam-speed-bump,
not a security boundary; set `REPORT_WRITE_KEY` for a real gate.

Success: `201 { ok, pathname, url, received_at }`.

## Read path: GET /api/history

`GET /api/history?agency_id=<id>&limit=<1..200>&cursor=<opaque>`

Returns metadata only:

```json
{
  "agency_id": "staunton-va-police",
  "reports": [{ "pathname": "…", "url": "…", "size": 412, "uploadedAt": "…" }],
  "cursor": null,
  "hasMore": false
}
```

Report payloads are public JSON at their blob URLs. The tracker drawer shows
the 20 most recent per agency.

## Costs and limits

Blob storage and bandwidth bill to the Vercel project. Reports are capped at
32 KB each and rate-limited; expected volume is a handful per week. If the
store ever needs pruning, do it from the Vercel dashboard (there is
deliberately no API delete).
