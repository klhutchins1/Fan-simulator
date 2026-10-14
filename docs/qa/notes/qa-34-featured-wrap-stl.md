# QA-34 — featured wrap STL not watertight (S5_0184)

r10b W1/W6 FAIL. Closed 2026-10-14. Did **not** change `_capped_loft`.

## What it was

Featured wrapped **S5_0184** (7 blades; tubercles + serrations + dimples; designed hang 0).
`fuse_many` returned **1 solid**. The STL was 8 mesh bodies, 7 degenerate faces. Planar twin clean.
Assess would refuse; isolated P / Preview would not.

Mesh: `handoff/2026-10-13_from-qa-10/data/S5_0184_Pc.stl.gz`.

## Root cause

The impeller mesh **is** one watertight body (78 260 faces, 30 935 mm³). The extra seven “bodies”
are collapsed triangles (2 unique vertices, area 0), one per blade, at r ≈ 15.4 mm (inside the hub
at 17.4 mm), z ≈ 12.47. Tessellation needles at the wrap+feature hub join. Dropping them leaves
watertight / 1 body / the same volume.

## Fix

`fansim/geometry/export.py`: `sanitize_stl` strips faces with < 3 unique vertices or area < 1e-9 mm²
(K2). `export_stl` runs it after CadQuery tessellation, so Preview, Export, and Assess all write a
clean mesh. Fuse still only checks B-rep one-solid.

Tests: `tests/test_stl_sanitize.py`. On the kept gz: 8 bodies → 1, 7 faces dropped, volume unchanged.
