"""Tests for permeable 2x2 face-patch FW-H (24 panels). Synthetic only; no GPU."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from fansim.acoustics.farfield import blade_pass_frequency
from fansim.acoustics.fwh import (
    PATCH_N,
    analyze_patches_csv,
    cv_box_from_dia_mm,
    patch_panels_from_csv,
)


def _bpf_Fz(amp=0.01, n_blades=7, rpm=2000.0, t_end=0.4):
    bpf = blade_pass_frequency(n_blades, rpm)
    fs = 20000.0
    t = np.arange(0, t_end, 1.0 / fs)
    Fz = amp * np.sin(2.0 * np.pi * bpf * t)
    return t, Fz


def _write_patch_csv(path: Path, t, patch_F):
    n = PATCH_N * PATCH_N * 6
    assert len(patch_F) == n
    header = "t_s," + ",".join(f"P{i}{c}" for i in range(n) for c in "xyz")
    rows = [header]
    for k, tk in enumerate(t):
        cols = [f"{tk:.9g}"]
        for Fi in patch_F:
            cols.extend(f"{Fi[k, j]:.9g}" for j in range(3))
        rows.append(",".join(cols))
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def test_patch_n_is_two():
    assert PATCH_N == 2


def test_patch_panels_from_csv_twenty_four(tmp_path):
    t, Fz = _bpf_Fz()
    zeros = np.zeros((len(t), 3))
    patch_F = []
    for i in range(24):
        F = zeros.copy()
        F[:, 2] = Fz * (0.05 + 0.01 * (i % 5))
        patch_F.append(F)
    csv = tmp_path / "patches.csv"
    _write_patch_csv(csv, t, patch_F)
    box = cv_box_from_dia_mm(110.5)
    panels = patch_panels_from_csv(csv, box)
    assert len(panels) == 24
    assert panels[0]["n_hat"] == pytest.approx((1.0, 0.0, 0.0))
    assert panels[0]["r0"][0] == pytest.approx(box["half_xy_m"])
    assert panels[0]["r0"][1] == pytest.approx(-0.5 * box["half_xy_m"])
    assert panels[0]["r0"][2] == pytest.approx(-0.5 * box["half_z_m"])
    m = analyze_patches_csv(csv, dia_mm=110.5)
    assert m["analogy"] == "fwh_patches"
    assert m["n_panels"] == 24
    assert math.isfinite(m["noise_dba_band"])


def test_four_patches_sum_to_face_force(tmp_path):
    t, Fz = _bpf_Fz(amp=0.02)
    face = np.column_stack([np.zeros_like(t), np.zeros_like(t), Fz])
    parts = [face * w for w in (0.1, 0.2, 0.3, 0.4)]
    zeros = np.zeros((len(t), 3))
    patch_F = [zeros.copy() for _ in range(24)]
    for k, p in enumerate(parts):
        patch_F[16 + k] = p  # face 4 = +z
    path = tmp_path / "p.csv"
    _write_patch_csv(path, t, patch_F)
    panels = patch_panels_from_csv(path, cv_box_from_dia_mm(110.5))
    face_sum = sum(panels[16 + k]["f"] for k in range(4))
    err = float(np.sqrt(np.mean((face_sum - face) ** 2)))
    rms = float(np.sqrt(np.mean(face ** 2)))
    assert err / rms < 1e-9


def test_evaluate_noise_declares_patches_and_rejects_combos():
    text = Path("scripts/evaluate_noise.py").read_text(encoding="utf-8")
    assert "--patches" in text
    assert "★" not in text
    assert "cannot combine" in text.lower() or (
        "cannot use" in text and "patches" in text
    )
