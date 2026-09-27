"use strict";
/* Shared error codes for Flock-Off API endpoints.
 *
 * Every error response includes:
 *   - code: stable machine-readable identifier (search docs/ERROR_CODES.md)
 *   - error: human-readable summary
 *   - action: what the maintainer should do to resolve it
 *
 * Format: {ENDPOINT}_{HTTP_STATUS}_{SEQ}
 */

function err(code, error, action) {
  return { code, error, action, ts: new Date().toISOString() };
}

const CODES = {
  // promote.js
  PROMOTE_405_001: () => err("PROMOTE_405_001", "method not allowed",
    "Use POST with a JSON body: {url, action}."),
  PROMOTE_503_001: () => err("PROMOTE_503_001", "promotion not configured",
    "Set REPORT_ADMIN_KEY and BLOB_READ_WRITE_TOKEN in Vercel Production env, then redeploy."),
  PROMOTE_401_001: () => err("PROMOTE_401_001", "missing or invalid admin key",
    "Send the correct REPORT_ADMIN_KEY in the x-admin-key header. If the key was rotated, update the caller."),
  PROMOTE_415_001: () => err("PROMOTE_415_001", "content-type must be application/json",
    "Set Content-Type: application/json on the request."),
  PROMOTE_400_001: () => err("PROMOTE_400_001", "unreadable body",
    "The request body could not be read. Retry with a valid JSON payload."),
  PROMOTE_400_002: () => err("PROMOTE_400_002", "malformed JSON",
    "The body is not valid JSON. Validate the payload before sending."),
  PROMOTE_400_003: () => err("PROMOTE_400_003", "url must be a reports-pending/ blob URL",
    "The url field must point to a blob in the reports-pending/ prefix. Check the pending queue for the correct URL."),
  PROMOTE_400_004: () => err("PROMOTE_400_004", "could not fetch pending blob",
    "The blob store did not return the pending report. Verify BLOB_READ_WRITE_TOKEN is valid and the blob exists."),
  PROMOTE_400_005: () => err("PROMOTE_400_005", "pending blob is not valid JSON",
    "The pending blob is corrupt. Delete it manually from the blob store and ask the submitter to resubmit."),
  PROMOTE_400_006: () => err("PROMOTE_400_006", "blob is not a pending report",
    "The blob lacks the pending-report marker. It may have been already processed; check the reports/ archive."),
  PROMOTE_400_007: () => err("PROMOTE_400_007", 'action must be "approve" or "reject"',
    "Send exactly \"approve\" or \"reject\". There is no default; a typo is a 400 with no state change."),

  // report.js
  REPORT_405_001: () => err("REPORT_405_001", "method not allowed",
    "Use POST with a JSON body."),
  REPORT_503_001: () => err("REPORT_503_001", "report intake not configured",
    "Set REPORT_WRITE_KEY and BLOB_READ_WRITE_TOKEN in Vercel Production env, then redeploy."),
  REPORT_401_001: () => err("REPORT_401_001", "missing or invalid write key",
    "Send the correct REPORT_WRITE_KEY in the x-report-key header."),
  REPORT_429_001: () => err("REPORT_429_001", "rate limit exceeded for subnet bucket",
    "Wait one hour and retry. If legitimate traffic is hitting this, the limits are 10/hour per /24 subnet."),
  REPORT_429_002: () => err("REPORT_429_002", "global daily write limit reached",
    "The site-wide 500/day cap is hit. Wait until UTC midnight. If this recurs, investigate abuse."),
  REPORT_415_001: () => err("REPORT_415_001", "content-type must be application/json",
    "Set Content-Type: application/json on the request."),
  REPORT_400_001: () => err("REPORT_400_001", "unreadable body",
    "The request body could not be read. Retry with a valid JSON payload."),
  REPORT_413_001: () => err("REPORT_413_001", "body exceeds 32 KB",
    "Report submissions are capped at 32 KB. Trim the report text and retry."),
  REPORT_400_002: () => err("REPORT_400_002", "malformed JSON",
    "The body is not valid JSON. Validate the payload before sending."),
  REPORT_400_003: (details) => ({ ...err("REPORT_400_003", "validation failed",
    "Fix the listed field errors and resubmit."), details }),
  REPORT_502_001: () => err("REPORT_502_001", "could not write to history store",
    "The blob store write failed. Verify BLOB_READ_WRITE_TOKEN and check Vercel Blob status."),

  // pending.js
  PENDING_405_001: () => err("PENDING_405_001", "method not allowed",
    "Use GET with the x-admin-key header."),
  PENDING_503_001: () => err("PENDING_503_001", "review queue not configured",
    "Set REPORT_ADMIN_KEY and BLOB_READ_WRITE_TOKEN in Vercel Production env, then redeploy."),
  PENDING_401_001: () => err("PENDING_401_001", "missing or invalid admin key",
    "Send the correct REPORT_ADMIN_KEY in the x-admin-key header."),
  PENDING_502_001: () => err("PENDING_502_001", "could not list pending reports",
    "The blob store list operation failed. Verify BLOB_READ_WRITE_TOKEN and check Vercel Blob status."),

  // history.js
  HISTORY_405_001: () => err("HISTORY_405_001", "method not allowed",
    "Use GET."),
  HISTORY_503_001: () => err("HISTORY_503_001", "history store not configured",
    "Set BLOB_READ_WRITE_TOKEN in Vercel Production env, then redeploy."),
  HISTORY_400_001: () => err("HISTORY_400_001", "agency_id is required (a-z, 0-9, dashes)",
    "Provide a valid agency_id query parameter matching the dataset ID format."),
  HISTORY_502_001: () => err("HISTORY_502_001", "could not read history store",
    "The blob store read failed. Verify BLOB_READ_WRITE_TOKEN and check Vercel Blob status."),
};

module.exports = { CODES };
