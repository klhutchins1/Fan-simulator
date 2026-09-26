"""Assemble a complete OpenFOAM v2406 MRF case directory from an impeller + TestRig."""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path

import trimesh

from fansim.cfd import templates as T
from fansim.cfd.domain import MM_TO_M, TestRig
from fansim.cfd.wall_roughness import nut_wall_bc, wall_ks_m

RHO_AIR = 1.2
NU_AIR = 1.5e-5
CMU = 0.09
TURB_INTENSITY = 0.05
BOX_SCALE = 1.12  # hex half-side / duct_radius when a circular casing is present


SURF_LEVEL_MIN = 2  # baseline snappy surface refinement (thick blades keep this)
SURF_LEVEL_MAX = 4  # cap so a knife-thin wall can't demand an unbounded mesh
WALL_CELLS_ACROSS = 3  # target cells through the thinnest blade wall (finest cell <= wall/3)


def surface_level_for_wall(
    base_cell_m: float,
    min_wall_mm: float,
    *,
    cells_across: int = WALL_CELLS_ACROSS,
    min_level: int = SURF_LEVEL_MIN,
    max_level: int = SURF_LEVEL_MAX,
) -> int:
    """snappy surface-refinement level that resolves a thin blade wall.

    snappy halves the background cell once per level, so the finest surface cell is
    ``base_cell / 2**level``. Return the smallest level whose finest cell is <=
    ``min_wall_mm / cells_across``, clamped to ``[min_level, max_level]``. Thin plates
    (the a12x25 refit's ~1.5 mm wall) need more levels; thick blades keep the cheap baseline.
    Under-resolving to ~1 cell suppresses blade loading (see the a12x25 CFD investigation).
    """
    if min_wall_mm <= 0:
        return max_level
    target_mm = min_wall_mm / cells_across
    base_mm = base_cell_m * 1000.0
    level = math.ceil(math.log2(base_mm / target_mm)) if base_mm > target_mm else min_level
    return int(max(min_level, min(max_level, level)))


@dataclass
class MeshResolution:
    base_cell: float = 0.003  # m, background hex size
    surf_min: int = 1
    surf_max: int = 2
    feature_level: int = 2
    add_layers: bool = False
    n_surface_layers: int = 3

    @classmethod
    def for_blade(
        cls,
        base_cell: float,
        min_wall_mm: float,
        *,
        cells_across: int = WALL_CELLS_ACROSS,
        add_layers: bool = False,
    ) -> "MeshResolution":
        """Resolution whose surface refinement resolves ``min_wall_mm`` (>= ~3 cells).

        Adapts snappy surface + feature levels to the blade's thinnest wall so thin plates
        are meshed properly without over-refining thick blades. surf_min trails surf_max by
        one so the whole impeller surface carries at least the coarser level.
        """
        lvl = surface_level_for_wall(base_cell, min_wall_mm, cells_across=cells_across)
        return cls(base_cell=base_cell, surf_min=max(1, lvl - 1), surf_max=lvl,
                   feature_level=lvl, add_layers=add_layers)


def snappy_layers_mapping(mesh: MeshResolution) -> dict[str, str]:
    """Snappy placeholders for opt-in impeller prism layers. Default is off."""
    if not mesh.add_layers:
        return {"ADDLAYERS": "false", "LAYER_PATCHES": ""}
    n = mesh.n_surface_layers
    return {
        "ADDLAYERS": "true",
        "LAYER_PATCHES": f"        impeller {{ nSurfaceLayers {n}; }}\n",
    }


def grid_convergence_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="grid-convergence study (free delivery)")
    ap.add_argument("--base-json", required=True)
    ap.add_argument("--base-trial", type=int, required=True)
    ap.add_argument("--cells", default="0.007,0.005,0.0035",
                    help="base_cell sizes (m), coarse->fine")
    ap.add_argument("--iters", type=int, default=1000)
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--out", default="runs/gridconv")
    ap.add_argument("--layers", action="store_true", default=False,
                    help="grow prism layers on the impeller (off)")
    return ap


def _header(cls: str, obj: str) -> str:
    return T.render(T.FOAM_HEADER, {"CLASS": cls, "OBJECT": obj})


def _write(path: Path, template: str, cls: str, obj: str, mapping: dict) -> None:
    body = T.render(template, {"HEADER": _header(cls, obj), **mapping})
    path.write_text(body, encoding="utf-8")


