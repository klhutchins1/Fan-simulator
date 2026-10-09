# Task 5 Report: CLI + unit flags + roadmap

**Date:** 2026-09-07  
**Status:** DONE

## Deliverables

| File | Action |
|------|--------|
| `scripts/evaluate_prop_cfd.py` | Created |
| `tests/test_prop_cfd.py` | Added 2 tests |
| `docs/roadmap.md` | §4.3 + Last reviewed updated |

## CLI

- Args: `--spec` (default `fpv_5inch`), `--rpm` (default `None` → `0.7 * rpm_max`), `--iters`, `--procs`, `--base-cell`, `--out`, `--dry-run`
- **Dry-run:** builds prop STL + compressible case via `build_prop_case`; writes `dry_run.json` with `domain_extents` (PropOpenAir) + stamps (`solver`, `domain`, `regime`); no Docker
- **Full run:** calls `evaluate_prop_cfd` when `image_available()`; writes `result.json`; exit 2 if no Docker image

## Tests

```
uv run python -m pytest tests/test_prop_cfd.py -q --tb=short
6 passed in 22.17s
```

Exit code `-1073741819` (CadQuery ACCESS_VIOLATION teardown) — assertions all passed; ignored per brief.

- `test_cli_evaluate_prop_cfd_declares_flags` — PASS
- `test_default_rpm_tip_mach_compressible` — PASS (0.7 × 30000 rpm → tip Mach ≈ 0.55)

## Roadmap

- §4.3: stage-1 wiring marked DONE 2026-09-07; Docker smoke pending Task 6
- Last reviewed: 2026-09-07

## Commit

`Task 5: prop CFD CLI, tests, and roadmap` — `catalog/catalog.db` not staged.

## Next (Task 6)

Manual Docker smoke: `--dry-run` then full run on `runs/prop_cfd_smoke`; update spec status to `implemented` when green.
