"""QA r7 Task A harness: change settings while a (fake) job runs, inspect what is saved.

Test harness only, not a patch. It runs a headless cockpit (the same CockpitCtx construction as
tests/test_fan_tab_setup_smoke.py) on a REAL asyncio loop with a REAL thread executor, and
monkeypatches fan_assess.evaluate_candidate_isolated (the runner _blocking_eval calls) to record
the kwargs it was given, sleep JOB_S seconds, and return a canned result built from `flat`.
Preview's build_stl_isolated and Export's _export_isolated are patched the same way.
During the sleep the harness changes settings exactly as the UI handlers would, then prints
what was saved. Usage: python harness.py [JOB_S]   (brief says 60 s; 4 s gives the same result,
because only ordering matters.)
"""
from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

JOB_S = float(sys.argv[1]) if len(sys.argv) > 1 else 4.0
sys.modules.setdefault("pytest", SimpleNamespace())  # fan_tab stubs heavy UI bits under pytest

import trame.app as trame  # noqa: E402

import fansim.cockpit.fan_assess as fan_assess  # noqa: E402
import fansim.cockpit.fan_runtime as fan_runtime  # noqa: E402
import fansim.cockpit.fan_tab as fan_tab  # noqa: E402
from fansim.cockpit.context import CockpitCtx  # noqa: E402
from fansim.cockpit.data import Design  # noqa: E402
from fansim.fan_spec import _REGISTRY  # noqa: E402

CALLS: list[dict] = []


class TDict(dict):  # FanSession does `ctx.by_trial or {}`; an empty dict would be replaced
    def __bool__(self):
        return True


class TList(list):
    def __bool__(self):
        return True


def fake_eval(flat, features, workdir, **kw):
    rec = {"t": time.monotonic(), "flat_camber_mid": flat.get("camber_mid"),
           "spec": kw["spec"].name, "material": kw["material"], "load_pa": kw["load_pa"],
           "refine_op": kw["refine_op"], "wall_ks_mm": kw["wall_ks_mm"]}
    CALLS.append(rec)
    time.sleep(JOB_S)
    Path(workdir).mkdir(parents=True, exist_ok=True)
    (Path(workdir) / "impeller.stl").write_text("solid fake\nendsolid fake\n")
    raw = {"used": rec}  # what the run really used, for comparison
    return SimpleNamespace(feasible=True, reason="", over_spec=[], cfm_free=50.0,
                           cfm_load=40.0, efficiency=30.0, actual_rpm=2000.0, raw=raw)


fan_assess.evaluate_candidate_isolated = fake_eval
LAST_FLAT: dict = {}
_orig_eval = fake_eval


def fake_eval2(flat, features, workdir, **kw):
    LAST_FLAT.clear(); LAST_FLAT.update(flat)
    return _orig_eval(flat, features, workdir, **kw)


fan_assess.evaluate_candidate_isolated = fake_eval2

import fansim.geometry.isolated as _iso  # noqa: E402
import fansim.isolated_job as _ij  # noqa: E402


def fake_build_stl_isolated(flat, feat, out, **kw):
    CALLS.append({"job": "preview", "camber_mid": flat.get("camber_mid"),
                  "motor_mount": bool(kw.get("motor_mount")), "preview": kw.get("preview")})
    time.sleep(JOB_S)
    import trimesh
    trimesh.creation.cylinder(radius=50, height=20).export(str(out))


def fake_run_worker_module(mod, payload, **kw):
    CALLS.append({"job": "export", "spec": payload["spec"].get("name"),
                  "hub_radius": payload["flat"].get("hub_radius"),
                  "camber_mid": payload["flat"].get("camber_mid"),
                  "also_mirror": payload["also_mirror"], "out": Path(payload["out"]).name})
    time.sleep(JOB_S)
    Path(payload["result"]).write_text(json.dumps({"ok": True, "mount_fits": None,
                                       "mount_msg": "", "mirror_note": "", "gauge": None}))


_iso.build_stl_isolated = fake_build_stl_isolated
_ij.run_worker_module = fake_run_worker_module


def make_ctx(tmp: Path, loop):
    server = trame.get_server(f"qa7_{tmp.name}")
    state, ctrl = server.state, server.controller
    ctrl.figure_update = lambda *a, **k: None
    ctrl.view_update = lambda *a, **k: None
    fan_runtime.asynchronous = SimpleNamespace(create_task=loop.create_task)
    ctx = CockpitCtx(
        server=server, state=state, ctrl=ctrl, run_dir=tmp, runs_root=tmp.parent,
        plotter=MagicMock(), busy_bar=lambda *a, **k: None, busy_expr=lambda *a, **k: "",
        spawn_busy_ticker=lambda **_: (MagicMock(), 0.0), study_name=None, study_designs=[],
        user_designs=TList(), by_trial=TDict(), next_id=[9000], assess_dir=tmp / "cockpit_assess",
    )
    fan_tab.setup_fan_tab(ctx)
    return ctx


async def wait_idle(state, key="assess_busy"):
    await asyncio.sleep(0.2)
    while state.assess_busy or state.preview_busy or state.export_busy:
        await asyncio.sleep(0.1)


def saved(ctx, trial):
    d = ctx.by_trial[trial]
    keys = ("fan_model", "material", "preset", "load_pa", "refine_op", "parent_id", "placed_on",
            "cfd_stale")
    return {"trial": d.trial, "params.camber_mid": d.params.get("camber_mid"),
            **{k: d.extra.get(k) for k in keys}, "run_used": d.extra.get("used") or None}


