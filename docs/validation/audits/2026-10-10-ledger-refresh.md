# Ledger refresh: 2026-10-10

Method: as in `2026-10-08-ledger-refresh.md`.
1. Run `scripts/audit_status.py`.
2. Re-run each CHANGED unit's registered `checks`, and the dependants' (no Docker).
3. When they are green, `record_pass` with the new fingerprint and this report.

| Unit | Change | Checks | Verdict |
|------|--------|--------|---------|
| `geometry.stock_handedness` | §25.2 / QA-21 `_trim_blade_to_tip_cylinder`: after the plain attempts at exactly R, retry with the cutter 0.02 mm and then 0.05 mm inside R before the existing fallbacks. **Root cause:** the outermost loft section sits at r = R, so its mid-chord touches the cutter tangentially. On the QA repro, a featured blade with 43° lean, OCCT returned empty at R and a clean result at R ± 0.02. Stock and every design whose plain cut works are unchanged (the first attempt still wins) | `tests/audit/test_stock_handedness.py`, golden/validation geometry, `tests/test_tip_trim.py` (new repro test), plus the dependants' checks (direction contract, orientation, placement, CROR/mixed setup, prop thrust sign / builder direction / CFD setup, math consistency, convergence) | **PASS**: 108 passed. The QA repro now builds a watertight 10-blade impeller with r_max 52.534 ≤ R 52.554 |

The dependants (`cfd.*`, `propeller.*`) return to PROVEN with their parent; none of their own code
changed.
