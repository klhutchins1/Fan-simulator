# Lead #9: Balla & Vad (2021) cambered-plate lift/drag (investigated 2026-10-08)

**Verdict: not worth it for now.** It makes the Stock prediction worse. The formulas are being used outside the range they were fitted for. They also do nothing about the stall exploit.

## Source
I read the accepted manuscript from the MTAK repository.
- **What the formulas give:** third-order polynomials in angle of attack, with coefficients that vary quadratically with camber. Lift and drag at a given Re are found by extrapolating linearly from Re = 3e5 (Eqs. 2–7, Tables 2–5).
- **Validity range:** **angle 0–10° only**, camber 0–8 %, **Re 6e4–3e5**.
- **Licence:** the manuscript says "non-commercial, no derivatives". Putting the table coefficients in code with a citation is our usual math-from-papers practice, but that is a grey area. Kimball should decide before shipping.

## Where it would apply
- The A12x25 runs at **Re ≈ 1.5–3.5e4** at 2000 rpm. The fan BEM never reaches the vendored tables (they start at 4e4), so every element uses the analytic polar.
- Using these formulas here means extrapolating 2–4× below the bottom of their Re range.
- They only cover `section_family: plate`. That is **Stock**. Every optimizer and screen design uses NACA sections, so it would change Stock and nothing else.

## Prototype
Code: `proto/bem_variants.py` (`polar="bv"` / `"bv_ps"`). Results: `proto/compare.py` → `compare.json`.

| case | base: free CFM / shut-off Pa / peak η | B&V plate | B&V + post-stall extension |
|---|---|---|---|
| Stock (7-station) | 58.2 / 38.9 / 0.536 | **51.1 / 40.1 / 0.498** | 50.8 / 38.9 / 0.491 |
| top 5 / S03681 (NACA) | 61.3–64.3 / 40.1–41.6 | unchanged | free unchanged, η −0.06 |
| paddle 89° | 62.5 / 38.9 / 0.549 | 81.6 / 40.1 | **95.8** / 38.3 |
| reversed −45° | 7.6 / 38.0 / 0.528 | 28.0 / 40.8 | **94.8** / 38.3 |
| 0 blades | none / 0.07 | unchanged | unchanged |

Against the references (datasheet 60.1 CFM / 22.9 Pa; CFD Stock v2 free 56.5): Stock free moves **away** from both (58.2 → 51.1), and shut-off moves away too (38.9 → 40.1).

## Re-ranking the 517 guarded designs from the screen
- Spearman ρ = 0.994 against the current ranking, and 25 of the top 30 stay.
- 423 designs now "beat Stock". That is an artefact: only Stock got the harsher plate polar.

## Key finding: why adding post-stall drag made the exploits worse
Adding Viterna-style post-stall drag made the paddle and reversed blades look *better*. In `fan_bem.py`, blade drag adds swirl, and swirl is credited as Euler work and so as pressure. The real QA-4 root cause is the **pressure accounting**, not the polar. See `axial-force-pressure-accounting.md`.

## Effort vs gain
- Effort: S.
- Gain: negative until both of these exist:
  - a plate polar that is valid at Re < 4e4 (e.g. NeuralFoil on a plate section, or our own measurements);
  - the pressure-accounting fix.
- Revisit then.
