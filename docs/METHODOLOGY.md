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

## Evidence tiers

Terminal claims (**cancelled**, **rejected**, **expired**) are shown in one of
two tiers, computed from independent citations from verified sources:

- **Verified** (3 or more independent verified citations): strongly claimed.
  Counted in the verified-claims headline stat.
- **Pending validation\*** (fewer than 3): visible but marked with an
  asterisk, with the exact citation count shown per record (e.g. "1 of 3").
  A single local report is still a lead worth tracking; the asterisk says
  "help corroborate."

\* Pending validation = fewer than 3 independent verified citations;
shown while awaiting corroboration.

**Verified sources** are:

- Primary records: signed contracts, council minutes, procurement documents,
  official agency or vendor statements, court records, Flock transparency
  portal data.
- Established news outlets with an editorial process: named reporters,
  a masthead, published corrections.

**Not verified** (usable as leads, never as citations toward the bar):

- Advocacy organizations and campaign sites, including ones we agree with.
- Social media, video platforms, self-publishing platforms.
- News aggregators and AI-generated summaries.
- Personal blogs and outlets with no verifiable editorial process.

**Independent** means distinct publishers. Three outlets quoting the same press
release, or syndicated copies of one wire story, count once. Automation
approximates independence by distinct domains; a human judges the rest.

Verification is stamped per citation (`sources[].verified`) by
`scripts/classify_sources.py`, an explicit domain map reviewed in git.
Unknown domains fail closed to unverified, and the weekly monitor flags
newly added sources until they are classified.

## Research priorities

Ranked by what most improves the tracker's trustworthiness:

1. **Corroborate terminal claims.** Most cancelled/rejected records are pending
   validation\* (a single local article, or advocacy-only sourcing). Each needs
   3 independent verified citations to move to verified.
2. **Fill Maryland.** Zero sourced records, and the East Coast rollout claims
   ME-to-FL coverage. Then deepen the single-record states.
3. **Renewal dates for active contracts.** Nearly all active records lack an
   exact renewal date; without dates there are no pressure windows, which is
   the tracker's core civic value.

## Rules

1. Every non-null factual field must trace to a `sources[]` entry. No source, no field: use `null`.
2. A missing agency means **not yet researched**, never "confirmed absent." The coverage note on the tracker says this in plain language.
3. Costs are reported figures only. The ~$3,000/camera/year figure is context, not a substitute; never multiply a camera count by it and present the result as a fact.
4. Dates are ISO `YYYY-MM-DD`. If only a month is known, leave the field `null` and put the precision in `notes`.
5. `last_verified` is the date a human last checked the record against its sources. Stale records (over 180 days) get flagged for re-verification.
6. Terminal statuses (cancelled, rejected, expired) show an evidence tier: verified (3+ independent verified citations) or pending validation\* (fewer).
7. Corrections win over pride. A wrong record is worse than a missing one; fix upstream facts first, then the JSON.

## What we don't track

Individual officers, individual vehicles, plate numbers. This is a contracts dataset, not a surveillance dataset. See `THREAT_MODEL.md`.
