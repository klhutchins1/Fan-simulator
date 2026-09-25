# Physics Audit Foundation + Audit #1 (flow direction) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the change-driven audit machinery (registry, fingerprints, ledger, status) and the
single air-properties source. Then run Audit #1, which proves which way the axial fan is designed to
spin and pump, using geometry alone and a bias-free CFD matrix.

**Architecture:** A new `fansim/audit/` package holds:
- a YAML registry of audited "units",
- AST fingerprinting of each unit's target code,
- a JSON ledger of passed fingerprints,
- a pure status classifier behind `scripts/audit_status.py`,
- a mesh-only direction proof (`direction.py`) with known-answer synthetic geometry (`synthetic.py`),
- a pure CFD-matrix verdict function (`direction_verdict.py`) driven by `scripts/audit_direction_cfd.py`.

Audit #1 ends with a dated report. Fixing the direction bug is a **separate follow-up plan**, written
after the verdict.

**Tech Stack:** Python 3.11+, pytest, numpy, trimesh, networkx, pyyaml, OpenFOAM (Docker image
`opencfd/openfoam-default:2406`) via `fansim.cfd.runner`.

## Global Constraints

- **FREEZE:** do not change `TestRig.spin`, `flow_sign`, `u_axial`, inlet/outlet placement, glyph
  direction, `normalize_metrics_sign`, blade mirror/lean/stagger signs, or `_hub_axial_range`
  (roadmap banner, §19.1). This plan only *reads* and *measures* them.
- Do not touch `tests/test_cfd.py::rig.spin == -1` or `tests/test_glyphs.py`. They are replaced after
  the verdict, in the follow-up plan.
- Branch: `master`, no worktree, no PRs (user standing preference). Commit after every task.
- Commit trailer: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Tests run with `uv run pytest ...` from the repo root `T:\Projects\Fan Simulator`.
- Before committing, check `git status` for rewritten tracked reference STLs/goldens (memory:
  test-churns-reference-stl). Restore them with `git checkout -- <file>` if pytest rewrote them.
- Ledger updates happen **only on PASS**. INCONCLUSIVE and SKIPPED never count as proof.
- Air constants: fans/CFD use ρ = 1.2 (AMCA standard air); props/turbines use ρ = 1.225 (ISA). This
  plan does **not** consolidate the existing copies; it only stops new ones.

---

### Task 0: Spec amendment (BC asymmetry + efficiency proxy)

While planning, a flaw surfaced in the spec's CFD proof. The free-air BCs are **asymmetric**:
- inlet (−Z): `totalPressure p0=0`,
- outlet (+Z): static `fixedValue 0` (`fansim/cfd/templates.py`, `FIELD_P_PDRIVEN`).

Flow that runs backwards through the duct (toward −Z) therefore sees easier boundary conditions than
forward flow, so the 2026-09-24 spin A/B (+42.4 vs −70.5 CFM) is **not** evidence either way.

The spec's "flip the case end-for-end and get the same |CFM|" check is also invalid under these BCs.
It is replaced by a 2×2 matrix: {as-built, flipped 180° about X} × {spin −1, +1}. Each rotation sense
is judged only in the orientation where it pumps +Z through the proper BCs. At free air the static
rise is about 0, so η is replaced by delivered CFM per shaft watt.

