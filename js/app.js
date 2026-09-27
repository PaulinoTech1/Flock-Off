/* App shell: tab navigation (hash-routed), tool directory rendering, footer year. */
"use strict";

// Global error trap: nothing fails silently. Unhandled errors and rejected
// promises are logged with a code so they show up in the console and in any
// error-monitoring the maintainer wires up later.
window.addEventListener("error", (e) => {
  console.error("[CLIENT_UNHANDLED_001]", e.message, "at", e.filename + ":" + e.lineno);
});
window.addEventListener("unhandledrejection", (e) => {
  console.error("[CLIENT_UNHANDLED_002]", e.reason);
});

const App = (() => {
  const TABS = ["tracker", "sources", "tools", "learn", "legal"];

  function show(name) {
    if (!TABS.includes(name)) name = "tracker";
    for (const t of TABS) {
      const panel = document.getElementById(`tab-${t}`);
      if (panel) panel.hidden = t !== name;
      const btn = document.getElementById(`nav-${t}`);
      if (btn) {
        btn.setAttribute("aria-selected", String(t === name));
        btn.classList.toggle("active", t === name);
        // Roving tabindex: only the selected tab is in the Tab order.
        btn.tabIndex = t === name ? 0 : -1;
      }
    }
    if (location.hash !== `#${name}`) history.replaceState(null, "", `#${name}`);
  }

  function renderDirectory() {
    const grid = document.getElementById("tools-grid");
    for (const tool of FLOCKOFF_CONFIG.directory) {
      const card = document.createElement("article");
      card.className = "tool-card";
      const h = document.createElement("h3");
      const a = document.createElement("a");
      a.href = tool.url;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.textContent = tool.name;
      h.appendChild(a);
      const tag = document.createElement("p");
      tag.className = "tool-tag";
      tag.textContent = tool.tag;
      const desc = document.createElement("p");
      desc.textContent = tool.desc;
      card.append(h, tag, desc);
      grid.appendChild(card);
    }
  }

  // Data-integrity check: recompute SHA-256(agencies.json) in-browser and
  // compare against the release manifest. Honest about scope: proves the
  // file matches the published release, not that the origin is clean.
  async function verifyIntegrity() {
    const status = document.getElementById("verify-integrity-status");
    status.textContent = "Fetching dataset and manifest…";
    try {
      const [dataRes, manRes] = await Promise.all([
        fetch("data/agencies.json"),
        fetch("data/integrity/manifest.json"),
      ]);
      if (!dataRes.ok) throw new Error(`dataset HTTP ${dataRes.status}`);
      if (!manRes.ok) throw new Error(`manifest HTTP ${manRes.status}`);
      const buf = await dataRes.arrayBuffer();
      const digest = await crypto.subtle.digest("SHA-256", buf);
      const hex = [...new Uint8Array(digest)]
        .map((b) => b.toString(16).padStart(2, "0")).join("");
      const man = await manRes.json();
      const match = hex === man.agencies_sha256;
      const sig = man.signature
        ? "Signed by the maintainer (signature present; verify against the published key)."
        : "Not signed with the maintainer key yet (unsigned release).";
      status.textContent = match
        ? `✓ Hash matches the release manifest (${hex.slice(0, 16)}…). Released ${man.timestamp || "unknown time"} at commit ${(man.commit || "unknown").slice(0, 12)}. ${sig}`
        : `✗ HASH MISMATCH: computed ${hex.slice(0, 16)}… but the manifest says ${String(man.agencies_sha256).slice(0, 16)}…. Treat this dataset as suspect and open an issue.`;
    } catch (err) {
      console.error("[CLIENT_INTEGRITY_001]", err);
      status.textContent = `Could not verify (${err.message}). [CLIENT_INTEGRITY_001] Check data/integrity/manifest.json exists and is reachable.`;
    }
  }
  // Deep links: "#learn-privacy" opens the Learn tab, then scrolls to the anchor.
  function showFromHash() {
    const raw = location.hash.replace("#", "") || "tracker";
    const tab = TABS.includes(raw)
      ? raw
      : TABS.find((t) => raw.startsWith(t + "-")) || raw;
    show(tab);
    if (raw !== tab) {
      const el = document.getElementById(raw);
      if (el) el.scrollIntoView({ block: "start" });
    }
  }

  function init() {
    for (const t of TABS) {
      document.getElementById(`nav-${t}`).addEventListener("click", () => show(t));
    }
    // ARIA tabs keyboard pattern: arrows move between tabs, Home/End jump.
    document.querySelector("nav.tabs").addEventListener("keydown", (e) => {
      const id = document.activeElement && document.activeElement.id;
      const i = id ? TABS.indexOf(id.replace("nav-", "")) : -1;
      if (i === -1) return;
      let j = null;
      if (e.key === "ArrowRight") j = (i + 1) % TABS.length;
      else if (e.key === "ArrowLeft") j = (i - 1 + TABS.length) % TABS.length;
      else if (e.key === "Home") j = 0;
      else if (e.key === "End") j = TABS.length - 1;
      if (j !== null) {
        e.preventDefault();
        show(TABS[j]);
        document.getElementById(`nav-${TABS[j]}`).focus();
      }
    });
    window.addEventListener("hashchange", showFromHash);
    renderDirectory();
    const vib = document.getElementById("verify-integrity-btn");
    if (vib) vib.addEventListener("click", verifyIntegrity);
    document.getElementById("year").textContent = new Date().getFullYear();
    showFromHash();
    TrackerTab.init();
    SourcesTab.init();
    MapTab.init();
  }

  return { init };
})();

document.addEventListener("DOMContentLoaded", App.init);
