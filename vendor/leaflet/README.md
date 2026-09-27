# Vendored Leaflet 1.9.4

Self-hosted so the tracker has zero third-party script/style dependencies.
No CDN, no SRI needed: the bytes below are served from the same origin as
the page and are covered by the site's Content-Security-Policy
(`script-src 'self'` / `style-src 'self'`).

## Provenance

- Upstream: Leaflet 1.9.4 (https://leafletjs.com), BSD 2-Clause (see LICENSE).
- Fetched 2026-09-26 from **two** independent CDNs and compared byte-for-byte:
  - https://unpkg.com/leaflet@1.9.4/dist/
  - https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/
- All 7 files (leaflet.js, leaflet.css, 5 images) matched exactly across both.

## Integrity

- `leaflet.js` SHA-256: `db49d009c841f5ca34a888c96511ae936fd9f5533e90d8b2c4d57596f4e5641a`
- `leaflet.css` SHA-256: `a7837102824184820dfa198d1ebcd109ff6d0ff9a2672a074b9a1b4d147d04c6`

To upgrade: re-fetch from both CDNs, verify the match, update the hashes
above, and record the change in the release notes.