**Files:**
- Modify: `docs/superpowers/specs/2026-09-24-physics-audit-design.md` (the "Proofs required" list under Audit #1)

- [ ] **Step 1: Replace proof item 3 in the spec**

Replace the whole bullet that starts `3. **CFD both ways.**` with:

```markdown
3. **CFD matrix (bias-free).** The free-air BCs are asymmetric (total-pressure inlet at −Z, static
   outlet at +Z), so reversed through-flow gets easier BCs. The 2026-09-24 spin A/B is therefore not
   evidence. Run {as-built, flipped 180° about X} × {spin −1, +1} at free air on converged solves.
   A flip about X maps body rotation ω → −ω, so each physical rotation sense appears twice: once
   pumping +Z through the proper BCs ("proper run") and once pumping −Z ("improper run").
   - The designed sense must win on its proper run: at least 20% more CFM **and** higher CFM per shaft
     watt (static rise is ~0 at free air, so η is not usable).
   - It must match the geometric proof.
   - The report records improper − proper |CFM| per sense as the measured BC bias.
```

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/specs/2026-09-24-physics-audit-design.md
git commit -m "docs(audit): replace axis-invariance proof with bias-free 2x2 CFD matrix

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 1: Audit registry loader

**Files:**
- Create: `fansim/audit/__init__.py`
- Create: `fansim/audit/registry.py`
- Create: `fansim/audit/registry.yaml`
- Test: `tests/audit/test_audit_registry.py`

**Interfaces:**
- Produces:
  - `Unit(id: str, targets: tuple[str, ...], claim: str, source: dict, regime: dict, checks: tuple[str, ...], depends_on: tuple[str, ...], libs: tuple[str, ...])` (frozen dataclass)
  - `Registry(units: dict[str, Unit], exempt: tuple[str, ...])`
  - `load_registry(path: Path = REGISTRY_PATH) -> Registry`, which raises `RegistryError` on invalid content
  - `REGISTRY_PATH: Path`
  - Target string format: `"pkg.module"` (whole module) or `"pkg.module:Name"` / `"pkg.module:Class.method"`

- [ ] **Step 1: Write the failing test**

`tests/audit/test_audit_registry.py`:

```python
"""Audit registry: schema validation and the shipped registry loads."""

from __future__ import annotations

from pathlib import Path

import pytest

from fansim.audit.registry import REGISTRY_PATH, RegistryError, load_registry


def _write(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "registry.yaml"
    p.write_text(body, encoding="utf-8")
    return p


GOOD = """
exempt: ["fansim.cfd.glyphs:*"]
units:
  - id: a.base
    targets: ["fansim.cfd.metrics:parse_fan_metrics"]
    claim: "x"
    source: {kind: standard, ref: "unit conversion"}
  - id: a.child
    targets: ["fansim.cfd.metrics"]
    claim: "y"
    source: {kind: derivation, ref: "hand"}
    depends_on: [a.base]
    libs: [numpy]
"""


def test_loads_valid_registry(tmp_path):
    reg = load_registry(_write(tmp_path, GOOD))
    assert set(reg.units) == {"a.base", "a.child"}
    assert reg.units["a.child"].depends_on == ("a.base",)
    assert reg.units["a.child"].libs == ("numpy",)
    assert reg.units["a.base"].checks == ()
    assert reg.exempt == ("fansim.cfd.glyphs:*",)


@pytest.mark.parametrize("body, msg", [
    ("units:\n  - {id: a, claim: c, source: {kind: paper, ref: r}}\n", "targets"),
    ("units:\n  - {id: a, targets: [m], claim: c, source: {kind: vibes, ref: r}}\n", "kind"),
    ("units:\n  - {id: a, targets: [m], claim: c, source: {kind: paper, ref: r}}\n"
     "  - {id: a, targets: [m], claim: c, source: {kind: paper, ref: r}}\n", "duplicate"),
    ("units:\n  - {id: a, targets: [m], claim: c, source: {kind: paper, ref: r}, depends_on: [zz]}\n",
     "unknown"),
    ("units:\n  - {id: a, targets: [m], claim: c, source: {kind: paper, ref: r}, depends_on: [b]}\n"
     "  - {id: b, targets: [m], claim: c, source: {kind: paper, ref: r}, depends_on: [a]}\n", "cycle"),
    ("units:\n  - {id: a, targets: ['bad target!'], claim: c, source: {kind: paper, ref: r}}\n",
     "target"),
])
def test_rejects_invalid(tmp_path, body, msg):
    with pytest.raises(RegistryError, match=msg):
        load_registry(_write(tmp_path, body))


def test_shipped_registry_loads():
    reg = load_registry(REGISTRY_PATH)
    assert "cfd.flow_direction_convention" in reg.units
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/audit/test_audit_registry.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'fansim.audit'`

- [ ] **Step 3: Write the implementation**

`fansim/audit/__init__.py`:

```python
"""Physics & math audit machinery (roadmap §19, spec 2026-09-24-physics-audit-design)."""
```

`fansim/audit/registry.py`:

```python
"""Load and validate the audit unit registry (``registry.yaml``).

A *unit* is one audited piece of physics: the code that implements it (``targets``), what it
claims, where the claim comes from, and which checks prove it. See the design spec
``docs/superpowers/specs/2026-09-24-physics-audit-design.md``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

REGISTRY_PATH = Path(__file__).with_name("registry.yaml")
SOURCE_KINDS = frozenset({"paper", "datasheet", "standard", "derivation"})
_TARGET_RE = re.compile(r"^[A-Za-z_][\w.]*(:[A-Za-z_][\w.]*)?$")


class RegistryError(ValueError):
    """The registry file is malformed."""


@dataclass(frozen=True)
class Unit:
    id: str
    targets: tuple[str, ...]
    claim: str
    source: dict
    regime: dict
    checks: tuple[str, ...]
    depends_on: tuple[str, ...]
    libs: tuple[str, ...]


@dataclass(frozen=True)
class Registry:
    units: dict[str, Unit]
    exempt: tuple[str, ...]


def _unit(raw: dict) -> Unit:
    uid = raw.get("id")
    if not uid:
        raise RegistryError(f"unit without id: {raw!r}")
    targets = tuple(raw.get("targets") or ())
    if not targets:
        raise RegistryError(f"{uid}: needs at least one entry in targets")
    for t in targets:
        if not _TARGET_RE.match(str(t)):
            raise RegistryError(f"{uid}: bad target {t!r} (want 'pkg.mod' or 'pkg.mod:Name')")
    source = dict(raw.get("source") or {})
    if source.get("kind") not in SOURCE_KINDS:
        raise RegistryError(f"{uid}: source kind must be one of {sorted(SOURCE_KINDS)}")
    return Unit(
        id=str(uid),
        targets=tuple(str(t) for t in targets),
        claim=str(raw.get("claim", "")),
        source=source,
        regime=dict(raw.get("regime") or {}),
        checks=tuple(str(c) for c in raw.get("checks") or ()),
        depends_on=tuple(str(d) for d in raw.get("depends_on") or ()),
        libs=tuple(str(x) for x in raw.get("libs") or ()),
    )


def _check_graph(units: dict[str, Unit]) -> None:
    for u in units.values():
        for d in u.depends_on:
            if d not in units:
                raise RegistryError(f"{u.id}: depends_on unknown unit {d!r}")
    state: dict[str, int] = {}  # 1 = visiting, 2 = done

    def visit(uid: str) -> None:
        if state.get(uid) == 1:
            raise RegistryError(f"dependency cycle through {uid!r}")
        if state.get(uid) == 2:
            return
        state[uid] = 1
        for d in units[uid].depends_on:
            visit(d)
        state[uid] = 2

    for uid in units:
        visit(uid)


def load_registry(path: Path = REGISTRY_PATH) -> Registry:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    units: dict[str, Unit] = {}
    for raw in data.get("units") or ():
        u = _unit(raw)
        if u.id in units:
            raise RegistryError(f"duplicate unit id {u.id!r}")
        units[u.id] = u
    _check_graph(units)
    return Registry(units=units, exempt=tuple(str(e) for e in data.get("exempt") or ()))
```

`fansim/audit/registry.yaml` holds the Audit #1 units. Later audits append to it.

```yaml
# Audited physics units. Schema + states: docs/superpowers/specs/2026-09-24-physics-audit-design.md
# targets: "pkg.module" (whole module) or "pkg.module:Name[.method]". Fingerprints ignore comments,
# docstrings and formatting, so only logic changes invalidate a unit.
exempt: []
units:
  - id: physics.air_properties
    targets: ["fansim.physics.air"]
    claim: "Room-temperature sea-level air: rho 1.2 (AMCA) / 1.225 (ISA), nu 1.5e-5, mu 1.81e-5, c0 343"
    source: {kind: standard, ref: "AMCA 210 standard air; ISA sea level; ideal gas + Sutherland"}
    regime: {fluid: air, T_K: [288, 298], p_Pa: 101325}
    checks: [tests/audit/test_air_properties.py]

  - id: audit.direction_geometry
    targets: ["fansim.audit.direction"]
    claim: "Designed rotation = the way the concave (pressure) face points; air leaves along that face normal"
    source: {kind: derivation, ref: "velocity triangles, Dixon & Hall, Fluid Mechanics and Thermodynamics of Turbomachinery, ch. 1/5"}
    checks: [tests/audit/test_direction_geometry.py]
    libs: [trimesh, networkx]

  - id: cfd.flow_direction_convention
    targets:
      - "fansim.cfd.domain:TestRig"
      - "fansim.cfd.openfoam_case:build_case"
      - "fansim.cfd.templates:MRF_PROPERTIES"
      - "fansim.cfd.templates:BLOCK_MESH"
      - "fansim.cfd.templates:FIELD_U_PDRIVEN"
      - "fansim.cfd.templates:FIELD_P_PDRIVEN"
    claim: "Duct inlet -Z / outlet +Z; MRF omega = spin*|omega| about +Z (right-hand); the solved fan pumps +Z in its designed rotation"
    source: {kind: derivation, ref: "Audit #1 (geometry proof + CFD matrix)"}
    checks: [tests/audit/test_cfd_direction_contract.py, "ref:a12x25_direction_matrix"]
    depends_on: [audit.direction_geometry]
    libs: [openfoam]

  - id: cfd.cfm_from_outlet_flow
    targets: ["fansim.cfd.metrics:parse_fan_metrics", "fansim.cfd.metrics:CFM_PER_M3S", "fansim.cfd.templates:CONTROL_DICT"]
    claim: "CFM = sum(phi) over the +Z outlet patch * 2118.882; positive = delivery toward +Z; never abs()"
    source: {kind: standard, ref: "unit conversion; AMCA 210 flow sign"}
    checks: [tests/audit/test_cfd_direction_contract.py, tests/test_math_consistency.py]
    depends_on: [cfd.flow_direction_convention, physics.air_properties]

  - id: optimize.reject_dead_designs
    targets: ["fansim.optimize.system_curve:score_operating_point"]
    claim: "Zero/negative free delivery is rejected (SystemCurveError), never scored"
    source: {kind: derivation, ref: "a fan that does not deliver has no operating point"}
    checks: [tests/audit/test_dead_design_guard.py]

  - id: propeller.thrust_sign
    targets: ["fansim.propeller.calibrate:normalize_metrics_sign", "fansim.propeller.calibrate:preferred_spin_for_positive_thrust"]
    claim: "Prop thrust sign comes from the geometry-derived rotation, not from flipping spin until thrust > 0"
    source: {kind: derivation, ref: "Audit #1"}
    checks: []
    depends_on: [cfd.flow_direction_convention]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/audit/test_audit_registry.py -v`
Expected: all PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add fansim/audit/__init__.py fansim/audit/registry.py fansim/audit/registry.yaml tests/audit/test_audit_registry.py
git commit -m "feat(audit): unit registry schema + Audit #1 units

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: AST fingerprints

**Files:**
- Create: `fansim/audit/fingerprint.py`
- Test: `tests/audit/test_audit_fingerprint.py`

**Interfaces:**
- Consumes: `Unit` from Task 1.
- Produces:
  - `ROOT: Path` (repo root)
  - `module_path(module: str, root: Path = ROOT) -> Path`
  - `normalized_source(target: str, root: Path = ROOT) -> str`, which raises `FingerprintError` if the target is not found
  - `fingerprint_target(target: str, root: Path = ROOT) -> str` (16 hex chars)
  - `lib_versions(libs: tuple[str, ...]) -> dict[str, str]`, where the lib `"openfoam"` maps to `fansim.cfd.runner.DEFAULT_IMAGE`
  - `fingerprint_unit(unit: Unit, root: Path = ROOT) -> str` (16 hex chars)

- [ ] **Step 1: Write the failing test**

`tests/audit/test_audit_fingerprint.py`:

```python
"""Fingerprints change on logic edits only (not comments / docstrings / formatting)."""

from __future__ import annotations

from pathlib import Path

import pytest

from fansim.audit.fingerprint import (
    FingerprintError,
    fingerprint_target,
    fingerprint_unit,
    lib_versions,
    normalized_source,
)
from fansim.audit.registry import Unit

BASE = '''"""Module doc."""
RHO = 1.2

def f(x):
    """Doc."""
    # comment
    return x * RHO

class C:
    def m(self):
        return 1
'''


def _pkg(tmp_path: Path, body: str) -> Path:
    (tmp_path / "pkgx").mkdir(exist_ok=True)
    (tmp_path / "pkgx" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "pkgx" / "mod.py").write_text(body, encoding="utf-8")
    return tmp_path


def test_comment_docstring_and_format_changes_are_ignored(tmp_path):
    root = _pkg(tmp_path, BASE)
    before = fingerprint_target("pkgx.mod:f", root)
    _pkg(tmp_path, BASE.replace('"""Doc."""', '"""Other doc."""')
         .replace("# comment", "# changed").replace("x * RHO", "x*RHO"))
    assert fingerprint_target("pkgx.mod:f", root) == before


def test_logic_change_is_detected(tmp_path):
    root = _pkg(tmp_path, BASE)
    before = fingerprint_target("pkgx.mod:f", root)
    _pkg(tmp_path, BASE.replace("x * RHO", "-x * RHO"))
    assert fingerprint_target("pkgx.mod:f", root) != before


def test_constant_method_and_module_targets(tmp_path):
    root = _pkg(tmp_path, BASE)
    assert "1.2" in normalized_source("pkgx.mod:RHO", root)
    assert "return 1" in normalized_source("pkgx.mod:C.m", root)
    whole = normalized_source("pkgx.mod", root)
    assert "Module doc" not in whole and "def f" in whole


def test_missing_target_raises(tmp_path):
    root = _pkg(tmp_path, BASE)
    with pytest.raises(FingerprintError):
        fingerprint_target("pkgx.mod:nope", root)
    with pytest.raises(FingerprintError):
        fingerprint_target("pkgx.missing", root)


def test_unit_fingerprint_includes_libs(tmp_path, monkeypatch):
    root = _pkg(tmp_path, BASE)
    u = Unit("u", ("pkgx.mod:f",), "c", {"kind": "derivation"}, {}, (), (), ("numpy",))
    a = fingerprint_unit(u, root)
    import fansim.audit.fingerprint as fp
    monkeypatch.setattr(fp, "lib_versions", lambda libs: {"numpy": "0.0-test"})
    assert fingerprint_unit(u, root) != a


def test_openfoam_lib_version_is_the_image_tag():
    from fansim.cfd.runner import DEFAULT_IMAGE
    assert lib_versions(("openfoam",)) == {"openfoam": DEFAULT_IMAGE}
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/audit/test_audit_fingerprint.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'fansim.audit.fingerprint'`

- [ ] **Step 3: Write the implementation**

`fansim/audit/fingerprint.py`:

```python
"""Logic-only fingerprints of audited code.

Source is parsed to an AST, docstrings are dropped, and ``ast.unparse`` re-emits it. Comments,
docstrings and formatting therefore never change a fingerprint; any change to what the code *does*
does. Modules are read from disk, not imported, so fingerprinting is fast and side-effect free.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib.metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class FingerprintError(LookupError):
    """A registry target does not resolve to code."""


def module_path(module: str, root: Path = ROOT) -> Path:
    base = Path(root, *module.split("."))
    for cand in (base.with_suffix(".py"), base / "__init__.py"):
        if cand.is_file():
            return cand
    raise FingerprintError(f"module {module!r} not found under {root}")


def _strip_docstrings(tree: ast.AST) -> ast.AST:
    tree = copy.deepcopy(tree)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(
                getattr(body[0], "value", None), ast.Constant
            ) and isinstance(body[0].value.value, str):
                node.body = body[1:] or [ast.Pass()]
    return tree


def _find(body: list[ast.stmt], name: str) -> ast.stmt | None:
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == name:
            return node
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == name for t in node.targets
        ):
            return node
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
            return node
    return None


def normalized_source(target: str, root: Path = ROOT) -> str:
    module, _, qual = target.partition(":")
    tree = ast.parse(module_path(module, root).read_text(encoding="utf-8"))
    node: ast.AST = tree
    if qual:
        for part in qual.split("."):
            found = _find(getattr(node, "body", []), part)
            if found is None:
                raise FingerprintError(f"{target!r}: {part!r} not found")
            node = found
    return ast.unparse(_strip_docstrings(node))


def fingerprint_target(target: str, root: Path = ROOT) -> str:
    return hashlib.sha256(normalized_source(target, root).encode()).hexdigest()[:16]


def lib_versions(libs: tuple[str, ...]) -> dict[str, str]:
    out: dict[str, str] = {}
    for lib in libs:
        if lib == "openfoam":
            from fansim.cfd.runner import DEFAULT_IMAGE
            out[lib] = DEFAULT_IMAGE
        else:
            try:
                out[lib] = importlib.metadata.version(lib)
            except importlib.metadata.PackageNotFoundError:
                out[lib] = "missing"
    return out


def fingerprint_unit(unit, root: Path = ROOT) -> str:
    parts = [f"{t}={fingerprint_target(t, root)}" for t in sorted(unit.targets)]
    parts += [f"lib:{k}={v}" for k, v in sorted(lib_versions(unit.libs).items())]
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()[:16]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/audit/test_audit_fingerprint.py -v`
Expected: all PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add fansim/audit/fingerprint.py tests/audit/test_audit_fingerprint.py
git commit -m "feat(audit): logic-only AST fingerprints for audited code

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Ledger, status classifier, `scripts/audit_status.py`

**Files:**
- Create: `fansim/audit/status.py`
- Create: `scripts/audit_status.py`
- Create: `docs/validation/audits/ledger.json` (content: `{"units": {}}`)
- Test: `tests/audit/test_audit_status.py`

**Interfaces:**
- Consumes: `Registry`, `Unit`, `load_registry` (Task 1); `fingerprint_unit`, `module_path`, `ROOT` (Task 2).
- Produces:
  - `State` (str Enum): `PROVEN`, `CHANGED`, `AFFECTED`, `NEW`
  - `LEDGER_PATH: Path`
  - `load_ledger(path: Path = LEDGER_PATH) -> dict`, shaped `{"units": {id: {"fingerprint", "verdict", "date", "report"}}}`
  - `record_pass(unit_id: str, fingerprint: str, report: str, date: str, path: Path = LEDGER_PATH) -> None`
  - `classify(registry: Registry, ledger: dict, fingerprints: dict[str, str]) -> dict[str, State]`
  - `PHYSICS_PACKAGES: tuple[str, ...]`
  - `find_unregistered(registry: Registry, packages: tuple[str, ...] = PHYSICS_PACKAGES, root: Path = ROOT) -> list[str]`

- [ ] **Step 1: Write the failing test**

`tests/audit/test_audit_status.py`:

```python
"""Status: only changed / affected / new units need re-audit."""

from __future__ import annotations

from pathlib import Path

from fansim.audit.registry import Registry, Unit
from fansim.audit.status import State, classify, find_unregistered, load_ledger, record_pass


def _u(uid, deps=(), targets=("m",)):
    return Unit(uid, tuple(targets), "c", {"kind": "derivation"}, {}, (), tuple(deps), ())


REG = Registry(units={"a": _u("a"), "b": _u("b", ["a"]), "c": _u("c", ["b"]), "d": _u("d")},
               exempt=())


def _ledger(**fps):
    return {"units": {k: {"fingerprint": v, "verdict": "PASS"} for k, v in fps.items()}}


def test_all_proven():
    fps = {"a": "1", "b": "2", "c": "3", "d": "4"}
    st = classify(REG, _ledger(**fps), fps)
    assert set(st.values()) == {State.PROVEN}


def test_change_propagates_transitively_but_not_sideways():
    led = _ledger(a="1", b="2", c="3", d="4")
    st = classify(REG, led, {"a": "X", "b": "2", "c": "3", "d": "4"})
    assert st == {"a": State.CHANGED, "b": State.AFFECTED, "c": State.AFFECTED, "d": State.PROVEN}


def test_never_passed_is_new_and_blocks_dependents():
    led = _ledger(b="2", c="3", d="4")
    st = classify(REG, led, {"a": "1", "b": "2", "c": "3", "d": "4"})
    assert st["a"] is State.NEW and st["b"] is State.AFFECTED and st["c"] is State.AFFECTED


def test_record_pass_round_trip(tmp_path):
    p = tmp_path / "ledger.json"
    record_pass("a", "abc", "docs/validation/audits/x.md", "2026-09-24", path=p)
    led = load_ledger(p)
    assert led["units"]["a"] == {"fingerprint": "abc", "verdict": "PASS", "date": "2026-09-24",
                                 "report": "docs/validation/audits/x.md"}


def test_find_unregistered(tmp_path: Path):
    pkg = tmp_path / "phys"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "m1.py").write_text("def covered():\n    pass\n\ndef loose():\n    pass\n\n"
                               "def _private():\n    pass\n\nclass K:\n    pass\n", encoding="utf-8")
    (pkg / "m2.py").write_text("def whole():\n    pass\n", encoding="utf-8")
    (pkg / "m3.py").write_text("def skipme():\n    pass\n", encoding="utf-8")
    reg = Registry(units={"x": _u("x", targets=("phys.m1:covered", "phys.m2"))},
                   exempt=("phys.m3:*",))
    assert find_unregistered(reg, ("phys",), tmp_path) == ["phys.m1:K", "phys.m1:loose"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/audit/test_audit_status.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'fansim.audit.status'`

- [ ] **Step 3: Write the implementation**

`fansim/audit/status.py`:

```python
"""Which audited units need re-auditing: PROVEN / CHANGED / AFFECTED / NEW (+ unregistered code)."""

from __future__ import annotations

import ast
import fnmatch
import json
from enum import Enum
from pathlib import Path

from fansim.audit.fingerprint import ROOT
from fansim.audit.registry import Registry

LEDGER_PATH = ROOT / "docs" / "validation" / "audits" / "ledger.json"
PHYSICS_PACKAGES = (
    "fansim.cfd", "fansim.acoustics", "fansim.propeller", "fansim.cror", "fansim.centrifugal",
    "fansim.volute", "fansim.wind_turbine", "fansim.structural", "fansim.physics", "fansim.fan_bem",
)


class State(str, Enum):
    PROVEN = "PROVEN"
    CHANGED = "CHANGED"
    AFFECTED = "AFFECTED"
    NEW = "NEW"


def load_ledger(path: Path = LEDGER_PATH) -> dict:
    if not Path(path).is_file():
        return {"units": {}}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def record_pass(unit_id: str, fingerprint: str, report: str, date: str,
                path: Path = LEDGER_PATH) -> None:
    led = load_ledger(path)
    led.setdefault("units", {})[unit_id] = {
        "fingerprint": fingerprint, "verdict": "PASS", "date": date, "report": report,
    }
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(led, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def classify(registry: Registry, ledger: dict, fingerprints: dict[str, str]) -> dict[str, State]:
    passed = ledger.get("units", {})
    own: dict[str, State] = {}
    for uid in registry.units:
        rec = passed.get(uid)
        if rec is None or rec.get("verdict") != "PASS":
            own[uid] = State.NEW
        elif rec.get("fingerprint") != fingerprints[uid]:
            own[uid] = State.CHANGED
        else:
            own[uid] = State.PROVEN
    out: dict[str, State] = {}

    def resolve(uid: str) -> State:
        if uid in out:
            return out[uid]
        state = own[uid]
        if state is State.PROVEN and any(
            resolve(d) is not State.PROVEN for d in registry.units[uid].depends_on
        ):
            state = State.AFFECTED
        out[uid] = state
        return state

    for uid in registry.units:
        resolve(uid)
    return out


def _covered(name: str, registry: Registry) -> bool:
    module = name.split(":")[0]
    for u in registry.units.values():
        for t in u.targets:
            if t == name or t == module:
                return True
    return any(fnmatch.fnmatch(name, pat) for pat in registry.exempt)


def find_unregistered(registry: Registry, packages: tuple[str, ...] = PHYSICS_PACKAGES,
                      root: Path = ROOT) -> list[str]:
    names: list[str] = []
    for pkg in packages:
        base = Path(root, *pkg.split("."))
        files = sorted(base.rglob("*.py")) if base.is_dir() else [base.with_suffix(".py")]
        for f in files:
            if not f.is_file():
                continue
            rel = f.relative_to(root).with_suffix("")
            parts = rel.parts[:-1] if rel.name == "__init__" else rel.parts
            module = ".".join(parts)
            tree = ast.parse(f.read_text(encoding="utf-8"))
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) \
                        and not node.name.startswith("_"):
                    name = f"{module}:{node.name}"
                    if not _covered(name, registry):
                        names.append(name)
    return sorted(names)
```

`scripts/audit_status.py`:

```python
"""Show which audited physics units need re-auditing.

Usage:
    uv run python scripts/audit_status.py                 # table of registered units
    uv run python scripts/audit_status.py --unregistered  # also list physics code with no unit
    uv run python scripts/audit_status.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fansim.audit.fingerprint import fingerprint_unit  # noqa: E402
from fansim.audit.registry import load_registry  # noqa: E402
from fansim.audit.status import State, classify, find_unregistered, load_ledger  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Physics audit status")
    ap.add_argument("--unregistered", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    reg = load_registry()
    fps = {uid: fingerprint_unit(u) for uid, u in reg.units.items()}
    states = classify(reg, load_ledger(), fps)
    loose = find_unregistered(reg)
    if args.json:
        print(json.dumps({"units": {k: v.value for k, v in states.items()},
                          "unregistered": loose}, indent=2))
        return 0
    for uid in sorted(states):
        print(f"{states[uid].value:<9} {uid}")
    counts = {s.value: sum(1 for v in states.values() if v is s) for s in State}
    print("\n" + "  ".join(f"{k}={v}" for k, v in counts.items()) + f"  UNREGISTERED={len(loose)}")
    if args.unregistered:
        print("\nUnregistered physics code:")
        for name in loose:
            print(f"  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

`docs/validation/audits/ledger.json`:

```json
{"units": {}}
```

- [ ] **Step 4: Run the tests, then the CLI**

Run: `uv run pytest tests/audit/test_audit_status.py -v`
Expected: all PASS (5 tests)

Run: `uv run python scripts/audit_status.py`
Expected: exit 0. Every Task 1 unit prints as `NEW` or `AFFECTED`, then a count line. If it raises
`FingerprintError`, a registry target name is wrong: fix the YAML entry, not the code.

- [ ] **Step 5: Commit**

```bash
git add fansim/audit/status.py scripts/audit_status.py docs/validation/audits/ledger.json tests/audit/test_audit_status.py
git commit -m "feat(audit): ledger + change-driven status (PROVEN/CHANGED/AFFECTED/NEW)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Air properties single source + "are we on Earth?" checks

**Files:**
- Create: `fansim/physics/air.py`
- Test: `tests/audit/test_air_properties.py`

**Interfaces:**
- Produces: `RHO_AMCA = 1.2`, `RHO_ISA = 1.225`, `NU_AIR = 1.5e-5`, `MU_AIR = 1.81e-5`,
  `C0_AIR = 343.0`, `P0_PA = 101325.0`, `T_ROOM_K = 293.15`, `R_AIR = 287.05`, `GAMMA_AIR = 1.4`.
  `KNOWN_COPIES` (in the test) snapshots today's local constant copies. New copies fail.

- [ ] **Step 1: Write the failing test**

`tests/audit/test_air_properties.py`:

```python
"""Air is room-temperature sea-level air, derived from first principles, and nobody forks it."""

from __future__ import annotations

import ast
import math
import re
from pathlib import Path

import pytest

from fansim.physics import air

ROOT = Path(__file__).resolve().parents[2]
NAME_RE = re.compile(r"^(RHO(_AIR)?|NU(_AIR)?|MU(_AIR)?|C0(_AIR)?|C_SOUND|SPEED_OF_SOUND)$")

# Local copies that existed on 2026-09-24 (spec finding). Consolidating them is a later change;
# this list may only SHRINK. Values must still agree with fansim.physics.air.
KNOWN_COPIES = {
    ("fansim/acoustics/farfield.py", "C0_AIR"), ("fansim/acoustics/proxies.py", "RHO_AIR"),
    ("fansim/acoustics/proxies.py", "C0_AIR"), ("fansim/cfd/des_fwh.py", "RHO_AIR"),
    ("fansim/cfd/metrics.py", "RHO_AIR"), ("fansim/cfd/openfoam_case.py", "RHO_AIR"),
    ("fansim/cfd/openfoam_case.py", "NU_AIR"), ("fansim/fan_bem.py", "RHO_AIR"),
    ("fansim/fan_bem.py", "NU_AIR"), ("fansim/physics/regime.py", "NU_AIR"),
    ("fansim/physics/regime.py", "C0_AIR"), ("fansim/propeller/bemt.py", "RHO_AIR"),
    ("fansim/propeller/bemt.py", "NU_AIR"), ("fansim/propeller/noise.py", "C_SOUND"),
    ("fansim/propeller/power.py", "RHO_AIR"), ("fansim/wind_turbine/evaluate.py", "RHO_AIR"),
    ("scripts/fan_noise_curle.py", "C0"), ("scripts/fan_noise_cv.py", "C0"),
}


def _module_level_air_constants() -> dict[tuple[str, str], float]:
    found: dict[tuple[str, str], float] = {}
    for top in ("fansim", "scripts"):
        for f in sorted((ROOT / top).rglob("*.py")):
            rel = f.relative_to(ROOT).as_posix()
            if rel == "fansim/physics/air.py":
                continue
            for node in ast.parse(f.read_text(encoding="utf-8")).body:
                if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) \
                        and isinstance(node.value.value, (int, float)):
                    for t in node.targets:
                        if isinstance(t, ast.Name) and NAME_RE.match(t.id):
                            found[(rel, t.id)] = float(node.value.value)
    return found


def test_density_is_ideal_gas_at_room_conditions():
    rho = air.P0_PA / (air.R_AIR * air.T_ROOM_K)
    assert air.RHO_AMCA == pytest.approx(rho, rel=0.01)          # 1.204 at 20 °C
    assert air.RHO_ISA == pytest.approx(air.P0_PA / (air.R_AIR * 288.15), rel=0.01)


def test_speed_of_sound_is_ideal_gas():
    assert air.C0_AIR == pytest.approx(math.sqrt(air.GAMMA_AIR * air.R_AIR * air.T_ROOM_K), rel=0.005)


def test_viscosity_matches_sutherland_and_nu_is_mu_over_rho():
    t = air.T_ROOM_K
    mu = 1.458e-6 * t**1.5 / (t + 110.4)
    assert air.MU_AIR == pytest.approx(mu, rel=0.02)
    assert air.NU_AIR == pytest.approx(air.MU_AIR / air.RHO_AMCA, rel=0.03)


def test_not_water_not_mars():
    # Water: rho ~1000, nu ~1e-6, c ~1480. Mars surface: rho ~0.02, c ~240.
    assert 1.0 < air.RHO_AMCA < 1.3 and 1.0e-5 < air.NU_AIR < 2.0e-5 and 330 < air.C0_AIR < 350


def test_no_new_local_copies():
    new = set(_module_level_air_constants()) - KNOWN_COPIES
    assert not new, f"import these from fansim.physics.air instead of redefining: {sorted(new)}"


def test_existing_copies_agree_with_single_source():
    allowed = {
        "RHO": {air.RHO_AMCA, air.RHO_ISA}, "NU": {air.NU_AIR}, "MU": {air.MU_AIR},
        "C0": {air.C0_AIR}, "C_SOUND": {air.C0_AIR}, "SPEED_OF_SOUND": {air.C0_AIR},
    }
    bad = []
    for (rel, name), val in _module_level_air_constants().items():
        key = name.split("_AIR")[0]
        if val not in allowed[key]:
            bad.append(f"{rel}:{name}={val}")
    assert not bad, bad
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/audit/test_air_properties.py -v`
Expected: FAIL with `ImportError: cannot import name 'air' from 'fansim.physics'`

- [ ] **Step 3: Write the implementation**

`fansim/physics/air.py`:

```python
"""Single source of air properties: room-temperature, sea-level air.

Two densities are deliberate. Fans and ducted CFD use AMCA 210 standard air (1.2 kg/m³, 20 °C,
101.325 kPa). Props and turbines use ISA sea level (1.225 kg/m³, 15 °C) to match the published data
they are compared against. Import from here; do not redefine locally
(``tests/audit/test_air_properties.py`` fails on new copies).
"""

from __future__ import annotations

P0_PA = 101325.0      # sea-level static pressure, Pa
T_ROOM_K = 293.15     # 20 °C
R_AIR = 287.05        # specific gas constant of dry air, J/(kg·K)
GAMMA_AIR = 1.4       # ratio of specific heats

RHO_AMCA = 1.2        # kg/m³ — AMCA 210 standard air (fans, ducted CFD)
RHO_ISA = 1.225       # kg/m³ — ISA sea level (props, turbines, UIUC comparisons)
MU_AIR = 1.81e-5      # dynamic viscosity at 20 °C, Pa·s (Sutherland)
NU_AIR = 1.5e-5       # kinematic viscosity, m²/s (MU_AIR / RHO_AMCA ≈ 1.51e-5)
C0_AIR = 343.0        # speed of sound at 20 °C, m/s
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/audit/test_air_properties.py -v`
Expected: all PASS (6 tests). If `test_no_new_local_copies` lists a file that is not in
`KNOWN_COPIES`, it was missed in the 2026-09-24 grep. Add it to `KNOWN_COPIES` (it pre-dates this
guard), note it in the Task 10 report, and re-run.

- [ ] **Step 5: Commit**

```bash
git add fansim/physics/air.py tests/audit/test_air_properties.py
git commit -m "feat(audit): single air-properties source + first-principles / no-fork checks

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Geometric direction proof (mesh only) with known-answer synthetic fans

This is the core of Audit #1, proof 1. Physics (velocity triangles; Dixon & Hall): a fan blade's
**concave (pressure) face points in the direction of rotation**, and the blade pushes air along that
face's normal. So, from the mesh alone:
1. cut the rotor with a cylinder r = r₀; each blade gives one closed section loop;
2. unroll the loop to (s = r₀·θ, z) and fit the chord line plus a quadratic camber;
3. the concave side gives the pressure-face normal **n_p**;
4. designed rotation = sign(n_p · ŝ), where +ŝ is +θ, i.e. ω_z > 0, CCW seen from +Z;
5. designed delivery = sign(n_p · ẑ).

A second, independent number from face normals (chirality χ = sign Σ A·n_θ·n_z) must equal
rotation × delivery on every section. It is invariant under any proper rotation of the part and flips
under a mirror image.

**Files:**
- Create: `fansim/audit/synthetic.py` (known-answer geometry)
- Create: `fansim/audit/direction.py`
- Test: `tests/audit/test_direction_geometry.py`

**Interfaces:**
- Produces:
  - `cambered_blade_fan(n_blades=5, r_hub=15.0, r_tip=50.0, chord=20.0, stagger_deg=60.0, camber=0.06, thick=1.0, cup_side: int | None = None, hub_height=16.0, sweep_deg=0.0) -> trimesh.Trimesh`, where `sweep_deg` > 0 moves the tip ahead of the root toward +θ
  - `SectionReading(r_mm: float, omega_sign: int, pump_sign: int, chirality: int, camber_ratio: float)`
  - `DirectionProof(omega_sign: int | None, pump_sign: int | None, chirality: int | None, agreement: float, n_sections: int, readings: tuple[SectionReading, ...], verdict: str, note: str)`, where `verdict` is `"CONCLUSIVE"` or `"INCONCLUSIVE"`
  - `prove_direction(mesh: trimesh.Trimesh, r_fracs=(0.55, 0.65, 0.75, 0.85)) -> DirectionProof`
  - `motor_side(mesh: trimesh.Trimesh) -> int | None`: +1 means the open motor cup faces +Z, −1 means −Z, None means unclear
  - `flip_about_x(mesh: trimesh.Trimesh) -> trimesh.Trimesh` (proper 180° rotation, returns a copy)
  - `tip_lead_sign(mesh: trimesh.Trimesh, r_fracs=(0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9), min_sweep_deg=3.0) -> int | None`: +1 means the tips sit ahead of the roots toward +θ, −1 toward −θ, None means unclear. The user-confirmed real fan has its tips leading the rotation, so the expected result is `tip_lead_sign == omega_sign`.
  - `REAL_FAN_CHIRALITY = -1`: the real NF-A12x25 turns CCW seen from the intake and pushes air away from the viewer. With intake at +Z that is ω_z > 0 pumping −Z, so χ = (+1)(−1) = −1.

- [ ] **Step 1: Write the failing test**

`tests/audit/test_direction_geometry.py`:

```python
"""Known-answer checks for the geometric direction proof (Audit #1, proof 1).

Oracle (pressure face = concave face, faces the rotation, pushes air along its normal):
the synthetic section is chord c=(cos g, sin g), normal e=(-sin g, cos g) in (s, z), with camber
bulging toward +e when camber > 0, so the pressure normal is -e = (sin g, -cos g).
  g=+60, camber>0 -> n_p=(+0.87,-0.5): rotation +1 (CCW from +Z), pumps -Z
  g=-60, camber>0 -> n_p=(-0.87,-0.5): rotation -1,              pumps -Z
  g=+60, camber<0 -> n_p=(-0.87,+0.5): rotation -1,              pumps +Z
"""

from __future__ import annotations

import numpy as np
import pytest
import trimesh

from fansim.audit.direction import (
    REAL_FAN_CHIRALITY,
    flip_about_x,
    motor_side,
    prove_direction,
    tip_lead_sign,
)
from fansim.audit.synthetic import cambered_blade_fan


def _mirror_x(mesh):
    m = mesh.copy()
    m.apply_transform(np.diag([-1.0, 1.0, 1.0, 1.0]))
    m.fix_normals()
    return m


@pytest.mark.parametrize("stagger, camber, omega, pump", [
    (60.0, 0.06, +1, -1),
    (-60.0, 0.06, -1, -1),
    (60.0, -0.06, -1, +1),
    (30.0, 0.06, +1, -1),
])
def test_known_answers(stagger, camber, omega, pump):
    p = prove_direction(cambered_blade_fan(stagger_deg=stagger, camber=camber))
    assert p.verdict == "CONCLUSIVE", p.note
    assert (p.omega_sign, p.pump_sign) == (omega, pump)
    assert p.chirality == omega * pump
    assert p.agreement == 1.0


def test_overlapping_high_solidity_blades():
    # 9 long blades overlap in theta at mid-span (like the A12x25); loops must still separate.
    p = prove_direction(cambered_blade_fan(n_blades=9, chord=40.0, stagger_deg=55.0))
    assert p.verdict == "CONCLUSIVE" and (p.omega_sign, p.pump_sign) == (+1, -1)


def test_proper_rotation_keeps_chirality_mirror_flips_it():
    base = cambered_blade_fan()
    flipped = prove_direction(flip_about_x(base))
    assert (flipped.omega_sign, flipped.pump_sign) == (-1, +1)   # same physical fan, turned over
    assert flipped.chirality == prove_direction(base).chirality
    mirrored = prove_direction(_mirror_x(base))
    assert mirrored.chirality == -prove_direction(base).chirality


def test_face_winding_does_not_matter():
    m = cambered_blade_fan()
    m.invert()
    p = prove_direction(m)
    assert (p.omega_sign, p.pump_sign) == (+1, -1)


def test_flat_plate_is_inconclusive():
    p = prove_direction(cambered_blade_fan(camber=0.0))
    assert p.verdict == "INCONCLUSIVE" and p.omega_sign is None


@pytest.mark.parametrize("sweep, expected", [(25.0, +1), (-25.0, -1), (0.0, None)])
def test_tip_lead_sign(sweep, expected):
    assert tip_lead_sign(cambered_blade_fan(n_blades=9, chord=30.0, sweep_deg=sweep)) == expected


def test_tip_lead_follows_the_part_when_turned_over():
    # Turning the fan over reverses theta, so the tip-lead sign flips together with omega.
    m = cambered_blade_fan(sweep_deg=25.0)
    assert tip_lead_sign(flip_about_x(m)) == -1


def test_real_fan_chirality_constant():
    # CCW seen from the intake (+Z viewer => omega_z > 0) pushing air away (-Z): (+1)*(-1).
    assert REAL_FAN_CHIRALITY == -1


@pytest.mark.parametrize("side", [+1, -1])
def test_motor_side(side):
    assert motor_side(cambered_blade_fan(cup_side=side)) == side


def test_motor_side_unclear_without_cup():
    assert motor_side(cambered_blade_fan(cup_side=None)) is None


def test_synthetic_blades_are_watertight():
    for b in cambered_blade_fan().split(only_watertight=False):
        assert isinstance(b, trimesh.Trimesh) and b.is_watertight
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/audit/test_direction_geometry.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'fansim.audit.direction'`

- [ ] **Step 3: Write the synthetic geometry**

`fansim/audit/synthetic.py`:

```python
"""Known-answer rotor geometry for audit self-checks (no CadQuery; pure trimesh).

Each blade is a thin cambered section, extruded radially and wrapped onto the cylinder
(theta = s / rho), so it is a true helical blade and not a flat card. In the section plane (s, z):
chord c = (cos g, sin g), normal e = (-sin g, cos g), mean line bulging toward +e by
``camber * chord``. The hub is a solid cylinder or a motor cup (``cup_side`` = the open face).
"""

from __future__ import annotations

import numpy as np
import trimesh


def _blade(theta0, r_hub, r_tip, chord, stagger_deg, camber, thick, sweep_deg=0.0,
           n_chord=40, n_span=12):
    g = np.radians(stagger_deg)
    c_hat = np.array([np.cos(g), np.sin(g)])
    e_hat = np.array([-np.sin(g), np.cos(g)])
    xi = np.linspace(-chord / 2, chord / 2, n_chord)
    eta_m = camber * chord * (1.0 - (2.0 * xi / chord) ** 2)
    rho = np.linspace(r_hub - 1.0, r_tip, n_span)
    layers = []
    for side in (+1.0, -1.0):
        eta = eta_m + side * thick / 2.0
        s = xi * c_hat[0] + eta * e_hat[0]
        a = xi * c_hat[1] + eta * e_hat[1]
        sweep = np.radians(sweep_deg) * (rho - r_hub) / (r_tip - r_hub)
        th = theta0 + sweep[None, :] + s[:, None] / rho[None, :]
        x = rho[None, :] * np.cos(th)
        y = rho[None, :] * np.sin(th)
        z = np.broadcast_to(a[:, None], th.shape)
        layers.append(np.stack([x, y, z], axis=-1).reshape(-1, 3))
    verts = np.vstack(layers)
    nc, ns = n_chord, n_span

    def vid(side, i, j):
        return side * nc * ns + i * ns + j

    faces = []

    def quad(a_, b_, c_, d_):
        faces.extend([[a_, b_, c_], [a_, c_, d_]])

    for i in range(nc - 1):
        for j in range(ns - 1):
            for side in (0, 1):
                quad(vid(side, i, j), vid(side, i + 1, j), vid(side, i + 1, j + 1), vid(side, i, j + 1))
    for i in (0, nc - 1):
        for j in range(ns - 1):
            quad(vid(0, i, j), vid(1, i, j), vid(1, i, j + 1), vid(0, i, j + 1))
    for j in (0, ns - 1):
        for i in range(nc - 1):
            quad(vid(0, i, j), vid(0, i + 1, j), vid(1, i + 1, j), vid(1, i, j))
    mesh = trimesh.Trimesh(verts, np.asarray(faces), process=True)
    mesh.fix_normals()
    return mesh


def _hub(r_hub, height, cup_side):
    if cup_side is None:
        return trimesh.creation.cylinder(radius=r_hub, height=height, sections=48)
    cup_r, cap = 0.75 * r_hub, 1.5
    wall = trimesh.creation.annulus(r_min=cup_r, r_max=r_hub, height=height, sections=48)
    lid = trimesh.creation.cylinder(radius=cup_r, height=cap, sections=48)
    # The lid closes the face OPPOSITE the open cup.
    lid.apply_translation([0.0, 0.0, -cup_side * (height - cap) / 2.0])
    return trimesh.util.concatenate([wall, lid])


def cambered_blade_fan(n_blades: int = 5, r_hub: float = 15.0, r_tip: float = 50.0,
                       chord: float = 20.0, stagger_deg: float = 60.0, camber: float = 0.06,
                       thick: float = 1.0, cup_side: int | None = None,
                       hub_height: float = 16.0, sweep_deg: float = 0.0) -> trimesh.Trimesh:
    parts = [_blade(2.0 * np.pi * k / n_blades, r_hub, r_tip, chord, stagger_deg, camber, thick,
                    sweep_deg)
             for k in range(n_blades)]
    parts.append(_hub(r_hub, hub_height, cup_side))
    return trimesh.util.concatenate(parts)
```

- [ ] **Step 4: Write the direction proof**

`fansim/audit/direction.py`:

```python
"""Audit #1, proof 1: which way a rotor is designed to turn and pump, from its mesh alone.

Velocity-triangle physics (Dixon & Hall): the concave pressure face of a fan blade points in the
direction of rotation, and the blade pushes air along that face's normal. For cylinder cuts
r = r0 through the blades we unroll each section loop to (s = r0*theta, z), fit chord + quadratic
camber, take the concave side's normal n_p, and read rotation = sign(n_p.s) (+1 = +theta =
omega_z > 0, CCW seen from +Z) and delivery = sign(n_p.z) (+1 = +Z).

Cross-check: chirality chi = sign(sum A * n_theta * n_z) over the cut faces. chi is invariant under
any proper rotation of the part and flips under mirroring; it must equal rotation * delivery.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import networkx as nx
import numpy as np
import trimesh

MIN_CAMBER_RATIO = 0.01   # camber height / chord below which the concave side is not trusted
MIN_AGREEMENT = 0.9       # fraction of sections that must agree
REAL_FAN_CHIRALITY = -1   # NF-A12x25: CCW seen from intake, air pushed away from the viewer


@dataclass(frozen=True)
class SectionReading:
    r_mm: float
    omega_sign: int
    pump_sign: int
    chirality: int
    camber_ratio: float


@dataclass(frozen=True)
class DirectionProof:
    omega_sign: int | None
    pump_sign: int | None
    chirality: int | None
    agreement: float
    n_sections: int
    readings: tuple[SectionReading, ...]
    verdict: str
    note: str


def _tip_radius(mesh: trimesh.Trimesh) -> float:
    v = mesh.vertices
    return float(np.percentile(np.hypot(v[:, 0], v[:, 1]), 99.5))


def _section_loops(mesh: trimesh.Trimesh, r0: float):
    """Cut with the cylinder r = r0. Yields (ordered loop points (k,3), crossed face ids)."""
    v = mesh.vertices
    r = np.hypot(v[:, 0], v[:, 1]) - r0
    e = mesh.edges_unique
    crossed = (r[e[:, 0]] * r[e[:, 1]]) < 0.0
    idx = np.nonzero(crossed)[0]
    if len(idx) == 0:
        return
    t = r[e[idx, 0]] / (r[e[idx, 0]] - r[e[idx, 1]])
    pts = v[e[idx, 0]] + t[:, None] * (v[e[idx, 1]] - v[e[idx, 0]])
    pos = -np.ones(len(e), dtype=int)
    pos[idx] = np.arange(len(idx))
    fue = mesh.faces_unique_edges
    hit = crossed[fue]
    g = nx.Graph()
    g.add_nodes_from(range(len(idx)))
    for f in np.nonzero(hit.sum(axis=1) == 2)[0]:
        a, b = pos[fue[f][hit[f]]]
        g.add_edge(int(a), int(b), face=int(f))
    for comp in nx.connected_components(g):
        sub = g.subgraph(comp)
        if len(comp) < 8:
            continue
        order = list(nx.dfs_preorder_nodes(sub))
        faces = np.array([d["face"] for _, _, d in sub.edges(data=True)], dtype=int)
        yield pts[order], faces


def _resample_closed(p2: np.ndarray, n: int = 400) -> np.ndarray:
    closed = np.vstack([p2, p2[:1]])
    seg = np.linalg.norm(np.diff(closed, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    u = np.linspace(0.0, cum[-1], n, endpoint=False)
    return np.column_stack([np.interp(u, cum, closed[:, 0]), np.interp(u, cum, closed[:, 1])])


def _read_section(mesh, pts, faces, r0) -> SectionReading | None:
    theta = np.arctan2(pts[:, 1], pts[:, 0])
    tm = np.angle(np.mean(np.exp(1j * theta)))
    s = r0 * np.angle(np.exp(1j * (theta - tm)))
    p2 = _resample_closed(np.column_stack([s, pts[:, 2]]))
    p2 = p2 - p2.mean(axis=0)
    _, vecs = np.linalg.eigh(p2.T @ p2)
    c_hat = vecs[:, 1]
    e_hat = np.array([-c_hat[1], c_hat[0]])
    xi, eta = p2 @ c_hat, p2 @ e_hat
    chord = float(xi.max() - xi.min())
    if chord <= 0.0:
        return None
    a = float(np.polyfit(xi, eta, 2)[0])
    camber_ratio = abs(a) * (chord / 2.0) ** 2 / chord
    n_p = np.sign(a) * e_hat  # a < 0: bulges +e, concave (pressure) face is -e
    fc = mesh.triangles_center[faces]
    fn = mesh.face_normals[faces]
    th = np.arctan2(fc[:, 1], fc[:, 0])
    n_theta = -np.sin(th) * fn[:, 0] + np.cos(th) * fn[:, 1]
    chi = float(np.sum(mesh.area_faces[faces] * n_theta * fn[:, 2]))
    return SectionReading(float(r0), int(np.sign(n_p[0])), int(np.sign(n_p[1])),
                          int(np.sign(chi)), float(camber_ratio))


def prove_direction(mesh: trimesh.Trimesh,
                    r_fracs: tuple[float, ...] = (0.55, 0.65, 0.75, 0.85)) -> DirectionProof:
    tip = _tip_radius(mesh)
    readings: list[SectionReading] = []
    flat = 0
    for f in r_fracs:
        for pts, faces in _section_loops(mesh, f * tip):
            rd = _read_section(mesh, pts, faces, f * tip)
            if rd is None:
                continue
            if rd.camber_ratio < MIN_CAMBER_RATIO:
                flat += 1
                continue
            readings.append(rd)
    if not readings:
        return DirectionProof(None, None, None, 0.0, 0, (), "INCONCLUSIVE",
                              f"no cambered sections ({flat} flat) — concave side undefined")
    (om, pu), n = Counter((r.omega_sign, r.pump_sign) for r in readings).most_common(1)[0]
    agreement = n / len(readings)
    chi_ok = sum(r.chirality == r.omega_sign * r.pump_sign for r in readings) / len(readings)
    chi = Counter(r.chirality for r in readings).most_common(1)[0][0]
    if agreement < MIN_AGREEMENT or chi_ok < MIN_AGREEMENT:
        return DirectionProof(None, None, None, agreement, len(readings), tuple(readings),
                              "INCONCLUSIVE",
                              f"sections disagree (agreement {agreement:.2f}, chirality check {chi_ok:.2f})")
    return DirectionProof(int(om), int(pu), int(chi), agreement, len(readings), tuple(readings),
                          "CONCLUSIVE", f"{len(readings)} sections, {flat} flat skipped")


def motor_side(mesh: trimesh.Trimesh, n: int = 64, min_depth_mm: float = 2.0) -> int | None:
    """Face (+1 = +Z, -1 = -Z) where the hub is an open cup: axial rays go deeper on that side."""
    v = mesh.vertices
    tip = _tip_radius(mesh)
    rv = np.hypot(v[:, 0], v[:, 1])
    hub = v[rv < 0.3 * tip]
    if len(hub) < 10:
        return None
    z0, z1 = float(hub[:, 2].min()), float(hub[:, 2].max())
    rng = np.random.default_rng(0)
    rr = tip * (0.05 + 0.10 * rng.random(n))
    th = 2.0 * np.pi * rng.random(n)
    xy = np.column_stack([rr * np.cos(th), rr * np.sin(th)])

    def depth(z_face: float, direction: float) -> float | None:
        origins = np.column_stack([xy, np.full(n, z_face - direction * 1.0)])
        dirs = np.tile([0.0, 0.0, direction], (n, 1))
        locs, _, _ = mesh.ray.intersects_location(origins, dirs, multiple_hits=False)
        if len(locs) < n // 2:
            return None
        return float(np.median(np.abs(locs[:, 2] - z_face)))

    d_lo, d_hi = depth(z0, +1.0), depth(z1, -1.0)
    if d_lo is None or d_hi is None or abs(d_lo - d_hi) < min_depth_mm:
        return None
    return -1 if d_lo > d_hi else +1


def tip_lead_sign(mesh: trimesh.Trimesh,
                  r_fracs: tuple[float, ...] = (0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9),
                  min_sweep_deg: float = 3.0) -> int | None:
    """Which way the blade tips sit ahead of the roots: +1 toward +theta, -1 toward -theta.

    Each blade is tracked outward through closely spaced cylinder cuts (nearest section centroid
    step to step, so large total sweep never jumps to a neighbour blade). The median total sweep
    across blades decides; |sweep| below ``min_sweep_deg`` is unclear (None).
    """
    tip = _tip_radius(mesh)
    rings = []
    for f in r_fracs:
        cents = []
        for pts, _ in _section_loops(mesh, f * tip):
            th = np.arctan2(pts[:, 1], pts[:, 0])
            cents.append(float(np.angle(np.mean(np.exp(1j * th)))))
        if not cents:
            return None
        rings.append(np.array(cents))
    totals = []
    for start in rings[0]:
        cur, total = start, 0.0
        for ring in rings[1:]:
            d = np.angle(np.exp(1j * (ring - cur)))
            k = int(np.argmin(np.abs(d)))
            total += float(d[k])
            cur = ring[k]
        totals.append(total)
    sweep = float(np.degrees(np.median(totals)))
    if abs(sweep) < min_sweep_deg:
        return None
    return 1 if sweep > 0 else -1


def flip_about_x(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Proper 180° rotation about X (z -> -z, y -> -y): same fan, turned over."""
    m = mesh.copy()
    m.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1.0, 0.0, 0.0]))
    return m
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/audit/test_direction_geometry.py -v`
Expected: all PASS (17 tests)

If a known-answer case fails, **do not change the oracle table to match the code**. The oracle comes
from the physics in the test docstring. Debug `_read_section`: check the θ unwrap and the concave-side
sign. If the physics itself looks wrong, stop and raise it with the user.

- [ ] **Step 6: Commit**

```bash
git add fansim/audit/synthetic.py fansim/audit/direction.py tests/audit/test_direction_geometry.py
git commit -m "feat(audit): mesh-only direction proof (camber + chirality) with known-answer fans

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Run the geometric proof on the real rotors

