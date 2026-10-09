"""Headless B1 timing (QA only): run the cockpit's Preview worker via build_stl_isolated, poll its
progress file every 20 ms, sample the worker tree RSS, then time the parent-side STL load (pyvista)."""
import json, os, sys, threading, time
from fansim.geometry.isolated import build_stl_isolated
from fansim.optimize.search_space import stock_blade_flat
from fansim.fan_spec import get_fan_spec
from dataclasses import asdict

mode = sys.argv[1]
out = os.path.abspath(f"preview_{mode}.stl"); prog = out + ".progress.json"
flat = stock_blade_flat("a12x25")
mount = asdict(get_fan_spec("a12x25").motor_mount) if mode == "cup" else None
events, t0, done = [], time.time(), False

def rss_tree():
    tot = 0
    for d in os.listdir("/proc"):
        if d.isdigit():
            try:
                cmd = open(f"/proc/{d}/cmdline").read()
                if "_build_worker" in cmd:
                    tot += int([l for l in open(f"/proc/{d}/status") if l.startswith("VmRSS")][0].split()[1]) // 1024
            except Exception: pass
    return tot

def poll():
    last, peak, k = None, 0, 0
    while not done:
        try: p = open(prog).read()
        except OSError: p = None
        if p != last:
            events.append((round(time.time() - t0, 2), p)); last = p
        k += 1
        if k % 25 == 0: peak = max(peak, rss_tree())
        time.sleep(0.02)
    events.append(("worker_peak_rss_mb", peak))

th = threading.Thread(target=poll); th.start()
build_stl_isolated(flat, {}, out, timeout=600, preview=(mount is None), motor_mount=mount, progress_path=prog)
t_done = time.time() - t0; done = True; th.join()
for e in events: print(e)
print("worker done at", round(t_done, 2), "s; STL MB", round(os.path.getsize(out) / 1e6, 1))
import pyvista as pv
t = time.time(); m = pv.read(out); print("pv.read", round(time.time() - t, 2), "s,", m.n_cells, "cells")
