# Roadmap

Ordered by "most accessibility gained per effort." Nothing here requires a backend.

## Next

- [ ] **Vendored Leaflet** — ship Leaflet from the repo instead of unpkg. One less third party, works offline once cached.
- [ ] **Service worker** — cache app shell + tiles + last camera fetch so the map works with spotty signal.
- [ ] **Empty-state copy** — most places have zero mapped cameras. The current "0 cameras" readout undersells the uncertainty; design a state that teaches contribution.
- [ ] **CI** — HTML validation, JS syntax check, and a scheduled smoke test against the real Overpass endpoint. (Workflow files must be added with a workflow-scoped token; see repo notes.)

## Later

- [ ] **Self-hosted routing option** — config flag to point at a personal OSRM instance instead of the demo server.
- [ ] **Eyes on Flock stats panel** — per-city camera/capture/search counts via their CC BY-SA 4.0 API, shown when the map centers on a covered city.
- [ ] **Offline regional packs** — pre-sliced GeoJSON from `data.dontgetflocked.com` for a metro area, selectable in the UI.
- [ ] **i18n** — Spanish first.
- [ ] **"Report" deep link** — one-tap handoff to DeFlock's reporting flow with the map location prefilled.

## Never

- User accounts, plate-number handling, server-side storage, background location tracking. See `docs/THREAT_MODEL.md`.
