"""Pilot-run timing: mesh_cells parsing, estimate_run/format_eta arithmetic, pilot.json writing.

See ``.superpowers/sdd/ring-duct-brief.md`` Part B.
"""

from __future__ import annotations

import json

import pytest

from fansim.cfd.timing import (
    SolveTiming,
    estimate_run,
    estimate_urans_wall_s,
    format_eta,
    mesh_cells,
    pilot_iters,
    write_pilot_json,
)


def test_mesh_cells_parses_real_format_excerpt(tmp_path):
    case = tmp_path / "case"
    (case / "logs").mkdir(parents=True)
    (case / "logs" / "checkMesh.log").write_text(
        "Create polyMesh for time = 0\n"
        "Mesh stats\n"
        "    points:           1543210\n"
        "    faces:            4531200\n"
        "    internal faces:   4321000\n"
        "    cells:            1234567\n"
        "    faces per cell:   5.9\n",
        encoding="utf-8",
    )
    assert mesh_cells(case) == 1234567


def test_mesh_cells_missing_log_returns_none(tmp_path):
    assert mesh_cells(tmp_path / "nope") is None


def test_mesh_cells_no_cells_line_returns_none(tmp_path):
    case = tmp_path / "case"
    (case / "logs").mkdir(parents=True)
    (case / "logs" / "checkMesh.log").write_text("garbage, no cells here\n", encoding="utf-8")
    assert mesh_cells(case) is None


def test_solve_timing_dataclass_fields():
    t = SolveTiming(cells=100000, iters=50, wall_s=120.0, sec_per_iter=2.4)
    assert t.cells == 100000
    assert t.iters == 50
    assert t.wall_s == pytest.approx(120.0)
    assert t.sec_per_iter == pytest.approx(2.4)


def test_pilot_iters_default_fraction():
    assert pilot_iters(1000) == 100
    assert pilot_iters(300) == 50  # floor: max(50, 300//10=30) -> 50
    assert pilot_iters(50) == 50


def test_estimate_run_arithmetic():
    # mesh 60s + 10 points * 100 iters * 0.5 s/iter = 60 + 500 = 560; *1.2 margin = 672
    got = estimate_run(mesh_s=60.0, sec_per_iter=0.5, iters=100, points=10, margin=1.2)
    assert got == pytest.approx(672.0)


def test_estimate_run_default_margin():
    got = estimate_run(mesh_s=0.0, sec_per_iter=1.0, iters=10, points=1)
    assert got == pytest.approx(12.0)  # (0 + 10) * 1.2


def test_estimate_urans_wall_s():
    # 5 revs at 2000 rpm -> 0.15 simulated seconds; at 0.01 sim-s per wall-s -> 15 wall s.
    sim_time_s = 5 * 60.0 / 2000.0
    assert sim_time_s == pytest.approx(0.15)
    got = estimate_urans_wall_s(sim_s_per_wall_s=0.01, revs=5, rpm=2000.0)
    assert got == pytest.approx(15.0)


def test_estimate_urans_wall_s_rejects_nonpositive_rate():
    with pytest.raises(ValueError):
        estimate_urans_wall_s(sim_s_per_wall_s=0.0, revs=5, rpm=2000.0)


@pytest.mark.parametrize("seconds,expected", [
    (5.2, "5 s"),
    (59.9, "60 s"),
    (60.0, "1 min"),
    (200 * 60.0, "3 h 20 min"),
    (90 * 60.0, "1 h 30 min"),
])
def test_format_eta(seconds, expected):
    assert format_eta(seconds) == expected


def test_write_pilot_json_writes_expected_payload(tmp_path):
    out = tmp_path / "pilot.json"
    payload = write_pilot_json(
        out, cells=500000, mesh_s=30.0, sec_per_iter=0.2, iters=1000, points=5, margin=1.2,
        extra={"note": "direction matrix: 2 meshes x 2 solves"},
    )
    assert out.exists()
    on_disk = json.loads(out.read_text(encoding="utf-8"))
    assert on_disk == payload
    assert payload["cells"] == 500000
    assert payload["mesh_s"] == pytest.approx(30.0)
    assert payload["sec_per_iter"] == pytest.approx(0.2)
    assert payload["iters"] == 1000
    assert payload["points"] == 5
    expected_s = estimate_run(30.0, 0.2, 1000, 5, margin=1.2)
    assert payload["estimated_full_run_s"] == pytest.approx(expected_s)
    assert payload["estimated_full_run_eta"] == format_eta(expected_s)
    assert payload["note"] == "direction matrix: 2 meshes x 2 solves"


def test_write_pilot_json_creates_parent_dirs(tmp_path):
    out = tmp_path / "nested" / "dir" / "pilot.json"
    write_pilot_json(out, cells=None, mesh_s=1.0, sec_per_iter=1.0, iters=10, points=1)
    assert out.exists()
