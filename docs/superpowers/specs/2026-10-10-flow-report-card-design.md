# Flow report card ("How the air moves") — design

Date: 2026-10-10 · Status: approved in conversation, awaiting spec review · Roadmap §24

## Why

The Fan → Results "Duct airflow" card shows six raw pictures that a newcomer cannot read:
- the colours are blocky, because cell data is drawn flat;
- the pressure picture is nearly one colour, because its scale is stretched by a few tip spots, and its
  unit is m²/s² (kinematic);
- the streamlines leave out the fan and look back down the axis, so they read as squares (the square
  outlet duct).

The user wants the airflow section to answer, against Stock:
1. Is the air moving the right way?
2. Where along the blade is the fan good, and where does it need work?
3. Where is air dead, blocked or wasted?
4. Where is the noise coming from?
5. Is it better than Stock overall?

This is sub-project 1 of 3 in the newcomer clean-up:
1. flow report card (this spec);
2. the simple/expert switch plus a text clean-up across the app;
3. a start page with plain tab descriptions.

## Audience and modes

- **Simple mode (default):** written for a hobbyist who 3D-prints a replacement fan. Kimball signs off
  on every word and picture. If he can't follow it, it's wrong.
- **Expert mode:** today's detail, with the picture fixes. It carries a grey note: "Technical detail,
  not reviewed for plain language". It is not polished further, because nobody available can verify it
  as an expert.
- The switch is a single global top-bar toggle (`ui_mode` = `simple` | `expert`), remembered per
  browser in `localStorage`. In this project it only affects the flow card; sub-project 2 reuses it.

## Data source

- **Design:** its Assess case directory (`Path(design.stl_path).parent`). Assess solves free air first
  and the loaded point (`load_pa`, 8 Pa for the "case" hose) last. The fields on disk are therefore
  the **loaded** point, which is the one the report uses. Fields: `U`, `p` (kinematic), `k`, `omega`.
- **Stock reference:** one designated Stock Assess case, recorded in `.cache/stock/flow_reference.json`
  (gitignored) by `scripts/set_flow_reference.py`. The initial value is
  `runs/screen_rank_audit/stock_hubclip/full` (2026-10-09, level-4 floor, hub clip, case hose).
- **Comparable** means the *test* settings match: the back pressure (`p_probe_pa / derate²` from
  `_eval_result.json` raw, rounded to 0.5 Pa, because `load_pa` itself is not stamped), `surf_max`
  (raw), and `cfd_version`, `rpm`, `duct_shape` and `casing` (`constant/case_meta.json`). A missing
  `surf_max` (runs before 2026-10-09) counts as a mismatch ("mesh level not recorded"). `hub_clip`
  is deliberately **not** a test setting: it is a property of the blade, and older runs don't record it.
  If the settings don't match, the report shows the design's own numbers without a Stock comparison
  and says why.
- **Flow axis:** in the CFD frame the flow runs from inlet −Z to outlet +Z. Forward means Uz > 0. A
  test checks this on Stock: its mean exit Uz must be positive.

## Measurements (`fansim/cfd/flow_report.py`, pure functions on arrays)

All are taken on the **exit slab**, the same plane `compute_spanwise_profile` uses
(z_fan + `_PLANE_Z_FRAC`·r_tip, ± half_dz), over hub_r ≤ r ≤ tip_r. Samples are weighted by cell
volume, which stands in for area within the slab.

| key | definition |
|---|---|
| `backflow_frac` | weighted share of slab samples with Uz < 0 |
| `net_reversed` | weighted mean Uz < 0 |
| `band_dp0_pa[5]` | 5 equal radial bands, hub to tip: ρ·(mean p_u at exit − mean p_u at inlet), where p_u = p + ½Uz², the useful push. **Swirl is excluded:** it is the separate spin row. Changed 2026-10-10 after F-check run 1; see the audit |
| `swirl_frac` | Σw·Uθ² / Σw·(Uz² + Uθ²) on the exit slab |
| `dead_frac` | weighted share of samples with \|Uz\| < 0.10 · (weighted mean Uz) |
| `tip_band_uz_ratio` | mean Uz in the outer 10 % of the span ÷ mean Uz over the whole span |
| `noise_swl_db` | Proudman SWL over the rotor region (\|z − z_fan\| ≤ 1.5·r_tip, r ≤ 1.2·r_tip), via the existing `proudman_power_density` and `epsilon_from_komega` |
| `noise_hot_mask` | the top 5 % of cells by Proudman power density, used for the picture only |

## Verdict rules (fixed now; changed only openly, see Validation)

Δ means design − Stock.

| row | ✓ | ⚠ | ✕ |
|---|---|---|---|
| Air direction | Δbackflow ≤ +0.02 | Δbackflow > +0.02 | `net_reversed` |
| Push along the blade | per band: "stronger" if > +15 %, "similar" if within ±15 %, "weaker" if < −15 % of Stock's band (**was ±10 %**: Stock run-to-run is 14.3 %, audit 2026-10-10-flow-report-checks) | — | — |
| Wasted spin | swirl_frac ≤ 1.10 × Stock | above that | — |
| Dead or blocked air | dead_frac ≤ Stock + 0.02 **and** tip ratio ≥ 0.90 × Stock | either fails | — |
| Noise hint | ΔSWL ≤ +2.8 dB | ΔSWL > +2.8 dB (**was 1.0 dB**: Stock run-to-run is 2.75 dB, same audit) | — |

