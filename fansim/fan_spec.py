# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""Fan-model constraint specs: the real-world envelope a candidate must fit to be BUILDABLE.

A FanSpec bundles a specific fan model's physical limits -- geometry (tip/hub diameter, depth),
mass, and the electrical/mechanical power budget (voltage x current -> shaft power) -- plus its
published performance targets. The optimizer gates candidates against the *selected model's* spec, so
it only produces fans that actually fit and can be driven on that motor. New fan models are new
FanSpec entries in the registry -- no engine change (the generality ethos, see fansim/problem/).

Some A12x25 values (weight ceiling, hub range) are reasonable estimates, not datasheet-exact -- they
are easy to refine per model; the electrical budget and envelope are from the datasheet.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fansim.manufacturability.materials import DEFAULT_MATERIAL, MATERIALS


@dataclass
class MotorMount:
    """Real motor-interface geometry a printed impeller needs to actually mount on the fan's motor.

    The impeller hub is a CUP that slips over the motor: an inner CAVITY (over the motor hub/stator),
    stepping down to a smaller REAR BORE (bearing/shaft region). Carved from the hub's REAR (motor)
    side at export — it's internal/hidden and does NOT affect the aero model (CFD is unchanged). To
    house the motor the impeller hub must be wide enough: hub_radius >= cavity_dia/2 + min_wall.
    """
    cavity_dia_mm: float          # inner cavity diameter (slips over the motor hub; add slip clearance)
    cavity_depth_mm: float        # cavity depth from the rear face
    rear_bore_dia_mm: float = 0.0  # smaller rear opening past the cavity (bearing/shaft region)
    shaft_dia_mm: float = 0.0      # motor shaft dia (reference; the shaft is on the MOTOR, not printed)
    min_wall_mm: float = 1.2       # min printable/strong hub wall around the cavity
    min_hub_height_mm: float = 0.0  # hub must be at least this TALL to house the cup + clear the frame
                                    # spokes (export grows the hub height to this; 0 = no requirement)


@dataclass
class FanSpec:
    name: str
    tip_dia_mm: tuple[float, float]   # (min, max) impeller tip diameter -- max must fit the frame
    hub_dia_mm: tuple[float, float]   # (min, max) hub diameter
    depth_mm: tuple[float, float]     # (min, max) axial depth -- max must fit the frame thickness
    rpm: float
    voltage_v: float
    max_current_a: float              # datasheet max current draw
    motor_efficiency: float = 0.40    # electrical -> shaft (assumption; calibrate per motor)
    max_weight_g: float | None = None
    material: str = DEFAULT_MATERIAL   # build material used for the weight estimate
    ref_cfm: float | None = None       # published performance (reference / validation targets)
    ref_static_pa: float | None = None
    ref_noise_dba: float | None = None
    motor_mount: "MotorMount | None" = None   # real motor interface (cup cavity + rear bore) for printing
    # LEEWAY: optional margins letting a design EXCEED the nominal limits for what-if exploration
    # (tip sticks out past the frame, blades extend further in Z, or over-voltage that may damage the
    # motor). Off by default (0) and never changes the nominal limits -- designs that use it are
    # ALLOWED but flagged 'over-spec' so the tradeoff is visible.
    leeway_tip_dia_mm: float = 0.0
    leeway_depth_mm: float = 0.0
    leeway_weight_g: float = 0.0
    over_voltage_v: float = 0.0        # extra volts allowed over nominal (raises the power budget)

    @property
    def max_power_w(self) -> float:
        """Nominal electrical power budget = voltage * max current."""
        return self.voltage_v * self.max_current_a

    @property
    def max_shaft_power_w(self) -> float:
        """Nominal mechanical (shaft) power available to drive the impeller."""
        return self.max_power_w * self.motor_efficiency

    @property
    def max_shaft_power_w_leeway(self) -> float:
        """Shaft power available if the leeway over-voltage is applied (may damage the motor)."""
        return (self.voltage_v + self.over_voltage_v) * self.max_current_a * self.motor_efficiency


