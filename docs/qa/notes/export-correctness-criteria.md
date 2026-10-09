# Pre-registration: export / print correctness on master (request 6), 2026-10-09 r4

Written and hashed **before** running. The hash is recorded in `handoff/2026-10-09_from-qa-3/README.md`.

**Designs:**
- **Stock:** `stock_blade_flat("a12x25")`.
- **9504:** `ref_prev04_T06559_bem_9504.flat.json` from repo-r3 `handoff/2026-10-09_from-qa-2/screen_r3/designs/`.

**Path:** exactly the cockpit Export path with the default switches, Fit frame ON and Fit hub ON:
- `prepare_export_flat(flat, spec, fit_frame=True, features=None, fit_hub=True)`;
- then `blade_from_flat`;
- then `fansim.cockpit.fan_export.do_export(params, out, spec, also_mirror=True)`.

That writes the as-designed STL plus the CW/CCW mirror pair (`impeller_as_designed.stl` and `impeller_mirrored.stl` in a `*_handedness` dir, or wherever `do_export` puts them).

**Checks.** Each STL is checked with trimesh; each design passes only if every check passes.

| # | check | pass rule |
|---|---|---|
| E1 | watertight, winding | `is_watertight`, `is_winding_consistent` |
| E2 | single body | `len(mesh.split(only_watertight=False)) == 1` |
| E3 | Euler number | equals 2 − 2g for the expected genus. One through-bore gives g = 1, so Euler = 0; with no through-hole, g = 0, so Euler = 2. Report the value and require it to equal the as-designed file's value for the mirror. |
| E4 | normals outward | `volume > 0` (signed) and `is_volume` |
| E5 | tip Ø | 2·max radial extent within the spec `tip_dia_mm` (95–110), and ≤ 110.0 + 0.1 |
| E6 | depth | z extent within the spec `depth_mm` (10–25), and ≤ 25.0 + 0.1 |
| E7 | motor cup Ø | measured cup inner Ø (largest empty circle at mid-cup depth on the cup side, from a mesh section) = `cavity_dia_mm` 37.25 ± 0.15 mm |
| E8 | motor cup depth | measured cavity depth = `cavity_depth_mm` 13.0 ± 0.2 mm |
| E9 | grip pads | `grip_count` (20) pads visible in the cup-wall section (local minima of section radius), each protruding `grip_protrude_mm` 0.7 ± 0.15 mm |
| E10 | blade count | count of separate blade cross-sections in a section at r = 0.8·R_tip = `n_blades` |
| E11 | mirror is a mirror | after reflecting the mirrored STL through the plane the code mirrors in (identified from `handedness` meta / code), the symmetric Hausdorff distance to the as-designed STL is ≤ 0.05 mm (200 k samples). Volumes agree within 0.1 %. Signed handedness is opposite: the sign of mean blade stagger slope dθ/dz at r = 0.8·R is opposite. |
| E12 | sidecars | the `print_fit.json` / mount checklist exist, and `mount_ok` and `frame_ok` are True for the as-designed file |

Thresholds won't change after seeing results. If a measurement method turns out to be unworkable (e.g. the grip section is ambiguous), I'll say so and report the raw measurement rather than adjusting the rule.
