# Flow Report Card Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Fan → Results "Duct airflow" card with a plain-language "How the air moves" report
card. Each row gets a ✓/⚠/✕ verdict against Stock and a picture, behind a new global Simple/Expert switch.

**Architecture:**
- Pure numeric measurements (`fansim/cfd/flow_report.py`) run on cell samples from the saved loaded-point
  CFD case.
- Verdict rules live in `fansim/cfd/flow_verdicts.py`.
- A case adapter (`fansim/cfd/flow_report_case.py`) handles caching and comparability.
- Pictures are off-screen PyVista PNGs (`fansim/cfd/flow_report_viz.py`); the shared fixes go into
  `fansim/cfd/midplane.py`.
- A new Fan binder (`fansim/cockpit/fan_flow_report.py`) builds the report off the event loop. The card
  sits in `fan_tab_ui.py`.

**Tech Stack:** Python 3.12, numpy, PyVista (off-screen), matplotlib, trame + Vuetify 3, pytest.

**Spec:** `docs/superpowers/specs/2026-10-10-flow-report-card-design.md`

## Global Constraints

- No new CFD runs and no change to any score, objective or saved design result.
- Data source: the design's Assess case dir `Path(design.stl_path).parent`. Its fields are the
  **loaded** point. Flow goes from inlet −Z to outlet +Z, so forward means Uz > 0.
- Exit slab: z = z_fan + 0.18·r_tip ± max(0.04·r_tip, 0.002 m). Inlet slab: z_fan − 0.18·r_tip with the
  same half-width. Radial range hub_r ≤ r ≤ tip_r. Samples are weighted by cell volume.
- ρ = `RHO_AMCA` = 1.2 kg/m³. Pressure is shown in **Pa** (ρ·p_kinematic).
- **Verdict thresholds (exact):**
  - backflow: Δ ≤ +0.02 gives ✓; ✕ if the weighted mean exit Uz < 0;
  - bands: ±10 %;
  - swirl: ≤ 1.10 × Stock;
  - dead: ≤ Stock + 0.02, **and** tip ratio ≥ 0.90 × Stock;
  - noise: ΔSWL ≤ +1.0 dB;
  - dead threshold: |Uz| < 0.10 · mean Uz;
  - tip band: outer 10 % of the span;
  - noise hot spots: top 5 % of cells.
- `FLOW_REPORT_VERSION = 1`. Bump it whenever a measurement or picture changes.
- **Stock reference pointer:** `.cache/stock/flow_reference.json` (gitignored). Initial reference:
  `runs/screen_rank_audit/stock_hubclip/full`.
- **Comparable test settings:**
  - back pressure (`p_probe_pa / derate²`, rounded to 0.5 Pa);
  - `surf_max` (raw; a missing value is a mismatch);
  - `cfd_version`, `rpm`, `duct_shape`, `casing` from `constant/case_meta.json`.
  - **`hub_clip` is not compared.**
- **Plain-language copy:** simple mode uses the exact strings in this plan. Expert-only content carries
  "Technical detail, not reviewed for plain language".
- `ui_mode` ∈ {`simple`, `expert`}, default `simple`, persisted in browser `localStorage` key
  `fansim.ui_mode`.
- **Python:** `.venv/Scripts/python.exe`. **Tests:** `.venv/Scripts/python.exe -m pytest -q <path>`.
- **Files are CRLF on disk:** use the Edit tool, not shell `write_text`, for existing files.
- **Work on a branch `flow-report-card` in a worktree** (`.claude/worktrees/flow-report-card`). Merge to
  master after Task 9.

## Review Focus

1. **The exit slab catches no cells** (a coarse mesh, or a design whose fan sits off z=0). The row
   must read "not available" and never ✓. Pinned in Task 1 (`test_empty_slab_raises`) and Task 2
   (`test_unavailable_metrics_never_ok`).
2. **The Stock reference is missing, deleted, or points at a case without fields.** The card must show
   design-only verdicts plus the "no comparison" line, with no exception. Pinned in Task 3
   (`test_reference_missing_returns_none`, `test_report_without_reference`).
3. **The user switches designs while a report is building.** The stale result must not be shown. Pinned
   in Task 8 (`test_stale_token_not_applied`).
4. **An old `flow_report.json` from an earlier `FLOW_REPORT_VERSION`, or from an earlier CFD time,** must
   be recomputed, not reused. Pinned in Task 3 (`test_cache_invalidated_by_version`).
5. **A design with a different hub or tip radius from Stock:** bands must use each case's own radii, so
   band i means the same *fraction* of span. Pinned in Task 1 (`test_bands_use_own_radii`).

---

### Task 1: Flow measurements (pure numeric)

**Files:**
- Create: `fansim/cfd/flow_report.py`
- Test: `tests/test_flow_report.py`

**Interfaces:**
- Consumes: `fansim.cfd.spanwise.cylindrical_velocity(pts, u) -> (r, u_ax, u_th)`,
  `total_pressure_kin(p, u)`, `fansim.acoustics.proxies.epsilon_from_komega`,
  `proudman_power_density`, `sound_power_level`, `fansim.physics.air.RHO_AMCA`.
- Produces:
  - `FLOW_REPORT_VERSION: int`, `N_BANDS = 5`;
  - `class FlowReportUnavailable(Exception)`;
  - `@dataclass FlowSamples(pts, u, p, w, k=None, omega=None)`, all `np.ndarray`;
  - `@dataclass FlowMetrics(backflow_frac: float, net_reversed: bool, band_dp0_pa: list[float],
    swirl_frac: float, dead_frac: float, tip_band_uz_ratio: float, noise_swl_db: float | None,
    mean_uz_exit: float)` with `to_dict()` and `FlowMetrics.from_dict(d)`;
  - `exit_slab_mask(pts, *, hub_r, tip_r, z_fan) -> np.ndarray[bool]`;
  - `inlet_slab_mask(pts, *, hub_r, tip_r, z_fan) -> np.ndarray[bool]`;
  - `compute_metrics(s: FlowSamples, *, hub_r: float, tip_r: float, z_fan: float) -> FlowMetrics`;
  - `noise_density(k, omega) -> np.ndarray` (W/m³).

- [ ] **Step 1: Write the failing tests**

```python
"""Unit tests for fansim.cfd.flow_report (synthetic fields with known answers)."""
from __future__ import annotations

import numpy as np
import pytest

from fansim.cfd.flow_report import (
    FlowMetrics, FlowReportUnavailable, FlowSamples, compute_metrics, exit_slab_mask,
)

HUB, TIP = 0.02, 0.055


def _annulus(n_r=20, n_th=72, zs=(-0.0099, 0.0099)):
    """Cells on an annulus at the inlet (z<0) and exit (z>0) slab planes (0.18*TIP = 0.0099)."""
    rs = np.linspace(HUB + 0.0005, TIP - 0.0005, n_r)
    th = np.linspace(-np.pi, np.pi, n_th, endpoint=False)
    R, T, Z = np.meshgrid(rs, th, np.asarray(zs), indexing="ij")
    pts = np.column_stack([(R * np.cos(T)).ravel(), (R * np.sin(T)).ravel(), Z.ravel()])
    return pts


def _samples(pts, u, p=None, w=None, k=None, omega=None):
    n = pts.shape[0]
    return FlowSamples(pts=pts, u=u, p=np.zeros(n) if p is None else p,
                       w=np.ones(n) if w is None else w, k=k, omega=omega)


def test_uniform_forward_flow():
    pts = _annulus()
    u = np.tile([0.0, 0.0, 3.0], (pts.shape[0], 1))
    m = compute_metrics(_samples(pts, u), hub_r=HUB, tip_r=TIP, z_fan=0.0)
    assert m.backflow_frac == 0.0
    assert m.net_reversed is False
    assert m.dead_frac == 0.0
    assert m.swirl_frac == pytest.approx(0.0, abs=1e-12)
    assert m.tip_band_uz_ratio == pytest.approx(1.0)
    assert m.mean_uz_exit == pytest.approx(3.0)
    assert m.noise_swl_db is None  # no k/omega supplied


def test_ten_percent_backflow():
    pts = _annulus()
    u = np.tile([0.0, 0.0, 3.0], (pts.shape[0], 1))
    exit_idx = np.flatnonzero(pts[:, 2] > 0)
    u[exit_idx[: len(exit_idx) // 10], 2] = -1.0
    m = compute_metrics(_samples(pts, u), hub_r=HUB, tip_r=TIP, z_fan=0.0)
    assert m.backflow_frac == pytest.approx(0.10, abs=0.005)
    assert m.net_reversed is False


def test_net_reversed():
    pts = _annulus()
    u = np.tile([0.0, 0.0, -2.0], (pts.shape[0], 1))
    m = compute_metrics(_samples(pts, u), hub_r=HUB, tip_r=TIP, z_fan=0.0)
    assert m.net_reversed is True
    assert m.backflow_frac == pytest.approx(1.0)


def test_pure_swirl_fraction_is_one():
    pts = _annulus()
    r = np.hypot(pts[:, 0], pts[:, 1])
    u = np.column_stack([-pts[:, 1] / r * 4.0, pts[:, 0] / r * 4.0, np.full(len(r), 1e-9)])
    m = compute_metrics(_samples(pts, u), hub_r=HUB, tip_r=TIP, z_fan=0.0)
    assert m.swirl_frac == pytest.approx(1.0, abs=1e-6)


def test_band_rise_in_pa():
    pts = _annulus()
    u = np.tile([0.0, 0.0, 3.0], (pts.shape[0], 1))
    p = np.where(pts[:, 2] > 0, 10.0, 0.0)  # kinematic rise of 10 m2/s2 everywhere
    m = compute_metrics(_samples(pts, u, p=p), hub_r=HUB, tip_r=TIP, z_fan=0.0)
    assert len(m.band_dp0_pa) == 5
    assert all(v == pytest.approx(12.0) for v in m.band_dp0_pa)  # rho 1.2 * 10


def test_bands_use_own_radii():
    hub2, tip2 = 0.025, 0.05
    rs = np.linspace(hub2 + 0.0005, tip2 - 0.0005, 20)
    th = np.linspace(-np.pi, np.pi, 72, endpoint=False)
    R, T, Z = np.meshgrid(rs, th, np.asarray([-0.009, 0.009]), indexing="ij")
    pts = np.column_stack([(R * np.cos(T)).ravel(), (R * np.sin(T)).ravel(), Z.ravel()])
    u = np.tile([0.0, 0.0, 3.0], (pts.shape[0], 1))
    frac = (np.hypot(pts[:, 0], pts[:, 1]) - hub2) / (tip2 - hub2)
    p = np.where(pts[:, 2] > 0, 10.0 * (frac >= 0.8), 0.0)  # rise only in the outer fifth
    m = compute_metrics(_samples(pts, u, p=p), hub_r=hub2, tip_r=tip2, z_fan=0.0)
    assert m.band_dp0_pa[:4] == pytest.approx([0, 0, 0, 0], abs=1e-9)
    assert m.band_dp0_pa[4] == pytest.approx(12.0)


def test_dead_fraction_and_tip_ratio():
    pts = _annulus()
    r = np.hypot(pts[:, 0], pts[:, 1])
    frac = (r - HUB) / (TIP - HUB)
    uz = np.where(frac > 0.9, 0.05, 3.0)  # outer 10 % nearly still
    u = np.column_stack([np.zeros_like(uz), np.zeros_like(uz), uz])
    m = compute_metrics(_samples(pts, u), hub_r=HUB, tip_r=TIP, z_fan=0.0)
    assert m.dead_frac == pytest.approx(0.10, abs=0.03)
    assert m.tip_band_uz_ratio < 0.1


def test_volume_weighting():
    pts = _annulus()
    u = np.tile([0.0, 0.0, 3.0], (pts.shape[0], 1))
    exit_idx = np.flatnonzero(pts[:, 2] > 0)
    back = exit_idx[: len(exit_idx) // 10]
    u[back, 2] = -1.0
    w = np.ones(pts.shape[0])
    w[back] = 9.0  # 10 % of cells holding half the exit volume
    m = compute_metrics(_samples(pts, u, w=w), hub_r=HUB, tip_r=TIP, z_fan=0.0)
    assert m.backflow_frac == pytest.approx(0.5, abs=0.02)


def test_noise_present_when_k_omega_given():
    pts = _annulus()
    u = np.tile([0.0, 0.0, 3.0], (pts.shape[0], 1))
    k = np.full(pts.shape[0], 0.5)
    om = np.full(pts.shape[0], 2000.0)
    m = compute_metrics(_samples(pts, u, k=k, omega=om, w=np.full(pts.shape[0], 1e-9)),
                        hub_r=HUB, tip_r=TIP, z_fan=0.0)
    assert m.noise_swl_db is not None and np.isfinite(m.noise_swl_db)


def test_empty_slab_raises():
    pts = _annulus(zs=(-0.04, 0.04))  # nothing near +-0.0099
    u = np.tile([0.0, 0.0, 3.0], (pts.shape[0], 1))
    with pytest.raises(FlowReportUnavailable):
        compute_metrics(_samples(pts, u), hub_r=HUB, tip_r=TIP, z_fan=0.0)


def test_metrics_roundtrip_dict():
    m = FlowMetrics(0.1, False, [1, 2, 3, 4, 5], 0.2, 0.05, 0.9, 61.0, 2.5)
    assert FlowMetrics.from_dict(m.to_dict()) == m


def test_exit_slab_mask_excludes_hub_and_outside():
    pts = np.array([[0.01, 0, 0.0099], [0.03, 0, 0.0099], [0.06, 0, 0.0099], [0.03, 0, 0.03]])
    assert exit_slab_mask(pts, hub_r=HUB, tip_r=TIP, z_fan=0.0).tolist() == [False, True, False, False]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest -q tests/test_flow_report.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'fansim.cfd.flow_report'`

