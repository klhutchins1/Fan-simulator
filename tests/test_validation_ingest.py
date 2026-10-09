"""Tests for the physical-validation ingest hooks (validation.ingest). Pure logic, no hardware."""

from validation.ingest import MeasuredPoint, calibrate, load_measurements


def test_load_measurements(tmp_path):
    csv = tmp_path / "m.csv"
    csv.write_text("rpm,cfm,static_pressure_pa,noise_dba,source,notes\n"
                   "2000,54.0,20.0,25.0,anemometer,run1\n"
                   "2000,,,26.5,phone_mic,run2\n")
    pts = load_measurements(csv)
    assert len(pts) == 2
    assert pts[0].cfm == 54.0 and pts[0].source == "anemometer"
    assert pts[1].cfm is None and pts[1].noise_dba == 26.5   # blanks -> None
    # Older CSVs omit rig extras — defaults stay empty / None
    assert pts[0].restriction_id == "" and pts[0].dp_pa is None
    assert pts[0].tach_rpm is None and pts[0].ambient_c is None


def test_load_measurements_rig_extras(tmp_path):
    csv = tmp_path / "rig.csv"
    csv.write_text(
        "rpm,cfm,static_pressure_pa,noise_dba,source,notes,"
        "restriction_id,dp_pa,tach_rpm,ambient_c,humidity_pct\n"
        "2000,45.0,12.0,38.0,sdp810,,plate3,12.3,1998,22.5,40\n"
    )
    pts = load_measurements(csv)
    assert len(pts) == 1
    p = pts[0]
    assert p.restriction_id == "plate3" and p.dp_pa == 12.3
    assert p.tach_rpm == 1998.0 and p.ambient_c == 22.5 and p.humidity_pct == 40.0


def test_calibrate_factors():
    measured = [MeasuredPoint(rpm=2000, cfm=54.0, static_pressure_pa=20.0, noise_dba=25.0)]
    simulated = [{"cfm": 60.0, "static_pressure_pa": 22.9, "noise_dba": 47.0}]
    cal = calibrate(measured, simulated)
    assert cal.n_points == 1
    assert cal.cfm == 54.0 / 60.0                     # reality = 0.9 * sim
    assert cal.static_pressure == 20.0 / 22.9
    assert cal.noise_dba_offset == 25.0 - 47.0        # dB is additive


def test_calibrate_skips_missing():
    measured = [MeasuredPoint(rpm=2000, noise_dba=25.0)]  # no cfm/pressure
    cal = calibrate(measured, [{"noise_dba": 47.0}])
    assert cal.cfm is None and cal.static_pressure is None
    assert cal.noise_dba_offset == -22.0