def published_scatter_point(spec: FanSpec, load_pa: float) -> dict | None:
    """Map datasheet free-air + shut-off onto the cockpit (cfm_free, cfm_load) axes.

    Free delivery is ``spec.ref_cfm``. Load CFM is a **published linear P–Q** estimate
    intersected with the same ΔP=kQ² hose used for Assess (``load_pa`` @ 50 CFM) — not a
    CFD of the stock impeller. Returns None when the model has no published refs.
    """
    q_free = spec.ref_cfm
    p_shut = spec.ref_static_pa
    if q_free is None or p_shut is None:
        return None
    q_free = float(q_free)
    p_shut = float(p_shut)
    if q_free <= 0.0 or p_shut <= 0.0:
        return None
    load_pa = float(load_pa)
    if load_pa <= 0.0:
        q_load = q_free
    else:
        # Linear datasheet fan line: P/P_shut = 1 − Q/Q_free at the probe pressure.
        frac = min(max(1.0 - load_pa / p_shut, 1e-6), 1.0 - 1e-6)
        q_probe = q_free * frac
        try:
            from fansim.optimize.system_curve import SystemCurveError, intersect_fan_line, k_from_pa

            q_load, _ = intersect_fan_line(q_free, q_probe, load_pa, k_from_pa(load_pa))
        except (SystemCurveError, ValueError, ZeroDivisionError):
            q_load = q_probe
    return {
        "cfm_free": q_free,
        "cfm_load": float(q_load),
        "name": spec.name,
        "noise_dba": spec.ref_noise_dba,
        "kind": "published",
    }


def mount_min_hub_radius(spec: FanSpec) -> float | None:
    """Smallest impeller hub radius (mm) that can house this fan's motor with a printable wall, or
    None if the model has no motor-mount defined. Below this, the printed hub can't slip over the motor."""
    m = spec.motor_mount
    return None if m is None else m.cavity_dia_mm / 2.0 + m.min_wall_mm


def estimate_weight_g(volume_mm3: float, material: str = DEFAULT_MATERIAL) -> float:
    """Printed part mass [g] from solid volume [mm^3] and material density (assumes 100% infill)."""
    density_kg_m3 = MATERIALS[material].density_kg_m3
    return volume_mm3 * density_kg_m3 * 1e-6  # mm^3 * kg/m^3 * (1e-9 m^3/mm^3 * 1e3 g/kg)


def _within(val, rng, label, unit) -> str | None:
    lo, hi = rng
    if val < lo:
        return f"{label} {val:.1f} {unit} < min {lo:.1f}"
    if val > hi:
        return f"{label} {val:.1f} {unit} > max {hi:.1f}"
    return None


def check_build(spec: FanSpec, tip_dia_mm: float, hub_dia_mm: float, depth_mm: float,
                weight_g: float | None = None) -> tuple[bool, str]:
    """Geometry/mass gate against a model's envelope + leeway. Returns (ok, reason).

    The hard limits are nominal + leeway; a design within leeway passes here but is flagged by
    over_spec_flags(). Hub diameter has no leeway (it must physically fit the motor).
    """
    def hi_msg(val, rng, lee, label):
        lo, hi = rng
        if val < lo:
            return f"{label} {val:.1f} mm < min {lo:.1f}"
        if val > hi + lee:
            return f"{label} {val:.1f} mm > max {hi:.1f}" + (f"+leeway {lee:.1f}" if lee else "")
        return None
    for msg in (hi_msg(tip_dia_mm, spec.tip_dia_mm, spec.leeway_tip_dia_mm, "tip dia"),
                hi_msg(hub_dia_mm, spec.hub_dia_mm, 0.0, "hub dia"),
                hi_msg(depth_mm, spec.depth_mm, spec.leeway_depth_mm, "depth")):
        if msg:
            return False, f"{spec.name}: {msg}"
    if weight_g is not None and spec.max_weight_g is not None \
            and weight_g > spec.max_weight_g + spec.leeway_weight_g:
        return False, f"{spec.name}: weight {weight_g:.1f} g > max {spec.max_weight_g:.1f} g"
    return True, ""


def check_power(spec: FanSpec, shaft_power_w: float) -> tuple[bool, str]:
    """Motor power gate: shaft power must fit the budget (nominal, or the over-voltage leeway budget)."""
    cap = spec.max_shaft_power_w_leeway
    if shaft_power_w > cap:
        return False, (f"{spec.name}: needs {shaft_power_w:.2f} W shaft > motor {cap:.2f} W "
                       f"({spec.voltage_v + spec.over_voltage_v:.0f} V x {spec.max_current_a:.2f} A "
                       f"x {spec.motor_efficiency:.2f})")
    return True, ""


