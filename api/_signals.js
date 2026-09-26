"use strict";
/* Shared privacy-preserving submission signals for the tip pipeline
 * (api/report.js intake, api/promote.js review decisions).
 *
 * PRIVACY MODEL — what is stored and what is NOT:
 *  - Raw IPs are NEVER stored: not in memory, not in the blob store, not in
 *    logs. Rate-limit buckets and reputation counters are keyed by
 *    SHA-256("flockoff-tip-v1" | day | subnet), where subnet is the /24
 *    (IPv4) or /48 (IPv6) prefix. The day component rotates the key daily,
 *    so buckets cannot be joined across days.
 *  - Honest limitation: a /24 has only 2^24 values, so the hash is
 *    brute-forceable by anyone who can read the blob store (requires the
 *    admin blob token). This is pseudonymization with daily rotation, NOT
 *    anonymization. What it guarantees: no IP database accumulates, and a
 *    leaked day-bucket cannot be linked to any other day's traffic.
 *  - Reputation is a REVIEWER AID, never an auto-decision. A flagged bucket
 *    only adds `_signals.reputation_flag: true` to the quarantined blob so
 *    the human reviewer looks closer. Flagged tips are still stored and
 *    still reviewed; nothing is auto-rejected.
 */

const crypto = require("crypto");

const VERSION = "flockoff-tip-v1";
// Flag a bucket when it has this many rejections AND this rejection rate
// among decided submissions. Tuned for recall of spam waves, not precision;
// the human reviewer is the precision filter.
const FLAG_MIN_REJECTIONS = 3;
const FLAG_REJECT_RATE = 0.6;

function dayUTC(d) {
  return (d || new Date()).toISOString().slice(0, 10);
}

function yesterdayUTC() {
  return dayUTC(new Date(Date.now() - 24 * 3600 * 1000));
}

// Coarse subnet: /24 for IPv4, /48 for IPv6. Returns "unknown" when the
// input does not parse, so unparseable clients still get a (shared) bucket.
function subnetOf(ip) {
  if (typeof ip !== "string") return "unknown";
  const v4 = ip.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
  if (v4 && v4.slice(1).every((o) => Number(o) <= 255)) {
    return `${v4[1]}.${v4[2]}.${v4[3]}.0/24`;
  }
  if (ip.includes(":")) {
    const parts = ip.split(":").filter((p) => p.length > 0);
    if (parts.length >= 3) return `${parts[0]}:${parts[1]}:${parts[2]}::/48`;
  }
  return "unknown";
}

function bucketHash(ip, day) {
  return crypto
    .createHash("sha256")
    .update(`${VERSION}|${day}|${subnetOf(ip)}`, "utf8")
    .digest("hex");
}

function repPath(day, bucket) {
  return `signals-rep/${day}/${bucket}.json`;
}

// Sum decisions across day-buckets. `reps` is an array of parsed rep blobs.
function summarize(reps) {
  let submitted = 0, approved = 0, rejected = 0;
  for (const r of reps) {
    if (!r || typeof r !== "object") continue;
    submitted += r.submitted | 0;
    approved += r.approved | 0;
    rejected += r.rejected | 0;
  }
  return { submitted, approved, rejected };
}

function reputationFlag(summary) {
  const decided = summary.approved + summary.rejected;
  return (
    summary.rejected >= FLAG_MIN_REJECTIONS &&
    decided > 0 &&
    summary.rejected / decided >= FLAG_REJECT_RATE
  );
}

module.exports = {
  VERSION,
  FLAG_MIN_REJECTIONS,
  FLAG_REJECT_RATE,
  dayUTC,
  yesterdayUTC,
  subnetOf,
  bucketHash,
  repPath,
  summarize,
  reputationFlag,
};
