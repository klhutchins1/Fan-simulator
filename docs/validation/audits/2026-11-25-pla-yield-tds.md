# PLA yield → NatureWorks ~60 MPa (#51) — 2026-11-25

**Ruling by Cursor.** Before changing `MATERIALS["PLA"].yield_strength_mpa`.

`tests/audit/test_structural_audit.py` already cites NatureWorks Ingeo 3D850 TDS:
PLA yield ~60 MPa; Eastman/generic PETG ~50 MPa. The table allowed PLA Y∈[35,70] and
PETG Y∈[35,55], but both catalogue entries were 50 MPa — identical root-bending SF.

## Pass / fail

| Id | Rule |
|----|------|
| P1 | `MATERIALS["PLA"].yield_strength_mpa != MATERIALS["PETG"].yield_strength_mpa` |
| P2 | Both stay inside the existing TDS ranges in `test_structural_audit.py` |
| P3 | `structural.deflection` (+ dependants centrifugal/flutter if CHANGED) checks green; `record_pass` |

No model-vs-data threshold change beyond the catalogue number.

## Result
P1–P3 PASS. PLA yield 50→60 MPa (NatureWorks); PETG stays 50. Four structural units re-proven.

## Snapshot follow-through (2026-11-25, Cursor)

`#64` landed the 60 MPa PLA yield but did not rewrite `tests/data/physics_snapshot.json`.
Structural PLA safety factors move with yield (bending_sf / centrifugal_sf). Refreshing the
snapshot against this audit so RV-1 CI matches the shipped materials table.
