# Built blade vs its sliders on wrapped builds, QA round 9 Task B

Branch `cylinder-sections` @ 7b02bed. Prereg `PREREG_R9.md` §Task B (a0260c0). Scripts
`handoff/2026-10-12_from-qa-9/scripts/run_b.py` and `pop_b.py`. Data `handoff/.../data/b_results.jsonl.gz` and
`b_population.jsonl.gz` (gitignored).
- The method is round-8 `run_d`: 2-blade `build_impeller`, `measure_sections` at each station radius (tip capped at
  0.99 R), analytic NACA camber bias.
- New this round: a "clip-reached" flag per station. The lone chord-realised blade is cut unclipped and
  `clip_blade_below`-clipped; a station is reached iff the two chords differ by more than 0.1 mm.
- All 26 designs are wrapped (`section_wrap = cylinder`).
- Material = |chord error| > 3 % or |net camber gap| > 0.005.
- The root station (inside the hub) is unreadable on every design, as before.

## 1. Stations the clip does not reach: V1 confirmed except two inner Stock stations (rule: NOT confirmed as registered)

58 readable stations. All 52 with chord/r ≥ 0.4 have chord error |Δ| ≤ 0.43 %, and 50/52 have camber within 0.005.

The 2 exceptions are both on **Stock v3**:

| station | r | camber_p | read | bias | net | chord |
|---|---|---|---|---|---|---|
| 1 | 27.3 mm, r/R 0.50 | 0.0323 | 0.0191 | −0.0069 | **−0.0063** | −0.02 % |
| 2 | 32.7 mm, r/R 0.60 | 0.0475 | 0.0331 | −0.0090 | **−0.0054** | 0.00 % |

Stock stations 3–6 are within 0.0007. Both exceptions are only just over the line, at the innermost readable
stations (chord/r 0.71–0.78). Stock is `section_family: plate`, but the bias I subtract is the NACA 4-digit
reference. So this could be estimator bias rather than geometry; I did not prove it either way.

t9000/2/3/5 and the 18 non-hanging stress designs are all clean.

## 2. Stations the clip reaches: chord is fixed, camber and stagger still move

QA-30 is fixed for chord.

8 stations were clip-reached: lt120 stations 3–9 and S1_0378 station 1. The clip removed 1.5–11.1 mm of chord
there, yet the built chord is only 0.4–2.0 % short: the realisation now stretches the loft to make up for it.

**Camber still reads low, by a net 0.002 to 0.011, getting worse outboard:**
- lt120 stations 5–9: −0.0050 … −0.0083;
- S1_0378 station 1: −0.0111.

**Stagger is −0.6° to −1.1°** at the same stations.

So 6 of the 8 are material on camber. On these stations the clipped section is a truncated airfoil. The chord
realisation can restore its length, but not its camber line. → **QA-32 (MED, new).**

## 3. The stress population: how often the clip matters

Sample: 200 random unshrouded stress designs (seed 9011). Each is a lone chord-realised wrapped blade, untrimmed and
unclipped.

- **40/200 (20 %) hang below the hub face.** Median 2.6 mm; 27 hang more than 1 mm, 13 more than 3 mm, and the
  worst is 13.0 mm.
- Every stratum has some: S1 10/55, S4 8/34, S5 8/32, S2 5/17, S3 3/23, S6 3/21, S8 2/17, CTL 1/1. Hanging
  doesn't track tip lean (lean_tip 4–45°).
- In the first 60, 10 designs hang. **9 of them have a clip-reached station: 10/185 stations (5.4 %), almost all
  the mid-span station.**
  - The clip removes 0.5–9.8 mm of chord there.
  - The rest of the stress population hangs −1.5 mm, which is the hub_axial_margin. In other words it sits above
    the face.

**Answer to "does the clip need its own fix":** yes, but for camber/stagger rather than chord. About one optimizer
design in 6–7 has a mid-span station whose built camber is 0.005–0.011 below its slider and whose stagger is up to
1° off.

Options (proposal only):
- (a) Realise camber and stagger as well as chord at clip-reached stations (measure the clipped section).
- (b) Raise the hub face, or grow `hub_axial_margin`, so that the TE corner doesn't hang. That is a design-space
  constraint.
- (c) Report "clip-altered stations" in the design caption so the user sees it.
