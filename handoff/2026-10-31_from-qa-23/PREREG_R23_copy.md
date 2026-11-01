# QA round 23 pre-registration (grok, QA bot)

Written 2026-10-31 MDT, before any round-23 data. Brief: `handoff/2026-10-31_to-qa-23/CLAUDE_TO_QA.md` (repo-r23,
master 3b92eea = 3b92eea33e1e4b3d763a534057f14ad93919b4f6, fresh clone of `handoff_in/master_3b92eea.bundle`; the brief's
`fansim.bundle` is not on the box, Kimball named this bundle).

**Seen before writing this (context/spec only, no numbers):** the brief (it quotes lt120 CFD +8 % at 6.85 Pa, +26 % at
13.71 Pa; tip gap 1.0 mm +28.9 %, 1.5 mm −9.6 % INCONCLUSIVE); the header line of
`docs/qa/benchmarks/lt120/curve.csv` (`q_m3s,dp_pa,rpm,power_w,eta,pressure_type`), not its rows; the code of
`fansim/optimize/system_curve.py`; the roadmap item "Loaded-point fidelity near the knee"; the FAN-01 reference README
header (source, licence, design point). Not opened: curve.csv rows, the two lt120 audit files, `source.md`, FAN-01
characteristic/report, any Stock A12x25 curve or run numbers, the Tutar & Cam paper.

## A. Is 13.71 Pa on lt120's knee? (no CFD)

**Data:** the 5 measured points (Q, ΔP) of `curve.csv`, sorted by Q ascending; the CFD points (Q, ΔP) quoted in
`2026-10-18-lt120-validation-prereg.md` and `2026-10-30-lt120-tip-gap-prereg.md` (`runs` numbers), baseline gap and
each tip gap separately. Q in m³/s and CFM (1 m³/s = 2118.88 CFM).

**Segment slopes:** s_i = (ΔP_{i+1} − ΔP_i)/(Q_{i+1} − Q_i) for the 4 neighbouring pairs (Pa per m³/s; the stable
branch has s < 0). s_steep = the most negative s_i.
**Segment classes:** *steep* if s_i < 0 and |s_i| ≥ 0.5·|s_steep|; *flat* if s_i < 0 and |s_i| < 0.5·|s_steep|;
*rising* if s_i ≥ 0 (stall dip / unstable, ΔP falls as Q falls).
**Where the test point sits:** the 13.71 Pa point at the measured flow (if it is a measured point, its two adjacent
segments; if not, the segment containing it on the stable branch = both sides).
**Definitions (pre-registered):**
- **on the steep branch**: both adjacent segments are *steep*;
- **at the knee**: not "past", and at least one adjacent segment is *flat* or *rising* (the slope is flattening or turns
  next to the point), or the two adjacent classes differ;
- **past the knee**: the high-flow-side adjacent segment is already *flat* or *rising* **and** the low-flow-side segment
  is *rising* (the point is in or below the stall dip), or the point's Q is below the Q of the first *rising* segment's
  low end.
- Knee location estimate (report): the Q where the piecewise slope crosses 0.5·s_steep, linear in slope between segment
  mid-points.

**Uncertainty (only 5 points):** Monte Carlo, 5000 draws, each measured Q perturbed ±3 % and ΔP ±0.5 Pa (uniform,
independent; assumed, no published per-point uncertainty unless `source.md` states one, then that is used instead and
noted). Report the fraction of draws giving each verdict. **Verdict is "robust"** if one class has ≥ 80 %; otherwise
the verdict is reported as "X (not robust: Y % X / Z % W)". Also report-only: a monotone-cubic (PCHIP) interpolant's
derivative at 13.71 Pa and 6.85 Pa.

**CFD shape comparison (report-only + one rule):** the same segment slopes/classes on the CFD points (free → 6.85 →
13.71, baseline; and per tip gap where ≥ 2 loaded points). **"CFD shape agrees"** if the CFD's class at 13.71 Pa equals
the measured one; also report the ratio CFD slope / measured slope on the 6.85–13.71 Pa interval (1 = same steepness;
< 0.5 = CFD much flatter, i.e. flow very sensitive to ΔP there).

**Tutar & Cam 2025:** found via web; record citation, licence, whether their CFD reports this fan at/near 6.85 and
13.71 Pa (figure/table number), and their CFD vs measured flow there. "They matched 13.71 Pa" if their CFD flow is
within ±10 % of the measured flow at that pressure; "did not" if outside; "not reported" if no CFD value at/near it
(± 1 Pa); "not accessible" if the paper can't be read. Figures cited only; no NC/ND data copied into the repo.

## B. Draft "near the knee" warning (proposal only, no source edits, no CFD)

**Inputs allowed (what Assess already has):** free-air CFD (Q0, p_free), the loaded CFD probe at P (Q1, converged or
not), the 2-point fan line of `system_curve.py`, and the BEM `pq_curve` (shutoff_dp_pa, points) for the same params/rpm.

**Rule R23-KNEE (fixed now; flag = any component true):**
- **K1 (probe status):** the loaded probe did not converge / failed.
- **K2 (flow ratio):** φ = Q1/Q0 ≤ 0.60 (loaded probe at ≤ 60 % of free delivery, where axial-fan knees usually sit).
- **K3 (BEM pressure ratio, pre-CFD):** P ≥ 0.60 × BEM `shutoff_dp_pa` for the design at its rpm.
Each component is reported alone and the OR combined; thresholds are not tuned after seeing the cases (any
post-hoc alternative is labelled exploratory).

**Ground truth per case point** (CFD loaded point vs measured/published at the same pressure):
- **bad** = loaded CFD did not converge, or |CFD flow / measured flow − 1| > 15 %, or the audit records a bistable /
  state-jumping result at that point;
- **good** = converged and within ±10 %;
- **grey** = 10–15 % (not scored; reported).
Cases: A12x25 Stock 5, 10, 15, 20 Pa (the brief: 5/10 held, 15/20 did not converge; numbers from the repo's Stock
audits); lt120 6.85 and 13.71 Pa (baseline gap); FAN-01 loaded point(s) from its report. A case with no measured
reference or no recorded CFD result is **unlabelled** (flag reported, not scored). Component inputs that don't exist
(e.g. Q1 of an unconverged probe for K2) are "n/a", and that component is false.

**Scoring:** **hit** = flagged and bad; **miss** = not flagged and bad; **false flag** = flagged and good; **clear**
= not flagged and good. Report counts for K1, K2, K3 and the OR. **False-flag risk** (report): the false-flag count on
the scored good points, plus the share of each fan's measured/published stable branch (Q from the knee estimate to
free delivery) whose points K2/K3 would flag.
**Proposal "worth landing"** if the OR rule has 0 misses and ≤ 1 false flag on the scored points; otherwise "needs
more data", with what would decide it.

## C. Waiting (R3.1 export leak check; r21 A re-run when R1.10 lands). Not run.

Timing with `time.monotonic`; logs trimmed (tail/grep). No CFD/Docker/OpenFOAM/Assess/Sweep; nothing committed to
repo-r23; no fansim source edits; nothing on Kimball's PC.
