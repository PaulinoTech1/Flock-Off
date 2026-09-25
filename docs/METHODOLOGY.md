# Methodology

How contract records get in, what the confidence ratings mean, and what we refuse to do.

## Statuses

- **active**: a signed contract is in force (or strongly evidenced by a live transparency portal plus procurement records).
- **pending**: a proposal, pilot, or renewal is under public debate.
- **cancelled**: a signed contract was ended early or not renewed.
- **rejected**: a proposal was killed before signing (council vote, dropped plan).
- **expired**: a contract lapsed with no public record of renewal or cancellation.

## Record fields

`agency_type` is one of: `municipal_police`, `sheriff`, `state_police`, `county`,
`municipal_government`, `university`, `private`.

## Confidence

- **high**: primary source. Signed contract, council minutes, Flock transparency portal figures, official press release.
- **medium**: reputable news reporting (named outlet, dated).
- **low**: single blog, social post, or activist claim without corroboration. Low-confidence records are included only when marked, and never drive the headline stats without a second source.

## Rules

1. Every non-null factual field must trace to a `sources[]` entry. No source, no field: use `null`.
2. A missing agency means **not yet researched**, never "confirmed absent." The coverage note on the tracker says this in plain language.
3. Costs are reported figures only. The ~$3,000/camera/year figure is context, not a substitute; never multiply a camera count by it and present the result as a fact.
4. Dates are ISO `YYYY-MM-DD`. If only a month is known, leave the field `null` and put the precision in `notes`.
5. `last_verified` is the date a human last checked the record against its sources. Stale records (over 180 days) get flagged for re-verification.
6. Corrections win over pride. A wrong record is worse than a missing one; fix upstream facts first, then the JSON.

## What we don't track

Individual officers, individual vehicles, plate numbers. This is a contracts dataset, not a surveillance dataset. See `THREAT_MODEL.md`.
