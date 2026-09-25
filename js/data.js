/* Camera data layer.
 * Primary: Overpass API queries for OSM nodes tagged surveillance:type=ALPR
 * (the same underlying data DeFlock renders). All client-side; nothing is
 * uploaded. Camera data is ODbL-licensed via OpenStreetMap (see docs/DATA_SOURCES.md).
 */
"use strict";

const CameraData = (() => {
  const cfg = () => FLOCKOFF_CONFIG;

  function normalizeNode(el) {
    const tags = el.tags || {};
    const blob = [tags.brand, tags.operator, tags.manufacturer, tags.name, tags.ref]
      .filter(Boolean)
      .join(" ");
    const isFlock = /flock/i.test(blob);
    return {
      id: `osm-${el.type || "node"}-${el.id}`,
      lat: el.lat,
      lon: el.lon,
      brand: tags.brand || tags.manufacturer || (isFlock ? "Flock Safety" : "Unknown"),
      operator: tags.operator || "Unknown",
      ref: tags.ref || "",
      isFlock,
      source: "OpenStreetMap",
    };
  }

  function bboxAround(lat, lon, km) {
    // Rough equirectangular box; fine for fetch scoping.
    const dLat = km / 111.32;
    const dLon = km / (111.32 * Math.cos((lat * Math.PI) / 180));
    return { s: lat - dLat, w: lon - dLon, n: lat + dLat, e: lon + dLon };
  }

  function overpassQuery(bbox) {
    const { s, w, n, e } = bbox;
    return `[out:json][timeout:30];
(
  node["surveillance:type"="ALPR"](${s},${w},${n},${e});
  node["surveillance"="ALPR"](${s},${w},${n},${e});
);
out tags center;`;
  }

  async function fetchInBbox(bbox) {
    const span = Math.max(bbox.n - bbox.s, bbox.e - bbox.w);
    if (span > cfg().maxBboxDegrees) {
      throw new Error("area too large: zoom in or shrink the search radius");
    }
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 35000);
    try {
      const res = await fetch(cfg().overpassUrl, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: "data=" + encodeURIComponent(overpassQuery(bbox)),
        signal: ctrl.signal,
      });
      if (!res.ok) throw new Error(`Overpass HTTP ${res.status}`);
      const json = await res.json();
      return (json.elements || []).map(normalizeNode);
    } finally {
      clearTimeout(timer);
    }
  }

  async function fetchAround(lat, lon, km) {
    return fetchInBbox(bboxAround(lat, lon, km));
  }

  // Haversine distance in meters.
  function distM(aLat, aLon, bLat, bLon) {
    const R = 6371000;
    const dLat = ((bLat - aLat) * Math.PI) / 180;
    const dLon = ((bLon - aLon) * Math.PI) / 180;
    const s1 = Math.sin(dLat / 2);
    const s2 = Math.sin(dLon / 2);
    const a =
      s1 * s1 +
      Math.cos((aLat * Math.PI) / 180) * Math.cos((bLat * Math.PI) / 180) * s2 * s2;
    return 2 * R * Math.asin(Math.sqrt(a));
  }

  // Distance from point P to segment AB, in meters (equirectangular projection).
  function pointToSegmentM(pLat, pLon, aLat, aLon, bLat, bLon) {
    const kx = 111320 * Math.cos(((aLat + bLat) / 2 * Math.PI) / 180);
    const ky = 110540;
    const px = pLon * kx, py = pLat * ky;
    const ax = aLon * kx, ay = aLat * ky;
    const bx = bLon * kx, by = bLat * ky;
    const dx = bx - ax, dy = by - ay;
    const len2 = dx * dx + dy * dy;
    let t = len2 === 0 ? 0 : ((px - ax) * dx + (py - ay) * dy) / len2;
    t = Math.max(0, Math.min(1, t));
    const cx = ax + t * dx, cy = ay + t * dy;
    return Math.hypot(px - cx, py - cy);
  }

  function minDistanceToRoute(cam, coords) {
    // coords: [[lon, lat], ...] GeoJSON linestring
    let best = Infinity;
    for (let i = 0; i < coords.length - 1; i++) {
      const d = pointToSegmentM(
        cam.lat, cam.lon,
        coords[i][1], coords[i][0],
        coords[i + 1][1], coords[i + 1][0]
      );
      if (d < best) best = d;
    }
    return best;
  }

  async function geocode(text) {
    const url =
      cfg().nominatimUrl +
      "?format=jsonv2&limit=1&countrycodes=us&addressdetails=0&q=" +
      encodeURIComponent(text);
    const res = await fetch(url, { headers: { Accept: "application/json" } });
    if (!res.ok) throw new Error(`geocode HTTP ${res.status}`);
    const arr = await res.json();
    if (!arr.length) throw new Error("no match found");
    return { lat: parseFloat(arr[0].lat), lon: parseFloat(arr[0].lon), label: arr[0].display_name };
  }

  async function getRoute(from, to) {
    const url =
      `${cfg().osrmUrl}/${from.lon},${from.lat};${to.lon},${to.lat}` +
      "?overview=full&geometries=geojson";
    const res = await fetch(url);
    if (!res.ok) throw new Error(`routing HTTP ${res.status}`);
    const json = await res.json();
    if (json.code !== "Ok" || !json.routes?.length) throw new Error("no route found");
    return json.routes[0]; // {geometry:{coordinates}, distance, duration}
  }

  return {
    fetchInBbox,
    fetchAround,
    bboxAround,
    distM,
    minDistanceToRoute,
    geocode,
    getRoute,
  };
})();
