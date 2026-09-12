# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
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