- **Overall line:** "Better than Stock at: …" lists the rows that are ✓ and strictly better than Stock.
  "Worse at: …" lists the ⚠/✕ rows. The push row counts as better when the stronger bands outnumber
  the weaker ones.
- **No comparison available:** only the ✕ direction check and the raw numbers are shown.

## Pictures (`fansim/cfd/flow_report_viz.py`, off-screen PyVista, cached PNGs in the case dir)

These fixes are shared with the existing pictures in `midplane.py`, so Mixed, Volute, Prop and CROR
get them too:
- cell data is converted to point data before drawing (`cell_data_to_point_data`), giving smooth
  shading;
- pressure is drawn as ρ·p in **Pa**;
- the colour range is the Stock reference's 2nd–98th percentile, and the design uses the same range;
  the legend notes "clipped at Stock's range";
- the rotor is shown as a grey outline: a slice of `impeller_cfd.stl` on cut planes, and a 30 %
  opaque mesh in 3-D views;
- the title goes in the card's HTML, not inside the image.

New pictures, one per row (design and Stock, rendered identically):

| picture | what it shows |
|---|---|
| Fan-face map | end-on view of the exit slab: Uz shown smoothly, backflow in red, dead zones in grey, hub and blade outline |
| Push bars | 5 grouped bars (design vs Stock), matplotlib |
| Spin side-view | Y=0 cut downstream of the fan, coloured by \|Uθ\|/\|U\| |
| Noise side-view | Y=0 cut, Proudman density shown as a grey-to-orange scale, top 5 % highlighted |
| Streamlines (rebuilt) | side view; seeds on 3 rings (0.4/0.65/0.9 of r_tip) 1.0·r_tip upstream; integrated both ways; see-through rotor; coloured by speed; caption "Each line is the path a bit of air takes. Straight through = good; loops = wasted or stuck air." |

- Stock's pictures and numbers are computed once and cached next to the reference
  (`.cache/stock/flow_report/`), keyed by the reference path and a code version.
- Each design's report goes to `<case>/flow_report.json` plus PNGs, keyed by a `FLOW_REPORT_VERSION`
  constant.

## UI (Fan → Results)

- A card titled "How the air moves" replaces "Duct airflow", in the same position. It follows the
  Results dropdown selection.
- The overall line sits at the top. Each row has: an icon (✓/⚠/✕), a one-sentence verdict with the
  numbers ("2 % of the fan face flows backwards (Stock 6 %)"), the picture, and Stock's picture next to
  it. Clicking a picture enlarges it.
- In expert mode the card adds the existing six-picture toggle (with the fixes) and a numbers table
  (every key above, design vs Stock).
- The report is built off the event loop, with a one-line progress state; it reuses the existing
  `airflow_gen` / `airflow_lock` / cancel pattern in `fan_viz.py`.

**When something is missing:**

| situation | message |
|---|---|
| never assessed, or BEM-only | "No flow simulation for this design yet. Run Assess to see how the air moves." |
| `cfd_stale` / `stale_reason` set | "These results are out of date ({why}). Re-run Assess." |
| reference missing or not comparable | verdicts without comparison + "Stock hasn't been tested this way, so no comparison ({first mismatch})" |
| no `k`/`omega` | noise row hidden: "No turbulence data in this run." |
| building | "Working out how the air moves…" |

## Out of scope

- No new CFD and no score changes.
- Other tabs keep their current airflow cards; they only get the shared picture fixes.
- No interactive 3-D flow viewer.

## Validation (before the card is shown by default)

1. **Unit tests** on synthetic arrays with known answers: 10 % backflow reads 0.10 ± 0.005; pure swirl
   gives swirl_frac 1; a uniform field has dead_frac 0; the bands sum correctly; verdict thresholds
   behave correctly at their edges.
2. **Self-consistency:** using the Stock reference as the "design" gives every row ✓, every band
   "similar" and the overall line "same as Stock".
3. **Run-to-run:** Stock's 2026-10-09 pre-clip run (`runs/screen_rank_audit/stock/full`) against the
   reference must read "similar" on every row. If it doesn't, the thresholds are inside run noise: widen
   them, and record the change and the reason in this spec. Never quietly.
4. **Known cases:** 9610 (`runs/screen_rank_audit/r3_9610/full`, stalls under load) gets ≥ 1 ⚠.
   t9005 gets no ✕ and an overall line with more "better" than "worse". Results are recorded in
   `docs/validation/audits/2026-10-10-flow-report-checks.md`.
5. **Browser check** (built-in browser): the card renders for Stock, 9604 and an unassessed design;
   simple and expert modes both work; each missing-data message appears; no console errors.
