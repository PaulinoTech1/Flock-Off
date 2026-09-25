/* Flock-Off configuration: endpoints and tunables.
 * Everything here is a public, unauthenticated endpoint. No keys, no accounts.
 */
"use strict";

const FLOCKOFF_CONFIG = {
  // Primary camera data: OpenStreetMap nodes tagged as ALPR (DeFlock's source).
  overpassUrl: "https://overpass-api.de/api/interpreter",
  // Secondary bulk source: FlockHopper/DeFlock OSM-derived GeoJSON feed.
  // Updated daily. Tens of MB for the full US file; use regional slices when offered.
  bulkFeeds: {
    us: "https://data.dontgetflocked.com/cameras.geojson.gz",
    ca: "https://data.dontgetflocked.com/cameras-ca.geojson.gz",
  },
  // Routing (demo server; self-host OSRM for production use).
  osrmUrl: "https://router.project-osrm.org/route/v1/driving",
  // Geocoding (Nominatim usage policy: max 1 req/s, no heavy use).
  nominatimUrl: "https://nominatim.openstreetmap.org/search",

  // Map
  defaultCenter: [42.2626, -71.8023], // Worcester, MA
  defaultZoom: 12,
  cameraFetchRadiusKm: 8,   // Overpass bbox half-size around map center
  maxBboxDegrees: 0.6,      // Overpass guard: refuse larger boxes

  // Radar
  radarWarnM: 150,
  radarAlertM: 75,
  radarCacheKm: 10,

  // Route exposure analysis
  routeExposureM: 60, // camera within this distance of the route counts as "on route"

  // Curated directory of existing anti-Flock tools (Tools tab)
  directory: [
    {
      name: "DeFlock",
      url: "https://deflock.org",
      tag: "Camera map + avoidance routing",
      desc: "The largest crowdsourced ALPR map (~133k cameras, OpenStreetMap-based). Search by address/ZIP, get privacy-optimized routes, contribute sightings. EFF-backed.",
    },
    {
      name: "FlockHopper",
      url: "https://dontgetflocked.com",
      tag: "Route planner",
      desc: "Plan car, bike, and walking routes that minimize ALPR exposure. GPX export, all processing local. Open source with a public GeoJSON camera feed.",
    },
    {
      name: "Have I Been Flocked",
      url: "https://haveibeenflocked.com",
      tag: "Audit-log lookup",
      desc: "Enter your plate to see if it appears in FOIA-obtained Flock search audit logs (~4.6M plates, ~242M searches). Searches are not stored.",
    },
    {
      name: "Eyes on Flock",
      url: "https://eyesonflock.com",
      tag: "Transparency stats",
      desc: "Per-city stats scraped from Flock transparency portals: camera counts, vehicles captured, searches, hotlist hits, data-sharing. CC BY-SA 4.0 data.",
    },
    {
      name: "SparrowMap",
      url: "https://map.sparrowmap.com",
      tag: "Counter-surveillance network",
      desc: "Volunteer cameras track government vehicles; private plates are destroyed on-device. Drive-mode alerts warn of nearby ALPR cameras like a radar detector.",
    },
    {
      name: "Flock-You firmware",
      url: "https://github.com/colonelpanichacks/flock-you",
      tag: "Hardware detector",
      desc: "Open-source ESP32 firmware that passively detects Flock cameras by their WiFi/BLE emissions. Receive-only; 1,100+ stars. Requires a ~$20 ESP32 board.",
    },
  ],
};
