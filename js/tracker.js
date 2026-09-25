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

  // Evidence bar (docs/METHODOLOGY.md): a terminal claim is verified only with
  // 3+ independent citations from verified sources. Independence is approximated
  // by distinct domains; a human judges syndication and press-release quoting.
  const TERMINAL_STATUS = new Set(["cancelled", "rejected", "expired"]);
  const EVIDENCE_BAR = 3;

  function hostOf(url) {
    try { return new URL(url).hostname.replace(/^www\./, ""); }
    catch { return String(url); }
  }

  function evidence(a) {
    const verified = (a.sources || []).filter((s) => s.verified);
    const independent = new Set(verified.map((s) => hostOf(s.url))).size;
    const terminal = TERMINAL_STATUS.has(a.status);
    return {
      independent,
      verifiedCount: verified.length,
      terminal,
      met: !terminal || independent >= EVIDENCE_BAR,
    };
  }

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
    for (const id of ["filter-state", "filter-status", "filter-sort", "filter-evidence"]) {
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
    renderPriorities();
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
    const evf = el("filter-evidence").value;
    let rows = agencies.filter((a) => {
      if (evf === "needs" || evf === "verified") {
        const ev = evidence(a);
        if (evf === "needs" && !(ev.terminal && !ev.met)) return false;
        if (evf === "verified" && !(ev.terminal && ev.met)) return false;
      }
      return (!st || a.state === st) &&
        (!status || a.status === status) &&
        (!q || `${a.agency} ${a.city}`.toLowerCase().includes(q));
    });
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
      const ev = evidence(a);
      const evBadge = (ev.terminal && !ev.met)
        ? ' <span class="badge badge-unverified">needs corroboration</span>' : "";
      tr.innerHTML =
        `<td><strong>${esc(a.agency)}</strong><br><span class="muted">${esc(a.city || "")}</span></td>` +
        `<td>${esc(a.state)}</td>` +
        `<td><span class="badge badge-${a.status}">${STATUS_LABEL[a.status] || a.status}</span>${evBadge}</td>` +
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
    const verifiedWon = won.filter((a) => evidence(a).met).length;
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
      stat(`${verifiedWon}/${won.length}`, "cancellations verified (evidence bar)") +
      stat(upcoming, "renewals within 180 days") +
      stat(spend ? usd(spend) : "—", "known annual spend (active)");
  }

  function openDrawer(a) {
    el("drawer-title").textContent = a.agency;
    const ev = evidence(a);
    const shownConfidence = (ev.terminal && !ev.met) ? "low" : (a.confidence || "unrated");
    const cappedNote = (ev.terminal && !ev.met && a.confidence && a.confidence !== "low")
      ? ' <span class="muted">(capped: evidence bar not met)</span>' : "";
    const src = (a.sources || []).map((s) =>
      `<li><span class="${s.verified ? "src-ver" : "src-unver"}" title="${s.verified
        ? "Verified source: counts toward the evidence bar"
        : "Unverified: lead only, not counted toward the evidence bar"}">${s.verified ? "✓" : "○"}</span> ` +
      `<a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.title)}</a>` +
      (s.date ? ` <span class="muted">(${esc(s.date)})</span>` : "") + `</li>`
    ).join("");
    const evSection = !ev.terminal ? "" :
      `<h3>Evidence</h3>` +
      `<p class="status">Evidence bar: <strong>${ev.independent} of ${EVIDENCE_BAR}</strong> independent verified citations. ` +
      (ev.met
        ? `<span class="badge badge-ok">met</span>`
        : `<span class="badge badge-unverified">not met</span> This claim is awaiting corroboration.`) +
      `</p>`;
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
      evSection +
      (a.transparency_portal
        ? `<p><a href="${esc(a.transparency_portal)}" target="_blank" rel="noopener noreferrer">Flock transparency portal</a></p>` : "") +
      (a.notes ? `<p>${esc(a.notes)}</p>` : "") +
      `<h3>Sources</h3><ul>${src || "<li>none listed</li>"}</ul>` +
      `<p class="muted">✓ verified citation · ○ unverified lead (not counted toward the evidence bar)</p>` +
      `<p class="status">Confidence: <strong>${esc(shownConfidence)}</strong>${cappedNote} · last verified ${esc(a.last_verified || "unknown" )}. ` +
      `Wrong or stale? <a href="https://github.com/PaulinoTech1/Flock-Off/issues" target="_blank" rel="noopener noreferrer">Open an issue</a>.</p>`;
    el("drawer").hidden = false;
    el("drawer-close").focus();
  }

  function renderPriorities() {
    const host = el("priorities");
    if (!host || !agencies.length) return;
    const terminal = agencies.filter((a) => TERMINAL_STATUS.has(a.status));
    const unmet = terminal.filter((a) => !evidence(a).met).length;
    const active = agencies.filter((a) => a.status === "active");
    const noRenewal = active.filter((a) => !a.renewal_date).length;
    const byState = {};
    agencies.forEach((a) => { byState[a.state] = (byState[a.state] || 0) + 1; });
    const thinStates = Object.entries(byState)
      .filter(([, n]) => n <= 1).map(([s]) => s).sort();
    const card = (title, body, done) =>
      `<div class="priority-card"><h3>${title}</h3><p>${body}</p>` +
      `<p><strong>Done looks like:</strong> ${done}</p></div>`;
    host.innerHTML =
      `<h2>Research priorities</h2>` +
      `<p class="status">Ranked by what most improves the tracker's trustworthiness. Counts are live from the dataset.</p>` +
      `<div class="priorities-grid">` +
      card("1. Corroborate terminal claims",
        `<strong>${unmet} of ${terminal.length}</strong> cancelled/rejected records sit below the evidence bar of ${EVIDENCE_BAR} independent verified citations.`,
        "3 independent verified citations per record.") +
      card("2. Fill the map gaps",
        (byState.MD ? "" : `<strong>Maryland: 0 records.</strong> `) +
        (thinStates.length ? `Single-record states: <strong>${thinStates.join(", ")}</strong>.` : "No single-record states."),
        "every East Coast state with 3+ sourced records.") +
      card("3. Renewal dates for active contracts",
        `<strong>${noRenewal} of ${active.length}</strong> active contracts have no exact renewal date.`,
        "a dated pressure window for every active contract.") +
      `</div>` +
      `<p class="status"><a href="https://github.com/PaulinoTech1/Flock-Off/blob/main/docs/METHODOLOGY.md#evidence-bar">Evidence bar</a> · ` +
      `<a href="https://github.com/PaulinoTech1/Flock-Off/issues" target="_blank" rel="noopener noreferrer">Contribute research</a></p>`;
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
