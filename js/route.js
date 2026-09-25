/* Route tab: ALPR exposure analysis for a trip.
 * Geocode origin/destination (Nominatim), route (OSRM), fetch cameras in the
 * route bbox (Overpass), then flag cameras within FLOCKOFF_CONFIG.routeExposureM
 * of the path. This is exposure *analysis*, not avoidance routing; for turn-by-
 * turn avoidance use DeFlock or FlockHopper (linked in Tools).
 */
"use strict";

const RouteTab = (() => {
  let map = null;
  let layer = null;
  let lastGeocode = 0;

  function el(id) { return document.getElementById(id); }
  function setStatus(msg) { el("route-status").textContent = msg; }

  function init() {
    map = L.map("route-map", { zoomControl: true }).setView(FLOCKOFF_CONFIG.defaultCenter, 10);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors (ODbL).',
    }).addTo(map);
    layer = L.layerGroup().addTo(map);
    el("route-go").addEventListener("click", analyze);
    for (const id of ["route-from", "route-to"]) {
      el(id).addEventListener("keydown", (e) => { if (e.key === "Enter") analyze(); });
    }
  }

  async function geocodeThrottled(text) {
    // Nominatim usage policy: max 1 request/second.
    const wait = Math.max(0, 1100 - (Date.now() - lastGeocode));
    if (wait) await new Promise((r) => setTimeout(r, wait));
    lastGeocode = Date.now();
    return CameraData.geocode(text);
  }

  async function analyze() {
    const fromText = el("route-from").value.trim();
    const toText = el("route-to").value.trim();
    if (!fromText || !toText) {
      setStatus("Enter both an origin and a destination (address, place, or ZIP).");
      return;
    }
    el("route-go").disabled = true;
    layer.clearLayers();
    try {
      setStatus("Geocoding origin...");
      const from = await geocodeThrottled(fromText);
      setStatus("Geocoding destination...");
      const to = await geocodeThrottled(toText);
      setStatus("Routing...");
      const route = await CameraData.getRoute(from, to);
      const coords = route.geometry.coordinates;

      // Route bbox -> one Overpass query.
      const lats = coords.map((c) => c[1]);
      const lons = coords.map((c) => c[0]);
      const pad = 0.02;
      const bbox = {
        s: Math.min(...lats) - pad, w: Math.min(...lons) - pad,
        n: Math.max(...lats) + pad, e: Math.max(...lons) + pad,
      };
      setStatus("Loading cameras along the route...");
      const cams = await CameraData.fetchInBbox(bbox);

      const threshold = FLOCKOFF_CONFIG.routeExposureM;
      const exposed = [];
      for (const cam of cams) {
        const d = CameraData.minDistanceToRoute(cam, coords);
        if (d <= threshold) exposed.push({ cam, d });
      }
      exposed.sort((a, b) => a.d - b.d);

      // Draw route + exposed cameras.
      const latlngs = coords.map((c) => [c[1], c[0]]);
      L.polyline(latlngs, { color: "#0a84ff", weight: 5 }).addTo(layer);
      for (const { cam, d } of exposed) {
        L.circleMarker([cam.lat, cam.lon], {
          radius: 7, color: "#e5484d", fillColor: "#e5484d", fillOpacity: 0.8, weight: 2,
        })
          .bindPopup(
            `<strong>${cam.isFlock ? "Flock Safety" : "ALPR"} camera</strong><br>` +
            `~${Math.round(d)} m from route<br>Operator: ${cam.operator}`
          )
          .addTo(layer);
      }
      map.fitBounds(L.polyline(latlngs).getBounds().pad(0.15));

      const km = (route.distance / 1000).toFixed(1);
      const min = Math.round(route.duration / 60);
      el("route-summary").hidden = false;
      el("route-summary").innerHTML =
        `<strong>${exposed.length}</strong> known camera${exposed.length === 1 ? "" : "s"} ` +
        `within ${threshold} m of this ${km} km (~${min} min) route. ` +
        `Data is crowdsourced and incomplete: treat this as a lower bound, not a clearance. ` +
        `For avoidance routing, use <a href="https://deflock.org" target="_blank" rel="noopener noreferrer">DeFlock</a> ` +
        `or <a href="https://dontgetflocked.com" target="_blank" rel="noopener noreferrer">FlockHopper</a>.`;
      const list = el("route-list");
      list.innerHTML = "";
      for (const { cam, d } of exposed.slice(0, 50)) {
        const li = document.createElement("li");
        li.textContent =
          `~${Math.round(d)} m off route: ${cam.isFlock ? "Flock Safety" : cam.brand} ` +
          `(${cam.operator}) at ${cam.lat.toFixed(5)}, ${cam.lon.toFixed(5)}`;
        list.appendChild(li);
      }
      setStatus(exposed.length ? "Analysis complete." : "Analysis complete. No known cameras within range of this route.");
    } catch (err) {
      setStatus(`Route analysis failed: ${err.message}`);
    } finally {
      el("route-go").disabled = false;
    }
  }

  return { init };
})();
