from pathlib import Path

p = Path("docs/roadmap.md")
t = p.read_text(encoding="utf-8")
if t.startswith("\ufeff"):
    t = t[1:]

start = t.find("## 11. Re-review leftovers")
end = t.find("**Do NOT** re-optimize tip-round", start)
assert start > 0 and end > start, (start, end)

new_block = """## 11. Re-review leftovers (2026-09-11)

Fresh pass after section 9/10. Fast pytest was **708 passed** before section 11 fixes.
Interpreter may still exit with Windows heap corruption (`0xC0000374`) —
OCCT/CadQuery shutdown, not a failed assertion.

- [x] **11.7 Math/science re-review (afternoon). DONE 2026-09-11.** **[impact: high]** **[effort: n/a]**
  No new wrong-equation must-fixes. Physics pytest 85 passed. BEMT swirl in code is
  propeller sign `Vt = Omega r (1-a')` (QProp / ETC2025-161). Keep simpleFoam +
  kOmegaSST + MRF (Ma << 0.3) and rhoSimpleFoam for props. Do not switch to DNS.
- [x] **11.1 Volute screening honesty parity. DONE 2026-09-11.** **[impact: high]** **[effort: low]**
  Stamps `SCREENING_GRID_STAMP` on volute evaluate. Does **not** call
  `require_circular_inlet_area` (sealed scroll, not tube-in-hex).
- [x] **11.2 Wire propeller into the Archetype registry. DONE 2026-09-11.** **[impact: med]** **[effort: med]**
  `PropellerArchetype` registered; wind_turbine remains the loud stub.
  `catalog.classify_entry` imports `fansim.fit` (not `cockpit.placement`).
- [x] **11.3 Cockpit starts without a feasible Optuna run. DONE 2026-09-11.** **[impact: med]** **[effort: med]**
  `load_study_designs` returns [] on empty/missing study; no `SystemExit`.
  Fan tab size is unchanged (further split is follow-up).
- [x] **11.4 Hide parked LE/TE thickness sliders. DONE 2026-09-11.** **[impact: med]** **[effort: low]**
  Sliders removed from Design UI; NACA caption points at Rounded plate for bullnose.
  State keys still load/save for old rows.
- [x] **11.5 CROR/prop Optimize: no `(0, 0)` gated trials. DONE 2026-09-11.** **[impact: med]** **[effort: low]**
  Depth overflow and over-power raise `TrialPruned` with `feasible=False`.
- [x] **11.6 Repair docs/roadmap.md encoding. DONE 2026-09-11.** **[impact: low]** **[effort: low]**
  Section 11 rewritten in clean UTF-8; full-file mojibake scrub deferred when tools
  mis-display valid em dashes / section marks.
- Hardware print + measure: **section 5** — staged; see `docs/validation/north-star-staged.md`
  (blocked on commercial hub; recorder ready).

"""

t = t[:start] + new_block + t[end:]

# Recommended sequence: mark 11 closed (match both ASCII and section-sign forms)
for old, new in (
    (
        "Open work is §11, then hardware §5.",
        "Section 11 closed; next is hardware section 5.",
    ),
    (
        "Open work is \u00a711, then hardware \u00a75.",
        "Section 11 closed; next is hardware section 5.",
    ),
):
    t = t.replace(old, new)

# Staged note under 5.1
sec5 = t.find("## 5.")
sec6 = t.find("## 6.", sec5)
if sec5 > 0 and sec6 > sec5 and "north-star-staged" not in t[sec5:sec6]:
    needle = "One measurement changes"
    idx = t.find(needle, sec5, sec6)
    if idx > 0:
        nl = t.find("\n", idx)
        insert = (
            "\n  **Staged 2026-09-11** (no commercial hub on hand): "
            "`docs/validation/north-star-staged.md`."
        )
        t = t[:nl] + insert + t[nl:]

# Drop obsolete uncommitted note if still present above section 11
t = t.replace(
    "Working tree still has the §9.6–9.11 / §10 eval+persist patch uncommitted\n"
    "(~794 lines). Commit that before treating it as pushed.\n\n",
    "",
)

p.write_text(t, encoding="utf-8", newline="\n")
print("patched", start, end, "len", len(t))
