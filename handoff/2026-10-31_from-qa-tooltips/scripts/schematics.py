"""Fallback schematics for SEARCH / EVAL settings the repo generator cannot draw (it only renders
impeller/blade geometry). Same canvas as the generator: 460x250 PNG, white bg, blue #3b82f6 accent.
Values quoted are from code: presets.py (8/20/35 Pa, legacy 1 Pa), fan_optimize.py (BEM floor 32,
GP floor 40, trials 2..40), casing.py (STEP_DEPTH_MM 1.2, STEP_LEN_MM 6), wall_roughness FDM ks,
surrogate_search.synthetic_label. Curves are illustrative shapes, NOT simulation output.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch
from pathlib import Path

OUT = Path("/workspace/fansim/qa_tooltips/img")
B, G, R, K = "#3b82f6", "#9ca3af", "#dc2626", "#111827"
plt.rcParams.update({"font.size": 8, "axes.titlesize": 9})


def fig(n=1):
    f, ax = plt.subplots(1, n, figsize=(4.6, 2.5), dpi=100)
    return f, ax


def save(f, name):
    f.tight_layout()
    f.savefig(OUT / f"{name}.png", dpi=100, facecolor="white")
    plt.close(f)
    print(name)


def box(ax, x, y, w, h, txt, c=B, fc="white", fs=7.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02", ec=c, fc=fc, lw=1.3))
    ax.text(x + w / 2, y + h / 2, txt, ha="center", va="center", fontsize=fs, color=K)


def arrow(ax, x0, y0, x1, y1, c=K):
    ax.annotate("", (x1, y1), (x0, y0), arrowprops=dict(arrowstyle="->", color=c, lw=1.1))


def fan_curve(q):  # illustrative pressure-flow curve
    return 40 * (1 - (q / 60) ** 1.6)


# --- assess_preset: which load line the design is scored at -------------------------------
f, ax = fig()
q = np.linspace(0, 60, 200)
ax.plot(q, fan_curve(q), color=K, lw=1.5, label="fan curve (illustrative)")
for pa, nm, c in [(1, "legacy 1 Pa", G), (8, "case 8 Pa", B), (20, "heatsink 20 Pa", "#f59e0b"),
                  (35, "radiator 35 Pa", R)]:
    ax.axhline(pa, color=c, ls="--", lw=1)
    qx = 60 * (1 - pa / 40) ** (1 / 1.6)
    ax.plot(qx, pa, "o", color=c)
    ax.text(61, pa, nm, va="center", fontsize=7, color=c)
ax.set_xlim(0, 80); ax.set_ylim(0, 45)
ax.set_xlabel("airflow (CFM)"); ax.set_ylabel("static pressure (Pa)")
ax.set_title("Application preset = back-pressure the design is scored at")
save(f, "assess_preset")

# --- assess_refine_op: 2-point estimate vs 3rd CFD at operating pressure --------------------
f, ax = fig()
ax.plot(q, fan_curve(q), color=G, lw=1.2, label="true curve (unknown)")
p_free, p_hi = (52, fan_curve(52)), (15, fan_curve(15))
ax.plot(*zip(p_free, p_hi), color=R, ls="--", lw=1.2, label="off: line through 2 CFD points")
ax.plot(*zip(p_free, p_hi), "s", color=R)
op = 20
q_est = np.interp(op, [p_free[1], p_hi[1]], [p_free[0], p_hi[0]])
q_true = 60 * (1 - op / 40) ** (1 / 1.6)
ax.axhline(op, color=K, lw=0.6, ls=":")
ax.plot(q_est, op, "x", color=R, ms=8)
ax.plot(q_true, op, "o", color=B, ms=7, label="on: 3rd CFD at operating Pa")
ax.set_xlim(0, 62); ax.set_ylim(0, 45)
ax.set_xlabel("airflow (CFM)"); ax.set_ylabel("Pa")
ax.legend(fontsize=6.5, loc="upper right", frameon=False)
ax.set_title("Refine op point: 3rd solve (~+50% time) vs 2-point estimate")
save(f, "assess_refine_op")

# --- assess_wall_ks: smooth vs FDM roughness -------------------------------------------------
f, axs = fig(2)
x = np.linspace(0, 10, 400)
for a, rough, t in [(axs[0], 0, "off = hydraulically smooth"), (axs[1], 1, "on = FDM ks ≈ 0.1 mm")]:
    y = 0.5 + rough * (0.12 * np.abs(np.sin(x * 6)) + 0.03 * np.sin(x * 23))
    a.fill_between(x, 0, y, color=B)
    for yy in (1.4, 2.0, 2.6):
        prof = yy + 0 * x
        a.annotate("", (9.5, yy), (0.5, yy), arrowprops=dict(arrowstyle="->", color=G))
    a.text(5, 3.1, "impeller + frame/stator walls", ha="center", fontsize=7)
    a.set_title(t); a.set_xlim(0, 10); a.set_ylim(0, 3.4); a.axis("off")
f.suptitle("Wall roughness only changes the CFD wall model (casing stays smooth)", fontsize=7.5)
save(f, "assess_wall_ks")

# --- opt_bem and opt_gp: skip-CFD screens ---------------------------------------------------
for name, title, gate in [
        ("opt_bem", "BEM prescreen (ranking only)", "BEM CFM < 32 ?"),
        ("opt_gp", "Catalog GP skip", "GP mean+σ < 40 ?")]:
    f, ax = fig(); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 5)
    box(ax, 0.2, 2, 2.0, 1, "Optuna proposes\na shape")
    box(ax, 3.0, 2, 2.4, 1, gate, c="#f59e0b")
    box(ax, 6.3, 3.2, 3.4, 1, "yes → SKIP CFD\n(trial pruned, minutes saved)", c=G)
    box(ax, 6.3, 0.8, 3.4, 1, "no → full CFD\n(tens of minutes)", c=B)
    arrow(ax, 2.2, 2.5, 3.0, 2.5); arrow(ax, 5.4, 2.7, 6.3, 3.6); arrow(ax, 5.4, 2.3, 6.3, 1.3)
    ax.text(5, 4.7, title, ha="center", fontsize=9)
    ax.text(5, 0.2, "Does not stamp geometry; only decides which shapes get a CFD score.",
            ha="center", fontsize=7, color=K)
    save(f, name)

# --- opt_gp_boost / opt_gp_nn: which model gives the mean ------------------------------------
for name, mean in [("opt_gp_boost", "boosted trees"), ("opt_gp_nn", "small neural net")]:
    f, ax = fig(); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 5)
    box(ax, 0.3, 2.6, 3.0, 1.2, "Catalog of past\nscored designs")
    box(ax, 4.0, 3.3, 2.6, 0.9, f"mean: {mean}", c=B)
    box(ax, 4.0, 2.0, 2.6, 0.9, "spread: GP", c=G)
    box(ax, 7.3, 2.6, 2.4, 1.2, "skip / rank\ndecision")
    arrow(ax, 3.3, 3.2, 4.0, 3.7); arrow(ax, 3.3, 3.2, 4.0, 2.45)
    arrow(ax, 6.6, 3.7, 7.3, 3.3); arrow(ax, 6.6, 2.45, 7.3, 3.0)
    ax.text(5, 4.7, f"{name}: swap the CFM predictor's mean", ha="center", fontsize=9)
    ax.text(5, 0.9, "Only takes effect when Catalog GP skip OR Surrogate-guided is on\n"
            "(cli_argv.py adds --surrogate-boost/--surrogate-nn only then).",
            ha="center", fontsize=7, color=R)
    save(f, name)

# --- opt_surrogate_guided --------------------------------------------------------------------
f, ax = fig(); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 5)
steps = ["DoE\n24 shapes", "fit GP/\nboost/NN", "NSGA-II on\nsurrogate (64)", "verify\ntop-4", "refit\n(2 rounds)"]
for i, s in enumerate(steps):
    box(ax, 0.2 + i * 1.95, 2.6, 1.6, 1.1, s, c=B if i != 3 else R)
    if i:
        arrow(ax, 0.2 + i * 1.95 - 0.35, 3.15, 0.2 + i * 1.95, 3.15)
ax.text(5, 4.6, "Surrogate-guided loop (replaces the normal CFD study)", ha="center", fontsize=9)
ax.text(5, 1.5, "Cockpit never passes --verify-cfd: labels + verify use synthetic_label()\n"
        "(formula on tip chord, mid stagger, blades, camber) — no CFD at all.\n"
        "Trials slider and all Geometry stamps / Search RPM / Refine / Roughness are ignored.",
        ha="center", fontsize=6.8, color=R)
save(f, "opt_surrogate_guided")

# --- opt_search_rpm / rpm band ----------------------------------------------------------------
f, ax = fig(); ax.set_xlim(0, 2400); ax.set_ylim(0, 3); ax.set_yticks([])
ax.barh(2, 2000 - 450, left=450, height=0.5, color=B, alpha=0.35)
ax.text(1225, 2, "on: Optuna picks RPM per trial inside [RPM min, RPM max]", ha="center", va="center", fontsize=7)
ax.plot([450, 450], [1.6, 2.4], color=B); ax.plot([2000, 2000], [1.6, 2.4], color=B)
ax.text(450, 2.55, "RPM min", ha="center", fontsize=7); ax.text(2000, 2.55, "RPM max", ha="center", fontsize=7)
ax.plot([2000], [0.9], "o", color=K)
ax.text(2000, 0.5, "off: fixed fan-model RPM", ha="center", fontsize=7)
ax.set_xlabel("rotor speed (RPM)")
ax.set_title("Search RPM: speed becomes a search variable (shape still from Optuna)")
save(f, "opt_search_rpm")

# --- opt_trials / opt_resume -------------------------------------------------------------------
f, axs = fig(2)
rng = np.random.default_rng(1)
for a, n, t in [(axs[0], 8, "Trials = 8"), (axs[1], 40, "Trials = 40")]:
    x = rng.uniform(20, 55, n); y = 30 - 0.35 * x + rng.normal(0, 3, n)
    a.scatter(x, y, s=10, color=G)
    pts = sorted(zip(x, y)); front = []; best = -1e9
    for xx, yy in sorted(pts, key=lambda p: -p[0]):
        if yy > best:
            front.append((xx, yy)); best = yy
    fx, fy = zip(*sorted(front)); a.plot(fx, fy, "-o", color=B, ms=3)
    a.set_title(t); a.set_xlabel("load CFM"); a.set_ylabel("efficiency")
    a.set_xticks([]); a.set_yticks([])
f.suptitle("More trials = more CFD runs = better-covered Pareto front", fontsize=8)
save(f, "opt_trials")

f, ax = fig(); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 5)
ax.text(5, 4.6, "Continue last run (resume)", ha="center", fontsize=9)
ax.text(0.2, 3.6, "off:", fontsize=8)
for i in range(2):
    box(ax, 1.2 + i * 4.2, 3.2, 1.6, 0.7, "random\nwarm-up", c=G, fs=6.5)
    box(ax, 2.9 + i * 4.2, 3.2, 1.3, 0.7, "learned", c=B, fs=6.5)
ax.text(0.2, 1.6, "on:", fontsize=8)
box(ax, 1.2, 1.2, 1.6, 0.7, "random\nwarm-up", c=G, fs=6.5)
box(ax, 2.9, 1.2, 6.6, 0.7, "learned … learned … learned (one study keeps learning)", c=B, fs=6.5)
ax.text(5, 0.3, "Risk: mixes results if flags/hose changed between batches.", ha="center", fontsize=7, color=R)
save(f, "opt_resume")

# --- opt_stepped: inlet bore section (generator view of a long tube is unreadable) -------------
f, ax = fig()
z = np.array([0, 6, 6, 30]); r_plain = np.full(4, 60.0); r_step = np.array([61.2, 61.2, 60, 60])
ax.plot([0, 30], [60, 60], color=G, lw=2, label="off: plain bore")
ax.plot(z, r_step, color=B, lw=2.5, label="on: stepped inlet")
ax.fill_between([12, 26], 50, 58.5, color="#e5e7eb"); ax.text(19, 54, "rotor\n(unchanged)", ha="center", fontsize=7)
ax.annotate("+1.2 mm", (3, 61.2), (3, 63), ha="center", fontsize=7, arrowprops=dict(arrowstyle="->"))
ax.annotate("6 mm long", (6, 60.6), (8, 62.5), fontsize=7, arrowprops=dict(arrowstyle="->"))
ax.set_ylim(50, 64); ax.set_xlabel("axial z from inlet (mm)"); ax.set_ylabel("bore radius (schematic)")
ax.legend(fontsize=7, loc="lower left", frameon=False)
ax.set_title("Stepped inlet: casing lip only (casing.py STEP_DEPTH/LEN)")
save(f, "opt_stepped")
