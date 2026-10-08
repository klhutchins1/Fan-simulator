"""Assemble a complete OpenFOAM v2406 MRF case directory from an impeller + TestRig."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path

import trimesh

from fansim.cfd import templates as T
from fansim.cfd.domain import MM_TO_M, TestRig
from fansim.cfd.metrics import CFD_VERSION
from fansim.cfd.wall_roughness import nut_wall_bc, wall_ks_m

from fansim.physics.air import RHO_AMCA as RHO_AIR
from fansim.physics.air import NU_AIR
CMU = 0.09
TURB_INTENSITY = 0.05
BOX_SCALE = 1.12  # hex half-side / duct_radius when a circular casing is present


SURF_LEVEL_MIN = 2  # baseline snappy surface refinement (thick blades keep this)
SURF_LEVEL_MAX = 4  # cap so a knife-thin wall can't demand an unbounded mesh
WALL_CELLS_ACROSS = 3  # target cells through the thinnest blade wall (finest cell <= wall/3)
# §19.14: optimizer / Assess CFD floors surface level so thick-wall designs are not coarsened
# relative to thin ones (adaptive-only moved CFM 1–4% in the v2 check). Validation scripts omit
# the floor and keep pure wall-adaptive levels.
OPTIMIZER_SURF_MAX_FLOOR = 3


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
    # §19.10: layers stay opt-in — OFF for NSGA/screening; validation P–Q passes add_layers=True.
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
        min_surf_max: int | None = None,
    ) -> "MeshResolution":
        """Resolution whose surface refinement resolves ``min_wall_mm`` (>= ~3 cells).

        Adapts snappy surface + feature levels to the blade's thinnest wall so thin plates
        are meshed properly without over-refining thick blades. surf_min trails surf_max by
        one so the whole impeller surface carries at least the coarser level.

        ``min_surf_max`` (optimizer path, §19.14) floors ``surf_max`` so thick-wall designs
        are not ranked on a coarser mesh than thin ones.
        """
        lvl = surface_level_for_wall(base_cell, min_wall_mm, cells_across=cells_across)
        if min_surf_max is not None:
            lvl = max(lvl, int(min_surf_max))
        return cls(base_cell=base_cell, surf_min=max(1, lvl - 1), surf_max=lvl,
                   feature_level=lvl, add_layers=add_layers)


def snappy_layers_mapping(mesh: MeshResolution) -> dict[str, str]:
    """Snappy placeholders for opt-in impeller prism layers.

    Default is off (§19.10): screening / NSGA stay layer-free; validation runners pass
    ``add_layers=True`` via ``--layers`` when they want resolved y+ (~2).
    """
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
    """k / omega wall-function lines for the snippet's patch and any rotating ``ROTOR2`` rider."""
    names = [snips[key].strip() for key in ("ROTOR2", "PATCH") if snips.get(key, "").strip()]
    return (
        "".join(f"    {n} {{ type kqRWallFunction; value uniform {k_val}; }}\n" for n in names),
        "".join(f"    {n} {{ type omegaWallFunction; value uniform {omega_val}; }}\n"
                for n in names),
    )


def split_dual_rotor_surface(surf: trimesh.Trimesh, dual_mrf: dict
                             ) -> tuple[trimesh.Trimesh, trimesh.Trimesh]:
    """Split a CROR surface (metres) at the inter-rotor gap: (upstream, downstream) rotor.

    Faces are assigned by centroid z against the mid-plane between ``front_z_max`` and
    ``rear_z_min`` (the zones are fitted so no blade crosses it; hub faces in the gap go to
    whichever side their centroid is on). Each part is an open surface; together they close.
    """
    import numpy as np

    z_split = 0.5 * (float(dual_mrf["front_z_max"]) + float(dual_mrf["rear_z_min"]))
    up = np.asarray(surf.triangles_center)[:, 2] < z_split
    if up.all() or not up.any():
        raise ValueError(f"dual-rotor split at z={z_split * 1e3:.2f} mm leaves one rotor empty")
    front = surf.submesh([np.flatnonzero(up)], append=True, repair=False)
    rear = surf.submesh([np.flatnonzero(~up)], append=True, repair=False)
    return front, rear


