# Threat model

Flock-Off is an awareness tool, not a security product. This page states plainly what it protects against, what it does not, and what data moves where.

## What the site stores

Two things, both public by design:

- **The contract dataset** (`data/agencies.json`): community-researched public records about agency Flock contracts, with per-field source citations.
- **Submitted tips**: contract tips are accepted via GitHub issues (public, attributed to the reporter's GitHub account). `/api/report` is a key-holder-only ingestion path for the operator pipeline: keyed submissions are held in a private quarantine until reviewed, and approved tips are published in the public history. A stored tip contains only what the submitter typed (agency, source URL, notes, timestamps). There is no anonymous public submission form.

No accounts, no cookies, no analytics. There is no place for private visitor data to go.

## What leaves your device

- **Everything**: only the page and its assets, served from the hosting provider. The site makes no third-party requests while you read; the only outbound traffic is the page load itself, until you click a link and leave the site.

## Hosting

The site runs on Vercel. Vercel keeps standard edge request logs (IP, URL, timestamp) as part of operating the service; that cannot be disabled on the platform. Flock-Off adds nothing on top: no analytics integrations, no cookies, no fingerprinting, no per-visitor logging in our code. The report endpoint reads the client IP only in memory for rate limiting; it is never written to storage.

## What the app does not do

- **No real-time detection of cameras.** The map shows *previously reported* camera locations. Absence of a pin means "no known camera here," never "no camera here."
- **No interference.** Everything is passive and informational. The project does not help disable, jam, or evade law enforcement in the commission of wrongdoing; it helps ordinary people understand and lawfully contest mass surveillance.

## Adversary considerations

- **Flock Safety / camera operators:** the camera locations shown are already public via DeFlock and OpenStreetMap. This app publishes nothing new.
- **Network observer:** use HTTPS (deployments should enforce HSTS). Tor for stronger protection.
- **Incorrect data:** a wrongly-placed pin could mislead someone into a false sense of safety or a needless detour. Corrections go upstream to DeFlock/OSM. The UI states that data is crowdsourced and incomplete wherever counts are shown.

## Out of scope (by design)

Plate-number handling of any kind, user accounts, push notifications, background location tracking. Server-side pieces are limited to the tip quarantine and public history; anything else that needs a backend does not belong here.