- [ ] **Step 3: Implement `fansim/cfd/flow_report.py`**

```python
"""Plain-language flow report: measurements on the saved loaded-point CFD field (roadmap §24).

Pure numpy on cell samples. The exit/inlet slabs match ``fansim.cfd.spanwise`` (z_fan +- 0.18 r_tip).
Flow runs inlet -Z -> outlet +Z in the CFD frame, so forward is Uz > 0. Weights are cell volumes.
Spec: docs/superpowers/specs/2026-10-10-flow-report-card-design.md
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from fansim.acoustics.proxies import epsilon_from_komega, proudman_power_density, sound_power_level
from fansim.cfd.spanwise import cylindrical_velocity, total_pressure_kin
from fansim.physics.air import RHO_AMCA

FLOW_REPORT_VERSION = 1
N_BANDS = 5
PLANE_Z_FRAC = 0.18           # same plane as fansim.cfd.spanwise._PLANE_Z_FRAC
DEAD_FRAC_OF_MEAN = 0.10      # |Uz| below this share of the mean exit Uz counts as dead air
TIP_BAND_FRAC = 0.10          # outer share of the span for the tip-leakage ratio
NOISE_Z_FRAC = 1.5            # rotor region for the noise total: |z - z_fan| <= 1.5 r_tip
NOISE_R_FRAC = 1.2            # ... and r <= 1.2 r_tip


class FlowReportUnavailable(Exception):
    """The field cannot support the report (e.g. no cells on the exit plane)."""


@dataclass
class FlowSamples:
    pts: np.ndarray
    u: np.ndarray
    p: np.ndarray
    w: np.ndarray
    k: np.ndarray | None = None
    omega: np.ndarray | None = None


@dataclass
class FlowMetrics:
    backflow_frac: float
    net_reversed: bool
    band_dp0_pa: list[float]
    swirl_frac: float
    dead_frac: float
    tip_band_uz_ratio: float
    noise_swl_db: float | None
    mean_uz_exit: float

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "FlowMetrics":
        return cls(**{k: d[k] for k in cls.__dataclass_fields__})


def _half_dz(tip_r: float) -> float:
    return max(0.04 * float(tip_r), 0.002)


def _annulus(pts, hub_r, tip_r):
    r = np.hypot(pts[:, 0], pts[:, 1])
    return (r >= hub_r) & (r <= tip_r)


def exit_slab_mask(pts, *, hub_r, tip_r, z_fan):
    z0 = float(z_fan) + PLANE_Z_FRAC * float(tip_r)
    return _annulus(pts, hub_r, tip_r) & (np.abs(pts[:, 2] - z0) <= _half_dz(tip_r))


def inlet_slab_mask(pts, *, hub_r, tip_r, z_fan):
    z0 = float(z_fan) - PLANE_Z_FRAC * float(tip_r)
    return _annulus(pts, hub_r, tip_r) & (np.abs(pts[:, 2] - z0) <= _half_dz(tip_r))


def _wmean(a, w) -> float:
    sw = float(np.sum(w))
    return float(np.sum(a * w) / sw) if sw > 0 else float("nan")


def noise_density(k, omega) -> np.ndarray:
    """Proudman acoustic power density [W/m^3] from k-omega fields."""
    return proudman_power_density(k, epsilon_from_komega(k, omega))


def _band_index(r, hub_r, tip_r):
    frac = (r - hub_r) / max(tip_r - hub_r, 1e-12)
    return np.clip((frac * N_BANDS).astype(int), 0, N_BANDS - 1)


def compute_metrics(s: FlowSamples, *, hub_r: float, tip_r: float, z_fan: float) -> FlowMetrics:
    pts, u, p, w = s.pts, s.u, np.asarray(s.p, float), np.asarray(s.w, float)
    ex = exit_slab_mask(pts, hub_r=hub_r, tip_r=tip_r, z_fan=z_fan)
    inn = inlet_slab_mask(pts, hub_r=hub_r, tip_r=tip_r, z_fan=z_fan)
    if not np.any(ex):
        raise FlowReportUnavailable("no cells on the exit plane")
    r, uz, uth = cylindrical_velocity(pts, u)
    we = w[ex]
    uz_e, uth_e, r_e = uz[ex], uth[ex], r[ex]

    mean_uz = _wmean(uz_e, we)
    backflow = _wmean((uz_e < 0).astype(float), we)
    denom = float(np.sum(we * (uz_e ** 2 + uth_e ** 2)))
    swirl = float(np.sum(we * uth_e ** 2) / denom) if denom > 0 else float("nan")
    dead_lim = DEAD_FRAC_OF_MEAN * abs(mean_uz)
    dead = _wmean((np.abs(uz_e) < dead_lim).astype(float), we)

    frac_e = (r_e - hub_r) / max(tip_r - hub_r, 1e-12)
    tip_sel = frac_e >= 1.0 - TIP_BAND_FRAC
    tip_ratio = (_wmean(uz_e[tip_sel], we[tip_sel]) / mean_uz
                 if np.any(tip_sel) and mean_uz != 0 else float("nan"))

    p0 = total_pressure_kin(p, u)
    b_ex = _band_index(r_e, hub_r, tip_r)
    b_in = _band_index(r[inn], hub_r, tip_r)
    p0_e, w_in, p0_in = p0[ex], w[inn], p0[inn]
    bands = []
    for i in range(N_BANDS):
        se, si = b_ex == i, b_in == i
        if not np.any(se) or not np.any(si):
            bands.append(float("nan"))
            continue
        bands.append(RHO_AMCA * (_wmean(p0_e[se], we[se]) - _wmean(p0_in[si], w_in[si])))

    swl = None
    if s.k is not None and s.omega is not None:
        rot = (np.abs(pts[:, 2] - z_fan) <= NOISE_Z_FRAC * tip_r) & (r <= NOISE_R_FRAC * tip_r)
        power = float(np.sum(noise_density(s.k[rot], s.omega[rot]) * w[rot]))
        swl = float(sound_power_level(power)) if power > 0 else None

    return FlowMetrics(
        backflow_frac=float(backflow), net_reversed=bool(mean_uz < 0), band_dp0_pa=bands,
        swirl_frac=swirl, dead_frac=float(dead), tip_band_uz_ratio=float(tip_ratio),
        noise_swl_db=swl, mean_uz_exit=float(mean_uz))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest -q tests/test_flow_report.py`
Expected: all PASS. If `test_band_rise_in_pa` fails, check that p0 includes ½|U|² on **both** slabs
(it cancels for uniform U).

- [ ] **Step 5: Commit**

```bash
git add fansim/cfd/flow_report.py tests/test_flow_report.py
git commit -m "feat(flow-report): measurements on the loaded-point field (backflow, bands, swirl, dead, tip, noise)"
```

---

### Task 2: Verdict rules and plain-language text

**Files:**
- Create: `fansim/cfd/flow_verdicts.py`
- Test: `tests/test_flow_verdicts.py`

