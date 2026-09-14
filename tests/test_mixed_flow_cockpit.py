"""Mixed-flow cockpit helpers + isolated job wiring. No Docker / no UI server."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from fansim.centrifugal.geometry import MixedFlowParams
from fansim.centrifugal.params_io import mixed_params_from_flat


def test_mixed_params_from_flat_defaults_and_overrides():
    p = mixed_params_from_flat({"n_blades": 8, "stagger_deg": 40.0})
    assert p.n_blades == 8
    assert p.stagger_deg == pytest.approx(40.0)
    assert p.r_tip_mm == MixedFlowParams().r_tip_mm
    assert p.thickness == MixedFlowParams().thickness


def test_mixed_params_from_flat_rejects_eye_ge_back():
    with pytest.raises(ValueError, match="eye"):
        mixed_params_from_flat({"r_eye_mm": 30.0, "r_back_mm": 28.0})


def test_mixed_eval_job_dict_round_trips_core_fields():
    from fansim.centrifugal.isolated import mixed_eval_job_dict
    from fansim.fan_spec import A12X25

    flat = {
        "n_blades": 9, "r_eye_mm": 16.0, "r_back_mm": 28.0, "r_tip_mm": 54.5,
        "z_span_mm": 18.0, "chord_mm": 22.0, "stagger_deg": 35.0,
    }
    job = mixed_eval_job_dict(
        flat, "runs/x", A12X25, procs=4, base_cell=0.006, iters=100,
        out="runs/x/out.json", load_pa=8.0, refine_op=True,
    )
    assert job["kind"] == "mixed_flow"
    assert job["flat"]["n_blades"] == 9
    assert job["load_pa"] == pytest.approx(8.0)
    assert job["refine_op"] is True
    assert "spec" in job


def test_mixed_eval_worker_module_imports_evaluate():
    text = Path("fansim/centrifugal/_eval_worker.py").read_text(encoding="utf-8")
    assert "evaluate_mixed_flow" in text
    assert "★" not in text


def _cockpit_src() -> str:
    # 09-11 tab split: Mixed-flow UI lives in mixed_tab.py (app.py only mounts tabs).
    app = Path("fansim/cockpit/app.py").read_text(encoding="utf-8")
    tab = Path("fansim/cockpit/mixed_tab.py").read_text(encoding="utf-8")
    return app + "\n" + tab


def test_mixed_flow_tab_in_cockpit():
    src = _cockpit_src()
    assert 'value="mixed"' in src
    assert "Mixed-flow" in src
    assert 'state.mf_assess_preset = "case"' in src
    for key in (
        "mf_n_blades", "mf_r_eye", "mf_r_back", "mf_r_tip",
        "mf_z_span", "mf_chord", "mf_stagger",
    ):
        assert key in src
    assert "evaluate_mixed_flow_isolated" in src or "mixed_eval" in src
    assert "export_mixed_flow_stl" in src
    m = re.search(r"def mf_assess\b|def assess_mixed|async def mf_assess", src)
    assert m is not None or "mf_assess" in src
