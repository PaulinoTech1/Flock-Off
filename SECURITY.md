# Security Policy

## Supported Versions

Flock-Off is continuously deployed. The `main` branch auto-deploys to
production on Vercel; there are no versioned releases. Security fixes land
on `main` and deploy with the next build.

| Deployment | Supported |
| ---------- | --------- |
| Production (`main` on Vercel) | Yes |
| Any other branch or fork | No |

## Reporting a Vulnerability

Open a private security advisory on GitHub
(repo Settings > Security > Advisories > New draft advisory). Do not open a
public issue for a suspected vulnerability.

Include: what you found, where (URL or file path), steps to reproduce, and
the impact as you see it. Reports are assessed by the solo maintainer;
expect an initial response within 7 days. If the report is accepted, a fix
is pushed to `main` and deployed; you will be credited unless you ask not
to be. If it is declined, you will get the reasoning.

## Security Model

This is a public read-mostly tracker with a narrow write path. The model
is fail-closed: anything unconfigured or unauthenticated refuses rather
than degrades.

**Reading is anonymous.** No accounts, no cookies, no analytics, no
sessions. The tracker, map, and legal pages work without identifying the
reader. Geolocation for the map stays on-device. Third-party exposure is
limited to the map tile and geocoding providers and is disclosed in the
UI (Overpass API, OpenStreetMap tiles, Nominatim, OSRM).

**Writing requires keys.** Report submission (`/api/report`) requires
`REPORT_WRITE_KEY` (constant-time compared `x-report-key` header).
Quarantine review (`/api/promote`, `/api/pending`) requires
`REPORT_ADMIN_KEY`. If either key is unset in the environment, the
endpoint answers 503 and changes nothing. There is no guest or fallback
write path.

**Rate limiting is per subnet bucket, privacy-preserving.** Buckets are
keyed by a daily-rotated salted hash of the /24 (IPv4) or /48 (IPv6)
subnet; raw IPs are never stored. Limits are 10 writes per bucket per
hour and 500 writes per day globally. State is in-memory per serverless
instance, so enforcement is best-effort under scale-out; the keys above
are the real gate.

**Reputation signals inform human review only.** Per-bucket submission
outcomes are counted under the same daily-rotated pseudonym. A poor
history flags a quarantined tip for closer human review; nothing is
auto-rejected and nothing is auto-approved. See `api/_signals.js` for the
model and its documented limitations.

**Dataset integrity is signed.** `data/integrity/manifest.json` carries
the SHA-256 of the dataset and an Ed25519 signature from the pipeline
key; the public key is published at `data/integrity/pubkey.pub`. The push
gate refuses to publish unless the test suite, source-key hygiene,
classification checks, manifest hash, audit-log tip, and signature all
verify. See `docs/RELEASE_SIGNING.md` for what the signature does and
does not attest.

**Content Security Policy is enforced.** The production CSP is set in
`vercel.json` (self-only scripts/styles, no objects, no framing) and is
verified clean in headless Chromium.

## Known Limitations (not vulnerabilities)

- Vercel edge logs are platform-level and cannot be disabled; this is
  disclosed in the site's privacy copy rather than claimed away.
- Rate-limit state does not survive serverless scale-out; a determined
  actor can get more attempts than the nominal limits by spreading
  across instances. The write keys remain the effective control.
- The pipeline signing key lives on the maintainer's build machine; a
  compromise of that machine defeats the signature. Key rotation, not
  secrecy theater, is the mitigation (see `docs/RELEASE_SIGNING.md`).
- The drift gate re-verifies cited sources before pushes and fails
  closed on unverifiable sources, but source availability varies;
  transient bot-blocks are retried, persistent ones block the push.

## Out of Scope

- The upstream sources cited by the tracker (news outlets, government
  sites). Report issues with those to their owners.
- Vercel, GitHub, or OpenStreetMap platform vulnerabilities. Report
  those to the respective platform.
- Social-engineering or physical attacks against the maintainer.
