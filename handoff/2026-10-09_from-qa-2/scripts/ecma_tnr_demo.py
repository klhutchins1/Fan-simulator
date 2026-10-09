"""Cheap MoSQITo 1.2.1 demo for noise lead #2: TNR/PR (ECMA-418-1) of a synthetic fan signal.
Broadband noise + a 300 Hz BPF tone (9 blades @ 2000 rpm) at three tone levels."""
import numpy as np
from mosqito.sq_metrics import tnr_ecma_st, pr_ecma_st
fs, T = 48000, 2.0; t = np.arange(int(fs * T)) / fs; rng = np.random.default_rng(0)
noise = rng.standard_normal(t.size) * 0.02
for amp in (0.0, 0.005, 0.02):
    sig = noise + amp * np.sin(2 * np.pi * 300 * t)
    T_tot, tnr, prom, ft = tnr_ecma_st(sig, fs, prominence=True)
    P_tot, pr, pprom, fp = pr_ecma_st(sig, fs, prominence=True)
    top = lambda f, v, p: [(round(float(a)), round(float(b), 1), bool(c)) for a, b, c in zip(np.ravel(f), np.ravel(v), np.ravel(p))][:3]
    print(f"tone amp {amp}: TNR total {float(np.ravel(T_tot)[0]):.1f} dB, tones {top(ft, tnr, prom)} | PR total {float(np.ravel(P_tot)[0]):.1f} dB, tones {top(fp, pr, pprom)}")
