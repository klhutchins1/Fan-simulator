from pathlib import Path
import re

t = Path("docs/roadmap.md").read_text(encoding="utf-8-sig")
# Actual remaining mojibake (UTF-8 interpreted as cp437/cp1252 then stored as Unicode)
fix = {
    "┬╖": "·",
    "├ù": "×",
    "ΓåÆ": "→",
    "ΓåÉ": "←",
    "Γê⌐": "∩",
    "ΓêÆ": "−",
    "Γëê": "≈",
    "╬ö": "Δ",
    "╧ü": "ρ",
    "╧Ç": "π",
    "╬╖": "η",
    "╬┤": "δ",
    "╬╝": "μ",
    "╧â": "σ",
    "╬╕": "θ",
    "╬ë": "Ω",
    "aΓÇ▓": "a′",
    "ΓÇ▓": "′",
}
for a, b in fix.items():
    t = t.replace(a, b)

# §11 block — replace from header through hardware line
start = t.find("## 11. Re-review leftovers")
end = t.find("**Do NOT** re-optimize tip-round", start)
assert start >= 0 and end > start, (start, end)
new_block = """## 11. Re-review leftovers (2026-09-11)

Fresh pass after §9/§10. Fast pytest was **708 passed** before §11 fixes.
Interpreter may still exit with Windows heap corruption (`0xC0000374`) —
OCCT/CadQuery shutdown, not a failed assertion.

- [x] **11.7 Math/science re-review (afternoon). DONE 2026-09-11.** **[impact: high]** **[effort: n/a]**
  No new wrong-equation must-fixes. Physics pytest 85 passed. BEMT swirl in code is
  propeller sign `Vt = Omega r (1−a′)` (QProp / ETC2025-161). Clay 2026-09-11: NS
  'apparently settled' but prize evaluation is unhurried; OpenAI claim is forced
  blow-up. That is not a new CFD solver. Keep simpleFoam + kOmegaSST + MRF
  (Ma << 0.3) and rhoSimpleFoam for props. Do not switch to DNS.
- [x] **11.1 Volute screening honesty parity. DONE 2026-09-11.** **[impact: high]** **[effort: low]**
  Stamps `SCREENING_GRID_STAMP` on volute evaluate. Does **not** call
  `require_circular_inlet_area` (sealed scroll, not tube-in-hex).
- [x] **11.2 Wire propeller into the Archetype registry. DONE 2026-09-11.** **[impact: med]** **[effort: med]**
  `PropellerArchetype` registered; wind_turbine remains the loud stub.
  `catalog.classify_entry` imports `fansim.fit` (not `cockpit.placement`).
- [x] **11.3 Cockpit starts without a feasible Optuna run. DONE 2026-09-11.** **[impact: med]** **[effort: med]**
  `load_study_designs` returns [] on empty/missing study; no `SystemExit`.
  Fan tab size is unchanged (further split is follow-up, not required to start blank).
- [x] **11.4 Hide parked LE/TE thickness sliders. DONE 2026-09-11.** **[impact: med]** **[effort: low]**
  Sliders removed from Design UI; NACA caption points at Rounded plate for bullnose.
  State keys still load/save for old rows.
- [x] **11.5 CROR/prop Optimize: no `(0, 0)` gated trials. DONE 2026-09-11.** **[impact: med]** **[effort: low]**
  Depth overflow and over-power raise `TrialPruned` with `feasible=False`.
- [x] **11.6 Repair `docs/roadmap.md` encoding. DONE 2026-09-11.** **[impact: low]** **[effort: low]**
  Re-saved as UTF-8 (section marks / dashes / Greek symbols).
- Hardware print + measure: **§5** — staged; see `docs/validation/north-star-staged.md`
  (blocked on commercial hub; recorder ready).

"""
t = t[:start] + new_block + t[end:]

# Header blurb
t = re.sub(
    r"- Last reviewed: \*\*2026-09-11\*\*.*?(?=\n\n- Tags:)",
    "- Last reviewed: **2026-09-11** (§11 leftovers closed. Suite was 708 passed "
    "pre-§11. Next: hardware §5 — staged runbook in "
    "`docs/validation/north-star-staged.md`.)",
    t,
    count=1,
    flags=re.S,
)

# §5 staged note
needle = '(only the CFD *engine* is, on the real STL). One measurement changes "hypothesis" → "result."'
if needle in t and "north-star-staged" not in t[t.find("## 5.") : t.find("## 6.")]:
    t = t.replace(
        needle,
        needle
        + "\n  **Staged 2026-09-11** (no commercial hub on hand): "
        "`docs/validation/north-star-staged.md`.",
        1,
    )

# Recommended sequence line
t = t.replace(
    "0. **Suite is green (708 passed, 2026-09-11 re-review).** Open work is §11, then hardware §5.",
    "0. **Suite is green (708 passed, 2026-09-11 re-review).** §11 closed; next is hardware §5.",
)
t = t.replace(
    "4. **§11 leftovers, then hardware §5.** Do not skip print-and-measure for more UI.",
    "4. **Hardware §5** (staged). Do not skip print-and-measure for more UI.",
)

Path("docs/roadmap.md").write_text(t, encoding="utf-8", newline="\n")
left = sorted({c for c in t if "┬" in c or "Γ" == c or "╧" == c or "╬" == c})
Path("scripts/_enc_check.txt").write_text(
    f"len={len(t)} leftover_markers={left!r}\n", encoding="utf-8"
)
