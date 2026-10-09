"""How often does the prop BEMT fixed-point fail to converge? Sweep registry props x rpm x forward speed."""
import sys, os, itertools; sys.path.insert(0, os.getcwd())
from fansim.prop_spec import _REGISTRY
from fansim.propeller.bemt import analyze
from fansim.propeller.geometry import prop_blade_params
n = bad = 0; ex = []
for name, spec in _REGISTRY.items():
    try:
        p = prop_blade_params(spec)
    except Exception as e:
        print("skip", name, type(e).__name__); continue
    pitch_v = spec.pitch_mm / 1000.0
    for rpm in (2000, 5000, 9000, 15000, 25000):
        for J in (0.0, 0.3, 0.6, 0.9, 1.1, 1.4):   # advance ratio up to windmill
            v = J * rpm / 60.0 * spec.diameter_mm / 1000.0
            r = analyze(p, rpm, v_forward=v); n += 1
            if not r.converged:
                bad += 1; ex.append((name, rpm, J))
print("runs", n, "unconverged", bad, ex[:8])
