"""QA r9 Task E analysis: shrouded fuse memory (27.1). For each build: n_faces / VmRSS / VmHWM at the
check_fuse_memory call and VmHWM at worker exit (round-8 hook_c). Ring cost = shrouded minus its unshrouded twin
(same design, shroud_thick_mm=0): d_faces, d_HWM, d_increment. Three models for the ring's extra HWM over the
fuse estimate, compared by leave-one-out RMSE: constant; per ring-face rate (through 0); linear in ring height
(shroud_height_frac). Run with PYTHONPATH=/tmp/r9master (master's fansim.resources).
Usage: python analyse_e.py <qa9e.jsonl>"""
import json, sys
import numpy as np
from fansim.resources import fuse_peak_estimate_gb, FUSE_MARGIN
G = 1048576
R = {}
for l in open(sys.argv[1]):
    r = json.loads(l)
    if r.get("outcome") != "OK": R[r["id"]] = r; continue
    calls = [e for e in r["events"] if e["ev"] == "call"]; ex = [e for e in r["events"] if e["ev"] == "exit"]
    if not calls or not ex: r["no_events"] = True; R[r["id"]] = r; continue
    c, x = calls[0], ex[-1]
    r.update(n_faces=c["n_faces"], rss_call=c["VmRSS"] / G, hwm=x["VmHWM"] / G, inc=x["VmHWM"] / G - c["VmRSS"] / G,
             avail_call=c["MemAvailable"] / G, est=fuse_peak_estimate_gb(c["n_faces"]))
    r["over_est"] = r["hwm"] - r["est"]; r["guard_covers"] = r["hwm"] <= FUSE_MARGIN * r["est"]
    r["inc_le_guard_need"] = r["inc"] <= FUSE_MARGIN * r["est"]   # growth after the call <= what the guard asks for
    r["fit_r8_hwm"] = 1.02 + 92.5 * c["n_faces"] / G   # round-8 unshrouded fit (GB)
    r["resid_r8"] = r["hwm"] - r["fit_r8_hwm"]; r.pop("events", None); R[r["id"]] = r
pairs = []
for k, r in R.items():
    if r.get("kind") == "shrouded" and "hwm" in r and "hwm" in R.get(k + "_twin", {}):
        t = R[k + "_twin"]
        pairs.append({"id": k, "h": r["shroud_height_frac"], "n_blades": r["n_blades"], "faces": r["n_faces"], "twin_faces": t["n_faces"],
                      "d_faces": r["n_faces"] - t["n_faces"], "hwm": r["hwm"], "twin_hwm": t["hwm"], "d_hwm": r["hwm"] - t["hwm"],
                      "d_inc": r["inc"] - t["inc"], "inc": r["inc"], "guard_need": FUSE_MARGIN * r["est"], "inc_le_guard_need": r["inc_le_guard_need"], "over_est": r["over_est"], "twin_over_est": t["over_est"],
                      "resid_r8": r["resid_r8"], "twin_resid_r8": t["resid_r8"], "guard_covers": r["guard_covers"], "est": r["est"]})
y = np.array([p["over_est"] for p in pairs]); f = np.array([p["d_faces"] for p in pairs], float); h = np.array([p["h"] for p in pairs])
def loo(pred_fn):
    e = []
    for i in range(len(y)):
        m = np.ones(len(y), bool); m[i] = False; e.append(y[i] - pred_fn(m, i))
    return float(np.sqrt(np.mean(np.square(e)))), float(np.max(np.abs(e)))
models = {}
if len(y) >= 3:
    models["constant"] = {"value_gb": float(y.mean()), "loo_rmse_max": loo(lambda m, i: y[m].mean())}
    rate = lambda m: float((f[m] @ y[m]) / (f[m] @ f[m]))
    models["per_ring_face"] = {"kb_per_face": rate(np.ones(len(y), bool)) * G, "loo_rmse_max": loo(lambda m, i: rate(m) * f[i])}
    def lin(m):
        A = np.column_stack([np.ones(m.sum()), h[m]]); return np.linalg.lstsq(A, y[m], rcond=None)[0]
    a, b = lin(np.ones(len(y), bool))
    models["ring_height"] = {"a_gb": float(a), "b_gb_per_frac": float(b), "loo_rmse_max": loo(lambda m, i: lin(m) @ [1, h[i]])}
    A = np.column_stack([np.ones(len(y)), f]); c0, c1 = np.linalg.lstsq(A, y, rcond=None)[0]
    models["const_plus_face (extra)"] = {"a_gb": float(c0), "kb_per_face": float(c1) * G,
                                         "loo_rmse_max": loo(lambda m, i: np.linalg.lstsq(np.column_stack([np.ones(m.sum()), f[m]]), y[m], rcond=None)[0] @ [1, f[i]])}
tf = np.array([p["twin_faces"] for p in pairs], float); dh = np.array([p["d_hwm"] for p in pairs])
if len(dh) >= 3:
    A = np.column_stack([np.ones_like(tf), tf]); c0, c1 = np.linalg.lstsq(A, dh, rcond=None)[0]
    e = [dh[i] - A[i] @ np.linalg.lstsq(A[np.arange(len(dh)) != i], dh[np.arange(len(dh)) != i], rcond=None)[0] for i in range(len(dh))]
    models["d_hwm_vs_blade_faces (post hoc)"] = {"a_gb": float(c0), "kib_per_blade_face": float(c1) * 1048576,
        "loo_rmse_max": (float(np.sqrt(np.mean(np.square(e)))), float(np.max(np.abs(e))))}
ctl = [R[k] for k in R if R[k].get("kind") in ("control", "twin") and "hwm" in R[k]]
O = {"n_ok": sum(1 for r in R.values() if "hwm" in r), "not_ok": [(k, r.get("outcome"), r.get("err")) for k, r in R.items() if "hwm" not in r],
     "pairs": pairs, "models_over_estimate_gb": models,
     "unshrouded_over_est_gb": {"n": len(ctl), "mean": float(np.mean([r["over_est"] for r in ctl])) if ctl else None,
                                "max": float(np.max([r["over_est"] for r in ctl])) if ctl else None},
     "unshrouded_resid_vs_r8_fit_gb": [round(r["resid_r8"], 3) for r in ctl],
     "guard_covers_shrouded": sum(p["guard_covers"] for p in pairs), "inc_le_guard_need_shrouded": sum(p["inc_le_guard_need"] for p in pairs),
     "inc_le_guard_need_unshrouded": sum(r["inc_le_guard_need"] for r in R.values() if r.get("kind") in ("control", "twin") and "inc" in r), "n_pairs": len(pairs),
     "corr_dhwm_dfaces": float(np.corrcoef([p["d_hwm"] for p in pairs], f)[0, 1]) if len(pairs) > 2 else None,
     "corr_dhwm_h": float(np.corrcoef([p["d_hwm"] for p in pairs], h)[0, 1]) if len(pairs) > 2 else None,
     "controls": [{k: r.get(k) for k in ("id", "kind", "n_faces", "hwm", "est", "over_est", "inc", "rss_call", "mono_s")} for r in ctl]}
print(json.dumps(O, indent=1, default=float))
