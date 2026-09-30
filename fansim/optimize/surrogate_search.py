"""Surrogate-guided search loop (roadmap §20.5).

Pro loop (software-first; CFD verify is opt-in):

  space-filling DoE → fit (GP / boost / NN ensemble) → NSGA-II on the surrogate
  → pick top-k using ensemble spread as acquisition → CFD-verify (or stub) → refit.

Reuses ``fansim.surrogate`` models and Optuna NSGA-II from ``study.py`` patterns.
Tests inject ``label_fn`` / ``verify_fn`` so Docker is never required.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Mapping, Sequence

import numpy as np

from fansim.optimize.search_space import BOUNDS, OBJECTIVE_NAMES, blade_from_flat
from fansim.surrogate.features import FEATURE_KEYS, feature_vector
from fansim.surrogate.gp import GaussianProcess

# Search DOFs used by DoE / NSGA (matches suggest_params core keys).
DOE_KEYS: tuple[str, ...] = (
    "n_blades",
    "stagger_root", "stagger_mid", "stagger_tip",
    "chord_root", "chord_mid", "chord_tip",
    "sweep_mid", "sweep_tip",
    "lean_mid", "lean_tip",
    "max_camber",
)

DEFAULT_HUB_TIP = {"hub_radius": 21.5, "tip_radius": 50.0}


@dataclass
class SurrogateCandidate:
    """One design ranked by the surrogate (μ) + uncertainty (σ)."""

    params: dict
    mu: dict[str, float]
    sigma: dict[str, float]
    acquisition: float = 0.0
    verified: dict[str, float] | None = None
    feasible: bool | None = None
    reason: str = ""


@dataclass
class GuidedSearchResult:
    """Full campaign snapshot after N rounds."""

    candidates: list[SurrogateCandidate]
    verified: list[SurrogateCandidate]
    X: np.ndarray
    y: dict[str, np.ndarray]
    rounds: int
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "rounds": self.rounds,
            "notes": list(self.notes),
            "n_train": int(len(self.X)),
            "verified": [
                {
                    "params": c.params,
                    "mu": c.mu,
                    "sigma": c.sigma,
                    "acquisition": c.acquisition,
                    "verified": c.verified,
                    "feasible": c.feasible,
                    "reason": c.reason,
                }
                for c in self.verified
            ],
        }


LabelFn = Callable[[dict], Mapping[str, float]]
VerifyFn = Callable[[dict, Path], tuple[bool, Mapping[str, float], str]]


def search_bounds(space: str = "guided") -> dict[str, tuple[float, float]]:
    """Continuous bounds for DoE / NSGA from ``BOUNDS[space]``."""
    b = BOUNDS.get(space) or BOUNDS["guided"]
    return {k: (float(b[k][0]), float(b[k][1])) for k in DOE_KEYS if k in b}


def latin_hypercube(n_samples: int, n_dims: int, seed: int = 42) -> np.ndarray:
    """Unit-cube Latin hypercube samples, shape ``(n_samples, n_dims)``."""
    n = max(1, int(n_samples))
    d = max(1, int(n_dims))
    rng = np.random.default_rng(int(seed))
    cut = np.linspace(0.0, 1.0, n + 1)
    u = np.empty((n, d), dtype=float)
    for j in range(d):
        u[:, j] = rng.uniform(cut[:-1], cut[1:])
        rng.shuffle(u[:, j])
    return u


def space_filling_doe(
    n: int,
    *,
    space: str = "guided",
    seed: int = 42,
    hub_tip: Mapping[str, float] | None = None,
) -> list[dict]:
    """Space-filling designs as flat param dicts (blade_from_flat-ready)."""
    bounds = search_bounds(space)
    keys = list(bounds.keys())
    u = latin_hypercube(n, len(keys), seed=seed)
    ht = {**DEFAULT_HUB_TIP, **(dict(hub_tip) if hub_tip else {})}
    out: list[dict] = []
    for row in u:
        p = dict(ht)
        for j, k in enumerate(keys):
            lo, hi = bounds[k]
            val = lo + float(row[j]) * (hi - lo)
            if k == "n_blades":
                p[k] = int(round(val))
                p[k] = max(int(lo), min(int(hi), p[k]))
            else:
                p[k] = float(val)
        # shroud defaults for feature_vector
        p.setdefault("shroud_thick_mm", 0.0)
        p.setdefault("shroud_height_frac", 1.0)
        out.append(p)
    return out


def design_matrix_from_params(params_list: Sequence[Mapping]) -> np.ndarray:
    """Stack feature vectors; skips incomplete rows (caller should pre-validate)."""
    return np.vstack([feature_vector(dict(p)) for p in params_list])


def fit_models(
    X: np.ndarray,
    y: Mapping[str, np.ndarray],
    *,
    boost: bool = False,
    nn: bool = False,
) -> dict[str, object]:
    """Fit one surrogate per objective. Prefers NN+GP, then boost+GP, else GP."""
    X = np.atleast_2d(np.asarray(X, float))
    models: dict[str, object] = {}
    for name, yy in y.items():
        yv = np.asarray(yy, float).ravel()
        if len(yv) < 2:
            continue
        models[name] = _fit_one(X, yv, boost=boost, nn=nn)
    return models


def _fit_one(X: np.ndarray, y: np.ndarray, *, boost: bool, nn: bool):
    if nn:
        try:
            from fansim.surrogate.ensemble import NnGpEnsemble
            from fansim.surrogate.nn import available as nn_available
            if nn_available():
                return NnGpEnsemble().fit(X, y)
        except Exception:  # noqa: BLE001
            pass
    if boost:
        try:
            from fansim.surrogate.boost import available
            from fansim.surrogate.ensemble import BoostGpEnsemble
            if available():
                return BoostGpEnsemble().fit(X, y)
        except Exception:  # noqa: BLE001
            pass
    return GaussianProcess().fit(X, y)


def predict_mu_sigma(
    models: Mapping[str, object],
    X: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    """Predict μ and σ for each fitted objective (σ=0 when model has no std)."""
    X = np.atleast_2d(np.asarray(X, float))
    mu: dict[str, np.ndarray] = {}
    sigma: dict[str, np.ndarray] = {}
    for name, model in models.items():
        pred = model.predict(X, return_std=True)
        if isinstance(pred, tuple):
            m, s = pred
            mu[name] = np.asarray(m, float).ravel()
            sigma[name] = np.asarray(s, float).ravel()
        else:
            mu[name] = np.asarray(pred, float).ravel()
            sigma[name] = np.zeros_like(mu[name])
    return mu, sigma


def acquisition_ucb(mu: float, sigma: float, kappa: float = 1.0) -> float:
    """Upper confidence bound using ensemble / GP spread as uncertainty."""
    return float(mu) + float(kappa) * float(sigma)


def select_top_k(
    candidates: Sequence[SurrogateCandidate],
    k: int,
    *,
    kappa: float = 1.0,
    objective: str = "cfm_free",
) -> list[SurrogateCandidate]:
    """Rank by UCB on ``objective`` (ensemble spread as acquisition signal)."""
    scored: list[SurrogateCandidate] = []
    for c in candidates:
        acq = acquisition_ucb(
            float(c.mu.get(objective, 0.0)),
            float(c.sigma.get(objective, 0.0)),
            kappa=kappa,
        )
        scored.append(
            SurrogateCandidate(
                params=dict(c.params),
                mu=dict(c.mu),
                sigma=dict(c.sigma),
                acquisition=acq,
                verified=c.verified,
                feasible=c.feasible,
                reason=c.reason,
            )
        )
    scored.sort(key=lambda c: c.acquisition, reverse=True)
    return scored[: max(0, int(k))]


def nsga_on_surrogate(
    models: Mapping[str, object],
    *,
    space: str = "guided",
    n_trials: int = 64,
    seed: int = 42,
    population_size: int = 16,
    hub_tip: Mapping[str, float] | None = None,
) -> list[SurrogateCandidate]:
    """NSGA-II maximizing surrogate μ for (cfm_free, cfm_load, efficiency)."""
    import optuna

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    bounds = search_bounds(space)
    ht = {**DEFAULT_HUB_TIP, **(dict(hub_tip) if hub_tip else {})}
    obj_names = [n for n in OBJECTIVE_NAMES if n in models]
    if not obj_names:
        return []

    sampler = optuna.samplers.NSGAIISampler(seed=seed, population_size=population_size)
    study = optuna.create_study(
        directions=["maximize"] * len(obj_names),
        sampler=sampler,
    )

    def _suggest(trial: optuna.Trial) -> dict:
        p = dict(ht)
        for k, (lo, hi) in bounds.items():
            if k == "n_blades":
                p[k] = trial.suggest_int(k, int(lo), int(hi))
            else:
                p[k] = trial.suggest_float(k, float(lo), float(hi))
        p.setdefault("shroud_thick_mm", 0.0)
        p.setdefault("shroud_height_frac", 1.0)
        return p

    def objective(trial: optuna.Trial):
        p = _suggest(trial)
        X = design_matrix_from_params([p])
        mu, sigma = predict_mu_sigma(models, X)
        trial.set_user_attr("params", p)
        trial.set_user_attr(
            "sigma", {n: float(sigma[n][0]) for n in obj_names if n in sigma})
        trial.set_user_attr(
            "mu", {n: float(mu[n][0]) for n in obj_names if n in mu})
        return tuple(float(mu[n][0]) for n in obj_names)

    study.optimize(objective, n_trials=max(1, int(n_trials)))

    out: list[SurrogateCandidate] = []
    for t in study.trials:
        if t.values is None:
            continue
        p = t.user_attrs.get("params") or {}
        mu = t.user_attrs.get("mu") or {
            n: float(t.values[i]) for i, n in enumerate(obj_names)
        }
        sigma = t.user_attrs.get("sigma") or {n: 0.0 for n in obj_names}
        # fill missing OBJECTIVE_NAMES for downstream select_top_k
        for n in OBJECTIVE_NAMES:
            mu.setdefault(n, 0.0)
            sigma.setdefault(n, 0.0)
        out.append(
            SurrogateCandidate(
                params=dict(p),
                mu={k: float(v) for k, v in mu.items()},
                sigma={k: float(v) for k, v in sigma.items()},
                acquisition=acquisition_ucb(
                    float(mu.get("cfm_free", 0.0)),
                    float(sigma.get("cfm_free", 0.0)),
                ),
            )
        )
    return out


def synthetic_label(params: Mapping) -> dict[str, float]:
    """Cheap deterministic ranking proxy for dry-run DoE / stub verify (no CFD).

    Correlates with tip chord + mid stagger so unit tests and Docker-free loops
    can fit a real GP without calling evaluate_candidate.
    """
    tip = float(params.get("chord_tip", 20.0))
    mid_st = float(params.get("stagger_mid", 30.0))
    nb = float(params.get("n_blades", 7))
    cam = float(params.get("max_camber", 0.03))
    cfm_free = 2.0 * tip + 0.4 * mid_st + 0.5 * nb - 40.0 * cam
    cfm_load = 0.55 * cfm_free + 0.1 * tip
    efficiency = 8.0 + 0.15 * mid_st + 0.05 * tip - 20.0 * cam
    return {
        "cfm_free": float(cfm_free),
        "cfm_load": float(cfm_load),
        "efficiency": float(efficiency),
    }


def stub_verify(params: Mapping, workdir: Path) -> tuple[bool, dict[str, float], str]:
    """Docker-free verify: write synthetic labels under ``workdir``."""
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    y = synthetic_label(params)
    (workdir / "stub_result.json").write_text(
        json.dumps({"params": dict(params), **y}, indent=2), encoding="utf-8")
    return True, y, "stub-verify"


def make_cfd_verify_fn(
    *,
    procs: int = 8,
    base_cell: float = 0.005,
    iters: int = 1000,
    load_pa: float = 1.0,
    fan_model: str = "a12x25",
    material: str = "PETG",
) -> VerifyFn:
    """Build a verify_fn that calls ``evaluate_candidate`` (needs Docker/OpenFOAM)."""

    def _verify(params: Mapping, workdir: Path) -> tuple[bool, dict[str, float], str]:
        from fansim.fan_spec import get_fan_spec
        from fansim.optimize.objectives import evaluate_candidate

        bp = blade_from_flat(dict(params))
        result = evaluate_candidate(
            bp, Path(workdir),
            procs=procs, base_cell=base_cell, iters=iters, load_pa=load_pa,
            material=material, spec=get_fan_spec(fan_model),
        )
        y = {
            "cfm_free": float(result.cfm_free),
            "cfm_load": float(result.cfm_load),
            "efficiency": float(result.efficiency),
        }
        return bool(result.feasible), y, str(result.reason or "")

    return _verify


def _append_labels(
    X: np.ndarray,
    y: dict[str, np.ndarray],
    params_list: Sequence[Mapping],
    labels: Sequence[Mapping[str, float]],
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    rows = [feature_vector(dict(p)) for p in params_list]
    if not rows:
        return X, y
    X2 = np.vstack([X, np.vstack(rows)]) if len(X) else np.vstack(rows)
    y2 = {k: np.asarray(v, float).ravel().copy() for k, v in y.items()}
    for name in OBJECTIVE_NAMES:
        vals = [float(lab[name]) for lab in labels]
        if name in y2 and len(y2[name]):
            y2[name] = np.append(y2[name], vals)
        else:
            y2[name] = np.asarray(vals, dtype=float)
    return X2, y2


def seed_from_catalog(
    db: str | Path | None,
    *,
    min_rows: int = 8,
) -> tuple[np.ndarray, dict[str, np.ndarray], str]:
    """Optional catalog seed with aligned (X, y) for all three objectives.

    Efficiency is rarely in the catalog; when missing we use a soft prior
    ``0.2 * cfm_free`` so GP training stays row-aligned. Empty when unavailable.
    """
    empty_X = np.zeros((0, len(FEATURE_KEYS)))
    empty_y = {n: np.zeros(0) for n in OBJECTIVE_NAMES}
    if db is None:
        return empty_X, empty_y, "no db"
    from fansim.catalog import load_catalog
    from fansim.surrogate.catalog import training_xy

    path = Path(db)
    if not path.exists():
        return empty_X, empty_y, f"no catalog at {path}"
    entries = load_catalog(path)
    Xf, yf = training_xy(entries, y_attr="cfm_free")
    if len(yf) < min_rows:
        return empty_X, empty_y, f"{len(yf)} free rows (need {min_rows})"
    Xl, yl = training_xy(entries, y_attr="cfm_load", require_k=True)
    if len(yl) == len(yf):
        y_load = yl
    else:
        y_load = 0.55 * yf
    y = {
        "cfm_free": yf,
        "cfm_load": y_load,
        "efficiency": 0.2 * yf,
    }
    return Xf, y, f"seeded {len(yf)} free rows from catalog"


def run_surrogate_guided(
    *,
    out_dir: str | Path,
    n_doe: int = 24,
    n_nsga: int = 64,
    top_k: int = 4,
    n_rounds: int = 2,
    space: str = "guided",
    seed: int = 42,
    kappa: float = 1.0,
    boost: bool = False,
    nn: bool = False,
    catalog_db: str | Path | None = None,
    label_fn: LabelFn | None = None,
    verify_fn: VerifyFn | None = None,
    verify_cfd: bool = False,
    fan_model: str = "a12x25",
    procs: int = 8,
    base_cell: float = 0.005,
    iters: int = 1000,
    load_pa: float = 1.0,
    material: str = "PETG",
) -> GuidedSearchResult:
    """Run DoE → fit → NSGA-on-surrogate → top-k verify → refit for ``n_rounds``.

    When ``verify_cfd`` is True and no ``verify_fn`` is given, attempts CFD via
    ``evaluate_candidate``. Otherwise uses ``stub_verify`` (Docker-free).
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    notes: list[str] = []
    label = label_fn or synthetic_label

    if verify_fn is None:
        if verify_cfd:
            try:
                from fansim.cfd.runner import image_available
                if image_available():
                    verify_fn = make_cfd_verify_fn(
                        procs=procs, base_cell=base_cell, iters=iters,
                        load_pa=load_pa, fan_model=fan_model, material=material,
                    )
                    notes.append("verify=cfd")
                else:
                    verify_fn = stub_verify
                    notes.append("verify=stub (Docker image missing)")
            except Exception as exc:  # noqa: BLE001
                verify_fn = stub_verify
                notes.append(f"verify=stub ({exc})")
        else:
            verify_fn = stub_verify
            notes.append("verify=stub")

    X, y, seed_note = seed_from_catalog(catalog_db)
    notes.append(seed_note)

    doe = space_filling_doe(n_doe, space=space, seed=seed)
    doe_labels = [dict(label(p)) for p in doe]
    X, y = _append_labels(X, y, doe, doe_labels)
    notes.append(f"DoE n={len(doe)}")

    # Guard: all objectives must match X rows
    if any(len(y[n]) != len(X) for n in OBJECTIVE_NAMES):
        X = design_matrix_from_params(doe)
        y = {
            n: np.asarray([float(lab[n]) for lab in doe_labels], float)
            for n in OBJECTIVE_NAMES
        }
        notes.append("training reset to DoE-only (catalog length mismatch)")

    verified_all: list[SurrogateCandidate] = []
    last_top: list[SurrogateCandidate] = []

    for rnd in range(max(1, int(n_rounds))):
        y_fit = {k: v for k, v in y.items() if len(v) == len(X) and len(v) >= 2}
        if "cfm_free" not in y_fit:
            notes.append(f"round {rnd}: abort — need ≥2 cfm_free labels")
            break
        models = fit_models(X, y_fit, boost=boost, nn=nn)
        pool = nsga_on_surrogate(
            models, space=space, n_trials=n_nsga, seed=seed + rnd,
        )
        top = select_top_k(pool, top_k, kappa=kappa)
        last_top = top
        notes.append(f"round {rnd}: NSGA pool={len(pool)} top_k={len(top)}")

        round_params: list[dict] = []
        round_labels: list[dict] = []
        for i, cand in enumerate(top):
            wdir = out_dir / "verify" / f"r{rnd}_k{i}"
            ok, ylab, reason = verify_fn(cand.params, wdir)
            cand.feasible = bool(ok)
            cand.reason = reason
            cand.verified = {k: float(ylab[k]) for k in OBJECTIVE_NAMES if k in ylab}
            verified_all.append(cand)
            if ok and cand.verified:
                round_params.append(cand.params)
                round_labels.append(cand.verified)

        if round_params:
            X, y = _append_labels(X, y, round_params, round_labels)
            notes.append(f"round {rnd}: refit += {len(round_params)} verified")
        else:
            notes.append(f"round {rnd}: no feasible verifies to refit")

    result = GuidedSearchResult(
        candidates=last_top,
        verified=verified_all,
        X=X,
        y=y,
        rounds=int(n_rounds),
        notes=notes,
    )
    (out_dir / "surrogate_guided.json").write_text(
        json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    return result
