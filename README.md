# Flock-Off

**The accessible way to see, avoid, and push back on ALPR surveillance.**

Flock Safety has put 120,000+ automated license plate reader cameras across the US. The tools to fight back exist, but they each demand something: buy and flash an ESP32, install an app, or already know what an ALPR is. Flock-Off is the zero-friction entry point: open the page in any browser and you get a camera map, a radar-detector-style proximity alert, route exposure analysis, a directory of the deeper tools, and what to do next. No install, no account, no tracking.

## Use it

Open `index.html` directly, or serve the directory:

```bash
python3 -m http.server 8080
# http://localhost:8080
```

Deploy anywhere static: GitHub Pages, Vercel, Cloudflare Pages, Netlify. No build step, no backend.

## What it does

| Tab | What | Data |
|---|---|---|
| **Map** | ALPR cameras near the map center or your location | OpenStreetMap via Overpass (DeFlock's source) |
| **Radar** | Audio + banner alert when a known camera is within 150 m / 75 m | Phone GPS + OSM, all local |
| **Route** | Exposure analysis: known cameras within 60 m of a trip | Nominatim + OSRM + Overpass |
| **Tools** | Directory of the existing anti-Flock ecosystem | Curated links |
| **Learn** | Spot cameras, contribute sightings, file records requests | Static content |

## Privacy posture

- No cookies, no analytics, no accounts, no backend. The site cannot track you because there is nowhere for the data to go.
- Geolocation stays on your device. The only network requests are the ones your browser makes to fetch public map/camera/route data (same as loading any map).
- Outbound links use `rel="noopener noreferrer"`.
- See `docs/THREAT_MODEL.md` for the full statement and `docs/DATA_SOURCES.md` for data licenses.

## Data

Camera locations come from OpenStreetMap nodes tagged `surveillance:type=ALPR`, the same underlying data DeFlock renders. It is **crowdsourced and incomplete**: a missing camera is expected. A wrong pin is worse than a missing one, so report corrections on [DeFlock](https://deflock.org). OSM data is © OpenStreetMap contributors, ODbL.

## Scope

Flock-Off is for awareness and lawful civic action: mapping, routing, records requests, public pressure. It is passive and informational. It does not interfere with any system, and the project does not condone touching or disabling cameras.

## Contributing

See `CONTRIBUTING.md`. Good first issues: better empty-state copy for areas with no mapped cameras, vendoring Leaflet instead of CDN, a service worker for offline tiles in a small area.

## Roadmap

See `ROADMAP.md`.

## License

MIT. See `LICENSE`.
