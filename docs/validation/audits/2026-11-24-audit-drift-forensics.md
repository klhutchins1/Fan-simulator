# Audit drift and red CI: why they changed (2026-11-24)

Written by Claude for Kimball. This is a **record**, not a re-proof and not a ruling. No unit is re-recorded in the
ledger by this file. The re-proof is board task RV-0 (`docs/release/RELEASE_PLAN.md`).

Checked on `cursor/ux-simple-mode-2026-11-24` (49d7436) and `origin/master` (5a05d9b); the physics files are the same
on both. Linux PC, `.venv` Python 3.12, mypy 2.3.1.

## 1. What `scripts/audit_status.py` shows

`PROVEN=25 CHANGED=5 AFFECTED=3 NEW=0 UNREGISTERED=1`

- CHANGED: `cfd.cfm_from_outlet_flow`, `cfd.flow_report`, `geometry.stock_handedness`,
  `optimize.search_space_handedness`, `propeller.cfd_setup`
- AFFECTED (only because of their dependencies): `cfd.archetype_direction`, `cfd.flow_direction_convention`,
  `propeller.thrust_sign`
- UNREGISTERED: `fansim.cfd.metrics:latest_pp_file`

Nothing fails on this. CI, `scripts/gate.py` and the night runner never call `audit_status.py`.

## 2. Method

A unit's fingerprint hashes four things: its target code (AST, comments and docstrings ignored), the installed
versions of its `libs`, its registry entry, and the source of its check test files
(`fansim/audit/fingerprint.py`). Each part was hashed on its own:

- at the commit that last wrote the unit to `ledger.json`;
- at every first-parent `master` commit after it, to find the first commit that changed that part.

None of the five units lists `libs`, and none of their registry entries changed. So library versions on this PC
explain none of the drift; it is all code or check files.

## 3. What changed and why

| unit (proven) | part that changed | first master commit (underlying commit) | what changed | does it move the maths? |
|---|---|---|---|---|
| `cfd.cfm_from_outlet_flow` (10-21) | `metrics:parse_fan_metrics`, `convergence`, `oscillation_pct` | `fce1ac0` 11-15 (`957a483` 11-09, R1.10 batch) | QA-39: `_pp_file` picked the newest `postProcessing/<time>/` folder by **name** (so `"100"` sorted before `"20"`); it now picks by numeric time through the new `latest_pp_file` | **Yes, a bug fix.** It matters only for a case with more than one time folder (restarts). It needs its own check |
| `cfd.flow_report` (10-19) | `flow_verdicts:judge`, `tests/test_flow_verdicts.py` | `3fca917` 11-08 (`8d06672` 11-04, QA-55 / R0.4) | the tip-speed + CFM noise hint is never marked quieter/louder (row state `na`) | changes a verdict on purpose (Kimball ruling: the noise hint is never judged). No number changes |
| `geometry.stock_handedness` (10-21) | `blade:build_impeller` | `93dc72a` 10-29 (`6f25583` 10-27, R1.1a) | new `BladeParams.reference_build` flag skips the print-hang refusal only (lt120 freeze) | no. Defaults to False |
| `geometry.stock_handedness` | `fansim.geometry.airfoil` | `7f96b76` 11-16 (`0eb1009` 11-15) | `rounded_plate` gains `te_face` / `le_face` wall tapers | no. Defaults to 1.0, and the taper code runs only below 1 − 1e-12 |
| `optimize.search_space_handedness` (10-15) | `fansim.optimize.search_space` | `7f96b76` 11-16 (`0eb1009`, `7d1f41e` 11-15) | flat-dict fields `te_face_*`, `le_face_*`, `root_embed`, `blade_z`; `outline_blade_flat()` | no. Default 1.0 / 0 = old shape; stagger and camber bounds untouched |
| `propeller.cfd_setup` (10-15) | `propeller.cfd:evaluate_prop_cfd`, `tests/test_prop_cfd.py` | `fce1ac0` 11-15 (`957a483` 11-09) | `PROP_CFD_HONESTY` string moved to `fansim/propeller/honesty.py` and reworded | no. Wording only |

**Measured, not just read.** Stock (`stock_blade_flat("a12x25")`, BEM `pq_curve`, 0.5 mm tip gap) gives the same
numbers at `d443682` (last ledger write) and at HEAD:

| | free CFM | shut-off Pa | peak η | hash of every P–Q point |
|---|---|---|---|---|
| `d443682` | 60.4 | 38.87 | 0.542 | `8ed15eae29d7` |
| HEAD | 60.4 | 38.87 | 0.542 | `8ed15eae29d7` |

Only the `repr` of `BladeParams` differs, because it gained the new fields. The fused STL was not rebuilt (that is
heavy CPU, and this ran in the 4–9 PM window). RV-0 re-proves geometry with the unit's own checks.

## 4. Why CI is red

- GitHub Actions has 3 runs (11-20 master, 11-25 UTC ×2 on the UX branch). All 3 fail at **mypy** before pytest
  starts, so pytest has never run on GitHub.
- The error is `fansim/optimize/search_space.py:495`
  (`float(flat[k])` where `flat` is `dict[str, object]`).
- It came in with **`20aed3e` (2026-10-08, "Stock keeps all 7 stations through the flat dict", §23.1)**: mypy passes
  on `20aed3e^` and fails on `20aed3e`. `uv.lock` has pinned mypy 2.3.1 since 09-15, so this is not a tool upgrade.
- It went unseen for 6 weeks for two reasons. `scripts/gate.py` (the gate that is actually used) runs pytest only:
  no mypy, no ruff, no `audit_status`. And CI did not run anywhere until the repo reached GitHub (R3.5, about 11-11
  to 11-20).

## 5. Work that is not on GitHub (seen from this PC)

- On GitHub: `master` and `cursor/ux-simple-mode-2026-11-24` only. `stock-outline`, `r22a-wake-aspect`,
  `r110-g2-merge` and `r111-hide-surrogate` are not branches there.
- `r111-hide-surrogate` is merged (`7f96b76`). Part of `stock-outline` and `r22a-wake-aspect` reached master: the
  11-13 to 11-15 outline/edge pre-registrations and `f4503ef` (C-grid wake cap, 11-16).
- Not in this clone: grok `handoff/*from-qa*` after 11-09 (W1 lists them to 11-15), `research/`, the leads 23–48
  `PREREG_*.md`, and `docs/qa/daily/` after 11-14. These probably exist only on the Windows PC. W1 still applies:
  run `scripts\stray_work.py` there and push.

## 6. What follows (board RV-0)

1. Fix the mypy line (no behaviour change).
2. `scripts/gate.py` runs the same checks as CI (mypy, ruff critical, `audit_status.py`), so they cannot disagree.
3. Re-prove the five units in one dated audit file that cites the commits above. Give QA-39 its own check (a case
   with time folders `20` and `100`). Register `latest_pp_file`.
4. CI fails on any CHANGED, AFFECTED, MISSING or UNREGISTERED unit.
