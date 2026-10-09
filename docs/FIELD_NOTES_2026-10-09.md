# Field Notes: Renewal-Date Research & Testing (2026-10-09)

What we tried, what failed, and what is structurally unknowable. Written so the
next research pass does not repeat dead ends.

## Renewal-date research: 20 agencies, 4 parallel batches

**Yield:** 2 records gained new dates (OKC, Decatur). 5 "finds" were already on
file (the researchers were not given current dataset values for batches B-D, so
they re-discovered Dallas, Johnson City, Fort Smith, College Station, and
Scottsdale dates). The rest produced confirmations, dead ends, or flags.

### Dead ends by agency

- **San Jose PD:** contract documents are not publicly indexed. Three search
  rounds including a Legistar-targeted query returned other cities' legislation.
  Next step is a California Public Records Act request to the city clerk.
- **Fort Worth PD:** the PD's arrangement appears to be a rolling lease below the
  council-action threshold. The only Flock council item (June 2025, M&C 25-0548)
  covers privately-owned cameras on public rights-of-way, not the PD contract.
  No public renewal date exists to find.
- **LVMPD:** structurally unobtainable. The deployment was funded through ~$2M
  in private donations (Horowitz Family Foundation via Friends of Metro),
  bypassing public procurement entirely. No council vote, no published term, no
  renewal date. Mark all three date fields genuinely unknowable from public
  sources, not merely "not yet found."
- **Caldwell PD:** a reported Oct 5, 2026 council vote to replace Flock with a
  10-year Axon bundle could not be verified. The only detailed write-ups were
  AI-generated (excluded per editorial rule) or a Substack (weak). Do NOT mark
  cancelled on that basis. Follow-up: pull Caldwell CivicClerk minutes directly.
- **Newport News PD:** purchase-order dates live behind an advocacy site's
  DocumentCloud links that did not resolve through text fetch. The 36-month term
  start was never pinned to a day. Autumn 2027 is a window, not a date.
- **Spokane PD:** the dataset's contract_end of 2026-01-28 could NOT be confirmed
  or refuted. August 2026 reporting shows an active partnership after that date,
  suggesting renewal, but no renewal document exists. Treat the on-file end date
  as stale/unverified, not as evidence the contract ended. Top follow-up
  candidate: 2026 council consent agendas or a records request.
- **Fresno PD:** council adopted the agreement 2024-02-22 (primary), but the
  agreement states the term "commences upon execution" and the published
  signature page is undated. Approval date is not start date. Do not file
  2024-02-22 as contract_start without the executed copy.

### Conflicting sources

- **Akron PD:** the Beacon Journal (Gannett, citing contract terms) says the
  contract expires Dec 31, 2028. Signal Akron (nonprofit newsroom) wrote
  "expires next September" (Sept 2027). Filed nothing; the specific,
  contract-citing source wins on paper, but the conflict drops it below the
  high-confidence bar. Resolve by pulling the council legislation.
- **Decatur PD:** the Nov 2023 renewal vote date was triangulated from a search
  index's "1066 days ago" relative timestamp converging with "Monday night."
  Flagged low-medium and not filed. Weak dating methods must be labeled as such.
- **Cleveland PD:** one source said the renewal vote was 9-5, another 9-6. Went
  with GovTech's 9-6. Minor, but recorded.

### Source-quality pollution

citizenportal.ai (explicitly AI-generated summaries) appeared repeatedly in
results across all four batches and was excluded in full per the editorial rule.
Content farms (motorbiscuit, archynewsy, newslocker, occasionaldigest,
mangaloremirror) and TikTok/YouTube results were also encountered and
disregarded. The AI-summary pollution is getting worse, not better; future
research passes should expect it and budget time for filtering.

Advocacy sites (DeFlock chapters, eyesonice.net, change.org petitions) were
useful as leads and corroboration but never as the basis for a date. One
advocacy-hosted document (a City of Woodland staff report mirrored on
deflockwoodland.org) was treated as primary content with corroboration, not as
an advocacy claim.

### Structural lessons

