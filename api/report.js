"use strict";
const { CODES } = require("./_errors.js");
const { argon2, randomBytes, createHash, timingSafeEqual: nodeTimingSafeEqual } = require("crypto");
/* POST /api/report — regulated write path for historical Flock contract reports.
 *
 * QUARANTINE MODEL: submissions land in reports-pending/, never directly in
 * the public archive. A reviewer promotes them with POST /api/promote after
 * human review. GET /api/history only ever lists the approved reports/ tree.
 *
 * Design constraints (per operator policy):
 *  - TEXT ONLY: accepts application/json bodies only, max 32 KB; the stored
 *    blob is canonical JSON re-serialized server-side (no raw passthrough).
 *  - NO EXECUTABLE CODE: all string fields are scanned for script injection
 *    patterns (<script, javascript:, event handlers). Rejected if found.
 *  - REGULATED ENTRY: strict schema validation; agency_id must be a known
 *    tracker record (list injected at deploy time); source_url,
 *    downloaded_at, and description are mandatory on every report.
 *  - AUTHENTICATED: REPORT_WRITE_KEY is mandatory. Requests without a
 *    matching x-report-key are rejected (constant-time compare).
 *  - RATE LIMITED: 10 writes / subnet-bucket / hour, 500 writes / day globally
 *    (in-memory per function instance: best-effort on serverless, documented
 *    in docs/BLOB_REPORTS.md). Buckets are keyed by a daily-rotated salted
 *    hash of the /24 (or /48) subnet: raw IPs are never stored.
 *  - DEDUPLICATION: content is hashed with Argon2id (server pepper). Before
 *    storing, pending blobs are checked for matching content hash. Duplicates
 *    are rejected with 409.
 *  - REPUTATION SIGNAL: per-bucket submission outcomes are counted in the
 *    blob store under the same daily-rotated pseudonym. A bucket with a
 *    poor decision history only flags the quarantined tip for closer human
 *    review; nothing is auto-rejected. See api/_signals.js for the privacy
 *    model and its honest limitations.
 *  - APPEND-ONLY: pathnames embed the server receive timestamp; no update
 *    endpoint exists. Promotion copies to reports/ and deletes the pending
 *    blob; the approved copy is never mutated.
 *
 * Requires REPORTS_BLOB_READ_WRITE_TOKEN and REPORT_WRITE_KEY env (set in the Vercel
 * dashboard; the function never logs them).
 */

const signals = require("./_signals");

const BLOB_API = "https://vercel.com/api/blob";
const API_VERSION = "12"; // pinned to the @vercel/blob protocol version verified 2026-09-25
const MAX_BODY = 32 * 1024;
const STATUSES = new Set(["active", "pending", "cancelled", "rejected", "expired"]);
const TOP_KEYS = new Set(["agency_id", "source_url", "downloaded_at", "description", "report"]);
const REPORT_KEYS = new Set(["status", "cameras", "annual_cost_usd", "renewal_date", "notes"]);

