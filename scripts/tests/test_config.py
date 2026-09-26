"""Tests for scripts/flockoff_config.py: validated YAML config loading.

Every tunable the pipeline reads must be present, well-typed, and in
range; a bad config fails fast with the exact key and constraint.
"""
import os
import sys
import tempfile
import unittest

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flockoff_config import ConfigError, load_config, resolve_config_path

REAL_CONFIG = resolve_config_path()


def _temp_config(overrides=None, remove=None, raw_text=None):
    """Write a temp config: real config + dotted-key overrides, minus `remove` keys."""
    if raw_text is not None:
        text = raw_text
    else:
        base = yaml.safe_load(open(REAL_CONFIG, encoding="utf-8"))
        for dotted, val in (overrides or {}).items():
            parts = dotted.split(".")
            node = base
            for part in parts[:-1]:
                node = node[part]
            node[parts[-1]] = val
        for dotted in (remove or []):
            parts = dotted.split(".")
            node = base
            for part in parts[:-1]:
                node = node[part]
            del node[parts[-1]]
        text = yaml.safe_dump(base)
    fh = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False)
    fh.write(text)
    fh.close()
    return fh.name


class TestConfigLoading(unittest.TestCase):
    def test_real_config_loads(self):
        cfg = load_config(REAL_CONFIG)
        for section in ("paths", "urls", "fetch", "dedup",
                        "fingerprints", "monitor", "classify"):
            self.assertIn(section, cfg)
        # Repo-relative paths resolve to absolute paths.
        self.assertTrue(os.path.isabs(cfg["paths"]["data"]))
        self.assertTrue(cfg["paths"]["data"].endswith("data/agencies.json"))

    def test_missing_file(self):
        with self.assertRaises(ConfigError) as cm:
            load_config("/nonexistent/flock-off.yaml")
        self.assertIn("E_CFG_MISSING", str(cm.exception))

    def test_malformed_yaml(self):
        path = _temp_config(raw_text=": : : not yaml :::")
        try:
            with self.assertRaises(ConfigError) as cm:
                load_config(path)
            self.assertIn("E_CFG_INVALID", str(cm.exception))
        finally:
            os.unlink(path)

    def test_missing_key_names_the_key(self):
        path = _temp_config(remove=["fetch.delay_seconds"])
        try:
            with self.assertRaises(ConfigError) as cm:
                load_config(path)
            msg = str(cm.exception)
            self.assertIn("E_CFG_INVALID", msg)
            self.assertIn("fetch.delay_seconds", msg)
        finally:
            os.unlink(path)

    def test_wrong_type_rejected(self):
        path = _temp_config(overrides={"fetch.delay_seconds": "slow"})
        try:
            with self.assertRaises(ConfigError) as cm:
                load_config(path)
            self.assertIn("fetch.delay_seconds", str(cm.exception))
        finally:
            os.unlink(path)

    def test_out_of_range_rejected(self):
        path = _temp_config(overrides={"fingerprints.near_dup_distance": 99})
        try:
            with self.assertRaises(ConfigError) as cm:
                load_config(path)
            msg = str(cm.exception)
            self.assertIn("fingerprints.near_dup_distance", msg)
            self.assertIn("0..64", msg)
        finally:
            os.unlink(path)

    def test_negative_delay_rejected(self):
        path = _temp_config(overrides={"fetch.delay_seconds": -1})
        try:
            with self.assertRaises(ConfigError):
                load_config(path)
        finally:
            os.unlink(path)

    def test_cross_field_thresholds(self):
        # update_distance must exceed near_dup_distance, else the two
        # detectors overlap.
        path = _temp_config(overrides={
            "fingerprints.near_dup_distance": 10,
            "fingerprints.update_distance": 5,
        })
        try:
            with self.assertRaises(ConfigError) as cm:
                load_config(path)
            self.assertIn("update_distance", str(cm.exception))
        finally:
            os.unlink(path)

    def test_version_mismatch(self):
        path = _temp_config(overrides={"config_version": 999})
        try:
            with self.assertRaises(ConfigError) as cm:
                load_config(path)
            self.assertIn("E_CFG_VERSION", str(cm.exception))
        finally:
            os.unlink(path)

    def test_env_override(self):
        path = _temp_config()
        old = os.environ.get("FLOCKOFF_CONFIG")
        os.environ["FLOCKOFF_CONFIG"] = path
        try:
            cfg = load_config()
            self.assertEqual(cfg["_config_path"], os.path.abspath(path))
        finally:
            if old is None:
                del os.environ["FLOCKOFF_CONFIG"]
            else:
                os.environ["FLOCKOFF_CONFIG"] = old
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
