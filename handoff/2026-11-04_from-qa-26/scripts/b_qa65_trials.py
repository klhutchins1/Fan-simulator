"""QA r26 B (PREREG_R26 00ed802) rule 3 probe: an Optuna trial with user attr converged=False/True/absent, loaded by
fansim.cockpit.data.load_designs and captioned by score_caption (the fan_trials.py path). No CFD; temp sqlite study.
Also exercises study.py's attr-setting expression on fake ObjectiveResult.raw dicts. Usage: python b_qa65_trials.py out.json"""
import json, sys, tempfile, inspect
from pathlib import Path
import optuna
from fansim.cockpit.data import load_designs
from fansim.cockpit.score_caption import score_caption
from fansim.optimize import study as S
optuna.logging.set_verbosity(optuna.logging.WARNING)
out = Path(tempfile.mkdtemp(prefix="r26_b_"))
st = optuna.create_study(study_name="s", storage=f"sqlite:///{(out/'study.db').as_posix()}", directions=["maximize"] * 3)
cases = {"False": False, "True": True, "absent": None}
for name, c in cases.items():
    t = st.ask()
    t.set_user_attr("feasible", True); t.set_user_attr("reason", ""); t.set_user_attr("n_blades", 7)
    if c is not None: t.set_user_attr("converged", c)
    t.set_user_attr("case", name)
    st.tell(t, [50.0, 30.0, 40.0])
R = {}
for d in load_designs(out):
    cap = score_caption(d.extra)
    R[f"trial{d.trial}"] = {"extra_converged": d.extra.get("converged", "KEY-ABSENT"), "warn": "did not settle" in cap, "caption": cap}
R["shows_only_for_False"] = R["trial0"]["warn"] and not R["trial1"]["warn"] and not R["trial2"]["warn"]
src = inspect.getsource(S.run_study)
R["study_sets_converged_attr"] = 'trial.set_user_attr("converged"' in src
json.dump(R, open(sys.argv[1], "w"), indent=1, ensure_ascii=False); print(json.dumps(R, indent=1, ensure_ascii=False))
