"""QA r18 A diagnostic (post-hoc, report only): why M1 (section points at n_span/n_chord) differs from M2 (built solid)."""
import json, math, sys
sys.path.insert(0, "/workspace/fansim/repo-r17/handoff/2026-10-19_from-qa-17/scripts")
import p2_built as P2
from c_common import export_hub
from fansim.geometry import blade as B
from fansim.geometry.chord_realisation import prepare_loft_chords
P = {json.loads(l)["id"]: json.loads(l) for l in open(sys.argv[1])}
out = []
for i in sys.argv[2].split(","):
    p, d = export_hub(P2.params_of(P[i])); zf = B._hub_axial_range(p)[0]
    pr = prepare_loft_chords(p)
    ns = pr.features.required_span_sections(pr.n_span); nsb = max(ns, 30) if len(pr.stations) > 3 else ns
    nc = pr.features.required_chord_points(pr.n_chord)
    z1, rf1 = P2.sec_zmin(pr, B)
    import dataclasses
    z2, rf2 = P2.sec_zmin(dataclasses.replace(pr, n_span=nsb, n_chord=nc), B)
    s = B.build_blade_solid(p); v = min(s.Vertices(), key=lambda v: v.Z)
    out.append(dict(id=i, n_span=pr.n_span, n_span_build=nsb, n_chord=pr.n_chord, n_chord_build=nc, n_st=len(pr.stations),
                    M1=zf - z1, M1_rf=rf1, M1_buildres=zf - z2, M1b_rf=rf2, M2=zf - v.Z, r_low=math.hypot(v.X, v.Y), tip=pr.tip_radius))
    print(out[-1], flush=True)
json.dump(out, open(sys.argv[3], "w"), indent=1)
