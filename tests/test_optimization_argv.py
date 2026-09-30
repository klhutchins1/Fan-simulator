import sys

from fansim.optimize.cli_argv import optimization_argv


def _argv(**kw):
    args = dict(
        trials=8, out="runs/x", fan_model="a12x25", preset="legacy",
        refine_op=False, shroud=False, bem_floor=0, gp_floor=0,
    )
    args.update(kw)
    return optimization_argv(**args)


def test_argv_starts_with_interpreter_and_script():
    argv = _argv()
    assert argv[0] == sys.executable
    assert "run_optimization.py" in argv[1].replace("\\", "/")


def test_legacy_omits_preset():
    assert "--preset" not in _argv(preset="legacy")


def test_case_includes_preset():
    argv = _argv(preset="case")
    assert argv[argv.index("--preset") + 1] == "case"


def test_refine_op_flag():
    assert "--refine-op" not in _argv(refine_op=False)
    assert "--refine-op" in _argv(refine_op=True)


def test_shroud_flag():
    assert "--shroud" not in _argv(shroud=False)
    assert "--shroud" in _argv(shroud=True)


def test_bem_floor_omitted_when_zero():
    assert "--bem-prescreen" not in _argv(bem_floor=0)
    argv = _argv(bem_floor=32)
    assert argv[argv.index("--bem-prescreen") + 1] == "32"


def test_gp_floor_omitted_when_zero():
    assert "--surrogate-prescreen" not in _argv(gp_floor=0)
    argv = _argv(gp_floor=40)
    assert argv[argv.index("--surrogate-prescreen") + 1] == "40"


def test_gp_boost_only_with_gp_floor():
    assert "--surrogate-boost" not in _argv(gp_floor=0, gp_boost=True)
    assert "--surrogate-boost" not in _argv(gp_floor=40, gp_boost=False)
    assert "--surrogate-boost" in _argv(gp_floor=40, gp_boost=True)


def test_gp_nn_only_with_gp_floor():
    assert "--surrogate-nn" not in _argv(gp_floor=0, gp_nn=True)
    assert "--surrogate-nn" not in _argv(gp_floor=40, gp_nn=False)
    assert "--surrogate-nn" in _argv(gp_floor=40, gp_nn=True)


def test_surrogate_guided_flag():
    assert "--surrogate-guided" not in _argv()
    assert "--surrogate-guided" in _argv(surrogate_guided=True)
    # Boost/NN may appear with guided even when gp_floor is 0.
    argv = _argv(surrogate_guided=True, gp_boost=True, gp_nn=True)
    assert "--surrogate-guided" in argv
    assert "--surrogate-boost" in argv
    assert "--surrogate-nn" in argv


def test_search_rpm_and_material_flags():
    assert "--search-rpm" not in _argv()
    argv = _argv(search_rpm=True, rpm_min=500, rpm_max=1800, material="PLA", wall_ks_mm=0.1)
    assert "--search-rpm" in argv
    assert argv[argv.index("--rpm-min") + 1] == "500"
    assert argv[argv.index("--rpm-max") + 1] == "1800"
    assert argv[argv.index("--material") + 1] == "PLA"
    assert argv[argv.index("--wall-ks-mm") + 1] == "0.1"

    assert "--study-name" not in _argv()
    from fansim.optimize.cli_argv import optimization_argv
    argv = optimization_argv(
        trials=8, out="runs/x", fan_model="a12x25", preset="legacy",
        refine_op=False, shroud=False, bem_floor=0, gp_floor=0, study_name="fansim")
    assert argv[argv.index("--study-name") + 1] == "fansim"


def test_opt_out_path_new_vs_resume():
    from fansim.optimize.cli_argv import opt_out_path
    from pathlib import Path
    p = opt_out_path(resume=False, run_dir=Path("runs/opened"), stamp="20260101-120000")
    assert p == Path("runs/cockpit_opt_20260101-120000")
    assert opt_out_path(resume=True, run_dir=Path("runs/opened")) == Path("runs/opened")


def test_merge_opt_designs_offsets_and_skips_duplicates():
    from fansim.cockpit.data import Design
    from fansim.optimize.cli_argv import OPT_TRIAL_OFFSET, merge_opt_designs

    d = Design(trial=3, params={"n_blades": 7},
               objectives={"cfm_free": 10, "cfm_load": 5, "efficiency": 1},
               feasible=True, is_pareto=False, stl_path=None)
    keys: set = set()
    first = merge_opt_designs([d], source_run="cockpit_opt_x", existing_keys=keys)
    assert len(first) == 1
    assert first[0].trial == 3 + OPT_TRIAL_OFFSET
    assert first[0].extra["orig_trial"] == 3
    assert first[0].extra["source_run"] == "cockpit_opt_x"
    second = merge_opt_designs([d], source_run="cockpit_opt_x", existing_keys=keys)
    assert second == []


def test_merge_opt_designs_skips_infeasible_sentinels():
    from fansim.cockpit.data import Design
    from fansim.optimize.cli_argv import merge_opt_designs

    bad = Design(
        trial=24, params={"n_blades": 10},
        objectives={"cfm_free": -1e6, "cfm_load": -1e6, "efficiency": -1e6},
        feasible=False, is_pareto=False, stl_path=None, reason="resonance",
    )
    good = Design(
        trial=25, params={"n_blades": 7},
        objectives={"cfm_free": 40.0, "cfm_load": 20.0, "efficiency": 15.0},
        feasible=True, is_pareto=False, stl_path=None,
    )
    keys: set = set()
    out = merge_opt_designs([bad, good], source_run="cockpit_opt_y", existing_keys=keys)
    assert len(out) == 1
    assert out[0].extra["orig_trial"] == 25
    assert ("cockpit_opt_y", 24) in keys  # remembered so we don't retry


def test_geometry_stamp_flags():
    from fansim.optimize.cli_argv import optimization_argv
    base = dict(trials=8, out="runs/x", fan_model="a12x25", preset="legacy",
                refine_op=False, shroud=False, bem_floor=0, gp_floor=0)
    assert "--stator" not in optimization_argv(**base)
    assert "--stator" in optimization_argv(**base, stator=True)
    assert "--stator-stack" in optimization_argv(**base, stator_stack=True)
    assert "--stator" not in optimization_argv(**base, stator_stack=True)
    try:
        optimization_argv(**base, stator=True, stator_stack=True)
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "cannot combine" in str(exc)
    assert "--sickle" in optimization_argv(**base, sickle=True)
    assert "--stepped-inlet" in optimization_argv(**base, stepped_inlet=True)
    assert "--notched-tips" in optimization_argv(**base, notched_tips=True)


def test_always_guided_mountable_and_fan_model():
    argv = _argv()
    assert argv[argv.index("--space") + 1] == "guided"
    assert "--mountable" in argv
    assert argv[argv.index("--fan-model") + 1] == "a12x25"
    assert argv[argv.index("--trials") + 1] == "8"
    assert argv[argv.index("--out") + 1] == "runs/x"
    assert "--features" not in argv
