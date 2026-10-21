"""QA r18 A (PREREG_R18 5df5059): built hang on the built blade solid at the export hub (R1.7 semantics).
Tasks: (id, 'x') all 10; (id, 'x_rep') S2_0269/S5_0207/G_0502; ('S2_0269', 'auto'). Resumable jsonl, 1 process per task.
Usage: python a_built.py <p1.jsonl> <selection.json> <out.jsonl> [workers]"""
import json, os, sys, time
from concurrent.futures import ProcessPoolExecutor, as_completed
HERE = "/workspace/fansim/qa/r18/scripts"; R17 = "/workspace/fansim/repo-r17/handoff/2026-10-19_from-qa-17/scripts"


def zmin_optimal(shape):
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    b = Bnd_Box(); BRepBndLib.AddOptimal_s(shape.wrapped, b, False, False)
    return b.CornerMin().Z()


def work(r, mode):
    t0 = time.monotonic(); out = {"id": r["id"], "mode": mode}
    try:
        sys.path.insert(0, R17)
        import p2_built as P2
        from c_common import export_hub
        from fansim.geometry import blade as B
        p0 = P2.params_of(r)
        if mode == "auto":
            p, d = p0, 0.0
        elif mode == "mount":  # supplementary (post-hoc): today's export path, mount_hub_params grows the hub symmetrically
            from c_common import MOUNT
            from fansim.manufacturability.print_export import mount_hub_params
            z0, z1 = B._hub_axial_range(p0); p, _ = mount_hub_params(p0, MOUNT); x0, x1 = B._hub_axial_range(p); d = (z0 - x0)
            out["dh_top"] = x1 - z1
        else:
            p, d = export_hub(p0)
        zf = float(B._hub_axial_range(p)[0])
        solid = B.build_blade_solid(p); tb = time.monotonic() - t0
        zo = zmin_optimal(solid)
        zv = min(v.Z for v in solid.Vertices())
        verts, _ = solid.tessellate(0.005, 0.1); zm = min(v.z for v in verts)
        cl = B.clip_blade_below(p, solid, zf); zc = zmin_optimal(cl)
        out.update(dh=d, z_face=zf, z_min=zo, s=zf - zo, h=max(0.0, zf - zo), z_vert=zv, h_vert=max(0.0, zf - zv),
                   z_mesh=zm, h_mesh=max(0.0, zf - zm), z_clipped=zc, clip_ok=zc >= zf - 0.01,
                   h_designed=B.blade_hang_below_hub_mm(p), n_faces=len(solid.Faces()), build_s=round(tb, 1))
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"{type(exc).__name__}: {exc}"[:300]
    out["mono_s"] = round(time.monotonic() - t0, 1)
    return out


def main(p1, sel, out, workers=3, supp=""):
    P = {json.loads(l)["id"]: json.loads(l) for l in open(p1)}
    ids = [s["id"] for s in json.load(open(sel))]
    tasks = [(i, "x") for i in ids] + [(i, "x_rep") for i in ("S2_0269", "S5_0207", "G_0502")] + [("S2_0269", "auto")]
    if supp:  # supplementary, post-hoc (not pre-registered): auto hub and today's mount_hub_params hub for all 10
        tasks += [(i, "auto") for i in ids if i != "S2_0269"] + [(i, "mount") for i in ids]
    done = {(json.loads(l)["id"], json.loads(l)["mode"]) for l in open(out)} if os.path.exists(out) else set()
    todo = [t for t in tasks if t not in done]
    print("tasks", len(tasks), "todo", len(todo), flush=True); t0 = time.monotonic()
    with ProcessPoolExecutor(int(workers), max_tasks_per_child=1) as ex:
        futs = [ex.submit(work, P[i], m) for i, m in todo]
        for k, f in enumerate(as_completed(futs)):
            rec = f.result()
            with open(out, "a") as fh: fh.write(json.dumps(rec) + "\n")
            print(k + 1, rec["id"], rec["mode"], rec.get("error") or round(rec["h"], 4), rec["mono_s"], round(time.monotonic() - t0), flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