def over_spec_flags(spec: FanSpec, tip_dia_mm: float, depth_mm: float,
                    weight_g: float | None = None, shaft_power_w: float | None = None) -> list[str]:
    """Which NOMINAL limits a (leeway-allowed) design exceeds -- for storing/showing on results."""
    flags = []
    if tip_dia_mm > spec.tip_dia_mm[1]:
        flags.append(f"tip +{tip_dia_mm - spec.tip_dia_mm[1]:.1f} mm past frame")
    if depth_mm > spec.depth_mm[1]:
        flags.append(f"depth +{depth_mm - spec.depth_mm[1]:.1f} mm")
    if weight_g is not None and spec.max_weight_g is not None and weight_g > spec.max_weight_g:
        flags.append(f"weight +{weight_g - spec.max_weight_g:.1f} g")
    if shaft_power_w is not None and shaft_power_w > spec.max_shaft_power_w:
        flags.append(f"over-power {shaft_power_w:.2f} W > {spec.max_shaft_power_w:.2f} W nominal "
                     f"(needs over-voltage)")
    return flags


# --- registry: one real model; add more as FanSpec entries (no engine change) ---
_REGISTRY: dict[str, FanSpec] = {
    "a12x25": FanSpec(
        name="Noctua NF-A12x25", tip_dia_mm=(95.0, 110.0), hub_dia_mm=(30.0, 60.0),
        depth_mm=(10.0, 25.0), rpm=2000.0, voltage_v=12.0, max_current_a=0.14,
        # max_weight_g is the SOLID (100% infill) printed mass; realistic optimized impellers run
        # ~50 g solid, so 65 g leaves headroom and only rejects very heavy (thick/high-solidity)
        # blades. Real printed weight is lower with infill; tune per model/print settings.
        motor_efficiency=0.40, max_weight_g=65.0, material="PETG",
        ref_cfm=60.1, ref_static_pa=22.9, ref_noise_dba=22.6,
        # Motor interface: REAL MEASURED 2026-08-31 (user printed a fan + measured; the old 50 mm was a
        # WRONG Google value that made the printed hub oversize). Motor hub the printed cup slips over =
        # 37.25 mm inner dia; cup ~13 mm deep; hub must be >=15 mm tall to clear the frame spokes; ~20 mm
        # rear bore; 3 mm shaft. Outer dia must be <=110 mm to clear the frame (tip_dia max above).
        # See [[fan-sim-a12x25-specs]].
        motor_mount=MotorMount(cavity_dia_mm=37.25, cavity_depth_mm=13.0, rear_bore_dia_mm=20.0,
                               shaft_dia_mm=3.0, min_hub_height_mm=15.0)),
    # GENERIC 120 mm axial fan — the LOOSE exploratory envelope our early optimizer runs used, BEFORE
    # the real a12x25 frame was measured to 110 mm. The old designs (e.g. opt_extended2_t36 ~118 mm)
    # are good aero DATA; they just target a generic 120 mm slot, not the tighter real Noctua frame, so
    # they belong here rather than reading as 'over-spec a12x25'. No motor_mount (generic aero, no real
    # motor to fit). Same RPM/power as a12x25 so numbers stay comparable; no ref specs (not a real fan).
    "generic_120": FanSpec(
        name="Generic 120 mm axial (exploratory)", tip_dia_mm=(95.0, 119.0), hub_dia_mm=(30.0, 60.0),
        depth_mm=(10.0, 25.0), rpm=2000.0, voltage_v=12.0, max_current_a=0.14,
        motor_efficiency=0.40, max_weight_g=65.0, material="PETG"),
    # A very different company + regime: Delta high-power industrial 120x38 mm fan. ~11x the power
    # budget, ~2x RPM, 38 mm thick -> a genuinely different constraint envelope (proves generality).
    # Specs from the AFC1212DE datasheet; 12.5 mmH2O = 122.6 Pa. Weight cap generous for a 38 mm solid.
    "delta_afc1212de": FanSpec(
        name="Delta AFC1212DE", tip_dia_mm=(95.0, 119.0), hub_dia_mm=(30.0, 68.0),
        depth_mm=(10.0, 38.0), rpm=3900.0, voltage_v=12.0, max_current_a=1.60,
        motor_efficiency=0.40, max_weight_g=120.0, material="PETG",
        ref_cfm=148.3, ref_static_pa=122.6, ref_noise_dba=51.0),
}


