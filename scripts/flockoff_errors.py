#!/usr/bin/env python3
"""Stable error codes for the Flock-Off maintenance pipeline.

Every failure mode gets a code with a fixed prefix:
  E_*  error: something is broken, a human must intervene
  W_*  warning: degraded but the run completed; review when convenient
  I_*  informational: an action item for the weekly triage, not a failure

Codes are stable across runs and greppable. Each code maps to a remediation
in docs/ERRORS.md. Emit them via fmt(), e.g.:

    from flockoff_errors import fmt
    print(fmt("E_DS_FETCH", "connection refused"), file=sys.stderr)
"""
from __future__ import annotations

# code: (severity, one-line summary, remediation pointer)
REGISTRY: dict[str, tuple[str, str, str]] = {
    # --- config -----------------------------------------------------------
    "E_DEP_MISSING": (
        "error",
        "PyYAML is not installed",
        "pip install -r scripts/requirements.txt",
    ),
    "E_CFG_MISSING": (
        "error",
        "config file not found",
        "restore config/flock-off.yaml; see docs/ERRORS.md#e_cfg_missing",
    ),
    "E_CFG_INVALID": (
        "error",
        "config failed validation",
        "fix the named key per the reported constraint; see docs/ERRORS.md#e_cfg_invalid",
    ),
    "E_CFG_VERSION": (
        "error",
        "config_version mismatch",
        "migrate the config to the loader's schema; see docs/ERRORS.md#e_cfg_version",
    ),
    # --- dataset / fingerprints inputs ------------------------------------
    "E_DS_FETCH": (
        "error",
        "dataset fetch from GitHub raw failed",
        "check network and githubstatus.com, then rerun; see docs/ERRORS.md#e_ds_fetch",
    ),
    "E_DS_PARSE": (
        "error",
        "dataset JSON is unparsable",
        "validate data/agencies.json locally (python -m json.tool); the file on main may be mid-push, wait and rerun",
    ),
    "E_FP_FETCH": (
        "error",
        "fingerprints file fetch failed",
        "same as E_DS_FETCH; fingerprints sections are skipped this run",
    ),
    "E_FP_PARSE": (
        "error",
        "fingerprints JSON is unparsable",
        "regenerate via: python3 scripts/flockoff.py fingerprints refresh",
    ),
    # --- layer 1: source keys ----------------------------------------------
    "E_KEY_MISSING": (
        "error",
        "citation has no source_key",
        "run: python3 scripts/flockoff.py keys backfill, then review the diff",
    ),
    "E_KEY_STALE": (
        "error",
        "source_key does not match canonical(url)",
        "run: python3 scripts/flockoff.py keys backfill, then review the diff",
    ),
    "E_KEY_DUP": (
        "error",
        "duplicate source_key within one agency",
        "remove the redundant citation (keep the stronger one), then rerun keys check",
    ),
    "E_KEY_BADURL": (
        "error",
        "source URL has an unexpected scheme",
        "fix the URL in data/agencies.json (http/https only)",
    ),
    # --- upstream discovery feeds (weekly monitor) --------------------------
    "W_UPSTREAM_FF": (
        "warning",
        "Finding Flock tracker check failed",
        "manual spot-check https://www.findingflock.com/learn/flock-contract-cancellations this week",
    ),
    "W_UPSTREAM_ATLAS": (
        "warning",
        "EFF Atlas CSV check failed",
        "manual spot-check https://www.atlasofsurveillance.org/download.csv?vendor=Flock+Safety this week",
    ),
    # --- layers 2/3: fingerprints (weekly monitor) --------------------------
    "W_FP_MISSING_KEYS": (
        "warning",
        "citations have no fingerprint entry",
        "run: python3 scripts/flockoff.py fingerprints refresh, then push",
    ),
    "W_PROBE_BLOCKED": (
        "warning",
        "update probe hit bot-blocked pages",
        "no action: blocked pages are unverifiable by design, recorded, never evaded",
    ),
    "W_PROBE_ERROR": (
        "warning",
        "update probe hit fetch errors",
        "transient; they retry on the next weekly rotation automatically",
    ),
    # --- informational triage items -----------------------------------------
    "I_DUP_PAIR": (
        "info",
        "near-duplicate source pair detected",
        "human review: same-agency pairs are removal candidates, cross-agency pairs are informational only",
    ),
    "I_SOURCE_CHANGED": (
        "info",
        "cited article materially changed since citation",
        "re-verify the claim against the live page before trusting the citation",
    ),
}


def summary(code: str) -> str:
    """One-line summary for a code; 'unknown code' for unregistered ones."""
    entry = REGISTRY.get(code)
    return entry[1] if entry else "unknown code"


def remediation(code: str) -> str:
    """Remediation pointer for a code."""
    entry = REGISTRY.get(code)
    return entry[2] if entry else "see docs/ERRORS.md"


def fmt(code: str, detail: str = "") -> str:
    """Render '[CODE] detail -- remediation' for logs and issue bodies."""
    sev, summ, rem = REGISTRY.get(code, ("?", "unknown code", "see docs/ERRORS.md"))
    base = f"[{code}] {summ}"
    if detail:
        base += f": {detail}"
    return f"{base} -- {rem}"


def is_registered(code: str) -> bool:
    return code in REGISTRY
