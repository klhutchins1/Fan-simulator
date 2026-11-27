# Pre-registration: search-space bounds & round-trip fixes (#127) — 2026-11-26

**Ruling by Cursor.** Written before changing `fansim/optimize/search_space.py`,
`fansim/optimize/study.py`, and `fansim/cockpit/fan_editor.py` (`AGENTS.md` rule 1).

## Problem

RV-3 Module 6 (`docs/review/2026-11-26-rv3-search-space.md`, issue `#127`) identified four
search-space and round-trip defects that waste optimizer CFD trials or corrupt edited designs:

1. **Non-coprime stator/rotor counts (`STATOR_BOUNDS["stator_n_extra"] = (1, 4)`):**
   For even `n_blades` (6, 8, 10) with `n_extra in (2, 4)` or `n_blades in (6, 9)` with `n_extra = 3`,
   `gcd(B, V) > 1`, causing simultaneous rotor–stator wake interactions and amplified Tyler–Sofrin
   cut-on BPF tones (Tyler & Sofrin 1962).
2. **`EXTENDED["tip_radius"] = (48.0, 58.0)` exceeds `a12x25` frame cap (`54.5 mm`):**
   Direct callers of `suggest_params(..., with_extended=True)` without an explicit `frame_half_mm` /
   `max_tip_radius` sample ~35 % out-of-frame designs that fail the build/gap gate.
3. **Unprintable `EXTENDED["thickness_mid"]` lower corner and `OPEN` not a superset of `GUIDED`:**
   - `EXTENDED["thickness_mid"] = (0.05, 0.09)` × `MIN_CHORD = 14.0 mm` = `0.70 mm` (< `0.80 mm`
     two-wall FDM floor in `fdm_rules.py`).
   - `OPEN["stagger_root"] = (20.0, 48.0)` and `OPEN["stagger_mid"] = (18.0, 42.0)` fail to cover
     `GUIDED["stagger_root"] = (19.5, 48.0)` and `GUIDED["stagger_mid"] = (27.2, 48.0)` (widened
     in R1.3 to include Stock v3 under wrap).
4. **Uneven blade spacing lost on round-trip:**
   `blade_to_flat` drops `BladeParams.blade_angles_deg` (hardcoding `spacing_spread=0.0`), and
   `fansim/cockpit/fan_editor.py` does not carry `blade_angles_deg` across slider edits.

## Ruling

| Change | Value | Rationale |
|---|---|---|
| `suggest_stator(trial, n_blades=...)` | Fixed Optuna `stator_n_extra` in `[1, 4]`, snapped to nearest coprime offset (`gcd(B, B + e) == 1`) when `n_blades` is given; `study.py` passes `n_blades=params.n_blades`. | Eliminates `gcd(B, V) > 1` BPF amplification while preserving fixed Optuna parameter distribution and backward compatibility when `n_blades=None`. |
| `EXTENDED["tip_radius"]` | `(48.0, 54.5)` | Matches default `a12x25` frame cap (`55.0 - 0.5 mm`); explicit `frame_half_mm` / `max_tip_radius` continues to override for other frames. |
| `EXTENDED["thickness_mid"]` | `(0.06, 0.09)` | Raises lower corner to `0.06 * 14.0 = 0.84 mm >= 0.80 mm` FDM floor. |
| `OPEN["stagger_root"]`, `OPEN["stagger_mid"]` | `(19.5, 48.0)`, `(18.0, 48.0)` | Restores strict `GUIDED ⊂ OPEN` invariant (Stock v3 inside both). |
| `blade_to_flat` / `blade_from_flat` / `fan_editor.py` | Preserve `blade_angles_deg` when present and `spacing_spread == 0` (and `len == n_blades`). | Prevents cockpit edits / flat serialization from silently wiping uneven spacing. |

## Pass / fail rules (fixed before edits)

| Id | Rule |
|---|---|
| P1 | For every `n_blades` in `5..11` and every raw `stator_n_extra` in `1..4`, `suggest_stator(trial, n_blades=B)` returns `n_extra` in `[1, 4]` with `math.gcd(B, B + n_extra) == 1`. `study.py` passes `n_blades=params.n_blades`. |
| P2 | `EXTENDED["tip_radius"][1] <= 54.5` (`a12x25` max tip radius) and `EXTENDED["thickness_mid"][0] * MIN_CHORD >= 0.80` mm. |
| P3 | Every key in `GUIDED` satisfies `OPEN[k][0] <= GUIDED[k][0]` and `GUIDED[k][1] <= OPEN[k][1]`; Stock v3 lies inside both `GUIDED` and `OPEN`. |
| P4 | `blade_from_flat(blade_to_flat(bp)).blade_angles_deg == bp.blade_angles_deg` for unevenly spaced blades, and editing an unrelated slider in `fan_editor` preserves `blade_angles_deg`. |
| P5 | Existing search-space, mountable, cockpit editor, and RV-1 snapshot tests remain green; `optimize.search_space_handedness` re-proven (`scripts/audit_status.py --strict`: `PROVEN=34 CHANGED=0`). |

## Result

P1–P5 **PASS**. Updated `fansim/optimize/search_space.py` (`coprime_stator_extras`,
`suggest_stator(..., n_blades=...)`, `EXTENDED["tip_radius"] = (48.0, 54.5)`,
`EXTENDED["thickness_mid"] = (0.06, 0.09)`, `OPEN["stagger_root"] = (19.5, 48.0)`,
`OPEN["stagger_mid"] = (18.0, 48.0)`, `blade_to_flat` / `blade_from_flat` `blade_angles_deg`
round-trip), `fansim/optimize/study.py`, and `fansim/cockpit/fan_editor.py`.
Re-proved `optimize.search_space_handedness` in `docs/validation/audits/ledger.json`
(`scripts/audit_status.py --strict`: `PROVEN=34 CHANGED=0 AFFECTED=0 NEW=0 UNREGISTERED=0`).
Zero drift on `tests/data/physics_snapshot.json`; 102/102 search-space/editor/snapshot tests pass.
