"""QA r14 Task C3 (PREREG_R14 586bbe9): first 40 allowed designs of the C sample (RandomSampler 14003, guided, cockpit
settings), 2-blade build_impeller (shipped path), measure_sections at _station_measure_fracs, family-aware estimator bias
(r10b c2 method). Rule: chord 3 % / net camber 0.005 / stagger 1.5 deg. Resumable. Usage: c3_build.py <out.jsonl>"""
import json, os, sys, time, dataclasses
import numpy as np, optuna
import fansim; assert fansim.__file__.startswith("/workspace/fansim/qa/run_r14"), fansim.__file__
optuna.logging.set_verbosity(optuna.logging.WARNING)
from fansim.geometry import build_impeller, export_stl
from fansim.geometry.airfoil import section_loop_2d, SECTION_PLATE
from fansim.optimize.search_space import suggest_params
from fansim.optimize.study import optimizer_max_tip_radius
from fansim.fan_spec import get_fan_spec, mount_min_hub_radius
from fansim.validation.section_compare import measure_sections, _measure_loop
from fansim.geometry import chord_realisation as CR
from fansim.geometry.blade import validate_blade_params, blade_hang_below_hub_mm, _thick_scale_kw
spec = get_fan_spec("a12x25"); lo = mount_min_hub_radius(spec); HUB = (lo, max(lo + 0.1, spec.hub_dia_mm[1] / 2)); MT = optimizer_max_tip_radius(spec)
st = optuna.create_study(sampler=optuna.samplers.RandomSampler(seed=14003)); todo = []
for i in range(300):
    tr = st.ask(); p = suggest_params(tr, space="guided", hub_radius_range=HUB, max_tip_radius=MT)
    try: validate_blade_params(p)
    except ValueError: continue
    todo.append((i, p))
    if len(todo) == 40: break
def bias(p, s, n=200):
    kw = _thick_scale_kw(p); fam = kw["section_family"]
    le, te = (kw["le_thick_scale"], kw["te_thick_scale"]) if fam == SECTION_PLATE else (1.0, 1.0)
    loop = np.asarray(section_loop_2d(fam, max_camber=s.max_camber, camber_pos=s.camber_pos, thickness=s.thickness, n_points=n, te_radius_frac=te, le_radius_frac=le), float)
    X2, Y2 = loop[:, 0] * 30.0, loop[:, 1] * 30.0; Rb = 1e4; th = X2 / Rb
    r = _measure_loop(np.column_stack([Rb * np.cos(th), Rb * np.sin(th), Y2]), Rb, 1, 1)
    return r["camber_ratio"] - s.max_camber, fam
def avail():
    for l in open("/proc/meminfo"):
        if l.startswith("MemAvailable"): return int(l.split()[1]) / 1048576
OUT = sys.argv[1]; done = {json.loads(l)["i"] for l in open(OUT)} if os.path.exists(OUT) else set()
print("todo", len(todo), flush=True)
for i, p in todo:
    if i in done: continue
    t0 = time.monotonic(); rec = {"i": i, "hang": blade_hang_below_hub_mm(p), "n_blades": p.n_blades}
    try:
        g = time.monotonic()
        while avail() < 2.5 and time.monotonic() - g < 600: time.sleep(10)
        rec["family"] = _thick_scale_kw(p)["section_family"]
        stl = "/tmp/qa14c3.stl"; export_stl(build_impeller(dataclasses.replace(p, n_blades=2, blade_angles_deg=None)), stl)
        fr = CR._station_measure_fracs(p); idx = [k for k, f in enumerate(fr) if f is not None]
        meas = measure_sections(stl, tuple(fr[k] for k in idx), tip_radius_mm=p.tip_radius)
        rows = []
        for k, m in zip(idx, meas):
            s = p.stations[k]; cb, fam = bias(p, s)
            y = {"k": k, "r_frac": s.r_frac, "r_mm": round(fr[k] * p.tip_radius, 2), "chord_p": s.chord, "stagger_p": s.stagger_deg, "camber_p": s.max_camber, "bias": cb, "n_read": m.get("n_blades", 0)}
            if m.get("n_blades"):
                y.update(chord_m=m["chord_mm"], stagger_m=m["stagger_deg"], camber_m=m["camber_ratio"])
                y["chord_err"] = m["chord_mm"] / s.chord - 1; y["camber_gap_net"] = m["camber_ratio"] - s.max_camber - cb; y["stagger_err"] = m["stagger_deg"] - s.stagger_deg
                y["fail"] = abs(y["chord_err"]) > 0.03 or abs(y["camber_gap_net"]) > 0.005 or abs(y["stagger_err"]) > 1.5
            rows.append(y)
        rec["stations"] = rows; rec["n_none"] = sum(f is None for f in fr)
    except Exception as exc:  # noqa: BLE001
        rec["error"] = f"{type(exc).__name__}: {exc}"[:400]
    rec["mono_s"] = round(time.monotonic() - t0, 1)
    with open(OUT, "a") as fh: fh.write(json.dumps(rec, default=float) + "\n")
    print(i, rec.get("error") or sum(y.get("fail", False) for y in rec["stations"]), rec["mono_s"], flush=True)
print("DONE", flush=True)
