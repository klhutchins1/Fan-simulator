"""RV-3 Module 8 (cockpit) and live-Chrome UX consistency regression tests."""

from __future__ import annotations

import logging
from pathlib import Path
from types import SimpleNamespace

import pytest

from fansim.cockpit.experimental import EXPERIMENTAL_LABEL
from fansim.cockpit.placement import _blade_z_bounds
from fansim.fan_spec import get_fan_spec
from fansim.geometry.blade import BladeParams, RadialStation, _section_points_3d, _thick_scale_kw

REPO = Path(__file__).resolve().parent.parent


def test_placement_blade_z_bounds_forwards_plate_zero_roundness_and_faces(monkeypatch):
    """C1: _blade_z_bounds must not turn le_thick_scale=0.0 into 1.0 and must forward te_face/le_face."""
    seen: list[dict] = []
    real_fn = _section_points_3d

    def spy(*args, **kwargs):
        seen.append(dict(kwargs))
        return real_fn(*args, **kwargs)

    monkeypatch.setattr("fansim.geometry.blade._section_points_3d", spy)

    params = BladeParams(
        section_family="plate",
        section_wrap="cylinder",
        le_thick_scale=0.0,
        te_thick_scale=0.0,
        n_span=4,
        n_chord=16,
        stations=[
            RadialStation(r_frac=0.0, chord=20.0, stagger_deg=35.0, thickness=0.06, te_face=0.25, le_face=0.35),
            RadialStation(r_frac=1.0, chord=20.0, stagger_deg=35.0, thickness=0.06, te_face=0.25, le_face=0.35),
        ],
    )
    lo, hi = _blade_z_bounds(params)
    assert hi > lo
    assert len(seen) >= 4  # n_span=4 stations (+ 1 root call inside _hub_axial_range)
    expected_kw = _thick_scale_kw(params)
    for kw in seen:
        assert kw["le_thick_scale"] == pytest.approx(0.0)
        assert kw["te_thick_scale"] == pytest.approx(0.0)
        assert kw["te_face"] == pytest.approx(0.25)
        assert kw["le_face"] == pytest.approx(0.35)
        assert kw["wrap"] == expected_kw["wrap"]
        assert kw["section_family"] == "plate"


def test_spec_status_warns_and_logs_on_unreadable_stl(tmp_path, caplog):
    """C2: spec_status must log and surface a warning when STL inspection fails (never silently pass)."""
    from fansim.cockpit import fan_assess

    class _DummyState:
        def __init__(self) -> None:
            self.sweep_items: list[str] = []

        def change(self, *_args, **_kwargs):
            return lambda fn: fn

    session = SimpleNamespace(
        state=_DummyState(),
        run_dir=tmp_path,
        assess_dir=tmp_path,
        user_designs=[],
        by_trial={},
        next_id=[9000],
        designs_lock=None,
        assess_proc={},
        sel_sig=[""],
        active_spec=lambda: get_fan_spec("a12x25"),
        _depth_driver_msg=lambda _flat: "",
    )
    fan_assess.bind(session)

    missing_stl = tmp_path / "does_not_exist.stl"
    with caplog.at_level(logging.WARNING, logger="fansim.cockpit.fan_assess"):
        ok, msg = session.spec_status(missing_stl, BladeParams())

    assert ok is True
    assert "⚠" in msg
    assert "Could not verify build spec" in msg
    assert any("spec_status STL read" in r.message for r in caplog.records)


def test_cancel_viz_button_hidden_when_airflow_idle():
    """C3: ⏹ Cancel viz must stay hidden unless airflow_busy is true (completing #101)."""
    src = (REPO / "fansim/cockpit/fan_tab_ui.py").read_text(encoding="utf-8")
    idx = src.index('"⏹ Cancel viz"')
    snippet = src[idx : idx + 320]
    assert 'v_show="airflow_busy"' in snippet


