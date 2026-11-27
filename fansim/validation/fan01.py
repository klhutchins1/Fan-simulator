"""FAN-01 benchmark: isolate the rotor from the full ISO 5801 test-rig IGES assembly.

``validation/reference/fan01/cad_model/cad_model.igs`` is the whole test rig (duct, inlet
grille/flange, settling chamber, rotor) exported as loose IGES surfaces (no solids, no
assembly/level structure survives the export -- every face comes back as a bare
``GeomAbs_BSplineSurface`` with no shared topology between faces, even where two faces are
geometrically coincident). So the rotor cannot be found via IGES entity levels, labels, or
XDE named sub-shapes: there is nothing there to read.

Instead this module isolates it geometrically:

1. Tessellate every face and cluster them into connected parts by 3-D point proximity
   (``tol_mm`` -- far tighter than the 2.5 mm tip-to-casing clearance, so the spinning rotor
   and the stationary casing/duct around it -- which are geometrically close but never
   touching -- fall into different clusters). This recovers "solids" that the IGES file
   itself does not encode as solids.
2. For each cluster with a plausible face count, fit a local axis by PCA: a disk-like part
   (large radial extent, short axial extent -- true of any fan rotor or its casing) has its
   *smallest*-variance principal direction along the rotation axis.
3. Keep only clusters that contain a group of ``expected_blade_count`` faces of matching area
   (the blade surfaces) spanning most of the cluster's radial extent -- i.e. an actual set of
   blades, not a bolt circle or a ring of rivet holes (those also cluster into same-sized
   groups, but at fixed small area and a narrow radial band). Exactly one cluster should
   survive; if zero or more than one do, extraction stops rather than guessing.

The surviving cluster's faces are sewn (``BRepBuilderAPI_Sewing``) and closed into a solid,
then rotated (a proper rotation only -- never a mirror, so the exported mesh keeps the
original part's handedness) so the fitted axis maps to +Z, and translated so the axis passes
through the origin with the rotor's axial mid-plane at z=0 -- the repo's STL convention.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path

import networkx as nx
import numpy as np
import trimesh
from scipy.spatial import cKDTree

from fansim.audit.direction import prove_direction
from fansim.cfd.domain import MM_TO_M, TestRig
from fansim.cfd.orientation import orientation_from_proof

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_IGS = ROOT / "validation" / "reference" / "fan01" / "cad_model" / "cad_model.igs"
DEFAULT_OUT_STL = ROOT / "validation" / "reference" / "fan01" / "fan01_rotor.stl"
DEFAULT_CHARACTERISTIC_CSV = ROOT / "validation" / "reference" / "fan01" / "characteristic.csv"

FAN01_DUCT_RADIUS_M = 0.250  # casing sleeve inner radius (brief: rig duct)
FAN01_MRF_MARGIN_MM = 5.0
# Dataset paper Table 2: tip clearance 2.5 mm, fan diameter 495 mm → tip radius 247.5 mm.
# Extracted STL 99.5th-percentile tip is ~247.9 mm → duct−tip ≈ 2.11 mm (§19.13). The
# geometric clearance in the mesh follows the STL; TestRig.tip_gap defaults to the
# published value for tip-speed / reporting. Pass tip_gap_source="measured" to use
# duct − STL tip instead.
FAN01_TIP_CLEARANCE_M = 0.0025
FAN01_TIP_RADIUS_MM = 247.5

MIN_CLUSTER_FACES = 20
MAX_CLUSTER_FACES = 500
AREA_GROUP_TOL = 0.03  # relative area tolerance for "matching" blade faces


def _read_iges_faces(igs_path: Path):
    """Return the list of TopoDS_Face in the IGES file, in Explorer order."""
    from OCP.IGESControl import IGESControl_Reader
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS

    reader = IGESControl_Reader()
    status = reader.ReadFile(str(igs_path))
    from OCP.IFSelect import IFSelect_RetDone

    if status != IFSelect_RetDone:
        raise ValueError(f"failed to read IGES file: {igs_path}")
    reader.TransferRoots()
    shape = reader.OneShape()

    faces = []
    exp = TopExp_Explorer(shape, TopAbs_FACE)
    while exp.More():
        faces.append(TopoDS.Face_s(exp.Current()))
        exp.Next()
    return faces


def _tessellate(faces, linear_deflection: float = 0.5):
    """Mesh every face and return per-face (points Nx3, area) via BRepMesh + GProp."""
    from OCP.BRep import BRep_Tool
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    from OCP.TopLoc import TopLoc_Location

    # BRepMesh_IncrementalMesh needs a compound of all faces to mesh in one pass.
    from OCP.BRep import BRep_Builder
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.TopoDS import TopoDS_Compound

    builder = BRep_Builder()
    compound = TopoDS_Compound()
    builder.MakeCompound(compound)
    for f in faces:
        builder.Add(compound, f)
    BRepMesh_IncrementalMesh(compound, linear_deflection, False, 0.5, True)

    out = []
    for f in faces:
        loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(f, loc)
        if tri is None:
            out.append((np.zeros((0, 3)), 0.0))
            continue
        trsf = loc.Transformation()
        n = tri.NbNodes()
        pts = np.zeros((n, 3))
        for k in range(1, n + 1):
            p = tri.Node(k).Transformed(trsf)
            pts[k - 1] = (p.X(), p.Y(), p.Z())
        gp = GProp_GProps()
        BRepGProp.SurfaceProperties_s(f, gp)
        out.append((pts, gp.Mass()))
    return out


def _cluster_by_proximity(face_points: list[np.ndarray], tol_mm: float) -> list[list[int]]:
    """Group face indices into connected components by point-proximity (< tol_mm)."""
    all_pts, tags = [], []
    for i, pts in enumerate(face_points):
        if len(pts) == 0:
            continue
        all_pts.append(pts)
        tags.append(np.full(len(pts), i, dtype=int))
    all_pts = np.vstack(all_pts)
    tags = np.concatenate(tags)

    tree = cKDTree(all_pts)
    pairs = tree.query_pairs(r=tol_mm, output_type="ndarray")
    fa, fb = tags[pairs[:, 0]], tags[pairs[:, 1]]

    g = nx.Graph()
    g.add_nodes_from(range(len(face_points)))
    g.add_edges_from(zip(fa.tolist(), fb.tolist()))
    return [sorted(c) for c in nx.connected_components(g)]


def _fit_axis(points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """PCA axis fit for a disk-like part: smallest-variance direction = rotation axis."""
    mean = points.mean(axis=0)
    cov = np.cov((points - mean).T)
    w, v = np.linalg.eigh(cov)
    axis = v[:, int(np.argmin(w))]
    return mean, axis / np.linalg.norm(axis)


def _radial_distance(points: np.ndarray, mean: np.ndarray, axis: np.ndarray) -> np.ndarray:
    d = points - mean
    ax_comp = d @ axis
    perp = d - np.outer(ax_comp, axis)
    return np.linalg.norm(perp, axis=1)


def _find_blade_groups(areas: np.ndarray, expected_blade_count: int) -> list[np.ndarray]:
    """All groups of `expected_blade_count` near-equal areas, largest area first.

    A cluster can contain several distinct groups of exactly N matching-area faces --
    small fillets or rivet holes just as often come in matched sets of N as blade
    surfaces do. Returning all of them (by descending area) lets the caller test each
    against a physical criterion (radial span) instead of taking whichever the area
    sort happens to hit first, which was previously always the *smallest*-area group.
    """
    order = np.argsort(areas)
    sorted_areas = areas[order]
    groups = []
    i = 0
    n = len(areas)
    while i < n:
        j = i
        while j < n and sorted_areas[j] < sorted_areas[i] * (1 + AREA_GROUP_TOL) + 1e-9:
            j += 1
        if j - i == expected_blade_count:
            groups.append(order[i:j])
        i = j
    groups.sort(key=lambda g: -areas[g].mean())
    return groups


def _rotation_to_z(axis: np.ndarray) -> np.ndarray:
    """Proper (det=+1) rotation matrix mapping `axis` to +Z, via Rodrigues' formula."""
    target = np.array([0.0, 0.0, 1.0])
    if axis[1] < 0:  # keep the mapping stable/deterministic: prefer +axis ~ +Y source
        axis = -axis
    v = np.cross(axis, target)
    s = np.linalg.norm(v)
    c = float(np.dot(axis, target))
    if s < 1e-12:
        return np.eye(3) if c > 0 else np.diag([1.0, -1.0, -1.0])
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx * ((1 - c) / (s**2))


