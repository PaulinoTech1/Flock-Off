/* Petitions tab: citizen petitions created to counter Flock Safety
 * deployments. Data: data/petitions.json, generated at build time by
 * scripts/vercel_build.py from the curated registry in
 * scripts/petitions.py. Card markup mirrors the deploy-time pre-render
 * (_prerender_petitions) so crawlers and no-JS readers see the same
 * list the JS renders. Signature counts are snapshots with an as-of
 * date, never live counters.
 */
"use strict";

const PetitionsTab = (() => {
  const { esc, el, fetchJson, PATHS, safeUrl } = Utils;
  let entries = [];

  function facts(e) {
    const parts = [];
    if (e.target_text) parts.push(`To: ${e.target_text}`);
    if (e.signatures != null) {
      const asof = e.signatures_as_of ? ` (as of ${e.signatures_as_of})` : "";
      parts.push(`${e.signatures.toLocaleString("en-US")} signatures${asof}`);
    }
    if (e.organizer) parts.push(`Organizer: ${e.organizer}`);
    if (e.started) parts.push(`Started ${e.started}`);
    return parts.join(" · ");
  }

  function card(e) {
    const badge = e.status === "open"
      ? `<span class="badge ok">${esc(e.status_label)}</span>`
      : `<span class="badge lead">${esc(e.status_label)}</span>`;
    const meta = [e.platform, e.place].filter(Boolean).join(" · ");
    return (
      `<article class="source-card">${badge}` +
      `<h3><a href="${esc(safeUrl(e.url))}" target="_blank" rel="noopener noreferrer">${esc(e.title)}</a></h3>` +
      `<p class="source-meta">${esc(meta)}</p>` +
      `<p class="contract-facts">${esc(facts(e))}</p>` +
      `<p class="cited-by">${esc(e.note)}</p></article>`
    );
  }

  function render() {
    const q = el("petition-filter-search").value.trim().toLowerCase();
    const tokens = q.split(/\s+/).filter(Boolean);
    const shown = entries.filter((e) => {
      if (!tokens.length) return true;
      const hay = [e.title, e.platform, e.place || "", e.target_text, e.note,
        e.agency || ""].join(" ").toLowerCase();
      return tokens.every((t) => hay.includes(t));
    });
    el("petitions-list").innerHTML = shown.map(card).join("");
    el("petitions-empty").hidden = shown.length !== 0;
    el("petitions-status").textContent =
      shown.length === entries.length
        ? `${entries.length} petitions.`
        : `${shown.length} of ${entries.length} petitions.`;
  }

  function debounce(fn, ms) {
    let t;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...args), ms);
    };
  }

  async function init() {
    el("petition-filter-search").addEventListener("input", debounce(render, 250));
    el("petitions-clear").addEventListener("click", () => {
      el("petition-filter-search").value = "";
      render();
    });
    try {
      const doc = await fetchJson(PATHS.petitions);
      entries = doc.entries || [];
      const open = entries.filter((e) => e.status === "open").length;
      el("petitions-stats").textContent =
        `${entries.length} citizen petitions against Flock deployments: ` +
        `${open} still collecting signatures. ` +
        `Signature counts are snapshots, dated on each card.`;
      render();
    } catch (err) {
      console.error("[CLIENT_PETITIONS_001]", err);
      el("petitions-status").textContent =
        `Could not load petitions (${err.message}). [CLIENT_PETITIONS_001] The pre-rendered list below may be stale.`;
    }
  }

  return { init };
})();
