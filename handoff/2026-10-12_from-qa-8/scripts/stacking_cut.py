"""Task F (round 7) prototype: direction proof from cuts NORMAL TO THE STACKING LINE (option b).
Separate function; fansim.audit.direction.prove_direction is not modified. It reuses its private helpers and thresholds.

Method:
1. Track each blade's stacking line: cylinder cuts at many radii give one loop per blade. Each loop's centroid
   (theta, z) at radius r is a point; loops are linked radius-to-radius by nearest angle.
2. At each evaluation radius, the local tangent t = dc/dr (quadratic fit over neighbours), oriented outward.
3. Cut the mesh with the plane through c, normal t. Keep the closed loop nearest c, then read it exactly like
   _read_section, in the in-plane frame e1 = theta_hat projected on the plane, e2 = t x e1. (e1, e2, t) is
   right-handed with t ~ r_hat, which matches the cylinder reading's (s, z, r) frame, so omega/pump signs keep their meaning.
4. Same filters (camber >= 0.02, t/c <= 0.25, midline residual) and the same vote as prove_direction.
mode="radial": same, but the plane normal is r_hat at c (ignores lean); reported as a variant only."""
from collections import Counter
import numpy as np, networkx as nx, trimesh
from fansim.audit import direction as D

TRACK_FRACS = tuple(np.round(np.linspace(0.50, 0.97, 25), 4))

def _loop_centroid(pts, r0):
    th = np.arctan2(pts[:, 1], pts[:, 0]); tm = np.angle(np.mean(np.exp(1j * th)))
    s = r0 * np.angle(np.exp(1j * (th - tm)))
    p2 = D._resample_closed(np.column_stack([s, pts[:, 2]]))
    span = s.max() - s.min()
    c_th = tm + p2[:, 0].mean() / r0
    return np.array([r0 * np.cos(c_th), r0 * np.sin(c_th), p2[:, 1].mean()]), c_th, span

def _tracks(mesh, tip):
    tracks = []  # list of dict r -> centroid
    for f in TRACK_FRACS:
        r0 = f * tip
        cs = []
        for pts, _ in D._section_loops(mesh, r0):
            c, th, span = _loop_centroid(pts, r0)
            if span > 1.2 * np.pi * r0:      # full ring (hub/shroud), not a blade
                continue
            cs.append((c, th))
        for c, th in cs:
            best, bd = None, 1e9
            for tr in tracks:
                rl = max(tr); cl = tr[rl]
                d = abs(np.angle(np.exp(1j * (th - np.arctan2(cl[1], cl[0])))))
                if rl < r0 and d < bd: best, bd = tr, d
            if best is not None and bd < np.radians(25):
                best[r0] = c
            else:
                tracks.append({r0: c})
    return [t for t in tracks if len(t) >= 5]

def _plane_loop(mesh, origin, normal):
    lines, faces = trimesh.intersections.mesh_plane(mesh, normal, origin, return_faces=True)
    if len(lines) == 0: return None, None
    key = lambda p: tuple(np.round(p, 6))
    g = nx.Graph(); coords = {}
    for (a, b), f in zip(lines, faces):
        ka, kb = key(a), key(b); coords[ka] = a; coords[kb] = b
        if ka != kb: g.add_edge(ka, kb, face=int(f))
    best, bd = None, 1e9
    for comp in nx.connected_components(g):
        if len(comp) < 8: continue
        P = np.array([coords[k] for k in comp]); d = np.linalg.norm(P.mean(0) - origin)
        if d < bd: best, bd = comp, d
    if best is None: return None, None
    sub = g.subgraph(best)
    order = list(nx.dfs_preorder_nodes(sub))
    return np.array([coords[k] for k in order]), np.array([d["face"] for _, _, d in sub.edges(data=True)], int)

