# Lead 20: mfoil / NFoil as our own low-Re polar for the Stock rounded_plate

Date: 2026-11-04 (MST). Status: **not-worth-it** for now. No CFD was run; this was a 2-D panel and boundary-layer prototype only.
Prototype: `research/proto/lead20/` (`mfoil_proto.py`, `out.json`, `summary.txt`, `e387_retry*.py`).

## What was tried
- **mfoil:** Fidkowski 2023, MIT, v2023-06-28. I used the pymfoil 0.1.0 wheel (MIT, Papadakis 2025).
  - pymfoil 0.1.0 does not run as shipped. It has three bugs, listed in `pymfoil-0.1.0-fixes.diff`:
    - `X.shape(1)` appears twice;
    - the sparse `R_x == tuple` comparison raises ValueError on current scipy.
  - It also imports matplotlib at the top level.
  - If we vendor anything, vendor upstream `mfoil.py` with these fixes and keep the MIT header.
- **NeuralFoil 0.3.3:** MIT; depends on aerosandbox. I used the "large" model and read its `analysis_confidence`.
- **NFoil's Numba/taichi dependencies:** not checked. They are moot unless this lead is reopened.
- **Validation data:** UIUC LSAT Vol 5, used locally for validation only and not shipped.
  - E387 at Re 59.9k, cl and cd.
  - 3.1 % flat plate at Re 40.0k. This case has cl only; the file's third column is cm, not drag.
- **Stock section:** mid-span station. t/c 0.0985, camber 0.0478 at 0.49, le/te 0.2. Re 20k, 30k and 45k, α −4…12°. Compared with the repo's current `_cl_cd` table.

## Results
| case | mfoil | NeuralFoil | repo table |
|---|---|---|---|
| E387, Re 60k | 0/17 converged (`stagpoint_move` assert, ~3 s/pt) | cl good at 0–3° (α 2.03: 0.529 vs UIUC 0.530); cl +0.14…+0.25 too high at 4–7°; cd 15–40 % low there; conf 0.42–0.98 | – |
| Flat plate 3.1 %, Re 40k | 8/15 converged (~12 s/pt); cl within 0.03–0.09 of UIUC at 4–11°; wrong sign/size below 2° (α 1.1: −0.10 vs 0.11) | α 2.1: 0.40 vs UIUC 0.22; dip at 5° (0.43 vs 0.63); conf 0.40–0.83 | – |
| Stock plate, Re 20/30/45k | **0/51 converged**; when it returns numbers they are nonsense (cl 2–5.9, cd 0) | conf **0.00–0.10** at every point (out of its training set); cl peaks 0.6–0.8 at 2–3°, then dips, cd up to 0.22 | NACA-family stand-in: cl 0.23–0.27 at 0°, cd a flat 0.037–0.058 |

### Sanity check on mfoil itself
mfoil's built-in NACA2412 converges at every Re tried, at about 5 s per point. At α 2°:

| Re | cl | cd |
|---|---|---|
| 1e6 | 0.449 | 0.0058 |
| 2e5 | 0.521 | 0.0101 |
| 6e4 | 0.404 | 0.0257 |
| 3e4 | 0.103 | 0.035 |

The same points fed back in as coordinates also converge.

The E387 failure therefore lies in how the imported coordinates are handled, not in low Re:
- E387 fails even at Re 1e6.
- It still fails with the trailing edge opened, with a densified spline, and with the point order reversed.

The cause was not found within this time box.

## Verdict
Not worth it now. Neither tool gives a trustworthy Stock-plate polar:
- mfoil converged on 0 of 51 Stock points;
- NeuralFoil's own confidence is about 0 on this blunt, rounded plate.

So the "revisit with a low-Re plate polar" condition from leads 9 and 14 is not met. Getting mfoil to work would mean open-ended numerical debugging, roughly 2–4 days with no guarantee:
- the coordinate-ingest bug;
- α/Re continuation;
- XFOIL-class integral-boundary-layer methods are weak on blunt-LE plates with leading-edge bubbles, which is exactly the regime that matters.

## Side finding (already implicit in leads 9/14)
`fan_bem` calls `_cl_cd(alpha, camber, re=re)` without a thickness, so it defaults to 0.12. The Stock plate is therefore always modelled as a 12 % NACA-family section with a flat cd. Any future plate polar would also need this call to pass `section_family`/thickness.

## Revisit if
- upstream mfoil (MATLAB/Python) fixes custom-coordinate stagnation handling; or
- a measured or CFD-free plate polar for Re 20–50k with t/c around 10 % and rounded edges turns up.

Effort if reopened: M (2–4 days), uncertain.
