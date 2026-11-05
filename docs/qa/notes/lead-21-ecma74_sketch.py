"""Lead 21 sketch: ECMA-74 cl. 7 / Annex B.1 hemisphere sound power, our own implementation (no ECMA text copied).
The core maths are the standard engineering-method relations ECMA-74 delegates to ISO 3744:
  Lp_bar = 10 lg( (1/N) sum 10^(0.1 Lp_i) )        energy average over the N positions
  K1     = -10 lg(1 - 10^(-0.1 dL)),  dL = Lp_bar(source+bg) - Lp_bar(bg); valid only if dL >= 6 dB (ECMA/ISO 3744 engineering)
  LW     = Lp_bar - K1 - K2 + 10 lg(S/S0),  S = 2 pi r^2 (hemisphere over reflecting plane), S0 = 1 m^2
  K2 (room) <= 2 dB per ECMA-74 7.3.1; at home use a reference source or report K2 = assumed.
Positions: the 10-point fixed array for tonal sources (ECMA-74 Table B.1, coordinates as x/r, y/r, z/r).
Radius: 1 m preferred; 0.5 m allowed for small quiet sources if r >= 2 x characteristic source size (low-freq limit ~172 Hz).
Run: python3 ecma74_sketch.py out.json
"""
import json, math, random, sys

POS10 = [(0.16, -0.96, 0.22), (0.78, -0.60, 0.20), (0.78, 0.55, 0.31), (0.16, 0.90, 0.41), (-0.83, 0.32, 0.45),
         (-0.83, -0.40, 0.38), (-0.26, -0.65, 0.71), (0.74, -0.07, 0.67), (-0.26, 0.50, 0.83), (0.10, -0.10, 0.99)]

def energy_mean(levels):
    return 10 * math.log10(sum(10 ** (0.1 * L) for L in levels) / len(levels))

def k1(lp_total, lp_bg):
    dl = lp_total - lp_bg
    if dl < 6.0:
        return None, dl            # invalid: background too close (report as upper bound only)
    return -10 * math.log10(1 - 10 ** (-0.1 * dl)), dl

def sound_power(lp_src_bg, lp_bg, r_m, k2=0.0):
    """lp_src_bg, lp_bg: lists of A-weighted levels at the same positions. Returns dict."""
    L, B = energy_mean(lp_src_bg), energy_mean(lp_bg)
    K1, dl = k1(L, B)
    S = 2 * math.pi * r_m ** 2
    lw = None if K1 is None else L - K1 - k2 + 10 * math.log10(S / 1.0)
    upper = L + 10 * math.log10(S)    # if invalid: LW is at most this
    return dict(Lp_bar=round(L, 2), Lbg_bar=round(B, 2), dL=round(dl, 2), K1=None if K1 is None else round(K1, 2),
                K2=k2, S=round(S, 3), LWA=None if lw is None else round(lw, 2), LWA_upper=round(upper, 2), valid=K1 is not None)

def positions(r_m):
    return [(round(x * r_m, 3), round(y * r_m, 3), round(z * r_m, 3)) for x, y, z in POS10]

def synth(lw_true, r_m, bg_dba, directivity_db=1.5, mic_sd=1.0, mic_bias=0.0, mic_floor=None, seed=0):
    """Ideal hemispherical source of sound power lw_true over a reflecting plane, with small directivity,
    per-reading scatter (mic_sd), a calibration bias, background bg_dba and optional mic self-noise."""
    rnd = random.Random(seed)
    lp0 = lw_true - 10 * math.log10(2 * math.pi * r_m ** 2)
    def add(*ls): return 10 * math.log10(sum(10 ** (0.1 * l) for l in ls if l is not None))
    src = [lp0 + directivity_db * (z - 0.5) * 2 for _, _, z in POS10]        # louder on axis (z up = fan axis)
    floor = [bg_dba + rnd.gauss(0, 0.5) for _ in POS10]
    if mic_floor is not None: floor = [add(f, mic_floor) for f in floor]
    tot = [add(s, f) + rnd.gauss(0, mic_sd) + mic_bias for s, f in zip(src, floor)]
    bg = [f + rnd.gauss(0, mic_sd) + mic_bias for f in floor]
    return tot, bg

if __name__ == "__main__":
    out = {"positions_r1m": positions(1.0), "positions_r0.5m": positions(0.5), "cases": []}
    LW = 33.6   # A12x25 at 2000 rpm per lead-12 conversion (22.6 dB(A) + 10 lg 4pi), itself +-3 dB
    for name, r, bg, floor, bias in [
        ("ideal lab (bg 10 dB(A)), r 1 m", 1.0, 10, None, 0.0),
        ("quiet room night bg 20 dB(A), USB meas. mic (floor 18), r 0.5 m", 0.5, 20, 18, 0.0),
        ("quiet room bg 25 dB(A), USB mic, r 0.5 m", 0.5, 25, 18, 0.0),
        ("quiet room bg 20, phone MEMS mic (floor ~30), r 0.5 m", 0.5, 20, 30, 0.0),
        ("quiet room bg 20, USB mic, r 1 m", 1.0, 20, 18, 0.0),
        ("as case 2 but +2 dB uncalibrated mic bias", 0.5, 20, 18, 2.0),
    ]:
        tot, bgl = synth(LW, r, bg, mic_floor=floor, mic_bias=bias)
        res = sound_power(tot, bgl, r)
        res.update(case=name, LW_true=LW)
        out["cases"].append(res)
    # louder test point: same fan at higher rpm is not available (2000 rpm max); a 3000 rpm print would be ~+9 dB (50 lg n)
    out["note_rpm_scaling_db_3000_vs_2000"] = round(50 * math.log10(3000 / 2000), 1)
    json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else "out.json", "w"), indent=1)
    for c in out["cases"]:
        print(f"{c['case']:<70} Lp_bar {c['Lp_bar']:5.1f} bg {c['Lbg_bar']:5.1f} dL {c['dL']:5.1f} -> LWA {c['LWA']} (upper {c['LWA_upper']}) true {LW}")
