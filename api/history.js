"use strict";
/* GET /api/history — read-only listing of historical reports for one agency.
 *
 * Query: ?agency_id=<id>&limit=<1..200, default 50>&cursor=<opaque>
 * Returns metadata only (pathname, url, size, uploadedAt); report payloads
 * are fetched from their public blob URLs. No auth required to read.
 *
 * Requires BLOB_READ_WRITE_TOKEN env (set in the Vercel dashboard).
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
    return send(res, 405, { error: "method not allowed" });
  }
  const token = process.env.BLOB_READ_WRITE_TOKEN;
  if (!token) return send(res, 503, { error: "history store not configured" });

  const q = req.query || {};
  const agencyId = typeof q.agency_id === "string" ? q.agency_id : "";
  if (!/^[a-z0-9-]{1,80}$/.test(agencyId)) {
    return send(res, 400, { error: "agency_id is required (a-z, 0-9, dashes)" });
  }
  let limit = parseInt(q.limit, 10);
  if (!Number.isFinite(limit) || limit < 1) limit = 50;
  if (limit > 200) limit = 200;
  const cursor = typeof q.cursor === "string" && q.cursor.length <= 500 ? q.cursor : undefined;

  try {
    const data = await blobList(`reports/${agencyId}/`, limit, cursor, token);
    return send(res, 200, {
      agency_id: agencyId,
      reports: (data.blobs || []).map((b) => ({
        pathname: b.pathname,
        url: b.url,
        size: b.size,
        uploadedAt: b.uploadedAt,
      })),
      cursor: data.cursor || null,
      hasMore: !!data.hasMore,
    });
  } catch (e) {
    return send(res, 502, { error: "could not read history store" });
  }
};
