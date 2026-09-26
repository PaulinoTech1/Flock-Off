# Flock-Off

**Follow the money behind ALPR surveillance.**

Flock Safety has put 120,000+ automated license plate reader cameras across the US. The map of *cameras* is well covered by DeFlock. What nobody tracks is the map of *contracts*: which agencies hold them, what they cost, when they renew, and where organizers already won cancellations. Every Flock camera is a contract, every contract has a renewal date, and every renewal is a pressure window. Flock-Off is that tracker.

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
