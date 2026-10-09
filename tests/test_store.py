"""Design-linked physical-measurement store (validation/store.py)."""

from __future__ import annotations

from validation.ingest import MeasuredPoint
from validation.store import (
    calibration_from_store,
    load_record,
    make_design_id,
    record_measurement,
    sim_vs_real,
)


def test_make_design_id():
    assert make_design_id("opt_extended2", 36) == "opt_extended2_t36"
    assert make_design_id("runs/opt_v2", 5) == "runs_opt_v2_t5"
    assert make_design_id("mydesign", None) == "mydesign"


def test_record_and_reload(tmp_path):
    rec = record_measurement(
        "opt_extended2_t36", MeasuredPoint(rpm=2000, cfm=55.0, noise_dba=25.0, source="anemometer"),
        run="opt_extended2", trial=36, material="PETG",
        sim={"cfm_free": 86.3, "cfm_load": 81.4, "efficiency": 40.7, "noise_dba": 50.0},
        instrument="cheap anemometer", store_dir=tmp_path)
    assert len(rec.measured) == 1
    back = load_record("opt_extended2_t36", tmp_path)
    assert back is not None
    assert back.trial == 36 and back.material == "PETG"
    assert back.sim["cfm_free"] == 86.3
    assert back.measured[0]["cfm"] == 55.0


def test_appending_points(tmp_path):
    record_measurement("d1", MeasuredPoint(rpm=1500, cfm=40.0), store_dir=tmp_path)
    rec = record_measurement("d1", MeasuredPoint(rpm=2000, cfm=52.0), store_dir=tmp_path)
    assert len(rec.measured) == 2
    assert {m["rpm"] for m in rec.measured} == {1500, 2000}


def test_sim_vs_real_deltas(tmp_path):
    rec = record_measurement(
        "d2", MeasuredPoint(rpm=2000, cfm=55.0, noise_dba=25.0),
        sim={"cfm_free": 86.0, "noise_dba": 50.0}, store_dir=tmp_path)
    rows = sim_vs_real(rec)
    assert len(rows) == 1
    cfm = rows[0]["cfm"]
    assert cfm["measured"] == 55.0 and cfm["sim"] == 86.0
    assert abs(cfm["ratio_real_over_sim"] - 55.0 / 86.0) < 1e-3   # store rounds to 4 dp
    # sim over-predicts flow -> positive pct_error ((sim-measured)/measured)
    assert cfm["pct_error"] > 0
    assert rows[0]["noise_dba"]["delta_db"] == -25.0   # measured 25 - sim 50


def test_calibration_from_store(tmp_path):
    record_measurement("a", MeasuredPoint(rpm=2000, cfm=55.0),
                       sim={"cfm_free": 86.0}, store_dir=tmp_path)
    record_measurement("b", MeasuredPoint(rpm=2000, cfm=60.0),
                       sim={"cfm_free": 90.0}, store_dir=tmp_path)
    cal = calibration_from_store(tmp_path)
    assert cal.n_points == 2
    # reality/sim ~ (55/86 + 60/90)/2 ≈ 0.653
    assert 0.6 < cal.cfm < 0.7


def test_empty_store(tmp_path):
    cal = calibration_from_store(tmp_path / "nope")
    assert cal.n_points == 0 and cal.cfm is None
    assert load_record("missing", tmp_path) is None
