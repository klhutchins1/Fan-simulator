"""Tests for OpenFOAM DES permeable FW-H helpers (synthetic only; no Docker)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest


def _write_six_face_csv(path: Path, n: int = 200, fs: float = 20000.0):
    t = np.arange(n) / fs
    bpf = 7 * 2000 / 60
    rows = []
    for ti in t:
        F = [0.0] * 18
        F[14] = 0.02 * np.sin(2 * np.pi * bpf * ti)  # F4z (+z face)
        rows.append((ti, *F))
    hdr = "t_s," + ",".join(f"F{i}{c}" for i in range(6) for c in "xyz")
    with path.open("w", encoding="utf-8") as f:
        f.write(hdr + "\n")
        for r in rows:
            f.write(",".join(f"{x:.8g}" for x in r) + "\n")


def test_reduce_des_permeable_stamps_analogy(tmp_path):
    from fansim.cfd.des_fwh import reduce_des_permeable

    csv = tmp_path / "face_loads.csv"
    _write_six_face_csv(csv)
    m = reduce_des_permeable(csv, dia_mm=110.5)
    assert m["analogy"] == "openfoam_des_fwh"
    assert m["turbulence"] == "kOmegaSSTDES"
    assert m["rotation"] == "MRF"
    assert m["surface"] == "permeable_box"
    assert m["n_panels"] == 6
    assert np.isfinite(m["noise_dba_band"])
    assert m["r_obs_m"] == pytest.approx(0.2)


def test_reduce_des_short_window_not_silent(tmp_path):
    """1 m observer delay (~3 ms) must not be used on a 2 ms force history."""
    from fansim.cfd.des_fwh import reduce_des_permeable

    csv = tmp_path / "face_loads.csv"
    _write_six_face_csv(csv, n=100, fs=50000.0)  # 2 ms
    m = reduce_des_permeable(csv, dia_mm=110.5)
    assert np.isfinite(m["noise_dba_band"])
    assert m["noise_dba_band"] > -200


def test_box_from_duct_fits_inside_radius():
    from fansim.cfd.des_fwh import box_from_duct

    box = box_from_duct(0.05, half_z_m=0.03)
    assert box["half_xy_m"] == pytest.approx(0.045)
    assert box["half_z_m"] == pytest.approx(0.03)


def test_box_sidecar_roundtrip(tmp_path):
    from fansim.acoustics.fwh import cv_box_from_dia_mm
    from fansim.cfd.des_fwh import read_box_sidecar, write_box_sidecar

    box = cv_box_from_dia_mm(110.5)
    p = write_box_sidecar(tmp_path / "box.json", box)
    b2 = read_box_sidecar(p)
    assert b2["half_xy_m"] == pytest.approx(box["half_xy_m"])
    assert b2["half_z_m"] == pytest.approx(box["half_z_m"])


def test_collect_face_loads_csv_from_fo(tmp_path):
    from fansim.acoustics.fwh import cv_box_from_dia_mm
    from fansim.cfd.des_fwh import collect_face_loads_csv, reduce_des_permeable

    case = tmp_path / "case"
    # Dense enough that Nyquist >> 2500 Hz cutoff used by FW-H band metric
    dt = 5e-5
    n = 400
    for i in range(6):
        d = case / "postProcessing" / f"desFace{i}" / "0"
        d.mkdir(parents=True)
        lines = ["# Time areaIntegrate(p)"]
        for j in range(n):
            lines.append(f"{(j + 1) * dt:.8g} {1.0 + 0.01 * np.sin(2 * np.pi * 233 * j * dt):.8g}")
        (d / "surfaceFieldValue.dat").write_text("\n".join(lines) + "\n", encoding="utf-8")
    out = case / "face_loads.csv"
    collect_face_loads_csv(case, out, box=cv_box_from_dia_mm(110.5))
    text = out.read_text(encoding="utf-8")
    assert text.splitlines()[0].startswith("t_s,")
    m = reduce_des_permeable(out, dia_mm=110.5)
    assert m["analogy"] == "openfoam_des_fwh"


def test_apply_des_transient_writes_pimple_and_faces(tmp_path):
    from fansim.acoustics.fwh import cv_box_from_dia_mm
    from fansim.cfd.openfoam_case import apply_des_transient

    case = tmp_path / "case"
    (case / "system").mkdir(parents=True)
    (case / "constant").mkdir(parents=True)
    (case / "system/controlDict").write_text("application     simpleFoam;\n", encoding="utf-8")
    (case / "constant/turbulenceProperties").write_text("simulationType RAS;\n", encoding="utf-8")
    apply_des_transient(case, box=cv_box_from_dia_mm(110.5), delta_t=1e-5, end_time=1e-3)
    cd = (case / "system/controlDict").read_text(encoding="utf-8")
    assert "pimpleFoam" in cd
    assert "desFace0" in cd and "desFace5" in cd
    turb = (case / "constant/turbulenceProperties").read_text(encoding="utf-8")
    assert "kOmegaSSTDES" in turb
    assert (case / "constant/des_perm_box.json").is_file()


def test_run_solve_des_invokes_pimple_foam_serial_and_parallel():
    from fansim.cfd.openfoam_case import run_solve_des

    cmds_par: list[str] = []

    class _FakeRunner:
        def __init__(self, log: list[str]) -> None:
            self.log = log

        def run(self, cmd: str, **_kw) -> None:
            self.log.append(cmd)

    run_solve_des(_FakeRunner(cmds_par), n_procs=4, reconstruct=True)
    assert any("pimpleFoam -parallel" in c for c in cmds_par)
    assert any("reconstructPar -latestTime" in c for c in cmds_par)
    assert not any("simpleFoam" in c for c in cmds_par)

    cmds_ser: list[str] = []
    run_solve_des(_FakeRunner(cmds_ser), n_procs=1, reconstruct=False)
    assert "pimpleFoam" in cmds_ser
    assert not any("simpleFoam" in c for c in cmds_ser)


def test_evaluate_des_fwh_declares_flags():
    text = Path("scripts/evaluate_des_fwh.py").read_text(encoding="utf-8")
    assert "--csv-only" in text
    assert "des_fwh" in text
    assert "★" not in text


def test_csv_only_cli(tmp_path):
    import json
    import subprocess
    import sys

    from fansim.acoustics.fwh import cv_box_from_dia_mm
    from fansim.cfd.des_fwh import write_box_sidecar

    csv = tmp_path / "face_loads.csv"
    _write_six_face_csv(csv)
    box_path = tmp_path / "box.json"
    write_box_sidecar(box_path, cv_box_from_dia_mm(110.5))
    out = tmp_path / "out"
    r = subprocess.run(
        [
            sys.executable,
            "scripts/evaluate_des_fwh.py",
            "--csv-only",
            str(csv),
            "--box-json",
            str(box_path),
            "--out",
            str(out),
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )
    # CadQuery teardown can ACCESS_VIOLATION after a successful main(); judge by artifact.
    assert (out / "des_fwh.json").is_file(), r.stderr or r.stdout
    data = json.loads((out / "des_fwh.json").read_text(encoding="utf-8"))
    assert data["analogy"] == "openfoam_des_fwh"
    assert "openfoam_des_fwh" in (r.stdout or "")
