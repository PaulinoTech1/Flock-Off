/* Tests for api/_errors.js: error code structure and completeness.
 * Run: node --test tests/js/errors.test.js
 */
"use strict";

const { describe, it } = require("node:test");
const assert = require("node:assert/strict");
const { CODES } = require("../../api/_errors.js");

describe("Error code structure", () => {
  it("every code returns code, error, action, and ts", () => {
    for (const [name, fn] of Object.entries(CODES)) {
      const result = name === "REPORT_400_003" ? fn(["test error"]) : fn();
      assert.equal(result.code, name, `${name}: code field must match key`);
      assert.ok(result.error, `${name}: must have error message`);
      assert.ok(result.action, `${name}: must have action guidance`);
      assert.ok(result.ts, `${name}: must have timestamp`);
      assert.ok(!isNaN(Date.parse(result.ts)), `${name}: ts must be valid ISO date`);
    }
  });

  it("codes follow ENDPOINT_STATUS_SEQ format", () => {
    for (const name of Object.keys(CODES)) {
      assert.match(name, /^[A-Z]+_\d{3}_\d{3}$/, `${name} must match format`);
    }
  });

  it("covers all four endpoints", () => {
    const prefixes = new Set(Object.keys(CODES).map(c => c.split("_")[0]));
    assert.ok(prefixes.has("PROMOTE"), "must have PROMOTE codes");
    assert.ok(prefixes.has("REPORT"), "must have REPORT codes");
    assert.ok(prefixes.has("PENDING"), "must have PENDING codes");
    assert.ok(prefixes.has("HISTORY"), "must have HISTORY codes");
  });

  it("REPORT_400_003 includes validation details", () => {
    const result = CODES.REPORT_400_003(["field x is required"]);
    assert.deepEqual(result.details, ["field x is required"]);
  });
});