**Interfaces:**
- Consumes: `FlowMetrics` (Task 1).
- Produces:
  - `@dataclass RowVerdict(key: str, title: str, status: str, text: str, better: bool | None,
    bands: list[str] | None = None)`. `status` ∈ {"ok", "warn", "bad", "na"}.
  - `ROW_KEYS = ("direction", "push", "spin", "dead", "noise")`.
  - `judge(design: FlowMetrics, stock: FlowMetrics | None) -> list[RowVerdict]` (always 5 rows, in
    `ROW_KEYS` order).
  - `overall_line(rows: list[RowVerdict], compared: bool) -> str`.
  - `ICONS = {"ok": "✓", "warn": "⚠", "bad": "✕", "na": "–"}`.

- [ ] **Step 1: Write the failing tests**

```python
from __future__ import annotations

import math

from fansim.cfd.flow_report import FlowMetrics
from fansim.cfd.flow_verdicts import ROW_KEYS, judge, overall_line

STOCK = FlowMetrics(0.06, False, [2.0, 4.0, 6.0, 8.0, 6.0], 0.20, 0.05, 0.80, 60.0, 2.5)


def _m(**kw):
    d = STOCK.to_dict() | kw
    return FlowMetrics.from_dict(d)


def test_stock_vs_itself_all_ok_and_similar():
    rows = judge(STOCK, STOCK)
    assert [r.key for r in rows] == list(ROW_KEYS)
    assert all(r.status == "ok" for r in rows)
    assert rows[1].bands == ["similar"] * 5
    assert overall_line(rows, compared=True) == "About the same as Stock on every check."


def test_backflow_edge():
    assert judge(_m(backflow_frac=0.08), STOCK)[0].status == "ok"      # +0.02 exactly
    assert judge(_m(backflow_frac=0.0801), STOCK)[0].status == "warn"
    assert judge(_m(net_reversed=True), STOCK)[0].status == "bad"


def test_band_labels():
    rows = judge(_m(band_dp0_pa=[2.3, 4.0, 5.3, 8.8, 6.0]), STOCK)
    assert rows[1].bands == ["stronger", "similar", "weaker", "similar", "similar"]


def test_swirl_dead_noise_edges():
    assert judge(_m(swirl_frac=0.22), STOCK)[2].status == "ok"
    assert judge(_m(swirl_frac=0.2201), STOCK)[2].status == "warn"
    assert judge(_m(dead_frac=0.0701), STOCK)[3].status == "warn"
    assert judge(_m(tip_band_uz_ratio=0.71), STOCK)[3].status == "warn"
    assert judge(_m(noise_swl_db=61.0), STOCK)[4].status == "ok"
    assert judge(_m(noise_swl_db=61.01), STOCK)[4].status == "warn"


def test_noise_missing_is_na():
    assert judge(_m(noise_swl_db=None), STOCK)[4].status == "na"


def test_unavailable_metrics_never_ok():
    rows = judge(_m(swirl_frac=math.nan, dead_frac=math.nan, tip_band_uz_ratio=math.nan), STOCK)
    assert rows[2].status == "na" and rows[3].status == "na"


def test_no_stock_only_direction_judged():
    rows = judge(STOCK, None)
    assert rows[0].status == "ok"
    assert [r.status for r in rows[1:]] == ["na"] * 4
    assert overall_line(rows, compared=False).startswith("No Stock comparison")


def test_overall_better_and_worse():
    d = _m(backflow_frac=0.02, swirl_frac=0.30)
    line = overall_line(judge(d, STOCK), compared=True)
    assert line == "Better than Stock at: air direction. Worse at: wasted spin."
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest -q tests/test_flow_verdicts.py`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `fansim/cfd/flow_verdicts.py`**

```python
"""Verdict rules for the flow report card (thresholds fixed in the spec, §24)."""

from __future__ import annotations

import math
from dataclasses import dataclass

from fansim.cfd.flow_report import FlowMetrics

ROW_KEYS = ("direction", "push", "spin", "dead", "noise")
TITLES = {"direction": "Air direction", "push": "Push along the blade", "spin": "Wasted spin",
          "dead": "Dead or blocked air", "noise": "Noise hint"}
ICONS = {"ok": "✓", "warn": "⚠", "bad": "✕", "na": "–"}

BACKFLOW_MARGIN = 0.02
BAND_TOL = 0.10
SWIRL_FACTOR = 1.10
DEAD_MARGIN = 0.02
TIP_FACTOR = 0.90
NOISE_MARGIN_DB = 1.0


@dataclass
class RowVerdict:
    key: str
    title: str
    status: str
    text: str
    better: bool | None
    bands: list[str] | None = None


def _bad(x) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x))


def _pct(x: float) -> str:
    return f"{100.0 * x:.0f} %"


def _row(key, status, text, better=None, bands=None):
    return RowVerdict(key, TITLES[key], status, text, better, bands)


def _direction(d: FlowMetrics, s: FlowMetrics | None) -> RowVerdict:
    if d.net_reversed:
        return _row("direction", "bad",
                    "More air goes backwards than forwards: this fan is blowing the wrong way.", False)
    if _bad(d.backflow_frac):
        return _row("direction", "na", "Couldn't measure the air direction for this run.")
    if s is None:
        return _row("direction", "ok",
                    f"Air leaves out the back. {_pct(d.backflow_frac)} of the fan face flows backwards.")
    ok = d.backflow_frac <= s.backflow_frac + BACKFLOW_MARGIN + 1e-12
    text = (f"{_pct(d.backflow_frac)} of the fan face flows backwards "
            f"(Stock {_pct(s.backflow_frac)}). Less is better.")
    return _row("direction", "ok" if ok else "warn", text,
                better=d.backflow_frac < s.backflow_frac - BACKFLOW_MARGIN)


def _push(d, s):
    if s is None:
        return _row("push", "na", "No Stock comparison for the push along the blade.")
    labels = []
    for a, b in zip(d.band_dp0_pa, s.band_dp0_pa):
        if _bad(a) or _bad(b) or b == 0:
            labels.append("unknown")
        elif a > b * (1 + BAND_TOL):
            labels.append("stronger")
        elif a < b * (1 - BAND_TOL):
            labels.append("weaker")
        else:
            labels.append("similar")
    n_up, n_dn = labels.count("stronger"), labels.count("weaker")
    names = ["near the hub", "inner middle", "middle", "outer middle", "near the tip"]
    parts = []
    if n_up:
        parts.append("stronger " + ", ".join(n for n, l in zip(names, labels) if l == "stronger"))
    if n_dn:
        parts.append("weaker " + ", ".join(n for n, l in zip(names, labels) if l == "weaker"))
    text = ("Pushes about as hard as Stock all along the blade." if not parts
            else "Compared with Stock: " + "; ".join(parts) + ".")
    status = "na" if labels.count("unknown") == len(labels) else ("warn" if n_dn > n_up else "ok")
    return _row("push", status, text, better=n_up > n_dn, bands=labels)


def _spin(d, s):
    if s is None or _bad(d.swirl_frac) or _bad(s.swirl_frac):
        return _row("spin", "na", "Couldn't compare the spin in the outgoing air.")
    ok = d.swirl_frac <= s.swirl_frac * SWIRL_FACTOR + 1e-12
    text = (f"{_pct(d.swirl_frac)} of the outgoing air's energy is spin instead of forward flow "
            f"(Stock {_pct(s.swirl_frac)}). Less is better.")
    return _row("spin", "ok" if ok else "warn", text, better=d.swirl_frac < s.swirl_frac / SWIRL_FACTOR)


def _dead(d, s):
    vals = (d.dead_frac, d.tip_band_uz_ratio)
    if s is None or any(_bad(v) for v in vals) or _bad(s.dead_frac) or _bad(s.tip_band_uz_ratio):
        return _row("dead", "na", "Couldn't compare dead or blocked air.")
    dead_ok = d.dead_frac <= s.dead_frac + DEAD_MARGIN + 1e-12
    tip_ok = d.tip_band_uz_ratio >= s.tip_band_uz_ratio * TIP_FACTOR - 1e-12
    bits = [f"{_pct(d.dead_frac)} of the fan face has air that barely moves (Stock {_pct(s.dead_frac)})."]
    if not tip_ok:
        bits.append("Air near the blade tips is weak: likely leaking round the tips.")
    return _row("dead", "ok" if dead_ok and tip_ok else "warn", " ".join(bits),
                better=d.dead_frac < s.dead_frac - DEAD_MARGIN and tip_ok)


def _noise(d, s):
    if d.noise_swl_db is None:
        return _row("noise", "na", "No turbulence data in this run.")
    if s is None or s.noise_swl_db is None:
        return _row("noise", "na", "No Stock comparison for noise.")
    delta = d.noise_swl_db - s.noise_swl_db
    word = "quieter" if delta < 0 else "louder"
    text = (f"Rough estimate: about {abs(delta):.1f} dB {word} than Stock. "
            "Compare only; this is not a real sound measurement.")
    return _row("noise", "ok" if delta <= NOISE_MARGIN_DB + 1e-12 else "warn", text,
                better=delta < -NOISE_MARGIN_DB)


def judge(design: FlowMetrics, stock: FlowMetrics | None) -> list[RowVerdict]:
    return [_direction(design, stock), _push(design, stock), _spin(design, stock),
            _dead(design, stock), _noise(design, stock)]


def overall_line(rows: list[RowVerdict], compared: bool) -> str:
    if not compared:
        return "No Stock comparison for this run, so only the air direction is checked."
    better = [r.title.lower() for r in rows if r.status == "ok" and r.better]
    worse = [r.title.lower() for r in rows if r.status in ("warn", "bad")]
    if not better and not worse:
        return "About the same as Stock on every check."
    parts = []
    if better:
        parts.append("Better than Stock at: " + ", ".join(better) + ".")
    if worse:
        parts.append("Worse at: " + ", ".join(worse) + ".")
    return " ".join(parts)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest -q tests/test_flow_verdicts.py`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add fansim/cfd/flow_verdicts.py tests/test_flow_verdicts.py
