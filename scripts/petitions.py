#!/usr/bin/env python3
"""Petitions page registry for Flock-Off.

The Petitions tab lists citizen petitions created to counter Flock
Safety deployments: petitions asking a city or agency to remove, ban,
defund, or decline to renew Flock cameras. A petition appears here only
because a reviewer opened the petition page and recorded what it said.

Petitions are citizen speech, not evidence about a contract. Signature
counts are snapshots: the count a reviewer read on the petition page on
the `signatures_as_of` date. Counts change; the page shows the as-of
date so a stale count never poses as a live one.

Each entry:
    (slug, title, url, platform, place, agency_id, target_text,
     organizer, started, status, signatures, signatures_as_of, note)

- slug: unique short id for the entry.
- title: the petition title exactly as printed on the petition page.
- url: the petition page itself.
- platform: the platform hosting the petition (e.g. "Change.org").
- place: the place the petition concerns, as it will be shown on the
  card (e.g. "Paducah, KY", "Statewide: Oregon", "National").
- agency_id: the tracker record the petition targets, or None when the
  petition targets a body with no tracker record; when set it must
  resolve against the dataset (fail-closed).
- target_text: who the petition is addressed to, as the page states it.
- organizer: the organizer name as publicly shown, or None.
- started: the start date the page shows (ISO), or None.
- status: one of STATUSES, as the page showed it at review time.
- signatures: the signature count the reviewer read, or None.
- signatures_as_of: the date the count was read (ISO), or None.
- note: one line: what the petition asks for, in the page's own terms.

Fail-closed: build_petition_entries() raises on a duplicate slug, a
non-https URL, an unknown status, or an agency_id missing from the
dataset, so a broken entry aborts the build instead of shipping a
petition card that misstates its target.

Stdlib only.
"""
from __future__ import annotations

STATUSES = {"open", "closed", "delivered", "victory"}
STATUS_LABELS = {
    "open": "Collecting signatures",
    "closed": "Closed",
    "delivered": "Delivered",
    "victory": "Declared victory",
}

