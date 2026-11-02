"""Every axial CFD entry point orients the rotor before build_case (Audit #1 fix)."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AXIAL_SCRIPTS = [
    "run_a12x25_validation.py", "run_fan_curve.py", "run_baseline.py", "validate_a12x25.py",
    "capture_convergence.py", "run_grid_convergence.py", "test_bistability.py", "validate_stl.py",
    "grid_convergence_stl.py", "evaluate_des_fwh.py", "run_fan01.py",
    "run_loaded_ladder.py",
    "validate_lt120.py",
]
# Non-axial or audit tooling that deliberately controls orientation itself.
EXEMPT = {
    "audit_direction_cfd.py", "evaluate_cror.py",
    # Audit #7: mixed-flow/volute/CROR, each oriented by its own production path, then spin
    # deliberately overridden to compare designed vs reversed rotation.
    "audit_archetype_direction_cfd.py",
}


def _calls(path: Path) -> set[str]:
    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call):
            f = node.func
            names.add(f.id if isinstance(f, ast.Name) else getattr(f, "attr", ""))
    return names


def test_listed_scripts_orient_before_build_case():
    for name in AXIAL_SCRIPTS:
        calls = _calls(ROOT / "scripts" / name)
        assert "build_case" in calls, name
        assert "prepare_axial_cfd" in calls, f"{name} calls build_case without prepare_axial_cfd"


def _prepare_calls(path: Path) -> list[ast.Call]:
    out = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call):
            f = node.func
            if (f.id if isinstance(f, ast.Name) else getattr(f, "attr", "")) == "prepare_axial_cfd":
                out.append(node)
    return out


def test_every_prepare_axial_cfd_call_states_its_direction_source():
    # Roadmap 19.2: builder vs external must be an explicit choice at every call site
    # (or an explicit orientation= AND spin= override).
    for name in AXIAL_SCRIPTS:
        calls = _prepare_calls(ROOT / "scripts" / name)
        assert calls, name
        for c in calls:
            kws = {k.arg for k in c.keywords}
            assert "source" in kws or {"orientation", "spin"} <= kws,                 f"{name}:{c.lineno} prepare_axial_cfd without source= (or orientation=+spin=)"


def test_no_unlisted_script_calls_build_case():
    for p in sorted((ROOT / "scripts").glob("*.py")):
        if p.name in AXIAL_SCRIPTS or p.name in EXEMPT:
            continue
        assert "build_case" not in _calls(p), f"{p.name}: add to AXIAL_SCRIPTS or EXEMPT"


def test_spin_smoke_removed():
    assert not (ROOT / "scripts" / "run_spin_ab_smoke.py").exists()
