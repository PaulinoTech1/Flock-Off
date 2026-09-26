# Error codes

The maintenance pipeline (`scripts/flockoff.py` and the scripts it drives)
reports failures with stable, greppable codes instead of free-text. Prefixes:

- `E_*` — error. Something is broken; a human must intervene.
- `W_*` — warning. The run completed degraded; review when convenient.
- `I_*` — informational. A triage action item, not a failure.

Every code below names the emitting step, what it means, and the exact
remediation. When a code appears in a weekly monitor issue, do what the
**Fix** line says.

## Config

### E_DEP_MISSING
PyYAML is not installed in the environment running the scripts.
**Fix:** `pip install -r scripts/requirements.txt`

### E_CFG_MISSING
`config/flock-off.yaml` was not found at the resolved path. The loader checks
`--config`, then `FLOCKOFF_CONFIG`, then `<repo>/config/flock-off.yaml`.
**Fix:** restore the file from git (`git checkout -- config/flock-off.yaml` or
re-clone). If you moved it deliberately, set `FLOCKOFF_CONFIG`.

### E_CFG_INVALID
The config parsed but failed validation. The message names the exact dotted
key, the expected type, and the violated constraint.
**Fix:** edit the named key to satisfy the constraint and rerun. Do not
silence the check; it exists so a typo'd threshold can never silently drive
the pipeline.

### E_CFG_VERSION
`config_version` in the file does not match the loader. This means the schema
changed under a stale config.
**Fix:** diff your config against `main`'s copy and migrate the changed keys.

## Dataset and fingerprints inputs

### E_DS_FETCH
The weekly monitor could not download `data/agencies.json` from GitHub raw.
**Fix:** check network connectivity and https://www.githubstatus.com, then
rerun. All dataset sections are skipped for that run.

### E_DS_PARSE
The downloaded dataset is not valid JSON. This can happen if a push landed
mid-run.
**Fix:** validate locally (`python3 -m json.tool data/agencies.json`). If the
local file is fine, wait for the next push to settle and rerun.

### E_FP_FETCH
`data/source_fingerprints.json` could not be downloaded. Fingerprint sections
(duplicate detection, change probe) are skipped for that run.
**Fix:** same as E_DS_FETCH.

### E_FP_PARSE
The fingerprints file is corrupt.
**Fix:** regenerate it: `python3 scripts/flockoff.py fingerprints refresh`,
review the diff, push.

## Layer 1: source keys

### E_KEY_MISSING
A citation has no `source_key` field.
**Fix:** `python3 scripts/flockoff.py keys backfill`, review the diff, push.

### E_KEY_STALE
A citation's `source_key` no longer matches `canonical_url(url)` — the URL
was edited without re-keying.
**Fix:** same as E_KEY_MISSING.

### E_KEY_DUP
Two citations within one agency resolve to the same `source_key`: the same
article cited twice.
**Fix:** remove the weaker duplicate, keep the stronger citation, rerun
`keys check`.

### E_KEY_BADURL
A source URL uses a scheme other than http/https.
**Fix:** correct the URL in `data/agencies.json`.

## Upstream discovery feeds

### W_UPSTREAM_FF
The Finding Flock cancellation-tracker check failed (fetch or parse).
**Fix:** manually spot-check
https://www.findingflock.com/learn/flock-contract-cancellations once this
week. The failure is reported under Monitor health, never fatal.

### W_UPSTREAM_ATLAS
The EFF Atlas of Surveillance CSV check failed.
**Fix:** manually spot-check
https://www.atlasofsurveillance.org/download.csv?vendor=Flock+Safety once this
week.

## Layers 2/3: fingerprints

### W_FP_MISSING_KEYS
Citations exist with no fingerprint entry (new citations, or the baseline
predates them).
**Fix:** `python3 scripts/flockoff.py fingerprints refresh` (fetches only
missing/stale keys), review, push.

### W_PROBE_BLOCKED
The weekly change probe hit bot-blocked pages. Blocked pages are unverifiable
by design: recorded, excluded from content comparison, never evaded.
**Fix:** none required. This is the system working as intended.

### W_PROBE_ERROR
The weekly change probe hit transient fetch errors (timeouts, DNS, 5xx).
**Fix:** none required. The probe rotates deterministically, so missed
citations are retried on a later week automatically.

## Informational triage items

### I_DUP_PAIR
Simhash comparison flagged a near-duplicate source pair.
**Fix:** human review. Same-agency pairs are removal candidates. Cross-agency
pairs are informational (often template boilerplate, not real duplication).
Nothing auto-merges, ever.

### I_SOURCE_CHANGED
A cited article's content changed materially (simhash distance or length
delta) since the fingerprint baseline.
**Fix:** re-verify the cited claim against the live page before relying on
the citation. Do not auto-update the baseline; it advances only via a
reviewed `fingerprints refresh`.
