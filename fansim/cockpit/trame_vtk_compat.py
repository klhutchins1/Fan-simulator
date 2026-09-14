"""Defer VTK geometry push until the Trame/wslink protocol exists.

``plotter_ui`` / ``VtkRemoteLocalView`` call ``update_geometry`` during widget
construction, but ``server.protocol`` is only created when the server starts.
Current trame-vtk raises ``ValueError: Protocol does not exist yet``; geometry
is already scheduled again via ``on_server_ready``, so skipping the early push
is safe.
"""

from __future__ import annotations


def patch_trame_vtk_protocol_defer() -> None:
    try:
        from trame_vtk.widgets.vtk import common as vtk_common
    except Exception:  # noqa: BLE001
        return

    for name in ("VtkRemoteLocalView", "VtkLocalView", "VtkRemoteView"):
        cls = getattr(vtk_common, name, None)
        if cls is None or not hasattr(cls, "update_geometry"):
            continue
        meth = cls.update_geometry
        if getattr(meth, "_fansim_protocol_defer", False):
            continue

        def _make(orig):
            def update_geometry(self, *args, **kwargs):
                if not getattr(self.server, "protocol", None):
                    return None
                return orig(self, *args, **kwargs)

            update_geometry._fansim_protocol_defer = True  # type: ignore[attr-defined]
            return update_geometry

        cls.update_geometry = _make(meth)