git commit -m "feat(flow-report): verdict rules + plain-language row text"
```

---

### Task 3: Case adapter, cache, comparability, Stock reference

**Files:**
- Create: `fansim/cfd/flow_report_case.py`
- Create: `fansim/cockpit/flow_reference.py`
- Create: `scripts/set_flow_reference.py`
- Test: `tests/test_flow_report_case.py`

**Interfaces:**
- Consumes: `compute_metrics`, `FlowSamples`, `FlowMetrics`, `FLOW_REPORT_VERSION` (Task 1);
  `fansim.cfd.spanwise.load_case_radii_omega(case_dir)`;
  `fansim.cfd.cockpit_viz.load_case_mesh(case_dir) -> pv grid | None`;
  `fansim.cockpit.stock_cache.STOCK_CACHE_DIR`.
- Produces:
  - `samples_from_mesh(mesh) -> FlowSamples`;
  - `case_geometry(case_dir, mesh) -> tuple[float, float, float]` (hub_r, tip_r, z_fan);
  - `test_settings(case_dir) -> dict`;
  - `first_mismatch(a: dict, b: dict) -> str | None`;
  - `report_json_path(case_dir) -> Path` (`<case>/flow_report.json`);
  - `latest_time(case_dir) -> str`;
  - `load_or_compute_metrics(case_dir, *, mesh=None, loader=load_case_mesh) -> FlowMetrics`
    (raises `FlowReportUnavailable`);
  - in `fansim/cockpit/flow_reference.py`: `REFERENCE_FILE: Path`,
    `set_reference(case_dir) -> None`, `get_reference() -> Path | None`.

- [ ] **Step 1: Write the failing tests**

```python
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import pyvista as pv

from fansim.cfd import flow_report_case as frc
from fansim.cfd.flow_report import FLOW_REPORT_VERSION, FlowReportUnavailable


def _grid(uz=3.0):
    """Small structured annulus-ish block around z=0 with cell U/p/k/omega."""
    # z spacing 2.5 mm so cell centres (±0.00875, ±0.01125) fall inside the ±0.0098 ± 0.0022 slabs
    g = pv.ImageData(dimensions=(23, 23, 17), spacing=(0.005, 0.005, 0.0025),
                     origin=(-0.055, -0.055, -0.02)).cast_to_unstructured_grid()
    n = g.n_cells
    g.cell_data["U"] = np.tile([0.0, 0.0, uz], (n, 1))
    g.cell_data["p"] = np.zeros(n)
    g.cell_data["k"] = np.full(n, 0.3)
    g.cell_data["omega"] = np.full(n, 1500.0)
    return g


def _case(tmp_path: Path, *, surf_max=4, p_probe=8.0, derate=1.0, rpm=2000.0, time="500") -> Path:
    c = tmp_path / "case"
    (c / "constant").mkdir(parents=True)
    (c / time).mkdir()
    (c / "constant" / "case_meta.json").write_text(json.dumps({
        "hub_radius_m": 0.0215, "tip_radius_m": 0.0545, "rpm": rpm, "spin": -1,
        "cfd_version": 5, "duct_shape": "ring", "casing": True}))
    (c / "_eval_result.json").write_text(json.dumps({"raw": {
        "surf_max": surf_max, "p_probe_pa": p_probe, "derate": derate}}))
    return c


def test_samples_from_mesh_has_weights_and_turbulence():
    s = frc.samples_from_mesh(_grid())
    assert s.w.shape[0] == s.pts.shape[0] and np.all(s.w > 0)
    assert s.k is not None and s.omega is not None


def test_settings_and_mismatch(tmp_path):
    a = frc.test_settings(_case(tmp_path / "a"))
    assert a["back_pressure_pa"] == 8.0 and a["surf_max"] == 4
    b = frc.test_settings(_case(tmp_path / "b", p_probe=8.0 * 0.9 ** 2, derate=0.9))
    assert frc.first_mismatch(a, b) is None          # derated probe maps back to 8 Pa
    c = frc.test_settings(_case(tmp_path / "c", surf_max=None))
    assert frc.first_mismatch(a, c) == "mesh level not recorded"
    d = frc.test_settings(_case(tmp_path / "d", rpm=2200.0))
    assert "rpm" in frc.first_mismatch(a, d)


def test_compute_and_cache(tmp_path):
    case = _case(tmp_path)
    calls = []

    def loader(cd):
        calls.append(cd)
        return _grid()

    m1 = frc.load_or_compute_metrics(case, loader=loader)
    m2 = frc.load_or_compute_metrics(case, loader=loader)
    assert m1 == m2 and len(calls) == 1
    data = json.loads(frc.report_json_path(case).read_text())
    assert data["version"] == FLOW_REPORT_VERSION and data["time"] == "500"


def test_cache_invalidated_by_version(tmp_path):
    case = _case(tmp_path)
    frc.report_json_path(case).write_text(json.dumps(
        {"version": FLOW_REPORT_VERSION - 1, "time": "500", "metrics": {}}))
    m = frc.load_or_compute_metrics(case, loader=lambda cd: _grid())
    assert m.mean_uz_exit == pytest.approx(3.0)
    (case / "750").mkdir()  # a newer CFD time also invalidates
    m2 = frc.load_or_compute_metrics(case, loader=lambda cd: _grid(uz=2.0))
    assert m2.mean_uz_exit == pytest.approx(2.0)


def test_no_fields_raises(tmp_path):
    with pytest.raises(FlowReportUnavailable):
        frc.load_or_compute_metrics(_case(tmp_path), loader=lambda cd: None)


def test_reference_missing_returns_none(tmp_path, monkeypatch):
    from fansim.cockpit import flow_reference as fr
    monkeypatch.setattr(fr, "REFERENCE_FILE", tmp_path / "ref.json")
    assert fr.get_reference() is None
    case = _case(tmp_path)
    fr.set_reference(case)
    assert fr.get_reference() == case.resolve()
    import shutil
    shutil.rmtree(case)
    assert fr.get_reference() is None  # deleted reference reads as missing
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest -q tests/test_flow_report_case.py`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `fansim/cfd/flow_report_case.py`**

```python
"""Flow report <-> saved CFD case: samples, geometry, test settings, cached metrics (§24)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from fansim.cfd.flow_report import (
    FLOW_REPORT_VERSION, FlowMetrics, FlowReportUnavailable, FlowSamples, compute_metrics,
)
from fansim.cfd.spanwise import load_case_radii_omega

REPORT_FILE = "flow_report.json"


def _default_loader(case_dir):
    from fansim.cfd.cockpit_viz import load_case_mesh
    return load_case_mesh(case_dir)


def samples_from_mesh(mesh) -> FlowSamples:
    g = mesh
    if "U" not in g.cell_data and "U" in g.point_data:
        g = g.point_data_to_cell_data()
    if "U" not in g.cell_data:
        raise FlowReportUnavailable("no velocity field")
    pts = np.asarray(g.cell_centers().points, float)
    n = pts.shape[0]
    u = np.asarray(g.cell_data["U"], float).reshape(n, -1)
    p = np.asarray(g.cell_data["p"], float).reshape(-1) if "p" in g.cell_data else np.zeros(n)
    sizes = g.compute_cell_sizes(length=False, area=False, volume=True)
    w = np.abs(np.asarray(sizes.cell_data["Volume"], float))
    k = np.asarray(g.cell_data["k"], float).reshape(-1) if "k" in g.cell_data else None
    om = np.asarray(g.cell_data["omega"], float).reshape(-1) if "omega" in g.cell_data else None
    return FlowSamples(pts=pts, u=u, p=p, w=w, k=k, omega=om)


def case_geometry(case_dir, mesh) -> tuple[float, float, float]:
    hub_r, tip_r, _omega = load_case_radii_omega(case_dir)
    b = getattr(mesh, "bounds", None)
    z_fan = 0.0 if b is None or float(b[4]) < 0.0 < float(b[5]) else 0.5 * (float(b[4]) + float(b[5]))
    return float(hub_r), float(tip_r), float(z_fan)


def _json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def test_settings(case_dir) -> dict:
    case_dir = Path(case_dir)
    raw = _json(case_dir / "_eval_result.json").get("raw") or {}
    meta = _json(case_dir / "constant" / "case_meta.json")
    bp = None
    try:
        der = float(raw.get("derate") or 1.0)
        bp = round(float(raw["p_probe_pa"]) / (der * der) * 2.0) / 2.0
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        bp = None
    return {"back_pressure_pa": bp, "surf_max": raw.get("surf_max"),
            "cfd_version": meta.get("cfd_version"), "rpm": meta.get("rpm"),
            "duct_shape": meta.get("duct_shape"), "casing": meta.get("casing")}


_LABELS = {"back_pressure_pa": "hose back pressure", "surf_max": "mesh level",
           "cfd_version": "solver version", "rpm": "rpm", "duct_shape": "duct shape",
           "casing": "casing"}


def first_mismatch(a: dict, b: dict) -> str | None:
    if a.get("surf_max") is None or b.get("surf_max") is None:
        return "mesh level not recorded"
    for key, label in _LABELS.items():
        if a.get(key) != b.get(key):
            return f"different {label} ({a.get(key)} vs {b.get(key)})"
    return None


def report_json_path(case_dir) -> Path:
    return Path(case_dir) / REPORT_FILE


def latest_time(case_dir) -> str:
    case_dir = Path(case_dir)
    roots = [case_dir] + sorted(case_dir.glob("processor0"))
    times = []
    for root in roots:
        for d in root.iterdir() if root.is_dir() else []:
            if d.is_dir():
                try:
                    times.append((float(d.name), d.name))
                except ValueError:
                    pass
    return max(times)[1] if times else "0"


def load_or_compute_metrics(case_dir, *, mesh=None, loader=None) -> FlowMetrics:
    case_dir = Path(case_dir)
    path = report_json_path(case_dir)
    t = latest_time(case_dir)
    cached = _json(path)
    if cached.get("version") == FLOW_REPORT_VERSION and cached.get("time") == t and cached.get("metrics"):
        try:
            return FlowMetrics.from_dict(cached["metrics"])
        except (KeyError, TypeError):
            pass
    if mesh is None:
        mesh = (loader or _default_loader)(case_dir)
    if mesh is None:
        raise FlowReportUnavailable("no saved flow fields")
    hub_r, tip_r, z_fan = case_geometry(case_dir, mesh)
    m = compute_metrics(samples_from_mesh(mesh), hub_r=hub_r, tip_r=tip_r, z_fan=z_fan)
    try:
        path.write_text(json.dumps({"version": FLOW_REPORT_VERSION, "time": t,
                                    "metrics": m.to_dict()}, indent=1), encoding="utf-8")
    except OSError:
        pass
    return m
```

The function is named `test_settings`, so pytest would try to collect it when the test module does
`from ... import`. The test file uses `frc.test_settings` through the module, which avoids that.
**Do not** `from fansim.cfd.flow_report_case import test_settings` in a test.

- [ ] **Step 4: Implement `fansim/cockpit/flow_reference.py` and the script**

```python
"""Which saved Stock CFD case the flow report compares against (gitignored pointer, §24)."""

from __future__ import annotations

import json
from pathlib import Path

from fansim.cockpit.stock_cache import STOCK_CACHE_DIR

REFERENCE_FILE = STOCK_CACHE_DIR / "flow_reference.json"


def set_reference(case_dir) -> None:
    REFERENCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    REFERENCE_FILE.write_text(json.dumps({"case_dir": str(Path(case_dir).resolve())}), encoding="utf-8")


def get_reference() -> Path | None:
    try:
        p = Path(json.loads(REFERENCE_FILE.read_text(encoding="utf-8"))["case_dir"])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return p if p.is_dir() else None
```

`scripts/set_flow_reference.py`:

```python
"""Point the flow report at a saved Stock Assess case.

    .venv/Scripts/python.exe scripts/set_flow_reference.py runs/screen_rank_audit/stock_hubclip/full
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fansim.cfd.flow_report_case import load_or_compute_metrics  # noqa: E402
from fansim.cockpit.flow_reference import REFERENCE_FILE, set_reference  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    case = Path(argv[0])
    m = load_or_compute_metrics(case)  # fails loudly if the case has no usable fields
    set_reference(case)
    print(f"reference -> {case.resolve()} ({REFERENCE_FILE})")
    print(m.to_dict())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest -q tests/test_flow_report_case.py`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add fansim/cfd/flow_report_case.py fansim/cockpit/flow_reference.py scripts/set_flow_reference.py tests/test_flow_report_case.py
git commit -m "feat(flow-report): case adapter, cached metrics, test-setting comparability, Stock reference pointer"
```

