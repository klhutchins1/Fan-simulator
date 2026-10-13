"""QA r7 stress K12 hook (PREREG amendment 8). Only active when STRESS_FACES_LOG is set.
Wraps fansim.resources.check_fuse_memory to record the n_faces fuse_impeller passes, then calls
the original unchanged. Test instrumentation only; no source change."""
import os

_p = os.environ.get("STRESS_FACES_LOG")
if _p:
    try:
        import fansim.resources as _r

        _orig = _r.check_fuse_memory

        def _wrap(n_faces, *a, **k):
            try:
                with open(_p, "a") as f:
                    f.write(f"{int(n_faces)}\n")
            except OSError:
                pass
            return _orig(n_faces, *a, **k)

        _r.check_fuse_memory = _wrap
    except Exception:  # noqa: BLE001
        pass
