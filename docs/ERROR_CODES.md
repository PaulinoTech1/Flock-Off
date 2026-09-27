# Flock-Off Error Codes

Every API error response includes a `code`, `error`, `action`, and `ts` (timestamp).
Search this file by code to find the cause and fix.

Format: `{ENDPOINT}_{HTTP_STATUS}_{SEQ}`

## POST /api/promote

| Code | HTTP | Meaning | Action |
|------|------|---------|--------|
| PROMOTE_405_001 | 405 | Wrong method | Use POST with JSON body `{url, action}` |
| PROMOTE_503_001 | 503 | Missing env config | Set REPORT_ADMIN_KEY and BLOB_READ_WRITE_TOKEN in Vercel Production, redeploy |
| PROMOTE_401_001 | 401 | Bad admin key | Check x-admin-key header matches REPORT_ADMIN_KEY |
| PROMOTE_415_001 | 415 | Wrong content type | Set Content-Type: application/json |
| PROMOTE_400_001 | 400 | Unreadable body | Retry with valid JSON payload |
| PROMOTE_400_002 | 400 | Malformed JSON | Validate payload before sending |
| PROMOTE_400_003 | 400 | Bad blob URL | URL must be in reports-pending/ prefix |
| PROMOTE_400_004 | 400 | Blob fetch failed | Check BLOB_READ_WRITE_TOKEN and blob exists |
| PROMOTE_400_005 | 400 | Blob not JSON | Blob corrupt; delete manually, ask for resubmit |
| PROMOTE_400_006 | 400 | Not a pending report | May be already processed; check reports/ archive |
| PROMOTE_400_007 | 400 | Bad action value | Send exactly "approve" or "reject" |

## POST /api/report

| Code | HTTP | Meaning | Action |
|------|------|---------|--------|
| REPORT_405_001 | 405 | Wrong method | Use POST with JSON body |
| REPORT_503_001 | 503 | Missing env config | Set REPORT_WRITE_KEY and BLOB_READ_WRITE_TOKEN in Vercel Production, redeploy |
| REPORT_401_001 | 401 | Bad write key | Check x-report-key header matches REPORT_WRITE_KEY |
| REPORT_415_001 | 415 | Wrong content type | Set Content-Type: application/json |
| REPORT_429_001 | 429 | Subnet rate limited | Wait 1 hour; limit is 10/hour per /24 subnet |
| REPORT_429_002 | 429 | Daily cap hit | Wait until UTC midnight; investigate if recurring |
| REPORT_400_001 | 400 | Unreadable body | Retry with valid JSON payload |
| REPORT_413_001 | 413 | Body too large | Trim report to under 32 KB |
| REPORT_400_002 | 400 | Malformed JSON | Validate payload before sending |
| REPORT_400_003 | 400 | Validation failed | Fix listed field errors, resubmit |
| REPORT_502_001 | 502 | Blob write failed | Check BLOB_READ_WRITE_TOKEN and Vercel Blob status |
| REPORT_409_001 | 409 | Duplicate report | Identical report already in pending queue; no action needed |
| REPORT_500_001 | 500 | Content hashing failed | Retry the submission |

## GET /api/pending

| Code | HTTP | Meaning | Action |
|------|------|---------|--------|
| PENDING_405_001 | 405 | Wrong method | Use GET with x-admin-key header |
| PENDING_503_001 | 503 | Missing env config | Set REPORT_ADMIN_KEY and BLOB_READ_WRITE_TOKEN in Vercel Production, redeploy |
| PENDING_401_001 | 401 | Bad admin key | Check x-admin-key header |
| PENDING_502_001 | 502 | Blob list failed | Check BLOB_READ_WRITE_TOKEN and Vercel Blob status |

## GET /api/history

| Code | HTTP | Meaning | Action |
|------|------|---------|--------|
| HISTORY_405_001 | 405 | Wrong method | Use GET |
| HISTORY_503_001 | 503 | Missing env config | Set BLOB_READ_WRITE_TOKEN in Vercel Production, redeploy |
| HISTORY_400_001 | 400 | Bad agency_id | Use format: lowercase, numbers, dashes, max 80 chars |
| HISTORY_502_001 | 502 | Blob read failed | Check BLOB_READ_WRITE_TOKEN and Vercel Blob status |

## Client-side error codes

Client errors are logged to the browser console with codes:

| Code | Where | Meaning |
|------|-------|---------|
| CLIENT_TRACKER_001 | tracker.js | Contract data failed to load |
| CLIENT_SOURCES_001 | sources.js | Source index failed to load |
| CLIENT_INTEGRITY_001 | app.js | Manifest verification failed |
| CLIENT_UNHANDLED_001 | app.js | Unhandled JS error |
| CLIENT_UNHANDLED_002 | app.js | Unhandled promise rejection |
