/* Contracts tab: the actual contract documents behind the tracker.
 * Data: data/contracts.json, generated at build time by
 * scripts/vercel_build.py from the curated registry in
 * scripts/contracts.py. Card markup mirrors the deploy-time pre-render
 * (_prerender_contracts) so crawlers and no-JS readers see the same
 * list the JS renders.
 */
"use strict";

const ContractsTab = (() => {
  const { esc, el, fetchJson, PATHS, safeUrl } = Utils;
  let entries = [];

  const STATUS_LABEL = {
    active: "Active",
    pending: "Under debate",
    cancelled: "Cancelled",
    rejected: "Proposal rejected",
    expired: "Expired",
  };

  function publisherOf(url) {
    try {
      return new URL(url).hostname.replace(/^www\./, "");
    } catch {
      return "";
    }
  }

  function facts(e) {
    const parts = [];
    const place = [e.city, e.state].filter(Boolean).join(", ");
    if (place) parts.push(place);
    if (e.status) parts.push(STATUS_LABEL[e.status] || e.status);
    if (e.contract_start || e.contract_end) {
      parts.push(`Term: ${e.contract_start || "?"} to ${e.contract_end || "open"}`);
    }
    if (e.renewal_date) parts.push(`Renewal: ${e.renewal_date}`);
    if (e.annual_cost_usd != null) {
      parts.push(`Annual cost: $${e.annual_cost_usd.toLocaleString("en-US")}`);
    }
    if (e.cameras != null) parts.push(`Cameras: ${e.cameras}`);
    return parts.join(" · ");
  }

  function card(e) {
    const badge = e.kind === "signed_agreement"
      ? '<span class="badge ok">Signed agreement</span>'
      : '<span class="badge lead">Authorizing instrument</span>';
    const asof = e.accurate_as_of
      ? `Record accurate as of ${e.accurate_as_of}`
      : "Record not yet re-verified";
    const meta = [publisherOf(e.doc_url), e.doc_date || "undated", asof]
      .filter(Boolean).join(" · ");
    return (
      `<article class="source-card">${badge}` +
      `<h3><a href="${esc(safeUrl(e.doc_url))}" target="_blank" rel="noopener noreferrer">${esc(e.doc_title)}</a></h3>` +
      `<p class="source-meta">${esc(meta)}</p>` +
      `<p class="contract-facts">${esc(facts(e))}</p>` +
      `<p class="cited-by">${esc(e.doc_note)}</p></article>`
    );
  }

  function render() {
    const kind = el("contract-filter-kind").value;
    const q = el("contract-filter-search").value.trim().toLowerCase();
    const tokens = q.split(/\s+/).filter(Boolean);
    const shown = entries.filter((e) => {
      if (kind && e.kind !== kind) return false;
      if (tokens.length) {
        const hay = [e.agency, e.city || "", e.state || "",
          e.doc_title, e.doc_note].join(" ").toLowerCase();
        if (!tokens.every((t) => hay.includes(t))) return false;
      }
      return true;
    });
    el("contracts-list").innerHTML = shown.map(card).join("");
    el("contracts-status").textContent =
      shown.length === entries.length
        ? `${entries.length} contract documents.`
        : `${shown.length} of ${entries.length} contract documents.`;
  }

  function debounce(fn, ms) {
    let t;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...args), ms);
    };
  }

  async function init() {
    el("contract-filter-kind").addEventListener("change", render);
    el("contract-filter-search").addEventListener("input", debounce(render, 250));
    try {
      const doc = await fetchJson(PATHS.contracts);
      entries = doc.entries || [];
      const signed = entries.filter((e) => e.kind === "signed_agreement").length;
      el("contracts-stats").textContent =
        `${entries.length} contract documents across ` +
        `${new Set(entries.map((e) => e.agency_id)).size} agencies: ` +
        `${signed} signed agreements, ${entries.length - signed} authorizing instruments. ` +
        `Dataset last updated ${doc.dataset_last_updated || "unknown"}.`;
      render();
    } catch (err) {
      console.error("[CLIENT_CONTRACTS_001]", err);
      el("contracts-status").textContent =
        `Could not load contracts (${err.message}). [CLIENT_CONTRACTS_001] The pre-rendered list below may be stale.`;
    }
  }

  return { init };
})();