**Files:**
- Create: `scripts/audit_direction_geometry.py`
- Output (not committed by the script; Task 10 commits it): `docs/validation/audits/direction_geometry.json`

**Interfaces:**
- Consumes: `prove_direction`, `motor_side`, `REAL_FAN_CHIRALITY` (Task 5); `load_blade_params`, `build_impeller`, `export_stl`.
- Produces: JSON `{"rotors": {name: {"omega_sign", "pump_sign", "chirality", "verdict", "note", "agreement", "n_sections", "motor_side", "checks": {...}}}, "cfd_spin_in_use": -1}`, with rotor names `"stock"` and `"reference_stl"`.

- [ ] **Step 1: Write the script**

`scripts/audit_direction_geometry.py`:

```python
"""Audit #1, proof 1 on the real rotors: Stock recipe STL + close-ref STL.

Checks (each True / False / None=unclear):
  real_handedness   chirality == REAL_FAN_CHIRALITY (model is not a mirror image of the real fan)
  motor_on_exhaust  motor_side == pump_sign (air leaves past the motor, like the real Noctua)
  tips_lead         tip_lead_sign == omega_sign (user-confirmed: real A12x25 tips lead the rotation)
  cfd_spin_matches  TestRig default spin == designed omega_sign (CFD turns it the designed way)
  cfd_pumps_plus_z  pump_sign == +1 (designed delivery matches the duct's inlet -Z -> outlet +Z)

Usage:
    uv run python scripts/audit_direction_geometry.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import trimesh  # noqa: E402

from fansim.audit.direction import (  # noqa: E402
    REAL_FAN_CHIRALITY,
    motor_side,
    prove_direction,
    tip_lead_sign,
)
from fansim.cfd.domain import TestRig  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "validation" / "audits" / "direction_geometry.json"
STOCK_PARAMS = ROOT / "config" / "problems" / "a12x25_reference.yaml"
REF_STL = ROOT / "validation" / "reference" / "a12x25_impeller.stl"
STOCK_STL = ROOT / "runs" / "audit_direction" / "stock_impeller.stl"


def _stock_stl() -> Path:
    if not STOCK_STL.is_file():
        from fansim.geometry import build_impeller, export_stl
        from fansim.geometry.config import load_blade_params
        STOCK_STL.parent.mkdir(parents=True, exist_ok=True)
        export_stl(build_impeller(load_blade_params(STOCK_PARAMS)), STOCK_STL)
    return STOCK_STL


def _tri(a, b):
    return None if a is None or b is None else bool(a == b)


def main() -> int:
    spin_in_use = TestRig.__dataclass_fields__["spin"].default
    rotors = {}
    for name, path in (("stock", _stock_stl()), ("reference_stl", REF_STL)):
        mesh = trimesh.load(str(path), force="mesh")
        p = prove_direction(mesh)
        ms = motor_side(mesh)
        tl = tip_lead_sign(mesh)
        rotors[name] = {
            "stl": str(path.relative_to(ROOT)),
            "omega_sign": p.omega_sign, "pump_sign": p.pump_sign, "chirality": p.chirality,
            "verdict": p.verdict, "note": p.note, "agreement": p.agreement,
            "n_sections": p.n_sections, "motor_side": ms, "tip_lead_sign": tl,
            "checks": {
                "real_handedness": _tri(p.chirality, REAL_FAN_CHIRALITY),
                "motor_on_exhaust": _tri(ms, p.pump_sign),
                "tips_lead": _tri(tl, p.omega_sign),
                "cfd_spin_matches": _tri(spin_in_use, p.omega_sign),
                "cfd_pumps_plus_z": _tri(p.pump_sign, 1),
            },
        }
        print(f"[{name}] {p.verdict}: rotate {p.omega_sign}, pump {p.pump_sign}, chi {p.chirality},"
              f" motor {ms} — {p.note}\n    checks {rotors[name]['checks']}", flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"rotors": rotors, "cfd_spin_in_use": spin_in_use}, indent=2) + "\n",
                   encoding="utf-8")
    print(f"-> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run it**

Run: `uv run python scripts/audit_direction_geometry.py`
Expected: exit 0, two `[stock]` / `[reference_stl]` lines, and the JSON written. **Record the printed
lines verbatim for the Task 10 report.** Do not interpret or act on them here.

If a rotor is INCONCLUSIVE with "no cambered sections", re-run with
`prove_direction(mesh, r_fracs=(0.5, 0.6, 0.7, 0.8, 0.9))` in a one-off `uv run python -c` and
record both results. Never lower `MIN_CAMBER_RATIO` to force a verdict.

If Python exits with a segfault (code 139) after printing, that is a known cadquery/VTK teardown
issue. It is harmless as long as the JSON was written.

- [ ] **Step 3: Commit the script only**

```bash
git add scripts/audit_direction_geometry.py
git commit -m "feat(audit): run geometric direction proof on Stock + close-ref rotors

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Signed moment + CFD convention contract tests

