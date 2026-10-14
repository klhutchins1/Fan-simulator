"""Round 11 fuse-guard hook. Active when FUSE_CALL_LOG is set.

At check_fuse_memory: n_faces, shrouded, n_blade_faces, VmRSS/VmHWM, MemAvailable.
At os._exit: VmHWM (the worker skips atexit).
"""
from __future__ import annotations

import json
import os
import time

_p = os.environ.get("FUSE_CALL_LOG")
if _p:
    def _status():
        d = {}
        try:
            from fansim.resources import free_ram_bytes, process_peak_rss_bytes, process_rss_bytes
            rss, peak = process_rss_bytes(), process_peak_rss_bytes()
            d["rss_bytes"], d["peak_bytes"] = rss, peak
            d["VmRSS"] = None if rss is None else rss // 1024  # kB, same as hook_c
            d["VmHWM"] = None if peak is None else peak // 1024
            avail = free_ram_bytes()
            d["MemAvailable"] = None if avail is None else avail // 1024
        except Exception:
            for line in open("/proc/self/status", encoding="ascii"):
                k, _, v = line.partition(":")
                if k in ("VmRSS", "VmHWM"):
                    d[k] = int(v.split()[0])  # kB
            for line in open("/proc/meminfo", encoding="ascii"):
                if line.startswith("MemAvailable:"):
                    d["MemAvailable"] = int(line.split()[1])
                    break
        return d

    def _w(rec):
        try:
            with open(_p, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec) + "\n")
        except OSError:
            pass

    _called = [False]

    def _exit_rec(code=None):
        if _called[0]:
            _w({"ev": "exit", "pid": os.getpid(), "code": code, "mono": time.monotonic(), **_status()})
            _called[0] = False

    _orig_exit = os._exit

    def _exit(code):
        _exit_rec(code)
        _orig_exit(code)

    os._exit = _exit
    try:
        import fansim.resources as _r

        _orig = _r.check_fuse_memory

        def _wrap(n_faces, *a, **k):
            _called[0] = True
            _w({
                "ev": "call", "pid": os.getpid(), "n_faces": int(n_faces),
                "shrouded": bool(k.get("shrouded")),
                "n_blade_faces": k.get("n_blade_faces"),
                "mono": time.monotonic(), **_status(),
            })
            return _orig(n_faces, *a, **k)

        _r.check_fuse_memory = _wrap
    except Exception:
        pass
