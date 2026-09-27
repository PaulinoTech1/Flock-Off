"use strict";
const { CODES } = require("./_errors.js");
/* GET /api/history — read-only listing of historical reports for one agency.
 *
 * Query: ?agency_id=<id>&limit=<1..200, default 50>&cursor=<opaque>
 * Returns full report records (proxied from private blobs). No auth required
 * to read approved reports. Blob URLs are never exposed; all content goes
 * through this endpoint.
 *
 * Requires REPORTS_BLOB_READ_WRITE_TOKEN env (set in the Vercel dashboard).
 */

const BLOB_API = "https://vercel.com/api/blob";
const API_VERSION = "12"; // pinned to the @vercel/blob protocol version verified 2026-09-25

function send(res, code, obj) {
  res.statusCode = code;
  res.setHeader("Content-Type", "application/json");
  res.setHeader("Cache-Control", "public, max-age=60");
  res.end(JSON.stringify(obj));
}

async function blobList(prefix, limit, cursor, token) {
  const params = new URLSearchParams({ prefix, limit: String(limit) });
  if (cursor) params.set("cursor", cursor);
  const res = await fetch(`${BLOB_API}/?${params.toString()}`, {
    headers: {
      authorization: `Bearer ${token}`,
      "x-api-version": API_VERSION,
    },
  });
  if (!res.ok) throw new Error(`blob list failed: HTTP ${res.status}`);
  return res.json();
}

module.exports = async (req, res) => {
  if (req.method !== "GET") {
    res.setHeader("Allow", "GET");
    return send(res, 405, CODES.HISTORY_405_001());
  }
  const token = process.env.REPORTS_BLOB_READ_WRITE_TOKEN;
  if (!token) return send(res, 503, CODES.HISTORY_503_001());

  const q = req.query || {};
  const agencyId = typeof q.agency_id === "string" ? q.agency_id : "";
  if (!/^[a-z0-9-]{1,80}$/.test(agencyId)) {
    return send(res, 400, CODES.HISTORY_400_001());
  }
  let limit = parseInt(q.limit, 10);
  if (!Number.isFinite(limit) || limit < 1) limit = 50;
  if (limit > 200) limit = 200;
  const cursor = typeof q.cursor === "string" && q.cursor.length <= 500 ? q.cursor : undefined;

  try {
    const data = await blobList(`reports/${agencyId}/`, limit, cursor, token);
    // Fetch each report's content via authenticated requests (private blobs).
    // Strip internal fields before returning to the public.
    const reports = [];
    for (const b of (data.blobs || [])) {
      try {
        const r = await fetch(b.url, {
          headers: { authorization: `Bearer ${token}` },
        });
        if (!r.ok) continue;
        const text = await r.text();
        if (text.length > 64 * 1024) continue;
        const record = JSON.parse(text);
        // Only return approved reports; strip internal signals
        if (record.status !== "approved") continue;
        const { _signals, content_hash, ...publicRecord } = record;
        reports.push({
          pathname: b.pathname,
          size: b.size,
          uploadedAt: b.uploadedAt,
          ...publicRecord,
        });
      } catch {
        continue;
      }
    }
    return send(res, 200, {
      agency_id: agencyId,
      reports,
      cursor: data.cursor || null,
      hasMore: !!data.hasMore,
    });
  } catch (e) {
    return send(res, 502, CODES.HISTORY_502_001());
  }
};
