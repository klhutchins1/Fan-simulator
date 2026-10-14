"""Prop readout compares BEMT with the class's typical figures (roadmap §23.18)."""

from types import SimpleNamespace

from fansim.cockpit.prop_tab import prop_reference_line, prop_static_headline
from fansim.prop_spec import get_prop_spec


def test_prop_headline_says_max_rpm_static():
    spec = get_prop_spec("fpv_5inch")
    line = prop_static_headline(spec)
    assert "@ 30,000 rpm (max), static" in line
    assert "3-blade" in line
    assert "5.0×4.3" in line or "5.0x4.3" in line


def test_fpv_5inch_reference_line():
    spec = get_prop_spec("fpv_5inch")
    line = prop_reference_line(spec, SimpleNamespace(thrust_g=2087.0, power_w=743.0))
    assert "1850 g / 650 W" in line and "thrust +13%" in line and "power +14%" in line


def test_reference_scaled_by_affinity_laws_and_absent_reference():
    spec = SimpleNamespace(ref_thrust_g=1000.0, ref_power_w=100.0, ref_rpm=10000.0, rpm_max=20000.0)
    line = prop_reference_line(spec, SimpleNamespace(thrust_g=4000.0, power_w=800.0))
    assert "4000 g / 800 W" in line and "+0%" in line
    assert prop_reference_line(SimpleNamespace(rpm_max=1.0), SimpleNamespace()) == ""
