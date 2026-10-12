"""QA r8 Task C hook. Active only when FUSE_CALL_LOG is set. Records, at check_fuse_memory(n_faces):
n_faces, own VmRSS/VmHWM, MemAvailable, monotonic; and the worker's VmHWM just before it exits
(wraps os._exit, since the build worker leaves via os._exit(0), and also registers atexit).
Instrumentation only; calls the original unchanged."""
import os, json, time, atexit
_p = os.environ.get("FUSE_CALL_LOG")
if _p:
    def _status():
        d = {}
        for line in open("/proc/self/status"):
            k, _, v = line.partition(":")
            if k in ("VmRSS", "VmHWM"): d[k] = int(v.split()[0])
        for line in open("/proc/meminfo"):
            if line.startswith("MemAvailable"): d["MemAvailable"] = int(line.split()[1])
        return d
    def _w(rec):
        try:
            with open(_p, "a") as f: f.write(json.dumps(rec) + "\n")
        except OSError: pass
    _called = [False]
    def _exit_rec(code=None):
        if _called[0]:
            _w({"ev": "exit", "pid": os.getpid(), "code": code, "mono": time.monotonic(), **_status()})
            _called[0] = False
    atexit.register(_exit_rec)
    _orig_exit = os._exit
    def _exit(code):
        _exit_rec(code); _orig_exit(code)
    os._exit = _exit
    try:
        import fansim.resources as _r
        _orig = _r.check_fuse_memory
        def _wrap(n_faces, *a, **k):
            _called[0] = True
            _w({"ev": "call", "pid": os.getpid(), "n_faces": int(n_faces), "mono": time.monotonic(), **_status()})
            return _orig(n_faces, *a, **k)
        _r.check_fuse_memory = _wrap
    except Exception:
        pass
