# Tests & pyproject snippets (from audit chat)

## pytest / optional deps (snippet recovered)

From `pyproject.toml` as quoted in chat:

```toml
[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff>=0.5"]
# no pytest-cov in that snapshot

[tool.pytest.ini_options]
testpaths = ["tests"]
# note: not scripts/test_*.py
```

Other remembered extras:
- `uv run --extra optim` for Optuna campaigns
- Dependencies cited in physics review: numpy, scipy, CadQuery, trimesh, PyVista, Optuna, Trame, …

## Test files named in chats

### Geometry / manufacturability
- `test_geometry.py` — NACA sections, watertight impeller, envelope fit, config YAML, shroud builds (`@pytest.mark.slow`)
- `test_rounded_plate.py`, `test_le_te_thick.py`, `test_span_interp.py` — plate sections, LE/TE thickness, linear vs PCHIP loft
- `test_features.py` — tubercles/dimples + slow watertight featured impeller

### Acoustics / FW-H / Proudman (synthetic)
- `test_des_fwh.py`, `test_fwh.py`, `test_permeable_*.py`, `test_farfield.py`
- `test_acoustics.py`, `test_loading.py`

### Viz / CFD helpers
- `test_glyphs.py`, `test_midplane.py` (often `pytest.importorskip("pyvista")`)

### Optimize / geometry features
- `test_optimize.py`, `test_shroud.py`, `test_stator.py`
- “many others” — CLI help strings tested against `scripts/*.py`

## Known red suite issue (at time of audit)

New default `cylindrical_tip=True` changed the envelope contract; old geometry/CFD/placement tests were not updated. Four cylindrical-tip related failures were “immediate” todos.

## Coverage posture

Audit said: strong on geometry, BEM/BEMT, acoustics math, optimizer plumbing; weak on real OpenFOAM end-to-end (Docker-gated).