def find_rotor_faces(
    igs_path: str | Path,
    expected_blade_count: int = 9,
    tol_mm: float = 0.02,
    expected_tip_radius_mm: float | None = 245.0,
    tip_radius_tol_frac: float = 0.3,
) -> tuple[list, np.ndarray, np.ndarray]:
    """Return (rotor TopoDS_Face list, axis point, axis direction) found geometrically.

    A set of N (``expected_blade_count``) matching-area faces spanning a wide radial band
    is necessary but not sufficient for "these are blades" -- a symmetric perforated grille
    panel (e.g. an inlet/outlet screen) can produce the same signature by coincidence. When
    ``expected_tip_radius_mm`` is given (the datasheet/spec value, known independently of the
    CAD), candidates whose fitted tip radius misses it by more than
    ``tip_radius_tol_frac`` are dropped first -- this is what actually resolves that
    ambiguity for FAN-01, where two large grille-panel clusters (tip radius ~478 mm) also
    pass the blade-group/radial-span test and must be excluded by the known ~245 mm rotor
    radius. Pass ``expected_tip_radius_mm=None`` to skip this and rely on shape alone.

    Raises ValueError if zero or more than one cluster looks like a bladed rotor -- this is
    deliberate: guessing which of several candidates is the real rotor is worse than stopping.
    """
    igs_path = Path(igs_path)
    faces = _read_iges_faces(igs_path)
    tessellated = _tessellate(faces)
    face_points = [t[0] for t in tessellated]
    face_areas = np.array([t[1] for t in tessellated])

    clusters = _cluster_by_proximity(face_points, tol_mm)
    candidates = []
    for cluster in clusters:
        if not (MIN_CLUSTER_FACES <= len(cluster) <= MAX_CLUSTER_FACES):
            continue
        pts = np.vstack([face_points[i] for i in cluster if len(face_points[i])])
        if len(pts) == 0:
            continue
        mean, axis = _fit_axis(pts)
        r = _radial_distance(pts, mean, axis)
        tip_r = float(np.percentile(r, 99.5))
        if expected_tip_radius_mm is not None:
            lo = expected_tip_radius_mm * (1 - tip_radius_tol_frac)
            hi = expected_tip_radius_mm * (1 + tip_radius_tol_frac)
            if not (lo <= tip_r <= hi):
                continue

        areas = face_areas[cluster]
        for blade_group in _find_blade_groups(areas, expected_blade_count):
            blade_face_idx = [cluster[k] for k in blade_group]
            blade_pts = np.vstack([face_points[i] for i in blade_face_idx])
            blade_r = _radial_distance(blade_pts, mean, axis)
            # blade faces should span a good chunk of the cluster's radial extent (real
            # blades, not a small-area bolt/rivet ring sitting at one fixed radius)
            if (blade_r.max() - blade_r.min()) >= 0.3 * tip_r:
                candidates.append((cluster, mean, axis, tip_r))
                break

    if len(candidates) == 0:
        raise ValueError(
            "no cluster in the IGES assembly looks like a bladed rotor "
            f"(expected_blade_count={expected_blade_count}); found {len(clusters)} "
            "clusters total -- stopping rather than guessing"
        )
    if len(candidates) > 1:
        sizes = [(len(c), round(t, 1)) for c, _, _, t in candidates]
        raise ValueError(
            f"{len(candidates)} clusters all look like a bladed rotor (n_faces, tip_radius_mm)"
            f" = {sizes} -- stopping rather than guessing which one is real"
        )

    cluster, mean, axis, _tip_r = candidates[0]
    return [faces[i] for i in cluster], mean, axis


