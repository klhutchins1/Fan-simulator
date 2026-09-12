## Task 3 report — `build_prop_case` (prop CFD, dry wiring)

### What was implemented
- Added `build_prop_case(case_dir, impeller_stl_mm, domain: PropOpenAir, *, mesh=None, n_iters=400, n_subdomains=8) -> Path` in `fansim/propeller/cfd.py`.
- The function writes a **compressible** OpenFOAM case targeting **`rhoSimpleFoam`** using the `PROP_*` templates added in Task 2.

### Case layout / pipeline (written, not executed)
- **STL handling**
  - Loads `impeller_stl_mm` (mm) with `trimesh`, scales by `MM_TO_M`, exports to `constant/triSurface/impeller.stl`.
- **Mesh dictionaries**
  - `system/blockMeshDict`: square/hex box spanning:
    - \(x,y\in[-domain\_radius, +domain\_radius]\)
    - \(z\in[z\_min, z\_max]\)
  - `system/snappyHexMeshDict`: impeller-only geometry (no frame/casing/stator), optional prism layers via `snappy_layers_mapping(mesh)`.
  - `system/surfaceFeatureExtractDict`: impeller-only.
  - `system/topoSetDict`: reuses `TOPOSET` template to create a single cellZone named **`rotor`** with:
    - cylinder radius \(= 1.05 \times tip\_radius\)
    - axial span \([mrf\_z\_min, mrf\_z\_max]\)
- **Solver / numerics**
  - `system/controlDict`: `PROP_CONTROL_DICT` (application **`rhoSimpleFoam`**) with `endTime=n_iters`, `writeInterval=max(1,n_iters//2)`, `FOINT=max(1,n_iters//40)`.
  - `system/fvSchemes`, `system/fvSolution`: `PROP_FV_SCHEMES`, `PROP_FV_SOLUTION`.
  - `system/decomposeParDict`: `DECOMPOSE_PAR` with `numberOfSubdomains=n_subdomains`.

### Physics files written
- `constant/thermophysicalProperties`: `PROP_THERMO` (perfect gas).
- `constant/turbulenceProperties`: `PROP_TURBULENCE` (RAS kOmegaSST).
- `constant/MRFProperties`: `PROP_MRF` with `omega = domain.omega_signed` and `cellZone rotor`.
- `0/` fields: `T`, `p`, `U`, `k`, `omega`, `nut` using `PROP_T/P/U/K/OMEGA/NUT`.

### Notes / deviations
- No `constant/transportProperties` is written (intentional; compressible thermo replaces nu-only file).
- Freestream/open-air BCs come from the `PROP_*` templates (freestream / inletOutlet / noSlip as defined there).
- `locationInMesh` is placed near the domain corner to avoid intersecting the impeller.

### Test coverage
- Added `tests/test_prop_cfd.py::test_build_prop_case_writes_compressible`:
  - Builds a real prop STL via `build_prop`.
  - Uses `watertight_report` bounds to parameterize `prop_open_air`.
  - Asserts `rhoSimpleFoam` is present in `system/controlDict`, key compressible files exist, and `rotor` appears in `constant/MRFProperties`.

### Known issue (Windows/CadQuery teardown)
- On Windows, pytest may end with `exit_code=3221226356` (ACCESS_VIOLATION) after assertions pass (noted in the task brief). The test itself passes; the crash appears during teardown in the CAD/geometry stack.
