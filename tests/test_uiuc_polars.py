"""Vendored UIUC-style polar tables for BEM Cl/Cd. Offline only."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from fansim.propeller.bemt import _cl_cd, _cl_cd_analytic
from fansim.propeller.polars import (
    POLAR_DIR,
    clear_polar_cache,
    cl_cd_table,
    family_for_camber,
    load_polar_family,
    section_table,
)


def test_polar_csvs_exist():
    assert (POLAR_DIR / "naca4412_re8e4.csv").is_file()
    assert (POLAR_DIR / "e387_re8e4.csv").is_file()
    assert (POLAR_DIR / "sd7032_re8e4.csv").is_file()
    assert (POLAR_DIR / "s1223_re8e4.csv").is_file()
    assert (POLAR_DIR / "README.md").is_file()


def test_family_for_camber_nearest():
    assert family_for_camber(0.0) == "naca0012"
    assert family_for_camber(0.02) == "naca2412"
    assert family_for_camber(0.04) == "naca4412"
    assert family_for_camber(0.035) == "naca4412"


def test_family_for_thickness_selects_selig():
    # Same camber as NACA 4412, thinner section → e387 (~9% thick)
    assert family_for_camber(0.04, thickness=0.09) == "e387"
    # Mid camber + 10% thick → sd7032
    assert family_for_camber(0.025, thickness=0.10) == "sd7032"
    # High camber at 12% → s1223
    assert family_for_camber(0.08, thickness=0.12) == "s1223"
    # Default thickness keeps NACA *12 for classic cambers
    assert family_for_camber(0.04, thickness=0.12) == "naca4412"


def test_cl_cd_table_matches_csv_row():
    clear_polar_cache()
    tables = load_polar_family("naca4412")
    assert 80000.0 in tables
    a, cl, cd = tables[80000.0]
    # pick α = 4°
    i = int(np.argmin(np.abs(a - 4.0)))
    out = cl_cd_table(math.radians(float(a[i])), 0.04, 80000.0)
    assert out is not None
    assert out[0] == pytest.approx(float(cl[i]), abs=0.02)
    assert out[1] == pytest.approx(float(cd[i]), abs=0.02)


def test_e387_table_hit_via_thickness():
    clear_polar_cache()
    tables = load_polar_family("e387")
    assert 80000.0 in tables
    a, cl, cd = tables[80000.0]
    i = int(np.argmin(np.abs(a - 4.0)))
    out = cl_cd_table(math.radians(float(a[i])), 0.04, 80000.0, thickness=0.09)
    assert out is not None
    assert out[0] == pytest.approx(float(cl[i]), abs=0.02)


def test_re_below_table_floor_returns_none():
    """Fan chord Re ~1–3e4 must not silently use the 4e4 table (§10.6)."""
    clear_polar_cache()
    assert cl_cd_table(math.radians(4.0), 0.04, 16000.0) is None
    # _cl_cd falls through to analytic
    cl, cd = _cl_cd(math.radians(4.0), 0.04, re=16000.0)
    assert math.isfinite(cl) and math.isfinite(cd)
    cl_a, cd_a = _cl_cd_analytic(math.radians(4.0), 0.04, re=16000.0)
    assert cl == pytest.approx(cl_a)
    assert cd == pytest.approx(cd_a)


def test_cl_cd_uses_table_when_re_set():
    clear_polar_cache()
    tab = _cl_cd(math.radians(4.0), 0.04, re=80000.0)
    ana = _cl_cd_analytic(math.radians(4.0), 0.04, re=80000.0)
    # Tables are shifted vs analytic — must differ
    assert abs(tab[0] - ana[0]) > 1e-4 or abs(tab[1] - ana[1]) > 1e-4
    assert math.isfinite(tab[0]) and math.isfinite(tab[1])


def test_cl_cd_analytic_when_re_none():
    cl, cd = _cl_cd(0.1, 0.04, re=None)
    assert math.isfinite(cl) and math.isfinite(cd)


def test_fallback_when_polar_dir_missing(monkeypatch, tmp_path):
    clear_polar_cache()
    import fansim.propeller.polars as pol
    monkeypatch.setattr(pol, "POLAR_DIR", tmp_path / "empty")
    clear_polar_cache()
    assert cl_cd_table(0.1, 0.04, 80000.0) is None
    cl, cd = _cl_cd(0.1, 0.04, re=80000.0)
    assert math.isfinite(cl) and math.isfinite(cd)


def test_no_star_in_polars_module():
    text = Path("fansim/propeller/polars.py").read_text(encoding="utf-8")
    assert "★" not in text


def test_naca4412_stall_gate_at_table_re():
    clear_polar_cache()
    attached = section_table(math.radians(4.0), 0.04, 80000.0)
    assert attached is not None
    cl, _cd, stalled, cap = attached
    assert stalled is False
    assert cl == pytest.approx(0.65703, abs=1e-5)
    assert cap == pytest.approx(1.04017, abs=1e-5)
    stalled_row = section_table(math.radians(16.0), 0.04, 80000.0)
    assert stalled_row is not None
    cl_s, _cd_s, stalled_s, cap_s = stalled_row
    assert stalled_s is True
    assert cl_s == pytest.approx(0.89370, abs=1e-5)
    assert cap_s == pytest.approx(1.04017, abs=1e-5)
    past = section_table(math.radians(64.0), 0.04, 80000.0)
    assert past is not None
    cl_p, _cd_p, stalled_p, cap_p = past
    assert stalled_p is True
    assert cl_p == pytest.approx(0.83129, abs=1e-5)
    assert cap_p == pytest.approx(1.04017, abs=1e-5)
    neg = section_table(math.radians(-5.0), 0.04, 80000.0)
    assert neg is not None
    cl_n, _cd_n, stalled_n, cap_n = neg
    assert stalled_n is True
    assert cl_n == pytest.approx(-0.28280, abs=1e-5)
    assert cap_n == pytest.approx(0.28280, abs=1e-5)
    near = section_table(math.radians(-4.0), 0.04, 80000.0)
    assert near is not None
    cl_a, _cd_a, stalled_a, cap_a = near
    assert stalled_a is False
    assert cl_a == pytest.approx(-0.17838, abs=1e-5)
    assert cap_a == pytest.approx(0.28280, abs=1e-5)


def test_stall_gate_blends_neighbor_tables():
    clear_polar_cache()
    re_mid = 10 ** (0.5 * (math.log10(40000.0) + math.log10(80000.0)))
    row = section_table(math.radians(16.0), 0.04, re_mid)
    assert row is not None
    cl, _cd, stalled, cap = row
    assert stalled is True
    assert cl == pytest.approx((0.79638 + 0.89370) / 2.0, abs=1e-5)
    assert cap == pytest.approx((0.95708 + 1.04017) / 2.0, abs=1e-5)
    attached = section_table(math.radians(4.0), 0.04, re_mid)
    assert attached is not None
    cl_a, _cd_a, stalled_a, cap_a = attached
    assert stalled_a is False
    assert cl_a == pytest.approx((0.63210 + 0.65703) / 2.0, abs=1e-5)
    assert cap_a == pytest.approx((0.95708 + 1.04017) / 2.0, abs=1e-5)


def test_section_table_misses_when_cl_cd_table_misses():
    clear_polar_cache()
    assert section_table(math.radians(4.0), 0.04, 16000.0) is None
