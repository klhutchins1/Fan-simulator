## Research leads #23–29 (2026-11-09) — Fan Sim QA

Prereg `1bfb38c` on `prereg/research-leads23-29` before prototypes. Clone master `83681c2`. No CFD/Assess/Sweep/Optimize; no PyTorch; patches not applied.

| Lead | Status | Note |
|---|---|---|
| #23 UIUC flat-plate Cl@40k | worth-it/proposed | Cl/Cm check table + test patch; no Cd online; flat≠Stock cambered |
| #24 Pelz tip η (C·s·ψ) | worth-it/proposed | `pelz-tip-eta.patch`; calibrate C; patents expired |
| #25 Kim 2021 OGV rules | worth-it/proposed | `stator-linear-exit-frac.patch`; CC BY 4.0; avoid US8333559B2 tip lean |
| #26 fluids ISO 5167 | blocked (hardware) | MIT maths OK; same gate as #18 |
| #27 BPF / acoustic tach | worth-it/proposed | MIT; BPF sketch recovers 2000 rpm synthetic |
| #28 Ax/BoTorch qNEHVI | worth-it/proposed (optional) | MIT; ~800 MB torch; park until CFD-finalist path |
| #29 PartForge UX pattern | worth-it/proposed | 51 controls → Preset/Primary/Advanced/Hidden; tie ui-hunt-1 |

Zip: `research_leads23-29_out.zip` (placement needs Kimball approval).
