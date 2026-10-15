# REFERENCE ONLY (QA research handoff 2026-10-14, lead #13). Not imported by fansim. Needs scikit-fem, pytetwild, pyvista, meshio.
"""Lead #13 feasibility: Stock blade f1 by 3-D tet FEA (own code, written from scikit-fem's public API,
not copied from ex21). Root clamped at hub radius. Run with /tmp/fea-venv."""
import time, resource, math, sys, numpy as np, meshio, pytetwild
import skfem as fem
from skfem.models.elasticity import linear_elasticity, lame_parameters
from scipy.sparse.linalg import eigsh
t0 = time.time()
STL = "/workspace/fansim/repo-r10/validation/reference/a12x25_impeller.stl"
HUB, TIP, NB = 21.5, 54.5, 9
E = 2.1e9*0.70; NU = 0.35; RHO = 1270.0          # PETG x FDM_E_K, as fansim
m = meshio.read(STL); V = m.points.astype(float); F = m.cells_dict["triangle"]
r = np.hypot(V[:,0], V[:,1]); print("stl bbox", V.min(0).round(1), V.max(0).round(1), "rmax", r.max().round(1), len(F), "tris")
edge = float(sys.argv[1]) if len(sys.argv) > 1 else 0.03
import os
cache = f"/tmp/tw_{edge}.npz"
if os.path.exists(cache): z = np.load(cache); tv, tt = z["v"], z["t"]
else:
    tv, tt = pytetwild.tetrahedralize(V, F, edge_length_fac=edge); np.savez(cache, v=tv, t=tt)
t1 = time.time(); print(f"tetwild {t1-t0:.1f}s  {len(tv)} nodes {len(tt)} tets")
c = tv[tt].mean(1); rc = np.hypot(c[:,0], c[:,1]); th = np.arctan2(c[:,1], c[:,0])
# pick blade around the angle of the outermost tet, wedge +-180/NB deg, radially outside hub
blade_th = th[np.argmax(rc)]
d = np.angle(np.exp(1j*(th-blade_th)))
sel = (rc > HUB - 0.3) & (np.abs(d) < math.pi/NB)
tt = tt[sel]
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
n = len(tv); rows = np.repeat(np.arange(len(tt)), 4); A = coo_matrix((np.ones(rows.size), (rows, tt.ravel())), shape=(len(tt), n)).tocsr()
nc, lab = connected_components(A @ A.T, directed=False)
cr = np.hypot(*tv[tt].mean(1)[:, :2].T); rootc = set(lab[cr < HUB+1.5])
keep = np.isin(lab, list(rootc)); print("components", nc, "kept tets", keep.sum(), "of", len(tt)); tt = tt[keep]
used = np.unique(tt); remap = -np.ones(len(tv), int); remap[used] = np.arange(len(used))
P = tv[used]*1e-3; T = remap[tt]
mesh = fem.MeshTet(P.T.copy(), T.T.copy())
e = fem.ElementVector(fem.ElementTetP2()); ib = fem.Basis(mesh, e)
K = linear_elasticity(*lame_parameters(E, NU)).assemble(ib)
@fem.BilinearForm
def mass(u, v, w): return RHO*fem.helpers.dot(u, v)
M = mass.assemble(ib)
rn = np.hypot(mesh.p[0], mesh.p[1])
root = ib.get_dofs(lambda x: np.hypot(x[0], x[1]) < (HUB+0.8)*1e-3)
I = ib.complement_dofs(root)
w2, _ = eigsh(K[I][:,I], k=4, M=M[I][:,I], sigma=0, which="LM")
f = np.sqrt(np.abs(w2))/2/math.pi
t2 = time.time()
print(f"blade tets {mesh.t.shape[1]}, dofs {K.shape[0]}, solve {t2-t1:.1f}s, total {t2-t0:.1f}s, maxRSS {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024:.0f} MB")
print("f (Hz, non-rotating):", f.round(0))
# Southwell: f_rot^2 = f0^2 + S*Omega^2, S~1.17 (uniform cantilever 1st flap, textbook); 2000 rpm
Om = 2000/60; print("Southwell f1 @2000rpm (S=1.17):", round(math.sqrt(f[0]**2+1.17*Om**2),1), " BPF", 9*Om)
