# Fan design rules (data-driven)

From `opt_v3`: **14 feasible trials**, **14 noise-scored** (LBM control-volume dipole, relative). Spearman rank correlations below; sign = direction, magnitude = strength (|rho|>0.5 notable at this n). Correlational, screening-fidelity — **design guidance to test, not law**.

## Strongest driver of each objective

- **Free-air airflow (max)** — driven by `max_camber` (-0.79), `stagger_mid` (+0.65), `stagger_mean` (+0.50), `chord_tip` (+0.49)
- **Airflow under load (max)** — driven by `max_camber` (-0.78), `stagger_mid` (+0.65), `stagger_mean` (+0.50), `chord_tip` (+0.49)
- **Efficiency (max)** — driven by `max_camber` (-0.78), `n_blades` (-0.61), `chord_tip` (+0.60), `sol_mid` (-0.57)
- **Noise dB(A) (min)** — driven by `stagger_mid` (-0.79), `sol_tip` (+0.70), `sol_mid` (+0.67), `n_blades` (+0.64)
- **Blade-pass tone (min)** — driven by `chord_tip` (-0.50), `chord_mean` (-0.50), `lean_mid` (+0.50), `stagger_mid` (+0.47)
- **Blade loading |thrust|** — driven by `stagger_tip` (+0.51), `sol_hub` (+0.49), `sol_mid` (+0.46), `stagger_root` (-0.44)

## Full correlation table

| design var | cfm_free | cfm_load | efficiency | noise_dba_band | bpf_tone_db | thrust_abs |
|---|---|---|---|---|---|---|
| `n_blades` | -0.35 | -0.35 | -0.61 | +0.64 | +0.06 | +0.40 |
| `stagger_root` | +0.13 | +0.14 | -0.19 | +0.03 | -0.11 | -0.44 |
| `stagger_mid` | +0.65 | +0.65 | +0.44 | -0.79 | +0.47 | +0.03 |
| `stagger_tip` | -0.22 | -0.22 | -0.29 | +0.07 | +0.21 | +0.51 |
| `chord_root` | +0.28 | +0.28 | +0.30 | -0.11 | -0.17 | +0.09 |
| `chord_mid` | -0.26 | -0.26 | -0.24 | +0.40 | +0.22 | +0.23 |
| `chord_tip` | +0.49 | +0.49 | +0.60 | +0.16 | -0.50 | -0.17 |
| `sweep_mid` | -0.03 | -0.00 | -0.22 | -0.48 | +0.45 | +0.15 |
| `sweep_tip` | -0.42 | -0.42 | -0.30 | +0.06 | +0.14 | -0.25 |
| `lean_mid` | +0.16 | +0.16 | -0.09 | +0.15 | +0.50 | +0.27 |
| `lean_tip` | +0.21 | +0.21 | +0.49 | +0.31 | -0.32 | -0.28 |
| `max_camber` | -0.79 | -0.78 | -0.78 | +0.22 | +0.10 | +0.08 |
| `sol_hub` | -0.06 | -0.06 | -0.13 | +0.25 | +0.01 | +0.49 |
| `sol_mid` | -0.47 | -0.47 | -0.57 | +0.67 | +0.20 | +0.46 |
| `sol_tip` | +0.01 | +0.01 | -0.11 | +0.70 | -0.24 | +0.29 |
| `chord_mean` | +0.16 | +0.16 | +0.29 | +0.39 | -0.50 | -0.03 |
| `stagger_mean` | +0.50 | +0.50 | +0.13 | -0.33 | +0.24 | -0.03 |
| `lean_mean` | +0.33 | +0.32 | +0.40 | +0.28 | +0.02 | -0.09 |

## Read-out

- **Blade count / solidity** trades loading, tone and efficiency. The table's airflow correlation with blade count is negative (ρ −0.35), so do not assume more blades mean more airflow.
- **Efficiency** favours *fewer, lightly-loaded* blades; **airflow** favours *more chord*. The quiet+efficient and the high-flow corners are geometrically distinct.
- **Noise** tracks blade loading (|thrust|) and blade count more than any single angle — so to get quieter at fixed flow, spread the load (more blades at lower stagger) rather than over-loading few blades.

_Caveats: n is small; screening mesh, GCI ≈ 21 %; ranks designs, ±1 % run to run on Stock; absolute noise is coarse-grid-limited so only the ranking is used; correlations are not causation._
