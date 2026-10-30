# r21 A: release claims audit (README, cockpit copy, export README, user docs)

QA bot, 2026-10-25. Master **5063a65**. Prereg **956b8ff** (`prereg_r6`, `prereg/round21`, `qa_r21/PREREG_R21.md` §A,
committed before any data). Data: `handoff/2026-10-25_from-qa-21/data/r21-A-claims.csv`. Script:
`handoff/2026-10-25_from-qa-21/scripts/a_claims.py`. Read-only; no source edits.

**Scope (as pre-registered):**
- `README.md`;
- cockpit copy: `fansim/cockpit/*copy*.py`, plus the tab, help, results and caption strings in the cockpit `.py` files,
  and `fansim/cfd/flow_verdicts.py`, which feeds the flow card;
- the export README (`print_readme`, `fansim/manufacturability/print_export.py:356`);
- `docs/*.md` plus the docs pages linked from the README.

Out of scope: `docs/qa`, `docs/validation/audits`, `docs/release`, `docs/plans`, `docs/superpowers`, `roadmap.md`, and
handoff/archive pages. The `blade_copy`, `mixed_copy`, `volute_copy` and `prop_copy` files hold descriptions only, with no
performance claims.

## Verdict: **A FAILS** (gate: 0 overstated and 0 unsupported)

60 claims: **20 supported as worded · 20 need a label · 15 overstated · 5 unsupported.**

### Worst overstatements (by user impact)

1. **`fan_assess.py:409-411` "vs stock free 60 CFM: +X % (better / lower free-air)"** after every Assess.
   - It compares the *scored* screening result (derated, ×0.95 print knockdown, GCI ≈ 21 %) with the Noctua
     **datasheet** value (60.1) and calls that "stock".
   - Assessing Stock itself prints about −17 % "lower free-air" (49.6 vs 60).
   - This is the opposite of R1.4's "compared with this Stock, like for like". → QA-56.
2. **Noise ranking presented as usable**:
   - README:59 "tone + relative ranking are usable";
   - the flow card noise row (`flow_verdicts.py:156-162`) gives ✓/⚠ "About x dB quieter than Stock … (ranking only)",
     although R0.4 ruled the hint only restates CFM;
   - `fan_flow_report.py:30`, `fan_tab_ui.py:1108` and `a12x25-reference.md:57`.
   - Audit-06 is validation INCONCLUSIVE: "Nothing here shows the absolute dB(A) or the ranking is right". → QA-55.
3. **"Honest MRF CFD"** for Volute (`volute_tab.py:164, 691`) and Mixed (`mixed_tab.py:765`).
   - Volute CFD oscillates 17–23 % (audit-07:112). Mixed has no published comparison.
   - Mixed is labelled "estimate", not "Experimental: not validated against published data" (R2.4, Kimball
     2026-10-17). → QA-57.
4. **`a12x25-reference.md:24` "validated on Stock: 59.8 vs 60.1 CFM"**: 59.8 is the close-ref STL. Stock (v3) is 55.7 vs
   58.3. On the same page, :30 says "every gap … has since been closed", but near-stall is unconverged and the Stock
   gap is open. → QA-58.
