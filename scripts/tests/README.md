# Flock-Off test suite

Stdlib `unittest` only. Run with `python3 scripts/flockoff.py test`
(from anywhere; the CLI cds to the repo root). Exit 1 on any failure.

## Module map

Each test module mirrors exactly one pipeline script. When a test
fails, the module name tells you which script broke:

| test module            | covers                    | a failure means                                  |
|------------------------|---------------------------|--------------------------------------------------|
| `test_config.py`       | `flockoff_config.py`      | `config/flock-off.yaml` is invalid or the loader regressed |
| `test_errors.py`       | `flockoff_errors.py`      | registry drift: a script emits an unregistered code, or an entry lost its summary/remediation |
| `test_source_keys.py`  | `source_keys.py`          | URL canonicalization or key hygiene changed      |
| `test_fingerprints.py` | `source_fingerprints.py`  | simhash/text-extraction/config accessors changed |
| `test_classify.py`     | `classify_sources.py`     | evidence-tier classification changed             |
| `test_monitor.py`      | `weekly_monitor.py`       | monitor helpers (dates, name normalization, table parsing) changed |

## Good break vs bad break

A failing test is a **good break** (update the test) when the behavior
change was deliberate:

- a config tunable changed on purpose (e.g. `stale_days` 180 -> 200):
  update the threshold assertion in `test_config.py` / `test_monitor.py`;
- a domain was re-tiered on purpose: update the domain-count assertions
  in `test_classify.py` (`test_counts`) and the sample-domain tests;
- an error code was renamed or reworded on purpose: update the registry
  and the assertions in `test_errors.py`;
- canonicalization was extended on purpose (e.g. a new tracking param):
  add the case to `test_source_keys.py`.

A failing test is a **bad break** (fix the code) when nothing was meant
to change:

- `test_no_verified_source_is_unlisted` fails: the YAML domain lists
  lost coverage (this exact bug dropped 87 domains on 2026-09-26);
- `test_preserves_source_key_and_unknown_fields` fails: write-mode
  classification is dropping fields again (the 2026-09-26 data-loss bug);
- `test_all_emitted_codes_are_registered` fails: a new code was emitted
  without a registry entry and a remediation;
- `test_check_mode_passes` / `test_clean_passes` fail: the real dataset
  violates an invariant the pipeline depends on.

## Rules for adding tests

1. New behavior in a script gets a test in its mirror module.
2. New error codes must be registered in `scripts/flockoff_errors.py`
   (the meta-test enforces this).
3. Dataset-driven tests (`TestDatasetConsistency`) use the real
   `data/agencies.json` as the oracle; keep them read-only (`--check`).
4. Network is never touched: mock `fetch_page` for fingerprint tests.
