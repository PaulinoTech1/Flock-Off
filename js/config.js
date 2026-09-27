/* Flock-Off configuration: curated tool directory.
 * Everything here is a public, unauthenticated endpoint. No keys, no accounts.
 */
"use strict";

const FLOCKOFF_CONFIG = {
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
    {
      name: "ALPR Watch",
      url: "https://alprwatch.org",
      tag: "Offline avoidance navigation",
      desc: "ALPR-avoiding navigation with downloadable offline data packages (CoMaps-compatible) plus a suspected-locations map. Built largely on DeFlock's dataset, packaged for offline use.",
    },
  ],
};