FORCES_REAR_BLOCK = """    forcesRear
    {
        type            forces;
        libs            (forces);
        patches         (impellerRear);
        rho             rhoInf;
        rhoInf          @RHO@;
        CofR            (0 0 0);
        writeControl    timeStep;
        writeInterval   @FOINT@;
    }
"""


def add_rear_forces(control_dict: Path) -> None:
    """Add a ``forcesRear`` monitor on ``impellerRear`` after ``forces`` (CROR only).

    Copies rho / write interval from the existing ``forces`` block so both rotors sample alike.
    """
    import re

    text = Path(control_dict).read_text(encoding="utf-8")
    if "forcesRear" in text:
        return
    m = re.search(r"\n    forces\n    \{.*?\n    \}\n", text, flags=re.S)
    if m is None:
        raise ValueError(f"no forces block in {control_dict}")
    block = m.group(0)
    rho = re.search(r"rhoInf\s+([^;]+);", block).group(1).strip()
    foint = re.search(r"writeInterval\s+([^;]+);", block).group(1).strip()
    rear = T.render(FORCES_REAR_BLOCK, {"RHO": rho, "FOINT": foint})
    Path(control_dict).write_text(text[:m.end()] + rear + text[m.end():], encoding="utf-8")


_PLACEMENT_TOL_M = 1e-6
_SEAL_TOL_MM = 1e-6


def check_casing_seals(casing_mm: trimesh.Trimesh, H_m: float) -> None:
    """Refuse a casing whose outer radius leaves the background box corners open.

    ``casing_mm`` is the casing mesh in its native millimetre scale (before the mm->m case
    scaling), ``H_m`` is the background hex/box half-width in metres (SI, as used elsewhere in
    :func:`build_case`). The box's far corner sits at ``H*sqrt(2)`` from the axis; a casing
    whose maximum radial extent is smaller than that leaves the corners open, and flow can
    bypass the fan bore around the outside of the tube (see the a12x25 casing-corner audit).
    """
    H_mm = H_m * 1000.0
    required_mm = H_mm * math.sqrt(2)
    max_r_mm = max(math.hypot(float(v[0]), float(v[1])) for v in casing_mm.vertices)
    if max_r_mm < required_mm - _SEAL_TOL_MM:
        raise ValueError(
            f"casing max radial extent {max_r_mm:.2f} mm is less than H*sqrt(2) = "
            f"{required_mm:.2f} mm (box half-width H={H_mm:.2f} mm) -- the box corners are "
            "open and flow can bypass the fan around the casing")


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


_PLENUM_TOL_M = 1e-3  # 1 mm: casing z_max below domain_z_max by more than this counts as a plenum
DUCT_OUTER_MARGIN_MM = 5.0  # extra radius past the box-corner requirement, for meshing slop
ROUND_DUCT_SECTIONS = 128  # annulus tessellation for the generated round duct / ring
ROUND_DUCT_Z_MARGIN_MM = 1.0  # each end extends past the domain so snappy trims it cleanly

RING_LENGTH_MM = 25.0  # nominal a12x25 frame depth
RING_Z_MARGIN_MM = 1.0  # each side's margin when the ring must lengthen to cover the impeller
_RING_COVER_TOL_MM = 1e-6


def _generate_round_duct_mesh_mm(rig: TestRig, box_scale: float) -> trimesh.Trimesh:
    """Sealed round-duct casing (mm), covering the ``box_scale``-half-width box's corners.

    Inner radius is ``rig.duct_radius``; outer radius is ``box_scale * rig.duct_radius *
    sqrt(2) + margin`` so it fully covers the background box's corners (see
    :func:`check_casing_seals`). Spans ``domain_z_min``..``domain_z_max``, extended by
    :data:`ROUND_DUCT_Z_MARGIN_MM` beyond each end so snappyHexMesh trims it cleanly at the
    domain faces instead of leaving a sliver gap.
    """
    inner_r_mm = rig.duct_radius / MM_TO_M
    outer_r_mm = box_scale * inner_r_mm * math.sqrt(2) + DUCT_OUTER_MARGIN_MM
    zmin_mm = rig.domain_z_min / MM_TO_M - ROUND_DUCT_Z_MARGIN_MM
    zmax_mm = rig.domain_z_max / MM_TO_M + ROUND_DUCT_Z_MARGIN_MM
    height_mm = zmax_mm - zmin_mm
    mesh = trimesh.creation.annulus(
        r_min=inner_r_mm, r_max=outer_r_mm, height=height_mm, sections=ROUND_DUCT_SECTIONS)
    mesh.apply_translation([0.0, 0.0, 0.5 * (zmin_mm + zmax_mm)])
    return mesh


