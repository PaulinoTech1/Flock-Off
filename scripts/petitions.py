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
    ('paducah-ky-review-vote', 'Demand a Public Review and Vote on Flock Cameras in Paducah', 'https://www.change.org/p/demand-a-public-review-and-vote-on-flock-cameras-in-paducah', 'Change.org', 'Paducah, KY', None, 'Paducah Board of Commissioners and City of Paducah', 'Zac Underwood', '2026-09-20', 'open', 2, '2026-10-19', 'Asks Paducah for a public review of its Flock program and a public vote on whether it continues, with removal or non-renewal as an available outcome.'),
    ('hewitt-tx-remove', 'Hewitt TX Residents: Remove Flock Safety and all ALPR Cameras', 'https://www.change.org/p/hewitt-tx-residents-remove-flock-safety-and-all-alpr-cameras', 'Change.org', 'Hewitt, TX', None, 'Hewitt City Council', 'RJ Pase', '2026-08-26', 'victory', 357, '2026-10-19', 'Asks Hewitt to terminate its Flock Safety program, remove the cameras (about 20, per the petition), and prohibit future ALPR use. The petition page declared victory on 2026-10-01, quoting city officials that the cameras are deactivated and set to be removed.'),
    ('bellevue-ky-get-out', 'Get the Flock Out of Bellevue, KY', 'https://www.change.org/p/get-the-flock-out-of-bellevue-ky', 'Change.org', 'Bellevue, KY', None, 'City of Bellevue', 'Heather Bailey', '2026-09-16', 'open', 185, '2026-10-19', "Demands immediate cancellation of Bellevue's Flock contract and permanent removal of the cameras; rejects a pause or suspension."),
    ('ottawa-county-mi-deflock', 'De-Flock Ottawa County', 'https://www.change.org/p/de-flock-ottawa-county', 'Change.org', 'Ottawa County, MI', 'mi-ottawa-county-so', "Ottawa County Board of Commissioners and Ottawa County Sheriff's Office", 'Tyler Duggins', '2026-09-20', 'open', 1, '2026-10-19', 'Asks Ottawa County to remove all Flock cameras, not renew or extend the agreement, and permanently delete stored Flock data.'),
    ('ottawa-county-mi-get-out', 'Get the FLOCK Out of Ottawa County', 'https://www.change.org/p/get-the-flock-out-of-ottawa-county', 'Change.org', 'Ottawa County, MI', 'mi-ottawa-county-so', 'Holland Township and Ottawa County leaders', 'Tasha Corrigan', '2026-06-24', 'open', 371, '2026-10-19', 'A separate Ottawa County campaign from the De-Flock petition above: asks Holland Township leaders for a public conversation before expansion and to reconsider the AI surveillance cameras.'),
    ('oregon-statewide-ban', 'Ban Flock and Other AI License Plate Cameras in Oregon', 'https://www.change.org/p/ban-flock-and-other-ai-license-plate-cameras-in-oregon', 'Change.org', 'Statewide: Oregon', None, 'Oregon State Legislature', 'Community Petition', '2026-10-08', 'open', 220, '2026-10-19', 'Asks the Oregon Legislature to pass the statewide ALPR ban bill the petition says Reps. Chotzen and Skarlatos plan to introduce.'),
    ('shasta-county-ca', 'Flock Off Shasta County - Ban Flock Safety cameras in Shasta County, CA', 'https://www.change.org/p/flock-off-shasta-county-ban-flock-safety-cameras-in-shasta-county-ca', 'Change.org', 'Shasta County, CA', None, 'Anderson City Council and Shasta County leaders', 'Christina Smith', '2026-08-19', 'open', 342, '2026-10-19', 'Asks Anderson and Shasta County to terminate Flock contracts, remove the cameras, and delete stored data; signatures are to be delivered at a council meeting.'),
    ('bakersfield-ca-remove', "Remove Bakersfield's Flock Cameras and Reject Any Expansion", 'https://www.change.org/p/remove-bakersfield-s-flock-cameras-and-reject-any-expansion', 'Change.org', 'Bakersfield, CA', None, 'Bakersfield City Council', 'Lucas Choate', '2026-10-16', 'open', 42, '2026-10-19', 'Asks the Bakersfield City Council to remove the existing Flock cameras and reject any extension of the system.'),
    ('garden-city-mi-remove', 'Remove Flock cameras in Garden City, Michigan', 'https://www.change.org/p/remove-flock-cameras-in-garden-city-michigan', 'Change.org', 'Garden City, MI', None, 'Garden City City Council', 'Rich Stoddard', '2026-09-28', 'open', 387, '2026-10-19', 'Asks Garden City not to renew any Flock contract and to remove the existing cameras, citing Westland and Eastpointe cancellations.'),
    ('denver-co-remove', 'Remove flock cameras from Denver', 'https://www.change.org/p/remove-flock-cameras-from-denver', 'Change.org', 'Denver, CO', 'co-denver-pd', 'City of Denver', 'Sabrina Popken', '2026-10-03', 'open', 6, '2026-10-19', 'Urges Denver to halt Flock camera use and convene a public forum on their future. The tracker record for Denver PD is already marked cancelled.'),
    ('avondale-estates-ga-cancel', 'Cancel the Flock Contract in Avondale Estates, GA', 'https://www.change.org/p/cancel-the-flock-contract-in-avondale-estates-ga', 'Change.org', 'Avondale Estates, GA', None, 'City of Avondale Estates', 'Gregory Hendler', '2026-08-31', 'open', 986, '2026-10-19', "Demands immediate cancellation of Avondale Estates' Flock contract (10 cameras, per the petition) and a commitment against future Flock or competitor surveillance contracts."),
    ('davie-county-nc-ban', 'REMOVE AND BAN ALL ALPR CAMERAS IN DAVIE COUNTY, NC', 'https://www.change.org/p/remove-and-ban-all-alpr-cameras-in-davie-county-nc', 'Change.org', 'Davie County, NC', None, 'Davie County Sheriff and Davie County Board of Commissioners', 'Jeff Plott', '2026-10-13', 'open', 583, '2026-10-19', 'Demands removal of all ALPR cameras, termination of Flock and other ALPR contracts, and a countywide ban.'),
    ('houston-tx-cancel', 'Cancel Houston’s Flock Safety Contract!', 'https://www.change.org/p/cancel-houston-s-flock-safety-contract', 'Change.org', 'Houston, TX', None, 'Houston City Council, Houston Police Department, and the City of Houston', 'Austin Pendergraft', '2026-08-18', 'open', 348, '2026-10-19', 'Calls on Houston to reject ALPR networks including Flock, and to require public disclosure, an independent privacy audit, and community approval before deployment or renewal.'),
    ('wisconsin-statewide-ban', 'Ban Flock Surveillance Cameras in Wisconsin', 'https://www.change.org/p/ban-flock-surveillance-cameras-in-wisconsin', 'Change.org', 'Statewide: Wisconsin', None, 'Wisconsin lawmakers', 'Community Petition', '2026-07-27', 'open', 2706, '2026-10-19', 'Asks Wisconsin lawmakers to ban Flock cameras and other warrantless automated surveillance. The largest petition on this page by signatures read.'),
    ('western-nc-ban', 'Ban Flock cameras in Western North Carolina', 'https://www.change.org/p/ban-flock-cameras-in-western-north-carolina', 'Change.org', 'Western North Carolina', None, 'Western North Carolina local governments', 'Lila Herman', '2026-10-01', 'open', 13, '2026-10-19', 'Demands removal of Flock cameras from schools and public spaces across Western North Carolina.'),
    ('utah-moveon-deflock', 'DeFlock Utah!', 'https://sign.moveon.org/petitions/deflock-utah', 'MoveOn', 'Statewide: Utah', None, 'Utah Legislature, the Governor, county governments, and municipal leaders', None, None, 'open', 10, '2026-10-18', 'Calls on Utah leaders to prohibit installation and use of Flock ALPR systems statewide, with judicial oversight and retention limits.'),
    ('congress-moveon-defund', "Tell Congress to defund Flock's totalitarian camera network!", 'https://sign.moveon.org/petitions/tell-congress-to-defund-flock-s-totalitarian-camera-network', 'MoveOn', 'National', None, 'U.S. Congress', None, None, 'open', 44, '2026-10-18', 'Urges Congress to pass legislation withholding federal funding from police departments and municipalities that use Flock or other ALPR cameras.'),
    ('moveon-transparency', 'Stop the Flock: Demand Transparency for License Plate Surveillance Cameras', 'https://sign.moveon.org/petitions/stop-the-flock-demand-transparency-for-license-plate-surveillance-cameras', 'MoveOn', 'National', None, 'City councils and U.S. Congress', None, None, 'open', 33, '2026-10-18', 'Asks for public disclosure of ALPR contract terms and false-positive rates, independent audits, and a warrant requirement for government purchase of location data. Explicitly does not ask for a ban.'),
    ('santa-barbara-ca-deflock805', 'Take action and protect our community from mass surveillance!', 'https://actionnetwork.org/petitions/deflock805', 'Action Network', 'Santa Barbara, CA', None, 'Santa Barbara City Council', None, None, 'open', 164, '2026-10-19', 'The DeFlock 805 petition: asks Santa Barbara not to renew Flock, not to contract another ALPR vendor, and to require audits and data protections.'),
    ('quincy-ma-flock-out', 'Flock Out of Quincy', 'https://actionnetwork.org/petitions/flock-out-of-quincy', 'Action Network', 'Quincy, MA', None, 'Quincy City Council', None, None, 'open', 137, '2026-10-19', "Asks Quincy, Massachusetts to dissolve its Flock contract (60+ cameras, per the page) and adopt a CCOPS-style oversight ordinance. The page's printed petition title is “Sign the Petition!”. Not Quincy, Illinois, which the tracker also covers."),
    ('rutherford-county-nc', 'Protect Our Privacy: Remove Flock Surveillance Cameras from Rutherford County', 'https://www.openpetition.org/us/petition/online/protect-our-privacy-remove-flock-surveillance-cameras-from-rutherford-county', 'openPetition', 'Rutherford County, NC', 'nc-rutherford-county', 'Rutherford County Commissioners and local authorities', None, '2026-08-11', 'open', 399, '2026-10-19', 'Calls on Rutherford County to remove existing Flock cameras and halt expansion or funding. The platform does not display a public organizer name.'),
    ('utah-getflocked', '#GetFlocked - Ban Mass License-Plate Surveillance in Utah', 'https://onemobclothingco.com/pages/get-flocked', 'One Mob Clothing Co.', 'Statewide: Utah', None, 'Governor of Utah, Utah State Legislature, Utah Privacy Governing Board, UDOT, and Utah city and county governments', 'One Mob Clothing Co.', None, 'open', None, None, "A civic initiative petition asking Utah to ban mass ALPR surveillance, revoke UDOT camera permits, and decline contract renewals. The page does not display a signature count; signatures are delivered to the signer's own state legislators."),
    ('congress-other98-defund', 'Congress: Defund Flock Surveillance', 'https://petitions.other98.com/defund-flock', 'The Other 98%', 'National', None, 'U.S. Congress', 'The Other 98%', None, 'open', None, None, 'Asks Congress to strip federal funding from departments running mass license plate surveillance. Goal shown on the page: 25,000 signatures; the current count is not displayed.'),
    ('livonia-mi-terminate-flock-contract', 'Terminate the contract with Flock to protect privacy rights', 'https://www.change.org/p/terminate-the-contract-with-flock-to-protect-privacy-rights', 'Change.org', 'Livonia, MI', None, 'Livonia City Council', 'Richie Par', '2026-10-06', 'open', 114, '2026-10-19', 'Asks Livonia to terminate its contract with Flock to protect privacy rights, citing the installation of Flock Safety cameras across the city.'),
    ('franklin-county-ky-ban-flock', 'Ban Flock & All ALPRs in Franklin County, KY', 'https://www.change.org/p/ban-flock-all-alprs-in-franklin-county-ky', 'Change.org', 'Franklin County, KY', None, 'Franklin County Sheriff and Franklin County governing bodies', 'Madeleine Hay', '2026-10-02', 'open', 212, '2026-10-19', 'Implores Sheriff Dwayne Depp to terminate his Flock Safety contract and all Franklin County governing bodies to ban ALPRs and AI mass surveillance.'),
    ('loveland-co-deflock', 'DeflockLoveland, Removing Flock Cameras in Loveland Colorado', 'https://www.change.org/p/deflockloveland-removing-flock-cameras-in-loveland-colorado', 'Change.org', 'Loveland, CO', None, 'Loveland City Council', 'Gabe Sayer', '2026-07-10', 'open', 1342, '2026-10-19', 'Asks Loveland to remove its Flock cameras; the petition cites at least 65 cameras installed in the city.'),
    ('dare-county-nc-remove', 'Petition to Remove Flock Cameras from Dare County, NC', 'https://www.change.org/p/petition-to-remove-flock-cameras-from-dare-county-nc', 'Change.org', 'Dare County, NC', 'nc-dare-county-sheriff', 'Dare County and its participating municipalities', "Andrea O'Donnell", '2026-07-11', 'open', 828, '2026-10-19', 'Asks Dare County and its municipalities to remove Flock Safety cameras and decline renewal of any current Flock contracts. The tracker record for the Dare County Sheriff is marked cancelled; the petition describes cameras operating in the county.'),
    ('sylacauga-al-deflock', 'DeFlock Sylacauga', 'https://www.change.org/p/deflock-sylacauga', 'Change.org', 'Sylacauga, AL', None, 'Sylacauga City Council', 'Cory Holcomb', '2026-09-06', 'open', 237, '2026-10-19', 'Asks Sylacauga to end the use of Flock Safety cameras in the city.'),
    ('henderson-county-nc-defund', 'Stop Funding mass surveillance: Defund Flock Cameras in Henderson County, NC', 'https://www.change.org/p/stop-funding-mass-surveillance-defund-flock-cameras-in-henderson-county-nc', 'Change.org', 'Henderson County, NC', 'nc-henderson-county-sheriff', 'Henderson County Board of Commissioners and Henderson County Manager', 'Austin Rhodes', '2026-08-06', 'open', 2886, '2026-10-19', 'Asks the Henderson County commissioners and county manager to stop funding Flock cameras; addressed to the funders of the sheriff deployment the tracker records.'),
    ('florida-statewide-deflock', 'De-Flock Florida: Expand the Highway Ban Statewide', 'https://www.change.org/p/de-flock-florida-expand-the-highway-ban-statewide', 'Change.org', 'Statewide: Florida', None, 'Florida State Legislature', 'Garrett culpepper', '2026-09-01', 'open', 41, '2026-10-19', 'Petitions the Florida Legislature to expand the state highway Flock ban statewide.'),
    ('indiana-statewide-deflock', 'DeFlock Indiana', 'https://www.change.org/p/deflock-indiana', 'Change.org', 'Statewide: Indiana', None, 'Governor of Indiana, Indiana General Assembly, and Indiana local governments', 'Kyle Alexander', '2026-08-14', 'open', 2, '2026-10-19', 'Petitions for the removal and permanent prohibition of all ALPR cameras throughout Indiana, naming Flock Safety, Axon, and Vigilant systems.'),
    ('north-carolina-statewide-end-flock-alpr', 'End Flock & ALPR Mass Surveillance in North Carolina', 'https://www.change.org/p/end-flock-alpr-mass-surveillance-in-north-carolina', 'Change.org', 'Statewide: North Carolina', None, 'North Carolina General Assembly and Governor of North Carolina', 'Mark Williams', '2026-09-12', 'open', 818, '2026-10-19', 'Asks North Carolina to end Flock and ALPR mass surveillance statewide.'),
    ('cambridge-oh-remove-flock', 'Request for Removal and Termination of Flock Safety Automated License Plate Readers', 'https://www.change.org/p/request-for-removal-and-termination-of-flock-safety-automated-license-plate-readers', 'Change.org', 'Cambridge, OH', None, 'Cambridge City Council', 'Trinity Milliken', '2026-08-26', 'open', 890, '2026-10-19', 'Petitions the Cambridge, Ohio City Council to terminate the city use of Flock Safety ALPR cameras and remove all Flock equipment in the city. Not Cambridge, Massachusetts.'),
    ('block-flock-moveon-national', "Block Flock and Protect Americans' Privacy and Data!", 'https://sign.moveon.org/petitions/block-flock', 'MoveOn', 'National', None, 'State and city elected officials nationwide', None, None, 'open', None, None, 'Asks state and city officials nationwide to cut or refuse contracts with Flock Safety and similar ALPR vendors, limit data retention and sharing. The page shows milestone updates only (1,000 signatures reached 2026-08-26), not a live count.'),
    ('cape-fear-nc-remove-flock', 'Remove Flock AI Cameras from the Cape Fear Region', 'https://www.change.org/DeFlockILM', 'Change.org', 'Cape Fear Region, NC', None, 'County commissions of New Hanover, Onslow, Pender, and Columbus counties and the Town of Carolina Beach', 'Mark Williams', '2026-02-24', 'open', 4207, '2026-10-19', 'Asks officials across the Cape Fear region to remove Flock AI cameras; a multi-county campaign with no single tracker record.'),
    ('deflock-roseville-ca', 'DeFlock Roseville, CA', 'https://www.change.org/p/deflock-roseville-ca', 'Change.org', 'Roseville, CA', None, 'Roseville City Council and Roseville Police Department', 'Kurtis Ostrom', '2026-08-06', 'open', 758, '2026-10-19', 'Asks the Roseville City Council and Police Department to end Flock camera use.'),
    ('deflock-auburn-ca', 'DeFlock Auburn, CA!', 'https://www.change.org/p/deflock-auburn-ca', 'Change.org', 'Auburn, CA', None, 'Auburn City Council and Auburn Police Department', 'Kurtis Ostrom', '2026-08-06', 'open', 1230, '2026-10-19', 'Petitions the Auburn, California City Council and Police Department to end Flock camera use. Not Auburn, New York.'),
    ('deflock-pdx-portland-or', 'DeFlock PDX: Stop ALPR Surveillance in Portland, Oregon', 'https://www.change.org/p/deflock-pdx-stop-alpr-surveillance-in-portland-oregon', 'Change.org', 'Portland, OR', None, 'Portland City Council, Mayor, and Portland Police Bureau', 'Denise Slattery', '2026-08-15', 'open', 435, '2026-10-19', 'Calls on Portland City Council, the Mayor, and the Police Bureau to stop ALPR surveillance in Portland, Oregon.'),
    ('lancaster-county-sc-ban-flock', 'Ban and remove Flock cameras in Lancaster County, South Carolina', 'https://www.change.org/p/ban-and-remove-flock-cameras-in-lancaster-county-south-carolina', 'Change.org', 'Lancaster County, SC', None, 'Lancaster County Council', 'Timothy Phillips', '2026-07-23', 'open', 561, '2026-10-19', 'Asks Lancaster County Council to ban and remove Flock cameras in Lancaster County, South Carolina.'),
    ('pickens-county-sc-public-vote', 'Demand a public vote on Flock cameras in Pickens County, SC', 'https://www.change.org/p/demand-a-public-vote-on-flock-cameras-in-pickens-county-sc', 'Change.org', 'Pickens County, SC', None, 'Pickens County Sheriff Tommy Blankenship', 'Ashley Talley', '2026-08-06', 'open', 26, '2026-10-19', 'Demands a public vote on Flock cameras in Pickens County, whose installation the petition says was initiated solely by Sheriff Blankenship.'),
    ('mount-pleasant-sc-remove-surveillance', 'Petition to Remove All Automated Vehicle Surveillance Systems from Mount Pleasant, SC', 'https://www.change.org/p/petition-to-remove-all-automated-vehicle-surveillance-systems-from-mount-pleasant-sc', 'Change.org', 'Mount Pleasant, SC', None, 'Mount Pleasant Town Council', 'Scott Roslund', '2026-07-02', 'open', 467, '2026-10-19', 'Demands the Town Council immediately remove all automated license plate reader cameras, including Flock Safety systems and Axon Lightpost.'),
    ('horry-county-sc-ban-flock', 'Ban Flock Safety License Plate Reader Cameras in Horry County, SC', 'https://www.change.org/p/ban-flock-safety-license-plate-reader-cameras-in-horry-county-sc', 'Change.org', 'Horry County, SC', None, 'Horry County Council', 'Charles Hooks', '2026-08-27', 'open', 272, '2026-10-19', 'Asks Horry County to end its use of Flock automated license plate readers.'),
    ('abilene-tx-ban-alprs', 'Ban ALPRs and Indiscriminate Mass Surveillance in Abilene and Taylor County', 'https://actionnetwork.org/petitions/ban-alprs-and-indiscriminate-mass-surveillance-in-abilene-and-taylor-county', 'Action Network', 'Abilene and Taylor County, TX', None, 'Abilene City Council, Taylor County Commissioners Court, Abilene Police Department', None, None, 'open', 120, '2026-10-19', 'An independent DeFlock Abilene advocacy petition asking Abilene and Taylor County to ban ALPRs and indiscriminate mass surveillance.'),
    ('orange-county-ca-deflock', 'DeFlock Orange County California', 'https://actionnetwork.org/petitions/deflock-orange-county-california', 'Action Network', 'Orange County, CA', None, 'All Orange County City Council Members and County Supervisors', None, None, 'open', 37, '2026-10-19', 'Asks Orange County city councils and the Board of Supervisors to end Flock camera use across the county.'),
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
