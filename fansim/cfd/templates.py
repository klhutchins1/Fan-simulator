# RECOVERED-FROM-CHAT 2026-09-12 - verbatim from a Claude Code transcript (Aug26-Sep03 snapshot); BEHIND the drive-death state, later Cursor work (09-04/09-11) built on top. Prefer any real recovered copy; see README_RECOVERY.md.
"""OpenFOAM v2406 dictionary templates for a steady incompressible MRF fan case.

Placeholders are written as @NAME@ and substituted by :func:`render` to avoid clashing
with OpenFOAM's own ``{ }`` blocks.
"""

from __future__ import annotations

FOAM_HEADER = """FoamFile
{
    version     2.0;
    format      ascii;
    class       @CLASS@;
    object      @OBJECT@;
}
"""


def render(template: str, mapping: dict[str, object]) -> str:
    out = template
    for key, val in mapping.items():
        out = out.replace(f"@{key}@", str(val))
    return out


BLOCK_MESH = """@HEADER@
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
    inlet  { type patch; faces ((0 3 2 1)); }
    outlet { type patch; faces ((4 5 6 7)); }
    walls  { type wall;  faces ((0 1 5 4) (2 3 7 6) (1 2 6 5) (3 0 4 7)); }
);

mergePatchPairs ();
"""


SNAPPY = """@HEADER@
castellatedMesh true;
snap            true;
addLayers       false;

geometry
{
    impeller.stl { type triSurfaceMesh; name impeller; }
}

castellatedMeshControls
{
    maxLocalCells 2000000;
    maxGlobalCells 6000000;
    minRefinementCells 10;
    maxLoadUnbalance 0.10;
    nCellsBetweenLevels 3;
    features ( { file "impeller.eMesh"; level @FEATLVL@; } );
    refinementSurfaces
    {
        impeller { level (@SURFMIN@ @SURFMAX@); patchInfo { type wall; } }
    }
    resolveFeatureAngle 30;
    refinementRegions {}
    locationInMesh (@LOCX@ @LOCY@ @LOCZ@);
    allowFreeStandingZoneFaces true;
}

snapControls
{
    nSmoothPatch 3;
    tolerance 2.0;
    nSolveIter 30;
    nRelaxIter 5;
    nFeatureSnapIter 10;
    implicitFeatureSnap false;
    explicitFeatureSnap true;
    multiRegionFeatureSnap false;
}

addLayersControls
{
    relativeSizes true;
    layers {}
    expansionRatio 1.2;
    finalLayerThickness 0.3;
    minThickness 0.1;
    nGrow 0;
    featureAngle 60;
    nRelaxIter 3;
    nSmoothSurfaceNormals 1;
    nSmoothNormals 3;
    nSmoothThickness 10;
    maxFaceThicknessRatio 0.5;
    maxThicknessToMedialRatio 0.3;
    minMedialAxisAngle 90;
    nBufferCellsNoExtrude 0;
    nLayerIter 50;
}

meshQualityControls
{
    maxNonOrtho 65;
    maxBoundarySkewness 20;
    maxInternalSkewness 4;
    maxConcave 80;
    minVol 1e-13;
    minTetQuality 1e-15;
    minArea -1;
    minTwist 0.02;
    minDeterminant 0.001;
    minFaceWeight 0.02;
    minVolRatio 0.01;
    minTriangleTwist -1;
    nSmoothScale 4;
    errorReduction 0.75;
}

mergeTolerance 1e-6;
"""


SURFACE_FEATURES = """@HEADER@
impeller.stl
{
    extractionMethod extractFromSurface;
    extractFromSurfaceCoeffs { includedAngle 150; }
    subsetFeatures { nonManifoldEdges no; openEdges yes; }
    writeObj no;
}
"""


