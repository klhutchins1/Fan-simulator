"""OpenFOAM templates specific to the volute radial-discharge domain.

Axial duct templates keep inlet@Zmin / outlet@Zmax. Here inlet is the +Z face and
outlet is the +X face so flow can turn 90° into the scroll stub.
"""

from __future__ import annotations

VOLUTE_BLOCK_MESH = """@HEADER@
scale 1;

vertices
(
    (@XMIN@ @YMIN@ @ZMIN@)
    (@XMAX@ @YMIN@ @ZMIN@)
    (@XMAX@ @YMAX@ @ZMIN@)
    (@XMIN@ @YMAX@ @ZMIN@)
    (@XMIN@ @YMIN@ @ZMAX@)
    (@XMAX@ @YMIN@ @ZMAX@)
    (@XMAX@ @YMAX@ @ZMAX@)
    (@XMIN@ @YMAX@ @ZMAX@)
);

blocks
(
    hex (0 1 2 3 4 5 6 7) (@NX@ @NY@ @NZ@) simpleGrading (1 1 1)
);

edges ();

boundary
(
    inlet  { type patch; faces ((4 5 6 7)); }
    outlet { type patch; faces ((1 2 6 5)); }
    walls  { type wall;  faces ((0 3 2 1) (0 1 5 4) (3 0 4 7) (2 3 7 6)); }
);

mergePatchPairs ();
"""


# Inlet on +Z: flow enters toward −Z. Outlet on +X: radial discharge.
VOLUTE_U_PDRIVEN = """@HEADER@
dimensions      [0 1 -1 0 0 0 0];
internalField   uniform (0 0 @UGUESS@);
boundaryField
{
    inlet    { type pressureInletVelocity; value uniform (0 0 @UGUESS@); }
    outlet   { type pressureInletOutletVelocity; value uniform (@UGUESS_OUT@ 0 0); }
    walls    { type noSlip; }
    impeller { type noSlip; }
@CASING_U@
}
"""


VOLUTE_U_VDRIVEN = """@HEADER@
dimensions      [0 1 -1 0 0 0 0];
internalField   uniform (0 0 @UIN@);
boundaryField
{
    inlet    { type fixedValue; value uniform (0 0 @UIN@); }
    outlet   { type pressureInletOutletVelocity; value uniform (0 0 @UIN@); }
    walls    { type noSlip; }
    impeller { type noSlip; }
@CASING_U@
}
"""
