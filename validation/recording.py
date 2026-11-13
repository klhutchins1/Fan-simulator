"""Turn a phone recording of a running fan into numbers (first print session, tach + phone only).

What a phone can and cannot tell us:

- **rpm**, from the blade-pass tone (``n_blades * rpm / 60``). This is an independent check on the tach.
- **How tonal** the fan is: how far the blade-pass tone and its harmonics stand above the broadband noise.
- **Relative loudness** between two recordings made the same way (same phone, app, gain, distance, room).
  The level is in dB relative to digital full scale, A-weighted. It is **not** dB(A) SPL: a phone is not a
  calibrated meter. Only differences between matched recordings mean anything.

The recorder app must save uncompressed WAV with automatic gain and noise suppression switched off, or the
levels are meaningless (the rpm still works).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile

MIN_SECONDS = 3.0
TONE_MIN_PROMINENCE_DB = 6.0      # below this the "tone" is just a bump in the noise
LEVEL_BAND_HZ = (50.0, 10000.0)


def load_wav(path: str | Path) -> tuple[np.ndarray, int]:
    """Mono float signal in [-1, 1] and its sample rate."""
    fs, data = wavfile.read(str(path))
    x = np.asarray(data)
    if np.issubdtype(x.dtype, np.integer):
        scale = 255.0 / 2 if x.dtype == np.uint8 else float(np.iinfo(x.dtype).max)
        x = (x.astype(np.float64) - (127.5 if x.dtype == np.uint8 else 0.0)) / scale
    else:
        x = x.astype(np.float64)
    if x.ndim == 2:
        x = x.mean(axis=1)
    return x, int(fs)


def a_weight_db(f: np.ndarray) -> np.ndarray:
    """IEC 61672 A-weighting in dB (0 dB at 1 kHz)."""
    f2 = np.maximum(np.asarray(f, dtype=float), 1e-6) ** 2
    ra = (12194.0**2 * f2**2) / ((f2 + 20.6**2) * np.sqrt((f2 + 107.7**2) * (f2 + 737.9**2)) * (f2 + 12194.0**2))
    return 20.0 * np.log10(ra) + 2.00


def _spectrum(x: np.ndarray, fs: int) -> tuple[np.ndarray, np.ndarray]:
    """Power spectrum (not density), 1 Hz bins, so a pure tone's peak equals its mean-square."""
    nper = min(len(x), int(fs))
    return signal.welch(x, fs=fs, window="hann", nperseg=nper, noverlap=nper // 2, scaling="spectrum")


def _prominence_db(f: np.ndarray, p: np.ndarray, f0: float) -> tuple[float, float]:
    """(refined peak frequency, dB above the median of the surrounding band) near ``f0``."""
    df = f[1] - f[0]
    near = (f >= f0 - max(3 * df, 0.01 * f0)) & (f <= f0 + max(3 * df, 0.01 * f0))
    if not near.any():
        return f0, 0.0
    i = np.flatnonzero(near)[np.argmax(p[near])]
    around = (f >= 0.8 * f[i]) & (f <= 1.25 * f[i]) & (np.abs(f - f[i]) > 5 * df)
    floor = float(np.median(p[around])) if around.any() else float(np.median(p))
    return float(f[i]), float(10 * np.log10(p[i] / max(floor, 1e-30)))


def analyze(x: np.ndarray, fs: int, *, n_blades: int, rpm_hint: float, hint_tol: float = 0.15) -> dict:
    """rpm from the blade-pass tone near ``rpm_hint`` (the tach reading), tone strength and relative level."""
    x = np.asarray(x, dtype=float)
    if len(x) < MIN_SECONDS * fs:
        raise ValueError(f"recording is {len(x) / fs:.1f} s; need at least {MIN_SECONDS:g} s of steady running")
    warnings: list[str] = []
    peak = float(np.max(np.abs(x)))
    if peak >= 0.98:
        warnings.append("clipping: the recording hits full scale; lower the gain or move the phone back")
    x = x - x.mean()
    rms = float(np.sqrt(np.mean(x**2)))
    if rms < 1e-3:
        warnings.append("very quiet recording (below -60 dB full scale): levels will be mostly phone noise")

    f, p = _spectrum(x, fs)
    bpf_hint = n_blades * rpm_hint / 60.0
    win = (f >= bpf_hint * (1 - hint_tol)) & (f <= bpf_hint * (1 + hint_tol))
    rpm = bpf = prom = None
    if win.any():
        cand = float(f[np.flatnonzero(win)[np.argmax(p[win])]])
        cand, cand_prom = _prominence_db(f, p, cand)
        if cand_prom >= TONE_MIN_PROMINENCE_DB:
            bpf, prom = cand, cand_prom
            rpm = 60.0 * bpf / n_blades
    if rpm is None:
        warnings.append(f"no clear blade-pass tone within {hint_tol:.0%} of {bpf_hint:.0f} Hz "
                        f"({n_blades} blades at {rpm_hint:.0f} rpm): check the blade count and the tach reading")

    harmonics = []
    if bpf is not None:
        for k in range(1, 6):
            if k * bpf > 0.45 * fs:
                break
            fk, pk = _prominence_db(f, p, k * bpf)
            harmonics.append({"harmonic": k, "hz": round(fk, 1), "prominence_db": round(pk, 1)})

    band = (f >= LEVEL_BAND_HZ[0]) & (f <= LEVEL_BAND_HZ[1])
    weighted = p[band] * 10 ** (a_weight_db(f[band]) / 10)
    # Hann-windowed spectrum bins overlap: 1.5 is the window's equivalent noise bandwidth in bins.
    level = float(10 * np.log10(max(weighted.sum() / 1.5, 1e-30)))

    return {"rpm": None if rpm is None else round(rpm, 1),
            "bpf_hz": None if bpf is None else round(bpf, 2),
            "bpf_prominence_db": None if prom is None else round(prom, 1),
            "harmonics": harmonics,
            "level_dba_rel": round(level, 2),
            "seconds": round(len(x) / fs, 1), "sample_rate": fs, "n_blades": n_blades,
            "rpm_hint": rpm_hint, "warnings": warnings}


def compare(a: dict, b: dict, rpm_match_tol: float = 0.03) -> dict:
    """B minus A. ``comparable`` is False unless both have an rpm and they agree within ``rpm_match_tol``."""
    ratio = None if not (a.get("rpm") and b.get("rpm")) else b["rpm"] / a["rpm"]
    comparable = ratio is not None and abs(ratio - 1.0) <= rpm_match_tol and not (a["warnings"] or b["warnings"])
    out = {"level_dba_rel_delta": round(b["level_dba_rel"] - a["level_dba_rel"], 2),
           "rpm_ratio": None if ratio is None else round(ratio, 4),
           "comparable": bool(comparable)}
    if a.get("bpf_prominence_db") is not None and b.get("bpf_prominence_db") is not None:
        out["bpf_prominence_db_delta"] = round(b["bpf_prominence_db"] - a["bpf_prominence_db"], 1)
    return out
