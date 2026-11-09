"""Lead 27: blade-pass RPM from a synthetic mic tone (numpy/scipy only). No hardware."""
from __future__ import annotations
import json, math
from pathlib import Path
import numpy as np

def bpf_rpm(signal: np.ndarray, sr: float, n_blades: int, fmin=50.0, fmax=800.0) -> float:
    """Peak-pick FFT magnitude in [fmin,fmax]; RPM = 60 * f_peak / B."""
    n = len(signal)
    window = np.hanning(n)
    spec = np.fft.rfft(signal * window)
    freqs = np.fft.rfftfreq(n, d=1.0/sr)
    mag = np.abs(spec)
    mask = (freqs >= fmin) & (freqs <= fmax)
    idx = np.argmax(mag[mask])
    f_peak = freqs[mask][idx]
    return 60.0 * f_peak / n_blades, float(f_peak)

sr = 16000
t = np.arange(0, 1.0, 1/sr)
true_rpm = 2000.0
B = 9
f_bpf = B * true_rpm / 60.0  # 300 Hz
# tone + harmonics + noise + a strut-ish tone at 4*rpm/60 = 133 Hz
sig = (0.8*np.sin(2*np.pi*f_bpf*t)
       + 0.3*np.sin(2*np.pi*2*f_bpf*t)
       + 0.25*np.sin(2*np.pi*(4*true_rpm/60)*t)  # strut 1x
       + 0.05*np.random.default_rng(0).normal(size=t.shape))
rpm_est, f_est = bpf_rpm(sig, sr, B)
err = abs(rpm_est - true_rpm)
# With strut tone lower, BPF should still win if amplitude higher
out = {
    "true_rpm": true_rpm, "B": B, "true_bpf_hz": f_bpf,
    "est_rpm": round(rpm_est, 1), "est_f_hz": round(f_est, 2),
    "abs_err_rpm": round(err, 1),
    "ok_within_2pct": bool(bool(err / true_rpm < 0.02)),
    "caveat": "Strut tones (lead 1) can confuse a naive peak-pick; prefer band around expected BPF or harmonic voting.",
    "deps": "numpy only for sketch; stock acoustic-tachometer wants sounddevice+numpy (both MIT/BSD) and a paper tab",
}
Path("out.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
