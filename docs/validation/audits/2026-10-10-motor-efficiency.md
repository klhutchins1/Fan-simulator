# Motor efficiency 0.40 → 0.50 and re-derate of saved scores (pre-registered 2026-10-10)

Decision (Kimball, 2026-10-10): use the researched motor efficiency (`docs/qa/notes/motor-efficiency.md`,
QA round 6, Task C).

**Change:**
- `motor_efficiency` goes from 0.40 to **0.50** for the NF-A12x25 class motor: `FanSpec "a12x25"` and
  `fansim.motor.envelope.A12X25_MOTOR`.
- The input power stays at the rated **12 V × 0.14 A = 1.68 W**: the most the motor can supply, as
  before.
- The Delta AFC1212DE (a ~19 W motor class, not researched) keeps 0.40.

**Why the input power stays at 1.68 W:**
- The budget means "the most shaft power this motor can deliver".
- The measured 1.3–1.5 W is what a real NF-A12x25 *draws with its own impeller*, not its ceiling.

**Consistency check:**
- The real fan holds 2000 rpm with the real impeller, so a correct model must **not** derate Stock.
- At 0.40 the model derates Stock to 1907 rpm, which contradicts the fan's own spec.
- At 0.50 the budget is 0.84 W, against Stock's 0.775 W shaft power.

## Re-derating saved scores without CFD

The derate is λ = min(1, (budget / P_shaft)^(1/3)), and the affinity laws say flow ∝ λ and pressure ∝ λ².
On the quadratic hose line (fixed k) the operating point therefore also scales with λ, and the
straight-line η is unchanged. A saved score can be re-derated from its saved RPM alone:
λ_old = actual_rpm / 2000, P_shaft = B_old / λ_old³, and λ_new = min(1, λ_old · (B_new/B_old)^(1/3)).
Free and load CFM scale by λ_new/λ_old; η stays the same. Print knockdowns are multiplicative and
unchanged.

## Rules (fixed now)

| id | check | pass rule |
|---|---|---|
| M1 | Stock is not derated at 0.50 | Stock's shaft power from the 2026-10-09 hub-clip run gives λ = 1.000 |
| M2 | The scaling shortcut equals the full scorer | on every saved `_eval_result.json` (Assess dirs and `runs/screen_rank_audit/*/full`) **without `refine_op`**: (a) rerunning the post-CFD scoring (`rescore_from_raw`) at 0.40 reproduces **that file's own** free / load / η within 0.1 %; **and** (b) at 0.50 the scaling shortcut applied to that file's numbers matches `rescore_from_raw` at 0.50 within 0.1 % |

*Amendment, 2026-10-10, before any check was run:*
- M2 first compared `_eval_result.json` with `design.json`. But some `_eval_result.json` files predate a
  later re-Assess of the same design (design_9000: 38.9 vs 51.6 CFM), so that comparison would test
  file history, not the math.
- M2 now checks each file against its own numbers.
- `refine_op` designs (3) ran extra CFD at the derated point, so the shortcut isn't exact for them.
  They get "needs re-run (old motor model)" if their derate changes.
| M3 | Ranking sensitivity is reported, not judged | load-CFM rank of the current-scored designs at 0.40 / 0.50 / 0.65; list every pair that flips |

- **If M2 fails:** designs whose re-derate can't be reproduced are marked "needs re-run (old motor
  model)" instead of being rewritten.
- **Designs with no saved RPM** (optimizer trials store it only in the reason text) use that text. When
  there is no "motor-limited" note, λ_old ≥ 0.995, so λ_new = 1 and the new value is old / λ_old,
  with up to 0.5 % under-correction. That limit is stated here, not hidden.

## Result (2026-10-10, `scripts/rederate_scores.py`, details in `2026-10-10-motor-efficiency.json`)

| id | verdict | evidence |
|---|---|---|
| M1 | **PASS** | Stock (hub-clip run) shaft power is 0.761 W, under the 0.84 W budget, so λ = 1.000. At 0.40 it was 0.959 (1919 rpm) |
| M2 | **FAIL on (a), as written; (b) PASS** | (a): 30 of 33 files reproduce within 0.1 %. 3 do not: design_9000, 9002 and 9003 (1.7 %, 1.1 % and 0.13 %), all three `opt_run1` files written by an earlier scorer version. **None of the three was speed-limited** (λ_old = 1 → λ_new = 1), so the re-derate leaves them unchanged and the failure changes no saved value. (b): the shortcut matches the full scorer on **33 of 33** (max error 0.0). 14 files were skipped: 6 infeasible, 8 refine_op or without metrics |
| M3 | reported | 76 cockpit designs: 128 rank pairs flip at 0.50 and 161 at 0.65 (most are stale designs). Among current-scored designs, **t9005 stays first**; 9016, 9631 and 9503 move up past 9003 and 9604 |

**Applied (backups in `runs/_backup_motor_eff_20261010/`):**
- 78 `design.json` stamped `motor_eff = 0.5`; 21 scores went up, by 0.2–7.7 %.
- One `refine_op` design (9013) got "needs re-run (old motor model)". It was already "blade below hub".
- 1,277 optimizer trials stamped; none changed. `fansim/optimize/objectives.py` writes "motor-limited"
  into each trial's reason whenever it slows a design, and no trial has that note.
- The catalog was rebuilt.

**Current-scored designs, load CFM (free / load / η), old → new:**
- t9005: 65.8 / 48.6 / 32.0 → **70.1 / 51.8 / 32.0** (was slowed to 1878 rpm; now 2000)
- 9016: 68.2 / 46.3 → 73.4 / 49.8 (still motor-limited at 1870 rpm)
- 9631: → 73.4 / 49.8
- 9503: → 62.7 / 49.6
- 9003: → 63.4 / 49.0
- 9632: → 69.5 / 48.6
- 9604: → 58.5 / 48.3
- **Stock: 49.8 / 41.0 / 18.3 → 51.9 / 42.7 / 18.3**

Efficiency never changes: it is a property of the operating point, not of the speed.