These tests pin **what the code currently means**: rotation axis, sign, which patch is which, and the
BC types. They do not claim the convention is correct. They fail if someone silently changes the
meaning, and they make the BC asymmetry explicit.

**Files:**
- Modify: `fansim/cfd/metrics.py` (`FanMetrics` gets `moment_z_nm: float = 0.0`; `parse_fan_metrics` fills it from `moment[3]`)
- Test: `tests/audit/test_cfd_direction_contract.py`

**Interfaces:**
- Produces: `FanMetrics.moment_z_nm`, the signed total moment of the fluid on the impeller about +Z.
  A fan doing work on the air has `moment_z_nm * omega_signed < 0`.

- [ ] **Step 1: Write the failing test**

`tests/audit/test_cfd_direction_contract.py`:

```python
"""Pins the CFD direction *meanings* (not their correctness — that is Audit #1's verdict)."""

from __future__ import annotations

import math
import re
from pathlib import Path

import pytest
import trimesh

from fansim.cfd.domain import TestRig
from fansim.cfd.metrics import parse_fan_metrics
from fansim.cfd.openfoam_case import build_case


def _rig(spin: int) -> TestRig:
    return TestRig(duct_radius=0.06, tip_gap=0.0005, inlet_length=0.24, outlet_length=0.48,
                   impeller_z_min=-0.008, impeller_z_max=0.008, mrf_z_min=-0.01, mrf_z_max=0.01,
                   rpm=2000.0, inlet_velocity=2.0, spin=spin)


def _case(tmp_path: Path, spin: int) -> Path:
    stl = tmp_path / "box.stl"
    trimesh.creation.box(extents=(20.0, 20.0, 5.0)).export(str(stl))
    return build_case(tmp_path / f"case_{spin}", stl, _rig(spin), back_pressure_pa=0.0)


def test_mrf_is_right_handed_about_plus_z_with_signed_omega(tmp_path):
    for spin in (-1, 1):
        text = (_case(tmp_path, spin) / "constant/MRFProperties").read_text(encoding="utf-8")
        assert re.search(r"axis\s+\(0 0 1\);", text)
        omega = float(re.search(r"omega\s+([-+\d.eE]+);", text).group(1))
        assert omega == pytest.approx(spin * 2000.0 * 2.0 * math.pi / 60.0, rel=1e-12)


def test_inlet_is_min_z_outlet_is_max_z(tmp_path):
    text = (_case(tmp_path, -1) / "system/blockMeshDict").read_text(encoding="utf-8")
    verts = re.findall(r"\(\s*([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s*\)", text.split("blocks")[0])
    zs = [float(z) for _, _, z in verts[:8]]
    assert zs[:4] == [min(zs)] * 4 and zs[4:] == [max(zs)] * 4
    assert "inlet  { type patch; faces ((0 3 2 1)); }" in text
    assert "outlet { type patch; faces ((4 5 6 7)); }" in text


def test_free_air_bcs_are_asymmetric(tmp_path):
    """Total-pressure inlet (-Z), static outlet (+Z): reversed through-flow gets easier BCs.

    This is why Audit #1 judges each rotation only in the orientation where it pumps +Z.
    """
    p = (_case(tmp_path, -1) / "0/p").read_text(encoding="utf-8")
    assert re.search(r"inlet\s+\{\s*type totalPressure; p0 uniform 0;", p)
    assert re.search(r"outlet\s+\{\s*type fixedValue; value uniform 0", p)


def test_outlet_flow_is_signed_phi_sum_on_plus_z_outlet(tmp_path):
    text = (_case(tmp_path, -1) / "system/controlDict").read_text(encoding="utf-8")
    block = text[text.index("outletFlow"):]
    block = block[:block.index("}") + 1]
    assert "name            outlet;" in block
    assert "operation       sum;" in block and "fields          (phi);" in block


def _write_pp(case: Path, flow: float, mz: float) -> None:
    def put(fo, fname, row):
        d = case / "postProcessing" / fo / "0"
        d.mkdir(parents=True, exist_ok=True)
        (d / fname).write_text("\n".join(row for _ in range(10)) + "\n", encoding="utf-8")
    put("forces", "moment.dat", f"1 (0 0 {mz}) (0 0 0) (0 0 0)")
    put("forces", "force.dat", "1 (0 0 0.05) (0 0 0) (0 0 0)")
    put("outletFlow", "surfaceFieldValue.dat", f"1 {flow}")
    put("inletP", "surfaceFieldValue.dat", "1 0.0")
    put("outletP", "surfaceFieldValue.dat", "1 0.0")


def test_metrics_keep_flow_and_moment_signed(tmp_path):
    _write_pp(tmp_path, flow=-0.02, mz=0.003)
    m = parse_fan_metrics(tmp_path, omega_rad_s=209.4)
    assert m.flow_m3s < 0 and m.cfm < 0          # reverse flow reads negative, never abs()
    assert m.moment_z_nm == 0.003                 # signed; torque stays |Mz|
    assert m.torque_nm == 0.003
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/audit/test_cfd_direction_contract.py -v`
Expected: the four case tests PASS (they pin existing behaviour).
`test_metrics_keep_flow_and_moment_signed` FAILS with `AttributeError: 'FanMetrics' object has no attribute 'moment_z_nm'`.

