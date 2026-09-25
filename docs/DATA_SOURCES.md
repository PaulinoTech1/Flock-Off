# Data sources

Flock-Off has no backend and no database. Every dataset below is fetched client-side from a public endpoint. This page records what we use, why, and what license/attribution each requires.

## Camera locations

| Source | Endpoint | License | Notes |
|---|---|---|---|
| OpenStreetMap (primary) | `https://overpass-api.de/api/interpreter`, nodes with `surveillance:type=ALPR` or `surveillance=ALPR` | ODbL © OpenStreetMap contributors | Same underlying data DeFlock renders. Crowdsourced; incomplete by design. |
| FlockHopper/DeFlock bulk feed (secondary) | `https://data.dontgetflocked.com/cameras.geojson.gz` (full US; regional slices exist) | ODbL (OSM-derived) | Tens of MB for the US file; suitable for offline/preload builds, not live fetch. Verified live 2026-09-25. |

**Attribution requirement:** any public deployment must credit "© OpenStreetMap contributors" with a link to openstreetmap.org/copyright. The app footer and map tiles do this.

**Corrections:** wrong pins get fixed upstream. Report them on [DeFlock](https://deflock.org) or tag directly in OSM; do not fork the dataset.

## Map tiles

OpenStreetMap standard tiles (`tile.openstreetmap.org`). Tile usage policy applies: no heavy scraping; this app's usage is normal interactive browsing.

## Geocoding and routing

| Service | Endpoint | Policy |
|---|---|---|
| Nominatim | `nominatim.openstreetmap.org/search` | Max 1 req/s; the app throttles geocoding. No bulk use. |
| OSRM demo server | `router.project-osrm.org` | Demo use only. For any serious traffic, self-host OSRM (see ROADMAP). |

## What we deliberately do not use

- **Flock's own APIs or transparency portals** scraped live: Eyes on Flock already mirrors portal stats under CC BY-SA 4.0; link there instead of re-scraping.
- **Have I Been Flocked's audit-log index**: plate lookups stay on their site; Flock-Off never handles plate numbers.
