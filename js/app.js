/* App shell: tab navigation (hash-routed), tool directory rendering, footer year. */
"use strict";

const App = (() => {
  const TABS = ["tracker", "map", "tools", "learn"];

  function show(name) {
    if (!TABS.includes(name)) name = "map";
    for (const t of TABS) {
      document.getElementById(`tab-${t}`).hidden = t !== name;
      const btn = document.getElementById(`nav-${t}`);
      btn.setAttribute("aria-selected", String(t === name));
      btn.classList.toggle("active", t === name);
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
    window.addEventListener("hashchange", () =>
      show(location.hash.replace("#", ""))
    );
    renderDirectory();
    document.getElementById("year").textContent = new Date().getFullYear();
    show(location.hash.replace("#", "") || "tracker");
    TrackerTab.init();
    MapTab.init();
  }

  return { init };
})();

document.addEventListener("DOMContentLoaded", App.init);
