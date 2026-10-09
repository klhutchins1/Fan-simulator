# Round 4, request 1: Claude's `axial_force` vs the QA implementation, and the exploit-guard break test

Pre-registration: `docs/qa/notes/r4-prereg-axial-crosscheck-eff-audit.md`, sha256 `1252f73ff4655137290a7eab8d30a181034cb1fe5ef7dadd46e5e09dccc4acaf`.
It was committed in the QA clone (branch `prereg/round4`, `e4db298b`, 2026-10-09 15:32 MDT) before any run.

The two sides compared:
- Claude = `5396796` (worktree `research/r4_axial`).
- QA = `e48a32d` plus the QA axial patch (`research/repo_research`).

Both were run single-core at nice 19.

## 1a. Cross-check: **EQUIVALENT** (pre-registered rule met with zero margin used)
- **Inputs:** all 6,596 screen-r3 designs (screen settings: 2000 rpm, leftover tip gap, "case" 8 Pa hose, max_camber ≤ 0.10), plus Stock (7-station YAML), paddle 89°,
  reversed −45° and −60°, and 0 blades.

| quantity | max abs diff | median | designs differing |
|---|---|---|---|
| free CFM | 0 | 0 | 0 / 6,596 |
| shut-off Pa | 0 | 0 | 0 / 6,596 |
| peak η | 0 | 0 | 0 / 6,596 |
| screen score (6,171 with objectives) | 0 (< 1e-12) | 0 | 0 |

- **Ranking:** Spearman ρ of the score is 1.000.
- **Disagreements:** 0 guard-verdict disagreements and 0 feasibility (first_fail) disagreements.
- **Precision note:** free CFM, shut-off and peak η are compared at `pq_curve`'s reported precision. The score is a float and also agrees exactly. So the two are numerically identical, not merely close. The base commit (e48a32d vs f238f54) makes no difference to the BEM.
- **Specials** (identical on both): see the table below. Claude's guard text for each is quoted in the last column.

| case | free CFM | shut-off Pa | peak η | guard |
|---|---|---|---|---|
| Stock | 59.8 | 22.08 | 47.4 % | PASS |
| paddle 89° | 14.0 | 0.84 | 0.9 % | REFUSE "churn air" |
| reversed −45° | no rise | | | REFUSE "no pressure" |
| reversed −60° | no rise | | | REFUSE "no pressure" |
| 0 blades | | | | REFUSE "no pressure" |

- **Guard on the screen:** it refuses **0 of 6,596** screen designs. The lowest peak η on the screen is 7.9 % (S00334), a 2.9 pp margin.
- **Guard call is consistent:** Claude's real `bem_exploit_reason(...)` and the rule applied to the recorded curve agree on 6,596 / 6,596.

## 1b. Break test (`handoff/2026-10-09_from-qa-3/scripts/guard_break.py`, 1,822 designs)
Design sets:
- **Editor ranges** (1,752 designs): a grid over blades × stagger × chord × camber, 72 twist shapes, and 1,500 uniform-random designs within the cockpit
  slider ranges.
- **File-loadable** (70 designs): partial paddles (75°/89° on 1–7 stations), wrong-hand stations (−20°/−45°), 1–3 blades, chord ×0.1–0.5,
  uniform stagger 60–89°.

### Pre-registered result, and why it's not usable
- As registered: **0 false refusals**, but "1,646 slip-throughs in editor ranges".
- The second number is an artefact of my **J1** criterion: "≥ 50 % of span past stall" at inlet incidence. J1 flags **Stock itself**
  (stall fraction 0.7) and 1,712 / 1,822 designs (editor median 0.9). Inlet incidence without swirl relief is simply high on real fans.
- J1 was a bad junk criterion, so I don't count those as real slips. The other criteria (J2 turbine span, J3 paddle/reversed span) still work. Everything
  below is analysis I added after seeing the results.

### Real findings
1. **No false refusals.**
   - Every editor-range design passes. The closest call is 5 blades, 55° stagger, 14 mm chord: peak η 7.3 %. Euler and axial agree on free CFM there (35.6 / 34.9), so it is a weak but real fan.
   - Outside the editor, the guard refuses Stock with chords ×0.1 (peak η 4.7 %, Euler free 20.6) and 2 blades × 0.1–0.2 chord. Those are near-junk, which is defensible.
2. **Exploits the guard lets through (file-loadable only; none possible with editor sliders):**
   - **A whole paddle at 80° passes**: peak η 8.9 %, axial free 44.6, Euler 62.5. Only 89° is refused.
   - **4 of 7 outer stations at 89° pass** (peak η 7.3 %, axial free 36.8 vs Euler 61.8), and so does `inner6_89` (7.3 %).
   - A wrong-hand inner half (4 stations at −20°, 65 % of span at negative incidence) passes at 10.9 %.
   - 1, 2 and 3 blades pass (peak η 14.8 / 22.2 / 27.4 %). The model treats them as weak fans, which is fair.
   - **Plain reading:** the 5 % bar only catches *fully* paddle-like or wrong-hand blades. A blade that is half paddle still clears it,
     though the axial model already cuts its claimed airflow by about 40 % compared with Euler.
   - **Cheap tightening idea (not tested against CFD):** also refuse when Euler free > 1.3 × axial free. Every editor design is ≤ 1.26. For the slips above the ratio is
     1.40 (80° paddle), 1.68 (outer-4 paddle) and 1.58 (wrong-hand inner 4).
3. **A different problem: the axial model can claim more than 100 % efficiency** (this is not a guard failure).
   - In editor ranges, peak η > 100 % for 6 / 1,752 designs (max **115 %**), > 90 % for 26 and > 70 % for 124. Euler never exceeds 51 % on any of them.
   - All the extreme ones are 11-blade, high-solidity designs (mid-span solidity 2.0–2.4).
   - The cause: the axial force is summed blade by blade, with no correction for blades crowding each other (cascade/solidity effects) and no link to the shaft work, so the "pressure" can exceed what the shaft supplies. It breaks energy conservation.
   - On the screen-r3 set the max peak η is 62.7 % (7 designs > 60 %). The r3 top 5 have peak η 44–57 % and are 10–11 blades with max chord. **This is likely
     part of why axial mode favours them**, which matches the round-3 caveat. The screen-r3 CFD should show it.
   - The guard only checks the low end, so it can't catch this. It doesn't matter while axial mode is "guard only, never rank", but it
     **must be fixed before axial mode ranks anything**. The obvious bound is static rise ≤ Euler total rise, or air power ≤ shaft power.
     Not implemented; this needs a new pre-registration.

## Verdict (plain language)
- Claude's re-implementation is **exactly** the QA model: same numbers on every design.
- The guard is **safe in normal use**:
  - nothing real is refused;
  - editor sliders can't make a paddle or a wrong-hand blade;
  - every fully paddled or wrong-hand case is refused.
- It **can be fooled by hand-edited files** with partly paddled or partly wrong-hand blades.
- Separately, the axial model's efficiency is **not physically bounded**, so don't use it to rank efficiency.
