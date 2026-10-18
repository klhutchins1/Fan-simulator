"""QA r14 Tasks A2-b and A3 (PREREG_R14 586bbe9). Launches the cockpit from run_r14 on :8090, drives it with headless
Chrome (Playwright, 1366x768), then (A3) SIGKILLs the cockpit mid-Export and watches the export worker.
Usage: pwvenv/bin/python a2b_a3.py <out.json> <screens_dir> [a2|a3|both]"""
import json, os, signal, subprocess, sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright
OUT, SH = Path(sys.argv[1]), Path(sys.argv[2]); WHAT = sys.argv[3] if len(sys.argv) > 3 else "both"
REAP = "--no-reap" not in sys.argv
SH.mkdir(parents=True, exist_ok=True)
RUN = Path("/workspace/fansim/qa/run_r14"); PY = "/workspace/fansim/repo-r9/.venv/bin/python"
EXP = RUN / "exports"; IDX = RUN / "validation/prints/index.jsonl"
R = json.loads(OUT.read_text()) if OUT.exists() else {}
def save(): OUT.write_text(json.dumps(R, indent=1, default=str))
def launch(tag):
    env = dict(os.environ, PYTHONPATH=str(RUN), FANSIM_CACHE_DIR="/workspace/fansim/qa/r14_cache")
    log = open(OUT.parent / f"cockpit_{tag}.log", "w")
    Path("/tmp/qa14_cockpit_run").mkdir(exist_ok=True)
    p = subprocess.Popen([PY, "scripts/cockpit.py", "--run", "/tmp/qa14_cockpit_run", "--port", "8090"], cwd=RUN, env=env,
                         stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    import urllib.request
    t = time.monotonic()
    while time.monotonic() - t < 180:
        try:
            urllib.request.urlopen("http://127.0.0.1:8090/", timeout=2); return p
        except Exception: time.sleep(1)
    raise RuntimeError("cockpit did not start")
def st(pg, k):
    try: return pg.evaluate(f"() => window.trame.state.get('{k}')")
    except Exception as e: return f"ERR {e}"[:120]
def wait_false(pg, k, tmax):
    t = time.monotonic(); seen = False
    while time.monotonic() - t < tmax:
        v = st(pg, k); seen = seen or v is True
        if seen and v is False: return round(time.monotonic() - t, 1)
        if not seen and time.monotonic() - t > 8: return None  # never went busy
        pg.wait_for_timeout(500)
    return "timeout"
def pick(pg, mat):
    """Set the 'Print material' v-select by clicking it (UI); fall back to trame state if the UI path fails."""
    try:
        sel = pg.locator(".v-select", has=pg.locator("label", has_text="Print material")).first
        sel.scroll_into_view_if_needed(timeout=2000); sel.click(timeout=2000); pg.wait_for_timeout(400)
        pg.locator(".v-overlay__content .v-list-item", has_text=mat).filter(has_not_text=mat + "+").first.click(timeout=2000) if mat == "PLA" else \
            pg.locator(".v-overlay__content .v-list-item").filter(has=pg.get_by_text(mat, exact=True)).first.click(timeout=2000)
        pg.wait_for_timeout(500); how = "ui"
    except Exception as e:
        pg.keyboard.press("Escape")
        pg.evaluate(f"() => window.trame.state.set('assess_material', '{mat}')"); pg.wait_for_timeout(500); how = f"state.set ({type(e).__name__})"
    return how, st(pg, "assess_material")
def click_btn(pg, text):
    b = pg.locator(".v-btn", has_text=text).first; b.scroll_into_view_if_needed(); b.click()
def listing():
    return {p.name: p.stat().st_mtime for p in EXP.iterdir()} if EXP.exists() else {}
def nlines(p): return sum(1 for _ in open(p)) if p.exists() else 0
def children(pid):
    out = subprocess.run(["ps", "-eo", "pid,ppid,pgid,args"], capture_output=True, text=True).stdout.splitlines()[1:]
    rows = [l.split(None, 3) for l in out]
    kids, frontier = [], {str(pid)}
    while frontier:
        nxt = {r[0] for r in rows if r[1] in frontier}
        kids += [r for r in rows if r[0] in nxt]; frontier = nxt
    return kids

if WHAT in ("a2", "both"):
    p = launch("a2"); R["a2_cockpit_pid"] = p.pid
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch(channel="chrome", headless=True); pg = b.new_context(viewport={"width": 1366, "height": 768}).new_page()
            pg.goto("http://127.0.0.1:8090/", wait_until="networkidle"); pg.wait_for_timeout(8000)
            R["cold_material"] = st(pg, "assess_material"); R["cold_mode"] = st(pg, "ui_mode")
            # ---- A2-b1: PLA+ -> Preview -> Export
            R["b1_pick"] = pick(pg, "PLA+")
            click_btn(pg, "Preview"); R["b1_preview_s"] = wait_false(pg, "preview_busy", 600)
            R["b1_preview_msg"] = st(pg, "preview_msg"); pg.screenshot(path=str(SH / "a2b1_preview_plaplus.png"))
            before, n0 = listing(), nlines(IDX)
            click_btn(pg, "Export STL"); R["b1_export_s"] = wait_false(pg, "export_busy", 1500)
            R["b1_export_msg"] = st(pg, "export_msg"); pg.screenshot(path=str(SH / "a2b1_export_plaplus.png"))
            after = listing(); R["b1_new_exports"] = sorted(set(after) - set(before))
            R["b1_index_lines"] = [n0, nlines(IDX)]
            R["b1_index_last"] = open(IDX).read().splitlines()[-1] if nlines(IDX) > n0 else None
            # ---- A2-b2: PETG -> Preview, switch to PLA+ while busy; then a control PETG Preview
            R["b2_pick_petg"] = pick(pg, "PETG")
            click_btn(pg, "Preview"); pg.wait_for_timeout(300)
            R["b2_busy_at_switch"] = st(pg, "preview_busy")
            R["b2_pick_plaplus_during"] = pick(pg, "PLA+")
            R["b2_busy_after_switch"] = st(pg, "preview_busy")
            R["b2_preview_s"] = wait_false(pg, "preview_busy", 600) if R["b2_busy_after_switch"] else "already done"
            R["b2_preview_msg"] = st(pg, "preview_msg"); pg.screenshot(path=str(SH / "a2b2_switch_during_preview.png"))
            R["b2_ctrl_pick_petg"] = pick(pg, "PETG")
            click_btn(pg, "Preview"); R["b2_ctrl_s"] = wait_false(pg, "preview_busy", 600)
            R["b2_ctrl_msg"] = st(pg, "preview_msg")
            R["b2_ctrl_pick_plaplus"] = pick(pg, "PLA+")
            click_btn(pg, "Preview"); R["b2_ctrl2_s"] = wait_false(pg, "preview_busy", 600)
            R["b2_ctrl_plaplus_msg"] = st(pg, "preview_msg")
            b.close()
    finally:
        os.killpg(p.pid, signal.SIGTERM); time.sleep(3)
        try: os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError: pass
    save()

if WHAT in ("a3", "both"):
    time.sleep(3)
    p = launch("a3"); R["a3_cockpit_pid"] = p.pid; R["a3_reap"] = REAP
    with sync_playwright() as pw:
        b = pw.chromium.launch(channel="chrome", headless=True); pg = b.new_context(viewport={"width": 1366, "height": 768}).new_page()
        pg.goto("http://127.0.0.1:8090/", wait_until="networkidle"); pg.wait_for_timeout(8000)
        R["a3_material"] = st(pg, "assess_material")
        before, n0 = listing(), nlines(IDX)
        click_btn(pg, "Export STL"); t0 = time.monotonic(); workers = []
        while time.monotonic() - t0 < 120:
            kids = [k for k in children(p.pid) if "python" in k[3] and ("worker" in k[3] or "-c" in k[3] or "isolated" in k[3] or "multiprocessing" in k[3])]
            if kids and not workers: workers = kids; tw = time.monotonic()
            if workers and time.monotonic() - tw >= 10 and time.monotonic() - t0 >= 10: break
            time.sleep(0.25)
        R["a3_children_before_kill"] = children(p.pid); R["a3_workers"] = workers
        R["a3_export_busy_before_kill"] = st(pg, "export_busy")
        wp = [int(w[0]) for w in workers]
        tk = time.monotonic(); os.kill(p.pid, signal.SIGKILL)
        if REAP:  # a terminal shell reaps its child at once; run 1 (no reap) left a zombie launcher
            import threading; threading.Thread(target=p.wait, daemon=True).start()
        gone_at = None; trace = []
        while time.monotonic() - tk < 30:
            alive = [w for w in wp if os.path.exists(f"/proc/{w}") and "zombie" not in open(f"/proc/{w}/status").read().lower()]
            if not trace: R["a3_launcher_state_after_kill"] = (open(f"/proc/{p.pid}/status").read().split("State:")[1].split("\n")[0].strip() if os.path.exists(f"/proc/{p.pid}") else "gone")
            trace.append((round(time.monotonic() - tk, 2), alive))
            if not alive: gone_at = round(time.monotonic() - tk, 2); break
            time.sleep(0.25)
        R["a3_worker_gone_s"] = gone_at; R["a3_trace_tail"] = trace[-5:]
        time.sleep(2)
        after = listing(); new = sorted(set(after) - set(before))
        R["a3_new_entries"] = new; R["a3_new_bare_stl"] = [n for n in new if n.endswith(".stl") and not n.startswith(".")]
        R["a3_index_lines"] = [n0, nlines(IDX)]
        try: b.close()
        except Exception: pass
    try: os.killpg(p.pid, signal.SIGKILL)
    except ProcessLookupError: pass
    R["A3_PASS"] = bool(R["a3_workers"]) and gone_at is not None and gone_at <= 5.0 and not R["a3_new_bare_stl"] \
        and all(n.startswith(".partial-") for n in new)
    save()
print(json.dumps({k: v for k, v in R.items() if not k.endswith("children_before_kill")}, default=str)[:3000])