---

### Task 4: Shared picture fixes (smooth, Pa, Stock-based scale, rotor outline)

**Files:**
- Modify: `fansim/cfd/midplane.py` (`render_midplane_pngs` `_shot` around lines 421–470;
  `render_axial_uz_png` around 525–625; add helpers near `throughflow_umag_clim` at line 318)
- Test: `tests/test_midplane.py` (append)

**Interfaces:**
- Produces, in `fansim.cfd.midplane`:
  - `robust_clim(values, lo_pct=2.0, hi_pct=98.0, symmetric=False) -> tuple[float, float]`;
  - `pressure_pa(p_kin) -> np.ndarray` (× `RHO_AMCA`);
  - `rotor_outline(case_dir, normal, origin) -> pv.PolyData | None` (slice of
    `constant/triSurface/impeller.stl`, which is in metres in the CFD frame);
  - a `clim_override: dict[str, tuple[float, float]] | None = None` keyword on `render_midplane_pngs`.

- [ ] **Step 1: Write the failing tests**

```python
def test_robust_clim_ignores_spikes():
    from fansim.cfd.midplane import robust_clim
    v = np.r_[np.linspace(0, 5, 1000), [400.0, 500.0]]
    lo, hi = robust_clim(v)
    assert lo == pytest.approx(0.1, abs=0.05) and hi < 6.0
    slo, shi = robust_clim(np.r_[v, -v], symmetric=True)
    assert slo == -shi


def test_pressure_pa_scales_by_rho():
    from fansim.cfd.midplane import pressure_pa
    assert pressure_pa(np.array([10.0]))[0] == pytest.approx(12.0)


def test_rotor_outline_none_without_stl(tmp_path):
    from fansim.cfd.midplane import rotor_outline
    assert rotor_outline(tmp_path, (0, 1, 0), (0, 0, 0)) is None


def test_rotor_outline_slices_stl(tmp_path):
    import pyvista as pv
    from fansim.cfd.midplane import rotor_outline
    tri = tmp_path / "constant" / "triSurface"
    tri.mkdir(parents=True)
    pv.Cylinder(radius=0.05, height=0.01, direction=(0, 0, 1)).triangulate().save(tri / "impeller.stl")
    out = rotor_outline(tmp_path, (0, 1, 0), (0, 0, 0))
    assert out is not None and out.n_points > 0
```

(If `tests/test_midplane.py` lacks `import numpy as np` / `import pytest`, add them.)

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest -q tests/test_midplane.py -k "robust_clim or pressure_pa or rotor_outline"`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Add the helpers to `midplane.py`** (after `throughflow_umag_clim`)

```python
def robust_clim(values, lo_pct: float = 2.0, hi_pct: float = 98.0,
                symmetric: bool = False) -> tuple[float, float]:
    """Colour range from percentiles so a few tip spikes don't flatten the picture (§24)."""
    arr = np.asarray(values, dtype=float).reshape(-1)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return (0.0, 1.0)
    if symmetric:
        m = float(np.percentile(np.abs(arr), hi_pct)) or 1.0
        return (-m, m)
    lo, hi = float(np.percentile(arr, lo_pct)), float(np.percentile(arr, hi_pct))
    return (lo, hi if hi > lo else lo + 1.0)


def pressure_pa(p_kin) -> np.ndarray:
    """OpenFOAM incompressible p is kinematic (m^2/s^2); multiply by rho for Pa."""
    from fansim.physics.air import RHO_AMCA
    return np.asarray(p_kin, dtype=float) * RHO_AMCA


def rotor_outline(case_dir, normal, origin):
    """Grey outline of the rotor where a plane cuts it, or None when the CFD STL is missing."""
    stl = Path(case_dir) / "constant" / "triSurface" / "impeller.stl"
    if not stl.is_file():
        return None
    try:
        out = pv.read(str(stl)).slice(normal=tuple(normal), origin=tuple(origin))
    except Exception:  # noqa: BLE001
        return None
    return out if out.n_points > 0 else None
```

`midplane.py` imports PyVista lazily (inside functions), so put `import pyvista as pv` inside
`rotor_outline`. `Path` and `np` are module-level imports already.

- [ ] **Step 4: Use the helpers in `render_midplane_pngs._shot`**
  1. Before the `_shot` definition, smooth the slice once:
     `slc = slc.cell_data_to_point_data(pass_cell_data=False)` (wrapped in try/except, keeping the
     original on failure).
  2. Add `slc.point_data["p_pa"] = pressure_pa(slc.point_data["p"])` when `"p"` is present, and call
     `_shot("p_pa", ...)` instead of `_shot("p", ...)`.
  3. Change `title_p` to `"pressure (Pa)"` and `title_u` to `"speed (m/s)"` (both layouts: replace
     `m2/s2` with `Pa`).
  4. In `_shot`, set the colour range:
     - U_mag keeps `throughflow_umag_clim`;
     - p_pa uses `robust_clim(..., symmetric=False)`;
     - `clim_override.get(scalars)` wins when given.
  5. After `pl.add_mesh(slc, ...)`, draw the outline:
     `ol = rotor_outline(case_dir, (0, 1, 0), origin)`, then
     `if ol is not None: pl.add_mesh(ol, color="black", line_width=2)`.
  6. Remove the in-image `pl.add_text(title, ...)` (the card shows titles in HTML). Keep the
     FRONT/OUTLET side labels.
  7. Bump the cached PNG file names at the top of `midplane.py` so old PNGs are rebuilt:
     - `_U_NAME` → `"U_midplane_v9.png"`;
     - `_P_NAME` → `"p_midplane_v8.png"`;
     - both `_SCROLL` names → `_v2`;
     - `_UAXIAL_NAME` → its next version;
     - Task 5 does the same for `_STREAM_NAME`.
  8. Apply the same `cell_data_to_point_data` smoothing and rotor outline (normal `(0, 0, 1)`, origin at
     the slice z) in `render_axial_uz_png`.

- [ ] **Step 5: Run the midplane and airflow tests**

Run: `.venv/Scripts/python.exe -m pytest -q tests/test_midplane.py tests/test_airflow_panel.py tests/test_prop_airflow_case.py`
Expected: all PASS. If an existing test asserts the old title text `m2/s2`, update it to `Pa`; the unit
change is intended.

- [ ] **Step 6: Commit**

```bash
git add fansim/cfd/midplane.py tests/test_midplane.py
git commit -m "fix(airflow): smooth shading, pressure in Pa, percentile colour range, rotor outline on cuts"
```

---

### Task 5: Rebuilt streamlines (side view, see-through fan, upstream seeds)

**Files:**
- Modify: `fansim/cfd/midplane.py` `render_streamlines_png` (around lines 647–780)
- Test: `tests/test_midplane.py` (append)

**Interfaces:**
- Produces: `streamline_seed_points(tip_r: float, z_fan: float, cx=0.0, cy=0.0, n_per_ring=12) ->
  pv.PolyData`, with seeds on rings at 0.4/0.65/0.9·tip_r, at z = z_fan − 1.0·tip_r.

- [ ] **Step 1: Write the failing test**

```python
def test_streamline_seeds_upstream_rings():
    from fansim.cfd.midplane import streamline_seed_points
    s = streamline_seed_points(0.05, 0.0, n_per_ring=12)
    pts = np.asarray(s.points)
    assert pts.shape == (36, 3)
    assert np.allclose(pts[:, 2], -0.05)
    radii = sorted(set(np.round(np.hypot(pts[:, 0], pts[:, 1]), 6)))
    assert radii == pytest.approx([0.02, 0.0325, 0.045])
```

- [ ] **Step 2: Run it to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest -q tests/test_midplane.py -k streamline_seeds`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement**

```python
def streamline_seed_points(tip_r: float, z_fan: float, cx: float = 0.0, cy: float = 0.0,
                           n_per_ring: int = 12):
    """Seeds upstream of the fan on three rings (inner, middle, outer span)."""
    pts = []
    for frac in (0.4, 0.65, 0.9):
        r = frac * tip_r
        for th in np.linspace(0.0, 2.0 * np.pi, n_per_ring, endpoint=False):
            pts.append((cx + r * np.cos(th), cy + r * np.sin(th), z_fan - 1.0 * tip_r))
    return pv.PolyData(np.asarray(pts, dtype=float))
```

In `render_streamlines_png`:
1. Replace the downstream `pv.Disc` seed with `streamline_seed_points(r_tip, z_fan, cx, cy)`.
2. Use `integration_direction="both"`.
3. After adding the tubes, add the fan: read `constant/triSurface/impeller.stl` if present and call
   `pl.add_mesh(fan, color="lightgray", opacity=0.3)`.
4. Set a side view, looking along +Y at the fan with the flow left → right:
   `pl.camera_position = [(cx, cy - 6.0 * r_tip, z_fan), (cx, cy, z_fan), (1.0, 0.0, 0.0)]`, then
   `pl.reset_camera()`, then `pl.camera.zoom(1.3)`.
   - Check this view against the midplane picture's side labels. Inlet must appear on the LEFT; if it
     appears on the right, negate the view-up vector.
