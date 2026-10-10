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
| M2 | The scaling shortcut equals the full scorer | on every saved design with an `_eval_result.json`, rerunning the post-CFD scoring (`rescore_from_raw`) at 0.40 reproduces the saved free / load / η within 0.1 %, **and** at 0.50 the scaling shortcut matches `rescore_from_raw` within 0.1 % |
| M3 | Ranking sensitivity is reported, not judged | load-CFM rank of the current-scored designs at 0.40 / 0.50 / 0.65; list every pair that flips |

- **If M2 fails:** designs whose re-derate can't be reproduced are marked "needs re-run (old motor
  model)" instead of being rewritten.
- **Designs with no saved RPM** (optimizer trials store it only in the reason text) use that text. When
  there is no "motor-limited" note, λ_old ≥ 0.995, so λ_new = 1 and the new value is old / λ_old,
  with up to 0.5 % under-correction. That limit is stated here, not hidden.

## Result

(filled in after the run)
