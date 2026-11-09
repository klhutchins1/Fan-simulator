# QA r26-qa68 subprocess mock: Docker 'present', CFD verify closure aborts if ever called. No Docker/CFD runs.
import os
if os.environ.get("QA68_MOCK") == "1":
    import fansim.cfd.runner as runner
    import fansim.optimize.surrogate_search as ss
    runner.image_available = lambda: True
    _real = ss.make_cfd_verify_fn
    def guarded(*a, **k):
        _real(*a, **k)
        def fn(*a, **k):
            raise SystemExit("ABORT: CFD verify called")
        return fn
    ss.make_cfd_verify_fn = guarded
