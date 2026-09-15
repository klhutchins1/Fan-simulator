<!-- STALE — kept for archaeology. Live status is docs/roadmap.md (§12–§13) and
     docs/validation/keep_cut_board.md. Do not treat the items below as open work. -->

# Known Issues / TODO (ARCHIVED 2026-09-15)

User-reported cockpit issues from Aug 2026. **Items 1–4 were fixed 2026-08-27**; the Fan tab
now lives in `fansim/cockpit/fan_tab.py` (not `app.py`). Wrap sliders, async Preview, and feature
auto-counts are in tree. For current fidelity / ship blockers see **`docs/roadmap.md`**.

## STATUS: cockpit UX items 1–4 FIXED (2026-08-27)

- #1 Preview reflects editor changes (ranges + wrap DOF).
- #2 Feature activation auto-fills sensible counts when amplitude > 0.
- #3 Wrap (`lean`) sliders present.
- #4 Async preview + loading indicator.

Original symptom notes retained below for chat recovery only.

## 1. Cockpit: "Preview geometry" barely changes the 3D model
**(Fixed.)** Historical notes omitted — see git history / `CHAT_RECOVERY/` if needed.

## 2–4. Feature activation / wrap / async preview
**(Fixed.)** See STATUS above.

## Remaining work
Tracked in `docs/roadmap.md` (§12 math-application, §13 production readiness) and
`docs/validation/a12x25_pq_report.md` (P–Q honesty). Absolute free-air CFD is **not** +2%.
