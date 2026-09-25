# Contributing

Flock-Off stays small on purpose: static files, no build, no backend, no dependencies beyond Leaflet via CDN. Keep it that way.

## Ground rules

1. **Client-side only.** If a feature needs a server, it doesn't belong here.
2. **No tracking, ever.** No analytics, no cookies, no fingerprinting, no third-party scripts beyond map tiles and Leaflet.
3. **Data stays upstream.** Camera corrections go to DeFlock/OpenStreetMap, not into this repo. We consume; we don't fork the dataset.
4. **Accessibility is a feature.** Every UI change must work with keyboard only, screen reader labels where it matters, and `prefers-reduced-motion` respected.
5. **Honest copy.** Never imply coverage is complete. "Known cameras" not "cameras." "No known cameras nearby" not "all clear."
6. **Evidence bar for data.** Terminal-status records (cancelled/rejected/expired) need 3+ independent verified citations per `docs/METHODOLOGY.md`; new source domains must be classified in `scripts/classify_sources.py` (unknown domains fail closed to unverified).

## Local dev

```bash
python3 -m http.server 8080
# open http://localhost:8080
```

No build step. Edit, reload.

## What we need

- Better empty states for areas with zero mapped cameras (most of the country).
- Vendored Leaflet (drop the CDN dependency).
- A service worker caching tiles + camera data for a small offline area.
- i18n scaffolding (Spanish first).
- Playwright smoke tests hitting the real Overpass endpoint on a schedule, alerting on breakage.

## Pull requests

Small, focused, with a before/after note on what changed for a first-time visitor on a phone. CI (lint + smoke test) is a planned addition; until then, test in a real mobile browser.
