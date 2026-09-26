#!/usr/bin/env python3
"""Stamp every source in data/agencies.json with a verified true/false flag.

Classification is an explicit domain map in this file, reviewed in git.
Fail-closed: any domain not listed here stamps false. New sources added to
the dataset get flagged by the weekly monitor until classified here.

Criteria live in docs/METHODOLOGY.md ("Evidence bar"). In short:
  verified   = primary/official record, or established news outlet with an
               editorial process (bylines, corrections, masthead).
  unverified = advocacy orgs, social/video platforms, aggregators, AI
               summaries, personal blogs, unknown outlets. Usable as leads,
               never as citations toward the evidence bar.

Usage: python3 scripts/classify_sources.py [--check]
  --check: exit 1 if any source lacks a verified flag (CI / monitor use).
"""
from __future__ import annotations

import json
import sys
import urllib.parse

DATA_PATH = "data/agencies.json"
CLASSIFICATION_PATH = "data/source_classification.json"

# Established news outlets with an editorial process.
VERIFIED_NEWS = {
    "providencejournal.com", "starnewsonline.com", "floridatoday.com",
    "capecodtimes.com", "heraldnews.com", "delawareonline.com",
    "citizen-times.com", "publicopiniononline.com", "newsleader.com",
    "blueridgenow.com", "fox29.com", "fox5dc.com", "fox5atlanta.com",
    "wamc.org", "whro.org", "cfpublic.org", "wncw.org",
    "publicradioeast.org", "coastalabc.com", "ricentral.com", "pbn.com",
    "phillyvoice.com", "psucollegian.com", "highlandscurrent.org",
    "newpineplainsherald.org", "thedailycatch.org", "compassvermont.com",
    "montco.today", "jalopnik.com", "carscoops.com", "thecooldown.com",
    "govtech.com", "police1.com", "dropsitenews.com", "karmactive.com",
    "washingtonexaminer.com", "breezejmu.org",  # JMU student paper, editorial process
    "cornellsun.com", "theithacan.org",  # established student papers w/ editorial process
    "607newsnow.com",  # Cayuga Media Group local news
    "latintimes.com", "d33gy59ovltp76.cloudfront.net",  # Latin Times (+ its CDN host)
    "94hjy.iheart.com", "b101.iheart.com", "wsyr.iheart.com", "b985.fm",
    "waltontribune.com", "news.thepalmbayer.com", "cardinalpine.com",
    "cvillerightnow.com",
    # Broadcaster CDN hosts (content is republished TV-station reporting).
    "gray-whns-prod.gtv-cdn.com",
    "gray-waff-prod.gtv-cdn.com",  # WAFF 48 Huntsville (Gray)
    "gray-wbay-prod.gtv-cdn.com",  # WBAY Green Bay (Gray)
    "gray-wpta-prod.gtv-cdn.com",  # WPTA Fort Wayne (Gray)
    "cmg-cmg-tv-10070-prod.cdn.arcpublishing.com",
    "gmg-wsls-prod.cdn.arcpublishing.com",
    # Wave 1 additions (2026-09-26), reviewed in git.
    "949tnt.iheart.com",  # iHeart; precedent: other iheart.com hosts
    "star64.tv",  # WSTR Star 64 Cincinnati (Sinclair)
    "wncy.com",  # WNCY Green Bay (Midwest Communications)
    "wvlt.tv",  # WVLT Knoxville (Gray)
    "wuot.org",  # WUOT Knoxville (NPR)
    "weku.org",  # WEKU Richmond KY (NPR)
    "wrn.com",  # Wisconsin Radio Network
    "wcsufm.org",  # WCSU-FM 88.9 Wilberforce OH, NPR member station (verified 2026-09-26)
    "wcia.com",  # WCIA Champaign (Nexstar)
    "fox11online.com",  # WLUK Fox 11 Green Bay
    "fox6now.com",  # WITI Fox 6 Milwaukee
    "tmj4.com",  # TMJ4 Milwaukee (Scripps)
    "indystar.com", "jsonline.com", "jconline.com",  # Gannett
    "beaconjournal.com", "cincinnati.com", "dispatch.com",
    "courierpress.com", "postcrescent.com", "sheboyganpress.com",
    "thenorthwestern.com", "greenbaypressgazette.com", "hollandsentinel.com",
    "htrnews.com", "mansfieldnewsjournal.com", "clarionledger.com",
    "commercialappeal.com", "clevescene.com",  # alt-weekly
    "knoxnews.com",  # Knox News (Gannett)
    "cnhinews.com",  # CNHI News Indiana
    "fitchburgstar.com", "gopresstimes.com",  # WI local papers
    "akronjewishnews.com",  # community paper
    "shepherdexpress.com",  # Milwaukee alt-weekly
    "thebeatofthecapital.com",  # Jackson MS radio news
    "theindianalawyer.com",  # legal news
    "route-fifty.com",  # GovExec
    "indianacapitalchronicle.com", "kentuckylantern.com",  # States Newsroom
    "ipm.org",  # Indiana Public Media (NPR)
    "signalakron.org", "civiclex.org", "mirrorindy.org",  # nonprofit newsrooms
    "capitolcitynow.com",  # Springfield IL (WTAX)
    "alpolitics.com",  # Alabama Political News
    "boropulse.com",  # Murfreesboro Pulse
    "basedinlafayette.com",  # veteran-journalist local newsletter
    "unraveledpress.com",  # investigative outlet
    "illinoispress.org",  # IL Press Assoc (carries Pioneer Press reprint)
    "wvpress.org",  # WV Press Association
    # Established student papers w/ editorial process (precedent: breezejmu.org).
    "dailyillini.com", "idsnews.com", "lanthorn.com",
    "louisvillecardinal.com", "purdueexponent.org", "thedaonline.com",
    "irishrover.net", "washtenawvoice.com",
}