5. Remove the in-image title text.
6. Keep the 95th-percentile clim clamp.
7. Rename `_STREAM_NAME` to its next version so old streamline PNGs are rebuilt.

- [ ] **Step 4: Run the tests**

Run: `.venv/Scripts/python.exe -m pytest -q tests/test_midplane.py`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add fansim/cfd/midplane.py tests/test_midplane.py
git commit -m "fix(airflow): streamlines seeded upstream, both directions, side view with see-through fan"
```

---

### Task 6: Report-card pictures

**Files:**
- Create: `fansim/cfd/flow_report_viz.py`
- Test: `tests/test_flow_report_viz.py`

**Interfaces:**
- Consumes: `samples_from_mesh`, `case_geometry` (Task 3); `exit_slab_mask`, `noise_density`,
  `FlowMetrics` (Task 1); `robust_clim`, `rotor_outline` (Task 4); the `_RENDER_LOCK` already in
  `fansim.cfd.midplane`.
- Produces:
  - `PICTURES = ("face", "push", "spin", "noise")`;
  - `render_report_pictures(case_dir, *, mesh, scales: dict | None = None, out_dir=None,
    stock_bands: list[float] | None = None, metrics: FlowMetrics | None = None) -> dict[str, Path]`.
    It writes `flow_<name>.png` in `out_dir` (default: the case dir).
  - `picture_scales(case_dir, *, mesh) -> dict` (keys `"uz"`, `"spin"`, `"noise"` → `(lo, hi)`), used to
    get Stock's ranges so the design is drawn on them.

- [ ] **Step 1: Write the failing tests**

```python
from __future__ import annotations

import numpy as np
import pyvista as pv

from fansim.cfd.flow_report import FlowMetrics
from fansim.cfd.flow_report_viz import PICTURES, picture_scales, render_report_pictures


def _grid():
    g = pv.ImageData(dimensions=(23, 23, 13), spacing=(0.005, 0.005, 0.005),
                     origin=(-0.055, -0.055, -0.03)).cast_to_unstructured_grid()
    n = g.n_cells
    c = g.cell_centers().points
    r = np.hypot(c[:, 0], c[:, 1]) + 1e-9
    g.cell_data["U"] = np.column_stack([-c[:, 1] / r, c[:, 0] / r, np.full(n, 3.0)])
    g.cell_data["p"] = np.zeros(n)
    g.cell_data["k"] = np.full(n, 0.3)
    g.cell_data["omega"] = np.full(n, 1500.0)
    return g


def test_all_pictures_written(tmp_path):
    m = FlowMetrics(0.0, False, [1, 2, 3, 4, 5], 0.1, 0.0, 1.0, 60.0, 3.0)
    out = render_report_pictures(tmp_path, mesh=_grid(), out_dir=tmp_path,
                                 stock_bands=[1, 1, 1, 1, 1], metrics=m)
    assert set(out) == set(PICTURES)
    assert all(p.is_file() and p.stat().st_size > 1000 for p in out.values())


def test_scales_are_reused(tmp_path):
    sc = picture_scales(tmp_path, mesh=_grid())
    assert set(sc) == {"uz", "spin", "noise"}
    out = render_report_pictures(tmp_path, mesh=_grid(), out_dir=tmp_path, scales=sc,
                                 metrics=FlowMetrics(0, False, [1] * 5, 0, 0, 1, None, 3))
    assert "noise" not in out or out["noise"].is_file()
```

- [ ] **Step 2: Run them to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest -q tests/test_flow_report_viz.py`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `fansim/cfd/flow_report_viz.py`**

```python
"""Pictures for the flow report card: fan-face map, push bars, spin and noise side views (§24)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pyvista as pv

from fansim.cfd.flow_report import (
    DEAD_FRAC_OF_MEAN, FlowMetrics, PLANE_Z_FRAC, noise_density,
)
from fansim.cfd.flow_report_case import case_geometry
from fansim.cfd.midplane import _RENDER_LOCK, robust_clim, rotor_outline

PICTURES = ("face", "push", "spin", "noise")
WINDOW = (640, 480)


def _cells(mesh):
    g = mesh if "U" in mesh.cell_data else mesh.point_data_to_cell_data()
    return g


def _with_derived(mesh, case_dir):
    g = _cells(mesh).copy()
    c = np.asarray(g.cell_centers().points)
    u = np.asarray(g.cell_data["U"], float)
    r = np.hypot(c[:, 0], c[:, 1]) + 1e-12
    uth = (-u[:, 0] * c[:, 1] + u[:, 1] * c[:, 0]) / r
    g.cell_data["Uz"] = u[:, 2]
    g.cell_data["spin"] = np.abs(uth) / (np.linalg.norm(u, axis=1) + 1e-12)
    if "k" in g.cell_data and "omega" in g.cell_data:
        g.cell_data["noise"] = np.log10(noise_density(g.cell_data["k"], g.cell_data["omega"]) + 1e-30)
    return g


def picture_scales(case_dir, *, mesh) -> dict:
    g = _with_derived(mesh, case_dir)
    sc = {"uz": robust_clim(g.cell_data["Uz"], symmetric=True),
          "spin": (0.0, robust_clim(g.cell_data["spin"])[1])}
    sc["noise"] = robust_clim(g.cell_data["noise"]) if "noise" in g.cell_data else (0.0, 1.0)
    return sc


def _plotter():
    pl = pv.Plotter(off_screen=True, window_size=list(WINDOW))
    pl.background_color = "white"
    return pl


def _face(g, case_dir, hub_r, tip_r, z_fan, scales, metrics, path):
    z0 = z_fan + PLANE_Z_FRAC * tip_r
    slc = g.slice(normal=(0, 0, 1), origin=(0, 0, z0))
    pts = slc.cell_centers().points if slc.n_cells else np.zeros((0, 3))
    rr = np.hypot(pts[:, 0], pts[:, 1])
    slc = slc.extract_cells(np.flatnonzero((rr >= hub_r) & (rr <= tip_r))) if slc.n_cells else slc
    with _RENDER_LOCK:
        pl = _plotter()
        try:
            pl.add_mesh(slc.cell_data_to_point_data(), scalars="Uz", cmap="Blues",
                        clim=[0.0, scales["uz"][1]], show_scalar_bar=True,
                        scalar_bar_args={"title": "forward speed (m/s)"})
            uz = np.asarray(slc.cell_data["Uz"]) if slc.n_cells else np.zeros(0)
            back = slc.extract_cells(np.flatnonzero(uz < 0)) if uz.size else None
            if back is not None and back.n_cells:
                pl.add_mesh(back, color="red")
            mean = metrics.mean_uz_exit if metrics else (float(np.mean(uz)) if uz.size else 0.0)
            dead = slc.extract_cells(np.flatnonzero(np.abs(uz) < DEAD_FRAC_OF_MEAN * abs(mean))) if uz.size else None
            if dead is not None and dead.n_cells:
                pl.add_mesh(dead, color="gray")
            ol = rotor_outline(case_dir, (0, 0, 1), (0, 0, z_fan))
            if ol is not None:
                pl.add_mesh(ol, color="black", line_width=1)
            pl.view_xy()
            pl.camera.parallel_projection = True
            pl.reset_camera()
            pl.screenshot(str(path))
        finally:
            pl.close()
    return path


def _side(g, case_dir, field, cmap, clim, title, path, z_fan, tip_r, highlight_pct=None):
    slc = g.slice(normal=(0, 1, 0), origin=(0, 0, z_fan))
    with _RENDER_LOCK:
        pl = _plotter()
        try:
            pl.add_mesh(slc.cell_data_to_point_data(), scalars=field, cmap=cmap, clim=list(clim),
                        scalar_bar_args={"title": title})
            if highlight_pct is not None and slc.n_cells:
                v = np.asarray(slc.cell_data[field])
                hot = slc.extract_cells(np.flatnonzero(v >= np.percentile(v, highlight_pct)))
                if hot.n_cells:
                    pl.add_mesh(hot, color="orangered")
            ol = rotor_outline(case_dir, (0, 1, 0), (0, 0, z_fan))
            if ol is not None:
                pl.add_mesh(ol, color="black", line_width=2)
            pl.camera_position = [(0, -6 * tip_r, z_fan), (0, 0, z_fan), (1, 0, 0)]
            pl.camera.parallel_projection = True
            pl.reset_camera()
            pl.screenshot(str(path))
        finally:
            pl.close()
    return path


def _push(bands, stock_bands, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    names = ["hub", "inner", "middle", "outer", "tip"]
    x = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(6.4, 3.2), dpi=100)
    ax.bar(x - 0.2, bands, 0.4, label="this design", color="#1f77b4")
    if stock_bands is not None:
        ax.bar(x + 0.2, stock_bands, 0.4, label="Stock", color="#c8a400")
    ax.set_xticks(x, names)
    ax.set_ylabel("pressure added (Pa)")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def render_report_pictures(case_dir, *, mesh, scales=None, out_dir=None, stock_bands=None,
                           metrics: FlowMetrics | None = None) -> dict[str, Path]:
    case_dir = Path(case_dir)
    out_dir = Path(out_dir or case_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    hub_r, tip_r, z_fan = case_geometry(case_dir, mesh)
    g = _with_derived(mesh, case_dir)
    sc = scales or picture_scales(case_dir, mesh=mesh)
    out: dict[str, Path] = {}
    out["face"] = _face(g, case_dir, hub_r, tip_r, z_fan, sc, metrics, out_dir / "flow_face.png")
    bands = metrics.band_dp0_pa if metrics else [0.0] * 5
    out["push"] = _push(bands, stock_bands, out_dir / "flow_push.png")
    out["spin"] = _side(g, case_dir, "spin", "Purples", sc["spin"], "share of speed that is spin",
                        out_dir / "flow_spin.png", z_fan, tip_r)
    if "noise" in g.cell_data:
        out["noise"] = _side(g, case_dir, "noise", "Greys", sc["noise"], "turbulence noise (log, relative)",
                             out_dir / "flow_noise.png", z_fan, tip_r, highlight_pct=95.0)
    return out
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/Scripts/python.exe -m pytest -q tests/test_flow_report_viz.py`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add fansim/cfd/flow_report_viz.py tests/test_flow_report_viz.py
git commit -m "feat(flow-report): fan-face, push-bar, spin and noise pictures on shared Stock scales"
```

---

### Task 7: Validation on real cases (thresholds must survive before UI work)

**Files:**
- Create: `scripts/flow_report_checks.py`
- Create: `docs/validation/audits/2026-10-10-flow-report-checks.md`

**Interfaces:**
- Consumes: `load_or_compute_metrics` (Task 3), `judge` and `overall_line` (Task 2).

- [ ] **Step 1: Write the pre-registration first.** Create the audit doc with the four checks from the
  spec's Validation §2–4, exactly as written there:
  - self-consistency;
  - run-to-run: `stock/full` vs `stock_hubclip/full`;
  - 9610 gets ≥ 1 ⚠;
  - t9005 gets no ✕ and more better than worse.

  Leave a `## Result` heading empty. Commit it **before** running anything:

