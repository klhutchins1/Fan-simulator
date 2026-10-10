# nv150: Novaković et al. baseline fan, 150 mm, 6 blades, 3500 rpm

- **Source:** Novaković, T., Čurović, L., Hočevar, M. and Prezelj, J. (2024), "Impact of geometric modifications of small axial fans on psychoacoustic metrics", *Applied Acoustics* 218:109913, doi:10.1016/j.apacoust.2024.109913.
  - Open copy: https://repozitorij.uni-lj.si/IzpisGradiva.php?id=154385&lang=eng
- **Geometry:** Table 1 gives the design point, β∞ and α, chord L, arc sagitta f and thickness t at 4 radii. The text gives 6 blades, D = 150 mm, hub 56 mm and a 2 mm tip gap. Blades are free-vortex circular-arc plates, 3D-printed in ABS.
- **Measurement:** ISO 5801 / ISO 5136 rig at 3500 rpm with 16 throttle points.
  - Flow is measured with an ISO 5167 orifice and pressure with Krohne differential transmitters.
  - Torque comes from the servo-drive software, so eta is total efficiency on shaft power.
  - The paper gives no uncertainty figure.
- **Licence: CC BY-NC-ND 4.0, so NOT MIT-compatible as a work.** Only numeric values are held here, with citation. Before any MIT release of this folder, confirm with Kimball (or the authors) that extracted numbers are acceptable.
- **Digitising:** baseline (black-square) series, Fig. 6, top-right panel. The figure is a raster image, 1739×1318 px.
  - Method: square-marker template detection, calibrated to gridlines. Error is about ±0.002 in ψ and ±0.001 in φ (about ±1 Pa, ±0.0005 m³/s).
  - Lower-confidence points: φ = 0.0211, where the η point is partly hidden by another marker, and φ = 0.0806, where the ψ and η markers overlap and could be swapped (ψ 0.2267 vs 0.2299).
- **Conversion:**
  - q = φ·(πD²/4)·u and Δp_t = ψ·½ρu², with u = πD·n/60 and ρ = 1.2 kg/m³ (assumed). This reproduces the published design point (φ 0.14, ψ 0.17).
  - power_w = q·Δp_t/η is derived, not measured directly.
- **Pressure type: total.** The data do not reach free air (lowest ψ is 0.075).
- **Geometry quality: full.** Stagger = β∞ + α is derived. Table column "R" is read as station radius (see geometry.json).