# Primary / official records: government domains, agency sites, official docs.
VERIFIED_PRIMARY = {
    "ayer.ma.us", "grotonma.gov", "stoughton.org", "ebpd.org",
    "opengovernment.ny.gov",
    "southportland-gov.community.diligentoneplatform.com",
    "resources.finalsite.net",
    "live-township-of-north-brunswick.pantheonsite.io",
    "origin.volusiasheriff.gov",
    "transparency.flocksafety.com",  # vendor portal: primary evidence of deployment
    "harrisonburgva.gov",  # official City of Harrisonburg site
    "tompkinscountyny.gov",  # official Tompkins County NY site
    "meetings.cvilledata.org",  # civic mirror hosting official Harrisonburg council docs
    "legistarweb-production.s3.amazonaws.com",  # Legistar official document store
    # Wave 1 additions (2026-09-26), reviewed in git.
    "apps.troymi.gov",  # City of Troy MI
    "champaignil.gov",  # City of Champaign IL
    "chestertonin.org",  # Town of Chesterton IN
    "cityofypsilanti.com",  # City of Ypsilanti MI
    "cityoffortwayne.in.gov",  # City of Fort Wayne IN
    "vernonhills.org",  # Village of Vernon Hills IL
    "docs.southbendin.gov",  # City of South Bend IN document store
    "collierville.granicus.com",  # Town of Collierville TN docs
    "legistar1.granicus.com",  # City of Appleton WI memo
    "content.govdelivery.com",  # City of Evanston IL official statement
    "department-test3.countyofdane.com",  # Dane County WI press release
    "cdn.euclidlibrary.org",  # Euclid public library hosting council docs
    "jeffcosheriffal.com",  # Jefferson County Sheriff AL
    "johnsoncitytn.civicweb.net",  # Johnson City TN agenda docs
    "johnsoncitytn.org",  # City of Johnson City TN
    "millingtontn.gov",  # City of Millington TN
    "kypublicnotices.newzgroup.com",  # KY legal notices
    "portal.ksba.org",  # KSBA meeting attachments (signed order form)
    "usi.edu",  # University of Southern Indiana
}

