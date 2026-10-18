"""QA r16 hang (PREREG 52eca5f) P2: built hang = z_face - min z of the realised loft section points
(prepare_loft_chords), plus the chord-only stage, and an untrimmed/unclipped STL check on the first 25.
Selection: seeded 16002 draw of <=220 designs with h_d > 0 and 80 with s_d in [-2, 0]. Resumable.
Usage: python p2_built.py <p1.jsonl> <out.jsonl> [workers]"""
import json, math, os, random, sys, time
from concurrent.futures import ProcessPoolExecutor, as_completed

R7 = "/workspace/fansim/repo-r7/handoff/2026-10-11_from-qa-7/stress/inputs.jsonl.gz"


def select(p1):
    P = [json.loads(l) for l in open(p1)]
    hang = [r for r in P if r["s_d"] > 0]; near = [r for r in P if -2.0 <= r["s_d"] <= 0.0]
    rng = random.Random(16002); rng.shuffle(hang); rng.shuffle(near)
    sel = hang[:220] + near[:80]
    random.Random(16002).shuffle(sel)
    return sel


def params_of(r):
    import gzip
    from fansim.geometry.features import Features
    from fansim.optimize.search_space import blade_from_flat, suggest_params, blade_to_flat
    if r["src"] == "r7":
        x = next(json.loads(l) for l in gzip.open(R7) if json.loads(l)["id"] == r["id"])
        p = blade_from_flat(dict(x["flat"], section_wrap="cylinder"), Features(**(x.get("features") or {})))
    else:
        import optuna
        optuna.logging.set_verbosity(optuna.logging.WARNING)
        st = optuna.create_study(sampler=optuna.samplers.RandomSampler(seed=16001)); k = int(r["id"][2:])
        for j in range(k + 1):
            tr = st.ask(); bp = suggest_params(tr, space="guided", with_extended=True)
        flat = blade_to_flat(bp); flat["hub_radius"] = bp.hub_radius; flat["tip_radius"] = bp.tip_radius
        p = blade_from_flat(dict(flat, section_wrap="cylinder"), Features())
    p.section_wrap = "cylinder"
    return p


def sec_zmin(p, B):
    it = B._interp_stations(p, p.n_span); r0 = p.hub_radius - p.root_embed; kw = B._thick_scale_kw(p); best = (math.inf, None)
    for i in range(p.n_span):
        rf = float(it["r_frac"][i])
        pts = B._section_points_3d(r=r0 + (p.tip_radius - r0) * rf, r_frac=rf, chord=float(it["chord"][i]),
            stagger_deg=float(it["stagger_deg"][i]), thickness=float(it["thickness"][i]), max_camber=float(it["max_camber"][i]),
            camber_pos=float(it["camber_pos"][i]), sweep=float(it["sweep"][i]), skew=float(it["skew"][i]),
            le_sweep=float(it["le_sweep"][i]), lean_deg=float(it["lean_deg"][i]), n_chord=p.n_chord, features=p.features,
            le_skew=float(it["le_skew"][i]), tip_notch_count=p.tip_notch_count, tip_notch_depth_mm=p.tip_notch_depth_mm, **kw)
        z = min(v.z for v in pts)
        if z < best[0]: best = (z, rf)
    return best


def work(r, do_stl):
    t0 = time.monotonic(); out = {"id": r["id"], "src": r["src"], "s_d": r["s_d"], "h_d": r["h_d"]}
    try:
        from fansim.geometry import blade as B
        from fansim.geometry.chord_realisation import loft_chords_for_measured_targets, with_loft_chords, correct_clipped_sections
        p = params_of(r); face = float(B._hub_axial_range(p)[0])
        loft = with_loft_chords(p, loft_chords_for_measured_targets(p))
        z1, rf1 = sec_zmin(loft, B)
        pr = correct_clipped_sections(loft, p)
        zb, rfb = sec_zmin(pr, B)
        out.update(face=face, s_chordonly=face - z1, s_b=face - zb, h_b=max(0.0, face - zb), low_rf_b=rfb,
                   r_frac=[s.r_frac for s in p.stations], chord_design=[s.chord for s in p.stations],
                   chord_loft=[s.chord for s in pr.stations], stagger_design=[s.stagger_deg for s in p.stations],
                   stagger_loft=[s.stagger_deg for s in pr.stations], camber_design=[s.max_camber for s in p.stations],
                   camber_loft=[s.max_camber for s in pr.stations], n_span=int(p.n_span))
        if do_stl:
            import trimesh
            from fansim.geometry import export_stl
            fn = f"/tmp/qa16_p2_{os.getpid()}.stl"
            export_stl(B.build_blade_solid(pr, _chord_realized=True, _trim_tip=False), fn)
            out["s_b_stl"] = face - float(trimesh.load(fn, force="mesh").bounds[0][2]); os.remove(fn)
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"{type(exc).__name__}: {exc}"[:300]
    out["mono_s"] = round(time.monotonic() - t0, 1)
    return out


def main(p1, out, workers=3):
    sel = select(p1); done = {json.loads(l)["id"] for l in open(out)} if os.path.exists(out) else set()
    stl_ids = {r["id"] for r in sel[:25]}
    todo = [r for r in sel if r["id"] not in done]
    print("selected", len(sel), "todo", len(todo), flush=True); t0 = time.monotonic()
    with ProcessPoolExecutor(int(workers), max_tasks_per_child=1) as ex:
        futs = [ex.submit(work, r, r["id"] in stl_ids) for r in todo]
        for k, f in enumerate(as_completed(futs)):
            rec = f.result()
            with open(out, "a") as fh: fh.write(json.dumps(rec) + "\n")
            print(k + 1, rec["id"], rec.get("error") or (round(rec["s_d"], 2), round(rec["s_b"], 2)), rec["mono_s"],
                  round(time.monotonic() - t0), flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
