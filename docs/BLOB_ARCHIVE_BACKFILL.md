# Blob archive backfill — 2026-10-04 stall incident

## Symptom
The source-snapshot blob store sat at **4 of 728 sources** for weeks while the
hourly `flock-off-archive-backfill` cron fired the GitHub Actions
"Source snapshot archiver" workflow (runs #26–#46 on 2026-10-04, all
conclusion=failure). Every run uploaded **zero** snapshots and failed the
"Verify blob uploads" step with `E_VERIFY_FAIL`.

## Root cause
`scripts/source_fingerprints.py::refresh()` marked **every** source with
`fetch_status != "ok"` as needing refresh on every run:

```python
needs = fp.get("fetch_status") != "ok" or age > max_age_days
```

Non-ok statuses (blocked/error/non_html/thin) are recorded by
`fingerprint_url()` but never age out. Citation order is stable, so each
batch of 25 re-fetched the same dead sources: 17 bot-blocked, 1 error,
5 non-HTML, 2 thin. All re-failed, all were re-recorded with today's date,
and the batch never advanced past them. The quarantine the run logs kept
implying ("selector re-picking the same 25 unarchivable sources") was never
implemented — the code just had no concept of "leave this one alone."

An earlier diagnosis blamed a missing `ARCHIVE_BLOB_READ_WRITE_TOKEN`; the
19:06 EDT run confirmed the token is present in the workflow environment.
The token was never the problem. The selector was.

## Fix (2026-10-04)
Non-ok fingerprints are now **quarantined** instead of retried every run:

- `fingerprint_url()` stamps `retry_after` on non-ok records.
- `refresh()` skips records still inside their quarantine window.
- Quarantine lengths are config in `config/flock-off.yaml`
  (`fingerprints.quarantine_days`): blocked 30d, error 7d,
  non_html 30d, thin 30d.
- Records written before this change have no `retry_after` and are retried
  once, then quarantined — so the first post-fix run re-fails the dead batch
  and quarantines it, and the second run advances.

Bot-blocked pages remain "unverifiable, never evaded": quarantine only
spaces out honest retries, it does not bypass the block.

## What to expect after deploy
- Next hourly run: re-fails the same ~25 dead sources (once), stamps
  quarantines, uploads 0. `E_VERIFY_FAIL` fires again.
- The run after: batch advances to the next 25 sources; real uploads resume.
- Expect upload counts to climb steadily, not instantly: most sources are
  reachable, the dead set is just front-loaded in citation order.

## Standing rule
A backfill that makes zero progress for N consecutive runs must page the
run logs' root-cause line, not the token. The 4 pre-existing snapshots date
from the build/test phase; none came from the hourly backfill.
