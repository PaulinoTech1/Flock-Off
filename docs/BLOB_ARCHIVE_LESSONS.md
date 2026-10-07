# Blob archive backfill: lessons learned (v4 era, 2026-10-06 onward)

Companion to `BLOB_ARCHIVE_BACKFILL.md` (the 2026-10-04 stall). This file
covers the v4 workflow era: how the backfill became what it is, the fixes
that un-stalled it twice, and the failures that taught the standing rules.

## How the project became what it is

**The problem.** The Vercel Blob store hit its 30-day free-tier suspension
(HTTP 403 `store_suspended`), freezing all snapshot uploads. The free tier
also rations advanced operations, so any design that LISTs the store per run
was unaffordable.

**The v4 design** (went live 2026-10-06 ~11:25 EDT on Boss's "let's go
live") is free-tier-safe by construction:

- Zero blob LIST calls per run. Progress is tracked via fingerprint data
  committed to the repo, not by inspecting the store.
- Batch-local upload accounting: each batch counts its own successes from
  its log; no cross-batch store verification.
- Deterministic snapshot paths that overwrite safely, so the old
  `snapshot_exists()` LIST-before-PUT check was removed (one advanced
  operation saved per snapshot).
- The persist step commits `data/source_fingerprints.json` with
  `(archived_total=N)` in the commit message, making progress greppable
  from git history without any blob API calls.
- Honest failure: attempted uploads with zero successes make the run red.
- Explicit `permissions: contents: write` on the workflow.

**Pro as a bridge.** Team `boss-projects-5a103493` was upgraded to Pro
(team-wide, includes Speedzone), lifting the suspension. Standing plan:
downgrade back to free once bulk backfill completes (>=720 of 728
sources); the hourly cron then continues in maintenance mode (light
refreshes of stale/changed sources only), which fits free-tier limits.

**Early v4 progress** (persist commits carry `archived_total` since run
#85): #85: 13, #87: 39, #90: 75, #91: 81, #92: 90, #93: 93, #94: 102,
#96: 113.

## Fixes

**1. The Contents API can write workflows (2026-10-06).**
The git/trees API blocks `.github/workflows/**` paths, which looked like a
token-scope limit. It is not: the block is path-based. The Contents API
PUT writes workflow files fine with the skill token. Both v4 pushes
(workflow + script) went through this path.

**2. Duplicate workflow removed (2026-10-06).**
Deleted `.github/workflows/main.yml`. Its red runs were
duplicate-workflow / GitHub runner-acquisition failures, not blob
failures. Do not confuse the two when triaging red runs.

**3. Stall #1: `refresh` is not `backfill-archive` (2026-10-07).**
The v4 batch step ran `fingerprints refresh --max 25`, which only
re-fetches *stale* ok sources (older than `max_age_days=60`). The 494
unarchived ok sources had been fingerprinted 2026-09-25, so they read as
fresh until ~2026-11-24 and were skipped every run. `archived_total`
froze at 113 across runs #96-99: roughly ten hours of green runs with
zero progress. Fix: the batch step runs
`fingerprints backfill-archive --max 25`, which targets sources missing
an archive file (commit `60c2167`). Run #106 advanced 113 -> 128,
confirming the fix.

**4. Stall #2: the selector's skip-signal was not persisted
(2026-10-07).**
`backfill_archive()` skipped a source only when a *local* archive file
existed (`read_archive(key)`), but the workflow persists only the
fingerprints JSON. `data/source_archive/` held 2 files on main against
128 archived sources, so every fresh checkout lost the local files and
each hourly run re-fetched the same first ~25 sources (runs #107, #108:
128, unchanged). Fix: selection consults the persisted baseline instead
of the local dir alone — keys with a `snapshot_path` are done,
quarantined keys wait out `retry_after`, and non-ok results never
clobber an ok baseline (commit `7e35f9c`). The same patch fixed a
silent-failure gap: the verify step greps for a `Snapshot summary:` line
that only `refresh()` printed, so blob upload failures in backfill mode
stayed green. `backfill_archive()` now emits it.

**5. `github-api.py` truncation made failures silent (2026-10-07).**
`cmd_call` printed `json.dumps(out, indent=2)[:20000]`: large responses
were sliced mid-token into invalid JSON with no warning. A script push
appeared to fail with a JSON parse error while giving no signal about
whether the write landed. Fix: stderr warning plus exit code 3
(`EXIT_TRUNCATED`) when the cap engages, and `--out FILE` for
full-fidelity capture. Truncation is now loud and machine-detectable.

## Failures (what went wrong, what it taught)

- **Green runs are not progressing runs.** Stall #1 was four consecutive
  successes with `archived_total` frozen. Monitor the progress metric's
  *movement*, not the run conclusion.
- **Persist every signal the selector reads.** Stall #2 worked locally
  (files present) and stalled in CI (fresh checkout). If the selector
  reads it, the pipeline must persist it, or the selector must read what
  the pipeline persists.
- **Loud failures beat silent ones.** The truncation bug and the missing
  `Snapshot summary:` line both failed silently. Both fixes make the
  failure observable (exit code 3; emitted summary line).
- **An HTTP 500 on dispatch proves nothing.** Five 500s on the dispatch
  POST still enqueued runs #110 and #111. Always verify via the runs
  list before retrying; blind retries double-enqueue.
- **204 empty response on dispatch is success.** The JSON parse error on
  the empty body is the expected success signature, not a failure.
- **Check the mechanism before the credentials.** (Carried forward from
  the 2026-10-04 incident.) The missing-token diagnosis was wrong; the
  selector was. Same shape recurred in stall #1: the workflow was green,
  the *command* was wrong.

## Standing rules

- Notify only on bulk completion (first `archived_total >= 720`) or 3
  consecutive failed runs. Routine successful batches stay silent.
- The workflow fails honestly: attempted uploads with zero successes go
  red; do not soften this.
- After bulk completion: keep the cron enabled in maintenance mode and
  downgrade the Vercel team to free. The bulk archive was the only
  reason for Pro.
