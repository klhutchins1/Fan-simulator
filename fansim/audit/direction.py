"""Audit #1, proof 1: which way a rotor is designed to turn and pump, from its mesh alone.

Velocity-triangle physics (Dixon & Hall): the concave pressure face of a fan blade points in the
direction of rotation, and the blade pushes air along that face's normal. For cylinder cuts
r = r0 through the blades we unroll each section loop to (s = r0*theta, z), fit chord + quadratic
camber, take the concave side's normal n_p, and read rotation = sign(n_p.s) (+1 = +theta =
omega_z > 0, CCW seen from +Z) and delivery = sign(n_p.z) (+1 = +Z).

Cross-check: chirality chi = sign(sum A * n_theta * n_z) over the cut faces. chi is invariant under
any proper rotation of the part and flips under mirroring. Algebraically chi always equals
rotation * delivery (both reduce to sign(e_s . e_z) of the same section frame), so this check only
confirms chord/normal consistency and the part's handedness -- it is not an independent proof of
which way the part is designed to turn. The independent check of the designed rotation is the tip
lead (on the real fan, tips lead the rotation). The motor side (air leaves past the motor, so
pump = motor_side and, via chirality, omega = chi * pump) is corroboration only, not an independent
proof: it reads the cup from a face recess of 2 mm or more, which any sufficiently deep recess on
either face -- cup or not -- would also satisfy.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import networkx as nx
import numpy as np
import trimesh

MIN_CAMBER_RATIO = 0.01   # camber height / chord below which the concave side is not trusted
MIN_AGREEMENT = 0.9       # fraction of sections that must agree
REAL_FAN_CHIRALITY = -1   # NF-A12x25: CCW seen from intake, air pushed away from the viewer


@dataclass(frozen=True)
class SectionReading:
    r_mm: float
    omega_sign: int
    pump_sign: int
    chirality: int
    camber_ratio: float


@dataclass(frozen=True)
class DirectionProof:
    omega_sign: int | None
    pump_sign: int | None
    chirality: int | None
    agreement: float
    n_sections: int
    readings: tuple[SectionReading, ...]
    verdict: str
    note: str


def _tip_radius(mesh: trimesh.Trimesh) -> float:
    v = mesh.vertices
    return float(np.percentile(np.hypot(v[:, 0], v[:, 1]), 99.5))


def _section_loops(mesh: trimesh.Trimesh, r0: float):
    """Cut with the cylinder r = r0. Yields (ordered loop points (k,3), crossed face ids)."""
    v = mesh.vertices
    r = np.hypot(v[:, 0], v[:, 1]) - r0
    r[r == 0.0] = 1e-12  # a vertex exactly on r0 must count as outside, not as a crossing
    e = mesh.edges_unique
    crossed = (r[e[:, 0]] * r[e[:, 1]]) < 0.0
    idx = np.nonzero(crossed)[0]
    if len(idx) == 0:
        return
    t = r[e[idx, 0]] / (r[e[idx, 0]] - r[e[idx, 1]])
    pts = v[e[idx, 0]] + t[:, None] * (v[e[idx, 1]] - v[e[idx, 0]])
    pos = -np.ones(len(e), dtype=int)
    pos[idx] = np.arange(len(idx))
    fue = mesh.faces_unique_edges
    hit = crossed[fue]
    g = nx.Graph()
    g.add_nodes_from(range(len(idx)))
    for f in np.nonzero(hit.sum(axis=1) == 2)[0]:
        a, b = pos[fue[f][hit[f]]]
        g.add_edge(int(a), int(b), face=int(f))
    for comp in nx.connected_components(g):
        sub = g.subgraph(comp)
        if len(comp) < 8:
            continue
        order = list(nx.dfs_preorder_nodes(sub))
        faces = np.array([d["face"] for _, _, d in sub.edges(data=True)], dtype=int)
        yield pts[order], faces


def _resample_closed(p2: np.ndarray, n: int = 400) -> np.ndarray:
    closed = np.vstack([p2, p2[:1]])
    seg = np.linalg.norm(np.diff(closed, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    u = np.linspace(0.0, cum[-1], n, endpoint=False)
    return np.column_stack([np.interp(u, cum, closed[:, 0]), np.interp(u, cum, closed[:, 1])])


def _read_section(mesh, pts, faces, r0) -> SectionReading | None:
    theta = np.arctan2(pts[:, 1], pts[:, 0])
    tm = np.angle(np.mean(np.exp(1j * theta)))
    s = r0 * np.angle(np.exp(1j * (theta - tm)))
    p2 = _resample_closed(np.column_stack([s, pts[:, 2]]))
    p2 = p2 - p2.mean(axis=0)
    _, vecs = np.linalg.eigh(p2.T @ p2)
    c_hat = vecs[:, 1]
    e_hat = np.array([-c_hat[1], c_hat[0]])
    xi, eta = p2 @ c_hat, p2 @ e_hat
    chord = float(xi.max() - xi.min())
    if chord <= 0.0:
        return None
    a = float(np.polyfit(xi, eta, 2)[0])
    camber_ratio = abs(a) * (chord / 2.0) ** 2 / chord
    n_p = np.sign(a) * e_hat  # a < 0: bulges +e, concave (pressure) face is -e
    fc = mesh.triangles_center[faces]
    fn = mesh.face_normals[faces]
    th = np.arctan2(fc[:, 1], fc[:, 0])
    n_theta = -np.sin(th) * fn[:, 0] + np.cos(th) * fn[:, 1]
    chi = float(np.sum(mesh.area_faces[faces] * n_theta * fn[:, 2]))
    return SectionReading(float(r0), int(np.sign(n_p[0])), int(np.sign(n_p[1])),
                          int(np.sign(chi)), float(camber_ratio))


def prove_direction(mesh: trimesh.Trimesh,
                    r_fracs: tuple[float, ...] = (0.55, 0.65, 0.75, 0.85)) -> DirectionProof:
    mesh = mesh.copy()
    mesh.merge_vertices()
    tip = _tip_radius(mesh)
    readings: list[SectionReading] = []
    flat = 0
    for f in r_fracs:
        for pts, faces in _section_loops(mesh, f * tip):
            rd = _read_section(mesh, pts, faces, f * tip)
            if rd is None:
                continue
            if rd.camber_ratio < MIN_CAMBER_RATIO:
                flat += 1
                continue
            readings.append(rd)
    if not readings:
        return DirectionProof(None, None, None, 0.0, 0, (), "INCONCLUSIVE",
                              f"no cambered sections ({flat} flat) — concave side undefined")
    (om, pu), n = Counter((r.omega_sign, r.pump_sign) for r in readings).most_common(1)[0]
    agreement = n / len(readings)
    chi_ok = sum(r.chirality == r.omega_sign * r.pump_sign for r in readings) / len(readings)
    chi = Counter(r.chirality for r in readings).most_common(1)[0][0]
    if agreement < MIN_AGREEMENT or chi_ok < MIN_AGREEMENT:
        return DirectionProof(None, None, None, agreement, len(readings), tuple(readings),
                              "INCONCLUSIVE",
                              f"sections disagree (agreement {agreement:.2f}, chirality check {chi_ok:.2f})")
    return DirectionProof(int(om), int(pu), int(chi), agreement, len(readings), tuple(readings),
                          "CONCLUSIVE", f"{len(readings)} sections, {flat} flat skipped")


def motor_side(mesh: trimesh.Trimesh, n: int = 64, min_depth_mm: float = 2.0) -> int | None:
    """Face (+1 = +Z, -1 = -Z) where the hub is an open cup: axial rays go deeper on that side.

    Probes a series of radial bands near the axis, capped BELOW the blade roots so the probe never
    reaches into the blades (a low hub/tip ratio previously let it do so and misread a plain solid
    hub as a cup). ``r_root`` is the smallest radius at which cylinder cuts start yielding real
    blade sections; only bands with r <= 0.9*r_root are probed.

    For each band, rays are cast from below and from above (starting outside the whole mesh's z
    bounds, ``multiple_hits=False``) and the median FIRST-HIT z is recorded on each side
    (``z_lo_hit``, ``z_hi_hit``) -- not a depth relative to a face, since a plain z-shift of a
    solid hub relative to the blades must not look like a cup. The hub's own end-face baselines
    are ``hub_z0 = min`` over bands of ``z_lo_hit`` and ``hub_z1 = max`` over bands of
    ``z_hi_hit`` (whichever band's rays reach the true solid end, e.g. the wall of a cup, sets the
    baseline). A band shows a cup open at -Z when its bottom hit is recessed from that baseline by
    at least ``min_depth_mm`` while its top hit sits at the baseline (within ``min_depth_mm``); the
    mirror condition shows a cup open at +Z. The side is returned only if every qualifying band
    agrees; disagreement or no qualifying band is None.
    """
    mesh = mesh.copy()
    mesh.merge_vertices()
    tip = _tip_radius(mesh)

    r_root = None
    for f in np.linspace(0.1, 0.6, 26):
        r0 = f * tip
        if sum(1 for _ in _section_loops(mesh, r0)) >= 3:
            r_root = r0
            break
    if r_root is None:
        return None
    r_cap = 0.9 * r_root
    bands = list(np.linspace(0.05 * tip, r_cap, 12))
    if not bands:
        return None

    z0, z1 = (float(b) for b in mesh.bounds[:, 2])
    rng = np.random.default_rng(0)

    def first_hit(z_face: float, direction: float, r_lo: float, r_hi: float) -> float | None:
        rr = r_lo + (r_hi - r_lo) * rng.random(n)
        th = 2.0 * np.pi * rng.random(n)
        xy = np.column_stack([rr * np.cos(th), rr * np.sin(th)])
        origins = np.column_stack([xy, np.full(n, z_face - direction * 1.0)])
        dirs = np.tile([0.0, 0.0, direction], (n, 1))
        locs, _, _ = mesh.ray.intersects_location(origins, dirs, multiple_hits=False)
        if len(locs) < n // 2:
            return None
        return float(np.median(locs[:, 2]))

    band_hits = []
    for r0 in bands:
        r_lo, r_hi = r0 - 0.02 * tip, r0 + 0.02 * tip
        band_hits.append((first_hit(z0, +1.0, r_lo, r_hi), first_hit(z1, -1.0, r_lo, r_hi)))

    lo_hits = [z for z, _ in band_hits if z is not None]
    hi_hits = [z for _, z in band_hits if z is not None]
    if not lo_hits or not hi_hits:
        return None
    hub_z0, hub_z1 = min(lo_hits), max(hi_hits)

    sides = set()
    for z_lo_hit, z_hi_hit in band_hits:
        if z_lo_hit is None or z_hi_hit is None:
            continue
        open_lo = (z_lo_hit - hub_z0) >= min_depth_mm and (hub_z1 - z_hi_hit) < min_depth_mm
        open_hi = (hub_z1 - z_hi_hit) >= min_depth_mm and (z_lo_hit - hub_z0) < min_depth_mm
        if open_lo:
            sides.add(-1)
        elif open_hi:
            sides.add(+1)
    return sides.pop() if len(sides) == 1 else None


def tip_lead_sign(mesh: trimesh.Trimesh,
                  r_fracs: tuple[float, ...] = (0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9),
                  min_sweep_deg: float = 3.0) -> int | None:
    """Which way the blade tips sit ahead of the roots: +1 toward +theta, -1 toward -theta.

    Each blade is tracked outward through closely spaced cylinder cuts (nearest section centroid
    step to step, so large total sweep never jumps to a neighbour blade). The median total sweep
    across blades decides; |sweep| below ``min_sweep_deg`` is unclear (None).

    The per-loop angular centroid is computed from the arc-length-resampled loop (same unwrap as
    ``_read_section``), not a raw vertex mean: uneven chordwise vertex density would otherwise bias
    a raw mean toward wherever vertices happen to be denser, faking a lead that isn't there.
    """
    mesh = mesh.copy()
    mesh.merge_vertices()
    tip = _tip_radius(mesh)
    rings = []
    for f in r_fracs:
        r0 = f * tip
        cents = []
        for pts, _ in _section_loops(mesh, r0):
            theta = np.arctan2(pts[:, 1], pts[:, 0])
            tm = np.angle(np.mean(np.exp(1j * theta)))
            s = r0 * np.angle(np.exp(1j * (theta - tm)))
            p2 = _resample_closed(np.column_stack([s, pts[:, 2]]))
            theta_r = tm + p2[:, 0] / r0
            cents.append(float(np.angle(np.mean(np.exp(1j * theta_r)))))
        if not cents:
            return None
        rings.append(np.array(cents))
    totals = []
    for start in rings[0]:
        cur, total = start, 0.0
        for ring in rings[1:]:
            d = np.angle(np.exp(1j * (ring - cur)))
            k = int(np.argmin(np.abs(d)))
            total += float(d[k])
            cur = ring[k]
        totals.append(total)
    sweep = float(np.degrees(np.median(totals)))
    if abs(sweep) < min_sweep_deg:
        return None
    return 1 if sweep > 0 else -1


def flip_about_x(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Proper 180° rotation about X (z -> -z, y -> -y): same fan, turned over."""
    m = mesh.copy()
    m.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1.0, 0.0, 0.0]))
    return m
