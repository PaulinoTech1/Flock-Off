# Weekly monitor runbook

The monitor keeps the contract dataset fresh with about one hour of human
review per week. Automation finds candidates; a human makes every call.

## What runs every Monday morning

1. **Deterministic checks** (`scripts/weekly_monitor.py`): pressure windows
   (active contracts renewing within 90 days), active contracts missing a
   renewal date, stale records (unverified > 180 days), low-confidence leads.
2. **Portal spot-checks**: up to 10 active records with a transparency portal
   URL get a best-effort fetch. A dead portal is a *weak* signal of contract
   termination: reported as "investigate", never as fact.
3. **News sweep**: targeted searches for Flock contract, cancellation, and
   renewal news from the last ~14 days, US-wide focus. Only items that are
   new or contradict the dataset survive; capped at 10.
4. **Upstream feed checks** (in `weekly_monitor.py`, free and keyless):
   Finding Flock's cancellation tracker (new in-scope terminal claims,
   status mismatches against our records) and the EFF Atlas of Surveillance
   CSV (in-scope agencies we lack). Failures are reported under Monitor
   health, never fatal.
5. **Digest**: one GitHub issue titled `Monitor digest YYYY-MM-DD`, sections
   ordered by priority, every item with a source link and a proposed dataset
   edit. Total action items capped around 25.

## The one-hour workflow

1. **Read the digest** (10 min). Sections are priority-ordered: pressure
   windows first, then news, then candidates, then hygiene.
2. **Verify each item against its source** (35 min). Open the link, confirm
   the claim, decide the edit. Per the methodology: no source, no field;
   a wrong record is worse than a missing one.
3. **Reply with approvals** (5 min). Comment on the issue
   ("approve all except #3", "item 2 is wrong because...") or just say so
   in chat.
4. **Apply and redeploy** (10 min, Constantine's job on your go-ahead):
   edit `data/agencies.json`, bump `last_verified` on touched records,
   push, redeploy. Nothing auto-merges.

## Section guide

| Section | What it means | Typical action |
|---|---|---|
| Pressure windows | Active contract renews within 90 days | Verify the date against a primary source; this is organizer intel |
| News items to classify | Fresh reporting not yet in the dataset | Read, decide status change, propose exact field edits |
| Candidate new agencies | Upstream lists an agency we lack | Research: confirm Flock vendor, find contract or vote record |
| Upstream candidates (feeds) | Finding Flock / Atlas entries not in dataset | Research: confirm vendor + find primary record; cite the linked source, not the feed |
| Status mismatches | Feed disagrees with our record status | Re-verify against the linked source; correct the record |
| Stale records | Unverified > 180 days | Re-check the top source; refresh `last_verified` or correct |
| Low-confidence leads | Single-source records | Corroborate or leave flagged; never cite as confirmed |
| Monitor health | What broke this run | Fix the check or accept the gap explicitly |

## Escape hatches

- Quiet week with no action items: no chat ping. The filed issue is the audit trail.
- Pause the monitor: say so in chat and the schedule is disabled.
- The monitor never edits `agencies.json` itself and never presents a weak
  signal as a confirmed status change. If it ever does, that's a bug: report it.
