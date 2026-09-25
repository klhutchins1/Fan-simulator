"""Known-answer rotor geometry for audit self-checks (no CadQuery; pure trimesh).

Each blade is a thin cambered section, extruded radially and wrapped onto the cylinder
(theta = s / rho), so it is a true helical blade and not a flat card. In the section plane (s, z):
chord c = (cos g, sin g), normal e = (-sin g, cos g), mean line bulging toward +e by
``camber * chord``. The hub is a solid cylinder or a motor cup (``cup_side`` = the open face).
"""

from __future__ import annotations

import numpy as np
import trimesh


def _blade(theta0, r_hub, r_tip, chord, stagger_deg, camber, thick, sweep_deg=0.0,
           chord_gamma=1.0, n_chord=40, n_span=12):
    g = np.radians(stagger_deg)
    c_hat = np.array([np.cos(g), np.sin(g)])
    e_hat = np.array([-np.sin(g), np.cos(g)])
    u = np.linspace(-1.0, 1.0, n_chord)
    if chord_gamma != 1.0:
        u = np.sign(u) * np.abs(u) ** chord_gamma
    xi = u * (chord / 2.0)
    eta_m = camber * chord * (1.0 - (2.0 * xi / chord) ** 2)
    rho = np.linspace(r_hub - 1.0, r_tip, n_span)
    layers = []
    for side in (+1.0, -1.0):
        eta = eta_m + side * thick / 2.0
        s = xi * c_hat[0] + eta * e_hat[0]
        a = xi * c_hat[1] + eta * e_hat[1]
        sweep = np.radians(sweep_deg) * (rho - r_hub) / (r_tip - r_hub)
        th = theta0 + sweep[None, :] + s[:, None] / rho[None, :]
        x = rho[None, :] * np.cos(th)
        y = rho[None, :] * np.sin(th)
        z = np.broadcast_to(a[:, None], th.shape)
        layers.append(np.stack([x, y, z], axis=-1).reshape(-1, 3))
    verts = np.vstack(layers)
    nc, ns = n_chord, n_span

    def vid(side, i, j):
        return side * nc * ns + i * ns + j

    faces = []

    def quad(a_, b_, c_, d_):
        faces.extend([[a_, b_, c_], [a_, c_, d_]])

    for i in range(nc - 1):
        for j in range(ns - 1):
            for side in (0, 1):
                quad(vid(side, i, j), vid(side, i + 1, j), vid(side, i + 1, j + 1), vid(side, i, j + 1))
    for i in (0, nc - 1):
        for j in range(ns - 1):
            quad(vid(0, i, j), vid(1, i, j), vid(1, i, j + 1), vid(0, i, j + 1))
    for j in (0, ns - 1):
        for i in range(nc - 1):
            quad(vid(0, i, j), vid(0, i + 1, j), vid(1, i + 1, j), vid(1, i, j))
    mesh = trimesh.Trimesh(verts, np.asarray(faces), process=True)
    mesh.fix_normals()
    return mesh


def _hub(r_hub, height, cup_side, bore_r=0.0):
    if cup_side is None:
        if bore_r > 0.0:
            return trimesh.creation.annulus(r_min=bore_r, r_max=r_hub, height=height, sections=48)
        return trimesh.creation.cylinder(radius=r_hub, height=height, sections=48)
    cup_r, cap = 0.75 * r_hub, 1.5
    wall = trimesh.creation.annulus(r_min=cup_r, r_max=r_hub, height=height, sections=48)
    if bore_r > 0.0:
        # A through-bore must pierce the lid too, or it would just be a blind cup.
        lid = trimesh.creation.annulus(r_min=bore_r, r_max=cup_r, height=cap, sections=48)
    else:
        lid = trimesh.creation.cylinder(radius=cup_r, height=cap, sections=48)
    # The lid closes the face OPPOSITE the open cup.
    lid.apply_translation([0.0, 0.0, -cup_side * (height - cap) / 2.0])
    return trimesh.util.concatenate([wall, lid])


def cambered_blade_fan(n_blades: int = 5, r_hub: float = 15.0, r_tip: float = 50.0,
                       chord: float = 20.0, stagger_deg: float = 60.0, camber: float = 0.06,
                       thick: float = 1.0, cup_side: int | None = None,
                       hub_height: float = 16.0, sweep_deg: float = 0.0,
                       chord_gamma: float = 1.0, bore_r: float = 0.0) -> trimesh.Trimesh:
    parts = [_blade(2.0 * np.pi * k / n_blades, r_hub, r_tip, chord, stagger_deg, camber, thick,
                    sweep_deg, chord_gamma)
             for k in range(n_blades)]
    parts.append(_hub(r_hub, hub_height, cup_side, bore_r))
    return trimesh.util.concatenate(parts)
