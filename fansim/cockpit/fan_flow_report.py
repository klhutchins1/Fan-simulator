"""Fan binder: the "How the air moves" report card (roadmap §24)."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from fansim.cfd.flow_report import FLOW_REPORT_VERSION, FlowReportUnavailable
from fansim.cfd.flow_report_case import (
    first_mismatch,
    latest_time,
    load_or_compute_metrics,
    test_settings,
)
from fansim.cfd.flow_verdicts import ICONS, judge, overall_line
from fansim.cockpit.airflow_panel import png_data_uri
from fansim.cockpit.data import scored_case_dir
from fansim.cockpit.flow_reference import get_reference
from fansim.cockpit.stock_cache import STOCK_CACHE_DIR

_log = logging.getLogger(__name__)

MSG_NONE = "No flow simulation for this design yet. Run Assess to see how the air moves."
MSG_BUILDING = "Working out how the air moves…"
NUMBER_LABELS = {"backflow_frac": "backflow share", "swirl_frac": "swirl energy share",
                 "dead_frac": "dead-air share", "tip_band_uz_ratio": "tip / mean forward speed",
                 "noise_swl_db": "Proudman SWL (dB, relative; mesh-dependent, don't compare)", "mean_uz_exit": "mean exit Uz (m/s)",
                 "mean_dp0_pa": "mean push (Pa, area-weighted)"}


def card_message(d) -> str | None:
    if not getattr(d, "has_model", False) or not getattr(d, "stl_path", ""):
        return MSG_NONE
    extra = getattr(d, "extra", {}) or {}
    if extra.get("cfd_stale"):
        why = extra.get("stale_reason") or "older solver"
        return f"These results are out of date ({why}). Re-run Assess."
    case = scored_case_dir(d)  # the run behind the score (refreshed designs live elsewhere)
    if case is None or not case.is_dir():
        return MSG_NONE
    has_time = any(p.is_dir() and p.name[:1].isdigit() for p in case.iterdir())
    if not has_time and not (case / "processor0").is_dir():
        return MSG_NONE
    return None


def _pictures(case_dir, metrics, *, scales=None, stock_bands=None, out_dir=None):
    from fansim.cfd.cockpit_viz import load_case_mesh
    from fansim.cfd.flow_report_viz import render_report_pictures
    mesh = load_case_mesh(case_dir)
    if mesh is None:
        return {}
    return render_report_pictures(case_dir, mesh=mesh, scales=scales, out_dir=out_dir,
                                  stock_bands=stock_bands, metrics=metrics)


PICTURES_STAMP = "flow_pictures.json"


def _pictures_cached(case_dir, metrics, *, key: str, out_dir=None, **kw) -> dict:
    """Render once per (report version, CFD time, reference); reuse the PNGs after that (§24)."""
    out = Path(out_dir or case_dir)
    stamp = out / PICTURES_STAMP
    try:
        saved = json.loads(stamp.read_text(encoding="utf-8"))
        pics = {k: Path(v) for k, v in saved.get("pictures", {}).items()}
        if saved.get("key") == key and pics and all(p.is_file() for p in pics.values()):
            return pics
    except (OSError, ValueError, AttributeError):
        pass
    try:
        pics = _pictures(case_dir, metrics, out_dir=out_dir, **kw)
    except Exception as exc:  # noqa: BLE001 - verdicts still show without pictures
        _log.warning("flow pictures failed for %s: %s: %s", case_dir, type(exc).__name__, exc)
        return {}
    if not pics:
        return {}
    try:
        out.mkdir(parents=True, exist_ok=True)
        stamp.write_text(json.dumps({"key": key, "pictures": {k: str(v) for k, v in pics.items()},
                                     "scales": kw.get("scales")}), encoding="utf-8")
    except OSError:
        pass
    return pics


def _key(case_dir, ref_dir) -> str:
    return f"{FLOW_REPORT_VERSION}|{latest_time(case_dir)}|{ref_dir or 'none'}"


def _stock_pack(ref_dir):
    """Stock metrics, colour scales and pictures, made once per reference and reused."""
    m = load_or_compute_metrics(ref_dir)
    out_dir = STOCK_CACHE_DIR / "flow_report"
    key = _key(ref_dir, ref_dir)
    scales = None
    try:
        saved = json.loads((out_dir / PICTURES_STAMP).read_text(encoding="utf-8"))
        if saved.get("key") == key and saved.get("scales"):
            scales = {k: tuple(v) for k, v in saved["scales"].items()}
    except (OSError, ValueError, AttributeError):
        pass
    if scales is None:
        from fansim.cfd.cockpit_viz import load_case_mesh
        from fansim.cfd.flow_report_viz import picture_scales
        mesh = load_case_mesh(ref_dir)
        scales = picture_scales(ref_dir, mesh=mesh) if mesh is not None else None
    pics = _pictures_cached(ref_dir, m, key=key, out_dir=out_dir, scales=scales,
                            stock_bands=m.band_dp0_pa)
    return m, scales, pics


def build_report(case_dir, ref_dir) -> dict:
    case_dir = Path(case_dir)
    m = load_or_compute_metrics(case_dir)
    stock = scales = None
    stock_pics: dict = {}
    msg = ""
    if ref_dir is None:
        msg = "Stock hasn't been tested this way, so no comparison (no Stock reference set)."
    else:
        why = first_mismatch(test_settings(case_dir), test_settings(ref_dir))
        if why:
            msg = f"Stock hasn't been tested this way, so no comparison ({why})."
        else:
            try:
                stock, scales, stock_pics = _stock_pack(ref_dir)
            except FlowReportUnavailable:  # pruned reference: still judge this design on its own
                stock, scales, stock_pics = None, None, {}
                msg = "Stock's saved run has no flow data, so no comparison."
    pics = _pictures_cached(case_dir, m, key=_key(case_dir, ref_dir if stock else None),
                            scales=scales, stock_bands=stock.band_dp0_pa if stock else None)
    rows = judge(m, stock)
    pic_for = {"direction": "face", "push": "push", "spin": "spin", "dead": "face", "noise": "noise"}
    out_rows = []
    for r in rows:
        if r.key == "noise" and r.status == "na" and m.noise_swl_db is None:
            continue  # spec: hide the noise row when the run has no turbulence data
        name = pic_for[r.key]
        out_rows.append({
            "key": r.key, "title": r.title, "icon": ICONS[r.status], "status": r.status,
            "text": r.text, "expert_only": r.expert_only,
            "img": png_data_uri(pics[name]) if name in pics else "",
            "stock_img": png_data_uri(stock_pics[name]) if name in stock_pics else ""})
    numbers = [{"name": NUMBER_LABELS.get(k, k), "design": v,
                "stock": (stock.to_dict()[k] if stock else None)}
               for k, v in m.to_dict().items() if k in NUMBER_LABELS]
    if m.noise_swl_db is None:
        msg = (msg + " " if msg else "") + "No turbulence data in this run."
    return {"flow_rows": out_rows, "flow_overall": overall_line(rows, compared=stock is not None),
            "flow_msg": msg, "flow_numbers": numbers}


def _apply_if_current(state, *, token, payload: dict) -> bool:
    if getattr(state, "selected_trial", None) != token:
        return False
    for k, v in payload.items():
        setattr(state, k, v)
    return True


def _run_if_current(gen: list, my_gen: int, lock, fn):
    """One build at a time; a build superseded by a newer pick is skipped before it starts."""
    with lock:
        if gen[0] != my_gen:
            return None
        return fn()


def bind(session) -> None:
    state = session.state
    import threading

    from fansim.cockpit import fan_runtime

    gen = [0]                 # bumped on every pick (spec: airflow_gen-style generation)
    lock = threading.Lock()   # single-flight: each build loads a full mesh

    def _schedule_flow_report(d):
        gen[0] += 1
        my_gen = gen[0]
        msg = card_message(d)
        state.flow_rows, state.flow_overall, state.flow_numbers = [], "", []
        if msg is not None:
            state.flow_msg, state.flow_busy = msg, False
            return
        token = d.trial
        case = scored_case_dir(d)
        state.flow_msg, state.flow_busy = MSG_BUILDING, True

        async def task():
            try:
                loop = asyncio.get_running_loop()
                payload = await loop.run_in_executor(None, lambda: _run_if_current(
                    gen, my_gen, lock, lambda: build_report(case, get_reference())))
                if payload is None:  # superseded by a newer pick before it started
                    return
            except FlowReportUnavailable as exc:
                payload = {"flow_msg": f"Couldn't read this run's flow ({exc}). Re-run Assess."}
            except Exception as exc:  # noqa: BLE001
                _log.warning("flow report failed for %s: %s: %s", case, type(exc).__name__, exc)
                payload = {"flow_msg": "The flow report couldn't be built for this design."}
            payload["flow_busy"] = False
            if _apply_if_current(state, token=token, payload=payload):
                state.flush()

        fan_runtime.asynchronous.create_task(task())

    session._schedule_flow_report = _schedule_flow_report
