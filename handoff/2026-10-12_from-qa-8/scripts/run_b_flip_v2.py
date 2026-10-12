"""QA r8 Task B, flipped parts v2 (deviation, see RESULTS): the builder's NACA camber line returns a
FLAT section for max_camber <= 0 (fansim/geometry/airfoil.py:102 and :61), so the brief's
"max_camber = -0.03 + bypass validate" builds a flat blade, not a backwards one. v2 wraps
blade.section_loop_2d in THIS process only: for max_camber < 0 it builds the |m| section and mirrors
it across the chord line (y -> -y, order reversed), i.e. a true negative-camber NACA section.
Then runs run_b.py unchanged on the flipped rows of the sample. Usage: run_b_flip_v2.py SAMPLE OUT"""
import json, os, runpy, sys, tempfile
import numpy as np
import fansim.geometry.blade as B
_orig = B.section_loop_2d
def _flip(family, *, max_camber, return_chord_param=False, **kw):
    if max_camber >= 0: return _orig(family, max_camber=max_camber, return_chord_param=return_chord_param, **kw)
    loop, xp = _orig(family, max_camber=-max_camber, return_chord_param=True, **kw)
    loop = np.column_stack([loop[:, 0], -loop[:, 1]])[::-1].copy(); xp = np.asarray(xp)[::-1].copy()
    return (loop, xp) if return_chord_param else loop
B.section_loop_2d = _flip
rows = [l for l in open(sys.argv[1]) if json.loads(l)["cell_sel"] == "flipped"]
tf = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False); tf.writelines(rows); tf.close()
sys.argv = [os.path.join(os.path.dirname(__file__), "run_b.py"), tf.name, sys.argv[2], "--no-refs"]
runpy.run_path(sys.argv[0], run_name="__main__")