If a case test fails instead, the written case differs from what this plan read on 2026-09-24. Fix
the **regex in the test** to match the real file text. That file text *is* the current meaning; do
not change `build_case`.

- [ ] **Step 3: Add the signed moment**

In `fansim/cfd/metrics.py`, add a field at the end of `FanMetrics`, after `eta_total`:

```python
    # Signed fluid moment on the impeller about +Z (N·m). A fan doing work on the air has
    # moment_z_nm * omega_signed < 0. torque_nm stays |moment_z| for power.
    moment_z_nm: float = 0.0
```

In `parse_fan_metrics`, add `moment_z_nm=moment[3],` to the `FanMetrics(...)` call, after
`flow_drift_pct=drift,`.

- [ ] **Step 4: Run the new tests plus the existing metrics consumers**

Run: `uv run pytest tests/audit/test_cfd_direction_contract.py tests/test_cfd.py tests/test_math_consistency.py -v -m "not docker"`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add fansim/cfd/metrics.py tests/audit/test_cfd_direction_contract.py
git commit -m "feat(audit): pin CFD direction meanings; expose signed moment_z

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Bias-free CFD matrix: verdict logic + runner

**Files:**
- Create: `fansim/audit/direction_verdict.py`
- Create: `scripts/audit_direction_cfd.py`
- Test: `tests/audit/test_direction_verdict.py`

