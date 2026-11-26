# Ruling: APC SF 9x4.7 C_T(J) RMS is a FAIL against the pre-registered 0.015 (Kimball, 2026-11-25)

**Ruling by Kimball, 2026-11-25:** "record it as a fail against 0.015". Recorded by Claude.

## What happened

- Audit #3 (`2026-09-29-audit-03-prop-bemt-uiuc.md`) pre-registered **C_T(J) RMS ≤ 0.015** and stated "Tolerances
  were not changed after seeing the data."
- APC SF 9x4.7 read 0.021–0.024 (FAIL). After a genuine bug fix (station thickness passed into the polars) it read
  about **0.0175**, still a FAIL.
- On 2026-09-30, after that data, the SF gate was "re-registered" to **0.020**, which made it pass. A tolerance
  widened after the data does not count (AGENTS.md rule 1).

## The ruling

- APC SF 9x4.7 C_T(J) RMS is a **FAIL** against the pre-registered 0.015. The 0.020 gate is not a validation pass.
- APC E 9x6 is unchanged: PASS against 0.015 (about 0.004).
- The release claim is unchanged. It is **static C_T** (SF −12.9 %, E 9x6 −1.0 %, both inside the pre-registered
  ±15 %). The SF static-C_T pass came from the bug fix judged on the unchanged tolerance, so it stands.

## Changes made with this ruling

- `fansim/audit/registry.yaml`, `propeller.bemt` claim: drops "C_T(J) RMS (tol 0.020) PASS" and states the SF
  sweep RMS as a known FAIL against 0.015, like the SF static C_P.
- `tests/audit/test_prop_bemt_audit.py`: a strict `xfail` test records the FAIL at 0.015, so it flags if the
  model ever clears it. The two 0.020 tests stay as regression guards only, and are named and documented that way.
- `docs/validation/scoreboard.md` already judged this row on 0.015 (FAIL). No change.
- The unit is re-proven with its own checks after these edits.
