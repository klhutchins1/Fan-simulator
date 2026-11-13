"""Phone recording of a running fan -> rpm from the blade-pass tone, tone strength, relative level."""
from __future__ import annotations

import numpy as np
import pytest
from scipy.io import wavfile

from validation import recording as rec

FS = 44100


def _tone(freq, amp, seconds=6.0, fs=FS):
    t = np.arange(int(seconds * fs)) / fs
    return amp * np.sin(2 * np.pi * freq * t)


def _noise(amp, seconds=6.0, fs=FS, seed=0):
    return amp * np.random.default_rng(seed).standard_normal(int(seconds * fs))


def test_rpm_from_the_blade_pass_tone():
    x = _tone(300.0, 0.05) + _noise(0.005)                 # 9 blades at 2000 rpm -> 300 Hz
    r = rec.analyze(x, FS, n_blades=9, rpm_hint=2000)
    assert r["rpm"] == pytest.approx(2000, rel=0.005)
    assert r["bpf_hz"] == pytest.approx(300, abs=1.5)
    assert r["bpf_prominence_db"] > 10


def test_a_stronger_once_per_rev_tone_does_not_fool_it():
    x = _tone(300.0, 0.02) + _tone(2000 / 60, 0.2) + _noise(0.003)   # imbalance hum at 33 Hz
    r = rec.analyze(x, FS, n_blades=9, rpm_hint=2100)                 # tach hint is 5 % off
    assert r["rpm"] == pytest.approx(2000, rel=0.005)


def test_no_tone_near_the_hint_is_reported_not_invented():
    r = rec.analyze(_noise(0.01), FS, n_blades=9, rpm_hint=2000)
    assert r["rpm"] is None
    assert "no clear blade-pass tone" in " ".join(r["warnings"])


def test_doubling_the_signal_adds_6_db():
    base = _tone(1000.0, 0.02) + _noise(0.002)
    a = rec.analyze(base, FS, n_blades=9, rpm_hint=2000)["level_dba_rel"]
    b = rec.analyze(2 * base, FS, n_blades=9, rpm_hint=2000)["level_dba_rel"]
    assert b - a == pytest.approx(6.02, abs=0.1)


def test_a_weighting_matches_the_standard_curve():
    # IEC 61672: A(1 kHz) = 0 dB, A(100 Hz) = -19.1 dB
    lvl_1k = rec.analyze(_tone(1000.0, 0.05), FS, n_blades=9, rpm_hint=2000)["level_dba_rel"]
    lvl_100 = rec.analyze(_tone(100.0, 0.05), FS, n_blades=9, rpm_hint=2000)["level_dba_rel"]
    assert lvl_100 - lvl_1k == pytest.approx(-19.1, abs=0.5)


def test_clipping_and_a_too_quiet_recording_are_flagged():
    clipped = np.clip(_tone(300.0, 1.5), -1.0, 1.0)
    assert any("clipp" in w for w in rec.analyze(clipped, FS, n_blades=9, rpm_hint=2000)["warnings"])
    quiet = _tone(300.0, 1e-4)
    assert any("quiet" in w for w in rec.analyze(quiet, FS, n_blades=9, rpm_hint=2000)["warnings"])


def test_too_short_a_recording_is_refused():
    with pytest.raises(ValueError, match="at least"):
        rec.analyze(_tone(300.0, 0.05, seconds=1.0), FS, n_blades=9, rpm_hint=2000)


def test_stereo_int16_wav_loads_as_mono_float(tmp_path):
    x = (_tone(300.0, 0.5, seconds=3.0) * 32767).astype(np.int16)
    p = tmp_path / "a.wav"
    wavfile.write(p, FS, np.stack([x, x], axis=1))
    y, fs = rec.load_wav(p)
    assert fs == FS and y.ndim == 1
    assert np.max(np.abs(y)) == pytest.approx(0.5, abs=0.01)


def test_harmonics_are_listed():
    x = _tone(300.0, 0.05) + _tone(600.0, 0.02) + _noise(0.002)
    r = rec.analyze(x, FS, n_blades=9, rpm_hint=2000)
    assert [h["harmonic"] for h in r["harmonics"]][:2] == [1, 2]
    assert r["harmonics"][1]["prominence_db"] > 10


def test_compare_reports_b_minus_a(tmp_path):
    a = rec.analyze(_tone(300.0, 0.02) + _noise(0.004), FS, n_blades=9, rpm_hint=2000)
    b = rec.analyze(_tone(300.0, 0.04) + _noise(0.008), FS, n_blades=9, rpm_hint=2000)
    d = rec.compare(a, b)
    assert d["level_dba_rel_delta"] == pytest.approx(6.0, abs=0.3)
    assert d["rpm_ratio"] == pytest.approx(1.0, abs=0.01)
    assert d["comparable"] is True


def test_compare_says_when_the_speeds_do_not_match():
    a = rec.analyze(_tone(300.0, 0.02) + _noise(0.002), FS, n_blades=9, rpm_hint=2000)
    b = rec.analyze(_tone(270.0, 0.02) + _noise(0.002), FS, n_blades=9, rpm_hint=1800)
    assert rec.compare(a, b)["comparable"] is False


def test_cli_compares_two_files_and_reports_a_missing_one_plainly(tmp_path, capsys):
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        "analyze_fan_recording", Path(__file__).resolve().parents[1] / "scripts" / "analyze_fan_recording.py")
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    for name, amp in (("a", 0.03), ("b", 0.06)):
        x = _tone(300.0, amp, seconds=4.0) + _noise(amp / 8, seconds=4.0)
        wavfile.write(tmp_path / f"{name}.wav", FS, (x * 32767).astype(np.int16))
    out_json = tmp_path / "o.json"
    assert cli.main([str(tmp_path / "a.wav"), str(tmp_path / "b.wav"), "--blades", "9", "--rpm", "2000",
                     "--json", str(out_json)]) == 0
    out = capsys.readouterr().out
    assert "b.wav minus a.wav: +6.0 dB" in out
    assert "not dB(A) SPL" in out
    assert out_json.exists()
    assert cli.main([str(tmp_path / "missing.wav"), "--blades", "9", "--rpm", "2000"]) == 2
    assert "cannot read" in capsys.readouterr().out
