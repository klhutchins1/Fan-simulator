# lt120: Lin & Tsai inverse-design fan, 120 mm, 7 blades, 2000 rpm

- **Geometry:** Tutar, M. and Cam, J. B. (2025), "Computational Design of an Energy-Efficient Small Axial-Flow Fan Using Staggered Blades with Winglets", *Int. J. Turbomach. Propuls. Power* 10(1):1.
  - https://www.mdpi.com/2504-186X/10/1/1 (PDF via mdpi-res.com).
  - Table 1 ("baseline blade geometry") gives 10 segments, each with radius, chord, setting angle and NACA 4-digit section. The text gives 7 blades, rotor diameter 120 mm and hub diameter 50 mm.
- **Measurement:** the experimental static-pressure points come from Lin, S.-C. and Tsai, M.-L. (2011), *Proc. IMechE C* 225(4), doi:10.1243/09544062JMES2231. That paper describes a CNC-made prototype tested at 2000 rpm. It is paywalled and I did not read it, so the rig standard and uncertainty are unknown here.
  - The points used are the "Experimental Data" markers that Tutar & Cam re-plot in their Figs. 8 and 9.
- **Licence:** Tutar & Cam is CC BY 4.0. Numbers are cited with attribution, and no figure or text is copied. MIT release of the numbers is OK with this citation kept.
  - The underlying measurement belongs to Lin & Tsai (SAGE): we cite it and hold only the 5 digitised points.
- **Digitising:** the figures are vector graphics in the PDF.
  - Method: read marker centres with PyMuPDF; calibrate against minor tick marks (2 CFM and 1 Pa).
  - Fig. 8 and Fig. 9 agree within 0.02 Pa and 0.02 CFM.
  - Digitising error is below ±0.05 Pa and ±0.05 CFM, which is far smaller than the unknown measurement error.
- **Gaps:** only 5 points. There is no free-air point: the highest point is 84 CFM at 6.85 Pa.
- **Geometry quality: full.**
  - Assumed: the setting angle is measured from the rotation plane (it decreases from hub to tip, which is normal twist), and the tip gap is 0.5 mm (not reported).
  - Table radii run 23.0–56.5 mm, but the stated annulus is 25–60 mm. This mismatch is unexplained (see geometry.json).
