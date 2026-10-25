"""Lead 15 prototype (research only, not fansim source): ISO 21940-11 style permissible unbalance for printed
fansim rotors, and a four-run (amplitude-only) single-plane trim solver with synthetic tests.
Formula (own derivation, matches BTI page + ISO 21940-11 preview definitions e_per = U_per/m, e_per*Omega = G):
  e_per[um] = 1000 * G[mm/s] / Omega[rad/s] = 60000 G / (2 pi n) = 9549.3 G / n ;  U_per[g mm] = m[kg] * e_per[um].
Run with the fansim venv (qa/run_r20 = repo-r20 027ebcb)."""
import json, math, sys
import numpy as np

K = 60000.0 / (2.0 * math.pi)  # 9549.296...


def permissible_unbalance_gmm(mass_kg: float, rpm: float, grade_mm_s: float) -> float:
    return K * grade_mm_s * mass_kg / rpm


def e_per_um(rpm: float, grade_mm_s: float) -> float:
    return K * grade_mm_s / rpm


# ---- four-run method: V_i^2 = V0^2 + b^2 - 2 V0 b cos(theta_i - psi); correction at psi, mass = TW * V0 / b
def four_run(v0, v_trials, trial_mass, angles_deg=(0.0, 120.0, 240.0)):
    """Amplitude-only single-plane balancing. v0: original amplitude; v_trials: amplitudes with the trial weight at
    angles_deg (same radius). Returns dict(correction_mass, correction_angle_deg, trial_effect, residual_rms, ok).
    psi = angle of the correction weight (same frame as the trial angles). Least squares over all trials (any >= 3
    distinct angles); closed form for equally spaced, refined by Gauss-Newton otherwise."""
    th = np.radians(np.asarray(angles_deg, float)); v = np.asarray(v_trials, float); n = len(v)
    if n < 3:
        raise ValueError("need >= 3 trial runs")
    # linear form: V_i^2 - V0^2 = b^2 - 2 V0 b cos(psi) cos th_i - 2 V0 b sin(psi) sin th_i = c0 + c1 cos th + c2 sin th
    A = np.column_stack([np.ones(n), np.cos(th), np.sin(th)])
    c, *_ = np.linalg.lstsq(A, v ** 2 - v0 ** 2, rcond=None)
    b2_lin = c[0]; X, Y = -c[1] / (2 * v0), -c[2] / (2 * v0)   # b cos psi, b sin psi
    b = math.hypot(X, Y); psi = math.atan2(Y, X)
    # consistency: b^2 from the constant term vs from the harmonic terms (noise / non-linearity indicator)
    resid = v - np.sqrt(np.maximum(v0 ** 2 + b ** 2 - 2 * v0 * b * np.cos(th - psi), 0.0))
    ok = b > 1e-12 and b2_lin > 0 and abs(math.sqrt(max(b2_lin, 0)) - b) < 0.25 * max(b, 1e-12)
    return dict(correction_mass=trial_mass * v0 / b if b > 0 else float("nan"),
                correction_angle_deg=math.degrees(psi) % 360.0, trial_effect=b, b_from_constant=math.sqrt(max(b2_lin, 0)),
                residual_rms=float(np.sqrt(np.mean(resid ** 2))), ok=bool(ok))


def simulate(U0_gmm, U0_deg, trial_gmm, k=1.0, angles=(0, 120, 240), noise=0.0, rng=None):
    """Synthetic rotor: vibration = k * |U| (linear, rigid, same lag for all). Returns v0, trial amplitudes."""
    rng = rng or np.random.default_rng(0)
    U0 = U0_gmm * np.exp(1j * np.radians(U0_deg))
    amp = lambda z: abs(k * z) * (1 + noise * rng.standard_normal())
    v0 = amp(U0); vt = [amp(U0 + trial_gmm * np.exp(1j * np.radians(a))) for a in angles]
    return v0, vt


def tests():
    out = {}
    # 1. exact synthetic: recovery of mass and angle (correction should sit opposite the heavy spot)
    v0, vt = simulate(1.5, 70.0, 0.6)  # 1.5 g mm heavy spot at 70 deg; trial 0.6 g mm (e.g. 15 mg at 40 mm)
    r = four_run(v0, vt, trial_mass=0.6)
    out["exact"] = dict(r, expected_mass=1.5, expected_angle=250.0)
    assert abs(r["correction_mass"] - 1.5) < 1e-9 and abs(r["correction_angle_deg"] - 250.0) < 1e-6
    # 2. non-equal angles (90 deg steps, as Reliabilityweb allows 90-120)
    v0, vt = simulate(2.0, 200.0, 1.0, angles=(0, 90, 180))
    r = four_run(v0, vt, 1.0, (0, 90, 180)); out["angles_0_90_180"] = r
    assert abs(r["correction_mass"] - 2.0) < 1e-9 and abs(r["correction_angle_deg"] - 20.0) < 1e-6
    # 3. published graphical examples (expect agreement to drawing accuracy)
    out["reliabilityweb"] = dict(four_run(10.0, [7.0, 12.0, 18.0], 50.0), published_mass=59.0, published_angle=42.0)
    out["motionics"] = dict(four_run(0.4852, [0.6759, 0.7595, 0.2045], 1.63), published_mass=2.37, published_angle=252.0)
    # 4. noise Monte Carlo: residual after one correction, as a fraction of the original unbalance
    rng = np.random.default_rng(1); mc = {}
    for noise in (0.02, 0.05, 0.10):
        for trial_frac in (0.3, 0.6, 1.0):
            res = []
            for _ in range(2000):
                U0d = rng.uniform(0, 360); v0, vt = simulate(1.0, U0d, trial_frac, noise=noise, rng=rng)
                r = four_run(v0, vt, trial_frac)
                if not np.isfinite(r["correction_mass"]):
                    res.append(np.nan); continue
                corr = r["correction_mass"] * np.exp(1j * np.radians(r["correction_angle_deg"]))
                res.append(abs(np.exp(1j * np.radians(U0d)) + corr))
            res = np.array(res)
            mc[f"noise{noise}_trial{trial_frac}"] = dict(median=float(np.nanmedian(res)), p90=float(np.nanpercentile(res, 90)))
    out["monte_carlo_residual_frac"] = mc
    return out


