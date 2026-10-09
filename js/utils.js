/* Shared utilities: HTML escaping, DOM helpers, data paths.
 * Single source of truth to prevent divergence bugs (e.g. XSS fix applied
 * in one file but missed in a duplicated copy).
 */
"use strict";

const Utils = (() => {
  // Centralized data paths. Change once here, not in three files.
  const PATHS = {
    agencies: "data/agencies.json",
    manifest: "data/integrity/manifest.json",
    classification: "data/source_classification.json",
    evidence: "data/evidence.json",
  };

  // HTML escape. Use for ALL user/data-derived strings injected via innerHTML.
  function esc(s) {
    return String(s ?? "").replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function el(id) {
    return document.getElementById(id);
  }

  // URL scheme gate for href attributes. esc() stops attribute breakout
  // but a javascript:/data: URL has no escapable characters and executes
  // on click, so data-derived URLs must pass this first. Returns "#" for
  // anything that is not http(s). Always esc() the result for the
  // attribute, same as before.
  function safeUrl(u) {
    return /^https?:\/\//i.test(u || "") ? u : "#";
  }

  // Fetch JSON with a descriptive error. Throws on network or parse failure.
  async function fetchJson(path) {
    const res = await fetch(path);
    if (!res.ok) throw new Error(`HTTP ${res.status} fetching ${path}`);
    return res.json();
  }

  return { PATHS, esc, el, fetchJson, safeUrl };
})();
