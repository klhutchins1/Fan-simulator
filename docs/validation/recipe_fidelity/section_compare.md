# Blade-section comparison: Stock recipe vs close-reference STL

Cylinder cuts at r = frac x tip, unrolled to (s = r*theta, z); median over blades. Stagger is measured from the circumferential (s) direction (0 = in the rotation plane, 90 = axial). camber/c = max midline deviation from the chord line over chord; camber pos from the LE. LE theta is modulo blade pitch (phase is arbitrary); compare its change with radius, not its value.

### Stock (built from recipe)

| r/R | N | chord mm | stagger deg | camber/c | camber pos | t max mm | t/c | axial mm | LE theta deg | LE z mm | solidity |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.45 | 9 | 11.4 | 41.8 | 0.061 | 0.42 | 1.62 | 0.142 | 8.2 | 13.1 | 4.2 | 0.67 |
| 0.55 | 9 | 13.2 | 50.2 | 0.066 | 0.42 | 1.72 | 0.131 | 10.6 | 17.1 | 5.5 | 0.63 |
| 0.65 | 9 | 15.3 | 54.2 | 0.069 | 0.42 | 1.79 | 0.117 | 12.8 | 22.8 | 6.6 | 0.62 |
| 0.75 | 9 | 17.5 | 54.8 | 0.065 | 0.42 | 1.86 | 0.106 | 14.7 | 29.4 | 7.5 | 0.61 |
| 0.85 | 9 | 19.7 | 51.3 | 0.056 | 0.43 | 1.95 | 0.099 | 15.8 | 37.5 | 8.1 | 0.61 |
| 0.95 | 9 | 20.9 | 44.0 | 0.040 | 0.33 | 2.02 | 0.097 | 15.2 | 46.0 | 8.2 | 0.58 |

### Reference STL

| r/R | N | chord mm | stagger deg | camber/c | camber pos | t max mm | t/c | axial mm | LE theta deg | LE z mm | solidity |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.45 | 0 | - | - | - | - | - | - | - | - | - | - |
| 0.55 | 9 | 22.2 | 38.1 | 0.030 | 0.47 | 2.51 | 0.113 | 13.6 | -4.6 | 4.7 | 1.05 |
| 0.65 | 9 | 24.3 | 33.9 | 0.038 | 0.48 | 2.51 | 0.104 | 13.8 | 3.3 | 5.4 | 0.97 |
| 0.75 | 9 | 26.6 | 29.0 | 0.037 | 0.47 | 2.47 | 0.093 | 13.3 | 11.1 | 6.1 | 0.92 |
| 0.85 | 9 | 29.8 | 24.6 | 0.030 | 0.47 | 2.48 | 0.083 | 13.0 | 18.5 | 6.7 | 0.91 |
| 0.95 | 9 | 32.7 | 22.9 | 0.036 | 0.42 | 2.75 | 0.084 | 13.2 | 25.4 | 7.2 | 0.89 |

### Difference (stock - reference)

| r/R | chord mm | stagger deg | camber/c | camber pos | t max mm | t/c | axial mm | LE theta deg | LE z mm | solidity |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.45 | - | - | - | - | - | - | - | - | - | - |
| 0.55 | -9.05 | +12.1 | +0.036 | -0.05 | -0.784 | +0.018 | -3.03 | +21.7 | +0.745 | -0.418 |
| 0.65 | -8.98 | +20.3 | +0.0313 | -0.05 | -0.723 | +0.0135 | -1.03 | +19.5 | +1.13 | -0.35 |
| 0.75 | -9.06 | +25.7 | +0.0287 | -0.05 | -0.608 | +0.0133 | +1.42 | +18.3 | +1.39 | -0.305 |
| 0.85 | -10.1 | +26.7 | +0.0261 | -0.05 | -0.523 | +0.016 | +2.82 | +19 | +1.43 | -0.3 |
| 0.95 | -11.8 | +21.1 | +0.00331 | -0.1 | -0.734 | +0.0124 | +2.07 | +20.6 | +1.01 | -0.314 |

### Recipe (interpolated at the measured radii) vs built Stock

Convention (fansim/geometry/blade.py `_section_loop`): stagger is measured from the circumferential (tangent-plane) direction; chord coordinate `a` maps to t = a cos(stagger), axial = a sin(stagger), so recipe chord is the true chord length. `thickness` and `max_camber` are fractions of chord (plate family: constant thickness t*c, NACA meanline camber bowing the plate). Sections are planar in the tangent plane, not wrapped on the cylinder.

| r/R | chord recipe | chord built | stagger recipe | stagger built | camber recipe | camber built | camber pos recipe | built | t/c recipe | t/c built |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.45 | 11.2 | 11.4 | 41.3 | 41.8 | 0.086 | 0.061 | 0.40 | 0.42 | 0.139 | 0.142 |
| 0.55 | 13.0 | 13.2 | 48.8 | 50.2 | 0.092 | 0.066 | 0.40 | 0.42 | 0.127 | 0.131 |
| 0.65 | 15.3 | 15.3 | 51.8 | 54.2 | 0.098 | 0.069 | 0.40 | 0.42 | 0.115 | 0.117 |
| 0.75 | 18.0 | 17.5 | 50.4 | 54.8 | 0.104 | 0.065 | 0.40 | 0.42 | 0.104 | 0.106 |
| 0.85 | 21.5 | 19.7 | 43.3 | 51.3 | 0.111 | 0.056 | 0.40 | 0.43 | 0.092 | 0.099 |
| 0.95 | 25.7 | 20.9 | 30.9 | 44.0 | 0.117 | 0.040 | 0.40 | 0.33 | 0.081 | 0.097 |

Recipe stations: `r_frac, chord, stagger_deg, max_camber, camber_pos, thickness, sweep, skew, lean_deg`

- r_frac=0.0, chord=10.0, stagger_deg=30.0, max_camber=0.08, camber_pos=0.4, thickness=0.15, sweep=0.0, skew=0.0, lean_deg=0.0
- r_frac=0.5, chord=16.0, stagger_deg=52.0, max_camber=0.1, camber_pos=0.4, thickness=0.112, sweep=0.0, skew=3.0, lean_deg=14.0
- r_frac=1.0, chord=28.0, stagger_deg=23.0, max_camber=0.12, camber_pos=0.4, thickness=0.075, sweep=0.0, skew=13.0, lean_deg=33.0
