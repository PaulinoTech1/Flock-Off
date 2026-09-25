# Threat model

Flock-Off is an awareness tool, not a security product. This page states plainly what it protects against, what it does not, and what data moves where.

## What the app knows about you

Nothing, by construction. There is no backend, no database, no analytics, no cookies, no accounts. The strongest privacy control is the absence of a place to put your data.

## What leaves your device

When you use the map, radar, or route features, your browser makes ordinary HTTPS requests to public services:

- **Overpass API** (camera data): request includes your IP and the bounding box you asked about. The bbox reveals an area of interest, not your identity.
- **Nominatim** (address search): the address text you type.
- **OSRM** (routing): origin/destination coordinates.
- **OSM tiles / Leaflet CDN**: standard web requests with IP + user-agent.

This is the same exposure as loading any online map. If that is unacceptable for your situation, use Tor Browser: the app is fully client-side and works fine over Tor (geolocation will be unavailable; use manual map panning).

Geolocation, when you grant it, is consumed by JavaScript running locally. Coordinates are never transmitted to any Flock-Off infrastructure because none exists.

## What the app does not do

- **No real-time detection of cameras.** Radar mode checks your GPS against *previously reported* camera locations. A silent phone means "no known camera here," never "no camera here."
- **No avoidance routing.** Route analysis counts known cameras near a route. DeFlock and FlockHopper do true avoidance routing; we link to them instead of shipping a worse copy.
- **No interference.** Everything is passive and informational. The project does not help disable, jam, or evade law enforcement in the commission of wrongdoing; it helps ordinary people understand and lawfully contest mass surveillance.

## Adversary considerations

- **Flock Safety / camera operators:** the camera locations shown are already public via DeFlock and OpenStreetMap. This app publishes nothing new.
- **Network observer:** use HTTPS (deployments should enforce HSTS). Tor for stronger protection.
- **Incorrect data:** a wrongly-placed pin could mislead someone into a false sense of safety or a needless detour. Corrections go upstream to DeFlock/OSM. The UI states that data is crowdsourced and incomplete wherever counts are shown.

## Out of scope (by design)

Plate-number handling of any kind, user accounts, server-side storage, push notifications, background location tracking. If a feature needs a backend, it does not belong in Flock-Off v1.
