"""QA r16 hang (PREREG 52eca5f) Option B: hub skirt via fansim's own params (hub_height_mm + blade_hub_z_mm, all growth
below the hub, top face fixed). No fansim source edits. Gates G1-G6 per the prereg.
Usage: python optB.py drive <p1.jsonl> <p2.jsonl> <out.jsonl> [workers]   (driver; one subprocess per design, 900 s cap)
       python optB.py one <p1.jsonl> <id>                                  (prints one JSON record)"""
import json, math, os, random, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)


def blade_vol(p, face, B):
    """Volume of one chord-realised blade, clipped at z=face (no validator), untrimmed tip is NOT used: trimmed."""
    from fansim.geometry.chord_realisation import prepare_loft_chords
    pr = prepare_loft_chords(p); bl = B.build_blade_solid(pr, _chord_realized=True)
    bl = B.clip_blade_below(p, bl, face)
    return float(bl.Volume()), pr


def one(p1, did):
    import trimesh
    from p2_built import params_of
    from optA import min_z
    from fansim.geometry import blade as B
    from fansim.geometry import export_stl
    from fansim.fan_spec import get_fan_spec, estimate_weight_g
    from fansim.manufacturability.print_export import build_impeller_with_mount, mount_hub_params
    from fansim.cockpit.placement import impeller_z_extent
    from fansim.optimize.system_curve import bem_screen_cfm
    t0 = time.monotonic(); P1 = {json.loads(l)["id"]: json.loads(l) for l in open(p1)}; r = P1[did]
    spec = get_fan_spec("a12x25"); mount = spec.motor_mount
    p = params_of(r); face0, top0 = B._hub_axial_range(p); h0 = top0 - face0; bias0 = float(p.blade_hub_z_mm or 0.0)
    rec = dict(id=did, h_d=r["h_d"], face0=face0, top0=top0, hub_h0=h0, hub_r=p.hub_radius, n_blades=p.n_blades)
    e = math.ceil((r["h_d"] + 0.5) * 10) / 10; passes = []
    for _ in range(3):
        pe = replace(p, hub_height_mm=h0 + e, blade_hub_z_mm=bias0 + e / 2)
        fe, te = B._hub_axial_range(pe)
        from fansim.geometry.chord_realisation import prepare_loft_chords
        pre = prepare_loft_chords(pe); s_b_ext = float(fe - min_z(pre)); passes.append(dict(e=e, face=fe, top=te, s_b_ext=s_b_ext))
        if s_b_ext <= 0.0: break
        e = math.ceil((e + s_b_ext + 0.5) * 10) / 10
    rec.update(e=e, passes=passes, face_ext=fe, top_ext=te, top_fixed=abs(te - top0) < 1e-9,
               hang_designed_ext=B.blade_hang_below_hub_mm(pe), s_b_ext=s_b_ext)
    try:
        B.validate_blade_params(pe); rec["validator_ok"] = True
    except ValueError as exc:
        rec["validator_ok"] = False; rec["validator_msg"] = str(exc)[:200]
    # mount growth (export path) and the realistic baselines
    pm, note = mount_hub_params(pe, mount); fm, tm = B._hub_axial_range(pm); rec.update(mount_note=note, face_final=fm, hub_h_final=tm - fm)
    pb15, _ = mount_hub_params(p, mount); fb15, tb15 = B._hub_axial_range(pb15)
    rec.update(hub_h_base15=tb15 - fb15, face_base15=fb15, hang_designed_base15=B.blade_hang_below_hub_mm(pb15))
    # G4 depth
    rec.update(depth_base=impeller_z_extent(p), depth_base15=impeller_z_extent(pb15), depth_final=impeller_z_extent(pm))
    rec["G4_depth_ok"] = rec["depth_final"] <= spec.depth_mm[1] + 1e-9
    # report-only: the skirt is what pushes the depth over (the base design fitted before)
    rec["G4_fail_caused_by_skirt"] = (not rec["G4_depth_ok"]) and rec["depth_base15"] <= spec.depth_mm[1] + 1e-9
    # G5 mass (single-blade CAD volumes x n + analytic hub cylinders)
    R = float(p.hub_radius); vb0, _ = blade_vol(p, face0, B); vbe, _ = blade_vol(pm, fm, B); vb15, _ = blade_vol(pb15, fb15, B)
    hubv = lambda h: math.pi * R * R * h
    dV_auto = hubv(tm - fm) - hubv(h0) + p.n_blades * (vbe - vb0)
    dV_15 = hubv(tm - fm) - hubv(tb15 - fb15) + p.n_blades * (vbe - vb15)
    rec.update(blade_vol_base=vb0, blade_vol_ext=vbe, blade_vol_base15=vb15, dV_vs_auto_mm3=dV_auto, dV_vs_base15_mm3=dV_15,
               dm_vs_auto_g20=estimate_weight_g(dV_auto, "PETG"), dm_vs_auto_gsolid=estimate_weight_g(dV_auto, "PETG", infill_frac=1.0),
               dm_vs_base15_g20=estimate_weight_g(dV_15, "PETG"), dm_vs_base15_gsolid=estimate_weight_g(dV_15, "PETG", infill_frac=1.0))
    # G6 BEM + annulus
    q_b = bem_screen_cfm(p, 2000.0, 10.0, 0.5); q_e = bem_screen_cfm(pm, 2000.0, 10.0, 0.5)
    rec.update(bem_base=q_b, bem_ext=q_e, bem_free_change_pct=100 * (q_e[0] - q_b[0]) / q_b[0] if q_b[0] else None,
               annulus_change_pct=0.0, skirt_wetted_mm2=2 * math.pi * R * (tm - fm - max(h0, tb15 - fb15)))
    # G1/G2/G3 full impeller with the a12x25 cup
    t1 = time.monotonic()
    try:
        model, fits, msg = build_impeller_with_mount(pm, mount)
        fn = f"/tmp/qa16_optB_{did}.stl"; export_stl(model, fn); m = trimesh.load(fn, force="mesh")
        bodies = m.split(only_watertight=False)
        lo, hi = m.bounds
        rec.update(build_ok=True, mount_fits=bool(fits), mount_msg=msg, watertight=bool(m.is_watertight), n_bodies=len(bodies),
                   mesh_volume=float(m.volume), mesh_zmin=float(lo[2]), mesh_zmax=float(hi[2]), mesh_xy=[float(hi[0] - lo[0]), float(hi[1] - lo[1])],
                   mass_total_g20=estimate_weight_g(float(m.volume), "PETG"), build_s=round(time.monotonic() - t1, 1))
        rec["G1_mesh_ok"] = bool(rec["validator_ok"] and m.is_watertight and len(bodies) == 1 and m.volume > 0)
        rec["G2_bed_ok"] = (lo[2] >= fm - 0.05) and (hi[2] - lo[2] <= 250) and max(rec["mesh_xy"]) <= 220
        rec["G3_cup_ok"] = bool(fits) and (tm - fm) >= max(mount.min_hub_height_mm, mount.cavity_depth_mm + mount.min_wall_mm) - 1e-6
        os.remove(fn)
    except Exception as exc:  # noqa: BLE001
        rec.update(build_ok=False, build_error=f"{type(exc).__name__}: {exc}"[:300], G1_mesh_ok=False, G2_bed_ok=False, G3_cup_ok=False)
    rec["G5_mass_ok"] = rec["dm_vs_auto_g20"] <= 2.0 and rec["dm_vs_auto_gsolid"] <= 8.0 and rec.get("mass_total_g20", 0) <= spec.max_weight_g
    rec["G6_aero_ok"] = rec["bem_free_change_pct"] is not None and abs(rec["bem_free_change_pct"]) <= 1.0
    rec["rescued"] = all(rec.get(k) for k in ("G1_mesh_ok", "G2_bed_ok", "G3_cup_ok", "G4_depth_ok", "G5_mass_ok", "G6_aero_ok"))
    rec["mono_s"] = round(time.monotonic() - t0, 1)
    print(json.dumps(rec, default=float))


