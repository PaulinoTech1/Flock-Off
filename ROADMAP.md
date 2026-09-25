# Roadmap

The tracker is the product. Everything below serves it.

## Next

- [ ] **Fill the dataset** — East Coast agencies north to south (ME, NH, VT, MA, RI, CT, NY, NJ, PA, DE, MD, DC, VA, NC, SC, GA, FL). Renewal dates are the highest-value field.
- [ ] **Renewal alerts** — optional email/RSS feed of renewals coming up in 90 days per state. (Requires a tiny backend or a scheduled static rebuild; decide explicitly.)
- [ ] **Cancellation playbook pages** — per-win writeups: what the vote was, what arguments worked, link the council packet. Turns anecdotes into a replicable playbook.
- [ ] **Eyes on Flock cross-check** — reconcile tracked agencies against transparency-portal camera counts; flag under-researched cities.
- [ ] **Vendored Leaflet** — ship Leaflet from the repo instead of unpkg.
- [ ] **CI** — JSON schema validation for `data/agencies.json`, HTML validation, JS syntax check. (Workflow files must be added with a workflow-scoped token.)

## Later

- [ ] **Expand westward** — Midwest, South, West, in that order of organizer demand.
- [ ] **FOIA kit** — state-by-state records-request generators feeding contract discovery (the pipeline behind Have I Been Flocked's audit logs).
- [ ] **i18n** — Spanish first.

## Never

- User accounts, plate-number handling, officer/vehicle tracking, server-side storage of visitor data. See `docs/THREAT_MODEL.md` and `docs/METHODOLOGY.md`.
