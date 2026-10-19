# Roadmap

The tracker is the product. Everything below serves it.

## Next

- [x] **Fill the dataset** — USA-wide, expanding westward in 10-state waves. Wave 1 (done 2026-09-26): OH, MI, IN, IL, WI, WV, KY, TN, AL, MS — 80 records added, 151 total, 8 verified-tier terminal claims. Renewal dates are the highest-value field.
- [ ] **Wave 2** — next 10 westward states, same research-then-approval pipeline.
- [ ] **Renewal alerts** — optional email/RSS feed of renewals coming up in 90 days per state. (Requires a tiny backend or a scheduled static rebuild; decide explicitly.)
- [ ] **Cancellation playbook pages** — per-win writeups: what the vote was, what arguments worked, link the council packet. Turns anecdotes into a replicable playbook.
- [ ] **Eyes on Flock cross-check** — reconcile tracked agencies against transparency-portal camera counts; flag under-researched cities.
- [x] **Quality upgrade program** (2026-10-19) — Phases Zero-F: baseline audit, homepage/count honesty, public-output allowlist (the whole repo root was being published), API authorization review, coverage reporting with document classes, UX/accessibility pass, research tooling (CSV export with formula-injection defense, corroboration queue, records-request drafts, case studies), and release-manifest commit stamping. Remaining, maintainer-gated: the document taxonomy refinement (official_statement / policy_document / contract_document classes) proposed in the Phase C report.
- [x] **Leaflet** — the map feature was removed; Leaflet itself was deleted 2026-10-19 (it had still been loading on every page).
- [x] **CI**: CodeQL (security-extended, JavaScript + Python) on push/PR/weekly; weekly source-snapshot archiver. Still open: JSON schema validation for `data/agencies.json`, HTML validation, JS syntax check.

## Later

- [ ] **Expand westward** — Midwest, South, West, in that order of organizer demand.
- [ ] **FOIA kit** — state-by-state records-request generators feeding contract discovery (the pipeline behind Have I Been Flocked's audit logs). First slice shipped 2026-10-19: a per-agency records-request draft generator in the tracker drawer (copy-only, lists the record's missing fields).
- [ ] **i18n** — Spanish first.

## Never

- User accounts, plate-number handling, officer/vehicle tracking, server-side storage of visitor data. See `docs/THREAT_MODEL.md` and `docs/METHODOLOGY.md`.
