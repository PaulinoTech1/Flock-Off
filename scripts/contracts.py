#!/usr/bin/env python3
"""Contracts page registry for Flock-Off.

The Contracts tab lists the actual contract documents behind tracker
records: signed agreements, and the authorizing instruments (resolutions,
legislation, agenda approvals) that create, renew, extend, or terminate
them. News articles and official statements ABOUT a contract do not
qualify; the linked document must BE the contract or its authorizing
instrument.

The registry is an explicit, human-curated allowlist keyed by the
dataset's canonical source_key. Nothing is inferred from title keywords
at build time, so a document appears here only because a reviewer read
it and classified it. Two kinds:

- "signed_agreement": the document is the contract itself (signed
  agreement, services agreement, or order form).
- "instrument": a resolution / legislative item / agenda attachment
  that authorizes, renews, extends, or terminates the contract.

"Accurate as of" on the page is the agency record's `last_verified`
date: the last date a reviewer checked the record against its sources.
It is NOT the document's date and NOT a claim that the contract is
still in force today; status comes from the tracker record.

Fail-closed: build_contract_entries() raises if a registry source_key
is missing from the dataset, so a renamed or removed citation breaks
the build instead of silently dropping a contract from the page.

Stdlib only.
"""
from __future__ import annotations

# Each entry: (agency_id, source_key, kind, doc_note)
# doc_note says what the document is, in one line, including any
# provenance caveat (FOIA release, reporter-hosted copy).
REGISTRY = [
    # --- Signed agreements: the document IS the contract ---
    (
        "ks-wichita-pd",
        "https://wichitaks.granicus.com/services/legistar/download/pdf/2900778/KS_-_Wichita_PD_-_Law_Enforcement_Agreement_-___8_.pdf",
        "signed_agreement",
        "The signed Law Enforcement Agreement between Flock Group Inc. and Wichita PD, served from the city's Legistar system.",
    ),
    (
        "ks-park-city-pd",
        "https://legistarweb-production.s3.amazonaws.com/uploads/attachment/pdf/1005584/Flock_Safety-Contract_Park_City_PD_KS__1___1_.pdf",
        "signed_agreement",
        "Flock Group Inc. Services Agreement order form for Park City, KS, filed as a council attachment.",
    ),
    (
        "ia-urbandale-pd",
        "https://urbandale.civicweb.net/document/35459/Professional%20Services%20Agreement%20-%20Automated%20Lic.pdf?handle=19EF686CDA154D40A9FDC715FC61F6FF",
        "signed_agreement",
        "Professional Services Agreement for automated license plate readers, filed with Urbandale Council Letter 7492 (FY24).",
    ),
    (
        "md-forest-heights-pd",
        "https://go.boarddocs.com/md/tofhmd/Board.nsf/files/DEWLR457C030/$file/MD%20-%20Forest%20Heights%20PD%20-%20Law%20Enforcement%20Agreement%20-%20%20(2)%20(1)%20(1).pdf",
        "signed_agreement",
        "The Law Enforcement Agreement between Flock Safety and the Town of Forest Heights, filed in the town's BoardDocs.",
    ),
    (
        "nm-las-cruces-pd",
        "https://haussamen.com/wp-content/uploads/2026/02/NM-Las-Cruces-PD-FlockOSLPRLive-Video-Law-Enforcement-Agreement-9122024.pdf",
        "signed_agreement",
        "Signed FlockOS LPR / live-video Law Enforcement Agreement (dated 2024-09-12 in the filename). Provenance: public-records release hosted on a journalist's site, not a government server, and the citation is not yet classified verified in the dataset.",
    ),
    # --- Authorizing instruments ---
    (
        "nj-north-brunswick-pd",
        "https://live-township-of-north-brunswick.pantheonsite.io/wp-content/uploads/2025/09/302-9.25-Authorizing-A-Proprietary-Contract-with-Flock-Safety-for-Automated-License-Plate-Reader-1.pdf",
        "instrument",
        "Township Resolution 302-9.25 authorizing the proprietary Flock ALPR contract.",
    ),
    (
        "ca-fresno-pd",
        "https://fresno.granicusideas.com/meetings/776-city-council-on-2024-02-22-9-00-am-regular-meeting/agenda_items/65cfdd83f395e7e05600c6fb-2-dot-z-id-24-204-approve-the-updated-agreement-betw",
        "instrument",
        "Council agenda item ID 24-204 approving the updated agreement between Fresno PD and Flock Safety.",
    ),
    (
        "ne-kearney-pd",
        "https://kearney.granicus.com/MetaViewer.php?clip_id=526&meta_id=43147&view_id=1",
        "instrument",
        "Resolution No. 2023-178 extending the Flock Group Inc. 60-month Services Agreement.",
    ),
    (
        "ne-sarpy-county-so",
        "https://sarpy.civicweb.net/document/81906/Resolution%202023-231%20-%20Flock%20Safety%20Agreement%20and%20M.pdf?handle=3836CED6AD5143F19AC4159C4A256CC3",
        "instrument",
        "Resolution 2023-231 adopting the Flock Safety agreement and MOU ($46,300; $43,000 annual renewal per the agenda item).",
    ),
    (
        "ar-little-rock-pd",
        "https://littlerock.gov/city-administration/board-of-directors/meeting-agenda/AGENDA - WEB - 10-21-2025/R%20-%20Flock%20License%20Plate%20Reader%20Camera%20Software.pdf",
        "instrument",
        "Board of Directors resolution authorizing the two-year Flock software subscription renewal ($690,000).",
    ),
    (
        "tx-dallas-pd",
        "https://cityofdallas.legistar.com/LegislationDetail.aspx?FullText=1&GUID=FDDAEA7D-A941-4B35-8A9D-318FF351CAE4&ID=7404358",
        "instrument",
        "City of Dallas legislative item approving the Flock Safety contract (term 2025-06-15 to 2028-06-14 in the tracker record).",
    ),
    (
        "wa-lynnwood-pd",
        "https://legistarweb-production.s3.amazonaws.com/uploads/attachment/pdf/3078028/PD_ALPR_Program_-_Waiver_Request___Contract_Approval_final.pdf",
        "instrument",
        "Official procurement document: waiver request and contract approval for the Lynnwood PD ALPR program (25 cameras, $171,153.50, 2 years, per the document).",
    ),
    (
        "va-harrisonburg-pd",
        "https://meetings.cvilledata.org/meetings/harrisonburg/1422203-city-council-meeting-2026-07-28/attachments/15723134-Resolution.pdf",
        "instrument",
        "Resolution RES 26-005 terminating the Flock Safety contract (contract ran 2023-06-30 to 2026-07-31 in the tracker record).",
    ),
    (
        "ny-ithaca-pd",
        "https://legistarweb-production.s3.amazonaws.com/uploads/attachment/pdf/3942354/Trumble_-_RESOLUTION_TO_END_THE_CITY_S_RELATIONSHIP_WITH_FLOCK_SAFETY_-_final_2_26.pdf",
        "instrument",
        "Common Council resolution to end the City of Ithaca's relationship with Flock Safety, filed in Legistar.",
    ),
    (
        "il-decatur-pd",
        "https://alprwatch.org/pub/muckrock/data/156449-foia-request-flock-safety/R2021-40_Resolution_Authorizing_a_Lease_Agreement_Between_the_City_of_Decatur_and_Flock_Safety_for_the_Deployment_of_60_LPR_Cameras_in_the_City_Neighborhoods_and_Adjacent_Thoroughfares.pdf",
        "instrument",
        "Resolution R2021-40 authorizing the lease agreement for 60 LPR cameras. Provenance: public-records (MuckRock) release hosted by ALPR Watch; the citation is not yet classified verified in the dataset.",
    ),
]

