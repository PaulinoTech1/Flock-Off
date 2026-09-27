/* Map tab: Leaflet map of nearby ALPR cameras.
 * Data: Overpass (OSM). Pins colored by vendor; popup shows what is known.
 */
"use strict";

const MapTab = (() => {
  let map = null;
  let layer = null;
  let meMarker = null;
  let lastFetch = 0;
  let pending = false;

  function pinColor(cam) {
    if (cam.isFlock) return "#e5484d"; // Flock Safety
    if (cam.brand && cam.brand !== "Unknown") return "#f5a524"; // other vendor
    return "#8e8e93"; // unidentified ALPR
  }

  function popupHtml(cam) {
    const rows = [
      ["Vendor", escapeHtml(cam.brand)],
      ["Operator", escapeHtml(cam.operator)],
    ];
    if (cam.ref) rows.push(["Ref", escapeHtml(cam.ref)]);
    rows.push(["Source", "OpenStreetMap (ODbL)"]);
    return (
      `<strong>${cam.isFlock ? "Flock Safety" : "ALPR"} camera</strong><br>` +
      rows.map(([k, v]) => `${k}: ${v}`).join("<br>") +
      `<br><a href="https://deflock.org" target="_blank" rel="noopener noreferrer">Report / correct on DeFlock</a>`
    );
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
    );
  }

  function init() {
    if (!document.getElementById("map")) return; // map tab not present
    const cfg = FLOCKOFF_CONFIG;
    map = L.map("map", { zoomControl: true }).setView(cfg.defaultCenter, cfg.defaultZoom);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors (ODbL). Camera data: OSM + DeFlock community.',
    }).addTo(map);
    layer = L.layerGroup().addTo(map);

    map.on("moveend", () => scheduleFetch());
    document.getElementById("locate-btn").addEventListener("click", locate);
    document.getElementById("refresh-btn").addEventListener("click", () => fetchNow(true));
    scheduleFetch();
  }

  function scheduleFetch() {
    const now = Date.now();
    if (pending || now - lastFetch < 4000) return;
    pending = true;
    setTimeout(() => { pending = false; fetchNow(false); }, 1200);
  }

  async function fetchNow(force) {
    const status = document.getElementById("map-status");
    const c = map.getCenter();
    status.textContent = "Loading cameras near map center...";
    try {
      const res = await CameraData.fetchAround(
        c.lat, c.lng, FLOCKOFF_CONFIG.cameraFetchRadiusKm
      );
      lastFetch = Date.now();
      render(res.cams);
      const n = res.cams.length;
      const base =
        `${n} camera${n === 1 ? "" : "s"} in view. ` +
        "Crowdsourced data: missing cameras are expected, wrong ones should be corrected on DeFlock.";
      status.textContent = res.live
        ? base
        : `Live camera data unavailable (${res.error || "network error"}). ` +
          `Showing last successful snapshot from ${res.cachedAt || "an earlier visit"}; ` +
          `it may be out of date. ` + base;
    } catch (err) {
      status.textContent =
        `Could not load camera data (${err.message}). No cached snapshot for this area yet. ` +
        "Tiles still work; try Refresh, or pan to an area you have loaded before.";
    }
  }

  function render(cams) {
    layer.clearLayers();
    for (const cam of cams) {
      L.circleMarker([cam.lat, cam.lon], {
        radius: 7,
        color: pinColor(cam),
        fillColor: pinColor(cam),
        fillOpacity: 0.75,
        weight: 2,
      })
        .bindPopup(popupHtml(cam))
        .addTo(layer);
    }
  }

  function locate() {
    const status = document.getElementById("map-status");
    if (!navigator.geolocation) {
      status.textContent = "Geolocation is not available in this browser.";
      return;
    }
    status.textContent = "Locating...";
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude, longitude } = pos.coords;
        map.setView([latitude, longitude], 15);
        if (meMarker) map.removeLayer(meMarker);
        meMarker = L.circleMarker([latitude, longitude], {
          radius: 6, color: "#0a84ff", fillColor: "#0a84ff", fillOpacity: 0.9,
        })
          .bindPopup("You are here (approximate). Your location never leaves this device.")
          .addTo(map);
        fetchNow(true);
      },
      () => { status.textContent = "Location denied or unavailable. Pan the map manually instead."; },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  return { init };
})();
