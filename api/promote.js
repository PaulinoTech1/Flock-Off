"use strict";
/* POST /api/promote — human-review gate for the quarantine model.
 *
 * Takes a pending report's public blob URL, verifies it is genuinely a
 * pending submission, copies it into the public reports/ tree stamped as
 * approved, then deletes the pending blob. The approved copy is never
 * mutated afterwards (append-only archive).
 *
 * Auth: REPORT_ADMIN_KEY is mandatory (constant-time compare against the
 * x-admin-key header). This key must differ from REPORT_WRITE_KEY: submitters
 * must not be able to approve their own reports.
 *
 * Body: { "url": "<pending blob url>", "action": "approve" | "reject" }
 *   "approve": copy into the public reports/ tree stamped as approved,
 *     then delete the pending blob.
 *   "reject": delete the pending blob without approving it and record a
 *     rejection against the submitter's bucket.
 *
 * The action is mandatory and exact: a missing, misspelled, or wrongly
 * typed value is a 400 with no state change. There is deliberately no
 * default path, so a malformed review request can never fall through to
 * approval.
 *
 * Reputation: approve/reject decisions increment per-bucket counters in the
 * blob store (signals-rep/<day>/<bucket>.json), keyed by the same
 * daily-rotated subnet pseudonym the intake uses. Buckets with a poor
 * decision history only get flagged for closer human review on future tips;
 * nothing is auto-rejected. See api/_signals.js for the privacy model.
 *
 * Failure semantics: if the approved copy is written but the pending delete
 * fails, the endpoint still returns 200 with a warning — the public archive
 * is correct; the orphaned pending blob is untidy, not wrong.
 */

const signals = require("./_signals");

const BLOB_API = "https://vercel.com/api/blob";
const API_VERSION = "12"; // pinned to the @vercel/blob protocol version verified 2026-09-25
const MAX_BODY = 32 * 1024;
const PENDING_RE = /^\/reports-pending\/[a-z0-9-]{1,80}\/[0-9A-Za-z._-]{1,120}\.json$/;

function send(res, code, obj) {
  res.statusCode = code;
  res.setHeader("Content-Type", "application/json");
  res.setHeader("Cache-Control", "no-store");
  res.end(JSON.stringify(obj));
}

function timingSafeEqual(a, b) {
  if (typeof a !== "string" || typeof b !== "string") return false;
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let bytes = 0;
    const chunks = [];
    req.on("data", (c) => {
      bytes += c.length;
      if (bytes > MAX_BODY) {
        reject(new Error("too large"));
        req.destroy();
        return;
      }
      chunks.push(c);
    });
    req.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    req.on("error", reject);
  });
}

function validPendingUrl(s) {
  if (typeof s !== "string" || s.length > 500) return null;
  let u;
  try {
    u = new URL(s);
  } catch {
    return null;
  }
  if (u.protocol !== "https:") return null;
  if (!u.hostname.endsWith(".blob.vercel-storage.com")) return null;
  if (!PENDING_RE.test(u.pathname)) return null;
  return u;
}

async function blobPut(pathname, jsonText, token) {
  const res = await fetch(`${BLOB_API}/?pathname=${encodeURIComponent(pathname)}`, {
    method: "PUT",
    headers: {
      authorization: `Bearer ${token}`,
      "x-api-version": API_VERSION,
      "x-vercel-blob-access": "public",
      "x-content-type": "application/json",
      "x-add-random-suffix": "0",
    },
    body: jsonText,
  });
  if (!res.ok) throw new Error(`blob put failed: HTTP ${res.status}`);
  return res.json();
}

async function blobDelete(url, token) {
  const res = await fetch(`${BLOB_API}/delete`, {
    method: "POST",
    headers: {
      authorization: `Bearer ${token}`,
      "x-api-version": API_VERSION,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ urls: [url] }),
  });
  if (!res.ok) throw new Error(`blob delete failed: HTTP ${res.status}`);
}

