<!-- RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md. -->

# NF-A12x25 Reference Data (validation ground truth)

Published manufacturer specs for the **Noctua NF-A12x25 PWM** — the target our CFD must
eventually reproduce (within a stated tolerance) before any absolute-performance claim.
Sources: [Noctua specs](https://noctua.at/en/nf-a12x25-pwm/specification),
[PCPartPicker](https://pcpartpicker.com/product/zxx2FT/noctua-nf-a12x25-pwm-601-cfm-120mm-fan-nf-a12x25-pwm).

| Quantity | Published value | SI |
|---|---|---|
| Max rotational speed | 2000 RPM | 209.4 rad/s |
| Speed range (PWM) | 450–2000 RPM | — |
| **Max airflow** (free delivery) | **60.1 CFM** | 102.1 m³/h = 0.02836 m³/s |
| **Max static pressure** (shut-off) | **2.34 mmH₂O** | **22.9 Pa** |
| **Max acoustic noise** | **22.6 dB(A)** | (18.8 dB(A) min) |
| Input power (max) | ~1.68 W | — |
| Tip clearance | **0.5 mm** | Sterrox LCP + MIM hub |
| Blade count | 7 | — |

## Immediate reality check (why validation matters)

Our current idealized sim of a *9-blade envelope-approximation* baseline gives **free-air ≈
81.5 CFM**; the real 7-blade A12x25 is **60.1 CFM**. The ~30–35% over-prediction is expected
from the idealizations and must be closed/quantified before trusting absolute numbers:
- **Slip duct walls** remove all duct friction (real ducts/frames add loss).
- **No fan frame / motor struts / venturi inlet** — the real fan has flow-blocking structure.
- **No resolved tip-leakage** (0.5 mm gap, ~1 mesh cell) — a dominant real loss.
- **Fully-turbulent SST at transitional Re**, coarse mesh (grid convergence pending).
- Geometry mismatch: 9 vs 7 blades, approximate profile.

## Validation plan (review §6.1)

1. Build the **actual A12x25 geometry** (from the Thingiverse remix thing:4553248, or a
   reverse-engineered 7-blade parameter fit) rather than the envelope approximation.
2. Run the full **P–Q curve** at 2000 RPM and compare to (60.1 CFM free-air, 22.9 Pa
   shut-off). Report the error.
3. Add the missing physics in priority of impact: resolved tip gap → frame struts/venturi →
   no-slip walls → grid convergence → transition model — and watch the error shrink.
4. Only once free-air CFM and shut-off pressure land within a documented tolerance do
   absolute numbers (and any "beats stock" claim) become defensible. Relative rankings on a
   controlled printed baseline remain valid before then.

## Noise target
22.6 dB(A) max is the number the (unbuilt) FW-H aeroacoustic tier must eventually reproduce.
