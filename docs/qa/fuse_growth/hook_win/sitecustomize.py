"""QA 27.1 Windows hook. Active when FUSE_CALL_LOG is set.

At check_fuse_memory: n_faces, shrouded, n_blade_faces, WorkingSet, PeakWorkingSet, AvailPhys.
At os._exit: PeakWorkingSet (the worker skips atexit).
"""
from __future__ import annotations

import json
import os
import time

_p = os.environ.get("FUSE_CALL_LOG")
if _p:
    def _status():
        from fansim.resources import free_ram_bytes, process_peak_rss_bytes, process_rss_bytes

        return {
            "ws": process_rss_bytes(),
            "peak_ws": process_peak_rss_bytes(),
            "avail": free_ram_bytes(),
        }

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