# Explicitly NOT counted toward the evidence bar. Listed here so the choice
# is reviewable; anything unlisted also stamps false (fail closed).
UNVERIFIED = {
    # Advocacy organizations: reputable, but advocacy. Leads, not citations.
    "eyesoffma.com", "riaclu.org", "deflocknewportnews.org",
    "atlasofsurveillance.org",  # EFF: approved discovery feed, records are leads.
    # Social / video / self-publishing platforms.
    "youtube.com", "patreon.com", "medium.com",
    "theinnovationattorney.substack.com",
    # Aggregators and AI-generated summaries.
    "newspub.live", "findglocal.com", "citizenportal.ai", "brief.news",
    "findingflock.com",  # approved discovery feed; cite the linked row source.
    # Activist / personal blogs.
    "thefreethoughtproject.com", "dankennedy.net",
    # Unknown or unverifiable outlets (revisit if they establish a masthead).
    "gov1.com", "washingtonsun.com", "nexfinitynews.com", "newscord.org",
    "piratemedia1.com",
    "loraindaily.com",  # unconfirmed outlet
    "quincycurrent.com",  # unconfirmed hyperlocal
    "myhuntleynews.com",  # unconfirmed hyperlocal
    "voicenews.com",  # unconfirmed hyperlocal
    "connect-clarksburg.com",  # unconfirmed local
    "bellevilleareaindependent.com",  # unconfirmed community paper
    "themidwesterner.news",  # unconfirmed
    "archynewsy.com",  # unknown provenance
    "webpronews.com",  # blog / syndicated
    "techtimes.com", "apbweb.com", "officer.com",  # trade press, per-source false
    "wyrz.org",  # low-power radio, per-source false
    "edition.pagesuite.com",  # e-edition hosting platform
    "internewscast.com", "europesays.com",  # reprint sites
    "newslocker.com",  # news aggregator
    "heartlandpost.com",  # aggregator
    "newsroom.theredemptionproject.news",  # newsletter
    "kenoshacountyeye.com",  # local blog
    "derekeder.com",  # personal blog (trustee's own account; primary-ish but blog)
    "ocdeez.github.io",  # citizen mirror of public docs
    "flocksafety.com",  # vendor: subject of the tracker, not independent
    "eff.org",  # advocacy (cited as lead)
    "aclu-wi.org",  # advocacy
    "alprwatch.org",  # advocacy / FOIA archive
    "eyesoffindiana.org", "deflockmonroe.com",  # advocacy
    "tiktok.com",  # platform (precedent: youtube.com)
}


def classify(url: str) -> tuple[bool, str]:
    host = urllib.parse.urlparse(url).netloc.lower().replace("www.", "")
    if host in VERIFIED_NEWS:
        return True, "verified-news"
    if host in VERIFIED_PRIMARY:
        return True, "verified-primary"
    if host in UNVERIFIED:
        return False, "unverified-listed"
    return False, "unverified-unlisted"


def main() -> None:
    check_only = "--check" in sys.argv
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    unlisted: set[str] = set()
    changed = 0
    for agency in data["agencies"]:
        for src in agency.get("sources") or []:
            verified, reason = classify(src.get("url", ""))
            if reason == "unverified-unlisted":
                host = urllib.parse.urlparse(src.get("url", "")).netloc.lower().replace("www.", "")
                unlisted.add(host)
            if src.get("verified") is not verified:
                changed += 1
            if not check_only:
                # Rebuild to keep a stable key order: title, url, date, verified.
                rebuilt = {
                    "title": src.get("title"),
                    "url": src.get("url"),
                    "date": src.get("date"),
                    "verified": verified,
                }
                src.clear()
                src.update(rebuilt)

    if unlisted:
        print("Unlisted domains (stamped false, review needed):")
        for h in sorted(unlisted):
            print(f"  {h}")

    if check_only:
        missing = sum(
            1 for a in data["agencies"] for s in (a.get("sources") or [])
            if "verified" not in s
        )
        print(f"sources missing verified flag: {missing}")
        sys.exit(1 if missing else 0)

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    # Publish the classification itself so the site can show it verbatim.
    from datetime import date
    classification = {
        "generated": date.today().isoformat(),
        "criteria": "docs/METHODOLOGY.md#evidence-tiers",
        "classifier": "scripts/classify_sources.py",
        "verified_news": sorted(VERIFIED_NEWS),
        "verified_primary": sorted(VERIFIED_PRIMARY),
        "unverified_listed": sorted(UNVERIFIED),
        "unverified_unlisted_seen": sorted(unlisted),
    }
    with open(CLASSIFICATION_PATH, "w", encoding="utf-8") as f:
        json.dump(classification, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"stamped {changed} source flags in {DATA_PATH}")
    print(f"wrote {CLASSIFICATION_PATH}")


if __name__ == "__main__":
    main()
