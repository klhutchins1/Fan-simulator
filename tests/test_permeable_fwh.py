"""Tests for permeable-surface FW-H (six CV faces). Synthetic only; no GPU."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from fansim.acoustics.farfield import blade_pass_frequency
from fansim.acoustics.fwh import (
    cv_box_from_dia_mm,
    face_panels_from_csv,
    noise_from_compact_force,
    noise_from_permeable_panels,
)


def _bpf_Fz(amp=0.01, n_blades=7, rpm=2000.0, t_end=0.4):
    bpf = blade_pass_frequency(n_blades, rpm)
    fs = 20000.0
    t = np.arange(0, t_end, 1.0 / fs)
    Fz = amp * np.sin(2.0 * np.pi * bpf * t)
    return t, Fz, 1.0 / fs, bpf


def _write_six_face_csv(path: Path, t, face_F):
    """face_F: list of 6 arrays shape (N, 3)."""
    header = "t_s," + ",".join(
        f"F{i}{c}" for i in range(6) for c in "xyz"
    )
    rows = [header]
    for k, tk in enumerate(t):
        cols = [f"{tk:.9g}"]
        for Fi in face_F:
            cols.extend(f"{Fi[k, j]:.9g}" for j in range(3))
        rows.append(",".join(cols))
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def test_cv_box_from_dia_mm_matches_setup_recipe():
    box = cv_box_from_dia_mm(110.5)
    assert box["cx_m"] == 0.0 and box["cy_m"] == 0.0 and box["cz_m"] == 0.0
    # R=55.25 cells, bh=min(67.25, 72)=67.25 → half_xy = 0.06725 m
    assert box["half_xy_m"] == pytest.approx(0.06725, abs=1e-6)
    assert box["half_z_m"] == pytest.approx(0.045, abs=1e-9)


def test_face_panels_from_csv_six_panels(tmp_path):
    t, Fz, _dt, _bpf = _bpf_Fz()
    zeros = np.zeros((len(t), 3))
    face_F = []
    for i in range(6):
        F = zeros.copy()
        F[:, 2] = Fz * (0.1 if i < 5 else 0.5)  # uneven so sum is unique
        face_F.append(F)
    csv = tmp_path / "perm.csv"
    _write_six_face_csv(csv, t, face_F)
    box = cv_box_from_dia_mm(110.5)
    panels = face_panels_from_csv(csv, box)
    assert len(panels) == 6
    assert panels[0]["n_hat"] == pytest.approx((1.0, 0.0, 0.0))
    assert panels[1]["n_hat"] == pytest.approx((-1.0, 0.0, 0.0))
    assert panels[4]["r0"][2] == pytest.approx(box["half_z_m"])
    m = noise_from_permeable_panels(t, panels)
    assert m["analogy"] == "fwh_permeable"
    assert math.isfinite(m["noise_dba_band"])


def test_sum_to_origin_matches_compact_within_half_db():
    t, Fz, dt, _bpf = _bpf_Fz(amp=0.02)
    F = np.column_stack([np.zeros_like(t), np.zeros_like(t), Fz])
    # Split equally across six faces; collapse by summing → one origin panel
    face_F = [F / 6.0 for _ in range(6)]
    panels = []
    for Fi in face_F:
        panels.append({
            "r0": (0.0, 0.0, 0.0),
            "n_hat": (0.0, 0.0, 1.0),
            "area": 1.0,
            "f": Fi,
        })
    Fsum = sum(face_F)
    m_c = noise_from_compact_force(t, Fsum)
    m_p = noise_from_permeable_panels(t, panels)
    assert abs(m_c["noise_dba_band"] - m_p["noise_dba_band"]) < 0.5


def test_opposite_faces_equal_fz_on_axis_finite():
    t, Fz, _dt, _bpf = _bpf_Fz()
    F = np.column_stack([np.zeros_like(t), np.zeros_like(t), Fz])
    box = cv_box_from_dia_mm(110.5)
    hz = box["half_z_m"]
    panels = [
        {"r0": (0.0, 0.0, hz), "n_hat": (0.0, 0.0, 1.0), "area": 1.0, "f": F},
        {"r0": (0.0, 0.0, -hz), "n_hat": (0.0, 0.0, -1.0), "area": 1.0, "f": F},
    ]
    m = noise_from_permeable_panels(t, panels)
    assert math.isfinite(m["noise_dba_band"])
    assert m["noise_dba_band"] != 0.0


def test_evaluate_noise_declares_permeable_and_rejects_combo():
    text = Path("scripts/evaluate_noise.py").read_text(encoding="utf-8")
    assert "--permeable" in text
    assert "★" not in text
    assert "cannot combine --fwh, --permeable, and --patches" in text
