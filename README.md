# Flock-Off

**Follow the money behind ALPR surveillance.**

Flock Safety has put 120,000+ automated license plate reader cameras across the US. The map of *cameras* is well covered by DeFlock. What nobody tracks is the map of *contracts*: which agencies hold them, what they cost, when they renew, and where organizers already won cancellations. Every Flock camera is a contract, every contract has a renewal date, and every renewal is a pressure window. Flock-Off is that tracker.

## Project origin and timeline

**Flock-Off was inspired by H.R. 10221, the “Flock-Off Act,” a bipartisan House bill introduced on September 2, 2026.** Rep. Thomas Massie (R-KY) introduced the legislation with original cosponsors including Eric Burlison (R-MO), Ro Khanna (D-CA), Victoria Spartz (R-IN), Paul Gosar (R-AZ), Chip Roy (R-TX), and Lauren Boebert (R-CO). Because its original sponsorship included members of both the Republican and Democratic parties, the proposal had bipartisan sponsorship from its introduction. The bill was referred to the House Committee on Oversight and Government Reform.

The bill's stated purpose is to prohibit federal funds from being used for covered camera systems and associated components. Its provisions specifically address automated license plate readers and biometric surveillance cameras, including associated contracts, subscriptions, databases, cloud services, and data-sharing arrangements. As of this writing, H.R. 10221 remains a bill introduced in the House, not enacted law.

**On September 25, 2026, 23 days after the bipartisan Flock-Off Act was introduced, the public Flock-Off repository was created.** The project adopted the same “Flock-Off” name but developed the idea into an independent open-source research project focused on documenting the public-record landscape surrounding Flock Safety ALPR contracts, costs, renewal dates, cancellations, and source provenance. GitHub records the repository's creation at September 25, 2026.

**On September 26, 2026, activity accelerated substantially.** The project expanded beyond its initial dataset with a second 10-state research wave covering **Arkansas, Iowa, Idaho, Maryland, Minnesota, Montana, Nebraska, New Mexico, Nevada, and Utah**. That expansion brought the tracker to **322 records across 45 jurisdictions** and closed Maryland's previous zero-record research gap. At that point, the methodology explicitly identified **Alaska, Hawaii, North Dakota, South Dakota, and Wyoming** as the remaining unresearched states.

The September 26 expansion was not simply bulk collection. The project formalized an evidence-validation system under which terminal claims such as a contract being **cancelled, rejected, or expired** qualify as verified only when supported by **at least one verified primary source plus two independent verified-news sources**. Advocacy organizations, campaign sites, social media, aggregators, and AI-generated summaries can provide research leads but do **not** satisfy the verification threshold. Unknown source domains fail closed to unverified, records not rechecked within 180 days automatically lose verified status until reviewed again, and cited source material is fingerprinted using cryptographic hashes and similarity measurements so substantive changes can trigger human re-review.

### Timeline

**September 2, 2026**
H.R. 10221, the **Flock-Off Act**, is introduced in the House with **bipartisan sponsorship**, including Republican members and Democratic Rep. Ro Khanna.

**September 25, 2026**
The independent **Flock-Off** open-source repository is created, 23 days after introduction of the congressional bill.

**September 26, 2026**
Research and development accelerate. A second 10-state research wave expands coverage to **322 records across 45 jurisdictions**, while the project formalizes stricter evidence-validation, source-classification, staleness, and provenance controls.

The bipartisan congressional proposal was the initial spark for the project. **Flock-Off itself is independent and is not affiliated with Rep. Massie, Rep. Khanna, any other sponsor or cosponsor, Congress, or any political party.** Its factual dataset is governed by its own published methodology, evidence thresholds, correction process, and source-provenance system.

## Use it

Live: **https://flock-off.vercel.app**

Or open `index.html` directly, or serve the directory:

```bash
python3 -m http.server 8080
# http://localhost:8080
```

Deploy: no build step. The tracker page is fully static; tip submission uses minimal serverless endpoints backed by blob storage (see Privacy posture).

## What it does

| Tab | What |
|---|---|
| **Tracker** | Searchable, filterable database of Flock contracts: status, cameras, cost, renewal dates, decision history, sources. Default sort surfaces renewals first. |
| **Map** | ALPR cameras near the map center or your location (OpenStreetMap via Overpass, DeFlock's source data). |
| **Tools** | Directory of the existing anti-Flock ecosystem. |
| **Learn** | How cancellations happen, spotting cameras, contributing. |

## The dataset

`data/agencies.json` is the whole database: one record per agency, every factual field traced to a `sources[]` entry, confidence-rated per the methodology in `docs/METHODOLOGY.md`. Coverage is USA-wide, expanding westward in 10-state waves (wave 1: OH, MI, IN, IL, WI, WV, KY, TN, AL, MS); a missing agency means not yet researched, never confirmed absent.

To contribute a contract tip (new deal, renewal date, cancellation vote): open a GitHub issue with a source link.

## Privacy posture

- No accounts, no cookies, no analytics, no fingerprinting, no third-party trackers on the page.
- The only thing stored about visitors is what they submit: tips are public documents by design. The tip form asks for no name, email, or private information, and none is stored. Client IPs are used in memory only for rate limiting the submission endpoint and never written to storage.
- Map tab exception: camera data comes from the Overpass API and map tiles from OpenStreetMap, so using the map exposes your IP and the viewed area to those services, like any online map. Precise geolocation never leaves your device.
- Hosting: the site runs on Vercel, which keeps standard edge request logs (IP, URL, time) to operate the service; that is platform-level and cannot be disabled. Flock-Off adds no tracking on top of it.
- Outbound links use `rel="noopener noreferrer"`.
- See `docs/THREAT_MODEL.md` for the full statement and `docs/DATA_SOURCES.md` for data licenses.

## Scope

Flock-Off is for awareness and lawful civic action: contract research, records requests, public pressure. It does not handle plate numbers, officers, or vehicles. It is passive and informational and does not condone touching or disabling cameras.

## Contributing

See `CONTRIBUTING.md`.

## Roadmap

See `ROADMAP.md`.

## License

MIT. See `LICENSE`.
