"""Lead 16 prototype (research only): tap-test natural frequency + damping from a mono recording.
Method A: scipy FFT peak-pick + half-power bandwidth (zeta = df/(2 f)), with an envelope-decay cross-check.
Method B: sdypy-EMA LSCF on the response spectrum (output-only: the flick's force is not measured, so the
spectrum of an impulsive response is used as a pseudo-FRF), poles picked nearest to Method A's peaks.
Synthetic signals: lead-13 FEA modes of the Stock blade (357, 1009, 1777, 2024 Hz). Run in /tmp/ema-venv."""
import json, sys, time, warnings
import numpy as np
from scipy import signal

MODES_F = [357.0, 1009.0, 1777.0, 2024.0]
MODES_Z = [0.025, 0.018, 0.012, 0.010]
MODES_A = [1.0, 0.5, 0.3, 0.25]


def synth(fs, dur=0.6, snr_db=40, phone=False, seed=0, t0=0.02):
    rng = np.random.default_rng(seed); t = np.arange(int(fs * dur)) / fs; x = np.zeros_like(t); tt = np.clip(t - t0, 0, None)
    for f, z, a in zip(MODES_F, MODES_Z, MODES_A):
        wd = 2 * np.pi * f * np.sqrt(1 - z * z); ph = rng.uniform(0, 2 * np.pi)
        x += (t >= t0) * a * np.exp(-z * 2 * np.pi * f * tt) * np.sin(wd * tt + ph)
    if phone:
        n_click = int(0.002 * fs); x[int(t0 * fs):int(t0 * fs) + n_click] += 2.0 * rng.standard_normal(n_click)  # finger click
        x += 0.05 * np.sin(2 * np.pi * 60 * t) + 0.02 * np.sin(2 * np.pi * 120 * t)  # mains hum
        b, a = signal.butter(2, 120, "highpass", fs=fs); x = signal.lfilter(b, a, x)  # phone mic low-cut
    p_sig = np.mean(x[int(t0 * fs):int((t0 + 0.05) * fs)] ** 2)
    x = x + rng.standard_normal(len(x)) * np.sqrt(p_sig / 10 ** (snr_db / 10))
    if phone:
        x = np.round(x / np.max(np.abs(x)) * 0.5 * 32767) / 32767  # 16-bit, -6 dBFS peak
    return t, x


def method_a(x, fs, fmin=150, fmax=3000, n_peaks=4, t0=0.02):
    x = x[int(t0 * fs) + int(0.003 * fs):]  # skip the click
    nfft = 1 << int(np.ceil(np.log2(len(x) * 8)))
    Xr = np.abs(np.fft.rfft(x, nfft)); f = np.fft.rfftfreq(nfft, 1 / fs); df = f[1] - f[0]
    X = np.sqrt(np.clip(signal.savgol_filter(Xr ** 2, max(5, int(3.0 / df) | 1), 2), 0, None))  # light smoothing (~3 Hz) of the power spectrum
    X = np.nan_to_num(X, nan=0.0)
    band = (f >= fmin) & (f <= fmax); L = 20 * np.log10(X + 1e-30)
    pk, pr = signal.find_peaks(np.where(band, L, L[band].min()), prominence=10.0)  # >= 10 dB above the surroundings
    acc = []
    for i in pk[np.argsort(-pr['prominences'])]:  # most prominent first
        if all(abs(f[i] - f[j]) > 0.08 * f[j] for j in acc):
            acc.append(i)
        if len(acc) == n_peaks:
            break
    cand = []
    for i in pk[np.argsort(-pr['prominences'])]:
        h = X[i] / np.sqrt(2); lo = i; hi = i
        while lo > 0 and X[lo] > h: lo -= 1
        while hi < len(X) - 1 and X[hi] > h: hi += 1
        if (hi - lo) * df >= 6.0:  # reject noise spikes narrower than ~2x the 3 Hz smoothing
            cand.append(i)
    acc = []
    for i in cand:
        if all(abs(f[i] - f[j]) > 0.08 * f[j] for j in acc):
            acc.append(i)
        if len(acc) == n_peaks:
            break
    out = []
    for i in sorted(acc):
        h = X[i] / np.sqrt(2)
        lo = i
        while lo > 0 and X[lo] > h: lo -= 1
        hi = i
        while hi < len(X) - 1 and X[hi] > h: hi += 1
        flo = f[lo] + (h - X[lo]) * (f[lo + 1] - f[lo]) / (X[lo + 1] - X[lo])
        fhi = f[hi - 1] + (X[hi - 1] - h) * (f[hi] - f[hi - 1]) / (X[hi - 1] - X[hi])
        a_, b_, c_ = np.log(X[i - 1]), np.log(X[i]), np.log(X[i + 1]); d = 0.5 * (a_ - c_) / (a_ - 2 * b_ + c_)
        fp = f[i] + d * df
        z_hp = (fhi - flo) / (2 * fp)
        # envelope decay: band-pass +-15 % around the peak, Hilbert envelope, fit log-linear on 80 %..20 % of peak
        sos = signal.butter(4, [0.85 * fp, 1.15 * fp], "bandpass", fs=fs, output="sos")
        env = np.abs(signal.hilbert(signal.sosfiltfilt(sos, x)))
        j0 = int(np.argmax(env)); e = env[j0:]; tt = np.arange(len(e)) / fs
        k_end = int(np.argmax(e < 0.1 * e[0])) if (e < 0.1 * e[0]).any() else len(e); m = np.zeros(len(e), bool); m[:k_end] = e[:k_end] < 0.8 * e[0]
        z_env = float("nan")
        if m.sum() > 10:
            s = np.polyfit(tt[m], np.log(e[m]), 1)[0]; z_env = -s / (2 * np.pi * fp)
        out.append(dict(f=float(fp), zeta_hp=float(z_hp), zeta_env=float(z_env)))
    return out