def _generate_ring_duct_mesh_mm(
    rig: TestRig,
    box_scale: float,
    *,
    ring_length_mm: float | None = None,
    ring_z_center_mm: float | None = None,
) -> tuple[trimesh.Trimesh, float]:
    """Short sealed frame-ring casing (mm), ``RING_LENGTH_MM`` long, centred on the rotor.

    Inner radius is ``rig.duct_radius``; outer radius covers the ``box_scale``-half-width
    box's corners exactly like the full-length round duct (:func:`check_casing_seals`). Axial
    length is :data:`RING_LENGTH_MM` (25 mm, the real NF-A12x25 frame depth), centred on the
    impeller mid-plane -- unlike the round duct, this leaves open air upstream and downstream
    of the rotor instead of noSlip pipe walls over the whole ~0.7 m domain. A longer rotor
    lengthens the ring to ``impeller span + 2*RING_Z_MARGIN_MM`` so it still fully covers the
    blades. Returns ``(mesh, ring_length_mm)``.

    ``ring_length_mm`` / ``ring_z_center_mm`` override the default nominal length / centring
    (e.g. FAN-01's real 201 mm rig sleeve, centred a few mm off the rotor mid-plane) -- both
    default to ``None``, which keeps the behaviour above unchanged.
    """
    inner_r_mm = rig.duct_radius / MM_TO_M
    outer_r_mm = box_scale * inner_r_mm * math.sqrt(2) + DUCT_OUTER_MARGIN_MM
    span_mm = (rig.impeller_z_max - rig.impeller_z_min) / MM_TO_M
    default_length_mm = max(RING_LENGTH_MM, span_mm + 2.0 * RING_Z_MARGIN_MM)
    length_mm = ring_length_mm if ring_length_mm is not None else default_length_mm
    default_mid_z_mm = 0.5 * (rig.impeller_z_min + rig.impeller_z_max) / MM_TO_M
    mid_z_mm = ring_z_center_mm if ring_z_center_mm is not None else default_mid_z_mm
    mesh = trimesh.creation.annulus(
        r_min=inner_r_mm, r_max=outer_r_mm, height=length_mm, sections=ROUND_DUCT_SECTIONS)
    mesh.apply_translation([0.0, 0.0, mid_z_mm])
    return mesh, length_mm


def check_ring_covers_impeller(ring_mm: trimesh.Trimesh, rig: TestRig) -> None:
    """Refuse a ring whose z-span does not fully cover the impeller's z-range.

    A ring shorter than the blades would solve part of the rotor as an open-air stationary
    wall gap instead of the sealed frame it's meant to model. ``ring_mm`` is in the ring's
    native millimetre scale (before mm->m case scaling); ``rig`` gives the impeller z-range
    in SI metres.
    """
    z0_mm = float(ring_mm.bounds[0, 2])
    z1_mm = float(ring_mm.bounds[1, 2])
    imp_z0_mm = rig.impeller_z_min / MM_TO_M
    imp_z1_mm = rig.impeller_z_max / MM_TO_M
    if z0_mm > imp_z0_mm + _RING_COVER_TOL_MM or z1_mm < imp_z1_mm - _RING_COVER_TOL_MM:
        raise ValueError(
            f"ring z-span [{z0_mm:.2f}, {z1_mm:.2f}] mm does not cover the impeller z-range "
            f"[{imp_z0_mm:.2f}, {imp_z1_mm:.2f}] mm")