def drive(p1, p2, out, workers=2):
    Q = [json.loads(l) for l in open(p2)]; Q = [q for q in Q if q.get("h_b", 0) > 2.0]
    ids = sorted(q["id"] for q in Q); random.Random(16005).shuffle(ids); ids = ids[:30]
    done = {json.loads(l)["id"] for l in open(out)} if os.path.exists(out) else set()
    todo = [i for i in ids if i not in done]; print("R", len(ids), "todo", len(todo), flush=True); t0 = time.monotonic()

    def run(did):
        t = time.monotonic()
        try:
            cp = subprocess.run([sys.executable, __file__, "one", p1, did], capture_output=True, text=True, timeout=900)
            line = [l for l in cp.stdout.splitlines() if l.startswith("{")]
            rec = json.loads(line[-1]) if line else dict(id=did, error=("rc=%d " % cp.returncode) + cp.stderr[-300:])
        except subprocess.TimeoutExpired:
            rec = dict(id=did, error="timeout 900 s")
        rec.setdefault("mono_s", round(time.monotonic() - t, 1))
        with open(out, "a") as fh: fh.write(json.dumps(rec) + "\n")
        print(did, rec.get("error") or (rec["e"], rec["rescued"]), rec["mono_s"], round(time.monotonic() - t0), flush=True)

    with ThreadPoolExecutor(int(workers)) as ex:
        list(ex.map(run, todo))
    print("DONE", flush=True)


if __name__ == "__main__":
    {"drive": drive, "one": one}[sys.argv[1]](*sys.argv[2:])
