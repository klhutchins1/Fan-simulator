"""Rung B runner pieces that need no CFD: UIUC interpolation, freestream speed, verdict rules."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "prop_cfd_jsweep", Path(__file__).resolve().parents[1] / "scripts" / "prop_cfd_jsweep.py")
js = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(js)


def test_uiuc_interpolation_hits_table_rows():
    assert js.uiuc_at(0.295)["ct"] == pytest.approx(0.0771)
    mid = js.uiuc_at(0.3)
    assert 0.0726 < mid["ct"] < 0.0771
    with pytest.raises(ValueError):
        js.uiuc_at(0.7)                      # outside the 6029 rpm table: CT ~ 0 there anyway


def test_freestream_is_j_n_d():
    assert js.freestream_ms(0.3, 6000.0, 9.0) == pytest.approx(0.3 * 100.0 * 0.2286)


def _p(e, conv=True):
    return {"e_ct": e, "converged": conv}


def test_verdict_rules():
    assert js.verdict({"0.20": _p(-0.40), "0.30": _p(-0.05), "0.43": _p(0.10)})["verdict"] == "B1 static-specific"
    assert js.verdict({"0.20": _p(-0.40), "0.30": _p(-0.38), "0.43": _p(-0.45)})["verdict"] == "B2 sectional"
    assert js.verdict({"0.20": _p(-0.40), "0.30": _p(-0.20), "0.43": _p(-0.10)})["verdict"].startswith("neither")
    assert js.verdict({"0.20": _p(-0.40), "0.30": _p(-0.05, conv=False), "0.43": _p(0.1)})["verdict"] == "INCONCLUSIVE"
