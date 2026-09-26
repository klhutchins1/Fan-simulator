"""In-house prop/impeller geometry takes its CFD direction from the builder, not the proof.

Re-review of Task 8: the section-quality guard (thickness ratio / midline-fit residual / minimum
distinct radii) correctly closed the "silent backwards solve" hole, but it also made
``fansim.propeller.direction.prop_direction`` (which requires a CONCLUSIVE mesh-only proof)
INCONCLUSIVE for ~10 of 12 ``random_prop_flat`` optimizer designs: thin, stubby, low-camber
sections that are still unambiguously built with Stock handedness, just hard for the proof to
read. That aborted ``refine_pareto_cfd`` and the cockpit CFD-refine flow on a single bad design.

Fix: in-house geometry (``build_prop``/``build_impeller``) uses
``fansim.propeller.direction.BUILDER_DIRECTION`` directly (the builders' handedness is fixed, see
``geometry.stock_handedness``), with ``prove_direction`` run only as a cross-check that raises on
disagreement, not on inconclusiveness.
"""

from __future__ import annotations

import random

import pytest
import trimesh

from fansim.audit.direction import prove_direction
from fansim.prop_spec import get_prop_spec
from fansim.propeller.direction import BUILDER_DIRECTION, resolve_prop_direction
from fansim.propeller.optimize import blade_params_from_trial_params, random_prop_flat


def test_builder_direction_constant():
    assert BUILDER_DIRECTION.orientation == "flipped"
    assert BUILDER_DIRECTION.spin == -1
    assert BUILDER_DIRECTION.source == "builder"
    assert BUILDER_DIRECTION.chirality == -1
    # spin == chirality, same identity documented on prop_direction (Task 8 follow-up).
    assert BUILDER_DIRECTION.spin == BUILDER_DIRECTION.chirality


def test_resolve_prop_direction_external_still_requires_the_proof(tmp_path):
    # External STLs are unchanged: a plain, unreadable mesh (no blades) must still raise.
    mesh = trimesh.creation.cylinder(radius=30.0, height=12.0, sections=32)
    p = tmp_path / "plain.stl"
    mesh.export(str(p))
    with pytest.raises(ValueError, match="INCONCLUSIVE"):
        resolve_prop_direction(p, external=True)


def test_resolve_prop_direction_builder_path_returns_builder_direction_even_when_inconclusive(
    tmp_path,
):
    # A stubby, near-flat blade the mesh-only proof cannot read (INCONCLUSIVE) must still resolve
    # cleanly via the builder path, recording the cross-check rather than raising.
    from fansim.audit.synthetic import cambered_blade_fan

    stubby = cambered_blade_fan(stagger_deg=60.0, camber=0.0)  # flat -> INCONCLUSIVE
    assert prove_direction(stubby).verdict == "INCONCLUSIVE"
    p = tmp_path / "stubby.stl"
    stubby.export(str(p))

    d, crosscheck = resolve_prop_direction(p, external=False)
    assert d == BUILDER_DIRECTION
    assert crosscheck is not None and crosscheck["verdict"] == "INCONCLUSIVE"


def test_resolve_prop_direction_builder_path_raises_on_conclusive_disagreement(tmp_path):
    # A design the proof CAN read, and which disagrees with the builder convention, must still
    # raise -- the cross-check is a real check, not a rubber stamp.
    from fansim.audit.synthetic import cambered_blade_fan

    mirrored = cambered_blade_fan(stagger_deg=60.0, camber=-0.06)  # proof: (omega=-1, pump=+1)
    assert prove_direction(mirrored).verdict == "CONCLUSIVE"
    assert (prove_direction(mirrored).omega_sign, prove_direction(mirrored).pump_sign) != (1, -1)
    p = tmp_path / "mirrored.stl"
    mirrored.export(str(p))
    with pytest.raises(ValueError, match="cross-check disagrees"):
        resolve_prop_direction(p, external=False)


def test_resolve_prop_direction_builder_path_agrees_when_conclusive(tmp_path):
    from fansim.audit.synthetic import cambered_blade_fan

    good = cambered_blade_fan(stagger_deg=60.0, camber=0.06)  # proof: (omega=+1, pump=-1)
    assert prove_direction(good).verdict == "CONCLUSIVE"
    p = tmp_path / "good.stl"
    good.export(str(p))
    d, crosscheck = resolve_prop_direction(p, external=False)
    assert d == BUILDER_DIRECTION
    assert crosscheck["verdict"] == "CONCLUSIVE"
    assert (crosscheck["omega_sign"], crosscheck["pump_sign"]) == (1, -1)


@pytest.mark.slow
def test_random_prop_flat_designs_never_raise_in_the_builder_path(tmp_path):
    # Regression for the bug this follow-up fixes: a handful of random_prop_flat designs (fixed
    # seed for determinism), most of which are expected to be INCONCLUSIVE under the
    # section-quality guard, must all resolve via the builder path without raising.
    from fansim.geometry import build_impeller, export_stl

    spec = get_prop_spec("fpv_5inch")
    rng = random.Random(12345)
    n_inconclusive = 0
    for i in range(3):
        flat = random_prop_flat(spec, rng)
        blade = blade_params_from_trial_params(spec, flat)
        stl = tmp_path / f"design_{i}.stl"
        export_stl(build_impeller(blade), stl, tolerance=0.02, angular_tolerance=0.1)

        d, crosscheck = resolve_prop_direction(stl, external=False)
        assert d == BUILDER_DIRECTION
        assert crosscheck is not None and crosscheck["verdict"] in ("CONCLUSIVE", "INCONCLUSIVE")
        if crosscheck["verdict"] == "INCONCLUSIVE":
            n_inconclusive += 1
    # Not a hard requirement, but documents why this test exists: this search space routinely
    # produces sections the proof can't read, which is exactly what the builder path must tolerate.
    assert n_inconclusive >= 1


@pytest.mark.slow
@pytest.mark.parametrize("spec_key", ["fpv_5inch", "cine_3inch"])
def test_build_prop_matches_builder_direction_convention(tmp_path, spec_key):
    # The default (non-optimizer) builder geometry should read CONCLUSIVE and agree with
    # BUILDER_DIRECTION outright -- this is the convention BUILDER_DIRECTION documents.
    from fansim.propeller.geometry import build_prop

    spec = get_prop_spec(spec_key)
    stl = tmp_path / "prop.stl"
    build_prop(spec, stl)
    mesh = trimesh.load(str(stl), force="mesh")
    p = prove_direction(mesh)
    assert p.verdict == "CONCLUSIVE", p.note
    assert (p.omega_sign, p.pump_sign) == (1, -1)
    assert p.chirality == BUILDER_DIRECTION.chirality