def rotors():
    from dataclasses import replace
    from fansim.fan_spec import get_fan_spec, estimate_weight_g
    from fansim.geometry.blade import build_impeller_parts
    from fansim.manufacturability.print_export import mount_hub_params
    from fansim.manufacturability.materials import MATERIALS
    from fansim.optimize.search_space import blade_from_flat, stock_blade_flat
    from fansim.geometry.features import Features
    from fansim.propeller.bemt_catalog import approximate_prop_blade
    rho = MATERIALS["PETG"].density_kg_m3
    M = get_fan_spec("a12x25").motor_mount
    p1 = "/workspace/fansim/repo-r15/handoff/2026-10-17_from-qa-16-hang/data/p1_designed.jsonl"
    cases = [("a12x25 Stock (printed, PETG)", blade_from_flat(stock_blade_flat("a12x25"), Features()), [2000, 3900], True)]
    for did in ("G_0502", "S1_0534"):
        row = next(json.loads(l) for l in open(p1) if json.loads(l)["id"] == did)
        cases.append((f"optimizer design {did} (r16)", blade_from_flat(row["flat"], Features()), [2000], True))
    cases.append(('prop 5x4.5 3-blade (approx)', approximate_prop_blade(5.0, 4.5, blade_count=3), [25000, 10000], False))
    cases.append(('prop 9x4.7 2-blade (approx)', approximate_prop_blade(9.0, 4.7, blade_count=2), [10000], False))
    out = []
    for name, p, rpms, mount in cases:
        if mount:
            p = mount_hub_params(p, M)[0]
        hub, blades, ring = build_impeller_parts(p)
        vb = sum(b.val().Volume() if hasattr(b, "val") else b.Volume() for b in (blades if isinstance(blades, (list, tuple)) else [blades]))
        vh = hub.val().Volume() if hasattr(hub, "val") else hub.Volume()
        m_solid = (vb + vh) * rho * 1e-9; m_real = (vb + 0.4 * vh) * rho * 1e-9  # blades ~solid (walls), hub at 40 % infill
        m_default = estimate_weight_g(vb + vh, "PETG") / 1000.0  # fansim default 20 % infill estimate
        r_tip = p.tip_radius
        for n in rpms:
            row = dict(rotor=name, rpm=n, blade_vol_mm3=round(vb), hub_vol_mm3=round(vh), n_blades=p.n_blades,
                       m_solid_g=round(m_solid * 1e3, 2), m_realistic_g=round(m_real * 1e3, 2), m_fansim_default_g=round(m_default * 1e3, 2),
                       tip_radius_mm=r_tip)
            for G in (2.5, 6.3):
                U = permissible_unbalance_gmm(m_real, n, G)
                row[f"G{G}_e_per_um"] = round(e_per_um(n, G), 2)
                row[f"G{G}_U_per_gmm_realistic"] = round(U, 4)
                row[f"G{G}_U_per_gmm_solid"] = round(permissible_unbalance_gmm(m_solid, n, G), 4)
                row[f"G{G}_blob_mg_at_0.9R"] = round(1000 * U / (0.9 * r_tip), 2)
            # random blade-mass scatter: sigma 1 % of one blade's mass at its centroid ~0.6 R -> expected |U|
            mb = vb / p.n_blades * rho * 1e-6  # g per blade
            row["blade_mass_g"] = round(mb, 3)
            row["exp_U_from_1pct_blade_scatter_gmm"] = round(0.01 * mb * 0.6 * r_tip * math.sqrt(p.n_blades) * math.sqrt(math.pi) / 2, 3)
            row["exp_U_from_50um_mount_offset_gmm"] = round(m_real * 1e3 * 0.05, 3)
            out.append(row)
    return out


if __name__ == "__main__":
    res = {"K": K, "tests": tests()}
    if "--rotors" in sys.argv:
        res["rotors"] = rotors()
    json.dump(res, open(sys.argv[1], "w"), indent=1, default=float)
    t = res["tests"]
    for k in ("reliabilityweb", "motionics"):
        print(k, {x: round(t[k][x], 3) if isinstance(t[k][x], float) else t[k][x] for x in t[k]})
    print("mc", t["monte_carlo_residual_frac"])
    for r in res.get("rotors", []):
        print(r)
