/* Sources tab: every citation in the dataset, aggregated by URL and browsable.
 * Data: data/agencies.json. Card markup mirrors the deploy-time pre-render
 * in vercel_deploy.py (_prerender_sources) so crawlers and no-JS readers
 * see the same list the JS renders.
 */
"use strict";

const SourcesTab = (() => {
  let entries = [];

  function el(id) {
    return document.getElementById(id);
  }

  function publisherOf(url) {
    try {
      return new URL(url).hostname.replace(/^www\./, "");
    } catch {
      return "";
    }
  }

  function aggregate(agencies) {
    const byUrl = new Map();
    for (const a of agencies) {
      for (const s of a.sources || []) {
        if (!s.url) continue;
        let e = byUrl.get(s.url);
        if (!e) {
          e = {
            url: s.url,
            title: s.title || s.url,
            date: s.date || null,
            verified: !!s.verified,
            publisher: publisherOf(s.url),
            agencies: [],
          };
          byUrl.set(s.url, e);
        }
        if (!e.title || e.title === e.url) e.title = s.title || e.title;
        if (s.verified) e.verified = true;
        e.agencies.push({ agency: a.agency, state: a.state, status: a.status });
      }
    }
    const list = [...byUrl.values()];
    list.sort((x, y) =>
      (y.verified - x.verified) ||
      x.publisher.localeCompare(y.publisher) ||
      x.title.localeCompare(y.title)
    );
    return list;
  }

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function card(e) {
    const badge = e.verified
      ? '<span class="badge ok">Verified citation</span>'
      : '<span class="badge lead">Lead</span>';
    const meta = [e.publisher, e.date || "undated"].filter(Boolean).join(" · ");
    const cited = e.agencies
      .map((a) => `${a.agency} (${a.state})`)
      .join(", ");
    return (
      `<article class="source-card">${badge}` +
      `<h3><a href="${esc(e.url)}" target="_blank" rel="noopener noreferrer">${esc(e.title)}</a></h3>` +
      `<p class="source-meta">${esc(meta)}</p>` +
      `<p class="cited-by">Cited by: ${esc(cited)}</p></article>`
    );
  }

  function render() {
    const type = el("src-filter-type").value;
    const q = el("src-filter-search").value.trim().toLowerCase();
    const shown = entries.filter((e) => {
      if (type === "verified" && !e.verified) return false;
      if (type === "lead" && e.verified) return false;
      if (q) {
        const hay = [e.title, e.publisher, e.url,
          ...e.agencies.map((a) => a.agency)].join(" ").toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
    el("sources-list").innerHTML = shown.map(card).join("");
    el("sources-status").textContent =
      shown.length === entries.length
        ? `${entries.length} sources.`
        : `${shown.length} of ${entries.length} sources.`;
  }

  function debounce(fn, ms) {
    let t;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...args), ms);
    };
  }

  async function init() {
    el("src-filter-type").addEventListener("change", render);
    el("src-filter-search").addEventListener("input", debounce(render, 250));
    try {
      const res = await fetch("data/agencies.json");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      entries = aggregate(json.agencies || []);
      const v = entries.filter((e) => e.verified).length;
      el("sources-stats").textContent =
        `${entries.length} unique sources across ${json.agencies.length} records: ` +
        `${v} verified citations, ${entries.length - v} leads.`;
      render();
    } catch (err) {
      el("sources-status").textContent =
        `Could not load sources (${err.message}). The pre-rendered list below may be stale.`;
    }
  }

  return { init };
})();