def seed_design(ctx, trial, flat, extra, tmp):
    stl = tmp / f"seed_{trial}.stl"
    stl.write_text("solid s\nendsolid s\n")
    d = Design(trial=trial, params=dict(flat), objectives={"cfm_free": 1, "cfm_load": 1,
               "efficiency": 1}, feasible=True, is_pareto=False, stl_path=stl, extra=dict(extra))
    ctx.user_designs.append(d)
    ctx.by_trial[trial] = d
    return d


async def scenario(name, mutate, setup=None, handler="fan_on_assess"):
    tmp = Path(tempfile.mkdtemp(prefix=f"qa7_{name}_"))
    loop = asyncio.get_running_loop()
    ctx = make_ctx(tmp, loop)
    st = ctx.state
    st.assess_preset, st.assess_material, st.assess_refine_op, st.assess_wall_ks = (
        "case", "PETG", False, False)
    await asyncio.sleep(2.0)  # let setup's own scheduled tasks (stock reference load) finish
    if setup:
        setup(ctx, tmp)
    before = set(ctx.by_trial)
    start = {"fan_model": st.fan_model, "material": st.assess_material,
             "preset": st.assess_preset, "refine_op": st.assess_refine_op,
             "camber_mid": st.e_camber_mid, "parent": st.library_parent_id,
             "selected": st.selected_trial}
    n0 = len(CALLS)
    getattr(ctx, handler)()
    await asyncio.sleep(JOB_S / 3)
    mutate(ctx)
    await wait_idle(st)
    new = sorted(set(ctx.by_trial) - before)
    out = {"scenario": name, "start": start,
           "used_by_run": CALLS[n0:],
           "saved_new": [saved(ctx, t) for t in new],
           "after": {"selected": st.selected_trial, "camber_mid_editor": st.e_camber_mid,
                     "msg": (st.assess_msg or "").splitlines()[:1],
                     "preview_msg": (st.preview_msg or "").splitlines()[:2],
                     "export_msg": (st.export_msg or "").splitlines()[:3]}}
    if setup and getattr(ctx, "_watch", None):
        out["saved_watch"] = [saved(ctx, t) for t in ctx._watch]
    return out


def other_model(cur):
    return next(k for k in _REGISTRY if k != cur)


async def main():
    res = []
    res.append(await scenario("A0_no_change", lambda c: None))
    res.append(await scenario("A1_slider", lambda c: setattr(c.state, "e_camber_mid",
                                                            float(c.state.e_camber_mid) + 0.03)))

    def m_settings(c):
        s = c.state
        s.assess_material = "PLA" if s.assess_material != "PLA" else "PETG"
        s.assess_preset = "legacy"
        s.assess_refine_op = True
    res.append(await scenario("A2_material_hose_refine", m_settings))
    res.append(await scenario("A3_fan_model", lambda c: setattr(c.state, "fan_model",
                                                               other_model(c.state.fan_model))))

    def setup_other(ctx, tmp):
        flat = dict(ctx.fan_active_spec and {}) or {}
        from fansim.cockpit import fan_tab as _ft  # noqa: F401
        base = {k: v for k, v in ctx.state.to_dict().items()} if False else {}
        d = seed_design(ctx, 4242, {**LAST_FLAT, "camber_mid": 0.07}, {"preset": "legacy", "refine_op": True,
                        "fan_model": ctx.state.fan_model, "material": "PETG"}, tmp)
        ctx.state.assess_preset = "case"

    res.append(await scenario("A4_select_other_design",
                              lambda c: c.fan_select(4242), setup=setup_other))

    def setup_lib(ctx, tmp):
        ctx.state.library_parent_id, ctx.state.library_place_op = "LIB_X", "fit_envelope"

    def m_lib(c):  # what _apply_library_to_editor does (fan_library.py:83-84) for recipe Y
        c.state.library_parent_id, c.state.library_place_op = "LIB_Y", "scale_to_hub"
    res.append(await scenario("A5_library_switch", m_lib, setup=setup_lib))

    def setup_stale(ctx, tmp):
        ctx._watch = [4300, 4301]
        a = seed_design(ctx, 4300, {**LAST_FLAT, "camber_mid": 0.05}, {"cfd_stale": True, "preset": "case",
                        "fan_model": ctx.state.fan_model}, tmp)
        seed_design(ctx, 4301, {**LAST_FLAT, "camber_mid": 0.06}, {"cfd_stale": True, "preset": "case",
                    "fan_model": ctx.state.fan_model}, tmp)
        ctx.fan_select(4300)
        _ = a
    res.append(await scenario("A6_existing_switch", lambda c: c.fan_select(4301),
                              setup=setup_stale))

    def m_sweep(c):
        c.state.assess_material = "PLA"
    def setup_sweep(ctx, tmp):
        ctx.state.sweep_steps = 3
    res.append(await scenario("A7_sweep_material", m_sweep, setup=setup_sweep,
                              handler="fan_on_sweep"))
    def m_prev(c):
        s = c.state
        s.e_camber_mid = float(s.e_camber_mid) + 0.03
        s.preview_motor_cup = not bool(s.preview_motor_cup)
    res.append(await scenario("P1_preview_camber_cup", m_prev, handler="fan_do_preview"))

    def setup_exp(ctx, tmp):
        ctx.state.cup_build_ok = True
        ctx.state.export_also_mirror = False
        ctx.state.export_fit_hub = False
        ctx.state.export_fit_frame = False
        seed_design(ctx, 4400, {**LAST_FLAT, "camber_mid": 0.04}, {"fan_model": ctx.state.fan_model}, tmp)

    def m_exp(c):
        s = c.state
        s.e_hub_radius = float(s.e_hub_radius) + 3.0
        s.export_also_mirror = True
        c.fan_select(4400)
    res.append(await scenario("E1_export_hub_mirror_select", m_exp, setup=setup_exp,
                              handler="fan_export_stl_current"))
    print(json.dumps(res, indent=1, default=str))


asyncio.run(main())