TOPOSET = """@HEADER@
actions
(
    {
        name    rotorCells;
        type    cellSet;
        action  new;
        source  cylinderToCell;
        point1  (0 0 @MRFZMIN@);
        point2  (0 0 @MRFZMAX@);
        radius  @MRFRADIUS@;
    }
    {
        name    rotor;
        type    cellZoneSet;
        action  new;
        source  setToCellZone;
        set     rotorCells;
    }
);
"""


DECOMPOSE_PAR = """@HEADER@
numberOfSubdomains @NPROCS@;
method          scotch;
"""


MRF_PROPERTIES = """@HEADER@
MRF1
{
    cellZone            rotor;
    active              yes;
    nonRotatingPatches  (walls inlet outlet);
    origin              (0 0 0);
    axis                (0 0 1);
    omega               @OMEGA@;
}
"""


TRANSPORT = """@HEADER@
transportModel Newtonian;
nu @NU@;
"""


TURBULENCE = """@HEADER@
simulationType RAS;
RAS { RASModel kOmegaSST; turbulence on; printCoeffs on; }
"""


CONTROL_DICT = """@HEADER@
application     simpleFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         @ENDTIME@;
deltaT          1;
writeControl    timeStep;
writeInterval   @WRITEINT@;
purgeWrite      2;
writeFormat     ascii;
writePrecision  7;
writeCompression off;
timeFormat      general;
runTimeModifiable true;

functions
{
    forces
    {
        type            forces;
        libs            (forces);
        patches         (impeller);
        rho             rhoInf;
        rhoInf          @RHO@;
        CofR            (0 0 0);
        writeControl    timeStep;
        writeInterval   @FOINT@;
    }
    outletFlow
    {
        type            surfaceFieldValue;
        libs            (fieldFunctionObjects);
        regionType      patch;
        name            outlet;
        operation       sum;
        fields          (phi);
        writeFields     false;
        writeControl    timeStep;
        writeInterval   @FOINT@;
    }
    inletP
    {
        type            surfaceFieldValue;
        libs            (fieldFunctionObjects);
        regionType      patch;
        name            inlet;
        operation       areaAverage;
        fields          (p);
        writeFields     false;
        writeControl    timeStep;
        writeInterval   @FOINT@;
    }
    outletP
    {
        type            surfaceFieldValue;
        libs            (fieldFunctionObjects);
        regionType      patch;
        name            outlet;
        operation       areaAverage;
        fields          (p);
        writeFields     false;
        writeControl    timeStep;
        writeInterval   @FOINT@;
    }
}
"""


FV_SCHEMES = """@HEADER@
ddtSchemes      { default steadyState; }
gradSchemes     { default Gauss linear; }
divSchemes
{
    default         none;
    div(phi,U)      bounded Gauss linearUpwindV grad(U);
    div(phi,k)      bounded Gauss upwind;
    div(phi,omega)  bounded Gauss upwind;
    turbulence      bounded Gauss upwind;
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
    div(nonlinearStress) Gauss linear;
}
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes   { default corrected; }
wallDist        { method meshWave; }
"""


FV_SOLUTION = """@HEADER@
solvers
{
    p
    {
        solver          GAMG;
        tolerance       1e-7;
        relTol          0.05;
        smoother        GaussSeidel;
    }
    Phi
    {
        solver          GAMG;
        tolerance       1e-6;
        relTol          0.01;
        smoother        GaussSeidel;
    }
    "(U|k|omega)"
    {
        solver          smoothSolver;
        smoother        symGaussSeidel;
        tolerance       1e-8;
        relTol          0.1;
    }
}

potentialFlow
{
    nNonOrthogonalCorrectors 5;
}

SIMPLE
{
    nNonOrthogonalCorrectors 1;
    consistent      no;
    residualControl { p 1e-4; U 1e-4; "(k|omega)" 1e-4; }
}

relaxationFactors
{
    fields    { p 0.3; }
    equations { U 0.7; "(k|omega)" 0.7; }
}
"""


# ---- 0/ field files (pressure-driven: total-pressure inlet, fixed back-pressure outlet) ----
# The flow the fan produces against @PBACK@ (kinematic) emerges from the blade design, so
# CFM becomes a real, blade-dependent objective. PBACK=0 gives the free-delivery point.