KINDS = frozenset({"signed_agreement", "instrument"})
KIND_LABELS = {
    "signed_agreement": "Signed agreement",
    "instrument": "Authorizing instrument",
}


def build_contract_entries(agencies: list) -> list:
    """Join the registry against the dataset.

    Returns one entry per registry row, in registry order, carrying the
    document fields from the cited source and the contract facts from
    the agency record. Raises ValueError on any registry row that does
    not resolve, so data drift fails the build loudly.
    """
    by_id = {}
    for a in agencies:
        by_id.setdefault(a.get("id"), a)
    entries = []
    for agency_id, source_key, kind, doc_note in REGISTRY:
        if kind not in KINDS:
            raise ValueError(f"contracts registry: unknown kind {kind!r}")
        rec = by_id.get(agency_id)
        if rec is None:
            raise ValueError(
                f"contracts registry: agency {agency_id!r} not in dataset")
        src = None
        for s in rec.get("sources") or []:
            if s.get("source_key") == source_key:
                src = s
                break
        if src is None:
            raise ValueError(
                f"contracts registry: source_key for {agency_id!r} not "
                f"found in its sources ({source_key})")
        entries.append({
            "agency_id": agency_id,
            "agency": rec.get("agency"),
            "city": rec.get("city"),
            "state": rec.get("state"),
            "status": rec.get("status"),
            "kind": kind,
            "kind_label": KIND_LABELS[kind],
            "doc_title": src.get("title") or src.get("url"),
            "doc_url": src.get("url"),
            "doc_date": src.get("date"),
            "doc_verified": bool(src.get("verified")),
            "doc_note": doc_note,
            "contract_start": rec.get("contract_start"),
            "contract_end": rec.get("contract_end"),
            "renewal_date": rec.get("renewal_date"),
            "annual_cost_usd": rec.get("annual_cost_usd"),
            "cameras": rec.get("cameras"),
            # "Accurate as of": last date the record was checked
            # against its sources. None means never re-verified.
            "accurate_as_of": rec.get("last_verified"),
        })
    return entries