def _write_case_meta(
    case_dir: Path,
    rig: TestRig,
    *,
    casing_mesh: trimesh.Trimesh | None,
    H: float,
    duct_shape: str,
    duct_source: str = "none",
    ring_length_mm: float | None = None,
    direction_meta: dict | None = None,
) -> None:
    """Write ``constant/case_meta.json`` with the patch areas and duct shape sanity checks need.

    ``H`` is the half-width (m) of the square background box (``rig.duct_radius`` with no
    casing, else ``box_scale * rig.duct_radius``). ``duct_shape`` is ``"ring"``, ``"round"``
    or ``"square"`` (the ``duct=`` value actually used, or ``"round"`` for a user-given
    ``casing_stl_mm``). ``duct_source`` records where the casing came from: ``"generated"``
    (the in-process ring or round duct), ``"casing_stl"`` (user-given), or ``"none"`` (legacy
    square slip-wall tunnel). ``ring_length_mm`` is recorded only for ``duct_shape=="ring"``.
    """
    has_casing = casing_mesh is not None
    # The bore is the inlet patch only when the casing reaches the inlet face; a short ring (or any
    # casing starting downstream) leaves the full square box face as the inlet.
    casing_at_inlet = False
    plenum = False
    if has_casing:
        casing_z_min = float(casing_mesh.bounds[0, 2])
        casing_z_max = float(casing_mesh.bounds[1, 2])
        casing_at_inlet = casing_z_min <= rig.domain_z_min + _PLENUM_TOL_M
        plenum = casing_at_inlet and casing_z_max < rig.domain_z_max - _PLENUM_TOL_M

    outlet_area = (2.0 * H) ** 2
    inlet_area = math.pi * rig.duct_radius ** 2 if casing_at_inlet else outlet_area

    meta = {
        "duct_shape": duct_shape,
        "duct_source": duct_source,
        "box_half_width_m": H,
        "inlet_area_m2": inlet_area,
        "outlet_area_m2": outlet_area,
        "casing": has_casing,
        "plenum": plenum,
        "duct_radius_m": rig.duct_radius,
        "tip_radius_m": rig.duct_radius - rig.tip_gap,
        "hub_radius_m": rig.hub_radius,
        "rpm": rig.rpm,
        "spin": rig.spin,
        "cfd_version": CFD_VERSION,
    }
    if duct_shape == "ring":
        meta["ring_length_mm"] = ring_length_mm
    if direction_meta:
        meta.update(direction_meta)
    (case_dir / "constant/case_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


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
    box_scale: float | None = None,
    duct: str = "ring",
    ring_length_mm: float | None = None,
    ring_z_center_mm: float | None = None,
    direction_meta: dict | None = None,
) -> Path:
    """Write a ready-to-run OpenFOAM case. ``impeller_stl_mm`` is a millimeter-scale STL.

    For an axial fan, ``impeller_stl_mm`` must be the CFD-oriented copy produced by
    :func:`fansim.cfd.orientation.prepare_axial_cfd` (or ``orient_impeller_for_cfd`` directly),
    not the as-built STL -- the rig's z-bounds and MRF zone are fitted to that oriented copy, and
    passing the as-built mesh instead solves the wrong rotation for the ``rig.spin`` in use.

    ``frame_stl_mm=None`` keeps the impeller-only case (used by validation scripts).
    ``casing_stl_mm`` snaps a user-given duct wall inside an oversized hex; a user-given
    casing always wins over ``duct``.
    ``stator_stl_mm`` may be used alone (replace frame) or together with ``frame_stl_mm``
    for a stator-then-frame stack (frame must sit further downstream).

    ``duct`` selects the background domain shape when ``casing_stl_mm`` is not given:
    ``"ring"`` (default, CFD_VERSION 5) generates a short sealed frame ring in-process (an
    annulus, inner radius ``rig.duct_radius``, outer radius covering the background box's
    corners, axial length :data:`RING_LENGTH_MM` -- 25 mm, the real NF-A12x25 frame depth --
    centred on the impeller mid-plane and lengthened if the rotor is longer) and writes it to
    ``constant/triSurface/casing.stl``; ``"round"`` generates the v4 full-length duct (same
    annulus, spanning the whole domain) kept for comparison -- it adds pipe friction, not
    free air; ``"square"`` keeps the legacy square slip-wall tunnel (half-width =
    ``rig.duct_radius``, corners open around the blade tips at 4 points). Any other value
    raises ``ValueError``. Whenever a casing is present (user-given or generated), its outer
    radius must cover the background box's corners (:func:`check_casing_seals`) or flow can
    bypass the fan; a generated ring must also cover the whole impeller z-range
    (:func:`check_ring_covers_impeller`).

    If ``back_pressure_pa`` is given, use pressure-driven BCs (total-pressure inlet, fixed
    static back-pressure outlet) so the flow rate emerges from the blade design -- this is
    the mode used for optimization, where CFM is an objective. Otherwise use the
    velocity-driven BCs (fixed inlet velocity) used by the fan-curve sweep.

    ``wall_ks_mm`` opt-in sand-grain roughness on printed walls (impeller + frame/stator);
    the circular screening casing stays smooth.

    ``dual_mrf`` when set enables two MRF zones (CROR). Keys (SI metres / rad·s⁻¹):
    ``front_z_min``, ``front_z_max``, ``rear_z_min``, ``rear_z_max``,
    ``omega_front``, ``omega_rear``.

    ``box_scale`` overrides the default hex half-width multiplier (``BOX_SCALE``) applied
    to ``rig.duct_radius`` whenever a casing is present (user-given or generated), e.g. for
    an oversized outlet-chamber (plenum) domain. Ignored when there is no casing.

    ``ring_length_mm`` / ``ring_z_center_mm`` override the generated ring's default axial
    length / z-centre (only meaningful with ``duct="ring"``; ignored otherwise) -- e.g. a real
    rig sleeve that is neither the nominal 25 mm long nor centred exactly on the rotor
    mid-plane. Both default to ``None``, which keeps the existing default ring unchanged.
    """
    if duct not in ("ring", "round", "square"):
        raise ValueError(f"duct must be 'ring', 'round' or 'square', got {duct!r}")

    case_dir = Path(case_dir)
    mesh = mesh or MeshResolution()
    for sub in ("0", "constant/triSurface", "system"):
        (case_dir / sub).mkdir(parents=True, exist_ok=True)

    # --- Load all STLs (still mm-scale) before any scaling or writing ---
    surf = trimesh.load(str(impeller_stl_mm), force="mesh")
    frame_mesh = trimesh.load(str(frame_stl_mm), force="mesh") if frame_stl_mm is not None else None
    stator_mesh = trimesh.load(str(stator_stl_mm), force="mesh") if stator_stl_mm is not None else None

    # --- Casing: user-given STL always wins; otherwise "ring" (default) generates a short
    # sealed frame ring, "round" the v4 full-length duct (both trimesh annuli, no CadQuery);
    # "square" keeps the legacy open-corner tunnel.
    effective_box_scale = box_scale if box_scale is not None else BOX_SCALE
    if casing_stl_mm is not None:
        ring_length_mm = None
        casing_mesh = trimesh.load(str(casing_stl_mm), force="mesh")
        duct_source = "casing_stl"
        duct_shape_meta = "round"
    elif duct == "ring":
        casing_mesh, ring_length_mm = _generate_ring_duct_mesh_mm(
            rig, effective_box_scale,
            ring_length_mm=ring_length_mm, ring_z_center_mm=ring_z_center_mm)
        check_ring_covers_impeller(casing_mesh, rig)
        duct_source = "generated"
        duct_shape_meta = "ring"
    elif duct == "round":
        ring_length_mm = None
        casing_mesh = _generate_round_duct_mesh_mm(rig, effective_box_scale)
        duct_source = "generated"
        duct_shape_meta = "round"
    else:
        ring_length_mm = None
        casing_mesh = None
        duct_source = "none"
        duct_shape_meta = "square"
    has_casing = casing_mesh is not None

    downstream_mm: dict[str, trimesh.Trimesh] = {}
    if frame_mesh is not None:
        downstream_mm["frame"] = frame_mesh
    if stator_mesh is not None:
        downstream_mm["stator"] = stator_mesh
    check_placement(surf, rig, dual_mrf=dual_mrf, downstream_mm=downstream_mm)

    H = effective_box_scale * rig.duct_radius if has_casing else rig.duct_radius
    if has_casing:
        check_casing_seals(casing_mesh, H)

    # --- Scale the impeller STL mm -> m into the case ---
    surf.apply_scale(MM_TO_M)
    rear_surf = None
    if dual_mrf is not None:
        # CROR: the two rotors spin opposite ways, so their reaction torques cancel in a single
        # patch's net moment and power = |net Mz| * omega undercounts the shaft power (Audit #7).
        # Split the surface at the inter-rotor gap: "impeller" = upstream rotor, "impellerRear"
        # = downstream rotor, each with its own forces monitor; both rotate with their MRF zone.
        surf, rear_surf = split_dual_rotor_surface(surf, dual_mrf)
        rear_surf.export(str(case_dir / "constant/triSurface/impellerRear.stl"))
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

    zmin, zmax = rig.domain_z_min, rig.domain_z_max
    nx = max(10, round(2 * H / mesh.base_cell))
    nz = max(20, round((zmax - zmin) / mesh.base_cell))
    write_int = max(1, n_iters // 2)  # field snapshots (kept small via purgeWrite)
    fo_int = max(1, n_iters // 40)  # fine function-object sampling for convergence tracking

    frame = (_extra_wall_snippets("frame", mesh.feature_level, mesh.surf_min, mesh.surf_max)
             if frame_stl_mm is not None else _empty_wall_snippets())
    casing = (_extra_wall_snippets("casing", mesh.feature_level, mesh.surf_min, mesh.surf_max)
              if has_casing else _empty_wall_snippets())
    stator = (_extra_wall_snippets("stator", mesh.feature_level, mesh.surf_min, mesh.surf_max)
              if stator_stl_mm is not None else _empty_wall_snippets())

    ks_m = wall_ks_m(wall_ks_mm)
    impeller_nut = nut_wall_bc("impeller", wall_ks_m=ks_m)
    if rear_surf is not None:
        rear = _extra_wall_snippets("impellerRear", mesh.feature_level, mesh.surf_min,
                                    mesh.surf_max, ks_m=ks_m)
        # Same wall treatment as "impeller" (noSlip in the MRF frame = rotating wall). Ride along
        # in the stator text slots, but NOT in PATCH: nonRotatingPatches must not list it.
        for key in ("GEOM", "FEAT", "SURF", "EXTRACT", "U", "P", "NUT"):
            stator[key] = rear[key] + stator[key]
        stator["ROTOR2"] = "impellerRear"
    # Printed solids get rough when ks is set; casing is a duct artifact → always smooth.
    if ks_m > 0.0:
        if frame_stl_mm is not None:
            frame["NUT"] = nut_wall_bc("frame", wall_ks_m=ks_m)
        if stator_stl_mm is not None:
            stator["NUT"] = nut_wall_bc("stator", wall_ks_m=ks_m)

    if has_casing:
        locx = 0.35 * rig.duct_radius
        locy = 0.0
        locz = rig.domain_z_min + 0.25 * rig.inlet_length
        if duct_shape_meta == "ring" and ring_length_mm is not None:
            # casing_mesh is still mm-scale here (scaled to m further below): use its own
            # z-bounds rather than recomputing from the rotor mid-plane, so this stays correct
            # under a ring_z_center_mm override that decouples the ring from that mid-plane.
            ring_z0 = float(casing_mesh.bounds[0, 2]) * MM_TO_M
            ring_z1 = float(casing_mesh.bounds[1, 2]) * MM_TO_M
            if ring_z0 - _PLACEMENT_TOL_M <= locz <= ring_z1 + _PLACEMENT_TOL_M:
                raise ValueError(
                    f"location-in-mesh z={locz * 1e3:.2f} mm falls inside the ring z-range "
                    f"[{ring_z0 * 1e3:.2f}, {ring_z1 * 1e3:.2f}] mm -- it must be in the "
                    "fluid upstream of the ring, not inside the ring solid")
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
    if rear_surf is not None:
        add_rear_forces(case_dir / "system/controlDict")
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

    if direction_meta is None:
        # prepare_axial_cfd leaves its decision next to the oriented STL it returns.
        dm_path = Path(impeller_stl_mm).parent / "direction_meta.json"
        if dm_path.is_file():
            direction_meta = json.loads(dm_path.read_text(encoding="utf-8"))
    _write_case_meta(case_dir, rig, casing_mesh=casing_mesh, H=H, duct_shape=duct_shape_meta,
                     duct_source=duct_source, ring_length_mm=ring_length_mm,
                     direction_meta=direction_meta)

    return case_dir


MESH_PIPELINE = [
    "surfaceFeatureExtract",
    "blockMesh",
    "snappyHexMesh -overwrite",
    "topoSet",
    "renumberMesh -overwrite",
    "checkMesh -allTopology",
]


# Clear stale decomposition, function-object output AND reconstructed time dirs (everything numeric
# but 0/) before a fresh solve. A case folder can be reused (re-Assess of a saved design); an old
# reconstructed time dir left at the case root belongs to an earlier mesh and was read by the
# airflow view against the new one ("mesh and field do not match", 2026-10-07).
CLEAN_BEFORE_SOLVE = (
    "rm -rf processor* postProcessing; "
    "for d in [0123456789]*; do case \"$d\" in 0|*[!0123456789.e+-]*) ;; "
    "*) if [ -d \"$d\" ]; then rm -rf \"$d\"; fi;; esac; done"
)


def mesh_pipeline(n_procs: int = 1) -> list[str]:
    """Meshing commands; ``n_procs`` > 1 runs snappyHexMesh in parallel.

    Serial snappy was the single biggest fixed cost of an Assess (~7 of ~9 min of meshing on a
    1M-cell mesh, one core busy). The parallel path decomposes the background block mesh,
    snaps on ``n_procs`` ranks, then reconstructs to ``constant/polyMesh`` and deletes the
    processor dirs, so topoSet / renumberMesh / checkMesh and every solve downstream see the
    same single-region case as before. The parallel mesh is not bit-identical to the serial
    one (load balancing changes refinement order), so it is opt-in per caller and was A/B'd on
    Stock before becoming the Assess default (docs/validation/audits/2026-10-07-assess-speed.md).
    """
    if not n_procs or n_procs <= 1:
        return list(MESH_PIPELINE)
    mpi = f"mpirun --allow-run-as-root --oversubscribe -np {int(n_procs)}"
    return [
        "surfaceFeatureExtract",
        "blockMesh",
        "decomposePar -force -no-fields",
        f"{mpi} snappyHexMesh -parallel -overwrite",
        "reconstructParMesh -constant",
        "rm -rf processor*",
        "topoSet",
        "renumberMesh -overwrite",
        "checkMesh -allTopology",
    ]


def run_mesh(runner, n_procs: int = 1) -> None:
    """Run the meshing pipeline in the container (serial snappy unless ``n_procs`` > 1)."""
    for cmd in mesh_pipeline(n_procs):
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
    runner.run(CLEAN_BEFORE_SOLVE, check=False)
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


_PIMPLE_BLOCK = (
    "PIMPLE\n"
    "{\n"
    "    nOuterCorrectors 1;\n"
    "    nCorrectors     2;\n"
    "    nNonOrthogonalCorrectors 1;\n"
    "}\n"
)


def _pimple_block_with_outer_correctors(n_outer: int) -> str:
    """PIMPLE block with ``n_outer`` outer correctors, residual control and under-relaxation.

    Lets ``apply_urans_transient`` run at larger Courant numbers than the single-pass
    (``nOuterCorrectors 1``, PISO-like) default by iterating the outer PIMPLE loop to
    convergence each time step -- ``outerCorrectorResidualControl`` stops the loop early
    once p/U/k/omega residuals fall below 1e-3, and ``relaxationFactors`` stabilizes the
    now-iterated equations the way a steady SIMPLE solve would.
    """
    return (
        "PIMPLE\n"
        "{\n"
        f"    nOuterCorrectors {n_outer};\n"
        "    nCorrectors     2;\n"
        "    nNonOrthogonalCorrectors 1;\n"
        "    outerCorrectorResidualControl\n"
        "    {\n"
        "        p { tolerance 1e-3; relTol 0; }\n"
        "        U { tolerance 1e-3; relTol 0; }\n"
        "        k { tolerance 1e-3; relTol 0; }\n"
        "        omega { tolerance 1e-3; relTol 0; }\n"
        "    }\n"
        "}\n"
        "\n"
        "relaxationFactors\n"
        "{\n"
        "    equations\n"
        "    {\n"
        '        ".*"      0.7;\n'
        '        ".*Final" 1;\n'
        "    }\n"
        "    fields\n"
        "    {\n"
        "        p      0.3;\n"
        "        pFinal 1;\n"
        "    }\n"
        "}\n"
    )


def apply_urans_transient(
    case_dir: str | Path,
    *,
    end_time: float,
    delta_t: float = 1e-5,
    max_co: float = 1.5,
    fo_interval: int = 1,
    n_outer: int = 1,
) -> Path:
    """Overlay frozen-rotor URANS (pimpleFoam) on an existing steady-RAS case.

    Keeps the same k-omega SST RAS model and the same metric function objects
    (forces, outletFlow, inletP, outletP) as the steady case, but switches the
    application to pimpleFoam with an adjustable time step. Does not remesh and
    leaves ``constant/turbulenceProperties`` as the steady RAS file build_case wrote.

    ``n_outer`` (default 1, byte-identical to the original single-pass PIMPLE block) sets
    ``nOuterCorrectors``; values > 1 add ``outerCorrectorResidualControl`` and
    ``relaxationFactors`` (see :func:`_pimple_block_with_outer_correctors`) so the outer
    loop can absorb a larger ``max_co`` than a single-pass PISO-like step would tolerate.
    """
    case_dir = Path(case_dir)

    write_interval = end_time / 10.0
    cd = T.render(T.CONTROL_DICT, {
        "HEADER": _header("dictionary", "controlDict"),
        "ENDTIME": end_time,
        "WRITEINT": write_interval,
        "FOINT": fo_interval,
        "RHO": RHO_AIR,
    })

    app_old = "application     simpleFoam;"
    app_new = "application     pimpleFoam;"
    assert cd.count(app_old) == 1, "expected exactly one steady application line"
    cd = cd.replace(app_old, app_new)

    dt_old = "deltaT          1;"
    dt_new = f"deltaT          {delta_t};"
    assert cd.count(dt_old) == 1, "expected exactly one steady deltaT line"
    cd = cd.replace(dt_old, dt_new)

    wc_old = f"writeControl    timeStep;\nwriteInterval   {write_interval};"
    wc_new = f"writeControl    adjustableRunTime;\nwriteInterval   {write_interval};"
    assert cd.count(wc_old) == 1, "expected exactly one steady writeControl/writeInterval pair"
    cd = cd.replace(wc_old, wc_new)

    adjust_lines = f"adjustTimeStep  yes;\nmaxCo           {max_co};\n"
    assert cd.count(dt_new) == 1
    cd = cd.replace(dt_new, dt_new + "\n" + adjust_lines.rstrip("\n"), 1)

    (case_dir / "system").mkdir(parents=True, exist_ok=True)
    (case_dir / "system/controlDict").write_text(cd, encoding="utf-8")

    _write(case_dir / "system/fvSchemes", T.DES_FV_SCHEMES, "dictionary", "fvSchemes", {})

    sol = T.render(T.DES_FV_SOLUTION, {"HEADER": _header("dictionary", "fvSolution")})
    if n_outer > 1:
        assert sol.count(_PIMPLE_BLOCK) == 1, "expected exactly one steady PIMPLE block"
        sol = sol.replace(_PIMPLE_BLOCK, _pimple_block_with_outer_correctors(n_outer), 1)
    (case_dir / "system/fvSolution").write_text(sol, encoding="utf-8")

    return case_dir


def run_solve_urans(runner, n_procs: int = 8) -> None:
    """URANS (frozen-rotor MRF)."""
    runner.run(CLEAN_BEFORE_SOLVE, check=False)
    if n_procs and n_procs > 1:
        runner.run("decomposePar -force")
        mpi = f"mpirun --allow-run-as-root --oversubscribe -np {n_procs}"
        runner.run(f"{mpi} potentialFoam -parallel -initialiseUBCs", check=False)
        runner.run(f"{mpi} pimpleFoam -parallel")
    else:
        runner.run("potentialFoam -initialiseUBCs", check=False)
        runner.run("pimpleFoam")


def run_solve_des(runner, n_procs: int = 8, reconstruct: bool = False) -> None:
    """Solve with pimpleFoam (DES transient), parallel via MPI when ``n_procs`` > 1."""
    runner.run(CLEAN_BEFORE_SOLVE, check=False)
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
