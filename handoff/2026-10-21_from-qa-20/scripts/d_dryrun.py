"""QA r20 D (PREREG_R20 2c4380d): README install-guide dry run as throwaway user fsdry, empty HOME, clean env.
Each step runs in a fresh login shell (= 'restart the shell'). Resumable: finished steps in d_steps.jsonl are skipped.
Run as box (uses sudo -u fsdry). Usage: python d_dryrun.py <workdir_file> <out.jsonl> <logdir>"""
import json, os, subprocess, sys, time, re, urllib.request

U = "fsdry"; HOME = f"/home/{U}"
OUT, LOG = sys.argv[2], sys.argv[3]
WD = open(sys.argv[1]).read().strip()  # mktemp dir owned by fsdry (made by run_d.sh)


def sh(cmd, timeout=3600):
    full = ["sudo", "-u", U, "env", "-i", f"HOME={HOME}", "PATH=/usr/bin:/bin", "TERM=dumb", "LANG=C.UTF-8",
            "bash", "-lc", cmd]
    t0 = time.monotonic()
    try:
        r = subprocess.run(full, capture_output=True, text=True, timeout=timeout, cwd="/tmp")
        rc, o = r.returncode, r.stdout + r.stderr
    except subprocess.TimeoutExpired as e:
        rc, o = "timeout", (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else str(e.stdout)
    return rc, o, round(time.monotonic() - t0, 1)


def done():
    return {json.loads(l)["step"] for l in open(OUT)} if os.path.exists(OUT) else set()


def rec(step, cmd, rc, o, dt, **kw):
    open(f"{LOG}/{step}.log", "w").write(f"$ {cmd}\n{o}")
    r = dict(step=step, cmd=cmd, rc=rc, secs=dt, tail=o[-600:], **kw)
    with open(OUT, "a") as f: f.write(json.dumps(r) + "\n")
    print(step, rc, dt, flush=True)


STEPS = [
    ("0_pre_uv_absent", "command -v uv; echo PATH=$PATH; python3 --version; git --version; curl --version | head -1; command -v docker || echo NO_DOCKER"),
    ("1a_install_uv", "curl -LsSf https://astral.sh/uv/install.sh | sh"),
    ("1b_uv_version_new_shell", "command -v uv; uv --version"),
    ("2a_clone", f"cd {WD} && git clone /tmp/fsdry_src/fansim.bundle && ls"),
    ("2b_cd_Fan_simulator", f"cd {WD} && cd Fan-simulator"),
    ("2c_uv_sync_dev", f"cd {WD}/fansim && git log -1 --format='%h %d' && uv sync --extra dev"),
    ("2d_python_version", f"cd {WD}/fansim && uv run python --version && uv run python -c 'import cadquery, OCP; print(cadquery.__version__)'"),
    ("3_docker_would_run", "command -v docker || echo 'docker: command not found'; getent group docker || echo 'no docker group'"),
    ("4b_optional_ui_test", f"cd {WD}/fansim && uv run python -m pytest tests/test_ui_says_what_it_does.py -q 2>&1 | tail -15"),
]


def cockpit():
    cmd = f"cd {WD}/fansim && exec uv run python scripts/cockpit.py --run runs/opt_mountable --reload"
    full = ["sudo", "-u", U, "env", "-i", f"HOME={HOME}", "PATH=/usr/bin:/bin", "TERM=dumb", "LANG=C.UTF-8", "bash", "-lc", cmd]
    t0 = time.monotonic(); logf = f"{LOG}/4a_cockpit.log"
    p = subprocess.Popen(full, stdout=open(logf, "w"), stderr=subprocess.STDOUT, start_new_session=True, cwd="/tmp")
    url, code, t_url, t_ok = None, None, None, None
    while time.monotonic() - t0 < 300 and p.poll() is None:
        time.sleep(3); txt = open(logf, errors="replace").read()
        if url is None:
            m = re.search(r"https?://(?:localhost|127\.0\.0\.1|0\.0\.0\.0)[:\d]*/?\S*", txt)
            if m: url, t_url = m.group(0).rstrip(".,)"), round(time.monotonic() - t0, 1)
        if url:
            try:
                code = urllib.request.urlopen(url.replace("0.0.0.0", "127.0.0.1"), timeout=10).status; t_ok = round(time.monotonic() - t0, 1); break
            except Exception as e:  # noqa
                code = f"{type(e).__name__}: {e}"[:200]
    alive = p.poll() is None
    time.sleep(2)
    subprocess.run(["sudo", "pkill", "-u", U, "-f", "cockpit.py"]); time.sleep(3)
    subprocess.run(["sudo", "pkill", "-9", "-u", U, "-f", "cockpit.py"])
    o = open(logf, errors="replace").read()
    with open(OUT, "a") as f:
        f.write(json.dumps(dict(step="4a_cockpit", cmd=cmd, url=url, t_url=t_url, http=code, t_http=t_ok, alive_at_check=alive,
                                rc=p.poll(), secs=round(time.monotonic() - t0, 1), tail=o[-1500:])) + "\n")
    print("4a_cockpit", url, code, flush=True)


if __name__ == "__main__":
    d = done()
    for step, cmd in STEPS[:7]:
        if step not in d: rec(step, cmd, *sh(cmd))
    if "3_docker_would_run" not in d: rec("3_docker_would_run", STEPS[7][1], *sh(STEPS[7][1]))
    if "4a_cockpit" not in d: cockpit()
    if "4b_optional_ui_test" not in d: rec("4b_optional_ui_test", STEPS[8][1], *sh(STEPS[8][1]))
    ma = int(re.search(r"MemAvailable:\s+(\d+)", open("/proc/meminfo").read()).group(1)) // 1024
    if "4c_full_fast_suite" not in d:
        if ma >= 10240:
            c = f"cd {WD}/fansim && uv run python scripts/pytest_chunks.py --chunks 3 --all -- -m 'not docker and not slow' -q 2>&1 | tail -30"
            rec("4c_full_fast_suite", c, *sh(c, 7200), mem_avail_mb=ma)
        else:
            rec("4c_full_fast_suite", "(not run)", "not_run_memory", f"MemAvailable {ma} MB < 10240 MB", 0.0, mem_avail_mb=ma)
    print("DONE", flush=True)
