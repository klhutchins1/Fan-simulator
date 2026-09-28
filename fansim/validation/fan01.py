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

from dataclasses import dataclass
from pathlib import Path

import networkx as nx
import numpy as np
import trimesh
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_IGS = ROOT / "validation" / "reference" / "fan01" / "cad_model" / "cad_model.igs"
DEFAULT_OUT_STL = ROOT / "validation" / "reference" / "fan01" / "fan01_rotor.stl"

MIN_CLUSTER_FACES = 20
MAX_CLUSTER_FACES = 500
AREA_GROUP_TOL = 0.03  # relative area tolerance for "matching" blade faces


@dataclass(frozen=True)
class RotorExtractionInfo:
    n_faces: int
    tip_radius_mm: float
    hub_radius_mm: float
    axial_extent_mm: float
    watertight: bool
    n_blades_found: int


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


def extract_rotor_stl(
    igs_path: str | Path = DEFAULT_IGS,
    out_stl: str | Path = DEFAULT_OUT_STL,
    expected_blade_count: int = 9,
    tol_mm: float = 0.02,
    expected_tip_radius_mm: float | None = 245.0,
    stl_tolerance_mm: float = 0.1,
) -> dict:
    """Isolate the FAN-01 rotor from the full test-rig IGES and write a watertight STL.

    Returns a dict of measured geometry (tip/hub radius, blade count, axial extent,
    watertight flag) for reporting/verification -- see module docstring for the method.
    """
    import cadquery as cq

    igs_path, out_stl = Path(igs_path), Path(out_stl)
    rotor_faces, mean, axis = find_rotor_faces(
        igs_path, expected_blade_count, tol_mm, expected_tip_radius_mm
    )
    solid = _sew_to_solid(rotor_faces)

    sample = _tessellate(rotor_faces)
    sample_pts = np.vstack([p for p, _ in sample if len(p)])

    final_solid = _transform_to_convention(solid, mean, axis, sample_pts)

    out_stl.parent.mkdir(parents=True, exist_ok=True)
    shp = cq.Shape.cast(final_solid)
    wp = cq.Workplane("XY").newObject([shp])
    wp.val().exportStl(str(out_stl), tolerance=stl_tolerance_mm, angularTolerance=0.2)

    mesh = trimesh.load(str(out_stl))
    watertight = bool(mesh.is_watertight)
    if not watertight:
        mesh.fill_holes()
        if mesh.is_watertight:
            mesh.export(str(out_stl))
            watertight = True

    v = mesh.vertices
    r = np.hypot(v[:, 0], v[:, 1])
    tip_radius_mm = float(np.percentile(r, 99.5))
    hub_radius_mm = float(np.percentile(r, 5.0))
    axial_extent_mm = float(v[:, 2].max() - v[:, 2].min())

    from fansim.audit.direction import _section_loops

    m2 = mesh.copy()
    m2.merge_vertices()
    n_blades_found = sum(1 for _ in _section_loops(m2, 0.75 * tip_radius_mm))

    return {
        "n_faces": len(rotor_faces),
        "tip_radius_mm": tip_radius_mm,
        "hub_radius_mm": hub_radius_mm,
        "axial_extent_mm": axial_extent_mm,
        "watertight": watertight,
        "n_blades_found": n_blades_found,
    }