1. **Renewal dates are rarely published.** Of 20 agencies, zero had a publicly
   documented future renewal *date*. Contract *end* dates are the decision
   points; renewal *options* (Dallas 2x1-yr, Scottsdale 2-yr term) exist
   contractually with no exercise date set. For tracker purposes, contract_end
   is the honest field; renewal_date should be reserved for actual scheduled
   decisions (e.g., Cleveland's Dec 2026 window).
2. **Give researchers current dataset values.** Batches B-D re-discovered dates
   already on file because the briefs omitted them. Wasted effort; include a
   per-record "already known" block in every future brief.
3. **"Not found" has flavors.** Distinguish: not indexed (San Jose), below
   public-action threshold (Fort Worth), structurally nonexistent (LVMPD),
   conflicting (Akron), stale/unverified (Spokane). They imply different
   follow-ups.

## Pentest (flock-off.us, 2026-10-09)

No vulnerabilities found. Strict CSP, correct auth gates (401/405), input
validation rejecting traversal and injection, no source/config exposure.

**Struggle:** POST, PUT, DELETE, and PATCH requests hang from this network
(even empty POSTs to static paths); GETs are fast (~0.7s). One POST completed
after ~20s with the correct 401, proving the gate works, but the write paths
(/api/report, /api/promote) could not be exercised reliably. This is a
transport/proxy limitation of the test environment, not a site defect. The
write paths need re-testing from an unrestricted network before they can be
called fully verified. Full report: workspace/flock-off-pentest-2026-10-09.md
(not committed to the repo).

## Data pipeline struggles

1. **The verified-domain test caught a real issue.** A new Decatur source
   (city council resolution hosted on NovusAgenda) was initially stamped
   verified=true, but novusagenda.com is not in the domain classification map,
   so test_no_verified_source_is_unlisted failed (as designed). The source is a
   legitimate primary document; it is now marked verified=false per the existing
   convention for unlisted domains (same as the record's FOIA sources).
   Promoting the domain requires a domain_approvals.yaml entry with approver,
   date, and rationale. The test also has a latent bug: it references
   agency['agency_id'] but records use 'id'; it only surfaces when an offender
   exists.
2. **Audit chain reconstruction.** The audit log hashes file bytes, not JSON
   serialization. Rebuilding the "before" state from a modified file is fragile;
   the reliable path was fetching the last release commit's agencies.json from
   GitHub (hash matched). Lesson: snapshot agencies.json to /tmp BEFORE any
   manual edit, or the audit append cannot chain.
3. **Meta regeneration is load-bearing.** Adding date fields changed the
   recomputed meta, so generate_meta.py must run before sign_manifest.py, and
   the audit entry must be appended against the true prior bytes.

## Open questions (not resolved today)

- meta.last_updated (2026-10-04) is the max record last_verified, not the
  dataset release date. The UI label "Data updated" may mislead; semantics
  unresolved.
- Everett WA is listed active but its program has been paused since 2026-02-25
  by mayoral directive. No status change made (contract status unknown); a
  notes-field convention for operational pauses does not yet exist.
- Spokane's 2026-01-28 contract_end is likely stale; no verified replacement.

---

## Appendix A: Batch A report (Dallas, Stockton, Scottsdale, Woodland, Spokane) — verbatim

Research complete. I've searched all five agencies across council records, local news, and official documents. Here are my findings.

---

### 1. Dallas Police Department — `tx-dallas-pd`

**renewal_date:** not found (no dated renewal decision located)
**contract_start:** 2025-06-15 — high confidence
**contract_end:** 2028-06-14 — high confidence (confirms dataset value)

**Sources:**
- Primary — Dallas City Council Legistar, File #25-1606A (agenda date May 28, 2025): "Authorize a three-year service contract, **with two one-year renewal options** with Flock Group, Inc. ... for the period **June 15, 2025 through June 14, 2028** - Not to exceed $5,738,414.61"
  https://cityofdallas.legistar.com/LegislationDetail.aspx?ID=7404358&GUID=FDDAEA7D-A941-4B35-8A9D-318FF351CAE4
- News — GovTech via Dallas Morning News (~Oct 1, 2026): 300+ state-funded cameras "will instead remain online for **at least another 90 days** under an agreement between police and the surveillance technology company" after Chief Comeaux met Flock CEO Garrett Langley. Terms undisclosed. (~Dec 30, 2026 implied end of that interim extension.)
  https://www.govtech.com/public-safety/dallas-flock-safety-cameras-stay-online-after-ceo-police-meeting
- News — FOX 4 (~Sept 16, 2026): state grant funding expired Sept 15, 2026 per Gov. Abbott's pause; council kept the $1.5M city-funded portion (300 cameras); only 3 members voted to cancel.
  https://fox4news.com/news/dallas-police-looking-new-ways-keep-over-300-flock-cameras-operational-state-funding-ends

**Confidence:** high for start/end dates (signed council authorization). The two one-year renewal options are documented, but no renewal date has been set publicly — renewal would be decided before June 2028.

**Status implication:** none — contract active through 2028-06-14, with the state-funded camera subset on a separate ~90-day interim extension to ~Dec 2026.

**Search notes:** Searched council records, Dallas Morning News/GovTech, FOX 4. Dead end: no RFP or renewal vote scheduled found; the renewal options exist contractually but are unexercised.

---

### 2. Stockton Police Department — `ca-stockton-pd`

**renewal_date:** not found (contract runs to 2031; no interim renewal date)
**contract_start:** 2023-09 (month precision) — medium confidence
**contract_end:** 2031-04-14 — high confidence (confirms dataset value)

**Sources:**
- News — RecordNet, April 2, 2026 (bylined staff reporting): "The 7-0 vote allowed the city to add six drones to its network of license plate reader cameras... The approval raised Stockton's total contract with Flock to about $5.4 million and **extended it through April 14, 2031**." Also notes LPR use began September 2023 (120 cameras installed to date.)
  https://www.recordnet.com/story/news/politics/government/2026/04/02/stockton-police-flock-drone-program-public-raises-surveillance-concerns/89414806007/
- News — RecordNet, March 30, 2026 (pre-vote): "If approved, the amendment would raise Stockton's total contract with Flock to about $5.4 million and **extend it through April 2031**."
  https://www.recordnet.com/story/news/politics/government/2026/03/30/stockton-city-council-flock-police-drone-surveillance-expansion/89382772007/
- Primary — Stockton Legistar File #24-1097 (Falcon platform amendment, $1,196,700): confirms the Flock contract lineage and COPS grant funding context.
  https://stockton.legistar.com/LegislationDetail.aspx?ID=7016574&GUID=30759F5D-9359-4C1C-8D09-F085922655CC&Options=&Search=

**Confidence:** high for contract_end 2031-04-14 (council vote, exact date in two articles). Medium for September 2023 start (reported as program history, month precision only).

**Status implication:** none — active, recently extended. Note: Sept 2026 reporting documents a misconduct termination (officer misused cameras) and resident calls to terminate, but no council action to end the contract.

**Search notes:** Searched Stockton council records and RecordNet coverage. Dead end: no separate renewal date — the April 2031 end date IS the next decision point; the amendment included cancellation provisions if future funding isn't identified.

---

### 3. Scottsdale Police Department — `az-scottsdale-pd`

**renewal_date:** not found (two-year renewal term exists contractually; no dated renewal decision)
**contract_start:** 2023-06-21 — medium-high confidence
**contract_end:** 2028-06 (month precision) — high confidence (confirms dataset value)

**Sources:**
- News — Scottsdale Progress via scottsdale.org (~Sept 20, 2026): "then-City Attorney Sherry Scott as well as the city's purchasing director and police operational support director **signed a contract with Flock Group's Mark Smith June 21, 2023**. The **$1.2 million contract has a five-year 'initial term' with a two-year 'renewal term.'**" (Details from contracts obtained via public records request.)
  https://www.scottsdale.org/city_news/scottsdale-keeps-cameras-on-despite-flock-fury/article_9670e344-0d7a-47fb-b7a8-d9f51747d359.html
- News — AZCentral, Aug 28, 2026: "the city contracted Flock for 85 cameras in 2023. **The current contract will expire in June 2028.**"
  https://www.azcentral.com/story/news/local/scottsdale/2026/08/28/scottsdale-chooses-oversight-over-removal-of-flock-cameras/91512992007/
- News — AZCentral, Oct 8, 2026: unanimous Oct 6 council vote for audits, misuse criminalization, and vendor review — cameras stay, safeguards added.
  https://www.azcentral.com/story/news/metro-phoenix/2026/10/08/scottsdale-to-make-flock-camera-abuse-a-crime/92137855007/

**Confidence:** high for June 2028 end (two independent outlets). Medium-high for June 21, 2023 signing (single local outlet citing obtained records).

**Status implication:** none — active through June 2028, with a two-year renewal term available thereafter. Council is adding safeguards, not exiting.

**Search notes:** Searched Scottsdale council actions and AZCentral/Progress coverage. Dead end: no renewal vote or renewal date located; the renewal term is contractual but unexercised.

---

### 4. Woodland Police Department — `ca-woodland-pd`

**renewal_date:** not found (next decision at contract end)
**contract_start:** 2026-02 (month precision) — high confidence
**contract_end:** 2028-02-03 — medium-high confidence (consistent with dataset value; exact day from agenda date + 2-year term)

**Sources:**
- Primary content (city staff report, hosted on advocacy mirror) — Woodland City Council Regular Meeting, **February 3, 2026**, Item H.6: "Staff recommends that the City Council adopt Resolution No. ___ to: (1) Authorize the City Manager to **enter into a 2-year contract** for goods and services with Flock Group, Inc. for an amount **not to exceed $300,000**..."
  https://deflockwoodland.org/wp-content/uploads/2026/02/Authorize-the-City-Manager-to-Enter-a-New-Co-Termed-Contract-for-the-Existing-Flock-License-Plate-Readers.pdf
  (Note: document is a City of Woodland staff report; the host domain is a local opposition group. Corroborated below.)
- News — GovTech via TNS (~Feb 10, 2026): "The Woodland City Council **renewed a $300,000 contract** with Flock Safety for automatic license plate readers **this week**" at its Tuesday-night meeting.
  https://www.govtech.com/transportation/woodland-calif-extends-license-plate-cam-program-amid-concern
- News — GovTech (~Sept 2, 2026): confirms "Woodland signed a **two-year extension** for its Flock cameras" in February; 38 cameras currently.
  https://www.govtech.com/public-safety/woodland-calif-police-defend-flock-safety-amid-concern
- Primary — City of Woodland ALPR page: "Woodland currently contracts with Flock Safety for its platform."
  https://www.cityofwoodland.gov/1704/Automated-License-Plate-Readers-ALPR

**Confidence:** high that a 2-year, $300K contract was authorized Feb 3, 2026 (staff report + contemporaneous news). Medium-high for the 2028-02-03 end day (agenda date + 2-year term; the exact end day is my arithmetic on the sourced term, flagged as such — the dataset already carried 2028-02-03 and nothing contradicts it).

**Status implication:** none — active; just renewed.

**Search notes:** Searched cityofwoodland.gov and news. Dead ends: the city's own site hosts the staff report PDF behind agenda archives I couldn't directly retrieve; the ALPR info page has no dates. No renewal date beyond the 2028 end.

---

### 5. Spokane Police Department — `wa-spokane-pd`

**renewal_date:** not found
**contract_start / contract_end:** not confirmed beyond dataset values
**Status implication:** UNCERTAIN — see below. This is the weakest result of the five.

**Sources:**
- Primary — City of Spokane Public Safety & Community Health Committee agenda, March 6, 2023 (static.spokanecity.org): "Purchase of Flock ALPR Cameras (**13 fixed cameras, 2 mobile cameras**, licensing for two existing cameras) related to FY22-23 WATPA supplemental grant funding." Establishes program origin ~early 2023.
  https://static.spokanecity.org/documents/bcc/committees/public-safety-and-community-health/agendas/2023/03/psch-agenda-2023-03-06.pdf
- News — Kitsap Sun / USA Today Network, Aug 17, 2026 (bylined, Zachary Fletcher): "**The City of Spokane currently partners with Flock Safety** and, according to DeFlock, operates around 100 cameras."
  https://www.kitsapsun.com/story/news/2026/08/17/flock-cameras-in-washington-state-where-to-find-them-near-me/91336758007/

**Confidence:** The dataset's 2026-01-28 end date could NOT be confirmed or refuted. The August 2026 Kitsap Sun piece indicates an active partnership AFTER that date, which suggests renewal/extension — but I found no renewal document, vote, or new end date. Do not treat the contract as ended; treat the end date as stale/unverified.

**Important disambiguation:** Much 2026 Spokane Flock coverage concerns the **Spokane County Sheriff** (shut down cameras over SB 6002) — a different agency. The city PD appears unaffected.

**Search notes:** Searched spokanecity.org council records, local news, 2026 contract actions. Dead ends: no 2026 renewal/extension vote or document located for the city PD; several AI-generated citizenportal.ai pages were encountered and disregarded per policy (one, about Kent WA, was also the wrong city). **This agency is the top follow-up candidate** — a records request to Spokane PD or a deeper pass through 2026 council consent agendas is needed.

---

### General notes (Batch A)

- **Renewal dates:** None of the five agencies has a publicly documented future renewal *date*. Dallas and Scottsdale have contractual renewal *options/terms* (2x one-year; two-year respectively) with no exercise date set. For tracker purposes, the honest value is "not found" for all five renewal_date fields; the contract_end dates above are the decision points.
- **Disregarded per policy:** citizenportal.ai (explicitly AI-generated), bellerian1.substack.com (conspiracy commentary), mangaloremirror.com (content-farm mirror), TikTok/YouTube results.
- **No dates were inferred** from contract lengths alone except where flagged (Woodland 2028-02-03 day arithmetic, marked medium-high).

---

## Appendix B: Batch B report (Fort Smith, San Jose, Fort Worth, LVMPD, Akron) — verbatim

Research complete. Here are my findings for all five agencies. All quotes kept brief per copyright limits.

---

### 1. Fort Smith Police Department — `ar-fort-smith-pd`

**contract_end: 2027-11-30** — confirmed, confidence HIGH
- Source (primary): Fort Smith Police Department press release, Aug 27, 2026, via City of Fort Smith official channel: "The current contract runs through November 30, 2027."
  - URL: https://content.govdelivery.com/accounts/ARFORTSMITH/bulletins/4271fdb
- Corroborated (news): Talk Business & Politics, Aug 27, 2026 ("The existing contract runs through Nov. 30, 2027") — https://talkbusiness.net/2026/08/fspd-makes-flock-camera-policy-changes-will-review-contract-renewal/ ; Southwest Times Record, Aug 28, 2026 — https://www.swtimes.com/story/news/2026/08/28/fort-smith-changes-rules-for-flock-automated-license-plate-readers/91508039007/

**renewal_date: not found**
- The FSPD release states the department "has notified Flock that it will review whether to renew its contract" and "Any decision on renewal will follow an additional public review by the Fort Smith Board of Directors." No renewal date has been set; the decision is pending.

**contract_start: not found**

**Status implication:** none — contract active through 2027-11-30; renewal under internal-audit-driven review, not a cancellation.

**Dead ends:** searched for council agenda items with a renewal vote; none exist yet. The Aug 2026 policy changes (7-day retention, no outside-agency access) are the substantive recent development.

---

### 2. San Jose Police Department — `ca-san-jose-pd`

**renewal_date: not found**
**contract_start: not found**
**contract_end: not found**

**Status implication:** none found — contract appears active (~516 cameras per San Jose Spotlight). Heavy political pressure (officer misuse firing, two lawsuits, Sept 30 2026 rules-committee memos to agendize ALPRs) but no cancellation vote has occurred; the March council vote kept the cameras with 30-day retention.

**Context only (not contract dates, do not file as such):** StateScoop reports the City Council approved the ALPR program in 2021 after privacy impact assessments (news) — https://statescoop.com/san-jose-automated-license-plate-readers-data-privacy/ ; San Jose Spotlight reports cameras "first introduced in San Jose in 2022" (news) — https://sanjosespotlight.com/san-jose-again-attempts-to-tighten-controls-on-license-plate-readers/

**What I searched / dead-ended:** three rounds including a Legistar-targeted query (returned Monterey County and other cities' legislation, not San Jose's). San Jose's Flock contract documents and term length are not publicly surfaced in indexed sources. A California Public Records Act request to the city clerk would be the next step — outside my remit (no outreach).

---

### 3. Fort Worth Police Department — `tx-fort-worth-pd`

**renewal_date: not found**
**contract_start: not found**
**contract_end: not found**

**Key primary document found (not the police contract):** Fort Worth City Council minutes, June 10, 2025, M&C 25-0548 — "Authorize Execution of a Public Right-of-Way Use Agreement Granting Flock Group, Inc. a License to Install and Maintain Non-Police Department Flock License Plate Reader Cameras on Public Rights of Way" — Motion: Approved. This covers privately-owned cameras on public ROW, not FWPD's own contract.
- URL: https://fortworthgov.legistar1.com/fortworthgov/meetings/2025/6/1570_M_CITY_COUNCIL_25-06-10_Meeting_Minutes.pdf (primary)

**Context only:** FWPD installed its first Flock camera September 2020; bulk of cameras since Jan 1 (2021); lease reported at $2,000/camera/year (Security Today, 2021, news) — https://securitytoday.com/articles/2021/03/16/high-tech-cameras-agree-with-fort-worth.aspx ; city briefing June 2024 states ~250 Flock cameras (primary) — https://www.fortworthtexas.gov/files/assets/public/v/1/communications/documents/city-council-presentations/2024/06-04-2024/briefing-on-police-technology.pdf

**Status implication:** none — active.

**Dead ends:** no Mayor & Council communication for the police department's Flock purchase/renewal found on Legistar; the PD's arrangement appears to be a rolling lease below the council-action threshold. The June 2025 item is the only Flock council action and it is not the police contract.

---

### 4. Las Vegas Metropolitan Police Department — `nv-lvmpd`

**renewal_date: not found**
**contract_start: not found**
**contract_end: not found**

**Why:** LVMPD's Flock deployment was funded through private donations, not public procurement. The Horowitz Family Foundation donated ~$2M in 2023 (TechCrunch, Nov 2024, news, citing foundation tax filings) — https://techcrunch.com/2024/11/08/ben-horowitzs-cozy-relationship-with-the-las-vegas-police-department-aided-a16z-portfolio-company-skydio/ — routed through the nonprofit Friends of Metro, bypassing public approval. Carscoops (Feb 2026, news, citing The Nevada Independent) confirms the arrangement — https://www.carscoops.com/2026/02/flock-safety-las-vegas-cameras/. ~180–200 cameras per Sheriff McMahill via Review-Journal (news) — https://www.officer.com/command-hq/technology/traffic/lpr-license-plate-recognition/news/55406211/nevada-lawmaker-proposes-ban-on-flock-safety-automated-license-plate-readers

**Status implication:** none — active; note Nevada Assemblymember La Rue Hatch has proposed an ALPR ban bill (2026), which is legislative risk, not a contract event.

**Dead ends:** there is no public contract to find — the donation structure means no council/board vote, no published term, no renewal date. LVMPD's Fiscal Affairs Committee agendas would be the only public venue and show nothing on Flock. Marking all three dates genuinely unknowable from public sources.

---

### 5. Akron Police Department — `oh-akron-pd`

**contract_end: 2028-12-31** — confidence MEDIUM-HIGH
- Source (news, established outlet): Akron Beacon Journal (Gannett), Oct 1, 2026, reporting on the contract itself: "the contract that's set to expire on Dec. 31, 2028" and "In 2023, Akron City Council signed a five-year contract for more than $1.8 million with Flock Safety."
  - URL: https://www.beaconjournal.com/story/news/crime/2026/10/01/akrons-contract-with-flock-explained/92019283007/
- Corroborating context (news): Beacon Journal, Oct 1, 2026 — council voted 12-0 in 2022 for a one-year contract, then "in 2023, council voted unanimously to extend the contract for five years" — https://www.beaconjournal.com/story/news/crime/2026/10/01/akron-ohio-flock-cameras-license-plate-readers/91454112007/

**renewal_date: not found** — no renewal date stated; the renewal decision would precede Dec 2028. Note the independent police auditor began a full audit of the ~145-camera system in Sept 2026, which will inform the renewal discussion.

**contract_start: not found** (five-year term signed 2023; exact start date not stated — not inferring)

**Discrepancy flagged:** Signal Akron (Sept 2026, nonprofit newsroom) wrote "The city's contract expires next September" (i.e., Sept 2027) — https://signalakron.org/akron-police-flock-camera-program-review-independent-auditor-anthony-finnell/ — which conflicts with the Beacon Journal's Dec 31, 2028. I'm going with the Beacon Journal: it is more specific, cites contract terms directly, and is consistent with a five-year term signed in 2023. Recommend treating 2028-12-31 as medium-high, not high, until the council legislation is pulled.

**Status implication:** none — active.

---

### Summary table (Batch B)

| Agency | record id | renewal_date | contract_start | contract_end | confidence |
|---|---|---|---|---|---|
| Fort Smith PD | ar-fort-smith-pd | not found | not found | 2027-11-30 | high (PD press release) |
| San Jose PD | ca-san-jose-pd | not found | not found | not found | — |
| Fort Worth PD | tx-fort-worth-pd | not found | not found | not found | — |
| LVMPD | nv-lvmpd | not found | not found | not found | — (no public contract exists) |
| Akron PD | oh-akron-pd | not found | not found | 2028-12-31 | medium-high (news citing contract) |

**Search notes:** I deliberately did not use aggregator/AI-generated content encountered during searching (citizenportal.ai AI-generated summaries, motorbiscuit.com, archynewsy.com, newslocker.com, occasionaldigest.com) — all disregarded per the source standards. Two solid, fileable results: Fort Smith's 2027-11-30 end date (primary) and Akron's 2028-12-31 end date (strong news). No agency yielded a stated renewal date; Fort Smith is the only one where a renewal decision is affirmatively pending. San Jose and Fort Worth contract documents are not publicly indexed — a records request would be the next move. LVMPD's dates are structurally unobtainable from public sources due to the private-donation funding model.

---

## Appendix C: Batch C report (Johnson City, Lexington, Cleveland, Decatur, OKC) — verbatim

Research complete on all five agencies. Here are my findings:

---

### 1. Johnson City Police Department — `tn-johnson-city-pd`

- **renewal_date:** not applicable (10-year term; no renewal clause found)
- **contract_start:** 2025-07-17 — confidence **high** (authorization date; execution presumably same period)
- **contract_end:** 2035-07 — confidence **medium** (10-year term stated in primary source; exact end date not published)
- **decision_date:** 2025-07-17 — confidence **high**
- **Status implication:** active; locked into a 10-year, $8.063M deal. Public pressure to cancel exists (Sept 2026 commission comments) but no action taken.

**Sources:**
- Primary: Johnson City CivicWeb agenda summary, "July 17, 2025 Approved by Board of Commissioners" — "Request to approve a resolution authorizing the City to enter into an 10 year licensing and purchasing agreement for hardware, software and Professional Services to implement the Flock Safety Platform"; "Contract Total: $8,063,000 Year 1 Funding: Drug Fund $300,000"
  `https://johnsoncitytn.civicweb.net/document/322557/Flock%20Group%20Inc.%20dba%20Flock%20Safety_Flock%20Safety%20.pdf?handle=FFC6987687084379BCCF1920802EF93D`
- News: Route Fifty (established, 2026-09) — "Johnson City, which partnered with Flock for a 10-year contract in 2025, has 145 license plate readers and 145 pan/tilt/zoom cameras"
  `https://www.route-fifty.com/public-safety/2026/09/flock-cameras-divide-tennessee-governments-residents-over-privacy-some-end-their-contracts/415832/`

**Search notes:** citizenportal.ai result was AI-generated — disregarded per policy. eyesonice.net (advocacy) used only as a lead. Dead end: exact contract execution/signing date beyond the 7/17 authorization vote not found.

---

### 2. Lexington Police Department — `ky-lexington-pd`

- **renewal_date:** 2029-04 — confidence **medium**
- **contract_start:** 2024-04-25 (five-year extension term) — confidence **medium-high**
- **contract_end:** 2029-04 — confidence **medium** (five-year term; exact end date not published)
- **decision_date:** 2024-04-25 — confidence **high**
- **Status implication:** active. Note: 25 additional cameras added at no cost via Aug 2024 amendment (125 total now).

**Sources:**
- Primary: Lexington-Fayette Legistar, File #0383-24 — action history: 4/9/2024 work session "Approved and Referred to Docket", 4/11/2024 "Received First Reading", 4/25/2024 Urban County Council "Approved / Pass"
  `https://lexington.legistar.com/LegislationDetail.aspx?ID=6610400&GUID=418DB336-548B-48EF-ACA4-4E8963EB418E&Options=&Search=`
- News: CivicLex (local nonprofit news org) — "Council voted to approve a five-year lease extension for the 100 Flock license plate reader cameras... The first year of this lease will cost the City $352,404.11, with each subsequent year's cost being $317,500"
  `https://civiclex.org/weekly-posts/council-approves-five-year-lease-extension-for-flock-cameras`
- News: WEKU (NPR affiliate, 2024-04-10) — council gave initial approval to extend for five years; pilot began 2022
  `https://www.weku.org/lexington-richmond/2024-04-10/lexingtons-city-council-takes-first-step-in-extending-license-reading-camera-program`

**Search notes:** background confirmed via Legistar meeting record 8/29/2024 (amendment for 25 extra cameras at no cost). Dead end: exact lease execution/effective date not published; using approval date.

---

### 3. Cleveland Police Department — `oh-cleveland-pd`

- **renewal_date:** 2026-12 — confidence **medium**
- **contract_start:** 2023 (initial 100-camera deployment, $250,000) — confidence **medium**
- **contract_end:** 2026-12 — confidence **medium** (six-month extension; GovTech: "gives City Hall until late December")
- **decision_date:** 2026-07-15 — confidence **high** (9-6 vote; one source said 9-5 — going with GovTech's 9-6)
- **Status implication:** active but fragile — council cut the mayor's requested 1-year/$250K renewal down to a 6-month/$125K extension and is soliciting other vendors. Strong candidate for non-renewal at year end.

**Sources:**
- News: GovTech (2026-07) — "Cleveland City Council voted 9-6 on July 15 to approve a six-month, $125,000 extension... Mayor Justin Bibb's administration had requested a one-year, $250,000 agreement, but council shortened the term while the city prepares to seek proposals from other automated license plate-reader vendors"
  `https://www.govtech.com/public-safety/3-ohio-cities-approve-automated-license-plate-reader-pacts`
- News: Cleveland Scene (alt-weekly) — 9-6 vote after "the city's Flock contract went null"; six no-voters named
  `https://www.clevescene.com/news/cleveland-city-council-warily-approves-flock-safety-renewal/`

**Search notes:** prior contract expiry 2026-06-29 sourced only from an advocacy video description — treated as low-confidence corroboration for the six-month math, not cited as fact. Dead end: the signed extension's exact end date not published.

---

### 4. Decatur Police Department — `il-decatur-pd`

- **renewal_date:** 2028-11 — confidence **low-medium**
- **contract_start:** 2021-03 (original 3-year lease, 60 cameras) — confidence **high**
- **contract_end:** 2028-11 — confidence **low-medium** (five-year renewal; exact date not pinned)
- **decision_date:** 2023-11 — confidence **medium**
- **Status implication:** active; mid-term on a five-year renewal.

**Sources:**
- Primary: Decatur City Council Resolution R2021-40 (via NovusAgenda/ALPRWatch FOIA PDF) — "lease of 60 LPR Cameras for the years 2021, 2022 and 2023... $165,000 for the year of 2021, $150,000 for each of the years of 2022 and 2023"; presented/adopted March 2021
  `https://decatur.novusagenda.com/agendapublic/AttachmentViewer.ashx?AttachmentID=8225&ItemID=3769`
- News: WCIA (Nexstar, ~Nov 2023) — "On Monday night, the Decatur City Council approved renewing their contract with Flock Safety... the contract extension with Flock Safety will keep the cameras in the city for another five years"; "total of 100 cameras"
  `https://www.wcia.com/news/decatur-extends-usage-of-license-plate-readers/`

**Search notes:** the WCIA page exposes no publication date; dated to Nov 2023 via the search index's "1066 days ago" relative timestamp converging with "Monday night" (Nov 6, 2023 was a Monday). This is the weakest date in the batch — flagged accordingly. Dead end: council minutes for the exact vote date not retrievable via text fetch.

---

### 5. Oklahoma City Police Department — `ok-oklahoma-city-pd`

- **renewal_date:** 2027-06-30 — confidence **high**
- **contract_start:** 2022-03 (initial deployment); expanded 2023-07 — confidence **medium**
- **contract_end:** 2027-06-30 — confidence **high**
- **decision_date:** 2026-08-18 — confidence **high** (5-3 council vote)
- **Status implication:** active; one-year $270,000 renewal with new guardrails (7-day retention, out of Flock national database).

**Sources:**
- News: The Oklahoman (2026-10-05) — "The Oklahoma City Police Department's contract with Flock Safety was recently renewed after a tense 5-3 vote by the Oklahoma City Council on Aug. 18. The $270,000 contract renewal... will go towards maintenance of the 90 active ALPR cameras"; "first began using Flock Safety cameras in March 2022 and further expanded their contract in July 2023"
  `https://www.oklahoman.com/story/news/crime/2026/10/05/flock-camera-search-tulsa-ok-deputy-ruled-unconstitutional-oklahoma-federal-judge/92107612007/`
- News: Oklahoma Gazette — "The renewed contract pays Flock Safety $270,000 through June 30, 2027 to continue to operate 90 cameras across the metro"
  `https://www.okgazette.com/news/okc-council-passes-flock-extension/`
- News: News9 — council voted to renew $270,000 contract "for another year"
  `https://www.news9.com/oklahoma-city-news/get-the-flock-out-okc-renews-camera-contract-with-new-privacy-guardrails`

**Search notes:** four independent outlets agree on the 5-3 vote, $270K, and one-year term; two state the June 30, 2027 end date explicitly. Minor discrepancy: one Oklahoman piece said "extending until July 2027" — going with the explicit June 30 date.

---

### Method notes (Batch C)

- All dates are traceable to the cited source; contract_end values marked medium/low are computed only where the source states both the term length and the start/decision date (per the brief's rule).
- Disregarded per policy: citizenportal.ai (AI-generated summaries, appeared twice), TikTok, change.org petitions.
- Used as leads only, not cited for dates: eyesonice.net, news.marionwatch.com (advocacy), soonersentinel.substack.com (blog).
- No files modified, no one contacted.

---

## Appendix D: Batch D report (Caldwell, College Station, Newport News, Everett, Fresno) — verbatim

Boss, here are my findings for the 5 agencies. Constraints honored: no files modified, no contact made, AI-generated summaries excluded entirely, no dates inferred from term lengths alone.

---

### 1. Caldwell Police Department (Caldwell, ID) — `id-caldwell-pd`

- **renewal_date:** not found
- **contract_start:** 2023 (year only, per existing record; exact vote date not found)
- **contract_end:** not found
- **Status implication:** No verified change. A reported Oct 5, 2026 council vote to approve a 10-year Axon bundle replacing Flock could NOT be verified: the only detailed write-ups are AI-generated (excluded per standards) or a Substack (weak). Do NOT mark cancelled on that basis.

**Dates/sources:**
- 2023 three-year, $378,000/year deal for 33 cameras, plus a later $42,000/year expansion for 28 more cameras. Source: GovTech article (news, secondary of Idaho Statesman reporting), https://www.govtech.com/public-safety/how-tech-is-transforming-police-work-in-idaho. Exact quote: council "in 2023 unanimously approved a three-year, $378,000-per-year deal with Flock for 33 cameras." Confidence: medium. Exact approval date not stated.
- Resolution 41-25 (2025): $30,000/year for 10 more cameras, with a 30-day written non-renewal notice clause and auto-renewal. Source: change.org petition quoting the resolution (advocacy, lead only), https://www.change.org/p/caldwell-is-not-a-surveillance-state-remove-flock-cameras/fbog/768754366/bsv. Corroborated in substance by Route Fifty (established news): "an initial $30,000 per-year-agreement with Flock as of a 2025 city document," https://www.route-fifty.com/digital-government/2026/08/all-eyes-flock-idaho-navigates-surveillance-technology-across-state/415247/. Confidence: low for the clause terms (single advocacy source), medium that the 2025 $30k/yr agreement exists.
- Lead (unverified, do not cite as source): police chief proposed in June 2026 to bundle with Axon to "replace Flock"; council reportedly voted 4-1 on Oct 5, 2026 for a 10-year, $6.7M Axon contract expanding ALPRs 45 to 65. No acceptable source found.

**Dead ends:** Caldwell CivicClerk portal (caldwellid.api.civicclerk.com) attachments are indexed but I could not locate the Oct 2026 agenda/minutes via search; cityofcaldwell.org site search returned nothing on the Axon vote; no Idaho Press/KTVB/KIVI coverage found. Recommended follow-up: pull Caldwell council minutes for Oct 5, 2026 and the 2023 Flock approval directly from CivicClerk.

---

### 2. College Station Police Department (College Station, TX) — `tx-college-station-pd`

- **renewal_date (decision):** 2026-09-24 (council voted 4-2 to renew)
- **renewal_date (next):** ~2027-09, inferred from one-year term. Low confidence, not a confirmed date.
- **contract_start:** 2025-09 (month precision; original approval "in September 2025")
- **contract_end:** not found (exact)
- **Status implication:** Contract renewed and active for another year. No cancellation.

**Dates/sources:**
- Sept 24, 2026: "The Council voted 4-2 to approve an agreement not to exceed $158,000 with Flock Group for automatic license plate readers on Texas Department of Transportation roads and a $141,062 agreement for cameras on non-TxDOT roads. Councilmen Mark Smith and Bob Yancy voted against the motion." Source: City of College Station official blog, https://blog.cstx.gov/2026/09/24/live-from-city-hall-thursdays-city-council-meeting-sept-24/. Type: primary. Confidence: high.
- Original contract "approved for $395,098.10 in September 2025" and described as a "yearly renewal." Source: The Battalion (Texas A&M student paper, bylined), https://thebatt.com/news/college-station-city-council-to-vote-on-400000-flock-safety-contract/. Type: news. Confidence: medium.
- Corroboration: DeFlock BCS (advocacy): "On Thursday, September 24, the College Station City Council voted 4-2 to renew the city's contracts with Flock Safety. The city's license plate reader network stays on for another year." https://www.deflockbcs.com/news/college-station-council-renews-flock-4-2/. Type: advocacy. Confidence: low, corroborating only.

**Dead ends:** Exact day of the September 2025 original approval not found; the Sept 24, 2026 agenda item (9.6) with the agreements' exact term dates was not fetched. Note the renewal total ($299,062) is less than the original ($395,098.10); two separate agreements (TxDOT vs non-TxDOT roads).

---

### 3. Newport News Police Department (Newport News, VA) — `va-newport-news-pd`

- **renewal_date:** ~2027-09 to 2027-10 (autumn 2027), inferred. Low confidence.
- **contract_start:** not found (exact)
- **contract_end:** not found (exact)
- **Status implication:** Active. No council vote to cancel; advocacy analysis states "nothing on the books expires before Election Day" and the 74-unit order "run[s] to autumn 2027 at the earliest."

**Dates/sources:**
- PO 20251698-04: Falcon LPR, "ordered 24 Sep 2024 as 44 units ($132,000); modification no. 1 on 2 Oct raised it to 74," 74 units at $3,000 = $222,000. FY2026 PO 20262168: 15 units, $37,500. Source: deflocknewportnews.org "Follow the money" section, citing Virginia FOIA purchase orders published on DocumentCloud, https://deflocknewportnews.org/. Type: advocacy citing primary docs. Confidence: low-medium for the PO dates/amounts (I did not open the underlying DocumentCloud POs).
- Contract mechanics, quoting the site's reading of the agreements: "Each agreement runs 36 months... if council does nothing, every agreement *renews itself* for another 24 months unless notice goes out at least 30 days before the term ends." Same source. Confidence: low (advocacy interpretation of contract language I could not independently verify).
- Drone contract 26-1342-00 (RFP 26-1342-1403): $2.64M, 36-month, "renewable for a further 36 months." Same source. Confidence: low.

**Dead ends:** The DocumentCloud PO links from the advocacy page did not resolve through my fetches (outlink indices mismatched, one opened an unrelated PowerDMS policy). The 36-month term start date for the Falcon orders is not pinned to a specific day, so autumn 2027 is a window, not a date. Recommended follow-up: open the DocumentCloud "full Newport News set" directly and read PO 20251698-04 / the underlying Flock order form for exact subscription term dates.

---

### 4. Everett Police Department (Everett, WA) — `wa-everett-pd`

- **renewal_date:** not found
- **contract_start / contract_end:** not found
- **Status implication:** Program PAUSED since 2026-02-25, not confirmed cancelled. The "active" listing is misleading as to operations, but the contract's legal status is unknown. Recommend a status note, not a status change, until a termination is documented.

**Dates/sources:**
- Feb 25, 2026: "The mayor has asked the staff to temporarily turn off license plate reader cameras until they learn the result of legislation action in Olympia," after the city lost a court case requiring public disclosure of ALPR records. Mayor Cassie Franklin, at that day's council meeting, also issued Mayoral Directive 2026-01. Source: My Everett News (local news, quoting the mayor), https://myeverettnews.com/2026/02/25/everett-mayor-automated-license-plate-readers/. Type: news. Confidence: medium-high for the pause and date.
- Corroboration: Liberation News: "Less than a week later [after Lynnwood's February cancellation], the mayor of neighboring Everett announced that Everett would temporarily pause Flock cameras," https://liberationnews.org/nationwide-communities-say-get-flock-off-our-streets-no-mass-surveillance/. Type: news (activist outlet). Confidence: low, corroborating only.
- SeattleRed claims "paused or canceled" (https://seattlered.com/immigration/wa-cities-cancel-flock-cameras/4117033) — weak partisan outlet, lead only.

**Dead ends:** No Everett council vote to terminate, no contract document, no reinstatement/legislative outcome found. The Flock transparency portal for Everett WA PD still exists (vendor page, not a contract source). Searched KOMO-referenced reporting; no primary city statement beyond the mayor's announcement surfaced.

---

### 5. Fresno Police Department (Fresno, CA) — `ca-fresno-pd`

- **renewal_date:** not found (exact). Mechanics below give the framework.
- **contract_start:** not found (exact). Council approved the agreement 2024-02-22; the agreement states "The Term shall commence upon execution," and the published version's signature page is undated.
- **contract_end:** not found (exact; would be 36 months after execution, roughly Feb-Mar 2027 if executed promptly after approval, but that is inference, not a sourced date).
- **Status implication:** Active. No cancellation evidence.

**Dates/sources (all primary):**
- Feb 22, 2024: Council ADOPTED item ID 24-204: "Approve the updated Agreement between the City of Fresno Police Department and Flock Safety, in an amount not to exceed $1,498,690.41 for three (3) years for the subscription services of Automated License Plate Readers (ALPR), cameras, and software." Source: Fresno Legistar meeting record, https://fresno.legistar.com/MeetingDetail.aspx?ID=1145527&GUID=845026A9-DF6F-418C-97EE-20A4B8B474E2&Options=&Search=. Confidence: high. (The same agreement first appeared on the Dec 14, 2023 agenda as ID 23-1704.)
- Signed agreement, Order Form: "Initial Term: 36 Months," "Renewal Term: 24 Months," "Contract Total: $1,498,690.41." Section 7.1: "The initial term of this Agreement shall be for the period of time set forth on the Order Form (the 'Term'). Following the Term... this Agreement will automatically renew for successive renewal terms of the greater of one year or the length set forth on the Order Form... unless either Party gives the other Party notice of non-renewal at least thirty (30) days prior to the end of the then-current term." Source: agreement PDF via City of Fresno agendas, https://agendas.fresno.gov/api/v1/attachments/cmq0gq83x25k8peeiia47sczk/file. Confidence: high.
- Note: a prior Fresno Flock contract existed since 2023 (per local TV reporting); the Feb 2024 item was an "updated Agreement."

**Dead ends:** Execution (signature) date not in the published agenda attachment; the 36-month end date therefore cannot be fixed. Recommended follow-up: Fresno city clerk contract records for the executed copy.

---

### Cross-cutting notes (Batch D)

- **Verified decision dates:** College Station 2026-09-24 (renewal approved, high); Fresno 2024-02-22 (agreement adopted, high); Everett 2026-02-25 (program paused, medium-high).
- **No exact renewal/contract-end date** could be sourced for Caldwell, Newport News, Everett, or Fresno. Newport News (~autumn 2027) and College Station (~Sept 2027) next-renewal windows are inferences from stated term lengths plus order/vote dates; labeled low confidence and not to be entered as verified dates.
- **Two records likely mislabeled "active" in spirit:** Everett (program paused since Feb 2026) and Caldwell (reported Axon replacement, unverified). Neither has a documented contract termination, so status notes rather than status changes are recommended.
- citizenportal.ai appeared repeatedly in results and was excluded in full per the editorial rule; change.org, deflockbcs.com, deflocknewportnews.org, seattlered.com, misryoum.com, and Substack pieces were used as leads/corroboration only, never as the basis for a date.

---

## CI test failure incident (2026-10-09, runs 163-164)

**Problem:** The archive workflow's "Run test suite" step failed twice consecutively (runs 163, 164) immediately after the 14:41 ET adversarial-review release (94fa456020c5). Runs 155-162 (pre-release) all succeeded. Two consecutive failures; alert threshold is 3.

**Root cause:** `scripts/tests/test_fetch_client.py:86` asserted `client.backend == "urllib"` with the comment "curl_cffi not installed here." The GitHub Actions workflow installs `curl-cffi>=0.13` via `scripts/requirements.txt`, so in CI the backend is `"curl_cffi"` and the assertion fails. The test was written on a machine without curl_cffi (this VM) and never tested with it installed.

**Why it slipped through:** The 168 tests passed locally because curl_cffi is not installed on this VM. The CI environment differs. The test called `client._fetch_urllib` directly (correctly testing the fallback), making the backend assertion both unnecessary and wrong.

**Fix:** Removed the backend assertion (2026-10-09). The test now exercises `_fetch_urllib` directly regardless of default backend. Verified: 168 tests pass locally.

**Process lesson:** Tests must not assert environment-specific state. The sibling test at `test_fingerprints.py:261` does this correctly: `assertIn(c.backend, ("curl_cffi", "urllib"))`. When adding requirements.txt dependencies, re-run the suite with them installed (or mock their presence) before release.

**Status:** Fixed locally. NOT pushed; CI will continue failing until the fix reaches main.

---

## Paywalled sources policy (2026-10-09, Boss decision)

Two Oklahoman citations on `ok-oklahoma-city-pd` (2026-08-03 and 2026-08-18, both about the renewal vote) were removed. They returned HTTP 402 (paywall) and the drift gate correctly refused to push while they were unverifiable.

**Policy:** Paywalled sources are not worth the trouble. A citation the drift gate cannot re-fetch is a citation that cannot be verified, and an unverifiable citation is dead weight in the dataset. Prefer freely accessible sources; when a paywalled outlet is the only source, find corroboration in an accessible outlet or do not cite it. The two removed articles were redundant with fetchable coverage (News9, OKC.gov, and a later Oklahoman article that remains accessible), so no information was lost.
