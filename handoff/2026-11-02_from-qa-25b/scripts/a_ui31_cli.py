"""QA r25 A UI-31 b/c/d (PREREG_R25 b7e7574): cockpit argv seam + CLI guard, pure calls + source read. run_optimization.py NOT executed.
Usage: QA_REPO=<repo> <repo>/.venv/bin/python a_ui31_cli.py <out.json>"""
import json, os, re, sys
from pathlib import Path
from types import SimpleNamespace
REPO = Path(os.environ["QA_REPO"])
import fansim; assert fansim.__file__.startswith(str(REPO)), fansim.__file__
R = {}
src = (REPO / "fansim/cockpit/fan_optimize.py").read_text()
R["b_state_wired_lines"] = [f"fan_optimize.py:{i}: {l.strip()}" for i, l in enumerate(src.splitlines(), 1) if "surrogate_guided" in l]
try:
    from fansim.cockpit.fan_optimize import cockpit_optimization_argv
    st = SimpleNamespace(fan_model="a12x25", assess_preset="case", assess_refine_op=False, opt_shroud=False, opt_bem=False,
        opt_gp=True, opt_gp_boost=True, opt_gp_nn=True, opt_surrogate_guided=True, opt_stator=False, opt_stator_stack=False,
        opt_sickle=False, opt_stepped=False, opt_notched=False, assess_wall_ks=False, assess_material="PETG")
    argv = cockpit_optimization_argv(st, trials=8, out="runs/x", resume_study=None, search_rpm=False, rpm_min=None, rpm_max=None)
    R["b_seam"] = "cockpit_optimization_argv"
    R["b_argv_with_state_on"] = argv
    R["b_argv_has_surrogate_guided"] = "--surrogate-guided" in argv
except ImportError as e:
    R["b_seam"] = f"absent ({e})"
    R["b_argv_has_surrogate_guided"] = "by code reading: " + ("state wired" if any("bool(state.opt_surrogate_guided)" in l for l in R["b_state_wired_lines"]) else "not wired")
from fansim.optimize import cli_argv
g = getattr(cli_argv, "surrogate_guided_cli_error", None)
R["c_guard_fn"] = "present" if g else "absent"
if g:
    R["c_guard_table"] = {f"verify={v},stub={s}": g(guided=True, verify_cfd=v, stub_labels=s) for v in (False, True) for s in (False, True)}
ro = (REPO / "scripts/run_optimization.py").read_text().splitlines()
R["c_main_lines"] = [f"run_optimization.py:{i}: {l.strip()}" for i, l in enumerate(ro, 1)
                     if re.search(r"surrogate_guided_cli_error|stub.labels|return 2|synthetic labels", l)]
rs = REPO / "scripts/run_surrogate_search.py"
R["wrapper_lines"] = [f"run_surrogate_search.py:{i}: {l.strip()}" for i, l in enumerate(rs.read_text().splitlines(), 1) if "stub-labels" in l or "verify-cfd" in l]
R["d_stub_flag_in_parser"] = any("--stub-labels" in l for l in ro)
ss = (REPO / "fansim/optimize/surrogate_search.py").read_text()
R["d_stub_stamp_in_outputs"] = [f"surrogate_search.py:{i}: {l.strip()[:120]}" for i, l in enumerate(ss.splitlines(), 1) if re.search(r"synthetic labels|stub_labels|label_source|\"stub\"", l)]
tests = REPO / "tests"
R["e_tests_mentioning_stub_labels_or_guard"] = sorted({p.name for p in tests.glob("test_*.py") if re.search(r"stub.labels|surrogate_guided_cli_error|cockpit_optimization_argv", p.read_text())})
R["e_tests_calling_run_optimization_main"] = sorted({p.name for p in tests.glob("test_*.py") if re.search(r"run_optimization", p.read_text()) and re.search(r"main\(|build_parser|subprocess", p.read_text())})
json.dump(R, open(sys.argv[1], "w"), indent=1); print(json.dumps(R, indent=1))
