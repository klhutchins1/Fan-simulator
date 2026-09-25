"""Audit #1, proof 1: which way a rotor is designed to turn and pump, from its mesh alone.

Velocity-triangle physics (Dixon & Hall): the concave pressure face of a fan blade points in the
direction of rotation, and the blade pushes air along that face's normal. For cylinder cuts
r = r0 through the blades we unroll each section loop to (s = r0*theta, z), fit chord + quadratic
camber, take the concave side's normal n_p, and read rotation = sign(n_p.s) (+1 = +theta =
omega_z > 0, CCW seen from +Z) and delivery = sign(n_p.z) (+1 = +Z).

Cross-check: chirality chi = sign(sum A * n_theta * n_z) over the cut faces. chi is invariant under
any proper rotation of the part and flips under mirroring; it must equal rotation * delivery.
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
    """Face (+1 = +Z, -1 = -Z) where the hub is an open cup: axial rays go deeper on that side."""
    v = mesh.vertices
    tip = _tip_radius(mesh)
    rv = np.hypot(v[:, 0], v[:, 1])
    hub = v[rv < 0.3 * tip]
    if len(hub) < 10:
        return None
    z0, z1 = float(hub[:, 2].min()), float(hub[:, 2].max())
    rng = np.random.default_rng(0)
    rr = tip * (0.05 + 0.10 * rng.random(n))
    th = 2.0 * np.pi * rng.random(n)
    xy = np.column_stack([rr * np.cos(th), rr * np.sin(th)])

    def depth(z_face: float, direction: float) -> float | None:
        origins = np.column_stack([xy, np.full(n, z_face - direction * 1.0)])
        dirs = np.tile([0.0, 0.0, direction], (n, 1))
        locs, _, _ = mesh.ray.intersects_location(origins, dirs, multiple_hits=False)
        if len(locs) < n // 2:
            return None
        return float(np.median(np.abs(locs[:, 2] - z_face)))

    d_lo, d_hi = depth(z0, +1.0), depth(z1, -1.0)
    if d_lo is None or d_hi is None or abs(d_lo - d_hi) < min_depth_mm:
        return None
    return -1 if d_lo > d_hi else +1


def tip_lead_sign(mesh: trimesh.Trimesh,
                  r_fracs: tuple[float, ...] = (0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9),
                  min_sweep_deg: float = 3.0) -> int | None:
    """Which way the blade tips sit ahead of the roots: +1 toward +theta, -1 toward -theta.

    Each blade is tracked outward through closely spaced cylinder cuts (nearest section centroid
    step to step, so large total sweep never jumps to a neighbour blade). The median total sweep
    across blades decides; |sweep| below ``min_sweep_deg`` is unclear (None).
    """
    tip = _tip_radius(mesh)
    rings = []
    for f in r_fracs:
        cents = []
        for pts, _ in _section_loops(mesh, f * tip):
            th = np.arctan2(pts[:, 1], pts[:, 0])
            cents.append(float(np.angle(np.mean(np.exp(1j * th)))))
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
