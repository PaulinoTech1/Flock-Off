/* Tracker tab: Flock Safety contract / cancellation tracker.
 * Data: data/agencies.json (community-researched, sourced per record).
 * All stats and rendering derive from the loaded dataset; nothing is hardcoded.
 */
"use strict";

const TrackerTab = (() => {
  let agencies = [];
  let meta = {};
  let classification = null;

  const STATUS_LABEL = {
    active: "Active",
    pending: "Under debate",
    cancelled: "Cancelled",
    rejected: "Proposal rejected",
    expired: "Expired",
  };

  // Evidence tiers (docs/METHODOLOGY.md): terminal claims are "verified"
  // (strongly claimed) at 3+ independent verified citations, otherwise
  // "pending validation*" with the exact count shown. Independence is
  // approximated by distinct domains; a human judges syndication.
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
    const tier = !terminal ? "na" : independent >= EVIDENCE_BAR ? "verified" : "pending";
    return { independent, verifiedCount: verified.length, terminal, tier };
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
    try {
      const cres = await fetch("data/source_classification.json");
      if (cres.ok) classification = await cres.json();
    } catch { /* transparency list degrades to a repo link */ }
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
    // Keep keyboard focus inside the modal drawer while it is open.
    el("drawer").addEventListener("keydown", (e) => {
      if (e.key !== "Tab") return;
      const f = [...el("drawer").querySelectorAll(
        'a[href], button:not([disabled]), input, select, [tabindex]:not([tabindex="-1"])'
      )].filter((n) => n.offsetParent !== null);
      if (!f.length) return;
      const first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault(); last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault(); first.focus();
      }
    });
    render();
    renderPriorities();
    renderTransparency();
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
      if (evf === "pending" || evf === "verified") {
        const tier = evidence(a).tier;
        if (evf === "pending" && tier !== "pending") return false;
        if (evf === "verified" && tier !== "verified") return false;
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
    else if (sort === "state") rows.sort((a, b) => a.state.localeCompare(b.state) || a.agency.localeCompare(b.agency));
    else if (sort === "city") rows.sort((a, b) => (a.city || "").localeCompare(b.city || "") || a.agency.localeCompare(b.agency));
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
      const open = () => openDrawer(a, tr);
      tr.addEventListener("click", open);
      tr.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); }
      });
      const ev = evidence(a);
      const evBadge = ev.tier === "verified"
        ? ' <span class="badge badge-ok">verified</span>'
        : ev.tier === "pending"
        ? " " + pendingBadge() : "";
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
    const verifiedWon = won.filter((a) => evidence(a).tier === "verified").length;
    const pendingWon = won.filter((a) => evidence(a).tier === "pending").length;
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
      stat(verifiedWon, "verified claims") +
      stat(pendingWon, `pending validation<span aria-hidden="true">*</span><span class="visually-hidden">: fewer than 3 independent verified citations</span>`) +
      stat(upcoming, "renewals within 180 days") +
      stat(spend ? usd(spend) : "—", "known annual spend (active)");
  }

  // Accessible pending-validation badge: the visual asterisk is hidden from
  // screen readers and replaced with a spoken explanation.
  function pendingBadge() {
    return `<span class="badge badge-evpending" ` +
      `title="Fewer than ${EVIDENCE_BAR} independent verified citations; shown while awaiting corroboration">` +
      `pending validation<span aria-hidden="true">*</span>` +
      `<span class="visually-hidden">: fewer than ${EVIDENCE_BAR} independent verified citations</span></span>`;
  }

  let lastTrigger = null;

  // A modal dialog must remove the background from the accessibility tree
  // and the tab order; the focus trap alone does not stop screen-reader
  // virtual cursors from wandering behind the drawer.
  function setBackgroundInert(on) {
    for (const sel of ["header", "main", "footer"]) {
      const n = document.querySelector(sel);
      if (n) n.inert = on;
    }
  }

  function openDrawer(a, trigger) {
    lastTrigger = trigger || document.activeElement;
    el("drawer-title").textContent = a.agency;
    const ev = evidence(a);
    const src = (a.sources || []).map((s) =>
      `<li><span class="${s.verified ? "src-ver" : "src-unver"}" title="${s.verified
        ? "Verified source: counts toward the evidence bar"
        : "Unverified: lead only, not counted toward the evidence bar"}">${s.verified ? "✓" : "○"}</span> ` +
      `<a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.title)}</a>` +
      (s.date ? ` <span class="muted">(${esc(s.date)})</span>` : "") + `</li>`
    ).join("");
    const evSection = !ev.terminal ? "" :
      `<h3>Evidence</h3>` +
      `<p class="status"><strong>${ev.independent} of ${EVIDENCE_BAR}</strong> independent verified citations. ` +
      (ev.tier === "verified"
        ? `<span class="badge badge-ok">verified</span> Strongly claimed.`
        : pendingBadge()) +
      `</p>` +
      (ev.tier === "pending"
        ? `<p class="muted">* Fewer than ${EVIDENCE_BAR} independent verified citations; shown while awaiting corroboration. ` +
          `<a href="https://github.com/PaulinoTech1/Flock-Off/issues" target="_blank" rel="noopener noreferrer">Help corroborate</a>.</p>` : "");
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
      `<p class="muted">✓ verified citation · ○ unverified lead (not counted toward the evidence bar). ` +
      `Classification: <a href="https://github.com/PaulinoTech1/Flock-Off/blob/main/scripts/classify_sources.py" target="_blank" rel="noopener noreferrer">scripts/classify_sources.py</a>.</p>` +
      `<p class="status">Confidence: <strong>${esc(a.confidence || "unrated")}</strong> · last verified ${esc(a.last_verified || "unknown" )}. ` +
      `Wrong or stale? <a href="https://github.com/PaulinoTech1/Flock-Off/issues" target="_blank" rel="noopener noreferrer">Open an issue</a>.</p>` +
      `<details id="drawer-history"><summary>Report history</summary><div id="drawer-history-body"><p class="muted">Loading…</p></div></details>`;
    el("drawer").hidden = false;
    setBackgroundInert(true);
    el("drawer-close").focus();
    loadHistory(a.id);
  }

  // Historical reports live in the Vercel Blob store (append-only, JSON).
  // Degrades silently: the section simply reports unavailability.
  async function loadHistory(agencyId) {
    const box = el("drawer-history-body");
    if (!box) return;
    try {
      const res = await fetch(`/api/history?agency_id=${encodeURIComponent(agencyId)}&limit=20`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const reps = data.reports || [];
      box.innerHTML = reps.length === 0
        ? `<p class="muted">No historical reports filed yet for this agency.</p>`
        : `<ul>${reps.map((r) =>
            `<li><a href="${esc(r.url)}" target="_blank" rel="noopener noreferrer">${esc(new Date(r.uploadedAt).toISOString().slice(0, 10))}</a> ` +
            `<span class="muted">(${(r.size / 1024).toFixed(1)} KB JSON)</span></li>`).join("")}</ul>` +
          `<p class="muted">Append-only archive. Each report is tied to its source and download date; see the raw JSON.</p>`;
    } catch (e) {
      box.innerHTML = `<p class="muted">Report history unavailable.</p>`;
    }
  }

  function renderPriorities() {
    const host = el("priorities");
    if (!host || !agencies.length) return;
    const terminal = agencies.filter((a) => TERMINAL_STATUS.has(a.status));
    const pending = terminal.filter((a) => evidence(a).tier === "pending").length;
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
        `<strong>${pending} of ${terminal.length}</strong> cancelled/rejected records are pending validation* (fewer than ${EVIDENCE_BAR} independent verified citations).`,
        "3 independent verified citations per record → verified.") +
      card("2. Fill the map gaps",
        (byState.MD ? "" : `<strong>Maryland: 0 records.</strong> `) +
        (thinStates.length ? `Single-record states: <strong>${thinStates.join(", ")}</strong>.` : "No single-record states."),
        "every covered state with 3+ sourced records.") +
      card("3. Renewal dates for active contracts",
        `<strong>${noRenewal} of ${active.length}</strong> active contracts have no exact renewal date.`,
        "a dated pressure window for every active contract.") +
      `</div>` +
      `<p class="status"><a href="https://github.com/PaulinoTech1/Flock-Off/blob/main/docs/METHODOLOGY.md#evidence-tiers">Evidence tiers</a> · ` +
      `<a href="https://github.com/PaulinoTech1/Flock-Off/issues" target="_blank" rel="noopener noreferrer">Contribute research</a></p>`;
  }

  function closeDrawer() {
    el("drawer").hidden = true;
    setBackgroundInert(false);
    if (lastTrigger && typeof lastTrigger.focus === "function") lastTrigger.focus();
    lastTrigger = null;
  }

  function renderTransparency() {
    let v = 0, u = 0;
    for (const a of agencies) {
      for (const s of (a.sources || [])) {
        if (s.verified) v++; else u++;
      }
    }
    el("src-verified-count").textContent = v;
    el("src-unverified-count").textContent = u;
    el("data-updated").textContent = meta.last_updated || "unknown";
    const host = el("domain-lists");
    if (!classification) {
      host.innerHTML = `<p class="status">Classification list unavailable here; ` +
        `see <a href="https://github.com/PaulinoTech1/Flock-Off/blob/main/scripts/classify_sources.py">` +
        `scripts/classify_sources.py</a> for the full domain list.</p>`;
      return;
    }
    const news = classification.verified_news || [];
    const primary = classification.verified_primary || [];
    const leads = (classification.unverified_listed || [])
      .concat(classification.unverified_unlisted_seen || []);
    el("domain-count").textContent =
      news.length + primary.length + leads.length;
    const col = (title, items) =>
      `<div><h4>${title} (${items.length})</h4><ul class="domain-list">` +
      items.map((d) => `<li>${esc(d)}</li>`).join("") + `</ul></div>`;
    host.innerHTML = `<div class="domain-cols">` +
      col("Verified: established news outlets", news) +
      col("Verified: primary and official records", primary) +
      col("Not counted: leads only", leads) +
      `</div>`;
  }

  function esc(s) {
    return String(s ?? "").replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  return { init };
})();