```bash
git add docs/validation/audits/2026-10-10-flow-report-checks.md
git commit -m "audit: pre-register flow-report verdict checks"
```

- [ ] **Step 2: Write `scripts/flow_report_checks.py`**

```python
"""Run the pre-registered flow-report checks on saved cases (no CFD; reconstructs if needed)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fansim.cfd.flow_report_case import load_or_compute_metrics  # noqa: E402
from fansim.cfd.flow_verdicts import judge, overall_line  # noqa: E402

RUNS = ROOT / "runs" / "screen_rank_audit"
REF = RUNS / "stock_hubclip" / "full"
CASES = {"stock_self": REF, "stock_prev": RUNS / "stock" / "full",
         "9610": RUNS / "r3_9610" / "full", "t9005": RUNS / "t9005" / "full",
         "9604": RUNS / "r3_9604" / "full"}


def main() -> int:
    ref = load_or_compute_metrics(REF)
    out = {"reference": ref.to_dict()}
    for name, case in CASES.items():
        m = load_or_compute_metrics(case)
        rows = judge(m, ref)
        out[name] = {"metrics": m.to_dict(),
                     "rows": [{"key": r.key, "status": r.status, "text": r.text, "bands": r.bands}
                              for r in rows],
                     "overall": overall_line(rows, compared=True)}
        print(f"{name:11s} " + " ".join(f"{r.key}={r.status}" for r in rows) + " | " + out[name]["overall"])
    (RUNS / "flow_report_checks.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Run it.** Expect a few minutes: each case is reconstructed once through
  `load_case_mesh` (Docker/WSL OpenFOAM must be available).

Run: `.venv/Scripts/python.exe scripts/flow_report_checks.py`

Also confirm the flow-axis assumption: the reference's `mean_uz_exit` must be **> 0**. If it is
negative, stop. The CFD frame's flow direction is not what the spec assumes, so the measurements need a
sign fix before anything else.

- [ ] **Step 4: Record the results** under `## Result` in the audit doc, as a row per check with PASS/FAIL
  and the printed line.
  - **If run-to-run fails:** widen the failing threshold to the smallest value that passes. Record the
    old value, the new value and the reason in the audit doc **and** in the spec's verdict table. Re-run
    the script and record the second result too. Never change a threshold without writing it down.
  - **If 9610 gets no ⚠:** do not tune for it. Record FAIL, then ask Kimball whether to ship the card
    with the limitation stated or stop.

- [ ] **Step 5: Point the cockpit at the reference**

Run: `.venv/Scripts/python.exe scripts/set_flow_reference.py runs/screen_rank_audit/stock_hubclip/full`
Expected: prints the reference path and its metrics.

- [ ] **Step 6: Commit**

```bash
git add scripts/flow_report_checks.py docs/validation/audits/2026-10-10-flow-report-checks.md docs/superpowers/specs/2026-10-10-flow-report-card-design.md
git commit -m "audit: flow-report verdict checks on Stock (self, run-to-run), 9610, t9005"
```

---

### Task 8: Simple/Expert switch + "How the air moves" card

**Files:**
- Create: `fansim/cockpit/fan_flow_report.py` (binder)
- Modify: `fansim/cockpit/fan_tab.py:48` (call `fan_flow_report.bind(session)` after `fan_viz.bind`)
- Modify: `fansim/cockpit/fan_trials.py:116` (call `session._schedule_flow_report(d)` right after
  `session._schedule_airflow(d)`)
- Modify: `fansim/cockpit/fan_core.py` `apply_state_defaults` (new state keys)
- Modify: `fansim/cockpit/app.py` (top-bar switch + localStorage persistence)
- Modify: `fansim/cockpit/fan_tab_ui.py:1341` (new card above the existing airflow card; the old card
  becomes expert-only)
- Test: `tests/test_fan_flow_report.py`

**Interfaces:**
- Consumes: `load_or_compute_metrics`, `test_settings`, `first_mismatch`, `samples_from_mesh` (Task 3);
  `judge`, `overall_line`, `ICONS` (Task 2); `render_report_pictures`, `picture_scales` (Task 6);
  `get_reference` (Task 3); `png_data_uri` (`fansim.cockpit.airflow_panel`);
  `load_case_mesh` (`fansim.cfd.cockpit_viz`); `Design` (`.stl_path`, `.extra`, `.has_model`,
  `.trial`).
- Produces:
  - `card_message(d) -> str | None`: a pure function giving the missing-data message, or None when a
    report can be built;
  - `build_report(case_dir, ref_dir) -> dict`: the state payload;
  - `session._schedule_flow_report(d)`.
  - **State keys:** `ui_mode` ("simple"), `flow_rows` (list of dicts: key, title, icon, status, text,
    img, stock_img), `flow_overall` (str), `flow_msg` (str), `flow_busy` (bool),
    `flow_numbers` (list of dicts: name, design, stock).

- [ ] **Step 1: Write the failing tests**

```python
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from fansim.cockpit import fan_flow_report as ffr


def _d(**kw):
    base = dict(stl_path="", extra={}, has_model=False, trial=1)
    base.update(kw)
    return SimpleNamespace(**base)


def test_message_never_assessed():
    assert ffr.card_message(_d()) == (
        "No flow simulation for this design yet. Run Assess to see how the air moves.")


def test_message_stale():
    d = _d(has_model=True, stl_path="x/impeller.stl",
           extra={"cfd_stale": True, "stale_reason": "old solver"})
    assert ffr.card_message(d) == "These results are out of date (old solver). Re-run Assess."


def test_message_ok_when_case_exists(tmp_path):
    (tmp_path / "500").mkdir()
    d = _d(has_model=True, stl_path=str(tmp_path / "impeller.stl"))
    assert ffr.card_message(d) is None


def test_report_without_reference(tmp_path, monkeypatch):
    from fansim.cfd.flow_report import FlowMetrics
    m = FlowMetrics(0.05, False, [1, 2, 3, 4, 5], 0.2, 0.05, 0.8, 60.0, 2.5)
    monkeypatch.setattr(ffr, "load_or_compute_metrics", lambda cd, **k: m)
    monkeypatch.setattr(ffr, "_pictures", lambda *a, **k: {})
    out = ffr.build_report(tmp_path, None)
    assert out["flow_overall"].startswith("No Stock comparison")
    assert "Stock hasn't been tested this way" in out["flow_msg"]
    assert len(out["flow_rows"]) == 5


def test_stale_token_not_applied():
    state = SimpleNamespace(selected_trial=2, flow_rows=["old"])
    applied = ffr._apply_if_current(state, token=1, payload={"flow_rows": ["new"]})
    assert applied is False and state.flow_rows == ["old"]
    assert ffr._apply_if_current(state, token=2, payload={"flow_rows": ["new"]}) is True
    assert state.flow_rows == ["new"]
```

