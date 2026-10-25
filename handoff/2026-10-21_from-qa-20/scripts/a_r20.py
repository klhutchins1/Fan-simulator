"""QA r20 A2-A4 (PREREG_R20 2c4380d) on master 027ebcb (run clone qa/run_r20).
Tasks per design: 'mine' (r18 params), 'json' (feature designs, Cursor recipe from the r20 JSON), 'r16' (feature-free,
Cursor's tests.test_one_hub._r16), 'e2e' (build_impeller_parts on stage-1 passers). Resumable jsonl, 1 process per task.
Usage: python a_r20.py <selection.json> <feature_json> <out.jsonl> [workers]"""
import dataclasses, json, os, sys, time
from concurrent.futures import ProcessPoolExecutor, as_completed
R17 = "/workspace/fansim/repo-r17/handoff/2026-10-19_from-qa-17/scripts"
P1 = "/workspace/fansim/repo-r15/handoff/2026-10-17_from-qa-16-hang/data/p1_designed.jsonl"
FJ = sys.argv[2]


def mine(did):
    sys.path.insert(0, R17)
    import p2_built as P2
    r = next(json.loads(l) for l in open(P1) if json.loads(l)["id"] == did)
    return P2.params_of(r)


def zr(p):
    from fansim.geometry import blade as B
    return [float(v) for v in B._hub_axial_range(p)]


def work(did, mode):
    t0 = time.monotonic(); out = {"id": did, "mode": mode}
    try:
        from fansim.fan_spec import get_fan_spec
        from fansim.geometry import blade as B
        from fansim.geometry.features import Features
        from fansim.manufacturability.print_export import mount_hub_params
        from fansim.optimize.search_space import blade_from_flat, blade_to_flat
        spec = get_fan_spec("a12x25"); M = spec.motor_mount
        if mode == "json":
            d = json.load(open(FJ))[did]
            p0 = blade_from_flat(d["flat"], Features(**d["features"]))
            pm = mine(did)
            diff = [f.name for f in dataclasses.fields(p0) if getattr(p0, f.name) != getattr(pm, f.name)]
            out["fields_differ_from_r18_build"] = diff
        elif mode == "r16":
            sys.path.insert(0, "/workspace/fansim/qa/run_r20")
            from tests.test_one_hub import _r16
            p0 = _r16(did)
        else:
            p0 = mine(did)
        out["z_auto"] = zr(p0)
        p, note = mount_hub_params(p0, M); out["z_mount"] = zr(p); out["grow_note"] = note
        if mode == "e2e":
            try:
                B.build_impeller_parts(p); out["e2e"] = "built"
            except ValueError as e:
                out["e2e"] = f"refused: {e}"[:200]
        else:
            solid = B.build_blade_solid(p)
            out["h_built"] = B.blade_hang_built_mm(p)
            out["h_built_reuse"] = B.blade_hang_built_mm(p, solid)
            out["h_designed"] = B.blade_hang_below_hub_mm(p)
            try:
                B.validate_blade_params(p); out["stage1"] = "pass"
            except ValueError as e:
                out["stage1"] = f"refused: {e}"[:200]
            try:
                B._refuse_if_built_hang_past_limit(p, solid); out["stage2"] = "pass"
            except ValueError as e:
                out["stage2"] = f"refused: {e}"[:200]
            if mode == "mine":  # QA-44: Export flat path
                from fansim.cockpit.placement import prepare_export_flat
                flat0 = blade_to_flat(p0)
                fx, ch = prepare_export_flat(flat0, spec, False, p0.features, fit_hub=True)
                out["export_changes"] = [[c.field, c.before, c.after] for c in ch]
                pe = blade_from_flat(fx, p0.features)
                out["section_wrap_export"] = str(pe.section_wrap); out["z_export"] = zr(pe)
                out["hub_radius"] = [p0.hub_radius, pe.hub_radius]
                out["h_built_export"] = B.blade_hang_built_mm(pe)
                # same flat round trip without the hub grow, to separate flat-roundtrip effects
                out["z_flat_roundtrip_auto"] = zr(blade_from_flat(flat0, p0.features))
    except Exception as exc:  # noqa: BLE001
        import traceback
        out["error"] = f"{type(exc).__name__}: {exc}"[:300]; out["tb"] = traceback.format_exc()[-800:]
    out["mono_s"] = round(time.monotonic() - t0, 1)
    return out


def main(sel, fj, outp, workers=3):
    S = json.load(open(sel)); ids = [s["id"] for s in S]; feat = {s["id"]: s["features"] for s in S}
    tasks = [(i, "mine") for i in ids] + [(i, "json") for i in ids if feat[i]] + [(i, "r16") for i in ids if not feat[i]]
    tasks += [(i, "e2e") for i in ids]
    done = {(json.loads(l)["id"], json.loads(l)["mode"]) for l in open(outp)} if os.path.exists(outp) else set()
    todo = [t for t in tasks if t not in done]
    print("tasks", len(tasks), "todo", len(todo), flush=True); t0 = time.monotonic()
    with ProcessPoolExecutor(int(workers), max_tasks_per_child=1) as ex:
        futs = [ex.submit(work, *t) for t in todo]
        for k, f in enumerate(as_completed(futs)):
            rec = f.result()
            with open(outp, "a") as fh: fh.write(json.dumps(rec) + "\n")
            print(k + 1, rec["id"], rec["mode"], rec.get("error") or rec.get("h_built", rec.get("e2e", ""))[:60] if isinstance(rec.get("h_built", rec.get("e2e", "")), str) else round(rec["h_built"], 4), rec["mono_s"], round(time.monotonic() - t0), flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