def test_mixed_design_card_shows_experimental_label_like_volute_and_cror():
    """C4: Mixed Design card must display EXPERIMENTAL_LABEL consistently with Volute and CROR."""
    for rel, anchor in (
        ("fansim/cockpit/mixed_tab.py", "def _render_mf_design("),
        ("fansim/cockpit/volute_tab.py", "def _render_volute_design("),
        ("fansim/cockpit/cror_tab.py", "def _render_cror_design("),
    ):
        src = (REPO / rel).read_text(encoding="utf-8")
        idx = src.index(anchor)
        card_head = src[idx : idx + 650]
        assert "EXPERIMENTAL_LABEL" in card_head, f"{rel} missing EXPERIMENTAL_LABEL in top Design card"
    assert EXPERIMENTAL_LABEL.startswith("Experimental:")


def test_impeller_z_extent_and_fit_envelope_never_run_cad_on_shrouded_fan(monkeypatch):
    """Shrouded cylindrical-tip fans must stay purely analytic in impeller_z_extent/fit_envelope.

    Regression for the 45-minute CI hang / cockpit UI freeze where ``impeller_z_extent``
    called ``shroud_axial_range`` -> ``tip_section_points`` -> ``prepare_loft_chords``,
    building hundreds of OCCT blade lofts inside ``fit_envelope`` iterations.
    """
    import pytest

    import fansim.geometry.blade as blade_mod
    import fansim.geometry.chord_realisation as chord_mod
    from fansim.cockpit.placement import fit_envelope, impeller_z_extent
    from fansim.geometry.blade import Features
    from fansim.optimize.search_space import blade_from_flat, stock_blade_flat

    def _forbid_cad(*_a, **_k):
        pytest.fail("impeller_z_extent / fit_envelope must never invoke OCCT CAD lofts")

    monkeypatch.setattr(chord_mod, "prepare_loft_chords", _forbid_cad)
    monkeypatch.setattr(blade_mod, "build_blade_solid", _forbid_cad)

    flat = stock_blade_flat("a12x25")
    flat["shroud_thick_mm"] = 1.5
    flat["section_wrap"] = "cylinder"
    p = blade_from_flat(flat, Features(serration_amp=1.2, serration_waves=8))
    assert p.cylindrical_tip is True

    z = impeller_z_extent(p)
    assert z > 0.0

    res = fit_envelope(flat, get_fan_spec("a12x25"), Features(serration_amp=1.2, serration_waves=8))
    assert isinstance(res.flat, dict)
    assert isinstance(res.fit_status, str)


def test_cockpit_template_serves_control_images_statically_instead_of_inlining_pngs():
    """Control preview PNGs must be served over HTTP (lazy-loaded), not inlined into the Vue template."""
    from fansim.cockpit.fan_copy import CONTROL_IMAGES_URL_PREFIX, control_image_url
    from fansim.cockpit.fan_widgets import _tooltip_img_src

    assert CONTROL_IMAGES_URL_PREFIX == "fansim_control_images"
    url = control_image_url("e_n_blades")
    assert url == "/fansim_control_images/e_n_blades.png"
    assert _tooltip_img_src("e_n_blades", "data:image/png;base64,AAA") == url
    # Fallback to inline SVG diagram URI when no rendered PNG exists for the control.
    svg_uri = "data:image/svg+xml;utf8,<svg/>"
    assert _tooltip_img_src("__no_such_control__", svg_uri) == svg_uri

    app_src = (REPO / "fansim/cockpit/app.py").read_text(encoding="utf-8")
    assert "CONTROL_IMAGES_URL_PREFIX" in app_src
    widgets_src = (REPO / "fansim/cockpit/fan_widgets.py").read_text(encoding="utf-8")
    assert 'loading="lazy"' in widgets_src


def test_lazy_tabs_use_isolated_server_templates_instead_of_flushing_main_layout():
    """Lazy tabs must flush into isolated ServerTemplate slots so VTK views in other tabs don't remount."""
    import re

    app_src = (REPO / "fansim/cockpit/app.py").read_text(encoding="utf-8")
    assert "ServerTemplate" in app_src
    assert "DivLayout" in app_src
    assert "tab_layout.flush_content()" in app_src
    assert re.search(r"(?<!\w)layout\.flush_content\(", app_src) is None