5. **"~3–5 % discretization"** (`design-rules.md:43`, `adversarial-review.md:237-239`, which the README links as "what is
   validated vs. not") against GCI_fine ≈ 21 % on the screening mesh. → QA-58.
6. **README:66 "The one real gap: nothing printed"**: also open are prop CFD (−44 % FAIL), volute convergence, mixed/CROR
   (direction only) and noise validation. → QA-58.

### Unsupported (5)

- README:136-137: port 9001 and "several minutes". This is QA-53, still open at 5063a65.
- `fan_copy.py:129` "under-ranks CFD (~0.6×)": audit-04:80 calls it stale.
- `fan_tab_ui.py:493` "Assess runs one CFD solve (~15–30 min)": it is two solves, and the time is 21–40 min.
- `figures.py:399` "CFD under-predicts static ~2×": v5 is −9 % to −13 % at shut-off.
- `design-rules.md:39-40` "more blades … raise airflow": its own table gives ρ −0.35.

All five are in QA-58, except A17, which is QA-53.

### Needs a label (20): the release labels that the board has decided but not landed

| label | claims | board item |
|---|---|---|
| Stock gap ("about 5 % less airflow than the real A12x25 shape …") | A08 README:52, C19 `fan_trials.py:354` (and no README "Known limits" list exists) | R1.4 |
| structural / flutter "estimate, not validated" (and it is a resonance gate, not aeroelastic flutter) | A13, A14, C07, C08, C12 | R1.5 |
| no bare "dB(A)/dBA" without "relative" | A01, A04, C14 (design list "dBA"), E01 (`noise_swl` in the finalist print sheet) | R1.6 |
| Mixed "Experimental" in tab, results, README feature list, export README | C06, C21, C23 (volute "ranking only" with an unvalidated proxy) | R2.4 / R2.5 |
| prop BEMT "±15 % at static; worse toward zero-thrust J"; CFD "~35–45 % low" is static only (−58 % at J 0.43) | C26, C27 | R2.1 / R2.2b |
| BEM pre-screen "coarse; cannot separate close designs" | A12 | audit-04, bem-screen-top5 |
| print knockdown 0.95 is assumed, not measured | C04 | (none yet) |
| export "Predicted performance (sim)": screening mesh, ranking only, vs this Stock | E01 | R1.4 / R3.8 |
| historical banners: adversarial-review, pq_report's superseded "+22–29 %" | D08, D09 | R3.8 |

**Gaps (not counted as claims):**
- The README has no feature-list entry or label for Mixed / Volute / Prop / CROR, yet the cockpit ships them (Expert
  tabs). R2.4 wants the Mixed label in the README feature list.
- No user-facing doc states the lt120 / FAN-01 rig limits.

**Supported as worded (20):** the A12x25 close-ref and FAN-01 numbers (all recomputed within printed rounding), the
Assess screening caveat, the score worked example (recomputed), the datasheet markers, the prop "ranking estimate" and
"not calibrated dBA" strings, CROR "estimate / relative noise", the wind-turbine scaffold, and the export disclaimers.

## Full table

| id | file:line | wording (exact excerpt) | evidence | verdict |
|---|---|---|---|---|
| A01 | `README.md:4-5` | runs **real CFD** (OpenFOAM MRF) to measure airflow … scores **noise** on the GPU | audit-06 (`2026-09-29-audit-06-acoustics.md`) validation INCONCLUSIVE; R1.6 | **needs a label** |
| A02 | `README.md:12` | Read docs/adversarial-review.md — it documents what is validated vs. not. | adversarial-review.md:23-25 still says the core is "unvalidated against any ground truth"; :237-239 "~3–5 %" vs GCI_fine ≈ 21 % (`2026-10-07-assess-speed.md:89`) | **overstated** |
| A03 | `README.md:18-21` | A design the CFD measured at 54.8 CFM shows 49.6. | how-scores-are-computed.md:73; recomputed 54.79×0.954×0.95×0.9993 = 49.62 | **supported as worded** |
| A04 | `README.md:32` | BPF tone + relative dB(A) ranking | audit-06: "Nothing here shows the absolute dB(A) or the ranking is right"; R0.4 ruling | **needs a label** |
| A05 | `README.md:48` | free-air **59.8 CFM vs published 60.1 (−0.5%)** | audit-02 (`2026-09-28-audit-02-cfd-method-validation.md`); a12x25_pq_report.md v5 table; recomputed −0.50 % | **supported as worded** |
| A06 | `README.md:48-50` | 5 / 10 Pa converged (52.5 / 41.0 CFM); shut-off ≈ 20–21 Pa vs published 22.9 Pa, but the near-stall points do not converge | a12x25_pq_report.md v5 table (15 Pa osc 16 %, 20 Pa osc 41 %) | **supported as worded** |
| A07 | `README.md:51` | External benchmark FAN-01 (exact published CAD): within **+2.6% / +3.1%**. | docs/validation/fan01/fan01_report.md:23-24; recomputed 2.131/2.078 = +2.55 %, 1.859/1.804 = +3.05 % | **supported as worded** |
| A08 | `README.md:52-53` | Parametric Stock recipe v2: 56.5 / 49.8 / 40.2 CFM … (−5.5% vs the close-ref STL) | true for v2 (pq_report), but shipping Stock is v3: 55.7 vs 58.3 (−4.5 %), `2026-10-12-cylinder-sections.md:222,252`; R1.4 wording absent | **needs a label** |
| A09 | `README.md:55-56` | faster screening mesh (… GCI ≈ 21%): use it to **rank** designs, not as absolute CFM | `2026-10-07-assess-speed.md:89`; score mesh-robust ±1 % `2026-10-15-stock-flow-mesh-repeats-prereg.md:64` | **supported as worded** |
| A10 | `README.md:59` | absolute broadband dB(A) is coarse-grid-limited (tone + relative ranking are usable) | audit-06 validation INCONCLUSIVE; `flow_verdicts.py:30-31` NOISE_JUDGED False, Stock SWL moved 36 dB across meshes; R0.4 | **overstated** |
| A11 | `README.md:60` | Bio-feature benefit tested **null at achievable fidelity** — only a physical print settles it. | roadmap.md:100, 2041 (no audit file; hedged negative claim) | **supported as worded** |
| A12 | `README.md:61` | BEM is **ranking-only**, not absolute CFM. | audit-04 ρ 0.714 on 7 designs, "fragile"; `2026-10-09-bem-screen-top5.md`: "within the five, BEM order carries no information" | **needs a label** |
| A13 | `README.md:62` | Blade vibration (flutter) is a **warning**, not a reject, until printed blades confirm the beam model. | audit-05: resonance gate, verification only; beam out of regime (aspect < 1.5, Stock tip ≈ 0.98); R1.5 label "estimate, not validated" missing | **needs a label** |
| A14 | `README.md:27` | manufacturability + structural + fan-envelope + convergence gating | audit-05 verification only; R1.5 | **needs a label** |
| A15 | `README.md:63-64` | **Scaffolds, not validated:** the wind-turbine archetype | R2.6 | **supported as worded** |
| A16 | `README.md:66` | **The one real gap:** nothing has been physically **printed and measured** yet. | other open gaps: prop CFD FAIL −44 % (`2026-10-02-audit-08-prop-cfd.md:46`); volute CFD 17–23 % oscillation (`2026-10-01-audit-07-cror-mixed-setup.md:112`); mixed/CROR direction proof only (audit-07); noise unvalidated (audit-06); Stock −4.5 % | **overstated** |
| A17 | `README.md:136-137` | usually `http://localhost:9001` … takes several minutes | cockpit prints 127.0.0.1:8080; Assess 30–40 min in code, 21–24 min in assess-speed audit (QA-53, r20 D) | **unsupported** |
| C01 | `fansim/cockpit/fan_copy.py:125` | do not expect proven dB cuts. | audit-06 | **supported as worded** |
| C02 | `fansim/cockpit/fan_copy.py:128-129` | BEM … Not absolute CFM … typically under-ranks CFD (~0.6×). | audit-04:80: the "~0.6x" docstring is **stale** (BEM +2.7 % v2, −20 % v1, +11 % opt) | **unsupported** |
| C03 | `fansim/cockpit/fan_copy.py:162-163` | more honest load CFM … Risk: still RANS, not a lab measurement. | how-scores-are-computed.md §2 (two-point fan line) | **supported as worded** |
| C04 | `fansim/cockpit/fan_copy.py:167` | When to use: printed-part honesty. | print_k_cfm 0.95 is an assumed factor (`how-scores-are-computed.md:60-68`, `print_penalty.py`); nothing printed or measured | **needs a label** |
| C05 | `fansim/cockpit/fan_tab_ui.py:493` | Assess runs one CFD solve (~15–30 min) | how-scores §1–2: a free-air solve plus a probe point (two solves); 21–24 min (assess-speed); 30–40 min elsewhere in code (r20 D) | **unsupported** |
| C06 | `fansim/cockpit/fan_tab_ui.py:495-496` | Fan is CFD-checked — Mixed / Volute / Prop / CROR tabs are faster estimates or proxies. | Fan: audit-02 + FAN-01 (supported); but Mixed must read "Experimental: not validated against published data" (R2.4), and Mixed/Volute also offer MRF Assess | **needs a label** |
| C07 | `fansim/cockpit/fan_tab_ui.py:889` | Assess checks printability / stress (blade vibration is a warning) | audit-05 verification only; R1.5 | **needs a label** |
| C08 | `fansim/cockpit/fan_tab_ui.py:911` | Print material (stress gate + vibration warning) | audit-05; R1.5 | **needs a label** |
| C09 | `fansim/cockpit/fan_tab_ui.py:150` | Gold ✕ = datasheet free-air CFM with load CFM estimated from the published P–Q line (not OEM CFD) | fan_spec.py:92-96, 270 | **supported as worded** |
| C10 | `fansim/cockpit/fan_tab_ui.py:1108` | Noise ranking: use scripts/evaluate_noise.py (mic cal needed for absolute dB). | implies the relative ranking is usable; audit-06 INCONCLUSIVE | **overstated** |
| C11 | `fansim/cockpit/figures.py:335-336` | noise {noise:.1f} dB(A) (Stock datasheet marker) | Noctua published 22.6 dB(A), fan_spec.py:270; it is a datasheet value, shown on the published marker | **supported as worded** |
| C12 | `fansim/cockpit/figures.py:394` | (Not a full FEA — just a cheap safety gate.) | audit-05: resonance gate verified, not validated; "safety" reads as validated; R1.5 | **needs a label** |
| C13 | `fansim/cockpit/figures.py:399` | CFD also under-predicts static ~2× | v5 shut-off 20–21 vs 22.9 Pa (−9…−13 %), automated proxy 28.0 Pa (pq_report v5); no audit gives ~2× | **unsupported** |
| C14 | `fansim/cockpit/data.py:205` | ("swl_dba", "dBA") design-list column | Proudman SWL is a relative proxy (audit-06; fan_flow_report.py:29 says "relative; mesh-dependent, don't compare"); R1.6 grep rule | **needs a label** |
| C15 | `fansim/cockpit/fan_assess.py:409-411` | vs stock free 60 CFM: +X% (better/lower free-air) | compares the *scored* screening Assess (derated, ×0.95 knockdown, GCI ≈ 21 %) with the Noctua **datasheet** 60.1 (fan_spec.py:270), and calls it "stock". Stock's own Assess reads ≈ 49.6 → "−17 % lower" (how-scores:73). Not like for like (R1.4) | **overstated** |
| C16 | `fansim/cfd/flow_verdicts.py:156-162` | About {x} dB quieter/louder than Stock from tip speed and airflow (ranking only, not a microphone reading). | R0.4 ruling: the hint differs only through CFM, so "louder" restates "moves more air"; the row must not be ✓/⚠/better (status ready, not landed) | **overstated** |
| C17 | `fansim/cockpit/fan_flow_report.py:30` | tip-speed + airflow ranking (dB-ish, 27.3c) | R0.4 (as C16) | **overstated** |
| C18 | `fansim/cockpit/fan_flow_report.py:29` | Proudman SWL (dB, relative; mesh-dependent, don't compare) | flow_verdicts.py:31 (36 dB mesh spread) | **supported as worded** |
| C19 | `fansim/cockpit/fan_trials.py:354` | Stock reference loaded — geometry is a parametric stand-in for the real fan. | R1.4: must carry "about 5 % less airflow than the real A12x25 shape (55.7 vs 58.3 CFM …)" | **needs a label** |
| C20 | `fansim/cockpit/fan_models.py:33` | Published {cfm} CFM / {pa} Pa / {dba} dBA. | fan_spec.py:270 datasheet | **supported as worded** |
| C21 | `fansim/cockpit/app.py:187,191` | Mixed-flow — drop-in impeller (rough estimate, not full Fan CFD) / "Mixed · estimate" | R2.4 (Kimball 2026-10-17): must say "Experimental: not validated against published data"; audit-07 direction only | **needs a label** |
| C22 | `fansim/cockpit/mixed_tab.py:765` | Assess still scores the honest MRF duct. | no published comparison (R2.4, grok r15); audit-07 fixed setup/direction only | **overstated** |
| C23 | `fansim/cockpit/app.py:199` | Volute — radial blower (rough estimate, ranking only) | R2.5: ±20 % proxy, ranking unvalidated | **needs a label** |
| C24 | `fansim/cockpit/volute_tab.py:164` | ranking only; Assess for honest CFD. | volute CFD oscillates 17–23 % (audit-07:112); R2.5a not done | **overstated** |
| C25 | `fansim/cockpit/volute_tab.py:691` | Assess for honest radial MRF CFD. | as C24 | **overstated** |
| C26 | `fansim/cockpit/prop_tab.py:766,964,1216` | CFD thrust/power read ~35-45 % low on small props (Audit #8) | audit-08:46 C_T −44 %, C_P −40 % static (layers variant −41 / −34 %). Static only: R2.2b B2 −40 / −45 / −58 % at J 0.20 / 0.30 / 0.43 | **needs a label** |
| C27 | `fansim/cockpit/prop_tab.py:766,964,1216` | … rank and print from the BEMT numbers | BEMT C_T −12.8 % PASS static, −15/−20/−29 % with J; SF static C_P −21.3 % FAIL (`2026-09-29-audit-03-prop-bemt-uiuc.md:154`); R2.1 wording "±15 % at static; worse toward zero-thrust J" missing | **needs a label** |
| C28 | `fansim/cockpit/prop_tab.py:101` | BEMT is a ranking estimate, not a measurement | audit-03 | **supported as worded** |
| C29 | `fansim/cockpit/prop_tab.py:469` | relative rank, not calibrated dBA | audit-06 | **supported as worded** |
| C30 | `fansim/cockpit/cror_tab.py:97,593` | Relative noise only. / Optimize is BEMT-proxy NSGA (not dual-MRF). | audit-07 direction only; disclosed | **supported as worded** |
| C31 | `fansim/cockpit/app.py:218` | CROR — stacked rotors (fast estimate, not full CFD) | audit-07 direction only | **supported as worded** |
| E01 | `fansim/manufacturability/print_export.py:373-374 (via scripts/export_finalists.py:36,112)` | **Predicted performance (sim):** cfm_free …, cfm_load …, efficiency …, noise_swl … | bare numbers: no "screening mesh / ranking only" (assess-speed GCI 21 %), no Stock-gap note (R1.4), noise_swl unlabeled (R1.6) | **needs a label** |
| E02 | `fansim/manufacturability/print_export.py:429-430` | printed blades are a relative-comparison baseline, not a Noctua replacement | nothing printed yet; honest | **supported as worded** |
| E03 | `fansim/manufacturability/print_export.py:398` | This number is a guess. | bore placeholder; honest | **supported as worded** |
| D01 | `docs/a12x25-reference.md:24` | the CFD v5 setup … is validated on Stock: 59.8 vs 60.1 CFM | 59.8 is the **close-ref STL**, not Stock (pq_report v5 table); Stock v3 is 55.7 vs 58.3 (cylinder-sections:252) | **overstated** |
| D02 | `docs/a12x25-reference.md:30` | Every gap below has since been closed by the validated CFD v5 setup | near-stall 15/20 Pa unconverged (pq_report); Stock recipe −4.5 % open (R1.4) | **overstated** |
| D03 | `docs/a12x25-reference.md:57` | Today it ranks designs relatively; it is not yet calibrated to absolute dB(A). | audit-06: ranking not shown; R0.4 | **overstated** |
| D04 | `docs/design-rules.md:43` | CFD is screening fidelity (~3–5% discretization); absolute noise … only the ranking is used | assess-speed:89 GCI_fine ≈ 21 %; audit-06 | **overstated** |
| D05 | `docs/design-rules.md:39-40` | more blades (higher solidity) raise loading (\|thrust\|) and airflow | own table, design-rules.md:18: n_blades vs cfm_free ρ −0.35, cfm_load −0.35 (n = 14) | **unsupported** |
| D06 | `docs/how-scores-are-computed.md:30,73-74` | λ = 0.954 → 1907 rpm; free = 49.6, load 40.7 | recomputed: (0.672/0.775)^(1/3) = 0.9536; 2000×0.9536 = 1907; 49.62 | **supported as worded** |
| D07 | `docs/adversarial-review.md:237-239` | ~3–5% quantified discretization error … relative rankings are fine at the coarse mesh | GCI_fine ≈ 21 % (assess-speed:89); design-difference spread ~4 % vs ±1 % score spread (2026-10-15/16 repeats) | **overstated** |
| D08 | `docs/adversarial-review.md:23-25` | the core is currently **unvalidated against any ground truth.** | superseded by audit-02 / FAN-01; page needs a "historical" banner | **needs a label** |
| D09 | `docs/validation/a12x25_pq_report.md:41-42` | The Stock parametric recipe still over-delivers (+22–29% free air) | superseded within the same page (v2 −5.5 %) and by v3 −4.5 %; needs a "superseded" label | **needs a label** |