def _sew_to_solid(rotor_faces: list):
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeSolid, BRepBuilderAPI_Sewing
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.ShapeFix import ShapeFix_Solid
    from OCP.TopAbs import TopAbs_SHELL
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopoDS import TopoDS

    sew = BRepBuilderAPI_Sewing(1e-3)
    for f in rotor_faces:
        sew.Add(f)
    sew.Perform()
    sewed = sew.SewedShape()

    shells = []
    exp = TopExp_Explorer(sewed, TopAbs_SHELL)
    while exp.More():
        shells.append(TopoDS.Shell_s(exp.Current()))
        exp.Next()
    if not shells:
        raise ValueError("sewing produced no closed shell from the rotor faces")

    mk = BRepBuilderAPI_MakeSolid()
    for sh in shells:
        mk.Add(sh)
    solid = mk.Solid()
    fixer = ShapeFix_Solid(solid)
    fixer.Perform()
    solid = fixer.Solid()
    if not BRepCheck_Analyzer(solid).IsValid():
        raise ValueError("sewn rotor solid failed BRepCheck_Analyzer validity check")
    return solid


def _transform_to_convention(solid, mean: np.ndarray, axis: np.ndarray, sample_pts: np.ndarray):
    """Proper rotation (axis -> +Z) + translation: axis through origin, mid-plane at z=0."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    from OCP.gp import gp_Trsf, gp_Vec

    r = _rotation_to_z(axis)

    d = sample_pts - mean
    rotated = d @ r.T
    zc = 0.5 * (rotated[:, 2].min() + rotated[:, 2].max())

    t1 = gp_Trsf()
    t1.SetTranslation(gp_Vec(-mean[0], -mean[1], -mean[2]))
    t2 = gp_Trsf()
    t2.SetValues(
        r[0, 0], r[0, 1], r[0, 2], 0.0,
        r[1, 0], r[1, 1], r[1, 2], 0.0,
        r[2, 0], r[2, 1], r[2, 2], 0.0,
    )
    t3 = gp_Trsf()
    t3.SetTranslation(gp_Vec(0.0, 0.0, -zc))
    combined = t3.Multiplied(t2.Multiplied(t1))

    transformer = BRepBuilderAPI_Transform(solid, combined, True)
    return transformer.Shape()


# --- Rig + direction (task 1 & 2 of .superpowers/sdd/fan01-runner-brief.md) ---


def measured_tip_radius_mm(stl_mm: str | Path) -> float:
    """99.5th-percentile radial extent of the rotor STL (mm) — same convention as extract."""
    mesh = trimesh.load(str(stl_mm), force="mesh")
    r = np.hypot(mesh.vertices[:, 0], mesh.vertices[:, 1])
    return float(np.percentile(r, 99.5))


def tip_gap_report(stl_mm: str | Path) -> dict[str, float]:
    """Published vs STL-measured tip clearance (§19.13). All lengths in mm except where noted."""
    tip_mm = measured_tip_radius_mm(stl_mm)
    duct_mm = FAN01_DUCT_RADIUS_M / MM_TO_M
    measured_gap_mm = duct_mm - tip_mm
    return {
        "tip_radius_mm_measured": tip_mm,
        "tip_radius_mm_published": FAN01_TIP_RADIUS_MM,
        "duct_radius_mm": duct_mm,
        "tip_gap_mm_measured": measured_gap_mm,
        "tip_gap_mm_published": FAN01_TIP_CLEARANCE_M / MM_TO_M,
        "tip_overread_mm": tip_mm - FAN01_TIP_RADIUS_MM,
    }


def scale_rotor_to_published_tip(
    stl_in: str | Path,
    stl_out: str | Path,
    *,
    published_tip_mm: float = FAN01_TIP_RADIUS_MM,
) -> dict[str, float]:
    """Uniform scale about the origin so the measured tip matches the published radius.

    Keeps the duct at ``FAN01_DUCT_RADIUS_M`` and restores the Table-2 tip clearance in the
    mesh. Hub/blade lengths scale by the same factor (~0.998 for the current extract).
    """
    mesh = trimesh.load(str(stl_in), force="mesh")
    tip_mm = float(np.percentile(np.hypot(mesh.vertices[:, 0], mesh.vertices[:, 1]), 99.5))
    if tip_mm <= 1e-9:
        raise ValueError(f"tip radius {tip_mm} mm is not usable for tip alignment")
    scale = float(published_tip_mm) / tip_mm
    mesh.apply_scale(scale)
    out = Path(stl_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(str(out))
    tip_after = float(np.percentile(np.hypot(mesh.vertices[:, 0], mesh.vertices[:, 1]), 99.5))
    return {
        "tip_radius_mm_before": tip_mm,
        "tip_radius_mm_after": tip_after,
        "scale": scale,
        "tip_gap_mm_after": FAN01_DUCT_RADIUS_M / MM_TO_M - tip_after,
    }


def fan01_rig(
    stl_mm: str | Path,
    *,
    rpm: float = 1486.0,
    inlet_diameters: float = 2.0,
    outlet_diameters: float = 4.0,
    mrf_margin_mm: float = FAN01_MRF_MARGIN_MM,
    inlet_velocity: float = 2.0,
    tip_gap_source: str = "published",
) -> TestRig:
    """Build the FAN-01 ISO 5801 test-rig :class:`TestRig` from the extracted rotor STL.

    ``duct_radius`` is the rig's casing sleeve inner radius (250 mm, fixed by the physical
    rig). ``tip_gap`` defaults to the published 2.5 mm clearance (Table 2); the extracted
    STL's 99.5th-percentile tip over-reads ~0.4 mm so ``duct − tip_measured ≈ 2.11 mm``
    (§19.13). Pass ``tip_gap_source="measured"`` to use the STL-derived gap instead.
    Impeller / MRF z-range and hub radius still come from the STL.
    """
    mesh = trimesh.load(str(stl_mm), force="mesh")
    v = mesh.vertices
    r = np.hypot(v[:, 0], v[:, 1])
    tip_radius_mm = float(np.percentile(r, 99.5))
    hub_radius_mm = float(np.percentile(r, 5.0))
    z0_mm = float(mesh.bounds[0, 2])
    z1_mm = float(mesh.bounds[1, 2])

    duct_radius = FAN01_DUCT_RADIUS_M
    src = str(tip_gap_source or "published").strip().lower()
    if src == "published":
        tip_gap = FAN01_TIP_CLEARANCE_M
    elif src == "measured":
        tip_gap = duct_radius - tip_radius_mm * MM_TO_M
    else:
        raise ValueError(
            f"tip_gap_source must be 'published' or 'measured', got {tip_gap_source!r}"
        )
    impeller_z_min = z0_mm * MM_TO_M
    impeller_z_max = z1_mm * MM_TO_M
    mrf_z_min = impeller_z_min - mrf_margin_mm * MM_TO_M
    mrf_z_max = impeller_z_max + mrf_margin_mm * MM_TO_M

    return TestRig(
        duct_radius=duct_radius,
        tip_gap=tip_gap,
        inlet_length=inlet_diameters * 2.0 * duct_radius,
        outlet_length=outlet_diameters * 2.0 * duct_radius,
        impeller_z_min=impeller_z_min,
        impeller_z_max=impeller_z_max,
        mrf_z_min=mrf_z_min,
        mrf_z_max=mrf_z_max,
        rpm=rpm,
        inlet_velocity=inlet_velocity,
        hub_radius=hub_radius_mm * MM_TO_M,
    )


def fan01_direction(stl_mm: str | Path) -> tuple[str, int]:
    """Direction from geometry alone (roadmap Sec.19.2 applied to FAN-01).

    Runs :func:`fansim.audit.direction.prove_direction` on the rotor STL and maps the result
    through :func:`fansim.cfd.orientation.orientation_from_proof`. Raises ``ValueError`` if the
    proof is not CONCLUSIVE -- rather than guess, the caller must fix the input or investigate.
    Expected for the real FAN-01 rotor: ``("as_built", +1)``.
    """
    mesh = trimesh.load(str(stl_mm), force="mesh")
    proof = prove_direction(mesh)
    return orientation_from_proof(proof)


# --- Measured characteristic (Task 6: interpolation helpers, no CFD) ---


@dataclass(frozen=True)
class CharacteristicPoint:
    q_m3s: float
    p_chamber_pa: float
    shaft_power_w: float


def load_characteristic(
    csv_path: str | Path = DEFAULT_CHARACTERISTIC_CSV,
) -> list[CharacteristicPoint]:
    """Load ``characteristic.csv`` (20 measured points), sorted by ascending flow."""
    rows: list[CharacteristicPoint] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(CharacteristicPoint(
                q_m3s=float(row["volumetric_flow_m3_s"]),
                p_chamber_pa=float(row["p_chamber_static_pa"]),
                shaft_power_w=float(row["shaft_power_w_or_as_named"]),
            ))
    rows.sort(key=lambda r: r.q_m3s)
    return rows


def _monotone_decreasing_branch(
    rows: list[CharacteristicPoint],
) -> list[CharacteristicPoint]:
    """The measured curve's single monotone-decreasing (high-flow) branch.

    FAN-01's characteristic decreases with flow overall but has a small stall "hump" around
    Q~0.9-1.2 m3/s where pressure rises again before resuming its decrease -- not a clean
    function of pressure there. Greedily keep a point only if its pressure continues the
    decrease from the last kept point; this drops just the hump's rising outliers and leaves a
    single strictly-decreasing sequence spanning the whole flow range, safe to interpolate on.
    """
    if not rows:
        return []
    kept = [rows[0]]
    for r in rows[1:]:
        if r.p_chamber_pa < kept[-1].p_chamber_pa:
            kept.append(r)
    return kept


def interpolate_measured_q(
    rows: list[CharacteristicPoint], back_pressure_pa: float,
) -> float | None:
    """Flow Q (m3/s) at ``back_pressure_pa``, linearly interpolated on the monotone branch.

    Returns ``None`` if ``back_pressure_pa`` falls outside the branch's pressure range (which
    includes the small gap the stall hump's rejected points would otherwise have covered --
    use :func:`measured_q_all_crossings` there instead).
    """
    branch = _monotone_decreasing_branch(rows)
    if not branch:
        return None
    p_max, p_min = branch[0].p_chamber_pa, branch[-1].p_chamber_pa
    extrap_margin = 0.05 * (p_max - p_min)  # small clamp for a target just past a measured extreme
    if back_pressure_pa > p_max:
        return branch[0].q_m3s if back_pressure_pa <= p_max + extrap_margin else None
    if back_pressure_pa < p_min:
        return branch[-1].q_m3s if back_pressure_pa >= p_min - extrap_margin else None
    for a, b in pairwise(branch):
        if a.p_chamber_pa >= back_pressure_pa >= b.p_chamber_pa:
            if a.p_chamber_pa == b.p_chamber_pa:
                return a.q_m3s
            frac = (a.p_chamber_pa - back_pressure_pa) / (a.p_chamber_pa - b.p_chamber_pa)
            return a.q_m3s + frac * (b.q_m3s - a.q_m3s)
    return None


def measured_q_all_crossings(
    rows: list[CharacteristicPoint], back_pressure_pa: float,
) -> list[float]:
    """Every Q (m3/s) where the raw (unfiltered) measured curve crosses ``back_pressure_pa``.

    Used for back-pressures in the stall-region gap the monotone branch drops, where the
    measured curve is not single-valued: more than one flow rate can share the same chamber
    pressure. Returned ascending; may contain 0, 1 or several crossings.
    """
    out: list[float] = []
    for a, b in pairwise(rows):
        lo, hi = sorted((a.p_chamber_pa, b.p_chamber_pa))
        if lo <= back_pressure_pa <= hi and a.p_chamber_pa != b.p_chamber_pa:
            frac = (a.p_chamber_pa - back_pressure_pa) / (a.p_chamber_pa - b.p_chamber_pa)
            out.append(a.q_m3s + frac * (b.q_m3s - a.q_m3s))
    uniq = sorted({round(q, 6) for q in out})
    return uniq


def measured_q_report(
    rows: list[CharacteristicPoint], back_pressure_pa: float,
) -> dict:
    """Reporting dict for a run_fan01 point: primary measured Q plus stall-region alternates.

    ``measured_q_m3s`` is the monotone-branch interpolation (``None`` outside its range).
    ``measured_q_m3s_branches`` is added only when the raw curve crosses ``back_pressure_pa``
    at more than one flow rate (the stall-region case the brief calls out) -- every crossing
    found, so the caller can report both branches instead of picking one silently.
    """
    out: dict = {"measured_q_m3s": interpolate_measured_q(rows, back_pressure_pa)}
    all_q = measured_q_all_crossings(rows, back_pressure_pa)
    if len(all_q) > 1:
        out["measured_q_m3s_branches"] = all_q
    return out
