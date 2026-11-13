"""Assemble an OpenFOAM v2406 MRF case for a volute / radial blower."""

from __future__ import annotations

import math
from pathlib import Path

import trimesh

from fansim.cfd import templates as T
from fansim.cfd.domain import MM_TO_M
from fansim.cfd.openfoam_case import (
    MeshResolution,
    NU_AIR,
    RHO_AIR,
    CMU,
    TURB_INTENSITY,
    _extra_wall_snippets,
    _empty_wall_snippets,
    _k_omega_bc,
    _write,
    snappy_layers_mapping,
)
from fansim.cfd.wall_roughness import nut_wall_bc, wall_ks_m
from fansim.volute.domain import VoluteDomain
from fansim.volute.geometry import VOLUTE_HONESTY
from fansim.volute import templates as VT


def build_volute_case(
    case_dir: str | Path,
    impeller_stl_mm: str | Path,
    casing_stl_mm: str | Path,
    domain: VoluteDomain,
    *,
    mesh: MeshResolution | None = None,
    n_iters: int = 800,
    n_subdomains: int = 8,
    back_pressure_pa: float | None = None,
    u_guess: float = 2.0,
    wall_ks_mm: float | None = None,
    relax: dict | None = None,
) -> Path:
    """Write a ready-to-run volute MRF case.

    ``impeller_stl_mm`` / ``casing_stl_mm`` are millimeter-scale STLs (scaled to m).
    Inlet patch = +Z face of the hex; outlet patch = +X face. Pressure-driven mode
    when ``back_pressure_pa`` is set (optimizer / evaluate path).
    ``relax`` overrides the SIMPLE relaxation, ``{"p": .., "U": .., "turb": ..}`` (R2.5a sweep);
    None keeps the shared defaults (p 0.3, U and k/omega 0.7).
    """
    if relax is not None:
        for key in ("p", "U", "turb"):
            v = float(relax[key])
            if not 0.0 < v <= 1.0:
                raise ValueError(f"relax[{key!r}] must be in (0, 1], got {v}")
    case_dir = Path(case_dir)
    mesh = mesh or MeshResolution()
    for sub in ("0", "constant/triSurface", "system"):
        (case_dir / sub).mkdir(parents=True, exist_ok=True)

    ks_m = wall_ks_m(wall_ks_mm)

    for name, src in (("impeller", impeller_stl_mm), ("casing", casing_stl_mm)):
        surf = trimesh.load(str(src), force="mesh")
        surf.apply_scale(MM_TO_M)
        surf.export(str(case_dir / "constant/triSurface" / f"{name}.stl"))

    u_in = float(domain.inlet_velocity)
    # Entering from +Z toward the eye → negative Uz.
    u_axial = -abs(u_in)
    k = 1.5 * (TURB_INTENSITY * max(abs(u_in), 1e-3)) ** 2
    length_scale = 0.07 * max(2.0 * domain.tip_radius, 1e-6)
    omega_turb = math.sqrt(k) / (CMU**0.25 * length_scale)

    dx = domain.xmax - domain.xmin
    dy = domain.ymax - domain.ymin
    dz = domain.zmax - domain.zmin
    nx = max(12, round(dx / mesh.base_cell))
    ny = max(12, round(dy / mesh.base_cell))
    nz = max(12, round(dz / mesh.base_cell))
    write_int = max(1, n_iters // 2)
    fo_int = max(1, n_iters // 40)

    casing = _extra_wall_snippets(
        "casing", mesh.feature_level, mesh.surf_min, mesh.surf_max, ks_m=0.0)
    empty = _empty_wall_snippets()
    locx, locy, locz = domain.location_in_mesh

    _write(case_dir / "system/blockMeshDict", VT.VOLUTE_BLOCK_MESH,
           "dictionary", "blockMeshDict", {
               "XMIN": domain.xmin, "XMAX": domain.xmax,
               "YMIN": domain.ymin, "YMAX": domain.ymax,
               "ZMIN": domain.zmin, "ZMAX": domain.zmax,
               "NX": nx, "NY": ny, "NZ": nz,
           })
    _write(case_dir / "system/snappyHexMeshDict", T.SNAPPY,
           "dictionary", "snappyHexMeshDict", {
               "FEATLVL": mesh.feature_level,
               "SURFMIN": mesh.surf_min, "SURFMAX": mesh.surf_max,
               "LOCX": locx, "LOCY": locy, "LOCZ": locz,
               "FRAME_GEOM": empty["GEOM"], "FRAME_FEAT": empty["FEAT"],
               "FRAME_SURF": empty["SURF"],
               "CASING_GEOM": casing["GEOM"], "CASING_FEAT": casing["FEAT"],
               "CASING_SURF": casing["SURF"],
               "STATOR_GEOM": empty["GEOM"], "STATOR_FEAT": empty["FEAT"],
               "STATOR_SURF": empty["SURF"],
               **snappy_layers_mapping(mesh),
           })
    _write(case_dir / "system/surfaceFeatureExtractDict", T.SURFACE_FEATURES,
           "dictionary", "surfaceFeatureExtractDict", {
               "FRAME_EXTRACT": "",
               "CASING_EXTRACT": casing["EXTRACT"],
               "STATOR_EXTRACT": "",
           })
    _write(case_dir / "system/topoSetDict", T.TOPOSET, "dictionary", "topoSetDict", {
        "MRFZMIN": domain.mrf_z_min,
        "MRFZMAX": domain.mrf_z_max,
        "MRFRADIUS": domain.mrf_radius,
    })
    _write(case_dir / "system/controlDict", T.CONTROL_DICT, "dictionary", "controlDict", {
        "ENDTIME": n_iters, "WRITEINT": write_int, "FOINT": fo_int, "RHO": RHO_AIR,
    })
    _write(case_dir / "system/fvSchemes", T.FV_SCHEMES, "dictionary", "fvSchemes", {})
    _write(case_dir / "system/fvSolution", T.FV_SOLUTION, "dictionary", "fvSolution", {})
    if relax is not None:
        _set_relaxation(case_dir / "system/fvSolution", relax)
    _write(case_dir / "system/decomposeParDict", T.DECOMPOSE_PAR,
           "dictionary", "decomposeParDict", {"NPROCS": n_subdomains})

    _write(case_dir / "constant/transportProperties", T.TRANSPORT,
           "dictionary", "transportProperties", {"NU": NU_AIR})
    _write(case_dir / "constant/turbulenceProperties", T.TURBULENCE,
           "dictionary", "turbulenceProperties", {})
    _write(case_dir / "constant/MRFProperties", T.MRF_PROPERTIES,
           "dictionary", "MRFProperties", {
               "OMEGA": domain.omega_signed,
               "FRAME_PATCH": "",
               "CASING_PATCH": casing["PATCH"],
               "STATOR_PATCH": "",
           })

    if back_pressure_pa is not None:
        ug = -abs(float(u_guess))
        ug_out = abs(float(u_guess))
        k = 1.5 * (TURB_INTENSITY * abs(ug)) ** 2
        omega_turb = math.sqrt(k) / (CMU**0.25 * length_scale)
        pback_kin = back_pressure_pa / RHO_AIR
        casing_k, casing_omega = _k_omega_bc(casing, k, omega_turb)
        _write(case_dir / "0/U", VT.VOLUTE_U_PDRIVEN, "volVectorField", "U", {
            "UGUESS": ug, "UGUESS_OUT": ug_out, "CASING_U": casing["U"],
        })
        _write(case_dir / "0/p", T.FIELD_P_PDRIVEN, "volScalarField", "p", {
            "PBACK": pback_kin, "FRAME_P": "", "CASING_P": casing["P"], "STATOR_P": "",
        })
        _write(case_dir / "0/k", T.FIELD_K_PDRIVEN, "volScalarField", "k", {
            "K": k, "FRAME_K": "", "CASING_K": casing_k, "STATOR_K": "",
        })
        _write(case_dir / "0/omega", T.FIELD_OMEGA_PDRIVEN, "volScalarField", "omega", {
            "OMEGAT": omega_turb, "FRAME_OMEGA": "", "CASING_OMEGA": casing_omega,
            "STATOR_OMEGA": "",
        })
    else:
        casing_k, casing_omega = _k_omega_bc(casing, k, omega_turb)
        _write(case_dir / "0/U", VT.VOLUTE_U_VDRIVEN, "volVectorField", "U", {
            "UIN": u_axial, "CASING_U": casing["U"],
        })
        _write(case_dir / "0/p", T.FIELD_P, "volScalarField", "p", {
            "FRAME_P": "", "CASING_P": casing["P"], "STATOR_P": "",
        })
        _write(case_dir / "0/k", T.FIELD_K, "volScalarField", "k", {
            "K": k, "FRAME_K": "", "CASING_K": casing_k, "STATOR_K": "",
        })
        _write(case_dir / "0/omega", T.FIELD_OMEGA, "volScalarField", "omega", {
            "OMEGAT": omega_turb, "FRAME_OMEGA": "", "CASING_OMEGA": casing_omega,
            "STATOR_OMEGA": "",
        })

    _write(case_dir / "0/nut", T.FIELD_NUT, "volScalarField", "nut", {
        "IMPELLER_NUT": nut_wall_bc("impeller", wall_ks_m=ks_m),
        "FRAME_NUT": "",
        "CASING_NUT": casing["NUT"],
        "STATOR_NUT": "",
    })

    meta = case_dir / "constant" / "volute_domain.json"
    import json
    meta.write_text(json.dumps({
        "topology": "volute_radial",
        "inlet_patch": "+Z",
        "outlet_patch": "+X",
        "honesty": VOLUTE_HONESTY,
        "rpm": domain.rpm,
        "mrf_radius_m": domain.mrf_radius,
        "outlet_area_m2": domain.outlet_area_m2,
        "location_in_mesh": list(domain.location_in_mesh),
    }, indent=2), encoding="utf-8")

    return case_dir


def _set_relaxation(path: Path, relax: dict) -> None:
    """Swap the shared template's relaxation lines for the given factors."""
    text = path.read_text(encoding="utf-8")
    old_f, old_e = "fields    { p 0.3; }", 'equations { U 0.7; "(k|omega)" 0.7; }'
    if old_f not in text or old_e not in text:
        raise ValueError("fvSolution template changed: relaxation lines not found")
    text = text.replace(old_f, f"fields    {{ p {float(relax['p']):g}; }}")
    text = text.replace(
        old_e, f'equations {{ U {float(relax["U"]):g}; "(k|omega)" {float(relax["turb"]):g}; }}')
    path.write_text(text, encoding="utf-8")
