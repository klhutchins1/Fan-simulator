# fan_noise_curle / fan_noise_cv → farfield (#75/#76) — 2026-11-25

**Ruling by Cursor.** Scripts no longer own A-weighting or Curle dipole maths; they call
`fansim.acoustics.farfield`. Fixes the latent `r²` bug in `fan_noise_curle.observer_pressure`
(amplitude only correct at 1 m).

Audit check file `tests/audit/test_acoustics_audit.py` updated to expect the promote, so
fingerprints that include that check move — re-proven here after focused acoustics tests PASS.
