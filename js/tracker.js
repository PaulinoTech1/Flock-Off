/* Tracker tab: Flock Safety contract / cancellation tracker.
 * Data: data/agencies.json (community-researched, sourced per record).
 * All stats and rendering derive from the loaded dataset; nothing is hardcoded.
 */
"use strict";

const TrackerTab = (() => {
  let agencies = [];
  let meta = {};

  const STATUS_LABEL = {
    active: "Active",
    pending: "Under debate",
    cancelled: "Cancelled",
    rejected: "Proposal rejected",
    expired: "Expired",
  };

  const el = (id) => document.getElementById(id);
  const usd = (n) =>
    n == null ? "—" : new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);

  async function init() {
    try {
      const res = await fetch("data/agencies.json");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      agencies = json.agencies || [];
      meta = json.meta || {};
    } catch (err) {
      el("tracker-status").textContent = `Could not load contract data (${err.message}).`;
      return;
    }
    el("coverage-note").textContent = meta.coverage_note || "";
    buildStateFilter();
    for (const id of ["filter-state", "filter-status", "filter-sort"]) {
      el(id).addEventListener("change", render);
    }
    el("filter-search").addEventListener("input", debounce(render, 250));
    el("drawer-close").addEventListener("click", closeDrawer);
    el("drawer").addEventListener("click", (e) => {
      if (e.target.id === "drawer") closeDrawer();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !el("drawer").hidden) closeDrawer();
    });
    render();
  }

  function debounce(fn, ms) {
    let t;
    return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
  }

  function buildStateFilter() {
    const sel = el("filter-state");
    const states = [...new Set(agencies.map((a) => a.state))].sort();
    for (const s of states) {
      const opt = document.createElement("option");
      opt.value = s;
      opt.textContent = s;
      sel.appendChild(opt);
    }
  }

  function daysUntil(dateStr) {
    if (!dateStr) return null;
    const now = new Date();
    now.setHours(0, 0, 0, 0);
    const d = new Date(dateStr + "T00:00:00");
    return Math.round((d - now) / 86400000);
  }

  function filtered() {
    const st = el("filter-state").value;
    const status = el("filter-status").value;
    const q = el("filter-search").value.trim().toLowerCase();
    const sort = el("filter-sort").value;
    let rows = agencies.filter((a) =>
      (!st || a.state === st) &&
      (!status || a.status === status) &&
      (!q || `${a.agency} ${a.city}`.toLowerCase().includes(q))
    );
    const byRenewal = (a, b) => {
      const da = a.renewal_date || "9999";
      const db = b.renewal_date || "9999";
      return da < db ? -1 : da > db ? 1 : 0;
    };
    if (sort === "renewal") rows.sort(byRenewal);
    else if (sort === "cameras") rows.sort((a, b) => (b.cameras || 0) - (a.cameras || 0));
    else if (sort === "cost") rows.sort((a, b) => (b.annual_cost_usd || 0) - (a.annual_cost_usd || 0));
    else rows.sort((a, b) => a.agency.localeCompare(b.agency));
    return rows;
  }

  function renewalCell(a) {
    if (a.status === "active" && a.renewal_date) {
      const d = daysUntil(a.renewal_date);
      const soon = d != null && d >= 0 && d <= 180;
      return `${a.renewal_date}${soon ? ' <span class="badge badge-warn">renewal soon</span>' : ""}`;
    }
    if ((a.status === "cancelled" || a.status === "rejected") && a.decision_date) {
      return a.decision_date;
    }
    if (a.contract_end) return a.contract_end;
    return "—";
  }

  function render() {
    const rows = filtered();
    renderStats();
    const tb = el("tracker-table").querySelector("tbody");
    tb.innerHTML = "";
    for (const a of rows) {
      const tr = document.createElement("tr");
      tr.tabIndex = 0;
      tr.setAttribute("role", "button");
      tr.setAttribute("aria-label", `Details for ${a.agency}`);
      const open = () => openDrawer(a);
      tr.addEventListener("click", open);
      tr.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); }
      });
      tr.innerHTML =
        `<td><strong>${esc(a.agency)}</strong><br><span class="muted">${esc(a.city || "")}</span></td>` +
        `<td>${esc(a.state)}</td>` +
        `<td><span class="badge badge-${a.status}">${STATUS_LABEL[a.status] || a.status}</span></td>` +
        `<td>${a.cameras ?? "—"}</td>` +
        `<td>${usd(a.annual_cost_usd)}</td>` +
        `<td>${renewalCell(a)}</td>`;
      tb.appendChild(tr);
    }
    el("tracker-status").textContent =
      `${rows.length} record${rows.length === 1 ? "" : "s"} shown. Select a row for sources and detail.`;
  }

  function renderStats() {
    const active = agencies.filter((a) => a.status === "active");
    const won = agencies.filter((a) => a.status === "cancelled" || a.status === "rejected");
    const spend = active.reduce((s, a) => s + (a.annual_cost_usd || 0), 0);
    const upcoming = active.filter((a) => {
      const d = daysUntil(a.renewal_date);
      return d != null && d >= 0 && d <= 180;
    }).length;
    const stat = (n, label) =>
      `<div class="stat"><span class="stat-n">${n}</span><span class="stat-l">${label}</span></div>`;
    el("tracker-stats").innerHTML =
      stat(agencies.length, "agencies tracked") +
      stat(active.length, "active contracts") +
      stat(won.length, "cancelled / rejected") +
      stat(upcoming, "renewals within 180 days") +
      stat(spend ? usd(spend) : "—", "known annual spend (active)");
  }

  function openDrawer(a) {
    el("drawer-title").textContent = a.agency;
    const src = (a.sources || []).map((s) =>
      `<li><a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.title)}</a>` +
      (s.date ? ` <span class="muted">(${esc(s.date)})</span>` : "") + `</li>`
    ).join("");
    const timeline = [
      ["Status", `<span class="badge badge-${a.status}">${STATUS_LABEL[a.status] || a.status}</span>`],
      ["Location", `${esc(a.city || "")}, ${esc(a.state)}`],
      ["Agency type", esc((a.agency_type || "").replace(/_/g, " "))],
      ["Cameras", a.cameras ?? "unknown"],
      ["Annual cost", usd(a.annual_cost_usd)],
      ["Contract start", a.contract_start || "—"],
      ["Contract end", a.contract_end || "—"],
      ["Renewal date", a.renewal_date || "—"],
      ["Decision date", a.decision_date || "—"],
      ["Decision", esc(a.decision_summary || "—")],
    ].map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("");
    el("drawer-body").innerHTML =
      `<dl class="detail">${timeline}</dl>` +
      (a.transparency_portal
        ? `<p><a href="${esc(a.transparency_portal)}" target="_blank" rel="noopener noreferrer">Flock transparency portal</a></p>` : "") +
      (a.notes ? `<p>${esc(a.notes)}</p>` : "") +
      `<h3>Sources</h3><ul>${src || "<li>none listed</li>"}</ul>` +
      `<p class="status">Confidence: <strong>${esc(a.confidence || "unrated")}</strong> · last verified ${esc(a.last_verified || "unknown" )}. ` +
      `Wrong or stale? <a href="https://github.com/PaulinoTech1/Flock-Off/issues" target="_blank" rel="noopener noreferrer">Open an issue</a>.</p>`;
    el("drawer").hidden = false;
    el("drawer-close").focus();
  }

  function closeDrawer() {
    el("drawer").hidden = true;
  }

  function esc(s) {
    return String(s ?? "").replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  return { init };
})();
