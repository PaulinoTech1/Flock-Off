/* App shell: tab navigation (hash-routed), tool directory rendering, footer year. */
"use strict";

const App = (() => {
  const TABS = ["map", "radar", "route", "tools", "learn"];

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
    window.addEventListener("hashchange", () =>
      show(location.hash.replace("#", ""))
    );
    renderDirectory();
    document.getElementById("year").textContent = new Date().getFullYear();
    show(location.hash.replace("#", "") || "map");
    MapTab.init();
    RadarTab.init();
    RouteTab.init();
  }

  return { init };
})();

document.addEventListener("DOMContentLoaded", App.init);
