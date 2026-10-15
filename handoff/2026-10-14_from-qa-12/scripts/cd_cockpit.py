"""QA r12 Tasks C/D (PREREG_R12 42004b3): headless cockpit session (CockpitCtx + setup_fan_tab, as the r7 harness /
tests/test_fan_tab_setup_smoke.py), real asyncio loop + thread executor, REAL Preview/Export handlers and workers.
Only Assess's evaluate_candidate_isolated is faked (mode D, M3) so no CFD runs.
Usage: python cd_cockpit.py C|D <out.json>   (cwd anywhere; PYTHONPATH=/workspace/fansim/qa/run_r12)"""
import asyncio, json, sys, tempfile, time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
MODE, OUT = sys.argv[1], Path(sys.argv[2])
sys.modules.setdefault("pytest", SimpleNamespace())
import trame.app as trame
import fansim; assert fansim.__file__.startswith("/workspace/fansim/qa/run_r12"), fansim.__file__
import fansim.cockpit.fan_assess as fan_assess, fansim.cockpit.fan_runtime as fan_runtime, fansim.cockpit.fan_tab as fan_tab
from fansim.cockpit.context import CockpitCtx
SESS = []
_FS = fan_tab.FanSession
class CapSession(_FS):
    def __init__(self, *a, **k): super().__init__(*a, **k); SESS.append(self)
fan_tab.FanSession = CapSession
EVAL = []
def fake_eval(flat, features, workdir, **kw):
    EVAL.append({"material": kw.get("material"), "spec": getattr(kw.get("spec"), "name", None), "spec_material": getattr(kw.get("spec"), "material", None)})
    Path(workdir).mkdir(parents=True, exist_ok=True); (Path(workdir) / "impeller.stl").write_text("solid f\nendsolid f\n")
    return SimpleNamespace(feasible=True, reason="", over_spec=[], cfm_free=50.0, cfm_load=40.0, efficiency=30.0, actual_rpm=2000.0, raw={})
fan_assess.evaluate_candidate_isolated = fake_eval
class TDict(dict):
    def __bool__(self): return True
class TList(list):
    def __bool__(self): return True
R = {"mode": MODE, "events": []}
def ev(name, st, **kw):
    R["events"].append({"t": name, "mono": round(time.monotonic(), 1), "assess_material": st.assess_material,
                        "active_spec_material": SESS[0].active_spec().material, "selected": st.selected_trial, **kw})
async def wait(st, attr, limit=1200):
    t = time.monotonic(); await asyncio.sleep(0.5)
    while getattr(st, attr) and time.monotonic() - t < limit: await asyncio.sleep(1)
    return round(time.monotonic() - t, 1)
async def main():
    loop = asyncio.get_running_loop(); tmp = Path(tempfile.mkdtemp(prefix=f"qa12{MODE}_"))
    server = trame.get_server(f"qa12_{MODE}"); state, ctrl = server.state, server.controller
    ctrl.figure_update = lambda *a, **k: None; ctrl.view_update = lambda *a, **k: None
    fan_runtime.asynchronous = SimpleNamespace(create_task=loop.create_task)
    ctx = CockpitCtx(server=server, state=state, ctrl=ctrl, run_dir=tmp, runs_root=tmp.parent, plotter=MagicMock(),
                     busy_bar=lambda *a, **k: None, busy_expr=lambda *a, **k: "", spawn_busy_ticker=lambda **_: (MagicMock(), 0.0),
                     study_name=None, study_designs=[], user_designs=TList(), by_trial=TDict(), next_id=[9000], assess_dir=tmp / "cockpit_assess")
    fan_tab.setup_fan_tab(ctx); await asyncio.sleep(3.0); st = ctx.state
    R["busy_after_3s"] = {k: getattr(st, k) for k in ("preview_busy", "assess_busy", "export_busy")}
    t = time.monotonic()  # a user waits for the cold-open work to finish before pressing anything
    while (st.preview_busy or st.assess_busy or st.export_busy) and time.monotonic() - t < 600: await asyncio.sleep(1)
    R["cold_idle_wait_s"] = round(time.monotonic() - t, 1); R["preview_msg_cold"] = (st.preview_msg or "")[:600]
    R["cold"] = {"fan_model": st.fan_model, "selected": st.selected_trial, "assess_material": st.assess_material,
                 "items": list(st.assess_material_items or []), "cup_build_ok": st.cup_build_ok}
    ev("cold_open", st)
    if MODE == "D":
        st.assess_material = "PLA+"; ev("set_PLA+", st)
        ctx.fan_do_preview(); R["preview_wait_s"] = await wait(st, "preview_busy")
        ev("after_preview", st, preview_msg=(st.preview_msg or "")[:1500])
    idx = Path(fansim.__file__).resolve().parents[1] / "validation/prints/index.jsonl"
    n0 = len(idx.read_text().splitlines()) if idx.exists() else 0
    ctx.fan_export_stl_current(); await asyncio.sleep(0.5); R["export_started"] = bool(st.export_busy)
    R["export_wait_s"] = await wait(st, "export_busy")
    R["export_msg"] = (st.export_msg or "")[:2000]; R["export_download"] = st.export_download
    lines = idx.read_text().splitlines() if idx.exists() else []
    R["index_n0"], R["index_n1"], R["index_new"] = n0, len(lines), [json.loads(l) for l in lines[n0:]]
    ev("after_export", st)
    if MODE == "D":
        ctx.fan_on_assess(); await wait(st, "assess_busy", 120)
        R["assess_eval_calls"] = EVAL; R["assess_msg"] = (st.assess_msg or "")[:400]
        R["assess_saved"] = [{"trial": d.trial, "material": d.extra.get("material"), "fan_model": d.extra.get("fan_model")} for d in ctx.user_designs]
        ev("after_assess", st)
    OUT.write_text(json.dumps(R, indent=1, default=str))
asyncio.run(main())
print("DONE", flush=True)
