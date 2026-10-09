"""Prop BEMT vs one measured prop: UIUC Propeller Database, GWS Direct-Drive 5x4.3 (2 blades).

Source files (unmodified, CRLF, sha256 in ``data/uiuc_gws_5x4.3/SOURCES.md``) were supplied by the QA
bot from the UIUC archive; the geometry is read from them here, not transcribed. Tolerances were
proposed before this geometry was run (QA, ``docs/qa/notes/prop-solver-validation.md``):
forward-flight eta within +-0.10 absolute at the measured peak, static CT0 within +-15 %.
Camber (4 %) and thickness (8 %) are assumed: UIUC gives chord and twist only.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from fansim.geometry.blade import BladeParams, RadialStation
from fansim.propeller.bemt import analyze
from fansim.propeller.polar import nondim, run_bemt_polar, v_inf_from_j

DATA = Path(__file__).parent / "data" / "uiuc_gws_5x4.3"
D_M = 5.0 * 0.0254
R_MM = 0.5 * D_M * 1000.0


def _table(name: str) -> list[list[float]]:
    rows = []
    for line in (DATA / name).read_text(encoding="utf-8").splitlines()[1:]:
        if line.split():
            rows.append([float(x) for x in line.split()])
    return rows


def _gws_blade() -> BladeParams:
    geom = _table("gwsdd_5x4.3_geom.txt")              # r/R, c/R, beta (deg)
    hub = geom[0][0] * R_MM
    stations = [RadialStation((rr * R_MM - hub) / (R_MM - hub), cr * R_MM, beta, 0.08, 0.04, 0.4)
                for rr, cr, beta in geom]
    return BladeParams(n_blades=2, hub_radius=hub, tip_radius=R_MM, stations=stations)


def test_source_tables_parse():
    geom = _table("gwsdd_5x4.3_geom.txt")
    assert geom[0][0] == 0.15 and geom[-1][0] == 1.0 and len(geom) == 18
    assert len(_table("gwsdd_5x4.3_0512rd_6047.txt")[0]) == 4
    assert len(_table("gwsdd_5x4.3_static_0493rd.txt")[0]) == 3


def test_forward_flight_eta_at_the_measured_peak():
    rpm = 6047.0
    j, _ct, _cp, eta_meas = max(_table("gwsdd_5x4.3_0512rd_6047.txt"), key=lambda r: r[3])
    v = v_inf_from_j(j, rpm, D_M)
    (pt,) = run_bemt_polar(_gws_blade(), rpm, [v], diameter_m=D_M)
    assert pt.eta == pytest.approx(pt.thrust_n * v / pt.power_w, rel=1e-3)   # eta is T*V/P
    assert pt.eta == pytest.approx(eta_meas, abs=0.10)


def test_static_ct0():
    rpm, ct_meas, _cp = min(_table("gwsdd_5x4.3_static_0493rd.txt"), key=lambda r: abs(r[0] - 7406.667))
    perf = analyze(_gws_blade(), rpm)
    nd = nondim(perf.thrust_n, perf.power_w, rpm=rpm, diameter_m=D_M, v_inf=0.0)
    assert nd["CT"] == pytest.approx(ct_meas, rel=0.15)
    assert nd["eta"] is None