// Patterns that indicate executable code. Rejected in all string fields.
const EXECUTABLE_PATTERNS = [
  /<script/i,
  /<\/script/i,
  /javascript:/i,
  /data:text\/html/i,
  /on\w+\s*=/i,  // event handlers: onclick=, onerror=, etc.
  /<iframe/i,
  /<object/i,
  /<embed/i,
  /eval\s*\(/i,
  /Function\s*\(/i,
];

/* Valid agency ids, injected at deploy time from data/agencies.json. */
const AGENCY_IDS = new Set(/*__AGENCY_IDS__*/[]);

// ---- rate limiting (per-instance, best effort on serverless) ----
// Buckets are keyed by signals.bucketHash(ip, day): a daily-rotated salted
// hash of the /24 (IPv4) or /48 (IPv6) subnet. Raw IPs never enter storage.
// The map is dropped on day rollover because yesterday's hashes are useless
// under today's salt (and must not be joinable across days).
const bucketState = new Map();
let bucketDay = "";
let globalDay = "";
let globalCount = 0;

function rateLimited(ip) {
  const now = Date.now();
  const day = signals.dayUTC();
  if (day !== bucketDay) {
    bucketDay = day;
    bucketState.clear();
  }
  const bucket = signals.bucketHash(ip, day);
  let b = bucketState.get(bucket);
  if (!b || now > b.reset) {
    b = { count: 0, reset: now + 3600 * 1000 };
    bucketState.set(bucket, b);
  }
  b.count += 1;
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

// Scan all string values recursively for executable code patterns.
// Returns array of violation descriptions, empty if clean.
function scanForExecutable(obj, path = "") {
  const violations = [];
  if (typeof obj === "string") {
    for (const pattern of EXECUTABLE_PATTERNS) {
      if (pattern.test(obj)) {
        violations.push(`${path}: contains executable code pattern`);
        break;
      }
    }
  } else if (Array.isArray(obj)) {
    obj.forEach((v, i) => violations.push(...scanForExecutable(v, `${path}[${i}]`)));
  } else if (obj !== null && typeof obj === "object") {
    for (const [k, v] of Object.entries(obj)) {
      violations.push(...scanForExecutable(v, path ? `${path}.${k}` : k));
    }
  }
  return violations;
}

// Hash content with Argon2id using server pepper. Returns hex string.
// Used for deduplication: same content + same pepper = same hash.
function hashContent(canonicalJson, pepper) {
  return new Promise((resolve, reject) => {
    const salt = createHash("sha256").update(pepper).digest(); // deterministic salt from pepper
    const params = {
      message: canonicalJson,
      nonce: salt,
      parallelism: 1,
      memory: 19456,  // 19 MiB
      passes: 2,
      tagLength: 32,
    };
    argon2("argon2id", params, (err, hash) => {
      if (err) reject(err);
      else resolve(hash.toString("hex"));
    });
  });
}

// Check if a report with this content hash already exists in pending.
// Returns true if duplicate found.
async function isDuplicate(contentHash, token) {
  try {
    const res = await fetch(
      `${BLOB_API}/?prefix=${encodeURIComponent("reports-pending/")}&limit=100`,
      { headers: { authorization: `Bearer ${token}`, "x-api-version": API_VERSION } }
    );
    if (!res.ok) return false; // fail-open: if we can't check, allow submission
    const data = await res.json();
    const blobs = data.blobs || [];
    // Fetch each pending blob and compare content hashes
    for (const blob of blobs.slice(0, 50)) { // limit to 50 for performance
      try {
        const r = await fetch(blob.url);
        if (!r.ok) continue;
        const existing = await r.json();
        if (existing.content_hash === contentHash) return true;
      } catch {
        continue;
      }
    }
    return false;
  } catch {
    return false; // fail-open
  }
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
  if (typeof body.description !== "string" || body.description.trim().length < 10) {
    errors.push("description is required (min 10 chars, describe what this report documents)");
  }
  if (typeof body.description === "string" && body.description.length > 2000) {
    errors.push("description must be under 2000 chars");
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

// Reputation counters live at signals-rep/<day>/<bucket>.json, keyed by the
// same daily-rotated pseudonym as rate limiting. All helpers are
// best-effort: a signal failure must never block or fail a submission.
async function repBlob(day, bucket, token) {
  try {
    const prefix = signals.repPath(day, bucket);
    const res = await fetch(
      `${BLOB_API}/?prefix=${encodeURIComponent(prefix)}&limit=5`,
      { headers: { authorization: `Bearer ${token}`, "x-api-version": API_VERSION } }
    );
    if (!res.ok) return null;
    const data = await res.json();
    const hit = (data.blobs || []).find((b) => b.pathname === prefix);
    if (!hit || !hit.url) return null;
    const r = await fetch(hit.url);
    if (!r.ok) return null;
    return await r.json();
  } catch {
    return null;
  }
}

async function repUpdate(day, bucket, field, token) {
  try {
    const cur = (await repBlob(day, bucket, token)) || {};
    const next = {
      day,
      bucket,
      submitted: (cur.submitted | 0) + (field === "submitted" ? 1 : 0),
      approved: (cur.approved | 0) + (field === "approved" ? 1 : 0),
      rejected: (cur.rejected | 0) + (field === "rejected" ? 1 : 0),
    };
    await blobPut(signals.repPath(day, bucket), JSON.stringify(next), token);
  } catch {
    /* reputation is advisory; never fail the main operation */
  }
}

// Sum this bucket's decisions over today + yesterday. Fail-open: on any
// error the submission proceeds unflagged.
async function reputationSummary(ip, token) {
  try {
    const today = signals.dayUTC();
    const yday = signals.yesterdayUTC();
    const [t, y] = await Promise.all([
      repBlob(today, signals.bucketHash(ip, today), token),
      repBlob(yday, signals.bucketHash(ip, yday), token),
    ]);
    return signals.summarize([t, y]);
  } catch {
    return { submitted: 0, approved: 0, rejected: 0 };
  }
}

module.exports = async (req, res) => {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return send(res, 405, CODES.REPORT_405_001());
  }
  const token = process.env.REPORTS_BLOB_READ_WRITE_TOKEN;
  if (!token) return send(res, 503, CODES.HISTORY_503_001());

  const writeKey = process.env.REPORT_WRITE_KEY;
  if (!writeKey) return send(res, 503, CODES.REPORT_503_001());
  if (!timingSafeEqual(req.headers["x-report-key"], writeKey)) {
    return send(res, 401, CODES.REPORT_401_001());
  }

  const ct = req.headers["content-type"] || "";
  if (!ct.includes("application/json")) {
    return send(res, 415, CODES.REPORT_415_001());
  }

  if (rateLimited(clientIp(req))) {
    res.setHeader("Retry-After", "3600");
    return send(res, 429, CODES.REPORT_429_001());
  }

  let raw;
  try {
    raw = await readBody(req);
  } catch (e) {
    return send(res, e.code === 413 ? 413 : 400,
      e.code === 413 ? CODES.REPORT_413_001() : CODES.REPORT_400_001());
  }
  let body;
  try {
    body = JSON.parse(raw);
  } catch {
    return send(res, 400, CODES.REPORT_400_002());
  }

  const errors = validate(body);
  if (errors.length) return send(res, 400, CODES.REPORT_400_003(errors));

  // Data sanitization: reject any executable code patterns in string fields
  const execViolations = scanForExecutable(body);
  if (execViolations.length) {
    return send(res, 400, CODES.REPORT_400_003(
      ["Executable code detected in submission: " + execViolations.slice(0, 3).join("; ")]
    ));
  }

  const receivedAt = new Date().toISOString();
  const stamp = receivedAt.replace(/[^0-9A-Za-z]/g, "-");
  const rand = Math.random().toString(36).slice(2, 8);
  const pathname = `reports-pending/${body.agency_id}/${stamp}-${rand}.json`;

  // Canonical record: re-serialized server-side; tied to source + download time.
  // Build canonical form first (for hashing), then compute Argon2id content hash.
  const canonicalBody = {
    agency_id: body.agency_id,
    source_url: body.source_url,
    downloaded_at: body.downloaded_at,
    description: body.description.trim(),
    report: body.report,
  };
  const canonicalJson = JSON.stringify(canonicalBody);

  // Deduplication: hash with Argon2id + server pepper, check pending blobs.
  // Uses REPORT_WRITE_KEY as pepper (already required, never logged).
  let contentHash;
  try {
    contentHash = await hashContent(canonicalJson, writeKey);
  } catch (e) {
    return send(res, 500, CODES.REPORT_500_001());
  }
  if (await isDuplicate(contentHash, token)) {
    return send(res, 409, CODES.REPORT_409_001());
  }

  // Canonical record: re-serialized server-side; tied to source + download time.
  // status "pending": invisible to GET /api/history until promoted.
  // _signals carries the privacy-preserving bucket pseudonym (never an IP)
  // so promotion-time decisions can update reputation; reputation_flag only
  // asks the human reviewer to look closer, it changes no outcome by itself.
  const ip = clientIp(req);
  const day = signals.dayUTC();
  const bucket = signals.bucketHash(ip, day);
  const repSummary = await reputationSummary(ip, token);
  await repUpdate(day, bucket, "submitted", token);
  const record = {
    status: "pending",
    agency_id: body.agency_id,
    source_url: body.source_url,
    downloaded_at: body.downloaded_at,
    description: body.description.trim(),
    received_at: receivedAt,
    report: body.report,
    content_hash: contentHash,  // Argon2id hash for deduplication
    _signals: {
      bucket,
      day,
      reputation_flag: signals.reputationFlag(repSummary),
    },
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
    return send(res, 502, CODES.REPORT_502_001());
  }
};
