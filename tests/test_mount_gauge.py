"""Mount gauge + A12x25 print-fit checks (no Docker)."""

from __future__ import annotations

from fansim.cockpit.placement import fit_envelope, nominal_fits_spec
from fansim.fan_spec import get_fan_spec
from fansim.manufacturability.mount_gauge import gauge_print_stl
from fansim.manufacturability.print_export import export_print_ready
from fansim.optimize.search_space import blade_from_flat, stock_blade_flat


def test_stock_after_fit_envelope_is_mountable_and_frame_fit():
    spec = get_fan_spec("a12x25")
    flat = fit_envelope(stock_blade_flat("a12x25"), spec).flat
    assert nominal_fits_spec(flat, spec)


def test_gauge_accepts_carved_stock_export(tmp_path):
    spec = get_fan_spec("a12x25")
    flat = fit_envelope(stock_blade_flat("a12x25"), spec).flat
    params = blade_from_flat(flat)
    stl = tmp_path / "print.stl"
    rep = export_print_ready(params, stl, mount=spec.motor_mount)
    assert rep.ok and rep.mount_fits is True
    g = gauge_print_stl(str(stl), spec)
    assert g.watertight
    assert g.frame_ok
    assert g.mount_ok, g.notes
    assert g.cavity_dia_mm is not None
    assert abs(g.cavity_dia_mm - spec.motor_mount.cavity_dia_mm) <= 0.6


def test_cfd_reference_stl_is_not_print_mount_ready():
    """CFD close-ref mesh must not be mistaken for a carved motor cup."""
    from pathlib import Path

    stl = Path("validation/reference/a12x25_impeller.stl")
    if not stl.is_file():
        return
    spec = get_fan_spec("a12x25")
    g = gauge_print_stl(str(stl), spec)
    assert not g.mount_ok
