# Research leads #23–29 (2026-11-09 scout batch)

Date: 2026-11-09 (America/Denver). Prereg: `prereg/research-leads23-29` @ `1bfb38c` (before any prototype).
Clone: `/workspace/fansim/repo-leads2329` @ master `83681c2`. No CFD/Docker/Assess/Sweep/Optimize; no PyTorch install; no commits in the clone; nothing on Kimball's PC.

## Per-lead verdicts (one line)

| Lead | Status | One-line verdict |
|---|---|---|
| #23 UIUC flat-plate Cl @ Re≈40k | **worth-it/proposed** | Licence OK (free commercial + attribution); 27 upsweep pts @ Re 40021 parse clean; Cl rises 0.22→0.71 from 2°→6°; ship as Cl/Cm check table (no Cd online) — not a Stock BEM polar. |
| #24 Pelz tip-clearance η | **worth-it/proposed** | Formula is **C·s·ψ² for ψ_gap** (lead said s²ψ²); patents expired; opt-in η knockdown beside `K_TIP_LEAK`; calibrate C on Stock tip A/Bs (~40 if Ito-anchored). |
| #25 Kim 2021 OGV rules | **worth-it/proposed** | CC BY 4.0; 30% linear exit + 0.25D duct not in stator today; 2-D already matches; avoid Active US8333559B2 tip-lean geometry; use rules not absolute angles. |
| #26 fluids ISO 5167 | **blocked (hardware)** | MIT; orifice solver works (12 CFM toy @ 200 Pa / 50→25 mm); gated like lead #18 until orifice + ΔP sensor exist. |
| #27 acoustic tach / BPF RPM | **worth-it/proposed** | MIT; sounddevice MIT + numpy BSD; paper-tab tool awkward on a ducted fan; ~40-line BPF FFT recovers 2000 rpm on synthetic 9-blade tone. |
| #28 Ax/BoTorch qNEHVI | **worth-it/proposed (optional)** | Both MIT; distinct from Optuna GPSampler (#5); torch wheel ~770–900 MB — keep extras-only; payoff only on tiny CFD budgets, not BEM stub. |
| #29 PartForge progressive disclosure | **worth-it/proposed** | MIT patterns; Fan tab has 51 v_models, 37 VExpansion, **0** "Advanced" folds; map to Preset/Primary/Advanced/Hidden; tie to ui-hunt-1. |

## #23 UIUC Vol 5 flat-plate polars
- **Licence re-check:** pd.html "GPL'd Data" — free commercial use with attribution; redistribute with copyright, GPL, Manifesto. Not NC/ND.
- **Data:** `fp_baseline_lift.dat` — 5 Re blocks (40k…120k), 53 α each (upsweep+downsweep). **No** `fp_baseline_drag.dat` in vol5 listing (confirmed).
- **Prototype:** `research/proto/lead23/compare_cl.py` — Re 40021 upsweep Cl at 2.1°=0.22, 6.13°=0.71; thin-airfoil 2πα close near 0–6°, overpredicts past stall. Physically plausible.
- **vs Stock:** flat plate ≠ cambered rounded_plate (leads 9/14/20). Useful as NeuralFoil/plate **check**, not a drop-in BEM polar until Cd exists (Vol 5 PDF book).
- **Patch:** `docs/qa/patches/uiuc-flat-plate-cl-check.patch` — validation CSV + NOTICE + test. Not added to `_FAMILIES` (needs Cd).

## #24 Pelz & Karstadt (2010)
- **PDF:** J-STAGE free; findings only, no figures copied.
- **Formula correction:** ψ_gap ≈ C·s·ψ_ideal² → Δη ≈ C·s·ψ_ideal. Linear in relative clearance s=S/Do; quadratic in loading. Lead summary's "s²ψ²" overstates the s power (O(s²) discarded).
- **Patents:** US7326032B2 Expired–Lifetime; US8568095B2 Expired–Fee Related (hardware, not the formula).
- **vs today:** `K_TIP_LEAK=9` knocks outer-span swirl ~gap/chord; no explicit η(s,ψ). Pelz adds loading-dependent η for shrouded vs open ranking.
- **Toy:** with Ito-anchored C≈42, Δη(0.5→1.5 mm) @ ψ=0.35 ≈ 0.12; with undigitized C=2, <1% — **calibrate C** on Stock tip A/Bs before trusting magnitude.
- **Patch:** `docs/qa/patches/pelz-tip-eta.patch` — `pelz_tip_eta_knockdown()`, `PELZ_TIP_ETA=False` default. `git apply --check` clean on 83681c2. Not applied.

