"""PWM tables, field snapshots, FNO availability."""

from __future__ import annotations

from pathlib import Path

import pytest

from fansim.optimize.pwm_table import A12X25_PWM, get_pwm_table
from fansim.surrogate import fno
from fansim.surrogate.fields import ingest_case_fields, list_snapshots, snapshots_available


def test_a12x25_pwm_endpoints():
    tab = get_pwm_table("a12x25")
    assert tab.rpm_at_duty(0.0) == pytest.approx(450.0)
    assert tab.rpm_at_duty(100.0) == pytest.approx(2000.0)
    assert tab.duty_at_rpm(1225.0) == pytest.approx(50.0)
    assert tab.kv_approx == pytest.approx(2000.0 / 12.0)


def test_make_pwm_table_editor_bounds():
    from fansim.optimize.pwm_table import make_pwm_table, pwm_caption

    tab = make_pwm_table(400.0, 2200.0, name="edit")
    assert tab.rpm_at_duty(50.0) == pytest.approx(1300.0)
    assert "400" in pwm_caption(tab)


def test_field_snapshot_ingest(tmp_path):
    case = tmp_path / "case"
    t100 = case / "100"
    t100.mkdir(parents=True)
    (t100 / "U").write_text("Ufield\n", encoding="utf-8")
    (t100 / "p").write_text("pfield\n", encoding="utf-8")
    (case / "0").mkdir()
    dest = tmp_path / "snap"
    man = ingest_case_fields(case, dest, label="t")
    assert man["time"] == "100"
    assert (dest / "U").read_text(encoding="utf-8") == "Ufield\n"
    assert snapshots_available(tmp_path)
    assert list_snapshots(tmp_path)[0]["label"] == "t"


def test_fno_available_tracks_snapshots(tmp_path, monkeypatch):
    monkeypatch.setattr(fno, "DEFAULT_SNAPSHOT_ROOT", tmp_path)
    assert fno.available() is False
    case = tmp_path / "case"
    (case / "50").mkdir(parents=True)
    (case / "50" / "U").write_text("u\n", encoding="utf-8")
    (case / "50" / "p").write_text("p\n", encoding="utf-8")
    ingest_case_fields(case, tmp_path / "s1", label="s1")
    assert fno.available() is True
    with pytest.raises(NotImplementedError):
        fno.train_fno()
