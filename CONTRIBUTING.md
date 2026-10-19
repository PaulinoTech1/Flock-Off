# Contributing

Flock-Off stays small on purpose: static tracker page with a Python pre-render build (no framework build), minimal serverless endpoints only for the tip quarantine/history. Keep it that way.

## Ground rules

1. **Tiny server surface.** The only backend is the tip quarantine and public history endpoints. If a feature needs more server, it doesn't belong here.
2. **No tracking, ever.** No analytics, no cookies, no fingerprinting, no third-party scripts. All assets are served from the site's own origin.
3. **Data stays upstream.** Camera corrections go to DeFlock/OpenStreetMap, not into this repo. We consume; we don't fork the dataset.
4. **Accessibility is a feature.** Every UI change must work with keyboard only, screen reader labels where it matters, and `prefers-reduced-motion` respected.
5. **Honest copy.** Never imply coverage is complete. "Known cameras" not "cameras." "No known cameras nearby" not "all clear."
6. **Evidence tiers for data.** Terminal-status records (cancelled/rejected/expired) show verified (3+ independent verified citations) or pending validation\* (fewer); new source domains must be classified in `config/flock-off.yaml` (section `classify`; unknown domains fail closed to unverified).
7. **No duplicate citations.** Every source carries a `source_key`; run `python3 scripts/flockoff.py keys check` before pushing. The same key twice in one agency's sources is a reject.
8. **Run the test suite before pushing.** `python3 scripts/flockoff.py test` must be green. The suite is modular (`scripts/tests/test_*.py` mirrors the pipeline scripts) and includes regression tests for both bugs found 2026-09-26: write-mode classification must preserve `source_key`, and the YAML domain lists must cover every `verified=true` source. New error codes must be registered in `scripts/flockoff_errors.py`; a meta-test fails the suite if any script emits an unregistered code.

## Local dev

```bash
python3 -m http.server 8080
# open http://localhost:8080
```

Build step: `python3 scripts/vercel_build.py` runs on every Vercel deploy (see `vercel.json`); it pre-renders the tabs into `index.html`, injects the agency-ID allowlist into `api/report.js`, and stages `public/`. For local dev, run the build in a disposable copy, never in the repo root (it rewrites `index.html` and `api/report.js` in place), then serve `public/` and reload.

## What we need

- Better empty states for zero-result filters on the data tabs (plus a Clear filters affordance).
- A service worker for offline reading of the pre-rendered pages.
- i18n scaffolding (Spanish first).
- Playwright smoke tests against the deployed site on a schedule, alerting on breakage.

(The map tab and its camera-sightings feature were removed, so map-specific tooling is out of scope; camera sightings go to DeFlock upstream. The vendored Leaflet assets are currently unused.)

## Pull requests

Small, focused, with a before/after note on what changed for a first-time visitor on a phone. CI runs CodeQL (security-extended, JavaScript + Python) on push, pull request, and a weekly schedule, plus a weekly source-snapshot archiver workflow. The release gate runs the Python test suite before every push; keep it green (`python3 scripts/flockoff.py test`). Not yet in CI: JSON schema validation for `data/agencies.json`, HTML validation, JS syntax checks.
