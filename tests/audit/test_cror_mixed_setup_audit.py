"""Audit #7: CROR + mixed-flow (+ volute) CFD setup -- rotor direction, MRF placement, LE/TE.

Geometry only (CadQuery/trimesh); no CFD, no Docker. Report:
docs/validation/audits/2026-10-01-audit-07-cror-mixed-setup.md
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import cadquery as cq
import numpy as np
import pytest
import trimesh

from fansim.audit.direction import prove_direction
from fansim.cfd.domain import MM_TO_M
from fansim.cfd.openfoam_case import check_placement
from fansim.cfd.orientation import fit_rig_to_stl, flip_about_x, prepare_axial_cfd
from fansim.centrifugal.evaluate import rig_for_mixed_flow
from fansim.centrifugal.geometry import MixedFlowParams, export_mixed_flow_stl
from fansim.cror.evaluate import (
    cfd_dual_mrf_dict,
    check_cror_blades_in_zones,
    prepare_cror_cfd,
    rig_for_cror,
)
from fansim.cror.geometry import CrorParams, _hub_cylinder, cror_axial_layout_mm, export_cror_stl
from fansim.geometry.blade import build_blade_solid
from fansim.geometry.export import export_stl
from fansim.validation.section_compare import measure_sections
from fansim.volute.domain import VOLUTE_SPIN, domain_for_volute
from fansim.volute.geometry import (
    VoluteParams,
    build_radial_impeller,
    scroll_outer_radius_mm,
    volute_radii_mm,
)

RADII = (0.55, 0.75, 0.95)


def _rotor_mesh(bp, dz: float, path: Path) -> trimesh.Trimesh:
    """One CROR rotor (hub + blades) exactly as ``build_cror`` places it, alone."""
    blade = build_blade_solid(deepcopy(bp))
    pat = [blade.rotate((0, 0, 0), (0, 0, 1), k * 360.0 / bp.n_blades).translate((0, 0, dz))
           for k in range(bp.n_blades)]
    hub = _hub_cylinder(bp, -6.7 + dz, 6.7 + dz)
    sol = hub.fuse(*pat).clean().Solids()
    export_stl(cq.Workplane(obj=sol[0]), path)
    return trimesh.load(str(path), force="mesh")


@pytest.fixture(scope="module")
def cror(tmp_path_factory):
    d = tmp_path_factory.mktemp("cror")
    p = CrorParams()
    lay = cror_axial_layout_mm(p)
    front = _rotor_mesh(p.front, 0.0, d / "front.stl")
    rear = _rotor_mesh(p.rear, lay["z_rear_mm"], d / "rear.stl")
    return p, lay, front, rear, d


# ---------------------------------------------------------------- cror.direction
def test_cror_rotors_as_built_are_mirror_pair_both_pumping_minus_z(cror):
    _, _, front, rear, _ = cror
    pf, pr = prove_direction(front), prove_direction(rear)
    assert pf.verdict == "CONCLUSIVE" and pr.verdict == "CONCLUSIVE"
    assert (pf.omega_sign, pf.pump_sign) == (1, -1)   # Stock handedness
    assert (pr.omega_sign, pr.pump_sign) == (-1, -1)  # counter-rotating, same delivery side


def test_cror_cfd_orientation_each_rotor_turns_its_zone_omega(cror):
    """Flipped CFD copy: upstream rotor (former rear) designed +omega, downstream -omega, both
    pumping +Z, matching the signs ``cfd_dual_mrf_dict`` writes for spin -1."""
    p, _, front, rear, _ = cror
    rig = rig_for_cror(p, tip_gap_mm=0.5, casing_id_mm=120.0, rpm=2000.0)
    assert rig.spin == -1 and rig.omega_signed < 0
    dm = cfd_dual_mrf_dict(p, rig.omega_signed)
    up, down = flip_about_x(rear), flip_about_x(front)
    pu, pd = prove_direction(up), prove_direction(down)
    assert pu.pump_sign == +1 and pd.pump_sign == +1
    assert np.sign(dm["omega_front"]) == pu.omega_sign      # upstream zone
    assert np.sign(dm["omega_rear"]) == pd.omega_sign       # downstream zone
    assert dm["omega_front"] == pytest.approx(-dm["omega_rear"])
    # and the upstream rotor really sits in the upstream (front_*) zone
    assert up.bounds[1, 2] * MM_TO_M <= dm["front_z_max"] + 1e-6 + 1e-3  # hub stub may pass band
    assert down.bounds[0, 2] * MM_TO_M >= dm["rear_z_min"] - 1e-3


# ------------------------------------------------- cror LE/TE (roadmap claim, blade.py)
def test_cror_rear_section_is_exact_mirror_of_front_le_leads(cror):
    """The rear (negative stagger, keeps airfoil-frame sign) is the t -> -t mirror of the front:
    equal chord/stagger/camber_pos, opposite LE angle, LE on the same (+z, upstream-as-built)
    side, and each rotor's LE is the leading edge for ITS omega (measure_sections orients LE by
    omega_sign)."""
    p, lay, front, rear, d = cror
    mf = measure_sections(d / "front.stl", RADII)
    mr = measure_sections(d / "rear.stl", RADII)
    for a, b in zip(mf, mr):
        assert a["omega_sign"] == 1 and b["omega_sign"] == -1
        assert a["chord_mm"] == pytest.approx(b["chord_mm"], rel=0.02)
        assert a["stagger_deg"] == pytest.approx(b["stagger_deg"], abs=0.5)
        assert a["camber_pos"] == pytest.approx(b["camber_pos"], abs=0.02)
        assert a["camber_pos"] == pytest.approx(0.4, abs=0.06)   # recipe 0.4
        assert a["le_theta_deg"] == pytest.approx(-b["le_theta_deg"], abs=1.0)  # mirror
        assert a["le_z_mm"] > 0.0                        # LE on the +z face (front)
        assert b["le_z_mm"] - lay["z_rear_mm"] > 0.0     # same face on the rear
        assert a["le_z_mm"] == pytest.approx(b["le_z_mm"] - lay["z_rear_mm"], abs=0.5)


# ---------------------------------------------------------------- cror.placement
def test_cror_prepare_cfd_fits_zones_to_flipped_stl(tmp_path):
    p = CrorParams()
    stl = export_cror_stl(p, tmp_path / "impeller.stl")
    rig = rig_for_cror(p, tip_gap_mm=0.5, casing_id_mm=120.0, rpm=2000.0)
    ostl, rig2, dm = prepare_cror_cfd(p, stl, rig, tmp_path)
    mesh = trimesh.load(str(ostl), force="mesh")
    src = trimesh.load(str(stl), force="mesh")
    # flipped: as-built z-range mirrored
    assert mesh.bounds[0, 2] == pytest.approx(-src.bounds[1, 2], abs=1e-3)
    assert mesh.bounds[1, 2] == pytest.approx(-src.bounds[0, 2], abs=1e-3)
    check_placement(mesh, rig2, dual_mrf=dm)              # envelope inside the MRF zones
    check_cror_blades_in_zones(ostl, dm, p.front.hub_radius)  # every blade vertex in a zone
    assert dm["front_z_max"] < dm["rear_z_min"]           # zones do not overlap
    assert dm["omega_front"] > 0 > dm["omega_rear"]       # spin -1: downstream rotor negative
    meta = json.loads((tmp_path / "direction_meta.json").read_text())
    assert meta["orientation"] == "flipped" and meta["spin"] == -1


def test_cror_blade_outside_zones_is_refused(tmp_path):
    p = CrorParams()
    stl = export_cror_stl(p, tmp_path / "impeller.stl")
    rig = rig_for_cror(p, tip_gap_mm=0.5, casing_id_mm=120.0, rpm=2000.0)
    ostl, _, dm = prepare_cror_cfd(p, stl, rig, tmp_path)
    bad = {**dm, "rear_z_max": dm["rear_z_max"] - 4e-3}   # chop 4 mm off the downstream zone
    with pytest.raises(ValueError, match="outside both MRF zones"):
        check_cror_blades_in_zones(ostl, bad, p.front.hub_radius)


# ---------------------------------------------------------------- mixed.direction
@pytest.fixture(scope="module")
def mixed(tmp_path_factory):
    d = tmp_path_factory.mktemp("mixed")
    p = MixedFlowParams()
    stl = export_mixed_flow_stl(p, d / "impeller.stl")
    return p, Path(stl), d


def test_mixed_as_built_is_axial_handedness_proof_conclusive(mixed):
    _, stl, _ = mixed
    pr = prove_direction(trimesh.load(str(stl), force="mesh"))
    assert pr.verdict == "CONCLUSIVE"     # diagonal thin blades: the proof does apply
    assert (pr.omega_sign, pr.pump_sign) == (1, -1)


def test_mixed_cfd_is_flipped_with_eye_upstream(mixed):
    p, stl, d = mixed
    rig = rig_for_mixed_flow(p, tip_gap_mm=1.0, casing_id_mm=110.0, rpm=2000.0)
    ostl, rig2 = prepare_axial_cfd(stl, rig, d, source="builder")
    m = trimesh.load(str(ostl), force="mesh")
    pr = prove_direction(m)
    assert (pr.omega_sign, pr.pump_sign) == (-1, +1)   # spin -1 pumping the +Z duct
    assert rig2.spin == -1
    # conical hub: small eye radius must face the -Z inlet, large back-hub radius the +Z side
    v = m.vertices
    r = np.hypot(v[:, 0], v[:, 1])
    hub = r < p.r_back_mm + 0.5
    zlo, zhi = m.bounds[0, 2], m.bounds[1, 2]
    lo = r[hub & (v[:, 2] < zlo + 2.0)].max()
    hi = r[hub & (v[:, 2] > zhi - 2.0)].max()
    assert lo < hi


# ---------------------------------------------------------------- mixed.placement
def test_mixed_analytic_mrf_undersizes_and_prepare_fixes(tmp_path):
    p = MixedFlowParams(z_span_mm=10.0)
    stl = export_mixed_flow_stl(p, tmp_path / "impeller.stl")
    mesh = trimesh.load(str(stl), force="mesh")
    rig = rig_for_mixed_flow(p, tip_gap_mm=1.0, casing_id_mm=110.0, rpm=2000.0)
    with pytest.raises(ValueError, match="not inside the MRF zone"):
        check_placement(mesh, rig)                       # analytic +-z_span/2 + 2 mm
    ostl, rig2 = prepare_axial_cfd(stl, rig, tmp_path, source="builder")
    check_placement(trimesh.load(str(ostl), force="mesh"), rig2)


def test_mixed_default_mrf_fitted_to_stl(mixed):
    p, stl, d = mixed
    rig = rig_for_mixed_flow(p, tip_gap_mm=1.0, casing_id_mm=110.0, rpm=2000.0)
    ostl, rig2 = prepare_axial_cfd(stl, rig, d, source="builder")
    m = trimesh.load(str(ostl), force="mesh")
    assert rig2.mrf_z_min <= m.bounds[0, 2] * MM_TO_M - 1.9e-3
    assert rig2.mrf_z_max >= m.bounds[1, 2] * MM_TO_M + 1.9e-3
    assert rig2.impeller_z_min == pytest.approx(m.bounds[0, 2] * MM_TO_M)
    assert fit_rig_to_stl(rig, ostl).mrf_z_max == pytest.approx(rig2.mrf_z_max)


# ---------------------------------------------------------------- volute (radial)
def test_volute_impeller_direction_proof_is_inconclusive_so_scroll_sets_spin(tmp_path):
    """Flat radial blades have no concave side: the mesh-only proof cannot (and must not) decide."""
    p = VoluteParams()
    stl = tmp_path / "imp.stl"
    export_stl(build_radial_impeller(p), stl)
    pr = prove_direction(trimesh.load(str(stl), force="mesh"))
    assert pr.verdict == "INCONCLUSIVE"


def test_volute_spin_follows_scroll_growth():
    p = VoluteParams()
    rad = volute_radii_mm(p)
    # outer wall grows with +theta (narrow at the tongue, widest at 2pi next to the +X stub)
    assert scroll_outer_radius_mm(p, 0.1) < scroll_outer_radius_mm(p, 6.0)
    assert rad["r_out_exit_mm"] > rad["r_out_tongue_mm"]
    d = domain_for_volute(p)
    assert VOLUTE_SPIN == +1 and d.omega_signed > 0   # flow collected toward +theta


def test_volute_mrf_contains_impeller():
    p = VoluteParams()
    d = domain_for_volute(p)
    rad = volute_radii_mm(p)
    assert d.mrf_z_min <= rad["z0_mm"] * MM_TO_M - 1.9e-3
    assert d.mrf_z_max >= rad["z1_mm"] * MM_TO_M + 1.9e-3
    assert d.mrf_radius > p.r_tip_mm * MM_TO_M
    assert d.mrf_radius < (p.r_tip_mm + p.volute_clearance_mm) * MM_TO_M  # inside the scroll bore
