"use strict";
/* GET /api/pending — reviewer queue for the quarantine model.
 *
 * Lists reports-pending/ blobs with each submission's full record so a human
 * reviewer can decide whether to promote (POST /api/promote) or ignore them.
 * A body that fails to fetch or parse is returned with record: null rather
 * than failing the whole listing.
 *
 * Auth: REPORT_ADMIN_KEY is mandatory (constant-time compare against the
 * x-admin-key header).
 */

const BLOB_API = "https://vercel.com/api/blob";
const API_VERSION = "12"; // pinned to the @vercel/blob protocol version verified 2026-09-25

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

module.exports = async (req, res) => {
  if (req.method !== "GET") {
    res.setHeader("Allow", "GET");
    return send(res, 405, { error: "method not allowed" });
  }
  const token = process.env.BLOB_READ_WRITE_TOKEN;
  const adminKey = process.env.REPORT_ADMIN_KEY;
  if (!token || !adminKey) return send(res, 503, { error: "review queue not configured" });
  if (!timingSafeEqual(req.headers["x-admin-key"], adminKey)) {
    return send(res, 401, { error: "missing or invalid admin key" });
  }

  let listing;
  try {
    const r = await fetch(`${BLOB_API}/?prefix=${encodeURIComponent("reports-pending/")}&limit=50`, {
      headers: { authorization: `Bearer ${token}`, "x-api-version": API_VERSION },
    });
    if (!r.ok) return send(res, 502, { error: "could not list pending reports" });
    listing = await r.json();
  } catch {
    return send(res, 502, { error: "could not list pending reports" });
  }

  const items = [];
  for (const b of (listing.blobs || []).slice(0, 50)) {
    let record = null;
    let note = null;
    try {
      const r = await fetch(b.url);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const text = await r.text();
      if (text.length > 64 * 1024) throw new Error("body too large");
      record = JSON.parse(text);
    } catch (e) {
      note = "could not load submission body";
    }
    items.push({
      pathname: b.pathname,
      url: b.url,
      size: b.size,
      uploadedAt: b.uploadedAt,
      record,
      note,
    });
  }

  return send(res, 200, {
    count: items.length,
    hasMore: Boolean(listing.hasMore),
    cursor: listing.cursor || null,
    items,
  });
};
