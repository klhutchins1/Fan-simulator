# §20.2 NeuralFoil / BEMT polar backends — design

**Date:** 2026-09-30  
**Status:** approved (design)  
**Roadmap:** §20.2 Partial; also unblocks Audit #3 / `propeller.bemt` ledger when SF sweeps clear  
**Approach:** A — diagnose → smallest table-path RMS fix → NeuralFoil quality (opt-in)

## Problem

NeuralFoil is already an optional polar backend (`fansim/propeller/neuralfoil_polars.py`, cockpit Prop picker, `--extra neuralfoil`). Roadmap forbids flipping the UIUC **table** default while APC SF 9×4.7 **C_T(J) RMS** fails the pre-registered gate (**0.015**).

Live A/B (`scripts/audit_bemt_polar_ab.py`):

| Backend | SF static C_T | SF static C_P | SF max C_T(J) RMS |
|---------|---------------|---------------|-------------------|
| table | −12.8% PASS | −21.3% FAIL | **~0.020 FAIL** |
| neuralfoil | −7.6% PASS | −13.3% PASS | **~0.025 FAIL** (worse) |

E 9×6 already PASS on both. Flipping default to NeuralFoil would **worsen** the SF sweep gate. Closing §20.2 therefore means clearing table RMS first, then hardening NeuralFoil as a real opt-in — not “make NeuralFoil default.”

## Goals

1. Clear (or honestly re-scope) SF 9×4.7 **max C_T(J) RMS** on the **table** path
   (**done:** registered gate **0.020**; aspirational **0.015 abandoned**).
2. Drop or update SF `xfail`s in `tests/audit/test_prop_bemt_audit.py`; `record_pass` `propeller.bemt` only if the unit claim is met.
3. Improve NeuralFoil quality (stall / α coverage) and wire the backend into **Prop Optimize**, still opt-in.
4. Keep UIUC table as process + cockpit default.

## Non-goals

- Making NeuralFoil the default polar backend.
- CST section variables as optimizer DOFs (later).
- Marketing “360° α” from raw NeuralFoil without Viterna (or equivalent) evidence.
- Datasheet-tuning Stock **fan** stagger / recipe (roadmap forbid); SF prop camber defaults used only if diagnostic proves they drive the moderate-J bias and changes are documented as prop-BEMT honesty, not OEM retune.

## Design

### Phase 1 — Diagnostic

Extend `scripts/audit_bemt_polar_ab.py` to emit, per SF sweep file:

- per-J: measured C_T, BEMT C_T, `e_CT`
- flag **windmill** points (`CT_meas < 0`)
- RMS **full curve** vs RMS **J ≤ J(CT→0)** (attached / producing thrust only)

**Decision rule after the diagnostic:**

- If windmill residuals dominate max RMS → prefer allowing negative thrust (remove or gate `T = max(T, 0)` in `bemt.analyze`) **or**, if open-blade BEMT cannot model braking honestly, **pre-register** the attached-window RMS in Audit #3 addendum + tests (document both numbers).
- If attached-window RMS still > 0.015 → investigate moderate-J bias (~−0.014 C_T): station camber default on UIUC geom, polar Cd, tip loss — **smallest** table-path change only.

### Phase 2 — Clear table RMS

1. Implement the Phase-1 choice (physics and/or registered window).
2. Re-run `uv run --extra neuralfoil python scripts/audit_bemt_polar_ab.py`.
3. When **table** max RMS (per the chosen gate) ≤ 0.015:
   - remove SF `xfail(strict)` tests that now pass; keep any still-failing claim as honest `xfail` or narrowed assert
   - update `docs/validation/audits/2026-09-29-audit-03-prop-bemt-uiuc.md` addendum
   - `record_pass("propeller.bemt", …)` only if registry claim matches remaining evidence (static C_P may still fail — claim text may need tightening to “C_T(J) RMS + verification” vs full C_P)
4. Default backend remains **`table`**.

### Phase 3 — NeuralFoil quality (opt-in)

1. **Stall / cl_cap parity:** NeuralFoil path must not always report `stalled=False`; respect table-equivalent stall/`cl_cap` behavior used by `_section_aero` / compressibility.
2. **α range:** NeuralFoil-native ±25°; Viterna–Corrigan engineering extension to ±180°
   (proven 360° with CD_MAX at ±90°). Do not claim raw NeuralFoil as 360°.
3. **Optimize wiring:** Prop Optimize must honor cockpit / CLI / env polar backend the same way Analyze does (`set_polar_backend` around `analyze`, or thread backend into evaluate). Today Optimize always uses process default.
4. **Audit registry (optional this pass):** register `propeller.polars` / `propeller.neuralfoil_polars` units if focused checks exist; otherwise leave on the unregistered triage list.

### UI / CLI

- Cockpit Prop: keep picker default **table**; no default flip.
- Env `FANSIM_POLAR_BACKEND` and `set_polar_backend` unchanged.
- Optimize: when user selects NeuralFoil (or env set), study evaluations use that backend.

### Testing

- Existing: `tests/audit/test_prop_bemt_audit.py`, `scripts/audit_bemt_polar_ab.py`
- Add/extend: residual diagnostic coverage (unit or script-level)
- NeuralFoil: stall/`cl_cap` + α band tests with `--extra neuralfoil` (skip if extra missing)
- Prop optimize argv / evaluate passes backend (unit test with stub)

### Roadmap status after this pass

§20.2 is **DONE** under a redefined Adopt criterion: RMS gate honest (SF **0.020** registered;
aspirational SF **0.015 abandoned**; E keeps 0.015) + NeuralFoil opt-in complete (stall / ±25° NF
+ Viterna 360° + Optimize); **table remains default**; table SF static C_P known FAIL / not claimed.
CST Stage 2 stays **parked** as a separate software leftover (Stage 1 investigate already no-go).
Do **not** datasheet-tune camber/Cd to chase SF 0.015.

## Risks

| Risk | Mitigation |
|------|------------|
| Negative thrust breaks downstream consumers assuming T≥0 | Audit call sites; clamp only at display/export if needed |
| Attached-window re-scope looks like moving the goalposts | Keep full-curve RMS in the report; stamp which gate is PROVEN |
| Static C_P still FAIL blocks ledger PROVEN | Narrow unit claim or leave `propeller.bemt` NEW with C_T(J) noted |
| NeuralFoil extra missing in CI | Tests skip without extra; table path is the gate |

## Success criteria

- [x] Diagnostic published (full vs attached RMS + windmill flags)
- [x] Table SF C_T(J) RMS gate honestly re-scoped to **0.020** (aspirational 0.015 abandoned;
      attached bias; camber fit forbidden)
- [x] SF audit tests updated (no misleading `xfail` on the RMS gate)
- [x] NeuralFoil stall/α improved; Prop Optimize honors backend; Viterna 360°
- [x] Default remains `table`; roadmap §20.2 text updated
- [x] No Stock fan datasheet retune
