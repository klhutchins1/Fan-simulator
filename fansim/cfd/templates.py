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
addLayers       @ADDLAYERS@;

geometry
{
    impeller.stl { type triSurfaceMesh; name impeller; }
@FRAME_GEOM@@CASING_GEOM@@STATOR_GEOM@
}

castellatedMeshControls
{
    maxLocalCells 2000000;
    maxGlobalCells 6000000;
    minRefinementCells 10;
    maxLoadUnbalance 0.10;
    nCellsBetweenLevels 3;
    features
    (
        { file "impeller.eMesh"; level @FEATLVL@; }
@FRAME_FEAT@@CASING_FEAT@@STATOR_FEAT@
    );
    refinementSurfaces
    {
        impeller { level (@SURFMIN@ @SURFMAX@); patchInfo { type wall; } }
@FRAME_SURF@@CASING_SURF@@STATOR_SURF@
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
    layers
    {
@LAYER_PATCHES@
    }
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
@FRAME_EXTRACT@@CASING_EXTRACT@@STATOR_EXTRACT@
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


TOPOSET_DUAL_MRF = """@HEADER@
actions
(
    {
        name    rotorFrontCells;
        type    cellSet;
        action  new;
        source  cylinderToCell;
        point1  (0 0 @MRF_FRONT_ZMIN@);
        point2  (0 0 @MRF_FRONT_ZMAX@);
        radius  @MRFRADIUS@;
    }
    {
        name    rotorFront;
        type    cellZoneSet;
        action  new;
        source  setToCellZone;
        set     rotorFrontCells;
    }
    {
        name    rotorRearCells;
        type    cellSet;
        action  new;
        source  cylinderToCell;
        point1  (0 0 @MRF_REAR_ZMIN@);
        point2  (0 0 @MRF_REAR_ZMAX@);
        radius  @MRFRADIUS@;
    }
    {
        name    rotorRear;
        type    cellZoneSet;
        action  new;
        source  setToCellZone;
        set     rotorRearCells;
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
    nonRotatingPatches  (walls inlet outlet@FRAME_PATCH@@CASING_PATCH@@STATOR_PATCH@);
    origin              (0 0 0);
    axis                (0 0 1);
    omega               @OMEGA@;
}
"""


MRF_PROPERTIES_DUAL = """@HEADER@
MRF1
{
    cellZone            rotorFront;
    active              yes;
    nonRotatingPatches  (walls inlet outlet@FRAME_PATCH@@CASING_PATCH@@STATOR_PATCH@);
    origin              (0 0 0);
    axis                (0 0 1);
    omega               @OMEGA_FRONT@;
}
MRF2
{
    cellZone            rotorRear;
    active              yes;
    nonRotatingPatches  (walls inlet outlet@FRAME_PATCH@@CASING_PATCH@@STATOR_PATCH@);
    origin              (0 0 0);
    axis                (0 0 1);
    omega               @OMEGA_REAR@;
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
@FRAME_U@@CASING_U@@STATOR_U@
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
@FRAME_P@@CASING_P@@STATOR_P@
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
@FRAME_K@@CASING_K@@STATOR_K@
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
@FRAME_OMEGA@@CASING_OMEGA@@STATOR_OMEGA@
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
@FRAME_U@@CASING_U@@STATOR_U@
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
@FRAME_P@@CASING_P@@STATOR_P@
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
@FRAME_K@@CASING_K@@STATOR_K@
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
@FRAME_OMEGA@@CASING_OMEGA@@STATOR_OMEGA@
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
@IMPELLER_NUT@
@FRAME_NUT@@CASING_NUT@@STATOR_NUT@
}
"""
# ---- Prop open-air compressible MRF (rhoSimpleFoam) ----

PROP_THERMO = """@HEADER@
thermoType
{
    type            hePsiThermo;
    mixture         pureMixture;
    transport       const;
    thermo          hConst;
    equationOfState perfectGas;
    specie          specie;
    energy          sensibleInternalEnergy;
}
mixture
{
    specie { molWeight 28.9; }
    thermodynamics { Cp 1005; Hf 0; }
    transport { mu 1.8e-05; Pr 0.7; }
}
"""

PROP_CONTROL_DICT = """@HEADER@
application     rhoSimpleFoam;
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
        rho             rho;
        CofR            (0 0 0);
        writeControl    timeStep;
        writeInterval   @FOINT@;
    }
}
"""

PROP_MRF = """@HEADER@
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

PROP_TURBULENCE = """@HEADER@
simulationType RAS;
RAS { RASModel kOmegaSST; turbulence on; printCoeffs on; }
"""

PROP_FV_SCHEMES = """@HEADER@
ddtSchemes { default steadyState; }
gradSchemes { default Gauss linear; }
divSchemes
{
    default         none;
    div(phi,U)      bounded Gauss linearUpwind grad(U);
    div(phi,K)      bounded Gauss upwind;
    div(phi,h)      bounded Gauss upwind;
    div(phi,e)      bounded Gauss upwind;
    div(phi,k)      bounded Gauss upwind;
    div(phi,omega)  bounded Gauss upwind;
    div(((rho*nuEff)*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }
"""

PROP_FV_SOLUTION = """@HEADER@
solvers
{
    p
    {
        solver          GAMG;
        tolerance       1e-7;
        relTol          0.05;
        smoother        GaussSeidel;
    }
    "(U|h|e|k|omega)"
    {
        solver          smoothSolver;
        smoother        symGaussSeidel;
        tolerance       1e-8;
        relTol          0.1;
    }
    Phi
    {
        solver          GAMG;
        tolerance       1e-6;
        relTol          0.01;
        smoother        GaussSeidel;
    }
}
potentialFlow { nNonOrthogonalCorrectors 5; }
SIMPLE
{
    nNonOrthogonalCorrectors 1;
    consistent      no;
    residualControl { p 1e-4; U 1e-4; "(k|omega|h|e)" 1e-4; }
}
relaxationFactors
{
    fields    { p 0.3; }
    equations { U 0.7; "(k|omega|h|e)" 0.7; }
}
"""

PROP_FV_OPTIONS = """@HEADER@
"""

PROP_T = """@HEADER@
dimensions [0 0 0 1 0 0 0];
internalField uniform @T_INF@;
boundaryField
{
    inlet    { type fixedValue; value uniform @T_INF@; }
    outlet   { type inletOutlet; inletValue uniform @T_INF@; value uniform @T_INF@; }
    walls    { type zeroGradient; }
    impeller { type zeroGradient; }
}
"""

PROP_P = """@HEADER@
dimensions [1 -1 -2 0 0 0 0];
internalField uniform @P_INF@;
boundaryField
{
    inlet    { type freestreamPressure; freestreamValue uniform @P_INF@; value uniform @P_INF@; }
    outlet   { type freestreamPressure; freestreamValue uniform @P_INF@; value uniform @P_INF@; }
    walls    { type zeroGradient; }
    impeller { type zeroGradient; }
}
"""

PROP_U = """@HEADER@
dimensions [0 1 -1 0 0 0 0];
internalField uniform (0 0 @U_EPS@);
boundaryField
{
    inlet    { type freestreamVelocity; freestreamValue uniform (0 0 @U_EPS@); value uniform (0 0 @U_EPS@); }
    outlet   { type freestreamVelocity; freestreamValue uniform (0 0 @U_EPS@); value uniform (0 0 @U_EPS@); }
    walls    { type freestreamVelocity; freestreamValue uniform (0 0 @U_EPS@); value uniform (0 0 @U_EPS@); }
    impeller { type noSlip; }
}
"""

PROP_K = """@HEADER@
dimensions [0 2 -2 0 0 0 0];
internalField uniform @K@;
boundaryField
{
    inlet    { type inletOutlet; inletValue uniform @K@; value uniform @K@; }
    outlet   { type inletOutlet; inletValue uniform @K@; value uniform @K@; }
    walls    { type inletOutlet; inletValue uniform @K@; value uniform @K@; }
    impeller { type kqRWallFunction; value uniform @K@; }
}
"""

PROP_OMEGA = """@HEADER@
dimensions [0 0 -1 0 0 0 0];
internalField uniform @OMEGAT@;
boundaryField
{
    inlet    { type inletOutlet; inletValue uniform @OMEGAT@; value uniform @OMEGAT@; }
    outlet   { type inletOutlet; inletValue uniform @OMEGAT@; value uniform @OMEGAT@; }
    walls    { type inletOutlet; inletValue uniform @OMEGAT@; value uniform @OMEGAT@; }
    impeller { type omegaWallFunction; value uniform @OMEGAT@; }
}
"""

PROP_NUT = """@HEADER@
dimensions [0 2 -1 0 0 0 0];
internalField uniform 0;
boundaryField
{
    inlet    { type calculated; value uniform 0; }
    outlet   { type calculated; value uniform 0; }
    walls    { type calculated; value uniform 0; }
    impeller { type nutkWallFunction; value uniform 0; }
}
"""

PROP_ALPHAT = """@HEADER@
dimensions [1 -1 -1 0 0 0 0];
internalField uniform 0;
boundaryField
{
    inlet    { type calculated; value uniform 0; }
    outlet   { type calculated; value uniform 0; }
    walls    { type calculated; value uniform 0; }
    impeller { type compressible::alphatWallFunction; value uniform 0; }
}
"""


# --- DES / pimpleFoam overlay (roadmap §1.4 stage A; parked for absolute claims) ---

DES_FACE_FO = """
    desFace@IDX@
    {
        type            surfaceFieldValue;
        libs            (fieldFunctionObjects);
        writeControl    timeStep;
        writeInterval   @FOINT@;
        writeFields     false;
        log             false;
        regionType      sampledSurface;
        name            desFace@IDX@;
        sampledSurfaceDict
        {
            type        cuttingPlane;
            planeType   pointAndNormal;
            pointAndNormalDict
            {
                point   (@PX@ @PY@ @PZ@);
                normal  (@NX@ @NY@ @NZ@);
            }
            interpolate true;
        }
        operation       areaIntegrate;
        fields          (p);
    }
"""

DES_TURBULENCE = """@HEADER@
simulationType LES;
LES
{
    LESModel        kOmegaSSTDES;
    turbulence      on;
    printCoeffs     on;
    delta           cubeRootVol;
    cubeRootVolCoeffs { deltaCoeff 1; }
}
"""

DES_FV_SCHEMES = """@HEADER@
ddtSchemes      { default backward; }
gradSchemes     { default Gauss linear; }
divSchemes
{
    default         none;
    div(phi,U)      Gauss LUST grad(U);
    div(phi,k)      Gauss limitedLinear 1;
    div(phi,omega)  Gauss limitedLinear 1;
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }
wallDist { method meshWave; }
"""

DES_FV_SOLUTION = """@HEADER@
solvers
{
    p
    {
        solver          GAMG;
        tolerance       1e-6;
        relTol          0.01;
        smoother        DICGaussSeidel;
    }
    pFinal
    {
        $p;
        relTol          0;
    }
    "(U|k|omega)"
    {
        solver          smoothSolver;
        smoother        symGaussSeidel;
        tolerance       1e-6;
        relTol          0.1;
    }
    "(U|k|omega)Final"
    {
        $U;
        relTol          0;
    }
}
PIMPLE
{
    nOuterCorrectors 1;
    nCorrectors     2;
    nNonOrthogonalCorrectors 1;
}
"""

DES_CONTROL_DICT = """@HEADER@
application     pimpleFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         @ENDTIME@;
deltaT          @DELTAT@;
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
@DES_FACE_FOS@
}
"""
