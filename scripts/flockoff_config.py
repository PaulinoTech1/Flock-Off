#!/usr/bin/env python3
"""Validated loader for config/flock-off.yaml.

Every maintenance script gets its tunables from here instead of module
constants. Loading validates types and ranges and fails fast with the exact
key and constraint, so a typo'd threshold is a loud error, never silent
wrong behavior.

Resolution order for the config file:
  1. --config PATH / explicit argument
  2. FLOCKOFF_CONFIG environment variable
  3. <repo root>/config/flock-off.yaml (repo root = parent of scripts/)

Usage:
    from flockoff_config import load_config
    cfg = load_config()            # uses default resolution
    cfg["fetch"]["delay_seconds"]  # validated values
    cfg["_repo_root"]              # absolute repo root (helper, not in YAML)
    cfg["_config_path"]            # which file was loaded (helper)
"""
from __future__ import annotations

import os
import sys

try:
    import yaml
except ImportError:
    print(
        "[E_DEP_MISSING] PyYAML is required but not installed. "
        "Run: pip install -r scripts/requirements.txt",
        file=sys.stderr,
    )
    sys.exit(2)

CONFIG_VERSION = 1


class ConfigError(Exception):
    """Raised with code E_CFG_INVALID / E_CFG_MISSING / E_CFG_VERSION."""


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


# (dotted key, expected type, constraint fn, constraint description)
SCHEMA = [
    ("config_version", int, lambda v: v >= 1,
     "must be a positive int (mismatches raise E_CFG_VERSION)"),
    ("paths.data", str, lambda v: bool(v), "must be a non-empty path"),
    ("paths.fingerprints", str, lambda v: bool(v), "must be a non-empty path"),
    ("paths.classification", str, lambda v: bool(v), "must be a non-empty path"),
    ("urls.dataset", str, lambda v: v.startswith("https://"),
     "must be an https URL"),
    ("urls.fingerprints", str, lambda v: v.startswith("https://"),
     "must be an https URL"),
    ("urls.finding_flock_tracker", str, lambda v: v.startswith("https://"),
     "must be an https URL"),
    ("urls.atlas_csv", str, lambda v: v.startswith("https://"),
     "must be an https URL"),
    ("fetch.user_agent", str, lambda v: bool(v), "must be non-empty"),
    ("fetch.delay_seconds", (int, float), lambda v: _is_num(v) and v >= 0,
     "must be a number >= 0"),
    ("fetch.timeout_seconds", (int, float), lambda v: _is_num(v) and v > 0,
     "must be a number > 0"),
    ("fetch.max_bytes", int, lambda v: v > 0, "must be an int > 0"),
    ("dedup.host_prefixes", list, lambda v: all(isinstance(x, str) for x in v),
     "must be a list of strings"),
    ("dedup.tracking_params", list, lambda v: all(isinstance(x, str) for x in v),
     "must be a list of strings"),
    ("dedup.tracking_prefixes", list, lambda v: all(isinstance(x, str) for x in v),
     "must be a list of strings"),
    ("fingerprints.min_text_len", int, lambda v: v >= 0, "must be an int >= 0"),
    ("fingerprints.pair_min_len", int, lambda v: v >= 0, "must be an int >= 0"),
    ("fingerprints.near_dup_distance", int, lambda v: 0 <= v <= 64,
     "must be an int in 0..64"),
    ("fingerprints.update_distance", int, lambda v: 0 <= v <= 64,
     "must be an int in 0..64"),
    ("fingerprints.max_age_days", int, lambda v: v >= 0, "must be an int >= 0"),
    ("monitor.renewal_window_days", int, lambda v: v > 0, "must be an int > 0"),
    ("monitor.stale_days", int, lambda v: v > 0, "must be an int > 0"),
    ("monitor.update_probe_sample", int, lambda v: v > 0, "must be an int > 0"),
    ("monitor.update_probe_delay", (int, float), lambda v: _is_num(v) and v >= 0,
     "must be a number >= 0"),
    ("classify.verified_news", list, lambda v: all(isinstance(x, str) for x in v),
     "must be a list of strings"),
    ("classify.verified_primary", list,
     lambda v: all(isinstance(x, str) for x in v), "must be a list of strings"),
    ("classify.unverified", list, lambda v: all(isinstance(x, str) for x in v),
     "must be a list of strings"),
]


def _get(dotted: str, cfg: dict):
    cur = cfg
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None, False
        cur = cur[part]
    return cur, True


def validate(cfg: dict) -> None:
    if not isinstance(cfg, dict):
        raise ConfigError("[E_CFG_INVALID] top level must be a mapping")
    problems = []
    for dotted, types, ok, desc in SCHEMA:
        val, found = _get(dotted, cfg)
        if not found:
            problems.append(f"{dotted}: missing ({desc})")
        elif not isinstance(val, types):
            problems.append(
                f"{dotted}: expected {getattr(types, '__name__', types)}, "
                f"got {type(val).__name__}")
        elif not ok(val):
            problems.append(f"{dotted}: {desc}, got {val!r}")
    # Cross-field sanity: update threshold must exceed near-dup threshold,
    # otherwise "material rewrite" and "near-duplicate" overlap.
    f = cfg.get("fingerprints", {})
    if (isinstance(f.get("near_dup_distance"), int)
            and isinstance(f.get("update_distance"), int)
            and f["update_distance"] <= f["near_dup_distance"]):
        problems.append(
            "fingerprints.update_distance must exceed "
            "fingerprints.near_dup_distance")
    if problems:
        raise ConfigError(
            "[E_CFG_INVALID] config validation failed:\n  - "
            + "\n  - ".join(problems))


def default_config_path() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(here)
    return os.path.join(repo_root, "config", "flock-off.yaml")


def resolve_config_path(explicit: str | None = None) -> str:
    if explicit:
        return explicit
    env = os.environ.get("FLOCKOFF_CONFIG")
    if env:
        return env
    return default_config_path()


def load_config(explicit: str | None = None) -> dict:
    path = resolve_config_path(explicit)
    if not os.path.isfile(path):
        raise ConfigError(
            f"[E_CFG_MISSING] config file not found: {path} "
            f"(see docs/ERRORS.md#e_cfg_missing)")
    with open(path, encoding="utf-8") as fh:
        try:
            cfg = yaml.safe_load(fh)
        except yaml.YAMLError as exc:
            raise ConfigError(
                f"[E_CFG_INVALID] YAML parse error in {path}: {exc}") from exc
    validate(cfg)
    if cfg.get("config_version") != CONFIG_VERSION:
        raise ConfigError(
            f"[E_CFG_VERSION] config_version {cfg.get('config_version')} "
            f"!= supported {CONFIG_VERSION}")
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg["_repo_root"] = repo_root
    cfg["_config_path"] = os.path.abspath(path)
    # Resolve repo-root-relative paths to absolute.
    for key in ("data", "fingerprints", "classification"):
        rel = cfg["paths"][key]
        cfg["paths"][key] = rel if os.path.isabs(rel) else os.path.join(repo_root, rel)
    return cfg
