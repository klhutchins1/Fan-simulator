"""Focused §15.6 timings — phases + key ablations. Flush everything."""

from __future__ import annotations

import time

import cadquery as cq

from fansim.geometry.blade import (
    NOTCH_SPAN_SECTIONS,
    BladeParams,
    build_blade_solid,
    build_hub,
    build_impeller,
    _hub_axial_range,
)
from fansim.geometry.features import Features
from fansim.optimize.search_space import blade_from_flat, stock_blade_flat


def t(label: str, fn) -> float:
    t0 = time.perf_counter()
    fn()
    dt = time.perf_counter() - t0
    print(f"{label:48s} {dt:7.2f}s", flush=True)
    return dt


def stock_params(**kw) -> BladeParams:
    p = blade_from_flat(stock_blade_flat("a12x25"), Features())
    for k, v in kw.items():
        setattr(p, k, v)
    return p


def phases(p: BladeParams, title: str) -> None:
    print(f"\n--- phases: {title} ---", flush=True)
    blade = build_blade_solid(p)
    print(f"{'  (blade already built)':48s}", flush=True)
    z0, z1 = _hub_axial_range(p, blade)
    hub = build_hub(p, z0, z1)
    angles = [k * 360.0 / p.n_blades for k in range(p.n_blades)]
    blades = [blade.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), a) for a in angles]

    def fuse_clean():
        return hub.fuse(*blades).clean()

    t("  hub.fuse(N).clean()", fuse_clean)

    # rebuild for one-clean comparison (solids may be consumed)
    blades2 = [blade.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), a) for a in angles]

    def fuse_only():
        return hub.fuse(*blades2)

    solid = t("  hub.fuse(N) only", fuse_only)
    # can't clean consumed? use result
    # Actually fuse_only returned but we didn't capture - redo
    blades3 = [blade.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), a) for a in angles]
    fused = hub.fuse(*blades3)

    def just_clean():
        return fused.clean()

    t("  .clean() alone", just_clean)


def main() -> None:
    p = stock_params()
    print(
        f"stock: notches={p.tip_notch_count} n_span={p.n_span} "
        f"n_blades={p.n_blades} notch_floor={NOTCH_SPAN_SECTIONS} "
        f"cyl={p.cylindrical_tip} family={p.section_family}",
        flush=True,
    )

    print("\n=== full build_impeller ===", flush=True)
    t("stock (notches+cyl)", lambda: build_impeller(stock_params()))
    t(
        "no notches",
        lambda: build_impeller(stock_params(tip_notch_count=0, tip_notch_depth_mm=0.0)),
    )
    t(
        "no notches, no cyl tip",
        lambda: build_impeller(
            stock_params(
                tip_notch_count=0, tip_notch_depth_mm=0.0, cylindrical_tip=False
            )
        ),
    )
    t("BladeParams() default", lambda: build_impeller(BladeParams()))

    # Phase breakdown on no-notch (closer to old 13s recipe)
    phases(stock_params(tip_notch_count=0, tip_notch_depth_mm=0.0), "no notches")
    phases(stock_params(), "stock with notches")

    print("\nDONE", flush=True)


if __name__ == "__main__":
    main()
