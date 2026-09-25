"use strict";
/* POST /api/report — regulated write path for historical Flock contract reports.
 *
 * QUARANTINE MODEL: submissions land in reports-pending/, never directly in
 * the public archive. A reviewer promotes them with POST /api/promote after
 * human review. GET /api/history only ever lists the approved reports/ tree.
 *
 * Design constraints (per operator policy):
 *  - TEXT ONLY: accepts application/json bodies only, max 32 KB; the stored
 *    blob is canonical JSON re-serialized server-side (no raw passthrough).
 *  - REGULATED ENTRY: strict schema validation; agency_id must be a known
 *    tracker record (list injected at deploy time); source_url and
 *    downloaded_at are mandatory on every report.
 *  - AUTHENTICATED: REPORT_WRITE_KEY is mandatory. Requests without a
 *    matching x-report-key are rejected (constant-time compare).
 *  - RATE LIMITED: 10 writes / IP / hour, 500 writes / day globally
 *    (in-memory per function instance: best-effort on serverless, documented
 *    in docs/BLOB_REPORTS.md).
 *  - APPEND-ONLY: pathnames embed the server receive timestamp; no update
 *    endpoint exists. Promotion copies to reports/ and deletes the pending
 *    blob; the approved copy is never mutated.
 *
 * Requires BLOB_READ_WRITE_TOKEN and REPORT_WRITE_KEY env (set in the Vercel
 * dashboard; the function never logs them).
 */

const BLOB_API = "https://vercel.com/api/blob";
const API_VERSION = "12"; // pinned to the @vercel/blob protocol version verified 2026-09-25
const MAX_BODY = 32 * 1024;
const STATUSES = new Set(["active", "pending", "cancelled", "rejected", "expired"]);
const TOP_KEYS = new Set(["agency_id", "source_url", "downloaded_at", "report"]);
const REPORT_KEYS = new Set(["status", "cameras", "annual_cost_usd", "renewal_date", "notes"]);

/* Valid agency ids, injected at deploy time from data/agencies.json. */
const AGENCY_IDS = new Set(/*__AGENCY_IDS__*/[]);

// ---- rate limiting (per-instance, best effort on serverless) ----
const ipBuckets = new Map();
let globalDay = "";
let globalCount = 0;

function rateLimited(ip) {
  const now = Date.now();
  let b = ipBuckets.get(ip);
  if (!b || now > b.reset) {
    b = { count: 0, reset: now + 3600 * 1000 };
    ipBuckets.set(ip, b);
  }
  b.count += 1;
  const day = new Date().toISOString().slice(0, 10);
  if (day !== globalDay) {
    globalDay = day;
    globalCount = 0;
  }
  globalCount += 1;
  return b.count > 10 || globalCount > 500;
}

// ---- helpers ----
function send(res, code, obj) {
  res.statusCode = code;
  res.setHeader("Content-Type", "application/json");
  res.setHeader("Cache-Control", "no-store");
  res.end(JSON.stringify(obj));
}

function clientIp(req) {
  const fwd = req.headers["x-forwarded-for"];
  if (typeof fwd === "string" && fwd.length) return fwd.split(",")[0].trim().slice(0, 64);
  return (req.socket && req.socket.remoteAddress) || "unknown";
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
        reject(Object.assign(new Error("body too large"), { code: 413 }));
        req.destroy();
        return;
      }
      chunks.push(c);
    });
    req.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    req.on("error", reject);
  });
}

function isValidHttpUrl(s) {
  if (typeof s !== "string" || s.length === 0 || s.length > 500) return false;
  try {
    const u = new URL(s);
    return u.protocol === "http:" || u.protocol === "https:";
  } catch {
    return false;
  }
}

function isValidPastDate(s) {
  if (typeof s !== "string" || !/^\d{4}-\d{2}-\d{2}/.test(s)) return false;
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) return false;
  return d.getTime() <= Date.now() + 24 * 3600 * 1000;
}