# (slug, title, url, platform, place, agency_id, target_text,
#  organizer, started, status, signatures, signatures_as_of, note)
REGISTRY = [
    ('paducah-ky-review-vote', 'Demand a Public Review and Vote on Flock Cameras in Paducah', 'https://www.change.org/p/demand-a-public-review-and-vote-on-flock-cameras-in-paducah', 'Change.org', 'Paducah, KY', None, 'Paducah Board of Commissioners and City of Paducah', 'Zac Underwood', '2026-09-20', 'open', 2, '2026-10-18', 'Asks Paducah for a public review of its Flock program and a public vote on whether it continues, with removal or non-renewal as an available outcome.'),
    ('hewitt-tx-remove', 'Hewitt TX Residents: Remove Flock Safety and all ALPR Cameras', 'https://www.change.org/p/hewitt-tx-residents-remove-flock-safety-and-all-alpr-cameras', 'Change.org', 'Hewitt, TX', None, 'Hewitt City Council', 'RJ Pase', '2026-08-26', 'open', 357, '2026-10-18', 'Asks Hewitt to terminate its Flock Safety program, remove the cameras (about 20, per the petition), and prohibit future ALPR use.'),
    ('bellevue-ky-get-out', 'Get the Flock Out of Bellevue, KY', 'https://www.change.org/p/get-the-flock-out-of-bellevue-ky', 'Change.org', 'Bellevue, KY', None, 'City of Bellevue', 'Heather Bailey', '2026-09-16', 'open', 183, '2026-10-18', "Demands immediate cancellation of Bellevue's Flock contract and permanent removal of the cameras; rejects a pause or suspension."),
    ('ottawa-county-mi-deflock', 'De-Flock Ottawa County', 'https://www.change.org/p/de-flock-ottawa-county', 'Change.org', 'Ottawa County, MI', 'mi-ottawa-county-so', "Ottawa County Board of Commissioners and Ottawa County Sheriff's Office", 'Tyler Duggins', '2026-09-20', 'open', 1, '2026-10-18', 'Asks Ottawa County to remove all Flock cameras, not renew or extend the agreement, and permanently delete stored Flock data.'),
    ('ottawa-county-mi-get-out', 'Get the FLOCK Out of Ottawa County', 'https://www.change.org/p/get-the-flock-out-of-ottawa-county', 'Change.org', 'Ottawa County, MI', 'mi-ottawa-county-so', 'Holland Township and Ottawa County leaders', 'Tasha Corrigan', '2026-06-24', 'open', 370, '2026-10-18', 'A separate Ottawa County campaign from the De-Flock petition above: asks Holland Township leaders for a public conversation before expansion and to reconsider the AI surveillance cameras.'),
    ('oregon-statewide-ban', 'Ban Flock and Other AI License Plate Cameras in Oregon', 'https://www.change.org/p/ban-flock-and-other-ai-license-plate-cameras-in-oregon', 'Change.org', 'Statewide: Oregon', None, 'Oregon State Legislature', 'Community Petition', '2026-10-08', 'open', 219, '2026-10-18', 'Asks the Oregon Legislature to pass the statewide ALPR ban bill the petition says Reps. Chotzen and Skarlatos plan to introduce.'),
    ('shasta-county-ca', 'Flock Off Shasta County - Ban Flock Safety cameras in Shasta County, CA', 'https://www.change.org/p/flock-off-shasta-county-ban-flock-safety-cameras-in-shasta-county-ca', 'Change.org', 'Shasta County, CA', None, 'Anderson City Council and Shasta County leaders', 'Christina Smith', '2026-08-19', 'open', 338, '2026-10-18', 'Asks Anderson and Shasta County to terminate Flock contracts, remove the cameras, and delete stored data; signatures are to be delivered at a council meeting.'),
    ('bakersfield-ca-remove', "Remove Bakersfield's Flock Cameras and Reject Any Expansion", 'https://www.change.org/p/remove-bakersfield-s-flock-cameras-and-reject-any-expansion', 'Change.org', 'Bakersfield, CA', None, 'Bakersfield City Council', 'Lucas Choate', '2026-10-16', 'open', 38, '2026-10-18', 'Asks the Bakersfield City Council to remove the existing Flock cameras and reject any extension of the system.'),
    ('garden-city-mi-remove', 'Remove Flock cameras in Garden City, Michigan', 'https://www.change.org/p/remove-flock-cameras-in-garden-city-michigan', 'Change.org', 'Garden City, MI', None, 'Garden City City Council', 'Rich Stoddard', '2026-09-28', 'open', 379, '2026-10-18', 'Asks Garden City not to renew any Flock contract and to remove the existing cameras, citing Westland and Eastpointe cancellations.'),
    ('denver-co-remove', 'Remove flock cameras from Denver', 'https://www.change.org/p/remove-flock-cameras-from-denver', 'Change.org', 'Denver, CO', 'co-denver-pd', 'City of Denver', 'Sabrina Popken', '2026-10-03', 'open', 6, '2026-10-18', 'Urges Denver to halt Flock camera use and convene a public forum on their future. The tracker record for Denver PD is already marked cancelled.'),
    ('avondale-estates-ga-cancel', 'Cancel the Flock Contract in Avondale Estates, GA', 'https://www.change.org/p/cancel-the-flock-contract-in-avondale-estates-ga', 'Change.org', 'Avondale Estates, GA', None, 'City of Avondale Estates', 'Gregory Hendler', '2026-08-31', 'open', 985, '2026-10-18', "Demands immediate cancellation of Avondale Estates' Flock contract (10 cameras, per the petition) and a commitment against future Flock or competitor surveillance contracts."),
    ('davie-county-nc-ban', 'REMOVE AND BAN ALL ALPR CAMERAS IN DAVIE COUNTY, NC', 'https://www.change.org/p/remove-and-ban-all-alpr-cameras-in-davie-county-nc', 'Change.org', 'Davie County, NC', None, 'Davie County Sheriff and Davie County Board of Commissioners', 'Jeff Plott', '2026-10-13', 'open', 547, '2026-10-18', 'Demands removal of all ALPR cameras, termination of Flock and other ALPR contracts, and a countywide ban.'),
    ('houston-tx-cancel', 'Cancel Houston’s Flock Safety Contract!', 'https://www.change.org/p/cancel-houston-s-flock-safety-contract', 'Change.org', 'Houston, TX', None, 'Houston City Council, Houston Police Department, and the City of Houston', 'Austin Pendergraft', '2026-08-18', 'open', 346, '2026-10-18', 'Calls on Houston to reject ALPR networks including Flock, and to require public disclosure, an independent privacy audit, and community approval before deployment or renewal.'),
    ('wisconsin-statewide-ban', 'Ban Flock Surveillance Cameras in Wisconsin', 'https://www.change.org/p/ban-flock-surveillance-cameras-in-wisconsin', 'Change.org', 'Statewide: Wisconsin', None, 'Wisconsin lawmakers', 'Community Petition', '2026-07-27', 'open', 2705, '2026-10-18', 'Asks Wisconsin lawmakers to ban Flock cameras and other warrantless automated surveillance. The largest petition on this page by signatures read.'),
    ('western-nc-ban', 'Ban Flock cameras in Western North Carolina', 'https://www.change.org/p/ban-flock-cameras-in-western-north-carolina', 'Change.org', 'Western North Carolina', None, 'Western North Carolina local governments', 'Lila Herman', '2026-10-01', 'open', 12, '2026-10-18', 'Demands removal of Flock cameras from schools and public spaces across Western North Carolina.'),
    ('utah-moveon-deflock', 'DeFlock Utah!', 'https://sign.moveon.org/petitions/deflock-utah', 'MoveOn', 'Statewide: Utah', None, 'Utah Legislature, the Governor, county governments, and municipal leaders', None, None, 'open', 10, '2026-10-18', 'Calls on Utah leaders to prohibit installation and use of Flock ALPR systems statewide, with judicial oversight and retention limits.'),
    ('congress-moveon-defund', "Tell Congress to defund Flock's totalitarian camera network!", 'https://sign.moveon.org/petitions/tell-congress-to-defund-flock-s-totalitarian-camera-network', 'MoveOn', 'National', None, 'U.S. Congress', None, None, 'open', 44, '2026-10-18', 'Urges Congress to pass legislation withholding federal funding from police departments and municipalities that use Flock or other ALPR cameras.'),
    ('moveon-transparency', 'Stop the Flock: Demand Transparency for License Plate Surveillance Cameras', 'https://sign.moveon.org/petitions/stop-the-flock-demand-transparency-for-license-plate-surveillance-cameras', 'MoveOn', 'National', None, 'City councils and U.S. Congress', None, None, 'open', 33, '2026-10-18', 'Asks for public disclosure of ALPR contract terms and false-positive rates, independent audits, and a warrant requirement for government purchase of location data. Explicitly does not ask for a ban.'),
    ('santa-barbara-ca-deflock805', 'Take action and protect our community from mass surveillance!', 'https://actionnetwork.org/petitions/deflock805', 'Action Network', 'Santa Barbara, CA', None, 'Santa Barbara City Council', None, None, 'open', 164, '2026-10-18', 'The DeFlock 805 petition: asks Santa Barbara not to renew Flock, not to contract another ALPR vendor, and to require audits and data protections.'),
    ('quincy-ma-flock-out', 'Flock Out of Quincy', 'https://actionnetwork.org/petitions/flock-out-of-quincy', 'Action Network', 'Quincy, MA', None, 'Quincy City Council', None, None, 'open', 135, '2026-10-18', "Asks Quincy, Massachusetts to dissolve its Flock contract (60+ cameras, per the page) and adopt a CCOPS-style oversight ordinance. The page's printed petition title is “Sign the Petition!”. Not Quincy, Illinois, which the tracker also covers."),
    ('rutherford-county-nc', 'Protect Our Privacy: Remove Flock Surveillance Cameras from Rutherford County', 'https://www.openpetition.org/us/petition/online/protect-our-privacy-remove-flock-surveillance-cameras-from-rutherford-county', 'openPetition', 'Rutherford County, NC', 'nc-rutherford-county', 'Rutherford County Commissioners and local authorities', None, '2026-08-11', 'open', None, None, 'Calls on Rutherford County to remove existing Flock cameras and halt expansion or funding. The platform does not display a signature count or a public organizer name.'),
    ('utah-getflocked', '#GetFlocked - Ban Mass License-Plate Surveillance in Utah', 'https://onemobclothingco.com/pages/get-flocked', 'One Mob Clothing Co.', 'Statewide: Utah', None, 'Governor of Utah, Utah State Legislature, Utah Privacy Governing Board, UDOT, and Utah city and county governments', 'One Mob Clothing Co.', None, 'open', None, None, "A civic initiative petition asking Utah to ban mass ALPR surveillance, revoke UDOT camera permits, and decline contract renewals. The page does not display a signature count; signatures are delivered to the signer's own state legislators."),
    ('congress-other98-defund', 'Congress: Defund Flock Surveillance', 'https://petitions.other98.com/defund-flock', 'The Other 98%', 'National', None, 'U.S. Congress', 'The Other 98%', None, 'open', None, None, 'Asks Congress to strip federal funding from departments running mass license plate surveillance. Goal shown on the page: 25,000 signatures; the current count is not displayed.'),
]


