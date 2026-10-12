# Flock-Off research round 3 briefs — contract start/end hunt

Prepared 2026-10-09 (evening) for the standing research-throughput priority.
Strategy carries round 2 forward: hunt **contract start/end dates** (not renewal dates);
council votes and procurement records beat news coverage. 20 agencies in 4 batches of 5.

## Selection

- Pool: active records with no contract_start/contract_end/renewal_date on file,
  camera count in the 25-130 sweet spot (round-2 rationale: larger buries below council
  thresholds, smaller has no formal procurement). Two 24-camera high-confidence records
  (Salina KS, Renton WA) fill the 4x5 pattern; they sit one camera below the band.
- Excluded: all 20 round-1 agencies and the 11 known round-2 agencies.
  Caveat: 9 round-2 agencies are not individually documented; if any brief below
  duplicates a round-2 target, drop it and pull the next alternate (nm-las-cruces-pd,
  ny-niagara-falls-pd).
- Jurisdiction caution: **mi-troy-pd is Troy, Michigan** — not Troy NY (ny-troy-pd,
  researched in round 2). Keep the two cities strictly separate.

## Research constraints (unchanged)

- Primary records preferred (council minutes, agendas, procurement docs); established
  news secondary; AI-generated summaries excluded on sight; no outreach; no dataset edits.
- Paywalled sources are not worth the trouble (standing policy 2026-10-09): if the only
  citation for a date is paywalled, report the date as unverifiable, do not file it.
- Report confidence per date; month-level precision is acceptable when the source only
  supports month-level (e.g. contract_start=2021-03).

## Batch A

### Queen Creek Police Department (`az-queen-creek-pd`)
- Queen Creek, AZ | municipal_police | cameras: 62 | confidence: high
- On file: {'decision_date': '2026-09-02'} | sources on record: 3 | last_verified: 2026-09-25
- Decision context: Town Council unanimously criminalized misuse of the town's Flock system (up to 6 months jail, $2,500 fine) while keeping the contract, the first Arizona city with such penalties.
- Notes: Camera count 62 per Sept 2026 reporting; azcentral's Aug 16 list said 47, suggesting expansion. Town is also testing 15 Axon ALPR cameras separately.

### Kenner Police Department (`la-kenner-pd`)
- Kenner, LA | municipal_police | cameras: 55 | confidence: high
- On file: {'decision_date': '2022-12'} | sources on record: 3 | last_verified: 2026-09-25
- Decision context: City Council approved a two-year, $294,250 Flock ALPR contract in Dec 2022, growing the network to 55 cameras; still reported active in 2026.
- Notes: City Council approved a two-year Flock contract totaling $294,250 in Dec 2022 (GovTech/Tribune News Service); annual figure not published and not derived here. The city's 2023 newsletter confirms the $294,250 system. Shr

### Lafourche Parish Sheriff's Office (`la-lafourche-parish-so`)
- Thibodaux, LA | county_sheriff | cameras: 54 | confidence: high
- On file: no dates | sources on record: 2 | last_verified: 2026-09-25
- Decision context: Lafourche Parish Sheriff's Office operates 54 Flock cameras, used daily per its public information officer; two independent Gannett outlets confirmed the count.
- Notes: LPSO operates 54 Flock cameras; its public information officer says the system is used daily (Houma Today, 2026-08-03). Shreveport Times independently lists 54 cameras as of July 2026. Contract dates and cost not found i

### Green Bay Police Department (`wi-green-bay-pd`)
- Green Bay, WI | municipal_police | cameras: 42 | confidence: high
- On file: {'decision_date': '2026-09-14'} | sources on record: 3 | last_verified: -
- Decision context: Green Bay's mayor and police chief announced Sept 14, 2026 the city will keep its Flock cameras under a new ALPR policy: data retention cut from 30 days to 7, every search requires a case/call number and stated reason, l
- Notes: Camera count 42 (Sept 2026 reporting) vs 43 in Atlas as of April 2024. Decision was explicitly to retain, amid statewide cancellations.

### Elizabethtown Police Department (`ky-elizabethtown-pd`)
- Elizabethtown, KY | municipal_police | cameras: 40 | confidence: high
- On file: {'decision_date': '2023-12-08'} | sources on record: 2 | last_verified: -
- Decision context: Signed Flock order form (primary record): 60-month initial term, 40 Falcon cameras, $100,000 annual recurring ($114,400 year 1 with implementation), contract total $514,400, 30-day retention, executed 12/8/2023 by Chief 
- Notes: Term 'commences upon first installation and validation of Flock Hardware', so exact contract_start unknown; used signature date as decision_date. Atlas summary said 'began using in 2022'; this signed 2023 contract may be

