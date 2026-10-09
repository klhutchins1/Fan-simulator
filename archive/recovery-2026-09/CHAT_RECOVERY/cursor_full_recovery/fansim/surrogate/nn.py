"""Optional NN regressor for surrogate prescreening (torch soft-dep; roadmap §7.4).

This is intentionally conservative: small fixed MLP, deterministic seed, CPU-only, and a
minimal wrapper API mirroring `BoostRegressor` and friends.
"""

from __future__ import annotations

import numpy as np

_IMPORT_ERR: str | None = None


def _import_torch():
    """Return (torch, torch.nn) or (None, None) if not installed."""
    global _IMPORT_ERR
    try:
        import torch  # type: ignore
        import torch.nn as tnn  # type: ignore
    except ImportError as exc:  # pragma: no cover - env without torch
        _IMPORT_ERR = str(exc)
        return None, None
    return torch, tnn


def available() -> bool:
    torch, _tnn = _import_torch()
    return torch is not None


def unavailable_reason() -> str:
    if available():
        return ""
    return _IMPORT_ERR or "torch not installed (pip install 'fansim[surrogate-nn]')"


def _as_2d_float(x) -> np.ndarray:
    return np.atleast_2d(np.asarray(x, dtype=float))


class _Mlp:  # torch.nn.Module, but avoid importing at module import time
    def __init__(self, input_dim: int, hidden: tuple[int, int]):
        torch, tnn = _import_torch()
        if torch is None or tnn is None:  # pragma: no cover - defensive
            raise ImportError(unavailable_reason())
        h1, h2 = hidden
        self.net = tnn.Sequential(
            tnn.Linear(input_dim, h1),
            tnn.ReLU(),
            tnn.Linear(h1, h2),
            tnn.ReLU(),
            tnn.Linear(h2, 1),
        )

    def parameters(self):
        return self.net.parameters()

    def train(self, mode: bool = True):
        self.net.train(mode)
        return self

    def eval(self):
        self.net.eval()
        return self

    def state_dict(self):
        return self.net.state_dict()

    def load_state_dict(self, sd):
        return self.net.load_state_dict(sd)

    def __call__(self, x):
        return self.net(x)


class NnRegressor:
    """Fixed small MLP regressor. `predict` returns shape (n,)."""

    def __init__(
        self,
        *,
        hidden: tuple[int, int] = (64, 32),
        lr: float = 1e-2,
        max_epochs: int = 200,
        patience: int = 25,
        min_delta: float = 1e-8,
    ):
        self.hidden = hidden
        self.lr = float(lr)
        self.max_epochs = int(max_epochs)
        self.patience = int(patience)
        self.min_delta = float(min_delta)
        self._model = None
        self._fitted = False
        self._xm = None
        self._xs = None

    def fit(self, X, y) -> "NnRegressor":
        torch, tnn = _import_torch()
        if torch is None or tnn is None:
            raise ImportError(unavailable_reason())
        from fansim.surrogate.features import FEATURE_KEYS

        X = _as_2d_float(X)
        y = np.asarray(y, float).ravel()
        d = len(FEATURE_KEYS)
        if X.shape[1] != d:
            raise ValueError(f"expected X with {d} features (FEATURE_KEYS), got {X.shape[1]}")

        # Deterministic CPU training.
        torch.manual_seed(0)

        self._xm = X.mean(0)
        self._xs = X.std(0)
        self._xs[self._xs == 0.0] = 1.0
        Xs = (X - self._xm) / self._xs

        xt = torch.tensor(Xs, dtype=torch.float32)
        yt = torch.tensor(y.reshape(-1, 1), dtype=torch.float32)

        model = _Mlp(d, self.hidden)
        model.train(True)
        opt = torch.optim.Adam(model.parameters(), lr=self.lr)
        loss_fn = tnn.MSELoss()

        best = float("inf")
        best_sd = None
        stale = 0
        for _epoch in range(self.max_epochs):
            opt.zero_grad(set_to_none=True)
            pred = model(xt)
            loss = loss_fn(pred, yt)
            loss.backward()
            opt.step()

            cur = float(loss.detach().cpu().item())
            if cur < best - self.min_delta:
                best = cur
                best_sd = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
                stale = 0
            else:
                stale += 1
                if stale >= self.patience:
                    break
            if best < 1e-10:
                break

        if best_sd is not None:
            model.load_state_dict(best_sd)
        self._model = model.eval()
        self._fitted = True
        return self

    def predict(self, X) -> np.ndarray:
        if not self._fitted or self._model is None or self._xm is None or self._xs is None:
            raise RuntimeError("call fit() before predict()")
        torch, _tnn = _import_torch()
        if torch is None:  # pragma: no cover - defensive
            raise ImportError(unavailable_reason())

        X = _as_2d_float(X)
        Xs = (X - self._xm) / self._xs
        xt = torch.tensor(Xs, dtype=torch.float32)
        with torch.no_grad():
            yhat = self._model(xt).detach().cpu().numpy().ravel()
        return np.asarray(yhat, dtype=float)
