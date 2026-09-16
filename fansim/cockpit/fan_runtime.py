"""Shared optional-runtime handles for the Fan-tab binders (§13.9).

``pyvista`` and Trame's ``asynchronous`` are heavy and absent in the light test import, so
they are stubbed to ``None`` under pytest. Binders reference them as ``fan_runtime.pv`` /
``fan_runtime.asynchronous`` (attribute access at call time) so a test can monkeypatch a
single module instead of every binder.
"""

from __future__ import annotations

import sys

_RUNNING_TESTS = "pytest" in sys.modules

if _RUNNING_TESTS:
    pv = None  # type: ignore[assignment]
    asynchronous = None  # type: ignore[assignment]
else:  # pragma: no cover - exercised only in the live cockpit
    import pyvista as pv  # noqa: F401 - re-exported for binders
    from trame.app import asynchronous  # noqa: F401 - re-exported for binders
