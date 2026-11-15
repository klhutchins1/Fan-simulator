"""QA r26 follow-up (PREREG_R26_QA68 491f0d2): QA-68 behaviour probe on master 419df2e.
In-process run_optimization.main() + one real subprocess. Docker presence mocked; any CFD verify call aborts.
Usage (cwd = snapshot, its venv): python qa68_probe.py <repo> <out.json>"""
import contextlib, importlib.util, io, json, os, subprocess, sys, tempfile, traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
repo, OUT = Path(sys.argv[1]).resolve(), sys.argv[2]
import fansim
assert fansim.__file__.startswith(str(repo)), fansim.__file__
import fansim.cfd.runner as runner, fansim.optimize.surrogate_search as ss
from a_qa66_probe_catalog import catalog  # noqa
spec = importlib.util.spec_from_file_location("run_opt", repo / "scripts/run_optimization.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
cfd_calls = {"n": 0}
_real = ss.make_cfd_verify_fn
def guarded(*a, **k):
    _real(*a, **k)
    def fn(*a, **k):
        cfd_calls["n"] += 1; raise SystemExit("ABORT: CFD verify called")
    return fn
ss.make_cfd_verify_fn = guarded
R = {"head": subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()}
def case(tag, cli_docker, lib_docker, rows):
    tmp = Path(tempfile.mkdtemp(prefix=f"qa68_{tag}_")); out = tmp / "opt"
    db = catalog(tmp, rows) if rows else tmp / "missing.db"
    m.image_available = lambda: cli_docker; runner.image_available = lambda: lib_docker
    sys.argv = ["run_optimization.py", "--surrogate-guided", "--verify-cfd", "--out", str(out), "--surrogate-db", str(db)]
    buf = io.StringIO(); r = {}
    try:
        with contextlib.redirect_stdout(buf): r["returned"] = m.main()
    except BaseException as e:
        r["uncaught"] = f"{type(e).__name__}: {str(e)[:160]}"; r["tb_tail"] = traceback.format_exc().splitlines()[-2:]
    s = buf.getvalue(); r["stdout_tail"] = s.strip().splitlines()[-1:] ; r["traceback_in_stdout"] = "Traceback" in s
    r["json_written"] = (out / "surrogate_guided.json").exists(); r["out_dir_created"] = out.exists()
    R[tag] = r
case("c1_no_catalog", True, True, 0)
case("c2_catalog_7rows", True, True, 7)
case("c3_docker_absent_cli_guard", False, False, 0)
case("c3b_docker_absent_library_refusal", True, False, 0)   # CLI guard passes, library raises Docker RuntimeError
case("ctrl_catalog_8rows_reaches_verify", True, True, 8)    # control: past refusal, must hit the CFD guard
R["cfd_verify_calls_total"] = cfd_calls["n"]
# rule 5: real subprocess, sitecustomize mock
tmp = Path(tempfile.mkdtemp(prefix="qa68_sub_"))
env = dict(os.environ, QA68_MOCK="1", PYTHONPATH=f"/workspace/fansim/qa_r26_qa68/scripts/sitemock:{repo}")
p = subprocess.run([sys.executable, "scripts/run_optimization.py", "--surrogate-guided", "--verify-cfd", "--out", str(tmp / "opt"),
                    "--surrogate-db", str(tmp / "missing.db")], cwd=repo, env=env, capture_output=True, text=True, timeout=300)
R["c5_subprocess_no_catalog"] = {"exit": p.returncode, "traceback_in_stderr": "Traceback" in p.stderr,
    "stderr_tail": p.stderr.strip().splitlines()[-2:], "stdout_tail": p.stdout.strip().splitlines()[-2:]}
json.dump(R, open(OUT, "w"), indent=1, ensure_ascii=False); print(json.dumps(R, indent=1, ensure_ascii=False))