FIELD_U_PDRIVEN = """@HEADER@
dimensions [0 1 -1 0 0 0 0];
internalField uniform (0 0 @UGUESS@);
boundaryField
{
    inlet    { type pressureInletVelocity; value uniform (0 0 @UGUESS@); }
    outlet   { type pressureInletOutletVelocity; value uniform (0 0 @UGUESS@); }
    walls    { type slip; }
    impeller { type noSlip; }
}
"""

FIELD_P_PDRIVEN = """@HEADER@
dimensions [0 2 -2 0 0 0 0];
internalField uniform 0;
boundaryField
{
    inlet    { type totalPressure; p0 uniform 0; value uniform 0; }
    outlet   { type fixedValue; value uniform @PBACK@; }
    walls    { type zeroGradient; }
    impeller { type zeroGradient; }
}
"""

FIELD_K_PDRIVEN = """@HEADER@
dimensions [0 2 -2 0 0 0 0];
internalField uniform @K@;
boundaryField
{
    inlet    { type inletOutlet; inletValue uniform @K@; value uniform @K@; }
    outlet   { type inletOutlet; inletValue uniform @K@; value uniform @K@; }
    walls    { type slip; }
    impeller { type kqRWallFunction; value uniform @K@; }
}
"""

FIELD_OMEGA_PDRIVEN = """@HEADER@
dimensions [0 0 -1 0 0 0 0];
internalField uniform @OMEGAT@;
boundaryField
{
    inlet    { type inletOutlet; inletValue uniform @OMEGAT@; value uniform @OMEGAT@; }
    outlet   { type inletOutlet; inletValue uniform @OMEGAT@; value uniform @OMEGAT@; }
    walls    { type slip; }
    impeller { type omegaWallFunction; value uniform @OMEGAT@; }
}
"""


# ---- 0/ field files (velocity-driven: fixed inlet velocity, used for the fan-curve sweep) ----

FIELD_U = """@HEADER@
dimensions [0 1 -1 0 0 0 0];
internalField uniform (0 0 @UIN@);
boundaryField
{
    inlet    { type fixedValue; value uniform (0 0 @UIN@); }
    outlet   { type pressureInletOutletVelocity; value uniform (0 0 @UIN@); }
    walls    { type slip; }
    impeller { type noSlip; }
}
"""

FIELD_P = """@HEADER@
dimensions [0 2 -2 0 0 0 0];
internalField uniform 0;
boundaryField
{
    inlet    { type zeroGradient; }
    outlet   { type fixedValue; value uniform 0; }
    walls    { type zeroGradient; }
    impeller { type zeroGradient; }
}
"""

FIELD_K = """@HEADER@
dimensions [0 2 -2 0 0 0 0];
internalField uniform @K@;
boundaryField
{
    inlet    { type fixedValue; value uniform @K@; }
    outlet   { type inletOutlet; inletValue uniform @K@; value uniform @K@; }
    walls    { type slip; }
    impeller { type kqRWallFunction; value uniform @K@; }
}
"""

FIELD_OMEGA = """@HEADER@
dimensions [0 0 -1 0 0 0 0];
internalField uniform @OMEGAT@;
boundaryField
{
    inlet    { type fixedValue; value uniform @OMEGAT@; }
    outlet   { type inletOutlet; inletValue uniform @OMEGAT@; value uniform @OMEGAT@; }
    walls    { type slip; }
    impeller { type omegaWallFunction; value uniform @OMEGAT@; }
}
"""

FIELD_NUT = """@HEADER@
dimensions [0 2 -1 0 0 0 0];
internalField uniform 0;
boundaryField
{
    inlet    { type calculated; value uniform 0; }
    outlet   { type calculated; value uniform 0; }
    walls    { type slip; }
    impeller { type nutkWallFunction; value uniform 0; }
}
"""
