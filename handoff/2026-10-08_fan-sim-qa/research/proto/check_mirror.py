import sys, os; sys.path.insert(0, "/workspace/fansim/research/proto"); sys.path.insert(0, os.getcwd())
import bem_variants as V, cases as C
from fansim.fan_bem import pq_curve
for n, p in C.cases().items():
    a = pq_curve(p, 2000.0); b = V.pq_curve(p, 2000.0, V.Opts())
    same = [x.dp_static_pa for x in a.points] == [x.dp_static_pa for x in b.points]
    print(f"{n:12s} proj free {a.free_delivery_cfm:6} shut {a.shutoff_dp_pa:6} eff {a.peak_efficiency:5} conv {a.converged} | mirror free {b.free_delivery_cfm} shut {b.shutoff_dp_pa} same_curve {same}")
