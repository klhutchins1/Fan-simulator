"""Fourier Neural Operator (FNO) stub — requires stored flow-field snapshots (roadmap §7.4).

This module is intentionally honest: operator learning is not feasible without field data
(e.g., pressure/velocity snapshots). Until then, use tabular screens (GP, boost, NN).

Stage 1 snapshot dump: :mod:`fansim.surrogate.fields` + ``scripts/dump_field_snapshot.py``.
``available()`` is True only when at least one snapshot manifest exists under the default root.
Training/predict remain unimplemented until numeric tensor packing lands.
"""

from __future__ import annotations

from pathlib import Path

from fansim.surrogate.fields import snapshots_available

DEFAULT_SNAPSHOT_ROOT = Path("runs/field_snapshots")


def available(root: str | Path | None = None) -> bool:
    return snapshots_available(root or DEFAULT_SNAPSHOT_ROOT)


def train_fno(*args, **kwargs):
    raise NotImplementedError(
        "FNO needs numeric field tensors packed from snapshots; use "
        "scripts/dump_field_snapshot.py to ingest OF ASCII first, then a packer. "
        "Tabular screens: --surrogate-nn / --surrogate-boost (roadmap §7.4)."
    )


def predict_fno(*args, **kwargs):
    raise NotImplementedError(
        "FNO predict unavailable; no trained operator. See train_fno()."
    )
