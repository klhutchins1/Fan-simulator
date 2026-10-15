# Duplicate information after one Preview (round 13 Task B): report only

Prereg `02584e6`. Cold open, then one real Preview of Stock (8 s, `preview_busy` cleared). Visible text was captured in Simple and Expert, for
both Design and Results (`data/b_dup.json`, `screens/b_*.png`). No Assess was run. **Cached Assess:** none on disk. The run clones and
repo-r13 have no `runs/`. The only `cockpit_assess` dirs are `research/screen_r3/cockpit_import/…` BEM-screen imports, with BEM
objectives only and no CFD stamp or flow fields. They are not an Assess, so I did not open them.
After Preview, `score_line`, `flow_card` and `assess_msg` are empty, and `flow_numbers` is [].

| # | surface | text (≤ 80 chars) | already shown where | call |
|---|---|---|---|---|
| 1 | Intro alert (Design) | "Design 3D-printable replacement blades… Preview updates the shape in seconds; Assess runs one CFD solve (~15–30 min); Optimize…(hours)" | "Start here: 1) Pick a design ↓ 2) Preview (sec) 3) Assess (~15–30 min) 4) Optimize (hours…" directly below, and the button labels PREVIEW (SEC) / ASSESS (~15–30 MIN) / OPTIMIZE (HOURS). The timings appear 3 times | needs Kimball copy (keep one) |
| 2 | Results Design card, info line 1 | "Reference · Noctua NF-A12x25 (published datasheet)" | Design select right above it ("◆ Reference · Noctua A12x25 (published)"), and the scatter legend "Noctua NF-A12x25 (published)" | hide |
| 3 | Results Design card, info line 3 | "Parametric stock recipe loaded — press Preview/Assess to compare CFD vs published." | the pre-Preview Actions line "✓ Stock reference loaded … cached mesh". It is still shown **after** Preview ran, so it is stale | hide after Preview |
| 4 | Results Design card, info line 2 | "Published free 60.1 CFM · hose-est load 43.9 CFM" | Fan model header "Published 60 CFM / 23 Pa / 23 dBA", and the scatter ✕ at 60.1 / 43.9. The header rounds 60.1 to 60 | keep (numbers); header rounding needs Kimball copy |
| 5 | Results, above plot | "No scored designs yet — Assess one blade or open an Optimize run to fill this plot. Gold ✕ (stock) still shows when enabled." | "Show stock (published)" switch, and #6/#7 below. That makes 3 "no CFD yet → Assess" prompts on one screen | needs Kimball copy |
| 6 | Results, flow card | "No flow simulation for this design yet. Run Assess to see how the air moves." | #5, and the Design viewer caption "Schematic -Z annulus flow (stock has no CFD — Assess for real arrows…)" | keep one |
| 7 | Results (Expert only) | "Airflow not available for this design" | #6, directly above it | hide |
| 8 | Actions, preview_msg line 2 | "✓ fits Noctua NF-A12x25 (dia 109 mm, depth 16 mm, 11 g)" | tip_fit_info "built tip dia 109.0 mm … ✓ fits." and hub_fit_info "✓ fits — cup will carve" in Geometry. The 11 g is unique, and it is PETG regardless of picker (QA-36) | keep |
| 9 | Actions, preview_msg line 1 | "Preview (orange): 9 blades, camber 0.024/0.048/0.044, smooth." | the slider values in Planform / Airfoil | keep (it says what was built) |
| 10 | Actions chip | "case hose · PETG — change under Assess & print below." | the Assess & print panel's own dropdown, which is collapsed | keep |

Not duplicated: "🖨 Difficulty 33/100…", "Memory: 16GB tier — parallel fuse.", and the Export caption.
