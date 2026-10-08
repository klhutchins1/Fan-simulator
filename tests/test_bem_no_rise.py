"""BEM never ranks a fan with no pressure rise at the sweep's max flow (roadmap §23.4)."""

from fansim.fan_bem import pq_curve
from fansim.geometry.blade import BladeParams
from fansim.geometry.config import load_blade_params
from fansim.optimize.system_curve import bem_screen_cfm


def test_no_blades_has_no_free_delivery():
    c = pq_curve(BladeParams(n_blades=0), 2000)
    assert (c.free_delivery_cfm, c.free_status) == (0.0, "no_rise")


def test_hub_bigger_than_tip_has_no_free_delivery():
    b = BladeParams()
    b.hub_radius, b.tip_radius = 60.0, 50.0
    assert pq_curve(b, 2000).free_status == "no_rise"


def test_stalled_reversed_blades_rank_last(monkeypatch):
    from fansim import fan_bem

    real = fan_bem.operating_point

    def never_positive(*a, **k):
        pt = real(*a, **k)
        return pt.__class__(pt.flow_cfm, pt.flow_m3s, -abs(pt.dp_static_pa) - 1.0,
                            pt.dp_total_pa, 0.0, pt.power_w, pt.converged)

    monkeypatch.setattr(fan_bem, "operating_point", never_positive)
    stock = load_blade_params("config/problems/a12x25_reference.yaml")
    c = pq_curve(stock, 2000)
    assert (c.free_delivery_cfm, c.free_status) == (0.0, "no_rise")
    assert bem_screen_cfm(stock, 2000, 8.0, 0.5) == (0.0, 0.0)


def test_stock_still_crosses_inside_the_sweep():
    c = pq_curve(load_blade_params("config/problems/a12x25_reference.yaml"), 2000)
    assert c.free_status == "crossed" and 50 < c.free_delivery_cfm < 70
