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
    house the motor the impeller hub must be wide enough: hub_radius >= cavity_dia/2 + clearance +
    min_wall, and when grip pads are enabled also >= pad outer radius (see ``mount_min_hub_radius``).

    Optional **grip cylinders**: evenly spaced axial pads on the cavity wall (A12x25-style press-fit).
    The cup is cut slightly oversize (``grip_clearance_mm``), then cylinders are fused back with most of
    their body in the wall (``grip_protrude_mm`` into the cavity) so contact is at discrete pads.
    """
    cavity_dia_mm: float          # nominal motor boss OD the cup targets (before grip clearance)
    cavity_depth_mm: float        # cavity depth from the rear face
    rear_bore_dia_mm: float = 0.0  # smaller rear opening past the cavity (bearing/shaft region)
    shaft_dia_mm: float = 0.0      # motor shaft dia (reference; the shaft is on the MOTOR, not printed)
    min_wall_mm: float = 1.2       # min printable/strong hub wall around the cavity
    min_hub_height_mm: float = 0.0  # hub must be at least this TALL to house the cup + clear the frame
                                    # spokes (export grows the hub height to this; 0 = no requirement)
    grip_count: int = 0            # 0 = smooth cup; ~20 matches A12x25-style grip pads
    grip_dia_mm: float = 2.4       # diameter of each axial grip cylinder (mm)
    grip_clearance_mm: float = 0.35  # radial oversize of the cup cut before grips are fused back
    grip_protrude_mm: float = 0.35  # how far each pad sticks into the cavity (rest sits in the wall).
                                    # Equal to the default clearance, so the pad tips sit on cavity_dia_mm.


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


def mount_grip_pad_layout(mount: MotorMount) -> tuple[float, float, float] | None:
    """Return ``(cav_r, r_center, grip_r)`` for grip pads, or None if grips are off.

    Matches ``carve_motor_mount`` geometry so Fit / mount_min / export agree.
    """
    n_grip = int(getattr(mount, "grip_count", 0) or 0)
    grip_d = float(getattr(mount, "grip_dia_mm", 0.0) or 0.0)
    if n_grip <= 0 or grip_d <= 0.05:
        return None
    clear = float(getattr(mount, "grip_clearance_mm", 0.0) or 0.0)
    cav_r = float(mount.cavity_dia_mm) / 2.0 + clear
    grip_r = grip_d / 2.0
    protrude = float(getattr(mount, "grip_protrude_mm", 0.0) or 0.0)
    if protrude <= 0.0:
        # Unset means the pad tips stay on the motor-hub diameter, not 0.7 mm inside it.
        protrude = clear if clear > 0.0 else min(0.35, 0.35 * grip_d)
    protrude = min(protrude, max(0.15, grip_d - 0.1))
    wall_embed = grip_r - protrude
    if wall_embed < 0.05:
        wall_embed = 0.05
        protrude = grip_r - wall_embed
    r_center = cav_r - protrude + grip_r
    return cav_r, r_center, grip_r


def mount_min_hub_radius(spec: FanSpec) -> float | None:
    """Smallest impeller hub radius (mm) that can house this fan's motor with a printable wall
    (and grip pads when configured), or None if the model has no motor-mount defined.

    Below this, export either cannot carve the cup or silently skips grip pads.
    """
    m = spec.motor_mount
    if m is None:
        return None
    clear = float(m.grip_clearance_mm or 0.0)
    wall_need = m.cavity_dia_mm / 2.0 + clear + m.min_wall_mm
    layout = mount_grip_pad_layout(m)
    if layout is None:
        return wall_need
    _cav_r, r_center, grip_r = layout
    grip_need = r_center + grip_r + 0.05
    return max(wall_need, grip_need)


# Default sparse-FDM fill for weight gates (roadmap §2.4). Solid / resin use 1.0.
DEFAULT_PRINT_INFILL = 0.20


def _default_infill_frac(material: str) -> float:
    name = str(material or "").upper()
    if name in ("RESIN", "ABS_RESIN", "SLA") or "RESIN" in name:
        return 1.0
    return float(DEFAULT_PRINT_INFILL)


def estimate_weight_g(
    volume_mm3: float,
    material: str = DEFAULT_MATERIAL,
    *,
    infill_frac: float | None = None,
) -> float:
    """Printed part mass [g] from CAD solid volume [mm^3] and material density.

    ``volume_mm3`` is the watertight solid envelope. Multiply by ``infill_frac`` (0–1) for
    sparse FDM fills so the build-weight gate is not a 100%-infill pessimist (roadmap §2.4).
    Default is ``DEFAULT_PRINT_INFILL`` for filaments; resin defaults to solid (1.0).
    Pass ``infill_frac=1.0`` to force a solid-print mass.
    """
    density_kg_m3 = MATERIALS[material].density_kg_m3
    f = _default_infill_frac(material) if infill_frac is None else float(infill_frac)
    f = min(max(f, 0.0), 1.0)
    return volume_mm3 * density_kg_m3 * 1e-6 * f  # mm^3 → g via kg/m^3


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
        # max_weight_g is a *printed* mass budget (default estimate uses DEFAULT_PRINT_INFILL
        # for FDM; pass infill_frac=1.0 for solid). ~65 g leaves headroom for thick/high-solidity
        # blades under typical sparse fill; tune per model/print settings.
        # 0.50: researched (docs/qa/notes/motor-efficiency.md; audit 2026-10-10-motor-efficiency):
        # 0.40 slowed Stock to 1907 rpm although the real fan holds 2000 rpm.
        motor_efficiency=0.50, max_weight_g=65.0, material="PETG",
        ref_cfm=60.1, ref_static_pa=22.9, ref_noise_dba=22.6,
        # Motor interface: REAL MEASURED 2026-08-31 (user printed a fan + measured; the old 50 mm was a
        # WRONG Google value that made the printed hub oversize). The opening that slipped over the motor
        # is 37.25 mm inner dia — the pad tips, not the metal boss. The reference impeller STL
        # (validation/reference/a12x25_impeller.stl) has the same 37.25 mm inscribed opening.
        # Clearance opens the cut so the pads have wall to sit in; protrude equals that clearance so the
        # tips land back on 37.25. A 0.7 mm protrude (2026-09-15, d2aeed8) closed the tips to 36.55 mm
        # and the printed hub stopped fitting (H7MQ8). Cup ~13 mm deep; hub >=15 mm tall to clear the
        # frame spokes; ~20 mm rear bore; 3 mm shaft. Outer dia <=110 mm (tip_dia max above).
        # See [[fan-sim-a12x25-specs]].
        motor_mount=MotorMount(
            cavity_dia_mm=37.25, cavity_depth_mm=13.0, rear_bore_dia_mm=20.0,
            shaft_dia_mm=3.0, min_hub_height_mm=15.0,
            grip_count=20, grip_dia_mm=2.4, grip_clearance_mm=0.35, grip_protrude_mm=0.35,
        )),
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
USER_MODELS_DIR = Path(__file__).resolve().parents[1] / "config" / "fan_models"  # project-anchored (D8)
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
