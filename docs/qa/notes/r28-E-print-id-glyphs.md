# r28 Task E — how the 28.3 glyphs were measured (grok, 2026-11-09)

Results and tracker rows: `docs/qa/rounds/r28.md`. Prereg `f208f30`. Scripts and data: `handoff/2026-11-09_from-qa-28/{scripts,data}`.

- **Export** (`scripts/e_export.py`): `export_print_ready(stock params, mount=A12x25 MotorMount, print_id=None | "K7WB2", also_step=True)`, in-process.
  Timing / peak RSS in separate processes (`scripts/e_one_export.py`, `resource.getrusage` maxrss): `data/perf_*.json`.
- **Geometry** (`scripts/e_geom.py`, a separate QA venv with trimesh/shapely/rtree; CAD not needed): planar sections of the sibling and marked STLs.
  The removed region is the sibling section minus the marked section, at depths 0.05–3 mm below z_top. Depth is bisected (`scripts/e_depth.py`). K7 uses
  the r9 `cup_measure` (ray profile, unchanged). B-rep solid count = MANIFOLD_SOLID_BREP entities in the exported STEP.
- **Reading test (E9a)**: groove blobs at mid-depth are sorted left-to-right as seen from outside +Z (the mark centre is at θ = 90°, so screen x
  equals world x). Each blob is mapped to a local frame (right = clockwise, up = radially outward) and matched by IoU against every font glyph
  drawn at 0.6 mm with square caps, normal and mirrored. Symmetric glyphs (W) tie and count as not mirrored. This read does not assume anything
  about how the code lays the characters out. Renders: `screens/e9a_marked_top_view_from_plusZ.png` (master: "5BWΓK"-looking),
  `screens/patched/e9a_marked_top_view_from_plusZ.png` (reads K7WB2), and `e9a_same_mirrored_for_comparison.png`.
- **Font (E9b/E7)** (`scripts/e9_font_raster.py`, CAD-free): every glyph as cut (0.6 mm boxes, cell 1.8 × 3.2 mm), pairwise IoU (6/G = 1.000),
  and worst neighbour gap for all 37² ordered pairs at r_inner. Sheet: `screens/e9_font_sheet_as_cut.png`.
- **Codec (E8/E10)** (`scripts/e_codec_font.py`): seeded rng 28, 2000 ids, exhaustive single substitutions on 200 ids, all adjacent transpositions.
- **Land metric caveat:** "land narrower than 0.2 mm" = 0.55 mm² on K7WB2. These are acute-angle wedge tips at W/K/B stroke joins. They are not
  lands separating two features, so they were not classified as MED "grooves merge". The only real narrow lands are in QA-77.
- **STL hashes** (files not shipped, 4.6 MB each): `data/stl_hashes.txt`.
- **Disclosed deviations from prereg:** E5's "identical below z_top − 0.6" fails only because the floor is at 0.65 (QA-74). Sections are identical
  from −0.66 down. The export-time finding (QA-76) was not preregistered. The second code (`M3QZ`) was not cut; the font-level gap scan covers
  the collision check for all pairs.