def method_b(x, fs, approx, fmin=150, fmax=3000, order=60, t0=0.02):
    from sdypy import EMA
    x = x[int(t0 * fs) + int(0.003 * fs):]
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / fs)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m = EMA.Model(frf=X[None, :], freq=f, lower=fmin, upper=fmax, pol_order_high=order, frf_form="accelerance")
        m.get_poles(method="lscf", show_progress=False)
        m.select_closest_poles(approx, f_window=50)
    return [dict(f=float(a), zeta=float(b)) for a, b in zip(m.nat_freq, m.nat_xi)]


def score(res, key_z):
    out = []
    for f0, z0 in zip(MODES_F, MODES_Z):
        if not res:
            out.append(None); continue
        r = min(res, key=lambda r: abs(r["f"] - f0))
        out.append(dict(f_err_pct=100 * (r["f"] - f0) / f0, z_err_pct=100 * (r[key_z] - z0) / z0 if np.isfinite(r[key_z]) else None,
                        found=abs(r["f"] - f0) / f0 < 0.03))
    return out


def main(outp, seeds=10):
    rows = []
    for fs in (44100, 48000):
        for phone in (False, True):
            for snr in (40, 20, 10, 0):
                for s in range(seeds):
                    _, x = synth(fs, snr_db=snr, phone=phone, seed=s)
                    t1 = time.monotonic(); A = method_a(x, fs); ta = time.monotonic() - t1
                    rec = dict(fs=fs, phone=phone, snr=snr, seed=s, A_s=round(ta, 3), A=A,
                               A_hp=score(A, "zeta_hp"), A_env=score(A, "zeta_env"))
                    try:
                        t1 = time.monotonic(); B = method_b(x, fs, [r["f"] for r in A]); rec["B_s"] = round(time.monotonic() - t1, 2)
                        rec["B"] = B; rec["B_sc"] = score(B, "zeta")
                    except Exception as e:  # noqa
                        rec["B_err"] = f"{type(e).__name__}: {e}"[:200]
                    rows.append(rec)
            print(fs, phone, "done", flush=True)
    json.dump(rows, open(outp, "w"))
    # summary: median |error| per mode, per method, per condition
    summ = {}
    for fs in (44100, 48000):
        for phone in (False, True):
            for snr in (40, 20, 10, 0):
                R = [r for r in rows if r["fs"] == fs and r["phone"] == phone and r["snr"] == snr]
                key = f"fs{fs}_{'phone' if phone else 'clean'}_snr{snr}"; summ[key] = {}
                for name, k in (("A_halfpower", "A_hp"), ("A_envelope", "A_env"), ("B_sdypyEMA", "B_sc")):
                    per = []
                    for mi in range(4):
                        vals = [r[k][mi] for r in R if k in r and r[k][mi]]
                        fe = [abs(v["f_err_pct"]) for v in vals if v["found"]]; ze = [abs(v["z_err_pct"]) for v in vals if v["found"] and v["z_err_pct"] is not None]
                        per.append(dict(found=f"{len(fe)}/{len(R)}", f_med=round(float(np.median(fe)), 3) if fe else None,
                                        z_med=round(float(np.median(ze)), 1) if ze else None, z_p90=round(float(np.percentile(ze, 90)), 1) if ze else None))
                    summ[key][name] = per
                summ[key]["B_time_s_med"] = float(np.median([r["B_s"] for r in R if "B_s" in r])) if any("B_s" in r for r in R) else None
                summ[key]["B_errors"] = sum("B_err" in r for r in R)
    json.dump(summ, open(outp.replace(".json", "_summary.json"), "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 10)