def _read_plane(mesh, pts, faces, c, n):
    th_c = np.arctan2(c[1], c[0]); eth = np.array([-np.sin(th_c), np.cos(th_c), 0.0])
    e1 = eth - eth.dot(n) * n; e1 /= np.linalg.norm(e1); e2 = np.cross(n, e1)
    q = pts - c
    p2 = D._resample_closed(np.column_stack([q @ e1, q @ e2])); p2 = p2 - p2.mean(0)
    _, vecs = np.linalg.eigh(p2.T @ p2); c_hat = vecs[:, 1]; e_hat = np.array([-c_hat[1], c_hat[0]])
    xi, eta = p2 @ c_hat, p2 @ e_hat
    chord = float(xi.max() - xi.min())
    if chord <= 0: return None
    a = float(np.polyfit(xi, eta, 2)[0]); camber = abs(a) * (chord / 2) ** 2 / chord
    n_p = np.sign(a) * e_hat
    fc = mesh.triangles_center[faces]; fn = mesh.face_normals[faces]; th = np.arctan2(fc[:, 1], fc[:, 0])
    chi = float(np.sum(mesh.area_faces[faces] * (-np.sin(th) * fn[:, 0] + np.cos(th) * fn[:, 1]) * fn[:, 2]))
    return D.SectionReading(float(np.hypot(c[0], c[1])), int(np.sign(n_p[0])), int(np.sign(n_p[1])), int(np.sign(chi)),
                            float(camber), float((eta.max() - eta.min()) / chord), D._midline_residual_mm(xi, eta), chord)

def prove_direction_stacking(mesh, r_fracs=D.DEFAULT_R_FRACS, mode="stacking"):
    mesh = mesh.copy(); mesh.merge_vertices(); tip = D._tip_radius(mesh)
    tracks = _tracks(mesh, tip)
    readings, flat, rejected, lean_deg = [], 0, 0, []
    for tr in tracks:
        rs = np.array(sorted(tr)); C = np.array([tr[r] for r in rs])
        for f in r_fracs:
            re_ = f * tip
            if re_ < rs.min() or re_ > rs.max(): continue
            sel = np.argsort(np.abs(rs - re_))[:5]
            co = [np.polyfit(rs[sel], C[sel, k], 2) for k in range(3)]
            c = np.array([np.polyval(co[k], re_) for k in range(3)])
            t = np.array([np.polyval(np.polyder(co[k]), re_) for k in range(3)])
            rhat = np.array([c[0], c[1], 0.0]) / np.hypot(c[0], c[1])
            if mode == "radial": t = rhat.copy()
            t /= np.linalg.norm(t)
            if t.dot(rhat) < 0: t = -t
            lean_deg.append(float(np.degrees(np.arccos(np.clip(t.dot(rhat), -1, 1)))))
            pts, faces = _plane_loop(mesh, c, t)
            if pts is None: continue
            rd = _read_plane(mesh, pts, faces, c, t)
            if rd is None: continue
            if rd.camber_ratio < D.MIN_CAMBER_RATIO: flat += 1; continue
            h = rd.camber_ratio * rd.chord_mm
            if rd.thickness_ratio > D.MAX_THICKNESS_RATIO or rd.midline_residual_mm is None or h <= 0 \
                    or rd.midline_residual_mm > D.MAX_MIDLINE_RESIDUAL_RATIO * h:
                rejected += 1; continue
            readings.append(rd)
    extra = {"n_tracks": len(tracks), "max_tilt_deg": round(max(lean_deg), 1) if lean_deg else None,
             "median_camber": float(np.median([r.camber_ratio for r in readings])) if readings else None}
    if not readings:
        return D.DirectionProof(None, None, None, 0.0, 0, (), "INCONCLUSIVE", f"no cambered sections ({flat} flat, {rejected} low-quality)"), extra
    if len({round(r.r_mm, 3) for r in readings}) < D.MIN_SECTION_RADII:
        return D.DirectionProof(None, None, None, 0.0, len(readings), tuple(readings), "INCONCLUSIVE", "single radius"), extra
    (om, pu), n = Counter((r.omega_sign, r.pump_sign) for r in readings).most_common(1)[0]
    agr = n / len(readings); chi_ok = sum(r.chirality == r.omega_sign * r.pump_sign for r in readings) / len(readings)
    chi = Counter(r.chirality for r in readings).most_common(1)[0][0]
    if agr < D.MIN_AGREEMENT or chi_ok < D.MIN_AGREEMENT:
        return D.DirectionProof(None, None, None, agr, len(readings), tuple(readings), "INCONCLUSIVE",
                                f"sections disagree (agreement {agr:.2f}, chi {chi_ok:.2f})"), extra
    return D.DirectionProof(int(om), int(pu), int(chi), agr, len(readings), tuple(readings), "CONCLUSIVE",
                            f"{len(readings)} sections, {flat} flat, {rejected} low-quality"), extra
