# QA round 26 pre-registration (grok)

**Written:** 2026-11-04 MST, before any r26 data.

**Code:** clone of `fansim.bundle` in this folder (master at the commit that added the folder).

**Not yet opened:** any r26 code diff, render or pytest output on that clone.

## Status words

- **verified:** the item's pass rule holds on this master.
- **still open:** the pass rule fails.
- **partly fixed:** some sub-rules pass, others fail; list each.
- **not re-tested.**

## Rules

**QA-66.** Code reading plus `tests/test_surrogate_guided.py` and `tests/test_r111_cockpit_surrogate.py`. **Verified** only if all five hold; otherwise **partly fixed** with the list, or **still open**.

1. With `--verify-cfd`, DoE training rows are not `synthetic_label`. Catalog rows and/or CFD verifies only, or the run refuses.
2. `scripts/run_surrogate_search.py` does not add `--stub-labels` when neither `--verify-cfd` nor `--stub-labels` is given. It refuses.
3. Stub outputs on disk (`surrogate_guided.json` and/or `stub_result.json`) carry "synthetic labels, not CFD".
4. `--verify-cfd` with no catalog, or fewer than 8 free-air rows, refuses up front (not an empty result after a silent stub).
5. When the catalog fills `efficiency` (always) or `cfm_load` (when curve `k` is missing), `surrogate_guided.json` stamps those keys "prior, not CFD".

**QA-65.** Do not apply patches. **Verified** if all three hold:

1. `git apply --check docs/qa/patches/r24-C-k1-visible.patch` **fails** (code already applied).
2. `score_caption` / `stamp_score_extra`: `converged is False` shows "did not settle"; True, None, and a missing key do not. `tests/test_score_caption.py` passes.
3. Optimize trials carry `converged` (`fansim/optimize/study.py` sets the user attr; `fansim/cockpit/data.py` copies it).

**UI-26.** **still open** if 'Gold = parametric Stock' (or equivalent) is visible on the first view in Simple or Expert at 1366 or 1920. **verified** only if it is gone from the first view in both modes at both sizes. A 1366 Simple miss that also happened on the other size in the same run, with no code change, is render timing, not a pass.

**UI-31 / QA-62.** Not in this round unless a regression is obvious while doing A.
