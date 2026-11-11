"""Mount gauge + A12x25 print-fit checks (no Docker)."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict

from fansim.cockpit.placement import fit_envelope, nominal_fits_spec
from fansim.fan_spec import get_fan_spec
from fansim.manufacturability.mount_gauge import gauge_print_stl
from fansim.optimize.search_space import stock_blade_flat


def test_stock_after_fit_envelope_is_mountable_and_frame_fit():
    spec = get_fan_spec("a12x25")
    flat = fit_envelope(stock_blade_flat("a12x25"), spec).flat
    assert nominal_fits_spec(flat, spec)


def test_gauge_accepts_carved_stock_export(tmp_path):
    spec = get_fan_spec("a12x25")
    flat = fit_envelope(stock_blade_flat("a12x25"), spec).flat
    stl = tmp_path / "print.stl"
    result = tmp_path / "export.json"
    job = tmp_path / "job.json"
    # 23.55: the cup fuse peaks ~7.6 GB and retains it. Do it in a child so this
    # pytest process is not the suite's 8 GB peak (QA-15 S5). DEVNULL stdout: a
    # captured pipe can fill during the boolean. No STEP (the gauge only needs STL).
    job.write_text(
        json.dumps(
            {
                "flat": flat,
                "out": str(stl),
                "mount": asdict(spec.motor_mount),
                "result": str(result),
                "also_step": False,
            }
        ),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [sys.executable, "-m", "fansim.manufacturability._print_ready_worker", str(job)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        timeout=900,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr[-2000:] if proc.stderr else "worker failed"
    assert stl.is_file() and result.is_file()
    rep = json.loads(result.read_text(encoding="utf-8"))
    assert rep["ok"] and rep["mount_fits"] is True
    from fansim.manufacturability.mount_gauge import write_print_fit_sidecars

    g = write_print_fit_sidecars(
        stl, spec, report_mount_fits=rep["mount_fits"], report_mount_msg=rep["mount_msg"] or ""
    )
    assert g.watertight
    assert g.frame_ok
    assert g.mount_ok, g.notes
    assert stl.with_name("print_mount_checklist.md").is_file()
    assert stl.with_name("print_print_fit.json").is_file()


def test_inlet_glyph_ring_does_not_inflate_rear_bore():
    """Engraved print-id strokes sit on +Z at r 11.5–16.5 mm. The bore sampler used to take
    the 90th percentile of everything inside 0.75×cup, so a Stock hub with glyphs read ~26 mm
    instead of the 20 mm rear bore (P1: gauge must match the unmarked cup)."""
    import numpy as np
    import trimesh

    from fansim.manufacturability.mount_gauge import _estimate_cavity

    th = np.linspace(0.0, 2.0 * np.pi, 72, endpoint=False)
    cav_r, bore_r, mark_r = 18.625, 10.0, 13.1
    z_rear, z_floor, z_inlet = 0.0, 13.0, 16.5
    chunks = []
    for r, z, n in (
        (cav_r, z_rear, 72),
        (bore_r, z_rear, 72),
        (cav_r, z_floor, 72),
        (bore_r, z_floor, 72),
        (bore_r, z_inlet, 72),
        (mark_r, z_inlet, 400),  # dense glyph tessellation, like a fused stroke cut
    ):
        t = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
        chunks.append(np.column_stack([r * np.cos(t), r * np.sin(t), np.full(n, z)]))
    v = np.vstack(chunks)
    mesh = trimesh.Trimesh(vertices=v, faces=[[0, 1, 2]], process=False)
    _cav, _dep, bore_dia = _estimate_cavity(
        mesh, expected_cavity_r=cav_r, expected_cavity_depth=13.0, expected_bore_r=bore_r,
    )
    assert bore_dia is not None
    assert abs(bore_dia - 20.0) <= 1.25, f"rear bore read {bore_dia:.2f} mm (mark ring is 26.2)"


def test_cfd_reference_stl_is_not_print_mount_ready():
    """CFD close-ref mesh must not be mistaken for a carved motor cup."""
    from pathlib import Path

    stl = Path("validation/reference/a12x25_impeller.stl")
    if not stl.is_file():
        return
    spec = get_fan_spec("a12x25")
    g = gauge_print_stl(str(stl), spec)
    assert not g.mount_ok
