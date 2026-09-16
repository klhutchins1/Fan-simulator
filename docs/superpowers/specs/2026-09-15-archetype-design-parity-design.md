# Archetype Design Parity — Design Spec

**Date:** 2026-09-15  
**Roadmap:** §14  
**Status:** implemented (2026-09-15) — §14.1–14.5 landed; Volute Optimize 14.4b still open.

## Intent

Bring Prop / Mixed / Volute / CROR cockpit Design (+ Optimize where cheap) up toward Fan-like depth.
This is **UI + search vocabulary**, not new CFD fidelity campaigns. Keep/cut board still parks
archetype CFD expansion; Design editors are an explicit parallel track.

## Feature matrix (Fan lever → archetype)

| Lever | Prop | Mixed | Volute | CROR |
|-------|------|-------|--------|------|
| Blade count | yes | yes | yes | yes (front/rear) |
| Chord planform | yes (× tip R) | single → span later | N/A (radial height) | yes mm front/rear |
| Pitch / stagger | pitch→twist | stagger | N/A | stagger ± |
| Thickness t/c | yes R/M/T | yes (scalar) | blade_thick_mm | yes R/M/T |
| Camber | yes R/M/T | yes + camber_pos | N/A | yes R/M/T |
| Sweep / LE curve / sickle | yes | N/A stage-1 | N/A | light yes |
| Wrap (lean) | light tip | N/A | N/A | light |
| Tip round / cylindrical | yes | N/A | N/A | yes |
| Uniform wall mm | yes | later | blade_thick is mm | yes |
| Motor cup / Fit frame | **no** | mount gauge | N/A | thin-to-25mm |
| Shroud / stator | **no** | **no** | tongue/scroll | **no** |

## Contracts

1. Flat ↔ params round-trip for every Design slider.
2. Optuna `suggest_*` searches the same keys Design can set (or document fixed).
3. Old Pareto/Assess flats load with defaults for missing keys.
4. Tooltips via `*_copy.py` / shared `blade_copy.py`.

## Phases

- **14.1** Prop BladeParams depth  
- **14.2** Shared BladeParams editor kit  
- **14.3** Mixed thickness/camber (+ optional span loft later)  
- **14.4** Volute dormant params (+ optional Optimize 14.4b)  
- **14.5** CROR dual BladeParams Design + expanded suggest  

## Non-goals

Fan motor-cup Fit, stator/shroud on open props, claiming Mixed axial-duct CFD is calibrated,
blocking on hardware §5.
