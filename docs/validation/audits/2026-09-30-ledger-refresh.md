# Ledger refresh — 2026-09-30

Change-driven re-audit after §19.15 / §19.17 / §19.4 / air consolidation landed
new fingerprints on previously PROVEN units.

## Method

1. `uv run python scripts/audit_status.py` → CHANGED / AFFECTED / NEW list.
2. Re-run each unit's registered `checks` (no Docker).
3. On green, `record_pass` with the new fingerprint and this report path.
4. Leave units whose claim is still unmet as NEW / open.

## Results

| Unit | Prior | Checks | Verdict |
|------|-------|--------|---------|
| `structural.deflection` | CHANGED | `test_structural_audit` + `test_deflection` | **PASS** — beam closed-forms + Hermite FE still within Audit #5 tols; regime stamp is additive |
| `structural.centrifugal` | CHANGED | structural audit | **PASS** |
| `structural.flutter` | CHANGED | structural audit + `test_flutter` | **PASS** — `beam_aspect_ratio` WARN is additive, not a formula change |
| `structural.balance` | CHANGED | structural audit | **PASS** |
| `audit.direction_geometry` | CHANGED | direction geometry / verdict tests | **PASS** |
| `geometry.stock_handedness` | CHANGED | stock handedness tests | **PASS** — mirror export additive |
| `cfd.flow_direction_convention` | CHANGED | direction contract + sanity | **PASS** |
| `cfd.cfm_from_outlet_flow` | AFFECTED | (dependency only) | returns **PROVEN** once parents re-pass |
| `propeller.thrust_sign` | AFFECTED | thrust-sign tests | returns **PROVEN** once parents re-pass |
| `propeller.bemt` | NEW | `test_prop_bemt_audit` (2× `xfail` SF) | **kept NEW** — SF C_P / C_T(J) RMS still FAIL (Audit #3 / §19.15) |

## Command evidence

```
127 passed, 2 xfailed  # structural + bemt + direction + stock + thrust_sign
77 passed              # direction_verdict + search_space_handedness + cfd_sanity
```

## Unregistered triage

See `2026-09-30-unregistered-triage.md`. Scaffolding exempted; real physics
clusters remain for later unit registration (not claimed PROVEN here).