## Batch B

### Vernon Hills Police Department (`il-vernon-hills-pd`)
- Vernon Hills, IL | municipal_police | cameras: 28 | confidence: high
- On file: no dates | sources on record: 2 | last_verified: -
- Decision context: The Village of Vernon Hills contracted with Flock Safety for 28 ALPR units in phases: 10 effective February 2022, 6 more in March 2023, and the remaining 12 in August 2023. The department maintains a Flock transparency p
- Notes: Per the village's official ALPR page (primary). The initial ~2021 approval covered 10 stationary cameras at $20,000/year (GovTech/TNS); post-expansion annual cost not reported, so annual_cost_usd left null. Initial board

### Marion County Sheriff's Office (`wv-marion-county-so`)
- Fairmont, WV | sheriff | cameras: 41 | confidence: medium
- On file: no dates | sources on record: 1 | last_verified: -
- Decision context: Times West Virginian (~late Jul 2026) reports the Marion County Sheriff's Office operates 41 Flock Safety license plate reader cameras; Sheriff Roger Cunningham publicly defended continued use, noting 30-day retention, V
- Notes: Flock transparency portal (inaccessible, HTTP 403) reportedly listed 20 cameras as of Sept 2025; the sheriff's office stated 41 in ~July 2026 - used the newer, fetched figure. Camera deployment postdates a 2022 shooting 

### Lorain Police Department (`oh-lorain-pd`)
- Lorain, OH | municipal_police | cameras: 40 | confidence: medium
- On file: {'decision_date': '2023-02-08'} | sources on record: 2 | last_verified: -
- Decision context: Lorain City Council approved a five-year agreement with Flock Group Inc. for 40 license plate readers, not to exceed $531,500, funded from the city's American Rescue Plan Act share.
- Notes: $531,500 is the five-year total, not annual; annual_cost_usd null. Independent of the Lorain County Sheriff's discontinued program. Cameras recently used in the capture of a juvenile murder suspect (Sept. 2026).

### Decatur Police Department (`al-decatur-pd`)
- Decatur, AL | municipal_police | cameras: 40 | confidence: medium
- On file: no dates | sources on record: 3 | last_verified: -
- Decision context: WAFF reported in July 2026 that more than 40 Flock cameras were operating in Decatur and had been in place for about three years. The Decatur Daily (March 2025) confirmed DPD uses Flock cameras to solve crimes.
- Notes: WAFF phrasing is 'more than 40'; cameras=40 is the reported lower bound, July 2026. The EFF Atlas lead lists 44 as of Sept 2025 (unverified, not used). No cost, contract start/end, or renewal date found. Not to be confus

### Rhode Island State Police (`ri-state-police`)
- None, RI | state_police | cameras: 39 | confidence: medium
- On file: no dates | sources on record: 2 | last_verified: 2026-09-25
- Notes: agency_type 'sheriff' is a placeholder: schema lacks a state_police value. $597,000 three-year contract; term begins when all cameras installed. RISP policy: data not shared with other states or federal agencies incl. IC

## Batch C

### Terrebonne Parish Sheriff's Office (`la-terrebonne-parish-so`)
- Houma, LA | county_sheriff | cameras: 39 | confidence: medium
- On file: no dates | sources on record: 2 | last_verified: 2026-09-25
- Decision context: Terrebonne Parish Sheriff's Office operates 39 Flock cameras and spent $465,000 in opioid-settlement funds on them; Flock presented to the parish council in May 2023.
- Notes: TPSO has 39 Flock cameras installed throughout the parish (Houma Today, 2026-08-03); the agency spent $465,000 in opioid-settlement funds on Flock cameras (investigative reporting, Sept 2026). A Flock presentation to the

### Greenville County Sheriff's Office (`sc-greenville-county-sheriff`)
- Greenville County, SC | sheriff | cameras: 32 | confidence: medium
- On file: no dates | sources on record: 1 | last_verified: 2026-09-25
- Notes: County budget funds 32 LPRs (29 fixed, 1 pending install, 4 offline from damage, plus 3 portable). Sheriff Hobart Lewis told the county Public Safety Committee each camera costs $3,500/yr plus $900 one-time install; coun

### Ottawa County Sheriff's Office (`mi-ottawa-county-so`)
- None, MI | sheriff | cameras: 31 | confidence: medium
- On file: no dates | sources on record: 1 | last_verified: -
- Decision context: Use approved by the county board in spring 2024. Sheriff Eric DeBoer told the board on September 18, 2026 that the county operates 31 Flock cameras and pays $45,000 per year for its 15 county-owned cameras; two mobile an
- Notes: $45,000/yr covers the 15 county-owned cameras; 16 additional cameras operate under township pass-through agreements. decision_date left null (only 'spring 2024' reported).

