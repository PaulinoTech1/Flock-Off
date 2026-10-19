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
        "Signed FlockOS LPR / live-video Law Enforcement Agreement. Provenance: public-records release hosted on a journalist's site, not a government server, and the citation is not yet classified verified in the dataset.",
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
    (
        "tn-millington-pd",
        "https://millingtontn.gov/AgendaCenter/ViewFile/Item/4271?fileID=5051",
        "instrument",
        "Resolution 3-2024 (adopted 2024-01-08) approving Millington PD's contract with Flock Group Inc: maintenance and support for 19 cameras at $47,500 per year for five years, with an option to renew for two more years. All figures are the resolution's own stated terms.",
    ),
    (
        "ks-wichita-pd",
        "https://wichitaks.granicus.com/services/legistar/download/pdf/2912126/Agenda_Report_VI-7.pdf",
        "instrument",
        "City Council Agenda Report VI-7 (October 15, 2024) recommending approval of the contracts with Flock Safety: 10 additional Falcon LPR devices under a five-year agreement at $151,500, and 21 additional Falcon readers under a two-year agreement at $186,150 for year one. The signed Wichita agreement is also on this page.",
    ),
    (
        "ks-derby-pd",
        "https://derby.civicweb.net/document/21142/Flock%20License%20Plate%20Reader%20Cameras.pdf?handle=D1F9EFA8485941DC8A177D0D117C152B",
        "instrument",
        "City Council consent agenda item (October 26, 2021); the recommended motion reads: 'Approve the purchase of seven Flock cameras including installation for a two year period for $36,750.'",
    ),
    (
        "ia-coralville-pd",
        "https://coralville.org/AgendaCenter/ViewFile/Minutes/_02242026-1949",
        "instrument",
        "City Council minutes (February 24, 2026) recording adoption of Resolution No. 2026-16, 'Resolution terminating the Agreement with Flock Group and rescinding Police Policy regarding Automated License Plate Readers' (vote 3-1, one absent).",
    ),
    (
        "ca-fresno-pd",
        "https://agendas.fresno.gov/api/v1/attachments/cmq0gq83x25k8peeiia47sczk/file",
        "signed_agreement",
        "Executed order form (Exhibit A) with the Master Services Agreement between Flock Group, Inc. and the City of Fresno: 36-month initial term, annual recurring $492,000, contract total $1,498,690.41. The council item approving the updated agreement (ID 24-204) is also on this page.",
    ),
    (
        "wa-olympia-pd",
        "https://alprwatch.org/pub/muckrock/data/199260-flock-email-metadata-and-contracts/FLOCK_ALPR.pdf",
        "signed_agreement",
        "Signed order form between Flock Group, Inc. and the City of Olympia (signed March 28-29, 2024): 15 Falcon cameras, 24-month initial term, contract total $90,000 billed at signing. Provenance: public-records release hosted by ALPR Watch (MuckRock), not a government server.",
    ),
    (
        "il-decatur-pd",
        "https://alprwatch.org/pub/muckrock/data/156449-foia-request-flock-safety/R2023-231_Resolution_Authorizing_a_Five_Year_Lease_Agreement_Extension_Between_the_City_of_Decatur_and_Flock_Safety_for_LPR_Cameras_in_the_City_Neighborhoods_and_Adjacent_Thoroughfares.pdf",
        "instrument",
        "Resolution R2023-231 (adopted November 6, 2023) authorizing a five-year lease agreement extension with Flock Safety: 100 LPR cameras for 2024 through 2028, payments not to exceed $250,000 per year. Provenance: public-records (MuckRock) release hosted by ALPR Watch; text verified against the city's official agenda attachment.",
    ),
    (
        "tn-johnson-city-pd",
        "https://johnsoncitytn.civicweb.net/document/322557/Flock%20Group%20Inc.%20dba%20Flock%20Safety_Flock%20Safety%20.pdf?handle=FFC6987687084379BCCF1920802EF93D",
        "instrument",
        "City Commission agenda summary packet (approved July 17, 2025) for a resolution authorizing a 10-year licensing and purchasing agreement with Flock Group Inc. dba Flock Safety: contract total $8,063,000, procured via OMNIA cooperative contract #RS250203. The packet includes the Flock Safety statement of work (draft revision 1.0).",
    ),
    (
        "tx-austin-pd",
        "https://services.austintexas.gov/edims/document.cfm?id=452741",
        "instrument",
        "Council meeting backup text of the resolution authorizing continuation of the ALPR pilot program (File ID 25-0935, June 5, 2025 meeting). The document states the pilot under the 2023 Flock agreement ran March 28, 2024 to June 21, 2025 unless continued. Caveat: this copy's adoption block and resolution number are blank.",
    ),
    (
        "ma-stoughton-pd",
        "https://stoughton.org/DocumentCenter/View/6337/Amended-Motion-for-STM-Article-15---Police-Department-Capital-submitted-by-Noah-Beit-Aharon-Precinct-6-on-April-28-2026",
        "instrument",
        "Select Board's amended motion for Special Town Meeting Article 15 (February 3, 2026) requesting that Stoughton PD cancel any existing or pending contracts with Flock Safety and return Flock equipment, and striking the $60,000 Flock Safety Software capital line. The motion document does not itself record the town meeting vote.",
    ),
    (
        "oh-euclid-pd",
        "https://cdn.euclidlibrary.org/cdn/ecc/2022/20220420_SAF/agenda.pdf",
        "instrument",
        "Public Safety Committee agenda (April 20, 2022) printing Ordinance (040-22), authorizing the mayor to enter a two-year contract with Flock Safety, with an option for a two-year renewal, for LPR cameras and software, not to exceed $110,000.",
    ),
    (
        "mi-ypsilanti",
        "https://cityofypsilanti.com/Archive/ViewFile/Item/743",
        "instrument",
        "Ordinance No. 1401 (adopted September 13, 2022, effective October 13, 2022): 'The installation or use of electronic license plate scanning devices in the City of Ypsilanti is prohibited.' The ordinance bans the device class citywide; it does not name Flock Safety.",
    ),
    (
        "wi-appleton-pd",
        "https://legistar1.granicus.com/cityofappleton/attachments/48bf57af-4efe-459e-82ce-2c6caba53f49.pdf",
        "instrument",
        "Mayor's memorandum 'Flock Service Termination and Final Recommendation' (June 22, 2026): the City notified Flock Group, Inc. of its intention to end use of its products effective June 30, 2026, and the memo requests approval to issue no further payments under the terminated service. The document states Common Council approval is not required to terminate.",
    ),
    (
        "md-forest-heights-pd",
        "https://go.boarddocs.com/md/tofhmd/Board.nsf/files/DEWLR757C3C8/$file/Town Council Staff Report-GOCCP-Flock.pdf",
        "instrument",
        "Town Council staff report recommending approval of an expansion of the Flock ALPR system funded through the Governor's Office of Crime Control and Prevention ($40,000 grant): current cost $30,000 annually for 11 fixed sites, 7 additional sites at $16,500. The signed Forest Heights agreement is also on this page.",
    ),
    (
        "mn-columbia-heights-pd",
        "https://mccmeetingspublic.blob.core.usgovcloudapi.net/columbhtmn-meet-58b52135de1f43089d7974a55fb7def8/ITEM-Attachment-001-ff4c4d1fffa24182b6263fa8bd698d28.pdf",
        "instrument",
        "City Council agenda item (council letter, June 4, 2026): 'Service and Contract Cancellation with Flock Safety.' The item recounts the two contracts executed in May 2024 (7 fixed cameras and 5 flex cameras, 12-month initial terms, three-year totals $89,500 and $61,500) and carries the recommended motion to approve termination of all Flock Safety services and contracts.",
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


REGISTRY = REGISTRY + [
    ('ky-lexington-pd', 'https://lfucg.granicus.com/MinutesViewer.php?clip_id=6151&view_id=4', 'instrument', 'The minutes record Resolution 0621-24, authorizing the Mayor to execute an agreement with Flock Group Inc. for the purchase of 25 Flock cameras, warranty and implementation at a cost not to exceed $453,375 in FY 2025. The resolution was adopted on second reading July 2, 2024.'),
    ('oh-cleveland-pd', 'https://cityofcleveland.legistar1.com/cityofcleveland/attachments/17468918-7373-4770-8d8e-9ce387e0a528.pdf', 'instrument', 'The council summary authorizes the Director of Public Safety to enter into contracts with Flock Group, Inc. for acquisition or renewal of the annual license and maintenance of the Flock Safety ALPR solution for the Division of Police, for a period of six months as amended; the summary states $125,000, funded by the Division of Police operating budget, and that the Division has used the solution since 2023. The summary prints no date; the ordinance number is 683-2026.'),
    ('ia-west-des-moines-pd', 'https://wdm.iowa.gov/home/showpublisheddocument/38941/638170630876100000', 'instrument', "The April 3, 2023 council minutes record consent item 4(f), 'Approval of Additional Services Agreement - Flock Group, Inc.', approved with the consent agenda. The minutes print no camera count or dollar figure for the item."),
    ('az-scottsdale-pd', 'https://ww2.scottsdaleaz.gov/Assets/ScottsdaleAZ/Council/current-agendas-minutes/2026-agendas/10-06-26-regular-and-work-study-agenda.pdf', 'instrument', "Item 16 took up continued use of Flock technology by the Scottsdale Police Department. On a 7/0 vote the council directed staff to review the current Flock Safety contract and report on exit steps, stating: 'It is the City Council's intent not to fund the Flock Safety contract for Fiscal Year 2027-2028,' with the City Manager directed to leave the funding out of that budget and staff to identify the steps 'needed to end the contract by June 30, 2027.'"),
    ('nm-alamogordo-pd', 'https://deflockalamo.org/documents/foia-2026-06-09/Flock_Quotation_0228029725_-_CITY_OF_ALAMOGORDO_-_signed.pdf', 'signed_agreement', "Signed quotation for the City of Alamogordo's Flock purchase through Insight Public Sector under OMNIA Partners (Cobb County) contract #23-6692-03, released under New Mexico IPRA. Document date December 16, 2024; signed December 27, 2024 by the Acting City Manager and Insight's Global Compliance Officer. Term length 24 months; Year 1 $246,150 and Year 2 $215,850 plus tax, total contract commit $462,000 plus tax. Line items print coverage dates from December 27, 2024 to December 26, 2026."),
    ('ok-oklahoma-city-pd', 'https://okc.gov/files/assets/city/v/1/police/documents/flock/flock-amendment-august-2026.pdf', 'signed_agreement', 'Amendment No. 1 to the Master Services Agreement between Flock Group Inc. and the City of Oklahoma City (original agreement entered June 5, 2023, Item No. IX.CV). It adds Section 4.4, restricting disclosure of agency data to federal agencies except under compulsory legal process. The city-hosted copy bears the council approval line dated August 18, 2026; its signature blocks are blank.'),
    ('tx-college-station-pd', 'https://collegestationtx.api.civicclerk.com/v1/Meetings/GetAttachmentFile(fileId=10291)', 'instrument', "The council item attaches the Flock Safety Hardware and Software Agreement terms between the City of College Station and Flock Group, Inc. Per the city's meeting recap, the council approved the agreement on September 24, 2026 (4-2): not to exceed $158,000 for cameras on TxDOT roads and $141,062 for cameras on non-TxDOT roads. The attached terms print no date and their exhibits are blank."),
    ('dc-mpd', 'https://contracts.ocp.dc.gov/contracts/attachments/Q1cxMjMwMDXCpkJhc2UgUGVyaW9kwqZ7OEE2QzkwNzMtNjU4Ni00Njc2LUE5RTktRTUzNjMwNzk3MTM4fQ==', 'signed_agreement', 'Task order issued by the DC Office of Contracting and Procurement to Insight Public Sector for a Flock Safety LPR SaaS solution for the Metropolitan Police Department: 67 locations; implementation $135,046.54 and Falcon infrastructure $201,000, total award $336,046.54. Signed by the contractor December 30, 2024 and the District contracting officer December 31, 2024.'),
    ('wa-everett-pd', 'https://everettwa.gov/AgendaCenter/ViewFile/Item/16974?fileID=95049', 'instrument', 'Consent item recommending the council authorize the Mayor to sign the Master Services Agreement with Flock Group Inc.; contract costs not to exceed $250,000 per year, grant funded, for approximately 74 LPR cameras plus one PTZ camera in each of three parks. The attached order form (as presented, unexecuted) lists 71 Falcon, 2 Falcon Flex, 1 Falcon LR, and 3 Condor PTZ; Year 1 $253,900, annual recurring $234,000.'),
    ('ia-cedar-rapids-pd', 'https://cms8.revize.com/revize/cedarrapids/CityCouncil/2024/2024-06-25_Packet.pdf', 'instrument', "The packet's Resolution 0823-06-24 authorizes execution of a contract with Flock Group Inc. for the Police Department's ALPR system: two years, total not to exceed $499,250. The staff report states a contract has been prepared for the period July 1, 2024 to June 30, 2026, with two two-year renewal options. Adoption on June 25, 2024 is confirmed in the council minutes."),
]

REGISTRY = REGISTRY + [
    ('va-newport-news-pd', 'https://documentcloud.org/documents/28546791', 'signed_agreement', "Order form between Flock Group Inc. and the City of Newport News under the Law Enforcement Agreement, from a public-records release on DocumentCloud: 15 Falcon cameras; Year 1 $47,250, annual recurring $37,500, contract total $122,250; initial term 36 months, renewal term 24 months. The copy is unexecuted (signature blocks are blank placeholders) and prints no date. It covers 15 cameras; the record's larger deployment is documented in its other sources."),
]

REGISTRY = REGISTRY + [
    ('mi-van-buren-twp-pd', 'https://cms9files.revize.com/vanburentwp/Document_Center/Agendas%20&%20Minutes/Board%20Of%20Trustees/2021/Packets/BRD%2012-7-21%20Packet.pdf', 'instrument', 'Township board meeting packet for December 7, 2021: the Board approved the agreement with Flock Safety for the License Plate Recognition project and a $75,000 budget amendment to fund it (roll call vote, motion carried). The packet prints no camera count or contract term.'),
    ('mi-grand-rapids-pd', 'https://grandrapidsmi.gov/media/3cemd5zb/ao-2026-01-automated-license-plate-readers.pdf', 'instrument', "City Manager Administrative Order 2026-01 (September 3, 2026) governing ALPR use: it records that the City Commission approved GRPD's transition to Flock Safety through the Bid List Resolution dated January 23, 2024, that installation completed in June 2024, and that the current contract term expires June 9, 2027; the order authorizes continued use of the existing Flock units through that expiration. It prints no amounts or camera count."),
    ('il-vernon-hills-pd', 'https://vernonhills.org/AgendaCenter/ViewFile/Agenda/_06202023-1054', 'instrument', "Village Board agenda packet for June 20, 2023, containing Ordinance 2023-065 (omnibus item): authorizes payment to Flock Safety not to exceed $56,950 for seventeen additional ALPR cameras, funded by an Illinois Attorney General Organized Retail Crime Grant. The ordinance is an expansion authorization; the record's total includes cameras authorized earlier."),
    ('ny-niagara-falls-pd', 'https://cms3.revize.com/revize/niagarafallsny/Documents/Government/City Council/2025/0312/1 - Corrected DRAFT Support Packet for Regular Council Meeting on 3.12.25. (18 pgs).pdf', 'instrument', "Council support packet for March 12, 2025 embedding the draft minutes of February 26, 2025: Item 5 approved the award of contracts for a license plate reader project for the Niagara Falls Police Department and authorized the Mayor to execute the necessary documents, per the Mayor's recommendation memo dated February 19, 2025 (roll call 5-0, adopted). The minutes print no vendor name, camera count, or amounts, and are marked draft."),
    ('ky-elizabethtown-pd', 'https://portal.ksba.org/public/Meeting/Attachments/DisplayAttachment.aspx?AttachmentID=784808', 'signed_agreement', 'Executed Flock Group, Inc. Master Services Agreement and order form (DocuSign Envelope ID AC67427B-D6B8-4536-AC7B-C32EE200C444, dated December 8, 2023): 40 Falcon cameras; Flock Safety Platform $100,000 per year recurring; Year 1 subtotal $114,400; contract total $514,400; initial term 60 months, renewal term 24 months. The term commences on first installation and validation, so no start or end date is printed. Signed for Flock by Mark Smith, General Counsel, and for the customer by Jeremy Thompson, Chief of Police, both dated 12/8/2023.'),
    ('oh-lorain-pd', 'https://public.destinyhosted.com/loraidocs/2023/BOC/20230215_916/AGENDApacket__02-15-23_0308_915.pdf', 'signed_agreement', "Lorain Board of Control agenda packet, February 15, 2023, embedding the Flock Group Inc. order form and Government Agency Agreement: the item requests permission to enter a service agreement with Flock Group Inc. in the amount of $531,500, states Ordinance 24-23 passed City Council, and payment is from ARPA funds. Order form: 40 Falcon cameras at $2,500, total contract amount $531,500, annual recurring total $103,500, initial term 60 months, first four years paid upfront. Flock's signature (Mark Smith, General Counsel, February 1, 2023) appears in the packet copy; the agency signature block is blank in this copy."),
    ('ny-troy-pd', 'https://troyny.gov/AgendaCenter/ViewFile/ArchivedAgenda/_03192026-1474?packet=true', 'signed_agreement', "Flock Group Inc. order form and Government Agency Customer Agreement for the Troy City Police Department, carried in the City Council Finance Meeting packet of March 19, 2026 and executed by both parties on July 22, 2021 (PandaDoc certificate in the document): 11 Falcon cameras, Year 1 total $30,250, initial term 24 months, renewal term 24 months. Special terms state: Contract Starts on Mon 8/16 2021 after 60 Day Pilot finishes. The record's contract_start does not appear in the document; flagged for review, not changed."),
    ('ca-berkeley-pd', 'https://berkeleyca.gov/sites/default/files/city-council-meetings/2026-05-07%20Annotated%20Agenda%20-%20Council.pdf', 'instrument', "Annotated agenda of the Berkeley City Council special meeting, May 7, 2026: on the Flock Safety item (continued from March 24, 2026; 156 speakers), the council voted not to move forward with the full Master Services Agreement execution as proposed, and adopted Resolution No. 72,254-N.S. authorizing extension of the current ALPR contract for 12 months for an additional contract amount up to $200,000 (motion Blackaby/Humbert, carried 5-4). No camera count is printed. The record's pending status predates this action; flagged for review, not changed."),
    ('in-south-bend-pd', 'https://docs.southbendin.gov/weblink/0/edoc/386260/Encroachment%20%20Revocable%20Permit%20-%20Flock%20Safety.pdf', 'instrument', "City of South Bend Board of Public Works letter dated October 10, 2024 (Theresa Heffner, Clerk), recording that at its October 10, 2024 meeting the Board approved Flock Safety's installation of two ALPR cameras in the public right-of-way on behalf of the South Bend Police Department at W. LaSalle Ave. & N. Lafayette Blvd. and Bonfield Pl. & S. Sheridan St.; the signed revocable encroachment permit (dated October 8, 2024) is enclosed in the same document."),
    ('ms-ridgeland-pd', 'https://ridgelandms.api.civicclerk.com/v1/Meetings/GetMeetingFileStream(fileId=4124,plainText=false)', 'instrument', 'Minutes of the Ridgeland Mayor and Board of Aldermen, October 19, 2021: the consent agenda, moved by Alderman D.I. Smith and seconded by Alderman Wesley Hamlin, carried 7-0, including item 2(i) approving the Flock Safety Additional Services Agreement for the Ridgeland Police Department (order attached as Exhibit J). Minutes signed by Mayor Gene F. McGee on October 26, 2021, attested by City Clerk Paula Tierce. The agreement itself (Exhibit J to the meeting packet) is not reproduced in the minutes.'),
]

REGISTRY = REGISTRY + [
    ('oh-strongsville-pd', 'https://strongsville.org/CityOfStrongsville/media/StrongsvilleMedia/Documents/City%20Council/2024-008.pdf?ext=.pdf', 'instrument', 'Ordinance 2024-008 (adopted 2024-01-16, 7-0) authorizes a Master Services Agreement with Flock Group, Inc.; attached order form: 15 Falcon, 1 Falcon Flex, 3 Falcon LR; Year 1 $72,250; annual recurring $63,500; total $135,750; terms 24/24 months; mayor signed 2024-01-16; Flock signature block blank in packet copy; order form prints no start or end dates.'),
    ('oh-strongsville-pd', 'https://strongsville.org/CityOfStrongsville/media/StrongsvilleMedia/Documents/City%20Council/2025-127.pdf?ext=.pdf', 'instrument', 'Ordinance 2025-127 (adopted 2025-11-03, 7-0) authorizes six additional Flock LPR cameras; Year 1 $18,900; annual recurring $18,000; total $54,900; terms 36/36 months; mayor signed 2025-11-03; Flock signature block blank in packet copy; order form prints no start or end dates.'),
    ('la-central-pd', 'https://digital-release.louisianafirstnews.com/wp-content/uploads/sites/80/2022/04/Central-City-Council-Camera-Resolution.pdf', 'instrument', 'Council resolution authorizing Mayor Barrow to execute a multiyear agreement with Flock Group, Inc. for security cameras and license plate readers at city entrances; adopted 2022-04-12 per the certification paragraph; resolution number and vote tally blank in this copy; no figures or term dates printed.'),
    ('ct-putnam-pd', 'https://resources.finalsite.net/images/v1761753101/putnamctus/uv0v8sucfql7nza6eqp5/MayorandBoardofSelectmensMinutesOctober202025.pdf', 'instrument', "October 20, 2025 board minutes record unanimous votes to add license plate readers to the agenda and to place bags over the readers on Town property pending discussion with the SSD Board; Selectman Hayes disputed the mayor's authority to approve use of Town land. The minutes do not name the Flock brand."),
    ('il-champaign-pd', 'https://stopflock.org/foias/champaign_police_department/1/2022-03-15_contract.pdf', 'signed_agreement', "Executed contract between the City of Champaign and Flock Group, Inc. (public-records copy): 46 Flock Falcon cameras plus Raven gunshot-detection coverage of 1.3 square miles; contract amount $240,500 (Year 1 $125,500, Year 2 $115,000); printed term: 24 months starting February 28, 2022. Signed by the Acting City Manager on March 15, 2022. The record's current deployment rests on a later renewal that is not yet in the registry."),
    ('wi-green-bay-pd', 'https://deflockdane.org/reading-room/green-bay-pd-flock-dfr-law-enforcement-agreement-2025/file?download=1', 'signed_agreement', "Executed Flock Safety Law Enforcement Agreement and order form for Green Bay PD's drone-as-first-responder program (DocuSign, signed December 22-23, 2025): 42 Flock Safety LPR cameras, 2 DFR dock systems, radar and Flock911; Year 1 $270,000, years 4-5 $291,000 per year, contract total $1,392,000; initial term 60 months, renewal term 36 months. The term commences on first installation and validation, so no start or end date is printed. Copy hosted by a public-records reading room."),
]