def _extra_wall_snippets(name: str, feature_level: int, surf_min: int, surf_max: int,
                         ks_m: float = 0.0) -> dict[str, str]:
    """Snappy / BC placeholders for an extra stationary wall STL (frame, casing, stator)."""
    from fansim.cfd.wall_roughness import nut_wall_bc

    extract = (
        f"{name}.stl\n"
        "{\n"
        "    extractionMethod extractFromSurface;\n"
        "    extractFromSurfaceCoeffs { includedAngle 150; }\n"
        "    subsetFeatures { nonManifoldEdges no; openEdges yes; }\n"
        "    writeObj no;\n"
        "}\n"
    )
    return {
        "GEOM": f"    {name}.stl {{ type triSurfaceMesh; name {name}; }}\n",
        "FEAT": f'        {{ file "{name}.eMesh"; level {feature_level}; }}\n',
        "SURF": (
            f"        {name} {{ level ({surf_min} {surf_max}); "
            f"patchInfo {{ type wall; }} }}\n"
        ),
        "EXTRACT": extract,
        "PATCH": f" {name}",
        "U": f"    {name} {{ type noSlip; }}\n",
        "P": f"    {name} {{ type zeroGradient; }}\n",
        "NUT": nut_wall_bc(name, wall_ks_m=float(ks_m or 0.0)),
    }


def _empty_wall_snippets() -> dict[str, str]:
    return {k: "" for k in ("GEOM", "FEAT", "SURF", "EXTRACT", "PATCH", "U", "P", "NUT")}


def _k_omega_bc(snips: dict[str, str], k_val: float, omega_val: float) -> tuple[str, str]:
    if not snips["PATCH"]:
        return "", ""
    name = snips["PATCH"].strip()
    return (
        f"    {name} {{ type kqRWallFunction; value uniform {k_val}; }}\n",
        f"    {name} {{ type omegaWallFunction; value uniform {omega_val}; }}\n",
    )


_PLACEMENT_TOL_M = 1e-6


def check_placement(impeller_mm: trimesh.Trimesh, rig: TestRig, *, dual_mrf: dict | None = None,
                    downstream_mm: dict[str, trimesh.Trimesh] | None = None) -> None:
    """Refuse cases whose rotor pokes out of the MRF zone, or whose frame/stator overlaps the rotor.

    Blade parts outside the MRF zone are solved as stationary walls, and a frame inside the blade
    band intersects the rotor. Both silently corrupt CFM, so fail loudly instead.
    """
    z0 = float(impeller_mm.bounds[0, 2]) * MM_TO_M
    z1 = float(impeller_mm.bounds[1, 2]) * MM_TO_M
    if dual_mrf is not None:
        lo, hi = float(dual_mrf["front_z_min"]), float(dual_mrf["rear_z_max"])
    else:
        lo, hi = float(rig.mrf_z_min), float(rig.mrf_z_max)
    if z0 < lo - _PLACEMENT_TOL_M or z1 > hi + _PLACEMENT_TOL_M:
        raise ValueError(
            f"impeller z [{z0 * 1e3:.2f}, {z1 * 1e3:.2f}] mm is not inside the MRF zone "
            f"[{lo * 1e3:.2f}, {hi * 1e3:.2f}] mm — size the rig from the STL "
            f"(fansim.cfd.orientation.fit_rig_to_stl)")
    for name, part in (downstream_mm or {}).items():
        pz0 = float(part.bounds[0, 2]) * MM_TO_M
        if pz0 < z1 - _PLACEMENT_TOL_M:
            raise ValueError(
                f"{name} starts at z={pz0 * 1e3:.2f} mm, inside the impeller (z_max "
                f"{z1 * 1e3:.2f} mm) — export it from the fitted rig")