**Interfaces:**
- Consumes: `flip_about_x` (Task 5); `FanMetrics.moment_z_nm` (Task 7); `rig_for_reference_stl`, `build_case`, `run_mesh`, `run_solve`, `MeshResolution`, `OpenFOAMRunner`, `image_available`, `parse_fan_metrics`.
- Produces:
  - `MatrixRow(orientation: str, spin: int, cfm: float, converged: bool, shaft_power_w: float, moment_z_nm: float, omega_signed: float)`, with orientation `"as_built"` or `"flipped"`
  - `body_sense(row) -> int`: the rotation sense in the as-built body frame (`spin` for as_built, `-spin` for flipped)
  - `matrix_verdict(rows: list[MatrixRow], geometry_omega: int | None, margin: float = 0.20) -> dict`, with keys `verdict` (`"PASS"`, `"FAIL"` or `"INCONCLUSIVE"`), `designed_sense`, `proper`, `bc_bias_cfm`, `power_sign_ok`, `recommended`, `reasons`

- [ ] **Step 1: Write the failing test**

`tests/audit/test_direction_verdict.py`:

```python
"""CFD-matrix verdict: judge each rotation sense only where it pumps +Z through proper BCs."""

from __future__ import annotations

from fansim.audit.direction_verdict import MatrixRow, body_sense, matrix_verdict


def R(o, s, cfm, conv=True, p=0.5, mz=None):
    om = s * 209.44
    return MatrixRow(o, s, cfm, conv, p, -0.002 * (1 if om > 0 else -1) if mz is None else mz, om)


def test_body_sense():
    assert body_sense(R("as_built", -1, 1)) == -1 and body_sense(R("flipped", -1, 1)) == 1


# Hypothesis-shaped data: body sense +1 is designed (strong, pumps -Z as built, so its proper run
# is the flipped one), and sense -1 is the reversed rotation (weak, pumps +Z as built).
ROWS = [R("as_built", -1, 42.0), R("as_built", +1, -70.0),
        R("flipped", -1, 60.0), R("flipped", +1, -30.0)]


def test_designed_sense_wins_and_matches_geometry():
    v = matrix_verdict(ROWS, geometry_omega=+1)
    assert v["verdict"] == "PASS" and v["designed_sense"] == +1
    assert v["proper"] == {"+1": 60.0, "-1": 42.0}
    assert v["bc_bias_cfm"] == {"+1": 10.0, "-1": -12.0}   # |improper| - proper
    assert v["recommended"] == {"orientation": "flipped", "spin": -1}


def test_geometry_disagreement_fails():
    assert matrix_verdict(ROWS, geometry_omega=-1)["verdict"] == "FAIL"


def test_unconverged_proper_run_is_inconclusive():
    rows = ROWS[:2] + [R("flipped", -1, 60.0, conv=False), ROWS[3]]
    assert matrix_verdict(rows, geometry_omega=+1)["verdict"] == "INCONCLUSIVE"


def test_small_margin_is_inconclusive():
    rows = [R("as_built", -1, 55.0), R("as_built", +1, -70.0),
            R("flipped", -1, 60.0), R("flipped", +1, -58.0)]
    assert matrix_verdict(rows, geometry_omega=+1)["verdict"] == "INCONCLUSIVE"


def test_must_also_win_cfm_per_watt():
    rows = [R("as_built", -1, 42.0, p=0.2), R("as_built", +1, -70.0),
            R("flipped", -1, 60.0, p=2.0), R("flipped", +1, -30.0)]
    v = matrix_verdict(rows, geometry_omega=+1)
    assert v["verdict"] == "INCONCLUSIVE" and any("per watt" in r for r in v["reasons"])


def test_power_sign_violation_is_reported():
    rows = ROWS[:2] + [R("flipped", -1, 60.0, mz=-0.002), ROWS[3]]
    v = matrix_verdict(rows, geometry_omega=+1)
    assert v["power_sign_ok"] is False and v["verdict"] == "INCONCLUSIVE"
```

