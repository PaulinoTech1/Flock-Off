"use strict";
/* Shared constant-time string comparison for API key checks.
 *
 * Single copy so the three endpoints (report, promote, pending) cannot
 * drift apart. Rejects non-strings and length mismatches up front, then
 * compares every char code so the duration does not leak the match prefix.
 */

function timingSafeEqual(a, b) {
  if (typeof a !== "string" || typeof b !== "string") return false;
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

module.exports = { timingSafeEqual };