def build_case(
    case_dir: str | Path,
    impeller_stl_mm: str | Path,
    rig: TestRig,
    frame_stl_mm: str | Path | None = None,
    casing_stl_mm: str | Path | None = None,
    stator_stl_mm: str | Path | None = None,
    mesh: MeshResolution | None = None,
    n_iters: int = 800,
    n_subdomains: int = 8,
    back_pressure_pa: float | None = None,
    u_guess: float = 2.0,
    dual_mrf: dict | None = None,
    wall_ks_mm: float | None = None,
) -> Path:
    """Write a ready-to-run OpenFOAM case. ``impeller_stl_mm`` is a millimeter-scale STL.

    ``frame_stl_mm=None`` keeps the impeller-only case (used by validation scripts).
    ``casing_stl_mm`` snaps a cylindrical duct wall inside an oversized hex; omit it
    to keep the square-tunnel screening box.
    ``stator_stl_mm`` may be used alone (replace frame) or together with ``frame_stl_mm``
    for a stator-then-frame stack (frame must sit further downstream).

    If ``back_pressure_pa`` is given, use pressure-driven BCs (total-pressure inlet, fixed
    static back-pressure outlet) so the flow rate emerges from the blade design -- this is
    the mode used for optimization, where CFM is an objective. Otherwise use the
    velocity-driven BCs (fixed inlet velocity) used by the fan-curve sweep.

    ``wall_ks_mm`` opt-in sand-grain roughness on printed walls (impeller + frame/stator);
    the circular screening casing stays smooth.

    ``dual_mrf`` when set enables two MRF zones (CROR). Keys (SI metres / rad·s⁻¹):
    ``front_z_min``, ``front_z_max``, ``rear_z_min``, ``rear_z_max``,
    ``omega_front``, ``omega_rear``.
    """
    case_dir = Path(case_dir)
    mesh = mesh or MeshResolution()
    for sub in ("0", "constant/triSurface", "system"):
        (case_dir / sub).mkdir(parents=True, exist_ok=True)

    # --- Load all STLs (still mm-scale) before any scaling or writing ---
    surf = trimesh.load(str(impeller_stl_mm), force="mesh")
    frame_mesh = trimesh.load(str(frame_stl_mm), force="mesh") if frame_stl_mm is not None else None
    casing_mesh = trimesh.load(str(casing_stl_mm), force="mesh") if casing_stl_mm is not None else None
    stator_mesh = trimesh.load(str(stator_stl_mm), force="mesh") if stator_stl_mm is not None else None

    downstream_mm: dict[str, trimesh.Trimesh] = {}
    if frame_mesh is not None:
        downstream_mm["frame"] = frame_mesh
    if stator_mesh is not None:
        downstream_mm["stator"] = stator_mesh
    check_placement(surf, rig, dual_mrf=dual_mrf, downstream_mm=downstream_mm)

    # --- Scale the impeller STL mm -> m into the case ---
    surf.apply_scale(MM_TO_M)
    surf.export(str(case_dir / "constant/triSurface/impeller.stl"))

    # --- Optional stationary frame / casing, also mm -> m into the case ---
    if frame_mesh is not None:
        frame_mesh.apply_scale(MM_TO_M)
        frame_mesh.export(str(case_dir / "constant/triSurface/frame.stl"))
    if casing_mesh is not None:
        casing_mesh.apply_scale(MM_TO_M)
        casing_mesh.export(str(case_dir / "constant/triSurface/casing.stl"))
    if stator_mesh is not None:
        stator_mesh.apply_scale(MM_TO_M)
        stator_mesh.export(str(case_dir / "constant/triSurface/stator.stl"))

    # --- Derived flow / turbulence quantities ---
    u_in = abs(float(rig.inlet_velocity))
    u_axial = float(rig.u_axial)  # +Z duct flow (inlet −Z → outlet +Z); rotor oriented by fansim.cfd.orientation
    k = 1.5 * (TURB_INTENSITY * max(u_in, 1e-3)) ** 2
    length_scale = 0.07 * (2.0 * rig.duct_radius)
    omega_turb = math.sqrt(k) / (CMU**0.25 * length_scale)

    H = BOX_SCALE * rig.duct_radius if casing_stl_mm is not None else rig.duct_radius
    zmin, zmax = rig.domain_z_min, rig.domain_z_max
    nx = max(10, round(2 * H / mesh.base_cell))
    nz = max(20, round((zmax - zmin) / mesh.base_cell))
    write_int = max(1, n_iters // 2)  # field snapshots (kept small via purgeWrite)
    fo_int = max(1, n_iters // 40)  # fine function-object sampling for convergence tracking

    frame = (_extra_wall_snippets("frame", mesh.feature_level, mesh.surf_min, mesh.surf_max)
             if frame_stl_mm is not None else _empty_wall_snippets())
    casing = (_extra_wall_snippets("casing", mesh.feature_level, mesh.surf_min, mesh.surf_max)
              if casing_stl_mm is not None else _empty_wall_snippets())
    stator = (_extra_wall_snippets("stator", mesh.feature_level, mesh.surf_min, mesh.surf_max)
              if stator_stl_mm is not None else _empty_wall_snippets())

    ks_m = wall_ks_m(wall_ks_mm)
    impeller_nut = nut_wall_bc("impeller", wall_ks_m=ks_m)
    # Printed solids get rough when ks is set; casing is a duct artifact → always smooth.
    if ks_m > 0.0:
        if frame_stl_mm is not None:
            frame["NUT"] = nut_wall_bc("frame", wall_ks_m=ks_m)
        if stator_stl_mm is not None:
            stator["NUT"] = nut_wall_bc("stator", wall_ks_m=ks_m)

    if casing_stl_mm is not None:
        locx = 0.35 * rig.duct_radius
        locy = 0.0
        locz = rig.domain_z_min + 0.25 * rig.inlet_length
    else:
        locx = locy = 0.9 * rig.duct_radius
        locz = 0.0

    # --- system/ ---
    _write(case_dir / "system/blockMeshDict", T.BLOCK_MESH, "dictionary", "blockMeshDict", {
        "XMIN": -H, "XMAX": H, "YMIN": -H, "YMAX": H, "ZMIN": zmin, "ZMAX": zmax,
        "NX": nx, "NY": nx, "NZ": nz,
    })
    _write(case_dir / "system/snappyHexMeshDict", T.SNAPPY, "dictionary", "snappyHexMeshDict", {
        "FEATLVL": mesh.feature_level, "SURFMIN": mesh.surf_min, "SURFMAX": mesh.surf_max,
        "LOCX": locx, "LOCY": locy, "LOCZ": locz,
        "FRAME_GEOM": frame["GEOM"], "FRAME_FEAT": frame["FEAT"], "FRAME_SURF": frame["SURF"],
        "CASING_GEOM": casing["GEOM"], "CASING_FEAT": casing["FEAT"], "CASING_SURF": casing["SURF"],
        "STATOR_GEOM": stator["GEOM"], "STATOR_FEAT": stator["FEAT"], "STATOR_SURF": stator["SURF"],
        **snappy_layers_mapping(mesh),
    })
    _write(case_dir / "system/surfaceFeatureExtractDict", T.SURFACE_FEATURES,
           "dictionary", "surfaceFeatureExtractDict", {
               "FRAME_EXTRACT": frame["EXTRACT"], "CASING_EXTRACT": casing["EXTRACT"],
               "STATOR_EXTRACT": stator["EXTRACT"],
           })
    if dual_mrf is not None:
        _write(case_dir / "system/topoSetDict", T.TOPOSET_DUAL_MRF, "dictionary", "topoSetDict", {
            "MRF_FRONT_ZMIN": dual_mrf["front_z_min"],
            "MRF_FRONT_ZMAX": dual_mrf["front_z_max"],
            "MRF_REAR_ZMIN": dual_mrf["rear_z_min"],
            "MRF_REAR_ZMAX": dual_mrf["rear_z_max"],
            "MRFRADIUS": rig.duct_radius,
        })
    else:
        _write(case_dir / "system/topoSetDict", T.TOPOSET, "dictionary", "topoSetDict", {
            "MRFZMIN": rig.mrf_z_min, "MRFZMAX": rig.mrf_z_max, "MRFRADIUS": rig.duct_radius,
        })
    _write(case_dir / "system/controlDict", T.CONTROL_DICT, "dictionary", "controlDict", {
        "ENDTIME": n_iters, "WRITEINT": write_int, "FOINT": fo_int, "RHO": RHO_AIR,
    })
    _write(case_dir / "system/fvSchemes", T.FV_SCHEMES, "dictionary", "fvSchemes", {})
    _write(case_dir / "system/fvSolution", T.FV_SOLUTION, "dictionary", "fvSolution", {})
    _write(case_dir / "system/decomposeParDict", T.DECOMPOSE_PAR,
           "dictionary", "decomposeParDict", {"NPROCS": n_subdomains})

    # --- constant/ ---
    _write(case_dir / "constant/transportProperties", T.TRANSPORT,
           "dictionary", "transportProperties", {"NU": NU_AIR})
    _write(case_dir / "constant/turbulenceProperties", T.TURBULENCE,
           "dictionary", "turbulenceProperties", {})
    if dual_mrf is not None:
        _write(case_dir / "constant/MRFProperties", T.MRF_PROPERTIES_DUAL,
               "dictionary", "MRFProperties", {
                   "OMEGA_FRONT": dual_mrf["omega_front"],
                   "OMEGA_REAR": dual_mrf["omega_rear"],
                   "FRAME_PATCH": frame["PATCH"],
                   "CASING_PATCH": casing["PATCH"],
                   "STATOR_PATCH": stator["PATCH"],
               })
    else:
        _write(case_dir / "constant/MRFProperties", T.MRF_PROPERTIES,
               "dictionary", "MRFProperties", {
                   "OMEGA": rig.omega_signed,
                   "FRAME_PATCH": frame["PATCH"],
                   "CASING_PATCH": casing["PATCH"],
                   "STATOR_PATCH": stator["PATCH"],
               })

    # --- 0/ ---
    if back_pressure_pa is not None:
        # u_guess seeds the pressure-driven initial field; sweeping it probes whether the
        # steady solve has multiple solution branches (bistability).
        u_guess_axial = abs(float(u_guess))
        k = 1.5 * (TURB_INTENSITY * abs(u_guess)) ** 2
        omega_turb = math.sqrt(k) / (CMU**0.25 * length_scale)
        pback_kin = back_pressure_pa / RHO_AIR
        frame_k, frame_omega = _k_omega_bc(frame, k, omega_turb)
        casing_k, casing_omega = _k_omega_bc(casing, k, omega_turb)
        stator_k, stator_omega = _k_omega_bc(stator, k, omega_turb)
        _write(case_dir / "0/U", T.FIELD_U_PDRIVEN, "volVectorField", "U",
               {"UGUESS": u_guess_axial, "FRAME_U": frame["U"], "CASING_U": casing["U"],
                "STATOR_U": stator["U"]})
        _write(case_dir / "0/p", T.FIELD_P_PDRIVEN, "volScalarField", "p",
               {"PBACK": pback_kin, "FRAME_P": frame["P"], "CASING_P": casing["P"],
                "STATOR_P": stator["P"]})
        _write(case_dir / "0/k", T.FIELD_K_PDRIVEN, "volScalarField", "k",
               {"K": k, "FRAME_K": frame_k, "CASING_K": casing_k, "STATOR_K": stator_k})
        _write(case_dir / "0/omega", T.FIELD_OMEGA_PDRIVEN, "volScalarField", "omega",
               {"OMEGAT": omega_turb, "FRAME_OMEGA": frame_omega, "CASING_OMEGA": casing_omega,
                "STATOR_OMEGA": stator_omega})
    else:
        frame_k, frame_omega = _k_omega_bc(frame, k, omega_turb)
        casing_k, casing_omega = _k_omega_bc(casing, k, omega_turb)
        stator_k, stator_omega = _k_omega_bc(stator, k, omega_turb)
        _write(case_dir / "0/U", T.FIELD_U, "volVectorField", "U",
               {"UIN": u_axial, "FRAME_U": frame["U"], "CASING_U": casing["U"],
                "STATOR_U": stator["U"]})
        _write(case_dir / "0/p", T.FIELD_P, "volScalarField", "p",
               {"FRAME_P": frame["P"], "CASING_P": casing["P"], "STATOR_P": stator["P"]})
        _write(case_dir / "0/k", T.FIELD_K, "volScalarField", "k",
               {"K": k, "FRAME_K": frame_k, "CASING_K": casing_k, "STATOR_K": stator_k})
        _write(case_dir / "0/omega", T.FIELD_OMEGA, "volScalarField", "omega",
               {"OMEGAT": omega_turb, "FRAME_OMEGA": frame_omega, "CASING_OMEGA": casing_omega,
                "STATOR_OMEGA": stator_omega})
    _write(case_dir / "0/nut", T.FIELD_NUT, "volScalarField", "nut",
           {"IMPELLER_NUT": impeller_nut,
            "FRAME_NUT": frame["NUT"], "CASING_NUT": casing["NUT"], "STATOR_NUT": stator["NUT"]})

    return case_dir


MESH_PIPELINE = [
    "surfaceFeatureExtract",
    "blockMesh",
    "snappyHexMesh -overwrite",
    "topoSet",
    "renumberMesh -overwrite",
    "checkMesh -allTopology",
]


def run_mesh(runner) -> None:
    """Run the serial meshing pipeline in the container."""
    for cmd in MESH_PIPELINE:
        runner.run(cmd)


def run_solve(runner, n_procs: int = 8, reconstruct: bool = False) -> None:
    """Solve with simpleFoam, in parallel via MPI when ``n_procs`` > 1.

    Metrics come from function-object output written to the case root by the master rank,
    so reconstruction is only needed when the full field is wanted (e.g. visualization).
    """
    # Clear stale decomposition and postProcessing so this run writes fresh output.
    # On restart, OpenFOAM ROTATES function-object files (old surfaceFieldValue.dat ->
    # surfaceFieldValue_0.dat) and writes the new run to the suffixed name -- which the
    # metrics parser would miss -- so wipe postProcessing to keep the canonical filename.
    runner.run("rm -rf processor* postProcessing", check=False)
    if n_procs and n_procs > 1:
        runner.run("decomposePar -force")
        mpi = f"mpirun --allow-run-as-root --oversubscribe -np {n_procs}"
        # potentialFoam seeds a divergence-free initial field -> faster, quieter convergence.
        runner.run(f"{mpi} potentialFoam -parallel -initialiseUBCs", check=False)
        runner.run(f"{mpi} simpleFoam -parallel")
        if reconstruct:
            runner.run("reconstructPar -latestTime")
    else:
        runner.run("potentialFoam -initialiseUBCs", check=False)
        runner.run("simpleFoam")


def _face_centers_from_box(box: dict) -> list[tuple[float, float, float]]:
    """Six permeable-box face centers (+x,-x,+y,-y,+z,-z), SI metres."""
    cx, cy, cz = float(box["cx_m"]), float(box["cy_m"]), float(box["cz_m"])
    hxy, hz = float(box["half_xy_m"]), float(box["half_z_m"])
    return [
        (cx + hxy, cy, cz),
        (cx - hxy, cy, cz),
        (cx, cy + hxy, cz),
        (cx, cy - hxy, cz),
        (cx, cy, cz + hz),
        (cx, cy, cz - hz),
    ]


_FACE_NORMALS = (
    (1.0, 0.0, 0.0),
    (-1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, -1.0, 0.0),
    (0.0, 0.0, 1.0),
    (0.0, 0.0, -1.0),
)


def apply_des_transient(
    case_dir: str | Path,
    *,
    box: dict,
    delta_t: float,
    end_time: float,
    write_interval: int = 1,
    fo_interval: int = 1,
) -> Path:
    """Overlay DES/pimpleFoam + six permeable-face samplers on an existing case.

    Does not remesh. Writes ``constant/des_perm_box.json``. Steady RAS templates are
    replaced for turbulence / schemes / solution / controlDict only.
    """
    from fansim.cfd.des_fwh import write_box_sidecar

    case_dir = Path(case_dir)
    (case_dir / "system").mkdir(parents=True, exist_ok=True)
    (case_dir / "constant").mkdir(parents=True, exist_ok=True)

    fos = []
    for i, (center, n_hat) in enumerate(zip(_face_centers_from_box(box), _FACE_NORMALS)):
        block = T.DES_FACE_FO
        mapping = {
            "IDX": i,
            "PX": center[0], "PY": center[1], "PZ": center[2],
            "NX": n_hat[0], "NY": n_hat[1], "NZ": n_hat[2],
            "FOINT": fo_interval,
        }
        for k, v in mapping.items():
            block = block.replace(f"@{k}@", str(v))
        fos.append(block)

    _write(case_dir / "constant/turbulenceProperties", T.DES_TURBULENCE,
           "dictionary", "turbulenceProperties", {})
    _write(case_dir / "system/fvSchemes", T.DES_FV_SCHEMES, "dictionary", "fvSchemes", {})
    _write(case_dir / "system/fvSolution", T.DES_FV_SOLUTION, "dictionary", "fvSolution", {})
    _write(case_dir / "system/controlDict", T.DES_CONTROL_DICT, "dictionary", "controlDict", {
        "ENDTIME": end_time,
        "DELTAT": delta_t,
        "WRITEINT": write_interval,
        "DES_FACE_FOS": "".join(fos),
    })
    write_box_sidecar(case_dir / "constant" / "des_perm_box.json", box)
    return case_dir


def run_solve_des(runner, n_procs: int = 8, reconstruct: bool = False) -> None:
    """Solve with pimpleFoam (DES transient), parallel via MPI when ``n_procs`` > 1."""
    runner.run("rm -rf processor* postProcessing", check=False)
    if n_procs and n_procs > 1:
        runner.run("decomposePar -force")
        mpi = f"mpirun --allow-run-as-root --oversubscribe -np {n_procs}"
        runner.run(f"{mpi} potentialFoam -parallel -initialiseUBCs", check=False)
        runner.run(f"{mpi} pimpleFoam -parallel")
        if reconstruct:
            runner.run("reconstructPar -latestTime")
    else:
        runner.run("potentialFoam -initialiseUBCs", check=False)
        runner.run("pimpleFoam")