### Milwaukee Police Department (`wi-milwaukee-pd`)
- Milwaukee, WI | municipal_police | cameras: 27 | confidence: medium
- On file: {'decision_date': '2026-08-31'} | sources on record: 3 | last_verified: -
- Decision context: Milwaukee chose not to cancel. On Aug 31, 2026 Mayor Cavalier Johnson and MPD announced tightened policies after officer-misuse investigations (three officers investigated, including stalking of a romantic partner): only
- Notes: Camera count 27 is from Atlas (Aug 2023) with plans for 8 more; current count not confirmed. Separate from Milwaukee County Sheriff's Office and county-level funding decisions.

### Euclid Police Department (`oh-euclid-pd`)
- Euclid, OH | municipal_police | cameras: 26 | confidence: medium
- On file: no dates | sources on record: 2 | last_verified: -
- Decision context: Euclid Ordinance 040-22 (April 2022 public safety committee agenda, primary document) authorized the mayor to enter a two-year Flock Safety camera contract, with a two-year renewal option, not to exceed $110,000. Flock's
- Notes: Camera count is agency self-reported on Flock's portal (unverified flag kept). $110,000 NTE figure may be the two-year total; annual_cost_usd left null. decision_date left null: April 20, 2022 is the committee agenda dat

## Batch D

### Troy Police Department (`mi-troy-pd`)
- Troy, MI | municipal_police | cameras: 25 | confidence: medium
- On file: no dates | sources on record: 1 | last_verified: -
- Decision context: Troy's March 8, 2023 council agenda item recommended awarding a 2-year Flock Safety contract via Insight Public Sector (OMNIA contract 4400006644): 23 Falcon LE cameras at $2,500/yr and 2 Falcon Flex portable cameras at 
- Notes: annual_cost_usd = $66,000 is the recurring year-2 subscription figure (reported directly); year 1 was $74,050 including one-time implementation. Camera count 25 = 23 fixed + 2 portable per the attached vendor quote #0225

### Tulsa County Sheriff's Office (`ok-tulsa-county-so`)
- None, OK | county_sheriff | cameras: 25 | confidence: medium
- On file: no dates | sources on record: 3 | last_verified: 2026-09-25
- Decision context: County commissioners approved a 25-camera pilot in June 2022; Sheriff Vic Regalado later inked a contract and the office was still actively using Flock as of Aug 2026 while reviewing a seven-day retention recommendation.
- Notes: Exact transition from free pilot to paid contract and current contract terms not verified. News9 Aug 2026 reporting confirms continued active use. Medium confidence, not high, until a current contract or official stateme

### Van Buren Township Police Department (`mi-van-buren-twp-pd`)
- None, MI | municipal_police | cameras: 30 | confidence: low
- On file: {'decision_date': '2021-11-16'} | sources on record: 2 | last_verified: -
- Decision context: On November 16, 2021 the Van Buren Township Board of Trustees voted unanimously to approve a $75,000 contract with Flock Safety for 30 cameras at $2,500 per camera per year. The Downtown Development Authority later agree
- Notes: decision_date is the board meeting date (article reports the vote at the Nov. 16 meeting). Cost is annual subscription; equipment not purchased, installation included.

### Salina Police Department (`ks-salina-pd`)
- Salina, KS | municipal_police | cameras: 24 | confidence: high
- On file: {'decision_date': '2026-06-01'} | sources on record: 4 | last_verified: 2026-09-25
- Decision context: On 2026-06-01 the Salina City Commission voted 4-1 to renew the Flock Safety contract for three years covering 22 fixed and 2 portable ALPRs, despite public opposition over privacy. The prior contract dated to 2023 and e
- Notes: Renewal date confirmed by two independent local outlets (Salina Post and salina311). Contract end date of the renewed term not stated in cited sources; left null rather than inferred. Cost detail: June 2026 three-year re

### Renton Police Department (`wa-renton-pd`)
- Renton, WA | municipal_police | cameras: 24 | confidence: high
- On file: {'decision_date': '2026-05-04'} | sources on record: 6 | last_verified: 2026-09-25
- Decision context: Renton began a Flock trial in 2024 on a two-year contract at $88,240/yr with 24 cameras. After UW researchers found Border Patrol queries of Renton's system in 2025, the department locked down outside access. The city cy
- Notes: Camera count (24) from an Issaquah PD city government presentation (Feb 2025) and a KOMO News segment description; contract cost ($88,240/yr, 2-year, began 2024) from the Renton Public Safety Committee agenda (government