// Best-effort reputation update from a pending blob's _signals block.
// Never throws: reputation is advisory and must not break review actions.
async function repUpdateFromPending(pending, field, token) {
  try {
    const sig = pending && pending._signals;
    if (!sig || typeof sig.bucket !== "string" || typeof sig.day !== "string") return;
    if (!/^[0-9a-f]{64}$/.test(sig.bucket) || !/^\d{4}-\d{2}-\d{2}$/.test(sig.day)) return;
    const prefix = signals.repPath(sig.day, sig.bucket);
    let cur = {};
    try {
      const list = await fetch(
        `${BLOB_API}/?prefix=${encodeURIComponent(prefix)}&limit=5`,
        { headers: { authorization: `Bearer ${token}`, "x-api-version": API_VERSION } }
      );
      if (list.ok) {
        const data = await list.json();
        const hit = (data.blobs || []).find((b) => b.pathname === prefix);
        if (hit && hit.url) {
          const r = await fetch(hit.url);
          if (r.ok) cur = await r.json();
        }
      }
    } catch { /* missing counter starts at zero */ }
    const next = {
      day: sig.day,
      bucket: sig.bucket,
      submitted: cur.submitted | 0,
      approved: (cur.approved | 0) + (field === "approved" ? 1 : 0),
      rejected: (cur.rejected | 0) + (field === "rejected" ? 1 : 0),
    };
    await blobPut(prefix, JSON.stringify(next), token);
  } catch { /* advisory only */ }
}

module.exports = async (req, res) => {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return send(res, 405, { error: "method not allowed" });
  }
  const token = process.env.BLOB_READ_WRITE_TOKEN;
  const adminKey = process.env.REPORT_ADMIN_KEY;
  if (!token || !adminKey) return send(res, 503, { error: "promotion not configured" });
  if (!timingSafeEqual(req.headers["x-admin-key"], adminKey)) {
    return send(res, 401, { error: "missing or invalid admin key" });
  }
  const ct = req.headers["content-type"] || "";
  if (!ct.includes("application/json")) {
    return send(res, 415, { error: "content-type must be application/json" });
  }

  let raw;
  try {
    raw = await readBody(req);
  } catch {
    return send(res, 400, { error: "unreadable body" });
  }
  let body;
  try {
    body = JSON.parse(raw);
  } catch {
    return send(res, 400, { error: "malformed JSON" });
  }
  const u = validPendingUrl(body && body.url);
  if (!u) return send(res, 400, { error: "url must be a reports-pending/ blob URL" });

  // Fetch the pending submission and confirm it is what it claims to be.
  let pending;
  try {
    const r = await fetch(u.toString());
    if (!r.ok) return send(res, 400, { error: "could not fetch pending blob" });
    pending = await r.json();
  } catch {
    return send(res, 400, { error: "pending blob is not valid JSON" });
  }
  if (!pending || pending.status !== "pending" ||
      typeof pending.agency_id !== "string" ||
      typeof pending.source_url !== "string" ||
      typeof pending.downloaded_at !== "string") {
    return send(res, 400, { error: "blob is not a pending report" });
  }

  // Explicit action, fail closed: there is no default path. A missing,
  // misspelled, or wrongly typed action is a 400 with no state change, so
  // a malformed review request can never fall through to approval.
  const action = body && body.action;
  if (action !== "approve" && action !== "reject") {
    return send(res, 400, { error: 'action must be "approve" or "reject"' });
  }

  // Rejection path: delete the pending blob, record the decision against the
  // submitter's bucket, return. The report never enters the public archive.
  if (action === "reject") {
    await repUpdateFromPending(pending, "rejected", token);
    try {
      await blobDelete(u.toString(), token);
    } catch {
      return send(res, 502, { error: "could not delete pending blob" });
    }
    return send(res, 200, { ok: true, action: "rejected" });
  }

  const filename = u.pathname.split("/").pop();
  const approvedPath = `reports/${pending.agency_id}/${filename}`;
  const approvedAt = new Date().toISOString();
  const approved = {
    status: "approved",
    agency_id: pending.agency_id,
    source_url: pending.source_url,
    downloaded_at: pending.downloaded_at,
    received_at: pending.received_at,
    approved_at: approvedAt,
    approved_by: "admin",
    report: pending.report,
  };

  let stored;
  try {
    stored = await blobPut(approvedPath, JSON.stringify(approved), token);
  } catch {
    return send(res, 502, { error: "could not write approved copy" });
  }

  try {
    await blobDelete(u.toString(), token);
  } catch {
    return send(res, 200, {
      ok: true,
      warning: "approved copy written but pending blob could not be deleted; remove it from the dashboard",
      approved_pathname: stored.pathname || approvedPath,
      approved_url: stored.url,
      approved_at: approvedAt,
    });
  }

  await repUpdateFromPending(pending, "approved", token);

  return send(res, 200, {
    ok: true,
    action: "approved",
    approved_pathname: stored.pathname || approvedPath,
    approved_url: stored.url,
    approved_at: approvedAt,
  });
};
