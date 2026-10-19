/* Shared utilities: HTML escaping, DOM helpers, data paths.
 * Single source of truth to prevent divergence bugs (e.g. XSS fix applied
 * in one file but missed in a duplicated copy).
 */
"use strict";

const Utils = (() => {
  // Centralized data paths. Change once here, not in three files.
  const PATHS = {
    agencies: "data/agencies.json",
    contracts: "data/contracts.json",
    petitions: "data/petitions.json",
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

  // CSV cell with spreadsheet formula-injection defense. A cell whose
  // text starts with =, +, -, or @ (after optional leading spaces/tabs)
  // can execute as a formula when the CSV is opened in a spreadsheet;
  // prefixing a single quote neutralizes it (OWASP CSV injection
  // guidance). Cells containing commas, quotes, or newlines are
  // double-quoted with embedded quotes doubled (RFC 4180).
  function csvCell(value) {
    let s = value == null ? "" : String(value);
    if (/^[ \t]*[=+\-@\t\r]/.test(s)) s = "'" + s;
    if (/[",\n\r]/.test(s)) s = '"' + s.replace(/"/g, '""') + '"';
    return s;
  }

  function toCSV(headers, rows) {
    const lines = [headers.map(csvCell).join(",")];
    for (const row of rows) lines.push(row.map(csvCell).join(","));
    return lines.join("\r\n") + "\r\n";
  }

  // Client-side file download (Blob + object URL). No network involved.
  function download(filename, text, type = "text/csv") {
    const blob = new Blob([text], { type: `${type};charset=utf-8` });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
  }

  return { PATHS, esc, el, fetchJson, safeUrl, csvCell, toCSV, download };
})();
