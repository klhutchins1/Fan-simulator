# Round 18, Task B (R2.3a): velocity-triangle check of the Shigemitsu stagger ruling (amendment §2)

Prereg `5df5059`. Report only: the pre-registered rule changes the ruling only if it is "clearly inconsistent".

- **Data:** `docs/qa/r18/r18-B-shigemitsu-velocity-triangles.csv` (72 rows: 2 conventions × 6 sensitivity settings ×
  6 stations).
- **Scripts:** `handoff/2026-10-20_from-qa-18/scripts/b_triangles.py`, plus the post-hoc `b_euler_posthoc.py`.
- **Inputs:** Shigemitsu 2018 (CC BY 4.0) Table 1 and text, as listed in `r17-B-digitised-cror-centrifugal.md`.

## Set-up
- **Flow:**
  - Q_o = 0.55 m³/min, uniform axial velocity over the blade annulus: front 15.38 m/s (Ø25–37.2 mm), rear 16.49 m/s
    (Ø26–37.2 mm);
  - front at 15 000 rpm, rear counter-rotating at 14 000 rpm.
- **Incidence:**
  - i = β₁ − γ: the relative inlet angle minus the chord angle, both from the axis;
  - convention P (the ruling): γ = 90° − s; convention X: γ = s.
- **Front exit swirl:**
  - mid-span, from the generic NACA 4 %/40 % mean line (χ_LE 11.31°, χ_TE 7.59°) with Carter deviation;
  - spread by free vortex r·c_u = const;
  - the rear sees W_u = U_rear + c_u2.
  - Under P: c_u2,mid = 2.30 m/s (Carter δ = 4.0°). Under X: 16.69 m/s.

## Result (nominal)
| station | U (m/s) | β₁ from axis | P: γ / i | X: γ / i |
|---|---|---|---|---|
| front hub | 19.63 | 51.9° | 71.8° / **−19.9°** ✗ | 18.2° / +33.7° ✗ |
| front mid | 24.43 | 57.8° | 58.8° / **−1.0°** ✓ | 31.2° / +26.6° ✗ |
| front tip | 29.22 | 62.2° | 54.0° / **+8.2°** ✓ | 36.0° / +26.2° ✗ |
| rear hub (c_u 2.75) | 19.06 | 52.9° | 49.4° / **+3.5°** ✓ | 40.6° / +26.5° ✗ (c_u 19.96) |
| rear mid (c_u 2.30) | 22.80 | 56.7° | 50.0° / **+6.7°** ✓ | 40.0° / +27.3° ✗ |
| rear tip (c_u 1.92) | 27.27 | 60.5° | 44.5° / **+16.0°** ✗ | 45.5° / +22.7° ✗ |

In the X rows the rear c_u values are X's own swirl estimate.

- **Verdict, as pre-registered: P = MID-ONLY** (4/6 within ±15°: both mid stations pass, the front hub and rear tip
  fail). X = 0/6.
- The verdict holds at every sensitivity setting:
  - P gives 4–5/6 (c_ax × 0.85 / 1.15, swirl × 0 / 0.5 / 1.5), so it's MID-ONLY throughout;
  - X gives 0/6, rising to 3/6 only with zero rear swirl.
- **Not "clearly inconsistent"** (P never passes fewer stations than X), so **the ruling stands**.
  "Stagger from the rotation plane" is consistent at mid-span and at 4 of 6 stations, not all six.

## Things the ruling doesn't settle (report only, → QA-50)
- **Under P, the front rotor's twist runs against the flow.**
  - Its chord angle from the axis falls 17.8° from hub to tip, while the inlet flow angle rises 10.3°. That is why
    the incidence runs from −20° at the hub to +8° at the tip.
  - Under X, the twist has the right sign at both rotors, but the incidence is offset by a uniform +23 to +34°.
- **Work budget (post-hoc, not pre-registered).** With the ruled generic camber (4 %), the ideal (lossless) Euler
  rise at mid-span is:
  - **under P:** front 67 Pa + rear 212 Pa = **279 Pa**, against the **measured 510 Pa** at Q_o. With
    4 %-camber blades read from the plane, the model can't reach the measured curve even with no losses;
  - **under X:** 1240 Pa ideal, the right order for a ~40 % efficient stage. But X needs about 10 % camber
    (NACA m ≈ 0.10) to bring the front mid-span LE incidence to zero, which is a heavily cambered small-fan blade.
- So "P + 4 % camber" and "X + about 10 % camber" are both kinematically coherent somewhere. Only the first is
  consistent with Table 1's literal numbers at mid-span with generic camber, and it under-delivers on work.
- This sharpens the amendment's own expectation ("A1/A2 likely to miss"): under P with 4 % camber, A1 is expected to
  miss low by roughly half.
- Claude may want to record before the CFD whether S1′ (the sign of dΔP/dQ) is still meaningful with a stage that
  can't reach the measured pressure.