def get_fan_spec(name: str) -> FanSpec:
    """Look up a fan model by key (e.g. 'a12x25'). Raises KeyError listing the known models."""
    try:
        return _REGISTRY[name]
    except KeyError:
        raise KeyError(f"unknown fan model {name!r}; known: {sorted(_REGISTRY)}") from None


def fan_spec_names() -> list[str]:
    return sorted(_REGISTRY)


def register_fan_spec(key: str, spec: FanSpec) -> None:
    """Add (or replace) a fan model in the registry -- used by 'import new model' from a file/UI."""
    _REGISTRY[key] = spec


# --- import/export so new fan models can be defined as files (or from the UI) ---
_TUPLE_FIELDS = ("tip_dia_mm", "hub_dia_mm", "depth_mm")


def fan_spec_to_dict(spec: FanSpec) -> dict:
    from dataclasses import asdict
    return asdict(spec)


def fan_spec_from_dict(d: dict) -> FanSpec:
    d = dict(d)
    for f in _TUPLE_FIELDS:
        if f in d and d[f] is not None:
            d[f] = tuple(d[f])            # YAML lists -> (min, max) tuples
    mm = d.get("motor_mount")
    if isinstance(mm, dict):
        d["motor_mount"] = MotorMount(**mm)   # nested dict -> MotorMount
    return FanSpec(**d)


def save_fan_spec(spec: FanSpec, path: str | Path) -> None:
    import yaml
    Path(path).write_text(yaml.safe_dump(fan_spec_to_dict(spec), sort_keys=False))


def load_fan_spec(path: str | Path) -> FanSpec:
    """Load one fan model from a YAML file (import). Does not auto-register."""
    import yaml
    return fan_spec_from_dict(yaml.safe_load(Path(path).read_text()))


def load_fan_models_dir(directory: str | Path = "config/fan_models") -> list[str]:
    """Import every *.yaml fan model in a directory into the registry (key = filename stem)."""
    d = Path(directory)
    added = []
    if d.exists():
        for p in sorted(d.glob("*.yaml")):
            try:
                register_fan_spec(p.stem, load_fan_spec(p))
                added.append(p.stem)
            except Exception:  # noqa: BLE001 - skip a malformed model file
                continue
    return added


# --- user fan-model CRUD --------------------------------------------------------------------------
# Built-in models are canonical REFERENCES (a real Noctua, a real Delta, the generic slot) and are
# read-only: you can't edit or delete them, so a measured reference can't be silently corrupted. To
# make a variant, SAVE it under a new name -> it becomes a USER model (a YAML in config/fan_models/)
# that you can freely edit or delete. This is the "delete-and-recreate" the user asked about, but the
# built-in stays put as the source of truth.
USER_MODELS_DIR = Path("config/fan_models")
_BUILTIN_MODELS = frozenset(_REGISTRY)   # snapshot BEFORE any YAML/user models are loaded


def is_builtin(name: str) -> bool:
    return name in _BUILTIN_MODELS


def save_user_fan_model(key: str, spec: FanSpec, directory: str | Path = USER_MODELS_DIR) -> Path:
    """Save (or overwrite) a USER fan model as config/fan_models/<key>.yaml and register it live.
    Refuses to overwrite a built-in name (save under a different key instead)."""
    if is_builtin(key):
        raise ValueError(f"'{key}' is a built-in reference model — save your variant under a new name")
    d = Path(directory)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{key}.yaml"
    save_fan_spec(spec, path)
    register_fan_spec(key, spec)
    return path


def delete_user_fan_model(key: str, directory: str | Path = USER_MODELS_DIR) -> bool:
    """Delete a USER fan model (its YAML + registry entry). Built-ins can't be deleted. Returns True
    if a model was removed."""
    if is_builtin(key):
        raise ValueError(f"'{key}' is a built-in reference model and can't be deleted")
    (Path(directory) / f"{key}.yaml").unlink(missing_ok=True)
    return _REGISTRY.pop(key, None) is not None


A12X25 = _REGISTRY["a12x25"]
load_fan_models_dir()  # auto-import any user-defined models on first import
