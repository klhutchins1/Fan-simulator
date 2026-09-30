# Blade-section comparison: Stock recipe vs close-reference STL

Cylinder cuts at r = frac x tip, unrolled to (s = r*theta, z); median over blades. Stagger is measured from the circumferential (s) direction (0 = in the rotation plane, 90 = axial). camber/c = max midline deviation from the chord line over chord; camber pos from the LE. LE theta is modulo blade pitch (phase is arbitrary); compare its change with radius, not its value.

### Stock (built from recipe)

| r/R | N | chord mm | stagger deg | camber/c | camber pos | t max mm | t/c | axial mm | LE theta deg | LE z mm | solidity |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.45 | 9 | 19.9 | 35.3 | 0.017 | 0.28 | 2.59 | 0.130 | 13.0 | 19.4 | 5.2 | 1.16 |
| 0.55 | 9 | 22.6 | 38.4 | 0.027 | 0.48 | 2.53 | 0.112 | 15.3 | 21.9 | 6.1 | 1.08 |
| 0.65 | 9 | 24.0 | 34.3 | 0.040 | 0.47 | 2.49 | 0.104 | 14.8 | 29.5 | 6.1 | 0.97 |
| 0.75 | 9 | 26.3 | 29.6 | 0.039 | 0.47 | 2.49 | 0.095 | 14.5 | 36.5 | 6.3 | 0.92 |
| 0.85 | 9 | 29.0 | 24.7 | 0.038 | 0.48 | 2.52 | 0.087 | 13.8 | 43.8 | 6.3 | 0.90 |
| 0.95 | 9 | 32.2 | 22.2 | 0.037 | 0.42 | 2.53 | 0.079 | 13.7 | 50.7 | 6.5 | 0.89 |

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
| 0.55 | +0.355 | +0.317 | -0.00308 | +5.55e-17 | +0.0264 | -0.000597 | +1.75 | +26.5 | +1.37 | +0.0314 |
| 0.65 | -0.285 | +0.38 | +0.00264 | -5.55e-17 | -0.0206 | +0.000365 | +1.02 | +26.2 | +0.659 | +0.00185 |
| 0.75 | -0.242 | +0.534 | +0.00204 | +0 | +0.0231 | +0.00173 | +1.25 | +25.4 | +0.186 | +0.00425 |
| 0.85 | -0.777 | +0.111 | +0.00809 | +5.55e-17 | +0.0399 | +0.00359 | +0.764 | +25.3 | -0.465 | -0.0115 |
| 0.95 | -0.551 | -0.68 | +0.000204 | +0 | -0.219 | -0.00537 | +0.532 | +25.3 | -0.695 | -0.00288 |

### Recipe (interpolated at the measured radii) vs built Stock

Convention (fansim/geometry/blade.py `_section_loop`): stagger is measured from the circumferential (tangent-plane) direction; chord coordinate `a` maps to t = a cos(stagger), axial = a sin(stagger), so recipe chord is the true chord length. `thickness` and `max_camber` are fractions of chord (plate family: constant thickness t*c, NACA meanline camber bowing the plate). Sections are planar in the tangent plane, not wrapped on the cylinder.

| r/R | chord recipe | chord built | stagger recipe | stagger built | camber recipe | camber built | camber pos recipe | built | t/c recipe | t/c built |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.45 | 20.2 | 19.9 | 37.7 | 35.3 | 0.039 | 0.017 | 0.48 | 0.28 | 0.116 | 0.130 |
| 0.55 | 22.3 | 22.6 | 37.9 | 38.4 | 0.059 | 0.027 | 0.47 | 0.48 | 0.106 | 0.112 |
| 0.65 | 24.9 | 24.0 | 31.7 | 34.3 | 0.077 | 0.040 | 0.47 | 0.47 | 0.096 | 0.104 |
| 0.75 | 29.4 | 26.3 | 25.2 | 29.6 | 0.080 | 0.039 | 0.48 | 0.47 | 0.083 | 0.095 |
| 0.85 | 36.0 | 29.0 | 19.1 | 24.7 | 0.079 | 0.038 | 0.49 | 0.48 | 0.069 | 0.087 |
| 0.95 | 44.7 | 32.2 | 16.6 | 22.2 | 0.071 | 0.037 | 0.53 | 0.42 | 0.055 | 0.079 |

Recipe stations: `r_frac, chord, stagger_deg, max_camber, camber_pos, thickness, sweep, skew, lean_deg`

- r_frac=0.0, chord=17.7452, stagger_deg=24.1259, max_camber=0.037, camber_pos=0.4775, thickness=0.1249, sweep=0.0, skew=0.0, lean_deg=0.0
- r_frac=0.2214, chord=21.3408, stagger_deg=39.7779, max_camber=0.0411, camber_pos=0.4775, thickness=0.1108, sweep=-1.6014, skew=-0.7238, lean_deg=5.6246
- r_frac=0.3771, chord=23.3226, stagger_deg=34.595, max_camber=0.0758, camber_pos=0.4624, thickness=0.1016, sweep=-1.4798, skew=1.4448, lean_deg=10.1496
- r_frac=0.5329, chord=26.956, stagger_deg=28.6915, max_camber=0.0777, camber_pos=0.472, thickness=0.0899, sweep=-1.2557, skew=3.7372, lean_deg=15.0734
- r_frac=0.6886, chord=32.3827, stagger_deg=21.9015, max_camber=0.0808, camber_pos=0.489, thickness=0.0758, sweep=-0.8643, skew=6.5974, lean_deg=20.523
- r_frac=0.8443, chord=40.1135, stagger_deg=17.2416, max_camber=0.075, camber_pos=0.496, thickness=0.0616, sweep=-0.3279, skew=10.0436, lean_deg=26.5215
- r_frac=1.0, chord=49.7851, stagger_deg=16.2628, max_camber=0.0654, camber_pos=0.5868, thickness=0.049, sweep=0.3578, skew=13.7985, lean_deg=33.0

### Station chord semantics (§19.7, 2026-09-30)

YAML / recipe `chord` is the **measured** cylinder-cut chord (mm). Under `cylindrical_tip`,
planar-tangent loft wires put LE/TE corners outside `tip_radius`, so the builder raises an
internal loft chord (and scales `thickness` / `max_camber` so absolute wall and camber height
stay put) until the trimmed solid measures the YAML target. Tip measured ≈ 33.5 mm; loft tip
≈ 49.6 mm (same solid as the former loft-inflated recipe). `fit_recipe_to_stl` now writes the
measured chord directly — no YAML inflation knob.