(In `test_power_sign_violation_is_reported`, the flipped/spin −1 row has ω < 0, and mz is set to
−0.002, so mz·ω > 0: the fluid would be driving the rotor, which is non-physical for a delivering fan.)

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/audit/test_direction_verdict.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'fansim.audit.direction_verdict'`

- [ ] **Step 3: Write the verdict logic**

`fansim/audit/direction_verdict.py`:

```python
"""Audit #1, proof 3: verdict from the {as_built, flipped} x {spin -1, +1} free-air CFD matrix.

A 180° flip about X maps body rotation omega -> -omega, so each physical rotation sense appears
twice: once pumping +Z through the proper BCs (total-pressure inlet at -Z, static outlet at +Z) and
once pumping -Z (easier, biased BCs). Senses are compared only on their proper (+Z, positive CFM)
runs. The designed sense must win by ``margin`` on CFM and also on CFM per shaft watt, and must match
the geometric proof.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MatrixRow:
    orientation: str  # "as_built" | "flipped"
    spin: int
    cfm: float
    converged: bool
    shaft_power_w: float
    moment_z_nm: float
    omega_signed: float


def body_sense(row: MatrixRow) -> int:
    return row.spin if row.orientation == "as_built" else -row.spin


def _key(s: int) -> str:
    return f"{s:+d}"


def matrix_verdict(rows: list[MatrixRow], geometry_omega: int | None,
                   margin: float = 0.20) -> dict:
    reasons: list[str] = []
    proper: dict[int, MatrixRow] = {}
    improper: dict[int, MatrixRow] = {}
    for sense in (+1, -1):
        mine = [r for r in rows if body_sense(r) == sense]
        pos = [r for r in mine if r.cfm > 0]
        neg = [r for r in mine if r.cfm <= 0]
        if len(pos) != 1 or len(neg) != 1:
            reasons.append(f"sense {_key(sense)}: expected one +Z and one -Z run, got "
                           f"{[(r.orientation, r.spin, r.cfm) for r in mine]}")
            continue
        proper[sense], improper[sense] = pos[0], neg[0]
    out = {
        "verdict": "INCONCLUSIVE", "designed_sense": None,
        "proper": {_key(s): r.cfm for s, r in proper.items()},
        "bc_bias_cfm": {_key(s): round(abs(improper[s].cfm) - proper[s].cfm, 3)
                        for s in proper if s in improper},
        "power_sign_ok": all(r.moment_z_nm * r.omega_signed < 0 for r in proper.values()),
        "recommended": None, "reasons": reasons,
    }
    if len(proper) != 2:
        return out
    if not all(r.converged for r in proper.values()):
        reasons.append("a proper (+Z) run did not converge")
        return out
    if not out["power_sign_ok"]:
        reasons.append("moment_z * omega >= 0 on a delivering run: fluid driving the rotor")
        return out
    win, lose = sorted(proper, key=lambda s: proper[s].cfm, reverse=True)
    w, lo = proper[win], proper[lose]
    if w.cfm < (1.0 + margin) * lo.cfm:
        reasons.append(f"CFM margin {w.cfm / lo.cfm - 1:.0%} < {margin:.0%}")
        return out
    if w.cfm / max(w.shaft_power_w, 1e-9) <= lo.cfm / max(lo.shaft_power_w, 1e-9):
        reasons.append("winner does not also win CFM per watt")
        return out
    out["designed_sense"] = win
    out["recommended"] = {"orientation": w.orientation, "spin": w.spin}
    if geometry_omega is None:
        reasons.append("geometric proof inconclusive; CFD alone is not a verdict")
        return out
    out["verdict"] = "PASS" if geometry_omega == win else "FAIL"
    if out["verdict"] == "FAIL":
        reasons.append(f"CFD says sense {_key(win)}, geometry says {_key(geometry_omega)}")
    return out
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/audit/test_direction_verdict.py -v`
Expected: all PASS (7 tests)

- [ ] **Step 5: Write the CFD runner**

`scripts/audit_direction_cfd.py`:

```python
"""Audit #1, proof 3: bias-free free-air CFD matrix for one rotor STL.

Meshes each orientation once ({as_built, flipped 180° about X}), then solves spin -1 and +1 at
0 Pa back-pressure on that mesh, and writes the rows + verdict JSON.

Usage:
    uv run python scripts/audit_direction_cfd.py --rotor stock
    uv run python scripts/audit_direction_cfd.py --rotor reference_stl --iters 1500 --procs 8
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import trimesh  # noqa: E402