- [ ] **Step 2: Run them to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest -q tests/test_fan_flow_report.py`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement `fansim/cockpit/fan_flow_report.py`**

```python
"""Fan binder: the "How the air moves" report card (roadmap §24)."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fansim.cfd.flow_report import FlowReportUnavailable
from fansim.cfd.flow_report_case import first_mismatch, load_or_compute_metrics, test_settings
from fansim.cfd.flow_verdicts import ICONS, judge, overall_line
from fansim.cockpit.airflow_panel import png_data_uri
from fansim.cockpit.flow_reference import get_reference
from fansim.cockpit.stock_cache import STOCK_CACHE_DIR

_log = logging.getLogger(__name__)

MSG_NONE = "No flow simulation for this design yet. Run Assess to see how the air moves."
MSG_BUILDING = "Working out how the air moves…"
NUMBER_LABELS = {"backflow_frac": "backflow share", "swirl_frac": "swirl energy share",
                 "dead_frac": "dead-air share", "tip_band_uz_ratio": "tip / mean forward speed",
                 "noise_swl_db": "Proudman SWL (dB, relative)", "mean_uz_exit": "mean exit Uz (m/s)"}


def card_message(d) -> str | None:
    if not getattr(d, "has_model", False) or not getattr(d, "stl_path", ""):
        return MSG_NONE
    extra = getattr(d, "extra", {}) or {}
    if extra.get("cfd_stale"):
        why = extra.get("stale_reason") or "older solver"
        return f"These results are out of date ({why}). Re-run Assess."
    case = Path(d.stl_path).parent
    if not case.is_dir():
        return MSG_NONE
    has_time = any(p.is_dir() and p.name[:1].isdigit() for p in case.iterdir())
    if not has_time and not (case / "processor0").is_dir():
        return MSG_NONE
    return None


def _pictures(case_dir, metrics, *, scales=None, stock_bands=None, out_dir=None):
    from fansim.cfd.cockpit_viz import load_case_mesh
    from fansim.cfd.flow_report_viz import render_report_pictures
    mesh = load_case_mesh(case_dir)
    if mesh is None:
        return {}
    return render_report_pictures(case_dir, mesh=mesh, scales=scales, out_dir=out_dir,
                                  stock_bands=stock_bands, metrics=metrics)


def _stock_pack(ref_dir):
    """Stock metrics, scales and pictures, computed once per reference (cached on disk)."""
    from fansim.cfd.cockpit_viz import load_case_mesh
    from fansim.cfd.flow_report_viz import picture_scales
    m = load_or_compute_metrics(ref_dir)
    mesh = load_case_mesh(ref_dir)
    scales = picture_scales(ref_dir, mesh=mesh) if mesh is not None else None
    out_dir = STOCK_CACHE_DIR / "flow_report"
    pics = _pictures(ref_dir, m, scales=scales, stock_bands=m.band_dp0_pa, out_dir=out_dir)
    return m, scales, pics


def build_report(case_dir, ref_dir) -> dict:
    case_dir = Path(case_dir)
    m = load_or_compute_metrics(case_dir)
    stock = scales = None
    stock_pics: dict = {}
    msg = ""
    if ref_dir is None:
        msg = "Stock hasn't been tested this way, so no comparison (no Stock reference set)."
    else:
        why = first_mismatch(test_settings(case_dir), test_settings(ref_dir))
        if why:
            msg = f"Stock hasn't been tested this way, so no comparison ({why})."
        else:
            stock, scales, stock_pics = _stock_pack(ref_dir)
    pics = _pictures(case_dir, m, scales=scales,
                     stock_bands=stock.band_dp0_pa if stock else None)
    rows = judge(m, stock)
    pic_for = {"direction": "face", "push": "push", "spin": "spin", "dead": "face", "noise": "noise"}
    out_rows = []
    for r in rows:
        if r.key == "noise" and r.status == "na" and m.noise_swl_db is None:
            continue  # spec: hide the noise row when the run has no turbulence data
        name = pic_for[r.key]
        out_rows.append({
            "key": r.key, "title": r.title, "icon": ICONS[r.status], "status": r.status,
            "text": r.text,
            "img": png_data_uri(pics[name]) if name in pics else "",
            "stock_img": png_data_uri(stock_pics[name]) if name in stock_pics else ""})
    numbers = [{"name": NUMBER_LABELS.get(k, k), "design": v,
                "stock": (stock.to_dict()[k] if stock else None)}
               for k, v in m.to_dict().items() if k in NUMBER_LABELS]
    if m.noise_swl_db is None:
        msg = (msg + " " if msg else "") + "No turbulence data in this run."
    return {"flow_rows": out_rows, "flow_overall": overall_line(rows, compared=stock is not None),
            "flow_msg": msg, "flow_numbers": numbers}


def _apply_if_current(state, *, token, payload: dict) -> bool:
    if getattr(state, "selected_trial", None) != token:
        return False
    for k, v in payload.items():
        setattr(state, k, v)
    return True


def bind(session) -> None:
    state = session.state
    import fansim.cockpit.fan_runtime as fan_runtime

    def _schedule_flow_report(d):
        msg = card_message(d)
        state.flow_rows, state.flow_overall, state.flow_numbers = [], "", []
        if msg is not None:
            state.flow_msg, state.flow_busy = msg, False
            return
        token = d.trial
        case = Path(d.stl_path).parent
        state.flow_msg, state.flow_busy = MSG_BUILDING, True

        async def task():
            try:
                loop = asyncio.get_running_loop()
                payload = await loop.run_in_executor(None, lambda: build_report(case, get_reference()))
            except FlowReportUnavailable as exc:
                payload = {"flow_msg": f"Couldn't read this run's flow ({exc}). Re-run Assess."}
            except Exception as exc:  # noqa: BLE001
                _log.warning("flow report failed for %s: %s: %s", case, type(exc).__name__, exc)
                payload = {"flow_msg": "The flow report couldn't be built for this design."}
            payload["flow_busy"] = False
            if _apply_if_current(state, token=token, payload=payload):
                state.flush()

        fan_runtime.asynchronous.create_task(task())

    session._schedule_flow_report = _schedule_flow_report
```

`fan_runtime.asynchronous.create_task` is the scheduling helper `fan_viz.py` already uses (line ~652).
Confirm the attribute name there before relying on it.

- [ ] **Step 4: Run the binder tests**

Run: `.venv/Scripts/python.exe -m pytest -q tests/test_fan_flow_report.py tests/test_fan_binders_wiring.py`
Expected: all PASS.

- [ ] **Step 5: Wire the binder, state defaults and switch**
  1. **`fan_tab.py`:** add `fan_flow_report` to the cockpit imports, and after `fan_viz.bind(session)`
     add `fan_flow_report.bind(session)`.
  2. **`fan_trials.py`:** directly after `session._schedule_airflow(d)` add
     `session._schedule_flow_report(d)`.
  3. **`fan_core.apply_state_defaults`:** add
     `state.ui_mode = "simple"; state.flow_rows = []; state.flow_overall = ""; state.flow_msg = ""; state.flow_busy = False; state.flow_numbers = []`.
  4. **`app.py`, inside `with SinglePageLayout(server) as layout:`:** add a toolbar switch after the
     title.

```python
        with layout.toolbar:
            v3.VSpacer()
            v3.VBtnToggle(
                v_model=("ui_mode",),
                mandatory=True, density="compact", variant="outlined", color="primary",
                classes="mr-2",
                children=[v3.VBtn("Simple", value="simple", size="small"),
                          v3.VBtn("Expert", value="expert", size="small")],
            )
            # Remember the choice per browser (spec: localStorage key fansim.ui_mode).
            html.Div(v_show=False, v_effect=(
                "(() => { try { const k='fansim.ui_mode';"
                " if (!window.__fsUiInit) { window.__fsUiInit = 1;"
                " const s = localStorage.getItem(k); if (s && s !== ui_mode) ui_mode = s; }"
                " localStorage.setItem(k, ui_mode); } catch (e) {} })()",))
```

     If `v_effect` is not available in this trame build, use `trame.widgets.client.Script`.
     Alternatively, use a `@state.change("ui_mode")` handler plus a `client.JSEval` that writes to
     localStorage, and read it once on `ctrl.on_client_connected`. Whichever you use, verify it in the
     browser in Task 9.

- [ ] **Step 6: Add the card in `fan_tab_ui.py`**
  1. Insert this immediately before the existing
     `with v3.VCard(classes="mb-2 pa-2", v_show="fan_subtab === 'results'"):` (the "Duct airflow" card,
     line ~1341):

```python
                    with v3.VCard(classes="mb-2 pa-3", v_show="fan_subtab === 'results'"):
                        html.Div("How the air moves", classes="text-subtitle-1 mb-1")
                        html.Div("{{ flow_overall }}", classes="text-body-2 font-weight-medium mb-2",
                                 v_show="flow_overall")
                        html.Div("{{ flow_msg }}", classes="text-caption text-medium-emphasis mb-2",
                                 v_show="flow_msg")
                        v3.VProgressLinear(indeterminate=True, height=3, color="primary",
                                           classes="mb-2", v_show="flow_busy")
                        with v3.VRow(v_for="row in flow_rows", key="row.key", dense=True,
                                     classes="mb-2 align-center"):
                            with v3.VCol(cols=12, md=4):
                                html.Div("{{ row.icon }} {{ row.title }}",
                                         classes="text-subtitle-2")
                                html.Div("{{ row.text }}", classes="text-body-2")
                            with v3.VCol(cols=6, md=4):
                                html.Div("This design", classes="text-caption")
                                html.Img(src=("row.img",), v_show="row.img",
                                         style="width:100%;cursor:zoom-in;border-radius:4px;",
                                         click="window.open(row.img)")
                            with v3.VCol(cols=6, md=4):
                                html.Div("Stock", classes="text-caption")
                                html.Img(src=("row.stock_img",), v_show="row.stock_img",
                                         style="width:100%;cursor:zoom-in;border-radius:4px;",
                                         click="window.open(row.stock_img)")
                        with html.Div(v_show="ui_mode === 'expert' && flow_numbers.length"):
                            html.Div("Technical detail, not reviewed for plain language",
                                     classes="text-caption text-disabled mt-2")
                            with html.Table(classes="text-caption"):
                                with html.Tr(v_for="n in flow_numbers", key="n.name"):
                                    html.Td("{{ n.name }}", classes="pr-4")
                                    html.Td("{{ n.design }}", classes="pr-4")
                                    html.Td("{{ n.stock }}")
```

  2. Change the existing "Duct airflow" card's `v_show` to
     `"fan_subtab === 'results' && ui_mode === 'expert'"`, and add the same grey
     "Technical detail, not reviewed for plain language" line under its title.
  3. `window.open(dataURI)` is blocked in some browsers. If the Task 9 check shows that, replace it with a
     `VDialog` bound to a `flow_zoom_src` state key: clicking sets `flow_zoom_src = row.img`, and the
     dialog shows `html.Img(src=("flow_zoom_src",))`.

- [ ] **Step 7: Run the cockpit test suite**

Run: `.venv/Scripts/python.exe -m pytest -q tests -k "cockpit or fan_ or airflow or flow_report"`
Expected: all PASS. If the cockpit smoke test enumerates state keys or canned executor results (as
`_readouts` needed earlier), add the new keys or results there.

- [ ] **Step 8: Commit**

```bash
git add fansim/cockpit/fan_flow_report.py fansim/cockpit/fan_tab.py fansim/cockpit/fan_trials.py fansim/cockpit/fan_core.py fansim/cockpit/app.py fansim/cockpit/fan_tab_ui.py tests/test_fan_flow_report.py
git commit -m "feat(cockpit): Simple/Expert switch + 'How the air moves' report card on Fan Results"
```

---

### Task 9: Browser verification, full suite, roadmap

**Files:**
- Modify: `docs/roadmap.md` (§24 items → DONE with evidence)
- Modify: `docs/superpowers/specs/2026-10-10-flow-report-card-design.md` (Status line)

- [ ] **Step 1: Full suite**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: 0 failed. Before committing, restore any tracked reference STLs the suite rewrote:
`git status` → `git checkout -- <path>`.

- [ ] **Step 2: Browser check** (`preview_start` with name `cockpit`; Fan → Results)
  1. Select Stock: every row ✓, "About the same as Stock on every check."
  2. Select 9604: rows render with both pictures; the overall line is sensible.
  3. Select a design with no Assess: "No flow simulation for this design yet…".
  4. Select a stale design (e.g. 9502): the "out of date (blade below hub)" message.
  5. Switch Expert: the numbers table and the old six-picture card appear, each with the grey note.
     Reload: the mode is remembered.
  6. Streamlines picture: the fan is visible and the flow goes left → right.
  7. Switch designs quickly (3 clicks within 2 s): the final card matches the final selection.
  8. `read_console_messages` with `onlyErrors`: none.
  9. Screenshot the Stock and 9604 cards for the user.

- [ ] **Step 3: Update the roadmap and spec status.** Mark the §24.1 items DONE with the evidence
  (audit doc, browser check), and set the spec status to "implemented".

- [ ] **Step 4: Commit and merge**

```bash
git add docs/roadmap.md docs/superpowers/specs/2026-10-10-flow-report-card-design.md
git commit -m "docs: flow report card shipped (§24.1)"
```

Then merge `flow-report-card` into master, re-run the full suite on master, and push only if Kimball asks.
