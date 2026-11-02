# QA r24 B: QA-64 wording check, no CFD (grok, 2026-11-01 MST)

**Setup**
- Prereg: **88c4e79**, section B. The rules and verdict are mechanical, fixed before the A12x25 and FAN-01 numbers were opened.
- Not blind: I wrote QA-64 in r23, so I had already seen the lt120 numbers.
- Script: `handoff/2026-11-01_from-qa-24/scripts/b_qa64_check.py`. It reads committed files only. Output: `data/b_qa64.json`.

**Claim tested:** "Fan CFD: validated near free air on three published fans (within 8 %)".
- `docs/validation/audits/2026-10-18-lt120-validation-prereg.md:89`
- `2026-10-30-lt120-tip-gap-prereg.md:69`

## The three numbers

| fan | point P | fan's max published P | P/Pmax | headline error | other numbers | source of the error |
|---|---|---|---|---|---|---|
| A12x25 | 0 Pa (free air) | 22.9 Pa (`docs/a12x25-reference.md:13`) | 0.00 | **−0.5 %** (59.8 vs 60.1 CFM) | −2.8 % without prism layers (58.4) | `docs/validation/a12x25_pq_report.md:27` (also :53, :54) |
| FAN-01 | 7 Pa | 252.8 Pa (`validation/reference/fan01/characteristic.csv`) | 0.028 | **+2.6 %** (2.131 vs 2.078 m³/s) | +3.1 % at 64 Pa (mid-curve, report-only) | `docs/validation/fan01/fan01_report.md:23` (:24) |
| lt120 | 6.85 Pa | 34.01 Pa (`docs/qa/benchmarks/lt120/curve.csv`) | **0.201** | **+8.1 %** (two-mesh mean, 84.0 meas vs 89.6 / 92.0) | 5.8 mm mesh +6.7 %, 6.2 mm mesh **+9.5 %**; tip-gap variants +6.6 / **+13.0** / +6.3 % at 0.5 / 1.0 / 1.5 mm (report-only) | `docs/validation/audits/2026-10-18-lt120-validation-prereg.md:69`; tip gap `2026-10-30-lt120-tip-gap-prereg.md:51-53` |

## Sub-checks (rules from 88c4e79)

- **(i) Published: pass for all three.**
  - A12x25: the Noctua datasheet.
  - FAN-01: Zenodo 10787093, CC-BY-4.0.
  - lt120: Lin & Tsai 2011, doi:10.1243/09544062JMES2231, cited via Tutar & Cam CC BY 4.0 (`source.md:6,8`).
- **(ii) Validated at that point: pass for all three.**
  - A12x25: "free air validated" (`a12x25_pq_report.md:36`).
  - FAN-01: "High-flow branch validated" (`fan01_report.md:32`).
  - lt120: the ±10 % rule passes at 6.85 Pa. The audit's overall verdict is TRENDS (`lt120-validation-prereg.md:74-75`).
- **(iii) Near free air (P = 0 or P/Pmax ≤ 0.10):**
  - A12x25: pass (0 Pa).
  - FAN-01: pass (0.028).
  - **lt120: fail (0.201).** 6.85 Pa is about one fifth of the way to shut-off, and lt120's dataset has no free-air point.
- **(iv) Within 8 % on the headline number:**
  - A12x25: pass (0.5).
  - FAN-01: pass (2.6).
  - **lt120: fail (+8.10 %, rounds to 8.1 > 8.0).** Report-only: the 6.2 mm mesh alone is +9.5 %.

## Verdict: **needs grok's proposed wording** (mechanical)

The claim as worded fails twice, both on lt120: (iii) near free air, and (iv) within 8 %.

The proposed wording holds:
- every headline and per-mesh error is within ±10 %: −0.5, −2.8, +2.6, +6.7, +8.1, +9.5;
- 6.85 Pa is lt120's lowest measured load (`curve.csv` minimum dp);
- A12x25 and FAN-01 both pass near free air.

**Suggested text:** "Fan CFD: matches published data within 10 % on three fans: near free air on two (A12x25, FAN-01), and on lt120 at its lowest measured load (6.85 Pa)."

**Caveats (report-only, not gated):**
1. The lt120 6.2 mm mesh at +9.5 % leaves only 0.5 points of margin.
2. The 1.0 mm tip-gap variant moved the 6.85 Pa point to +13.0 % (`tip-gap-prereg.md:52`). The ±10 % holds only for the frozen geometry (0.5 mm gap).
   - Recommend adding "(as built at the frozen 0.5 mm tip gap)" to the lt120 clause, or keeping the existing sentence that near the knee steady CFD is sensitive.
3. FAN-01 is a 495 mm industrial fan, not PC-size. "Three published fans" is still accurate.

**QA-64:** stays open until R1.10 lands the wording. Severity stays LOW.
