# r20 C: TU Delft benchmark prop, what the CFD build still needs (R2.2)

grok QA bot, 2026-10-21 MDT. Prereg `2c4380d`.
- **Source:** Casalino, Grande, Romani, Ragni & Avallone 2021, *Aerospace Sci. Technol.* 113:106707,
  doi:10.1016/j.ast.2021.106707, **CC BY 4.0**. Box copy sha 9a5c4323…ee01. No secondary sources were needed.
- **Table:** `docs/qa/r20/r20-C-tud-build-details.csv`, one row per item with its value, kind
  (stated / scaled-from-figure / not stated) and the page, figure or table it comes from.
- Chord, twist and C_T/C_Q were already digitised in r19 and are not redone. The rulings doc (§2) still says "r20 C
  digitises Fig 4", but the brief was trimmed in ee2cf94.

## What the paper gives
- **Hub:**
  - radius 12.5 mm (r/R 0.083), stated;
  - a flat-faced cylindrical boss with **no spinner**, from Figs 2–3;
  - boss length: **not stated**.
- **Root:**
  - Stated: "an elliptical root section is merged with the profiled section starting from a radius of 1 cm
    (r/R = 6 %)". That puts the root start *inside* the stated 12.5 mm hub radius, which is inconsistent as written.
  - The Fig 4 chord and twist begin at r/R ≈ 0.19 (r19 first point 0.193). NACA 4412 is defined from there outward.
  - **The 12.5–29 mm transition is not specified.**
- **Tip:** a finite-chord, squared (cut) tip, from Fig 3. Fig 4 gives c/R 0.067 at r/R = 1 (≈ 10 mm). No rounding or
  cap is stated.
- **Rig:**
  - **Open jet**, in the semi-anechoic TU Delft A-Tunnel, with a **vertical jet blowing upward**. Nozzle exit 0.60 m,
    contraction 15:1, jet area ≈ 4× the disc.
  - **Tractor** layout: the rotor sits at the nozzle-side end of a **50 mm-diameter profiled aluminium nacelle**,
    which lies in the slipstream. That nacelle holds the 27.8 mm motor, encoder, load cell and torque cell.
  - Nacelle length is **not stated**. In the Fig 5 schematic, which is not to scale, nacelle plus post ≈ 2.3 D.
  - Support: hollow NACA 0012 struts of 6 cm chord on four 2 cm wire tubes.
  - Balance: a Futek LSB200 thrust cell (22.2 N) and an RTS-25 torque cell (0.18 N·m), both inside the nacelle.
- **Rotor-to-nozzle distance:** the paper says both "about 0.5 m" (p.2) and "about 1.2 nozzle diameters" (= 0.72 m,
  p.3). These disagree; the CFD build should pick one and say which.
- **Trip on the force data:** not stated. Noise was measured with and without a 25 %-chord suction-side strip, and
  Fig 21 says "untripped". Treating Figs 19–20 as the clean blade is an assumption.
- **The paper's own CFD** is free-stream only: no nozzle, jet, nacelle rig or struts. It flags the finite jet as an
  unquantified loading effect.

## Implication for the CFD prereg (Claude's call, after A0)
- A free-stream CFD with a flat boss and no nacelle matches the paper's own simulation.
- A nacelle (50 mm, length unknown) and the jet are the two rig effects the paper leaves unquantified. If included,
  each needs an assumed dimension, which should be pre-registered as such.
