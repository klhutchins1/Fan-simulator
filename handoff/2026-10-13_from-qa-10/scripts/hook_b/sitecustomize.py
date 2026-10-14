"""QA r10 hooks (PREREG_R10 26aa359). Test instrumentation only; no source change.
STRESS_FACES_LOG: round-7 K12 hook (n_faces passed to check_fuse_memory).
QA_FUSE_LOG: wraps fansim.geometry.blade.fuse_many, logging per call: n tools, one-by-one tier flag, mono s, len(Solids())."""
import json, os, time
_p = os.environ.get("STRESS_FACES_LOG")
if _p:
    try:
        import fansim.resources as _r
        _orig = _r.check_fuse_memory
        def _wrap(n_faces, *a, **k):
            try:
                with open(_p, "a") as f: f.write(f"{int(n_faces)}\n")
            except OSError: pass
            return _orig(n_faces, *a, **k)
        _r.check_fuse_memory = _wrap
    except Exception: pass
_q = os.environ.get("QA_FUSE_LOG")
if _q:
    try:
        import fansim.geometry.blade as _b
        _fm = _b.fuse_many
        def _fuse_many(base, tools, *, tier=None):
            from fansim.resources import current_tier
            t = tier or current_tier(); t0 = time.monotonic(); out = _fm(base, tools, tier=tier)
            try: ns = len(out.Solids())
            except Exception: ns = None
            try:
                with open(_q, "a") as f: f.write(json.dumps({"n_tools": len(tools), "one_by_one": bool(t.fuse_one_blade_at_a_time), "s": round(time.monotonic() - t0, 2), "solids": ns}) + "\n")
            except OSError: pass
            return out
        _b.fuse_many = _fuse_many
    except Exception: pass