function validate(body) {
  const errors = [];
  if (body === null || typeof body !== "object" || Array.isArray(body)) {
    return ["body must be a JSON object"];
  }
  for (const k of Object.keys(body)) {
    if (!TOP_KEYS.has(k)) errors.push(`unexpected field: ${k}`);
  }
  if (typeof body.agency_id !== "string" || !AGENCY_IDS.has(body.agency_id)) {
    errors.push("agency_id must be a known tracker record id");
  }
  if (!isValidHttpUrl(body.source_url)) {
    errors.push("source_url must be an http(s) URL under 500 chars");
  }
  if (!isValidPastDate(body.downloaded_at)) {
    errors.push("downloaded_at must be an ISO date not in the future");
  }
  const r = body.report;
  if (r === null || typeof r !== "object" || Array.isArray(r)) {
    errors.push("report must be an object");
  } else {
    for (const k of Object.keys(r)) {
      if (!REPORT_KEYS.has(k)) errors.push(`unexpected report field: ${k}`);
    }
    if (r.status !== undefined && !STATUSES.has(r.status)) errors.push("report.status invalid");
    if (r.cameras !== undefined && (!Number.isInteger(r.cameras) || r.cameras < 0)) {
      errors.push("report.cameras must be a non-negative integer");
    }
    if (r.annual_cost_usd !== undefined && (typeof r.annual_cost_usd !== "number" || r.annual_cost_usd < 0)) {
      errors.push("report.annual_cost_usd must be a non-negative number");
    }
    if (r.renewal_date !== undefined && !/^\d{4}-\d{2}-\d{2}$/.test(r.renewal_date)) {
      errors.push("report.renewal_date must be YYYY-MM-DD");
    }
    if (r.notes !== undefined && (typeof r.notes !== "string" || r.notes.length > 2000)) {
      errors.push("report.notes must be a string under 2000 chars");
    }
  }
  return errors;
}

async function blobPut(pathname, jsonText, token) {
  const url = `${BLOB_API}/?pathname=${encodeURIComponent(pathname)}`;
  const res = await fetch(url, {
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
  if (!res.ok) {
    const detail = (await res.text()).slice(0, 300);
    throw new Error(`blob store rejected upload: HTTP ${res.status} ${detail}`);
  }
  return res.json();
}

module.exports = async (req, res) => {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return send(res, 405, { error: "method not allowed" });
  }
  const token = process.env.BLOB_READ_WRITE_TOKEN;
  if (!token) return send(res, 503, { error: "history store not configured" });

  const writeKey = process.env.REPORT_WRITE_KEY;
  if (!writeKey) return send(res, 503, { error: "report submission not configured" });
  if (!timingSafeEqual(req.headers["x-report-key"], writeKey)) {
    return send(res, 401, { error: "missing or invalid write key" });
  }

  const ct = req.headers["content-type"] || "";
  if (!ct.includes("application/json")) {
    return send(res, 415, { error: "content-type must be application/json" });
  }

  if (rateLimited(clientIp(req))) {
    res.setHeader("Retry-After", "3600");
    return send(res, 429, { error: "rate limit exceeded" });
  }

  let raw;
  try {
    raw = await readBody(req);
  } catch (e) {
    return send(res, e.code === 413 ? 413 : 400, { error: e.code === 413 ? "body exceeds 32 KB" : "unreadable body" });
  }
  let body;
  try {
    body = JSON.parse(raw);
  } catch {
    return send(res, 400, { error: "malformed JSON" });
  }

  const errors = validate(body);
  if (errors.length) return send(res, 400, { error: "validation failed", details: errors });

  const receivedAt = new Date().toISOString();
  const stamp = receivedAt.replace(/[^0-9A-Za-z]/g, "-");
  const rand = Math.random().toString(36).slice(2, 8);
  const pathname = `reports-pending/${body.agency_id}/${stamp}-${rand}.json`;

  // Canonical record: re-serialized server-side; tied to source + download time.
  // status "pending": invisible to GET /api/history until promoted.
  const record = {
    status: "pending",
    agency_id: body.agency_id,
    source_url: body.source_url,
    downloaded_at: body.downloaded_at,
    received_at: receivedAt,
    report: body.report,
  };

  try {
    const stored = await blobPut(pathname, JSON.stringify(record), token);
    return send(res, 201, {
      ok: true,
      status: "pending_review",
      pathname: stored.pathname || pathname,
      url: stored.url,
      received_at: receivedAt,
    });
  } catch (e) {
    return send(res, 502, { error: "could not write to history store" });
  }
};
