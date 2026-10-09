"""Round-4 request 1: dump axial-force BEM results for all screen-r3 designs + Stock + paddle/reversed
from the CURRENT clone (run from the clone root). Usage: python xcheck_dump.py <tag> <out.jsonl>"""
import copy, functools, json, os, sys, time
sys.path.insert(0, os.getcwd()); sys.path.insert(0, "/workspace/fansim/screen")
import fansim.fan_bem as FB
from fansim.optimize import search_space as SS
from fansim.geometry.blade import BladeParams
from fansim.geometry.config import load_blade_params
import bem_screen as S
tag, out = sys.argv[1], sys.argv[2]
try:
    from fansim.optimize.system_curve import bem_exploit_reason, EXPLOIT_MIN_PEAK_EFF
except ImportError:
    bem_exploit_reason, EXPLOIT_MIN_PEAK_EFF = None, 0.05
LAST = {}
def pq_rec(*a, **k):
    c = FB.pq_curve(*a, pressure_model="axial_force", **k); LAST["c"] = c; return c
S.pq_curve = pq_rec
S.operating_point = functools.partial(FB.operating_point, pressure_model="axial_force")
SS.BOUNDS[S.SPACE]["max_camber"] = (SS.BOUNDS[S.SPACE]["max_camber"][0], 0.10)
rule = lambda c: ("no_rise" if c.free_status == "no_rise" else ("low_eff" if float(c.peak_efficiency) < EXPLOIT_MIN_PEAK_EFF else ""))
def curve_d(c):
    return dict(free=float(c.free_delivery_cfm), shut=float(c.shutoff_dp_pa), peak_eff=float(c.peak_efficiency),
                status=c.free_status, guard_rule=rule(c))
stock = load_blade_params("config/problems/a12x25_reference.yaml")
st_eval = S.evaluate(stock, {})
def restag(v):
    p = copy.deepcopy(stock)
    for s in p.stations: s.stagger_deg = v
    return p
fh = open(out, "w"); t0 = time.time()
specials = {"stock7": stock, "paddle89": restag(89.0), "rev-45": restag(-45.0), "rev-60": restag(-60.0), "zero_blades": BladeParams(n_blades=0)}
for n, p in specials.items():
    rec = dict(id=n, kind="special", default_gap=curve_d(FB.pq_curve(p, 2000.0, pressure_model="axial_force")))
    if bem_exploit_reason and p.n_blades > 0:
        rec["guard_fn"] = bem_exploit_reason(p, 2000.0, None)
    fh.write(json.dumps(rec) + "\n")
rows = [json.loads(l) for l in open("/workspace/fansim/research/screen_r3/all_designs.jsonl")]
for i, r in enumerate(rows):
    flat = r["flat"]; bp = S.blade_from_flat(dict(flat)); LAST.clear()
    try:
        e = S.evaluate(bp, dict(flat))
    except Exception as exc:  # noqa: BLE001
        e = {"first_fail": "exception", "feasible": False, "error": repr(exc), "flags": {}}
    rec = dict(id=r["id"], kind="screen", feasible=e.get("feasible"), first_fail=e.get("first_fail"),
               score=S.scalar_score(e, st_eval) if "cfm_free" in e else None,
               cfm_free=e.get("cfm_free"), cfm_load=e.get("cfm_load"), eff=e.get("efficiency"), tip_gap=e.get("tip_gap_mm"))
    if "c" in LAST: rec["curve"] = curve_d(LAST["c"])
    if bem_exploit_reason:
        try: rec["guard_fn"] = bem_exploit_reason(bp, 2000.0, e.get("tip_gap_mm"))
        except Exception as exc: rec["guard_fn"] = f"ERR {exc!r}"
    fh.write(json.dumps(rec, default=float) + "\n")
    if i % 1000 == 0: print(tag, i, f"{time.time()-t0:.0f}s", flush=True)
print(tag, "done", f"{time.time()-t0:.0f}s", flush=True)
