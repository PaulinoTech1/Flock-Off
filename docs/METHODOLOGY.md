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
two tiers. This is a hard rule, enforced by the test suite
(`scripts/tests/test_evidence.py`), not a guideline:

- **Verified**: the record cites **at least one verified-primary source**
  (government / procurement document, court record, official agency or
  vendor statement, Flock transparency portal data) **and at least two
  verified-news sources on independent domains**. Counted in the
  verified-claims headline stat.
- **Pending validation\***: anything else. Visible but marked with an
  asterisk, with the exact citation counts shown per record (e.g. "1 primary,
  1 of 2 news"). Pure news-only terminal claims stay in pending
  validation\* indefinitely, no matter how many outlets repeat the story.
  A single local report is still a lead worth tracking; the asterisk says
  "help corroborate."

New or changed terminal-status records must meet the bar before they are
shown as verified; the dataset marks non-compliant records explicitly with
`"validation": "pending"` (see `scripts/migrate_trust.py`). The test suite
enforces the invariant: a terminal record may not display verified without
meeting the bar, and every non-compliant terminal record must carry the
explicit pending marker (`scripts/tests/test_evidence.py`). Meeting the bar
is computed from the citations, not asserted by a human, so there is no
certification step to game. The one judgment automation cannot make,
whether two news sources are genuinely independent or syndicated copies of
one story, remains the reviewer's call; the weekly monitor's simhash layer
surfaces near-duplicate citations for that review, and the reviewer's
sign-off is recorded in the audit log.

**Stale auto-downgrade.** Records whose `last_verified` is older than 180
days automatically drop from "verified" to "pending validation\*" at
display time until re-confirmed. The underlying citations are kept; only
the badge changes. This is computed, not stored, so re-verification
restores the tier without a data migration.

\* Pending validation = does not (yet) meet the evidence bar above;
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

### Upstream discovery feeds (free only)

Two free feeds are approved for *discovery*; neither is a citation by itself,
and neither can drive a status change on its own:

- **Finding Flock cancellation tracker.** Each row links a direct news report
  or public record. Cite that linked source, not the tracker page.
- **EFF Atlas of Surveillance.** Each record links up to three sources. The
  Atlas is EFF-published advocacy data, so records are leads under the rule
  above; cite the underlying linked government/news source, and independently
  confirm the vendor on each record (the vendor filter is imperfect).

**Feed isolation (hard rule).** No record's `status` field may be set or
changed on the sole basis of a feed entry. The linked primary or news source
must be independently fetched, classified, and fingerprinted before the
record is accepted or updated. The test suite rejects any citation whose
URL is on a feed domain (`scripts/tests/test_feeds.py`).

Standing rule: every feed this tracker relies on must be 100% free, no key,
no account, no recurring cost. Paid sources are out regardless of data
quality, because a source we cannot afford to keep is a source we cannot
maintain. The weekly monitor diffs both approved feeds against the dataset;
see `docs/MONITOR.md`.

Verification is stamped per citation (`sources[].verified`) by
`config/flock-off.yaml` (section `classify`), an explicit domain map reviewed in git.
Unknown domains fail closed to unverified, and the weekly monitor flags
newly added sources until they are classified. The full domain
classification is published verbatim on the tracker page itself
("How this tracker works") and as `data/source_classification.json`, so
readers can audit exactly which outlets count and which do not.

**Fingerprint drift (hard gate).** Every citation carries a content
fingerprint (`data/source_fingerprints.json`: simhash + SHA-256 of the
article text). The weekly monitor re-fetches a rotating probe sample (60 per
run) and reports material rewrites; the pre-push gate
(`python3 scripts/flockoff.py fingerprints drift`, wired into the push
script) re-fetches the sources of every changed record and FAILS the push if
any shows Hamming distance >= `fingerprints.update_distance` (8) against its
stored simhash without a human re-review. Re-reviews are recorded in
`data/fingerprint_reviews.json`:

```json
{
  "<source_key>": {
    "reviewed_at": "2026-09-26",
    "reviewed_by": "Alexander",
    "decision": "accepted",
    "note": "site redesign; article text unchanged"
  }
}
```

A review covers only the baseline it was recorded against (`reviewed_at` >=
the fingerprint's `fetched_at`); refreshing the baseline after acceptance
retires the review. `decision` is `accepted` or `rejected`; a rejected drift
means the source is replaced, not kept.

## Research priorities

Ranked by what most improves the tracker's trustworthiness:

1. **Corroborate terminal claims.** Most cancelled/rejected records are pending
   validation\* (a single local article, or advocacy-only sourcing). Each needs
   1 verified-primary source plus 2 independent verified-news sources to move
   to verified.
2. **Fill the remaining states.** Maryland's zero-record gap was closed by the
   second 10-state wave (AR, IA, ID, MD, MN, MT, NE, NM, NV, UT), which landed
   2026-09-26 and took the tracker to 322 records across 45 jurisdictions.
   Montana researched to a well-evidenced zero (restrictive ALPR statutes, no
   qualifying government contracts). Still unresearched: AK, HI, ND, SD, WY.
   Then deepen the single-record states.
3. **Renewal dates for active contracts.** Nearly all active records lack an
   exact renewal date; without dates there are no pressure windows, which is
   the tracker's core civic value.

## Rules

1. Every non-null factual field must trace to a `sources[]` entry. No source, no field: use `null`.
2. A missing agency means **not yet researched**, never "confirmed absent." The coverage note on the tracker says this in plain language.
3. Costs are reported figures only. The ~$3,000/camera/year figure is context, not a substitute; never multiply a camera count by it and present the result as a fact.
4. Dates are ISO `YYYY-MM-DD`. If only a month is known, leave the field `null` and put the precision in `notes`.
5. `last_verified` is the date a human last checked the record against its sources. Records over 180 days stale are automatically shown as pending validation\* until re-confirmed (computed at display time; the citations are kept).
6. Terminal statuses (cancelled, rejected, expired) are verified only with 1+ verified-primary source and 2+ independent verified-news sources; anything else carries `"validation": "pending"` and shows pending validation\*. News-only terminal claims stay pending indefinitely.
7. Corrections win over pride. A wrong record is worse than a missing one; fix upstream facts first, then the JSON.
8. Citations are deduplicated in three layers: (1) every source carries a stable `source_key`, the canonical form of its URL, and the same key twice in one agency's sources is a reject; (2) content simhashes flag near-duplicate articles cited under different URLs for human review, never auto-merged; (3) re-fetched articles that materially changed since citation are flagged for re-verification. Bot-blocked pages are "unverifiable," never "probably fine."

## What we don't track

Individual officers, individual vehicles, plate numbers. This is a contracts dataset, not a surveillance dataset. See `THREAT_MODEL.md`.
