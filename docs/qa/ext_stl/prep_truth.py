"""QA r9 Task D step 1 (PREREG_R9 a0260c0): prepare each outside STL (local /tmp only) and record the
ground truth BEFORE either direction reader runs.
Prep: merge vertices; rotation axis = the inertia principal axis with the most distinct moment (a rotor is
near-axisymmetric about it); rotate it onto +Z (sign kept as the file's own orientation: the axis component
with the larger |value| keeps its sign), translate the axis to x=y=0. Proper rotation only (no mirroring).
Truth (independent of the readers' camber cue):
  omega: (a) leading-edge bluntness: at r = 0.6/0.7/0.8 tip, each blade's cylinder section is unrolled to
         (s, z); its chord ends are the farthest-apart pair; the end whose thickness at 8 % chord is larger is
         the LE (LE round, TE sharp); omega = sign(s_LE - s_TE). Needs >= 60 % of read sections to agree and
         a mean thickness ratio >= 1.25 (else unclear).
         (b) tip lead (fansim.audit.direction.tip_lead_sign; real fan tips lead the rotation).
         omega = (a) if clear; else (b); if both clear and they disagree -> no truth (coverage only).
  pump : a blade moving toward its LE pushes air toward its TE's axial side: pump = sign(z_TE - z_LE),
         majority over the same sections (stagger/helix cue, camber-free).
  chi  : omega * pump (the reader's chirality is algebraically omega*pump).
Writes truth.json (per part) and prepared STLs to /tmp/qa9_ext/prep/."""
import json, sys
from collections import Counter
from pathlib import Path
import numpy as np, trimesh
from fansim.audit import direction as D
SRC = Path("/tmp/qa9_ext"); OUT = SRC / "prep"; OUT.mkdir(exist_ok=True)

def prep(m):
    m = m.copy(); m.merge_vertices()
    c = m.center_mass if m.is_watertight else m.centroid
    I = m.moment_inertia if m.is_watertight else np.cov((m.vertices - c).T)
    w, V = np.linalg.eigh(I)
    gaps = [abs(w[0] - w[1]) + abs(w[0] - w[2]), abs(w[1] - w[0]) + abs(w[1] - w[2]), abs(w[2] - w[0]) + abs(w[2] - w[1])]
    a = V[:, int(np.argmax(gaps))]
    if a[np.argmax(np.abs(a))] < 0: a = -a
    T = trimesh.geometry.align_vectors(a, [0, 0, 1]); m.apply_transform(T)
    # axis through x=y=0: use the centre of the vertex xy bounding circle approx (mean of bounds) then refine by centroid
    b = m.bounds; m.apply_translation([-(b[0][0] + b[1][0]) / 2, -(b[0][1] + b[1][1]) / 2, -b[0][2]])
    return m

def le_truth(m):
    tip = D._tip_radius(m); votes = []; pumps = []; ratios = []
    for f in (0.6, 0.7, 0.8):
        r0 = f * tip
        try:
            loops = list(D._section_loops(m, r0))
        except Exception:
            loops = []
        for pts, _f in loops:
            th = np.arctan2(pts[:, 1], pts[:, 0]); tm = np.angle(np.mean(np.exp(1j * th)))
            s = r0 * np.angle(np.exp(1j * (th - tm))); P = np.column_stack([s, pts[:, 2]])
            if len(P) < 20 or (s.max() - s.min()) > r0 * np.pi: continue   # ring/hub loops are not blade sections
            if len(P) > 600: P = P[np.linspace(0, len(P) - 1, 600).astype(int)]
            dd = np.linalg.norm(P[:, None] - P[None], axis=2); i, j = np.unravel_index(np.argmax(dd), dd.shape)
            A, B = P[i], P[j]; ch = B - A; L = np.linalg.norm(ch)
            if L < 1e-6: continue
            e = ch / L; n = np.array([-e[1], e[0]]); x = (P - A) @ e / L; y = (P - A) @ n
            def thick(xc):
                sel = np.abs(x - xc) < 0.03
                return (y[sel].max() - y[sel].min()) if sel.sum() >= 2 else np.nan
            tA, tB = thick(0.08), thick(0.92)
            if not (np.isfinite(tA) and np.isfinite(tB)) or min(tA, tB) <= 0: continue
            le, te = (A, B) if tA > tB else (B, A); ratios.append(max(tA, tB) / min(tA, tB))
            votes.append(int(np.sign(le[0] - te[0]))); pumps.append(int(np.sign(te[1] - le[1])))
    return votes, pumps, ratios

def main(items):
    T = {}
    for name, path in items:
        m = trimesh.load(path, force="mesh"); m = prep(m); m.export(OUT / f"{name}.stl")
        rec = {"faces": len(m.faces), "watertight": bool(m.is_watertight), "tip_r": float(D._tip_radius(m)),
               "z_extent": float(m.bounds[1][2] - m.bounds[0][2])}
        try:
            v, pu, ra = le_truth(m)
        except Exception as exc:
            v, pu, ra = [], [], []; rec["le_err"] = str(exc)[:200]
        c = Counter(v); rec.update(le_votes=dict(c), le_ratio_mean=float(np.mean(ra)) if ra else None, pump_votes=dict(Counter(pu)))
        om_a = None
        if v:
            top, n = c.most_common(1)[0]
            if n / len(v) >= 0.6 and rec["le_ratio_mean"] >= 1.25 and top != 0: om_a = top
        try: tl = D.tip_lead_sign(m)
        except Exception as exc: tl = None; rec["tl_err"] = str(exc)[:200]
        rec["omega_le"], rec["omega_tiplead"] = om_a, tl
        if om_a is not None and tl is not None and om_a != tl: om = None; rec["why_none"] = "LE vs tip-lead disagree"
        else: om = om_a if om_a is not None else tl
        pc = Counter(pu); pump = None
        if pu:
            top, n = pc.most_common(1)[0]
            if n / len(pu) >= 0.6 and top != 0: pump = top
        if om is None or pump is None:
            rec["truth"] = None; rec.setdefault("why_none", "omega unclear" if om is None else "pump unclear")
        else:
            rec["truth"] = [om, pump, om * pump]
        T[name] = rec; print(name, json.dumps(rec), flush=True)
    return T

if __name__ == "__main__":
    items = [(p.stem, str(p)) for p in sorted(SRC.glob("p*.stl"))]
    items += [("a12x25_ref_stl", "validation/reference/a12x25_impeller.stl"), ("fan01_rotor", "validation/reference/fan01/fan01_rotor.stl")]
    T = main(items); json.dump(T, open(sys.argv[1], "w"), indent=1)
