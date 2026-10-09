"""Preview progress: the build worker reports stages; the bar only moves forward (§23.17, QA UI-4)."""

from __future__ import annotations

from pathlib import Path

from fansim.geometry.isolated import (
    build_stl_isolated,
    progress_caption,
    read_progress,
    write_progress,
)


def test_progress_roundtrip_and_caption(tmp_path):
    p = tmp_path / "x.progress.json"
    assert read_progress(p) is None
    assert progress_caption(None) == (2, "starting build process")      # determinate from the start
    pcts = []
    for k, label in enumerate(("reading design", "realising chords", "lofting", "writing"), 1):
        write_progress(p, k, 4, label)
        pct, text = progress_caption(read_progress(p))
        pcts.append(pct)
        assert text == f"stage {k}/4 · {label}"
    assert pcts == sorted(pcts) and pcts[0] > 0 and pcts[-1] < 100
    # never backwards, even if a stale/lower stage is read after a higher one
    assert progress_caption({"stage": 1, "of": 4, "label": "x"}, prev_pct=60)[0] == 60
    write_progress(None, 1, 4, "ignored")      # no path: no-op


def test_preview_worker_reports_every_stage(tmp_path):
    from fansim.optimize.search_space import stock_blade_flat

    out = tmp_path / "p.stl"
    prog = tmp_path / "p.progress.json"
    prog.write_text("stale")                       # a leftover file from an earlier run is cleared
    build_stl_isolated(stock_blade_flat(), {}, out, preview=True, progress_path=prog)
    assert out.exists()
    assert read_progress(prog) == {"stage": 4, "of": 4, "label": "writing mesh"}


def test_parent_records_the_kernel_load_stage_before_spawning(tmp_path, monkeypatch):
    """QA r3: the worker imports CadQuery before its own code runs, so stage 1 is the parent's."""
    import fansim.geometry.isolated as iso

    prog = tmp_path / "p.progress.json"
    seen = {}

    def fake_worker(module, job, **kw):
        seen["at_spawn"] = read_progress(prog)
        Path(job["out"]).write_text('solid x' + chr(10) + 'endsolid x' + chr(10))

    monkeypatch.setattr(iso, "run_worker_module", fake_worker)
    iso.build_stl_isolated({}, {}, tmp_path / "p.stl", preview=True, progress_path=prog)
    assert seen["at_spawn"] == {"stage": 1, "of": 4, "label": "loading CAD kernel"}
