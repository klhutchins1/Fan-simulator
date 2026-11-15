"""R2.5a sweep runner: step-1 gate, pre-registered variant choice, cutoff."""

from __future__ import annotations

import importlib.util
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("vcs", ROOT / "scripts" / "volute_convergence_sweep.py")
vcs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vcs)


def test_gate_needs_both_oscillation_and_mass():
    assert vcs.gate({"oscillation_pct": 4.9, "mass_imbalance": 0.009}) == "PASS"
    assert vcs.gate({"oscillation_pct": 5.1, "mass_imbalance": 0.0}) == "INCONCLUSIVE"
    assert vcs.gate({"oscillation_pct": 1.0, "mass_imbalance": 0.02}) == "INCONCLUSIVE"
    assert vcs.gate({"oscillation_pct": 1.0, "mass_imbalance": -0.02}) == "INCONCLUSIVE"
    assert vcs.gate({"error": "solve failed"}) == "INCONCLUSIVE"


def _units(passing: dict[str, set[str]]) -> dict:
    units = {}
    for mesh in vcs.MESHES:
        for v in vcs.VARIANTS:
            for pt in vcs.POINTS:
                ok = v in passing.get(mesh, set())
                units[f"{mesh}_{v}_{pt}"] = {"gate": "PASS" if ok else "INCONCLUSIVE"}
    return units


def test_choose_least_damped_passing_variant_per_mesh():
    got = vcs.choose(_units({"coarse": {"V0", "V1", "V2"}, "fine": {"V2"}}))
    assert got == {"coarse": "V0", "fine": "V2"}


def test_choose_none_when_nothing_passes_and_incomplete_when_missing():
    units = _units({})
    assert vcs.choose(units) == {"coarse": "none", "fine": "none"}
    del units["fine_V2_load50"]
    assert vcs.choose(units)["fine"] == "incomplete"


def test_variant_v0_is_todays_defaults():
    assert vcs.VARIANTS["V0"] == {"p": 0.3, "U": 0.7, "turb": 0.7}


def test_cutoff_at_1530():
    assert not vcs.past_cutoff(datetime(2026, 11, 13, 15, 29))
    assert vcs.past_cutoff(datetime(2026, 11, 13, 15, 30))
    assert not vcs.past_cutoff(datetime(2026, 11, 14, 0, 30))


def test_no_image_writes_progress_and_exits_2(tmp_path, monkeypatch):
    monkeypatch.setattr(vcs, "image_available", lambda: False)
    assert vcs.main(["--out", str(tmp_path)]) == 2
    assert "no OpenFOAM image" in (tmp_path / "progress.json").read_text(encoding="utf-8")
