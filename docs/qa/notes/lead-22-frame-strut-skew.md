# Lead 22: Ito, Minorikawa & Fan 2009 (IJFMS 2(2):136): frame changes on an 85 mm fan

Date: 2026-11-04 (MST). Status: **worth-it/proposed** (geometry patch only; the CFD A/B is for Kimball to run).
Paper: J-STAGE open PDF, read for findings only. No figures or text were copied.

## Findings (paraphrased)
- **Test setup:** a 92 mm frame and 85 mm impeller, with 3 spokes so that spoke tones and frame-side tones don't coincide. Ten printed variants tested:
  - tip gap δ/B from 0.024 to 0.096;
  - outlet exit radius from 43 to 53.5 mm (a conical flare);
  - spoke skew β of −60°, −35°, 0°, +35°, +60° in the rotor plane.
- **Tip gap:** about **−4 % efficiency per +1 % of span**. A larger gap lowered the discrete tones but raised broadband noise.
- **Outlet flare:** efficiency rose steadily as the outlet widened (diffuser effect), and noise was essentially unchanged.
- **Spoke skew:** both directions cut the spoke-interaction tones about equally.
  - Efficiency was higher with counter-rotation skew, with the outer end moved against rotation.
  - The paper's CFD explanation: swirl hitting a counter-skewed spoke is sent toward the hub and then turned axial, so the spoke acts as a crude stator.
  - Exact percentages are only in the figures. I read the trend and am not quoting numbers.

## Can our model express it?
- **`cfd/frame.py` today:** four straight radial 2.4 × 8 mm box struts plus a hub barrel. There is no skew, no lean, and no section shape, so the lead cannot be expressed today.
- **Strut skew: easy.** The proposed patch `docs/qa/patches/frame-strut-skew.patch` (+ `tests/test_frame_skew.py`):
  - adds `strut_skew_deg` (default 0, which leaves geometry identical) to `build_frame_solid` and `export_frame_stl`;
  - rotates each bar in-plane about its inner end, using the sign of `rig.spin`, so negative means counter-rotation as in the paper;
  - lengthens each bar to reach the wall inset and trims it to the wall cylinder.
  - Tests pass in a temp tree with the repo venv: 10 tests, the existing `test_frame.py` plus the new ones. `git apply --check` against repo-r25b (master 0635a18) is clean. Nothing was committed or applied.
  - Volumes: 5207 mm³ radial, 5372 at ±35°, 5655 at −60°.
  - Not plumbed into `optimize/objectives.py` or the CLI (`export_frame_stl(..., strut_skew_deg=)` plus a flag). That is about 1–2 h more.
- **Outlet flare ("rounded outlet corners"): not expressible.** `cfd/casing.py` is a constant-bore tube, apart from an optional stepped inlet. A conical outlet flare would change the fluid domain and outlet/plenum handling. That is an M-sized change, so no patch now.
  - Note that the paper's gain comes from a diffuser at the frame exit. In our duct rig the flow carries on downstream in a straight tube, so the A/B would not represent a free-blowing fan.
- **Tip gap:** already a rig parameter. Stock uses 1 mm on a 33 mm span (δ/B ≈ 0.030), and the paper's trend says keep it as small as printing allows. No new work is needed.

## Suggested A/B (Kimball to run; not run here)
`strut_skew_deg` 0 vs −35 vs +35 on Stock, frame-only mode, at the same load points.
- Expect a small efficiency change: only 4 struts of 8 mm depth sit in the swirl.
- The tonal benefit would need the LBM/FW-H tier.
- This only matters for a self-printed frame.

## Patents
| patent | status |
|---|---|
| Nidec US8133022B2 | expired (per the lead) |
| US 2007/0140844 A1 (Nidec, Yoshida; ribs with an inclined air-guide face, skewed or curved against rotation) | **abandoned**: Google Patents legal event 2010-01-11, "failure to respond to an office action"; never granted |

- No US rights arise from US 2007/0140844 A1. The CN counterpart CN1987122A was not checked.
- This is not legal advice.

## Effort
- Skew patch: XS–S. It is done; plumbing takes about 2 h.
- Outlet flare: M.