def build_petition_entries(agencies: list) -> list:
    """Validate REGISTRY and join agency context. Raises ValueError."""
    by_id = {a["id"]: a for a in agencies}
    seen = set()
    entries = []
    for row in REGISTRY:
        (slug, title, url, platform, place, agency_id, target_text,
         organizer, started, status, signatures, signatures_as_of,
         note) = row
        if slug in seen:
            raise ValueError(f"petitions: duplicate slug {slug!r}")
        seen.add(slug)
        if not url.startswith("https://"):
            raise ValueError(f"petitions: {slug}: url must be https: {url!r}")
        if status not in STATUSES:
            raise ValueError(f"petitions: {slug}: unknown status {status!r}")
        if not title or not platform or not place or not target_text or not note:
            raise ValueError(f"petitions: {slug}: missing required text field")
        agency = None
        if agency_id is not None:
            agency = by_id.get(agency_id)
            if agency is None:
                raise ValueError(
                    f"petitions: {slug}: agency_id {agency_id!r} not in dataset")
        entries.append({
            "slug": slug,
            "title": title,
            "url": url,
            "platform": platform,
            "place": place,
            "agency_id": agency_id,
            "agency": agency["agency"] if agency else None,
            "city": agency.get("city") if agency else None,
            "state": agency.get("state") if agency else None,
            "target_text": target_text,
            "organizer": organizer,
            "started": started,
            "status": status,
            "status_label": STATUS_LABELS[status],
            "signatures": signatures,
            "signatures_as_of": signatures_as_of,
            "note": note,
        })
    entries.sort(key=lambda e: (e["signatures"] is None,
                                -(e["signatures"] or 0), e["slug"]))
    return entries
