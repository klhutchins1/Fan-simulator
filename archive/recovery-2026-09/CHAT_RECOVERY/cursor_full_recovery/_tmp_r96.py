from pathlib import Path

p = Path("docs/roadmap.md")
t = p.read_text(encoding="utf-8")
old = (
    "- [ ] **9.6 Stamp BEM/GP prescreen exceptions; do not silently run CFD.** "
    "**[impact: high]** **[effort: low]**\n"
    "  `evaluate_candidate` and mixed-flow evaluate `except Exception: pass` on\n"
    "  screen crashes (`objectives.py` ~185, `centrifugal/evaluate.py` ~137).\n"
    "  Stamp `gap_raw` + log, or treat as infeasible."
)
new = (
    "- [x] **9.6 Stamp BEM/GP prescreen exceptions; do not silently run CFD. "
    "DONE 2026-09-11.** **[impact: high]** **[effort: low]**\n"
    "  BEM/GP screen crashes are infeasible with `bem_prescreen_error` / "
    "`surrogate_prescreen_error` stamped on `raw` (axial + mixed)."
)
if old not in t:
    # tolerant: mark checkbox only
    t2 = t.replace(
        "- [ ] **9.6 Stamp BEM/GP prescreen exceptions; do not silently run CFD.**",
        "- [x] **9.6 Stamp BEM/GP prescreen exceptions; do not silently run CFD. DONE 2026-09-11.**",
    )
else:
    t2 = t.replace(old, new)
p.write_text(t2, encoding="utf-8")
print("roadmap changed", t2 != t)