from fansim.audit.direction import flip_about_x  # noqa: E402
from fansim.audit.direction_verdict import MatrixRow, matrix_verdict  # noqa: E402
from fansim.cfd.metrics import parse_fan_metrics  # noqa: E402
from fansim.cfd.openfoam_case import MeshResolution, build_case, run_mesh, run_solve  # noqa: E402
from fansim.cfd.runner import OpenFOAMRunner, image_available  # noqa: E402
from fansim.validation.reference_stl import rig_for_reference_stl  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ROTORS = {
    "stock": ROOT / "runs" / "audit_direction" / "stock_impeller.stl",   # written by Task 6 script
    "reference_stl": ROOT / "validation" / "reference" / "a12x25_impeller.stl",
}
GEOM_JSON = ROOT / "docs" / "validation" / "audits" / "direction_geometry.json"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rotor", choices=sorted(ROTORS), required=True)
    ap.add_argument("--rpm", type=float, default=2000.0)
    ap.add_argument("--base-cell", type=float, default=0.006)
    ap.add_argument("--min-wall-mm", type=float, default=None,
                    help="thinnest blade wall for mesh sizing (default: Stock recipe value)")
    ap.add_argument("--iters", type=int, default=1500)
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--out", default="runs/audit_direction")
    args = ap.parse_args(argv)
    if not image_available():
        print("SKIPPED: OpenFOAM image not available")
        return 2
    src = ROTORS[args.rotor]
    if not src.is_file():
        print(f"missing {src}; run scripts/audit_direction_geometry.py first")
        return 2
    geom = json.loads(GEOM_JSON.read_text(encoding="utf-8"))["rotors"][args.rotor]
    base = Path(args.out) / args.rotor
    min_wall = args.min_wall_mm
    if min_wall is None:
        from fansim.geometry.blade import min_blade_wall_mm
        from fansim.geometry.config import load_blade_params
        min_wall = min_blade_wall_mm(load_blade_params(
            ROOT / "config" / "problems" / "a12x25_reference.yaml"))
    mesh_res = MeshResolution.for_blade(float(args.base_cell), float(min_wall))
    rows: list[MatrixRow] = []
    for orientation in ("as_built", "flipped"):
        case = base / orientation
        case.mkdir(parents=True, exist_ok=True)
        stl = case / "impeller_mm.stl"
        mesh = trimesh.load(str(src), force="mesh")
        (flip_about_x(mesh) if orientation == "flipped" else mesh).export(str(stl))
        rig0 = rig_for_reference_stl(stl, rpm=args.rpm)
        runner = OpenFOAMRunner(case)
        build_case(case, stl, rig0, mesh=mesh_res, n_iters=args.iters,
                   n_subdomains=args.procs, back_pressure_pa=0.0)
        t0 = time.time()
        run_mesh(runner)
        print(f"[{orientation}] meshed in {time.time() - t0:.0f}s", flush=True)
        for spin in (-1, 1):
            rig = replace(rig0, spin=spin)
            build_case(case, stl, rig, mesh=mesh_res, n_iters=args.iters,
                       n_subdomains=args.procs, back_pressure_pa=0.0)
            t0 = time.time()
            run_solve(runner, n_procs=args.procs)
            m = parse_fan_metrics(case, omega_rad_s=rig.omega_rad_s)
            row = MatrixRow(orientation, spin, m.cfm, m.converged, m.shaft_power_w,
                            m.moment_z_nm, rig.omega_signed)
            rows.append(row)
            print(f"[{orientation} spin {spin:+d}] CFM {m.cfm:+.1f} conv={m.converged} "
                  f"drift={m.flow_drift_pct:.1f}% P={m.shaft_power_w:.3f} W "
                  f"Mz={m.moment_z_nm:+.5f} ({time.time() - t0:.0f}s)", flush=True)
    verdict = matrix_verdict(rows, geometry_omega=geom["omega_sign"])
    payload = {"rotor": args.rotor, "rpm": args.rpm, "iters": args.iters,
               "mesh": asdict(mesh_res), "rows": [asdict(r) for r in rows],
               "geometry": geom, "verdict": verdict}
    out = ROOT / "docs" / "validation" / "audits" / f"direction_cfd_{args.rotor}.json"
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nVERDICT {verdict['verdict']}: {verdict}\n-> {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Smoke-check the script's argument parsing only (no Docker)**

Run: `uv run python scripts/audit_direction_cfd.py --help`
Expected: usage text listing `--rotor {reference_stl,stock}`; exit 0.

- [ ] **Step 7: Commit**

```bash
git add fansim/audit/direction_verdict.py scripts/audit_direction_cfd.py tests/audit/test_direction_verdict.py
git commit -m "feat(audit): bias-free 2x2 CFD direction matrix + verdict logic

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Dead-design guard check

**Files:**
- Test: `tests/audit/test_dead_design_guard.py`
- Modify (only if the test fails): `fansim/optimize/system_curve.py`, the top of `score_operating_point`

**Interfaces:**
- Consumes: `score_operating_point`, `SystemCurveError` from `fansim.optimize.system_curve`.

- [ ] **Step 1: Write the test**

`tests/audit/test_dead_design_guard.py`:

```python
"""A design that does not deliver air must be rejected, never scored (spec: optimizer guard)."""

from __future__ import annotations

import pytest

from fansim.optimize.system_curve import SystemCurveError, score_operating_point


@pytest.mark.parametrize("q_free, q_probe", [(-12.0, -20.0), (0.0, -5.0), (-3.0, 4.0)])
def test_non_delivering_free_air_is_rejected(q_free, q_probe):
    with pytest.raises(SystemCurveError):
        score_operating_point(q_free_cfm=q_free, q_probe_cfm=q_probe, p_probe_pa=5.0,
                              eta_free=0.1, eta_load=0.1, load_pa=5.0)


def test_delivering_design_still_scores():
    op = score_operating_point(q_free_cfm=50.0, q_probe_cfm=30.0, p_probe_pa=5.0,
                               eta_free=0.2, eta_load=0.3, load_pa=5.0)
    assert op.q_op_cfm > 0
```

- [ ] **Step 2: Run it**

Run: `uv run pytest tests/audit/test_dead_design_guard.py -v`
Expected: either all PASS (the guard already exists, and the test now locks it in; go to Step 5) or
some `test_non_delivering_free_air_is_rejected` cases FAIL with `DID NOT RAISE`. That failure is an
audit finding: continue to Step 3 and note it for the Task 10 report.

- [ ] **Step 3: Add the guard (only if Step 2 failed)**

At the top of `score_operating_point` in `fansim/optimize/system_curve.py`, before `k = k_from_pa(load_pa)`:

```python
    if float(q_free_cfm) <= 0.0:
        raise SystemCurveError(
            f"free delivery {float(q_free_cfm):+.1f} CFM is not positive — dead or reversed design"
        )
```

- [ ] **Step 4: Re-run the guard plus the existing system-curve tests**

Run: `uv run pytest tests/audit/test_dead_design_guard.py tests/test_system_curve.py tests/test_objectives_reason.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add tests/audit/test_dead_design_guard.py fansim/optimize/system_curve.py
git commit -m "test(audit): dead/reversed designs are rejected, never scored

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Run Audit #1 and write the verdict report

This task is execution plus writing. It needs Docker and about 1–2 hours of CFD per rotor. Run the
CFD commands in the background.

**Files:**
- Create: `docs/validation/audits/2026-09-24-audit-01-flow-direction.md` (use the actual run date)
- Create (from scripts): `docs/validation/audits/direction_geometry.json`, `direction_cfd_stock.json`, `direction_cfd_reference_stl.json`
- Modify: `docs/validation/audits/ledger.json` (only via `record_pass`, only for PASS units)
- Modify: `docs/roadmap.md` §19.1 (status line only)

- [ ] **Step 1: Fast suite green**

Run: `uv run pytest tests/audit -v`
Expected: all PASS. Then run `git status` and restore any rewritten reference STL/golden.

- [ ] **Step 2: Geometry proof** (skip if the Task 6 JSON is current)

Run: `uv run python scripts/audit_direction_geometry.py`

- [ ] **Step 3: CFD matrix, Stock then reference** (background, ~1–2 h each)

Run: `uv run python scripts/audit_direction_cfd.py --rotor stock`
Run: `uv run python scripts/audit_direction_cfd.py --rotor reference_stl`

If a verdict is INCONCLUSIVE only because a proper run did not converge, re-run that rotor once with
`--iters 3000`. If it is still unconverged, report INCONCLUSIVE; do not loosen tolerances.

- [ ] **Step 4: Write the report**

`docs/validation/audits/<date>-audit-01-flow-direction.md` uses this structure, filled only with
numbers copied from the three JSON files:

```markdown
# Audit #1 — flow direction & sign conventions (<date>)

**Plain-language verdict:** <one paragraph: which way the A12x25 model is designed to turn and pump,
whether our CFD has been solving it that way, whether the model is the real fan's handedness,
whether the motor sits on the exhaust side, and what that means for existing CFM numbers.>

| Unit | Claim | Method | Measured | Expected | Tolerance | Verdict | Evidence |
|---|---|---|---|---|---|---|---|
| audit.direction_geometry | known-answer fans read correctly | synthetic oracle | 17/17 | 17/17 | exact | PASS | tests/audit/test_direction_geometry.py |
| cfd.flow_direction_convention | CFD solves the designed rotation pumping +Z | geometry + 2x2 CFD | <omega/pump/spin/matrix> | designed sense proper-run, spin/orientation as recommended | ≥20% CFM & CFM/W | <PASS/FAIL/INCONCLUSIVE> | direction_geometry.json, direction_cfd_*.json |
| cfd.cfm_from_outlet_flow | signed phi sum on +Z outlet | contract tests | pinned | — | exact | <PASS if the unit it depends on passes, else AFFECTED> | test_cfd_direction_contract.py |
| physics.air_properties | Earth air | first principles | ... | ... | 1–3% | PASS | test_air_properties.py |
| optimize.reject_dead_designs | dead designs rejected | unit test | ... | raise | exact | PASS | test_dead_design_guard.py |
| propeller.thrust_sign | sign from geometry, not flipped | code review | flips spin until thrust>0 | derived | — | FAIL (masking) | fansim/propeller/calibrate.py |

## Evidence
### Proof 1 — geometry (per rotor: rotation, delivery, chirality, motor side, tip lead, 5 checks)
### Proof 2 — contract tests (what spin / patches / BCs / outletFlow mean today)
### Proof 3 — CFD matrix (all 4 rows per rotor, proper vs improper, BC bias, CFM/W, power sign)
### Findings list (air-constant copies, dead-design guard result, prop sign masking)
## Not checked
<e.g. near-shutoff direction, CROR rear rotor, mixed/volute, props beyond the sign-masking review>
## Follow-up plan inputs
<exact changes the verdict implies: spin/orientation, glyphs, docs §16.1, domain.py docstring,
normalize_metrics_sign, CFD_VERSION bump, Stock P–Q re-run — as a list, NOT applied here>
```

- [ ] **Step 5: Update the ledger for PASS units only**

For each unit the report marks PASS, run (in one `uv run python -c` or a scratch script):

```python
from fansim.audit.fingerprint import fingerprint_unit
from fansim.audit.registry import load_registry
from fansim.audit.status import record_pass

reg = load_registry()
for uid in ["<each PASS unit id>"]:
    record_pass(uid, fingerprint_unit(reg.units[uid]),
                "docs/validation/audits/<date>-audit-01-flow-direction.md", "<date>")
```

Then run `uv run python scripts/audit_status.py`. Expected: the PASS units show `PROVEN`, and
everything else shows NEW or AFFECTED.

- [ ] **Step 6: Roadmap status line**

In `docs/roadmap.md` §19.1, append one line under the item:
`**Verdict <date>:** <PASS/FAIL/INCONCLUSIVE> — see docs/validation/audits/<date>-audit-01-flow-direction.md. Freeze <stays|lifts after follow-up plan>.`
Keep the freeze banner. It lifts only when the follow-up fix plan lands.

- [ ] **Step 7: Commit**

```bash
git add docs/validation/audits/ docs/roadmap.md
git commit -m "docs(audit): Audit #1 flow-direction verdict + evidence

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 8: Hand the verdict to the user** in plain language, with the report link. Ask before
writing the follow-up fix plan.