## #25 Kim et al. 2021 (CC BY 4.0)
- **Licence:** Crossref → https://creativecommons.org/licenses/by/4.0/ confirmed.
- **Rules vs `stator.py`:**
  1. **30% linear exit** — NOT present (single NACA4, camber_pos=0.4). Gap.
  2. **2-D averaged inlet** — already 2-D extruded constant section + single stagger (50°). Match; keep; don't chase 3-D twist.
  3. **~0.25 Ds duct after short vanes** — not a stator solid param; document for domain/case builder.
- **Patents (quick):** US8333559B2 **Active** (tip lean / reverse stacking + tip camber/chord growth) — distinctive, **not** the 30% linear-exit rule. Do not ship that tip geometry. Search not exhaustive. Not legal advice.
- **Caveat:** hub ratio 0.41, ~880 rpm industrial wall fan — use rules, not absolute angles.
- **Patch:** `docs/qa/patches/stator-linear-exit-frac.patch` — plumbs `linear_exit_frac` (default 0.30); piecewise cambered-LE/flat-TE builder still TODO. `git apply --check` clean. Not applied.

## #26 fluids ISO 5167
- **Licence:** MIT (LICENSE checked).
- **Prototype:** fluids 1.1.0 `differential_pressure_meter_solver` (ISO 5167 orifice, flange taps): D=50 mm, d=25 mm, DP=200 Pa → ~12.2 CFM.
- **Status:** **blocked (hardware)** same gate as lead #18. Maths ready for a thin `rig_flow_from_dp` wrapper when the orifice exists. Do not copy ISO 5167 standard text.

## #27 Acoustic tachometer + BPF RPM
- **Licence:** MIT; deps sounddevice (MIT) + numpy (BSD) — OK. No GPL.
- **Stock tool:** paper/plastic tab strike once per rev — awkward on a spinning ducted fan.
- **BPF sketch:** `docs/qa/notes/lead-27-bpf_rpm_sketch.py` — synthetic 9-blade 2000 rpm → peak at 300 Hz → RPM exact. Caveat: strut tones (lead 1) can confuse naive peak-pick; band around expected BPF.
- **Use:** leads 15/16 balancing/tap + rig ingest `rpm=` without FG wire.

## #28 Ax + BoTorch qNEHVI
- **Licence:** Ax MIT; BoTorch MIT (LICENSE files checked). **PyTorch not installed** this run.
- **Size:** torch manylinux x86_64 wheels ~770–900 MB — must stay optional extra.
- **vs lead #5:** Optuna GPSampler is single-ish GP inside Optuna; this lead is **qNEHVI multi-objective hypervolume** + optional fully Bayesian GP for tens of CFD points.
- **Current stack:** NSGA-II + catalog GP surrogate_prescreen; no Ax path.
- **Verdict:** worth-it as optional CFD-finalist path (effort M); park wiring until a real tiny-CFD budget workflow needs it. No patch.

## #29 PartForge progressive disclosure
- **Licence:** MIT; patterns only (no JS vendoring into Trame).
- **Pattern:** presets → primary sliders → collapsed Advanced → `hidden`.
- **Fan tab today:** 51 `v_model`s, 37 `VExpansion`, **0** literal "Advanced". Mapping in `handoff/.../cockpit-control-buckets.json`.
- **Action:** regroup `fan_tab_ui.py` without new backend; coordinate with ui-hunt-1 clutter findings. Effort S. No code patch this round (mapping is the deliverable).

## Tracker / QA_REVIEW
Statuses written into `research/LEADS_TRACKER.md` (rows kept). Snippet for `QA_REVIEW.md` in this zip.

## Revisit / blocked
- #23 Cd: digitize from Vol 5 PDF book before BEM family wiring.
- #26: unblock with orifice + ΔP hardware (with #18).
- #28: wire only when CFD-finalist budget is a live workflow.
