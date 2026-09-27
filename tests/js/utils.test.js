/* Tests for js/utils.js: shared escaping, DOM helpers, data paths.
 * Run: node --test tests/js/utils.test.js
 */
"use strict";

const { describe, it } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

// Load utils.js in a sandbox with minimal browser globals
const utilsPath = path.join(__dirname, "..", "..", "js", "utils.js");
const utilsCode = fs.readFileSync(utilsPath, "utf8");
const sandbox = { console };
// Expose Utils to the sandbox global after evaluation
const wrappedCode = utilsCode + "\n;globalThis.__Utils = Utils;";
vm.createContext(sandbox);
vm.runInContext(wrappedCode, sandbox);
const Utils = sandbox.__Utils;

describe("Utils.esc", () => {
  it("escapes HTML special chars", () => {
    assert.equal(Utils.esc('<script>alert("x")</script>'),
      "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;");
  });

  it("escapes single quotes", () => {
    assert.equal(Utils.esc("it's"), "it&#39;s");
  });

  it("escapes ampersands", () => {
    assert.equal(Utils.esc("a & b"), "a &amp; b");
  });

  it("handles null and undefined", () => {
    assert.equal(Utils.esc(null), "");
    assert.equal(Utils.esc(undefined), "");
  });

  it("handles numbers", () => {
    assert.equal(Utils.esc(42), "42");
  });

  it("leaves plain text unchanged", () => {
    assert.equal(Utils.esc("Hello World"), "Hello World");
  });
});

describe("Utils.PATHS", () => {
  it("defines all required data paths", () => {
    assert.ok(Utils.PATHS.agencies);
    assert.ok(Utils.PATHS.manifest);
    assert.ok(Utils.PATHS.classification);
    assert.ok(Utils.PATHS.evidence);
  });

  it("paths are strings ending in .json", () => {
    for (const [key, p] of Object.entries(Utils.PATHS)) {
      assert.equal(typeof p, "string", `${key} should be a string`);
      assert.ok(p.endsWith(".json"), `${key} should end with .json`);
    }
  });
});

describe("Utils.fetchJson", () => {
  it("is a function", () => {
    assert.equal(typeof Utils.fetchJson, "function");
  });
});
