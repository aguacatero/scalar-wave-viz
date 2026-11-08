/**
 * Propulsion Explorer 3D (V0) — Interactive 3D Laboratory
 * Scalar Wave Viz — Visualizing Fields, Forces, and Whole-Body Conservation
 *
 * Remediated for Review Round V0 R2:
 * - V0-R1-F1: Removed invented numeric force values. Uses qualitative schematic vectors.
 * - V0-R1-F2: Corrected electric field direction (E = -grad Phi points ground -> cathode),
 *             zero-voltage behavior (vanishes at 0 kV), and labeled schematic flux paths.
 * - V0-R1-F3: Repaired keyboard orbit & zoom using robust spherical coordinate math.
 * - V0-R1-F4: Clarified system boundaries (DUT vs External Chamber Environment).
 * - V0-R1-M1: Dynamically updates all UI elements, legends, and inspector on slider changes.
 * - V0-R1-M2: Enabled enclosure wall raycasting and pointer hover inspection.
 * - V0-R1-M3: Synchronized physical mesh dimensions with JSON and bounded gap sweep.
 * - V0-R1-M4: Semantic HTML math, modal focus trapping, and responsive mobile handling.
 */

(function () {
  'use strict';

  // --- Embedded Fallback Provenance Data (used if fetch fails on file://) ---
  const DEFAULT_PROVENANCE_DATA = {
    metadata: {
      project: "Scalar Wave Viz",
      application: "Propulsion Explorer 3D (V0)",
      version: "0.5.0-r5",
      citation: "Exodus Propulsion Technologies US11511891B2 FIGS. 4-8",
      scientific_disposition: "EDUCATIONAL_3D_EXPLORER_NO_UNVERIFIED_THRUST",
      evidence_grade: "PROVISIONAL_ILLUSTRATIVE_SCENE",
      date: "2026-11-02",
      note: "V0 displays qualitative schematic force directions and illustrative field paths. No quantitative force magnitudes are established or claimed."
    },
    four_questions: {
      what_am_i_seeing: "An illustrative 3D model of an asymmetric electrostatic electrode pair inspired by Exodus Propulsion Technologies patent US11511891B2 (FIGS. 4–8). It depicts a tapered knife-edge blade cathode, an opposing planar ground counter-electrode, solid dielectric potting, and a surrounding grounded conductive test chamber.",
      why_does_it_happen: "Sharp conductor edges concentrate electric field lines (E &prop; 1/r), producing intense local Maxwell electrostatic tension pulling on the blade edge. In full 3D electrostatics, the vacuum Maxwell stress tensor component is T_xx = &epsilon;_0 (E_x^2 - &frac12;|E|^2) = &frac12;&epsilon;_0 (E_x^2 - E_y^2 - E_z^2); the simplified scalar form &frac12;&epsilon;_0 E_x^2 is an idealized 1D approximation where transverse fields vanish. Conventional electric field vectors E = -&nabla;&Phi; point from higher potential (ground, 0 V) toward lower potential (cathode, -20 kV). Newton's third law requires equal and opposite electrostatic reaction forces on the opposing ground electrode, dielectric material, and chamber enclosure.",
      what_changes_it: "Electrostatic forces scale quadratically with applied voltage (F &prop; V^2). Sharper blade geometry intensifies local peak field gradients. Dielectric choice alters polarization stress (modeled in V0 as a visual density/opacity proxy; continuous field redistribution deferred to solver-backed V1). Closer chamber walls increase capacitive coupling and image-charge reaction forces.",
      how_could_we_test_it: "To determine whether an asymmetric electrostatic geometry produces genuine propellantless propulsion, the entire isolated test article must be operated in high vacuum (< 10^-5 Torr) on a calibrated micro-Newton torsion pendulum (Tajmar & Schreiber 2020). Null controls must isolate corona ion wind, outgassing, electrostatic image forces on chamber walls, and thermal expansion."
    },
    components: [
      {
        id: "blade_electrode",
        name: "Asymmetric High-Voltage Blade",
        role: "Active cathode with sharp tapered knife-edge",
        citation: "US11511891B2, FIGS. 4–8; col. 6 lines 15–45 (tapered blade cathode)",
        material: "High-conductivity copper / brass",
        default_potential_v: -20000.0,
        provenance_badge: "PUBLISHED HYPOTHESIS",
        dimensions_mm: { width: 30.0, height: 25.4, thickness: 3.0, tip_radius: 0.1 },
        tip_radius_modeled_in_mesh: false,
        tip_geometry_note: "The V0 3D mesh models an idealized zero-radius knife-edge wedge vertex (r = 0); the cited patent specification (US11511891B2, FIG. 6 / col. 6 lines 15-45) indicates r ≈ 0.1 mm tip curvature. Tip curvature rounding is documented source metadata and is not filleted in the V0 polygonal geometry.",
        system_boundary: "DEVICE_UNDER_TEST",
        force_nature: "Attractive electrostatic traction toward ground electrode",
        schematic_direction: "+X (Forward traction toward ground)",
        force_magnitude_status: "SCHEMATIC_VECTOR_NOT_COMPUTED_IN_V0",
        status: "SCHEMATIC_TRACTION_DIRECTION (UNMEASURED IN V0)"
      },
      {
        id: "ground_electrode",
        name: "Ground Counter-Electrode",
        role: "Planar collector electrode held at reference ground potential (0 V)",
        citation: "US11511891B2, FIGS. 4–8; col. 6 lines 46–60",
        material: "Polished aluminum plate / collector mesh",
        default_potential_v: 0.0,
        provenance_badge: "ESTABLISHED MODEL",
        dimensions_mm: { width: 4.0, height: 40.0, depth: 50.8 },
        surface_gap_definition: "Surface-to-surface distance d from knife edge (x=0) to near planar face (x=d). With plate thickness 4 mm, center is at x=d+2.0 mm.",
        system_boundary: "DEVICE_UNDER_TEST",
        force_nature: "Attractive electrostatic reaction traction toward blade",
        schematic_direction: "-X (Reaction traction toward blade)",
        force_magnitude_status: "SCHEMATIC_VECTOR_NOT_COMPUTED_IN_V0",
        status: "SCHEMATIC_REACTION_DIRECTION (UNMEASURED IN V0)"
      },
      {
        id: "dielectric_block",
        name: "Solid Dielectric Barrier / Potting",
        role: "High-voltage breakdown suppression and dielectric polarization region",
        citation: "US11511891B2, FIGS. 6B, 21, 23A; col. 7 lines 30–55 (dielectric medium 600 / high-voltage epoxy potting)",
        material: "Epoxy resin / PTFE / FR-4",
        default_eps_r: 3.8,
        provenance_badge: "WHAT-IF PARAMETER",
        dimensions_mm: { width: 16.0, height: 30.0, depth: 45.0 },
        system_boundary: "DEVICE_UNDER_TEST",
        force_nature: "Dielectric virtual-work polarization stress toward highest field gradient",
        schematic_direction: "-X (Polarization stress toward blade)",
        force_magnitude_status: "SCHEMATIC_VECTOR_NOT_COMPUTED_IN_V0",
        status: "INTERNAL_MATERIAL_POLARIZATION_STRESS",
        permittivity_status: "VISUAL_MATERIAL_PROXY_ONLY_IN_V0",
        note: "Illustrative single-stage potting block in V0 representing patent dielectric medium 600 / epoxy potting. Does not reproduce the multi-blade FIG. 21 test article. Permittivity slider is a visual material proxy adjusting visual rendering/opacity only; continuous field redistribution, polarization force scaling, and capacitive coupling are not recalculated in V0 and will be introduced in solver-backed V1. Note that patent FIG. 7 depicts electrostatic pressure-force vectors, not dielectric specification."
      },
      {
        id: "support_mount",
        name: "Structural Support Mount",
        role: "Rigid non-conductive mechanical frame holding electrodes at fixed separation",
        citation: "Experimental apparatus mechanical requirement",
        material: "Delrin / PEEK non-conductive stand",
        default_potential_v: null,
        provenance_badge: "ESTABLISHED MODEL",
        dimensions_mm: { width: 90.0, height: 8.0, depth: 90.0 },
        system_boundary: "DEVICE_UNDER_TEST",
        force_nature: "Internal mechanical constraint holding electrodes apart against electrostatic attraction",
        schematic_direction: "+X (Structural reaction opposing ground pull)",
        force_magnitude_status: "SCHEMATIC_VECTOR_NOT_COMPUTED_IN_V0",
        status: "INTERNAL_STRUCTURAL_CONSTRAINT"
      },
      {
        id: "enclosure_walls",
        name: "Conductive Enclosure (Chamber)",
        role: "Faraday shield, vacuum chamber boundary, and capacitive return boundary",
        citation: "Standard vacuum chamber / grounded enclosure",
        material: "Stainless steel chamber",
        default_potential_v: 0.0,
        provenance_badge: "ESTABLISHED MODEL",
        dimensions_mm: { width: 160.0, height: 120.0, depth: 160.0 },
        system_boundary: "EXTERNAL_ENVIRONMENT",
        force_nature: "Wall reaction traction from image charges induced on external chamber boundary",
        schematic_direction: "-X (External wall image-charge coupling)",
        force_magnitude_status: "SCHEMATIC_VECTOR_NOT_COMPUTED_IN_V0",
        status: "EXTERNAL_ENVIRONMENT_COUPLING"
      }
    ],
    null_controls: [
      {
        name: "High-Vacuum Control (< 10^-5 Torr)",
        purpose: "Eliminate corona discharge, aerodynamic ion wind, and air convection",
        reference: "Tajmar & Schreiber (2020), J. Electrostat."
      },
      {
        name: "Polarity Inversion Control",
        purpose: "Reverse voltage polarity (+V to -V). Pure electrostatic force is symmetric (F ~ V^2); unipolar discharge or leakage shifts asymmetrically.",
        reference: "Standard electrostatic experimental methodology"
      },
      {
        name: "Enclosure Clearance Sweep",
        purpose: "Vary distance to conductive vacuum chamber walls to isolate image-charge coupling forces.",
        reference: "Exodus model contract (docs/EXODUS_MODEL_CONTRACT.md)"
      },
      {
        name: "Isolated Center-of-Mass Torsion Balance",
        purpose: "Measure net force on entire closed system including power source, avoiding lead-wire artifacts.",
        reference: "Tajmar & Schreiber (2020)"
      }
    ]
  };

  // --- State Variables ---
  let provenanceData = DEFAULT_PROVENANCE_DATA;
  let scene, camera, renderer, controls;
  let raycaster, mouse;
  let componentMeshes = {};
  let pickableObjects = [];
  let fieldGroup, forceGroup, geometryGroup, enclosureGroup;
  let selectedComponentId = null;
  let hoveredObject = null;
  let lastFocusedElement = null;

  // Parameters
  let currentVoltageKV = 20.0;
  let currentEpsR = 3.8;
  let currentGapMM = 25.0;

  // Tour Steps with clean HTML math
  let tourCurrentStep = 0;
  const tourSteps = [
    {
      title: "1. What am I seeing?",
      body: `
        <p>You are viewing an <strong>asymmetric high-voltage electrode assembly</strong> inspired by Exodus patent US11511891B2 (FIGS. 4–8).</p>
        <p>The <strong style="color:var(--color-blade)">red knife-edge blade</strong> is charged to negative high voltage opposite the <strong style="color:var(--color-ground)">green ground plate</strong> at 0 V. A semitransparent <strong style="color:var(--color-dielectric)">dielectric potting block</strong> sits between them inside a grounded stainless steel chamber.</p>
        <p><em>Click and drag anywhere to rotate the 3D model, pinch/scroll to zoom, or use the arrow keys.</em></p>
      `,
      cameraPos: { x: 90, y: 55, z: 110 },
      target: { x: 0, y: 0, z: 0 },
      highlight: "blade_electrode"
    },
    {
      title: "2. Why does it happen?",
      body: `
        <p><strong>Electric Field Concentration:</strong> The sharp wedge of the blade cathode concentrates electric field lines (<i>E</i> &prop; 1/<i>r</i>).</p>
        <p><strong>Field Vector Direction:</strong> Conventional electric field vectors <b>E</b> = -&nabla;&Phi; point from higher potential (ground, 0 V) toward lower potential (cathode, -20 kV).</p>
        <p><strong>Maxwell Electrostatic Stress:</strong> Field lines exert electrostatic tension, pulling the blade forward toward the ground electrode. In general 3D electrostatics, the vacuum stress component is <i>T<sub>xx</sub></i> = &epsilon;<sub>0</sub>(<i>E<sub>x</sub></i><sup>2</sup> &minus; &frac12;|<b>E</b>|<sup>2</sup>) = &frac12;&epsilon;<sub>0</sub>(<i>E<sub>x</sub></i><sup>2</sup> &minus; <i>E<sub>y</sub></i><sup>2</sup> &minus; <i>E<sub>z</sub></i><sup>2</sup>). The scalar expression &frac12;&epsilon;<sub>0</sub><i>E<sub>x</sub></i><sup>2</sup> applies only in the idealized 1D limit where transverse fields vanish (<i>E<sub>y</sub></i> = <i>E<sub>z</sub></i> = 0); the nonuniform 3D scene depicts qualitative lines of action rather than an integrated stress solution.</p>
      `,
      cameraPos: { x: 30, y: 20, z: 50 },
      target: { x: 5, y: 0, z: 0 },
      highlight: "blade_electrode"
    },
    {
      title: "3. What changes it?",
      body: `
        <p><strong>Quadratic Voltage Scaling:</strong> Electrostatic forces scale strictly with <i>V</i><sup>2</sup>. Doubling voltage quadruples the force; at 0 V all forces vanish.</p>
        <p><strong>Action and Reaction:</strong> Look at the <strong style="color:var(--color-force)">golden force arrows</strong>. While the blade is pulled forward (+X), the ground plate is pulled backward (-X) with equal and opposite attraction.</p>
        <p>Dielectric polarization stress and external chamber wall coupling balance the remaining forces. Internal forces on the test article sum to <strong>zero</strong>.</p>
      `,
      cameraPos: { x: 0, y: 70, z: 90 },
      target: { x: 0, y: 0, z: 0 },
      highlight: "ground_electrode"
    },
    {
      title: "4. How could we test it?",
      body: `
        <p><strong>Testing for Real Propellantless Thrust:</strong> To prove whether net propulsion exists, we must measure the <em>entire isolated test article</em> on a micro-Newton torsion pendulum in high vacuum (&lt; 10<sup>-5</sup> Torr).</p>
        <p><strong>Crucial Null Controls:</strong></p>
        <ul>
          <li>Eliminate corona ion wind and air convection via deep vacuum.</li>
          <li>Invert voltage polarity: electrostatic force is symmetric (<i>V</i><sup>2</sup>), while discharge or leakage drifts asymmetrically.</li>
          <li>Sweep chamber wall distance to isolate image-charge coupling.</li>
        </ul>
        <p><strong>Conclusion:</strong> Local force asymmetry on one electrode does NOT produce whole-system thrust.</p>
      `,
      cameraPos: { x: 120, y: 80, z: 140 },
      target: { x: 0, y: 0, z: 0 },
      highlight: "enclosure_walls"
    }
  ];

  // --- Initialization ---
  async function init() {
    try {
      const response = await fetch('provenance_data.json');
      if (response.ok) {
        provenanceData = await response.json();
      }
    } catch (e) {
      console.warn("Using embedded fallback provenance data:", e);
    }

    initThree();
    buildScene();
    populateUI();
    updateUIState();
    setupEventListeners();
    animate();

    // Hide loading screen
    const loader = document.getElementById('loading-overlay');
    if (loader) {
      setTimeout(() => loader.classList.add('hidden'), 200);
    }
  }

  // --- Three.js Setup ---
  function initThree() {
    const container = document.getElementById('viewport-container');
    const canvas = document.getElementById('webgl-canvas');

    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0e14);

    const width = container.clientWidth || window.innerWidth;
    const height = container.clientHeight || 500;

    camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(90, 60, 110);

    renderer = new THREE.WebGLRenderer({
      canvas: canvas,
      antialias: true,
      powerPreference: "high-performance"
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.minDistance = 20;
    controls.maxDistance = 350;
    controls.maxPolarAngle = Math.PI * 0.85;

    raycaster = new THREE.Raycaster();
    mouse = new THREE.Vector2();

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
    scene.add(ambientLight);

    const mainLight = new THREE.DirectionalLight(0xffffff, 0.9);
    mainLight.position.set(80, 120, 90);
    mainLight.castShadow = true;
    mainLight.shadow.mapSize.width = 1024;
    mainLight.shadow.mapSize.height = 1024;
    scene.add(mainLight);

    const fillLight = new THREE.DirectionalLight(0x38bdf8, 0.4);
    fillLight.position.set(-80, -40, -60);
    scene.add(fillLight);

    // Subtle coordinate ground grid
    const gridHelper = new THREE.GridHelper(160, 32, 0x273545, 0x16202c);
    gridHelper.position.y = -25;
    scene.add(gridHelper);

    // Groups
    geometryGroup = new THREE.Group();
    geometryGroup.userData = { isGeometryGroup: true };
    fieldGroup = new THREE.Group();
    fieldGroup.userData = { isFieldGroup: true };
    forceGroup = new THREE.Group();
    forceGroup.userData = { isForceGroup: true };
    enclosureGroup = new THREE.Group();
    enclosureGroup.userData = { isEnclosureGroup: true };

    scene.add(geometryGroup);
    scene.add(fieldGroup);
    scene.add(forceGroup);
    scene.add(enclosureGroup);

    // Expose test hooks for automated browser smoke testing
    window.__explorer = {
      scene: scene,
      renderer: renderer,
      camera: camera,
      controls: controls,
      geometryGroup: geometryGroup,
      fieldGroup: fieldGroup,
      forceGroup: forceGroup,
      enclosureGroup: enclosureGroup,
      getPickableObjects: () => pickableObjects,
      getPickedObject: getPickedObject,
      getComponentScreenCoords: getComponentScreenCoords,
      selectComponent: selectComponent,
      setViewPreset: setViewPreset,
      updateForceVectors: updateForceVectors,
      updateFieldLines: updateFieldLines,
      componentMeshes: componentMeshes,
      getCurrentState: () => ({
        voltageKV: currentVoltageKV,
        gapMM: currentGapMM,
        epsR: currentEpsR
      })
    };
  }

  // --- Build 3D Scene Elements ---
  function buildScene() {
    pickableObjects = [];

    // 1. Blade Electrode (Asymmetric Tapered Wedge - US11511891B2 FIGS. 4–8)
    // Synchronized dimensions: 30 mm width (X taper), 25.4 mm height (Y), 3 mm spine (Z thickness)
    const bladeGeo = createBladeWedgeGeometry(30, 25.4, 3);
    const bladeMat = new THREE.MeshStandardMaterial({
      color: 0xf43f5e,
      roughness: 0.35,
      metalness: 0.85,
      emissive: 0x881337,
      emissiveIntensity: 0.25
    });
    const bladeMesh = new THREE.Mesh(bladeGeo, bladeMat);
    bladeMesh.position.set(-15, 0, 0);
    bladeMesh.castShadow = true;
    bladeMesh.receiveShadow = true;
    bladeMesh.userData = { id: "blade_electrode", name: "Asymmetric High-Voltage Blade" };
    geometryGroup.add(bladeMesh);
    componentMeshes["blade_electrode"] = bladeMesh;
    pickableObjects.push(bladeMesh);

    // 2. Ground Counter-Electrode (Planar Collector at +X)
    // Physical surface-to-surface gap d:
    // Blade sharp knife-edge is at world x = 0.
    // Ground plate has thickness 4.0 mm (spans [x_center - 2, x_center + 2]).
    // Placing the mesh center at x = currentGapMM + 2.0 ensures that its near face
    // is at exactly x = currentGapMM, making the physical surface gap identically equal to currentGapMM.
    const groundGeo = new THREE.BoxGeometry(4, 40, 50.8);
    const groundMat = new THREE.MeshStandardMaterial({
      color: 0x10b981,
      roughness: 0.25,
      metalness: 0.9,
      emissive: 0x064e3b,
      emissiveIntensity: 0.2
    });
    const groundMesh = new THREE.Mesh(groundGeo, groundMat);
    groundMesh.position.set(currentGapMM + 2.0, 0, 0);
    groundMesh.castShadow = true;
    groundMesh.receiveShadow = true;
    groundMesh.userData = { id: "ground_electrode", name: "Ground Counter-Electrode" };
    geometryGroup.add(groundMesh);
    componentMeshes["ground_electrode"] = groundMesh;
    pickableObjects.push(groundMesh);

    // 3. Dielectric Block (Epoxy Potting Barrier)
    // Placed between x = -5 and x = +11 mm (width 16 mm, centered at x = 3 mm)
    // Ground plate near face is at x = currentGapMM (min gap >= 16 mm),
    // guaranteeing >= 5.0 mm positive physical clearance from dielectric potting.
    const dielGeo = new THREE.BoxGeometry(16, 30, 45);
    const dielMat = new THREE.MeshPhysicalMaterial({
      color: 0x818cf8,
      roughness: 0.15,
      metalness: 0.05,
      transmission: 0.75,
      transparent: true,
      opacity: 0.55,
      ior: 1.55
    });
    const dielMesh = new THREE.Mesh(dielGeo, dielMat);
    dielMesh.position.set(3, 0, 0);
    dielMesh.receiveShadow = true;
    dielMesh.userData = { id: "dielectric_block", name: "Solid Dielectric Barrier / Potting" };
    geometryGroup.add(dielMesh);
    componentMeshes["dielectric_block"] = dielMesh;
    pickableObjects.push(dielMesh);

    // 4. Structural Support Stand (Delrin/PEEK Insulating Base)
    const mountGeo = new THREE.BoxGeometry(90, 8, 90);
    const mountMat = new THREE.MeshStandardMaterial({
      color: 0x475569,
      roughness: 0.7,
      metalness: 0.1,
      emissive: 0x1e293b,
      emissiveIntensity: 0.1
    });
    const mountMesh = new THREE.Mesh(mountGeo, mountMat);
    mountMesh.position.set(5, -20, 0);
    mountMesh.receiveShadow = true;
    mountMesh.userData = { id: "support_mount", name: "Structural Support Mount" };
    geometryGroup.add(mountMesh);
    componentMeshes["support_mount"] = mountMesh;
    pickableObjects.push(mountMesh);

    // 5. Conductive Enclosure / Chamber Walls (160 x 120 x 160 mm matching JSON)
    const chamberGeo = new THREE.BoxGeometry(160, 120, 160);
    const chamberWire = new THREE.WireframeGeometry(chamberGeo);
    const chamberLine = new THREE.LineSegments(chamberWire);
    chamberLine.material.color.setHex(0x334155);
    chamberLine.material.transparent = true;
    chamberLine.material.opacity = 0.45;

    // Pickable chamber mesh with transparent double-sided faces
    const chamberMat = new THREE.MeshBasicMaterial({
      color: 0x1e293b,
      transparent: true,
      opacity: 0.06,
      side: THREE.DoubleSide
    });
    const chamberMesh = new THREE.Mesh(chamberGeo, chamberMat);
    chamberMesh.userData = { id: "enclosure_walls", name: "Conductive Enclosure (Chamber)" };
    chamberMesh.add(chamberLine);
    enclosureGroup.add(chamberMesh);
    componentMeshes["enclosure_walls"] = chamberMesh;
    pickableObjects.push(chamberMesh);

    // Build Electric Field Streamlines & Force Vectors
    updateFieldLines();
    updateForceVectors();
  }

  // --- Helper: Tapered Blade Wedge Geometry ---
  function createBladeWedgeGeometry(lengthX, heightY, spineZ) {
    const geom = new THREE.BufferGeometry();
    const halfH = heightY / 2;
    const halfZ = spineZ / 2;

    const vertices = new Float32Array([
      // Front sharp knife-edge (X = +lengthX/2)
      lengthX / 2, halfH, 0,
      lengthX / 2, -halfH, 0,
      // Back thick spine (X = -lengthX/2)
      -lengthX / 2, halfH, halfZ,
      -lengthX / 2, -halfH, halfZ,
      -lengthX / 2, halfH, -halfZ,
      -lengthX / 2, -halfH, -halfZ,
    ]);

    const indices = [
      0, 2, 4,
      1, 5, 3,
      0, 1, 3,
      0, 3, 2,
      0, 4, 5,
      0, 5, 1,
      2, 3, 5,
      2, 5, 4
    ];

    geom.setAttribute('position', new THREE.BufferAttribute(vertices, 3));
    geom.setIndex(indices);
    geom.computeVertexNormals();
    return geom;
  }

  // --- Helper: Clean GPU Resource Disposal ---
  // Remediated for V0-R2-M5: Walks full object hierarchy and disposes every geometry & material
  function disposeHierarchy(root) {
    if (!root) return;
    root.traverse((child) => {
      if (child.geometry && typeof child.geometry.dispose === 'function') {
        child.geometry.dispose();
      }
      if (child.material) {
        if (Array.isArray(child.material)) {
          child.material.forEach((m) => m && typeof m.dispose === 'function' && m.dispose());
        } else if (typeof child.material.dispose === 'function') {
          child.material.dispose();
        }
      }
    });
  }

  // --- Build / Update Electric Field Streamlines ---
  // Remediated for V0-R1-F2:
  // - Convention: E = -grad Phi points from Ground (0 V, high potential) to Blade (-V, low potential)
  // - When V = 0: fieldGroup is completely hidden and lines have 0 opacity
  function updateFieldLines() {
    while (fieldGroup.children.length > 0) {
      const obj = fieldGroup.children[0];
      fieldGroup.remove(obj);
      disposeHierarchy(obj);
    }

    if (currentVoltageKV <= 0.0) {
      fieldGroup.visible = false;
      return;
    }

    fieldGroup.visible = document.getElementById('toggle-fields').checked;

    const voltageRatio = currentVoltageKV / 20.0;
    const opacity = Math.min(0.9, 0.35 + voltageRatio * 0.45);
    const bladeTipX = 0; // Blade sharp knife-edge position
    const groundX = currentGapMM;

    // Streamlines flowing from ground plate (0 V) to sharp blade cathode (-V)
    const numLines = 28;
    for (let i = 0; i < numLines; i++) {
      const angle = (i / numLines) * Math.PI * 2;
      const spreadY = Math.sin(angle) * (6 + (i % 3) * 5);
      const spreadZ = Math.cos(angle) * (8 + (i % 4) * 6);

      // p0 at ground plate (0 V, high potential) -> p2 at sharp blade tip (-V, low potential)
      const p0 = new THREE.Vector3(groundX, spreadY * 0.85, spreadZ * 0.85);
      const p1 = new THREE.Vector3((bladeTipX + groundX) * 0.45, spreadY * 1.3, spreadZ * 1.3);
      const p2 = new THREE.Vector3(bladeTipX, 0, 0);

      const curve = new THREE.QuadraticBezierCurve3(p0, p1, p2);
      const points = curve.getPoints(24);
      const geom = new THREE.BufferGeometry().setFromPoints(points);

      // Color gradient: Cyan at ground (0 V) -> Magenta/Rose at blade (-V)
      const colors = [];
      const cStart = new THREE.Color(0x38bdf8); // 0 V
      const cEnd = new THREE.Color(0xf43f5e);   // -V
      for (let j = 0; j <= 24; j++) {
        const t = j / 24;
        const c = cStart.clone().lerp(cEnd, t);
        colors.push(c.r, c.g, c.b);
      }
      geom.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));

      const mat = new THREE.LineBasicMaterial({
        vertexColors: true,
        transparent: true,
        opacity: opacity,
        linewidth: 1.5
      });

      const line = new THREE.Line(geom, mat);
      line.userData = { isFieldLine: true, baseOpacity: opacity };
      fieldGroup.add(line);
    }

    // Equipotential contour rings near the blade tip
    const ringRadii = [4, 8, 14, 22];
    ringRadii.forEach((r, idx) => {
      const ringGeo = new THREE.RingGeometry(r - 0.25, r + 0.25, 32);
      const ringMat = new THREE.MeshBasicMaterial({
        color: 0x38bdf8,
        transparent: true,
        opacity: Math.max(0.08, (0.4 - idx * 0.08) * voltageRatio),
        side: THREE.DoubleSide
      });
      const ringMesh = new THREE.Mesh(ringGeo, ringMat);
      ringMesh.rotation.y = Math.PI / 2;
      ringMesh.position.set(bladeTipX + (idx + 1) * 2, 0, 0);
      fieldGroup.add(ringMesh);
    });
  }

  // --- Build / Update Action & Reaction Force Vectors ---
  // Remediated for V0-R1-F1, V0-R1-F4, V0-R2-M4, V0-R2-M5, V0-R3-M4:
  // - Bounded legibility encoding strictly preserving monotonic V^2 scaling:
  //   * Extinguishes completely at V = 0 kV (visible = false).
  //   * Scales from 6.0 mm (cleanly legible minimum) to 16.0 mm at 20 kV (nominal).
  //   * Scales from 16.0 mm to 30.0 mm at 50 kV (stays strictly within 80 mm chamber).
  // - Fully disposes nested geometries and materials before rebuild.
  function updateForceVectors() {
    while (forceGroup.children.length > 0) {
      const obj = forceGroup.children[0];
      forceGroup.remove(obj);
      disposeHierarchy(obj);
    }

    if (currentVoltageKV <= 0.0) {
      forceGroup.visible = false;
      return;
    }

    forceGroup.visible = document.getElementById('toggle-forces').checked;

    // V0-R3-M4: Bounded legibility encoding for schematic vectors
    const ARROW_MIN_LEN = 6.0;   // Clean legibility minimum for nonzero V
    const ARROW_NOM_LEN = 16.0;  // Nominal length at 20 kV
    const ARROW_MAX_LEN = 30.0;  // Upper bound to stay safely inside chamber (x_max < 75 mm)

    let arrowLen;
    if (currentVoltageKV <= 20.0) {
      const ratio = currentVoltageKV / 20.0;
      arrowLen = ARROW_MIN_LEN + (ARROW_NOM_LEN - ARROW_MIN_LEN) * (ratio * ratio);
    } else {
      const ratioUpper = (currentVoltageKV * currentVoltageKV - 400.0) / (2500.0 - 400.0);
      arrowLen = ARROW_NOM_LEN + (ARROW_MAX_LEN - ARROW_NOM_LEN) * Math.min(1.0, Math.max(0.0, ratioUpper));
    }

    // 1. Blade Attractive Traction (+X toward ground)
    const arrowBlade = createCustomArrow(
      new THREE.Vector3(1, 0, 0),
      new THREE.Vector3(0, 0, 0),
      arrowLen,
      0xfacc15,
      "DUT: Blade Electrostatic Traction (+X)"
    );
    arrowBlade.userData.element = "Blade Electrode";
    forceGroup.add(arrowBlade);

    // 2. Ground Reaction Traction (-X toward blade)
    const arrowGround = createCustomArrow(
      new THREE.Vector3(-1, 0, 0),
      new THREE.Vector3(currentGapMM, 0, 0),
      arrowLen,
      0xfacc15,
      "DUT: Ground Reaction Traction (-X)"
    );
    arrowGround.userData.element = "Ground Electrode";
    forceGroup.add(arrowGround);

    // 3. Dielectric Polarization Stress (-X toward blade)
    const arrowDiel = createCustomArrow(
      new THREE.Vector3(-1, 0, 0),
      new THREE.Vector3(11, 16, 0),
      arrowLen,
      0x818cf8,
      "DUT: Dielectric Polarization Stress (-X)"
    );
    arrowDiel.userData.element = "Dielectric Potting";
    forceGroup.add(arrowDiel);

    // 4. Mount Constraint Force (+X structural equilibrium)
    const arrowMount = createCustomArrow(
      new THREE.Vector3(1, 0, 0),
      new THREE.Vector3(5, -20, 0),
      arrowLen,
      0x64748b,
      "DUT: Mount Structural Equilibrium (+X)"
    );
    arrowMount.userData.element = "Structural Mount";
    forceGroup.add(arrowMount);

    // 5. External Chamber Wall Reaction (-X image-charge coupling)
    const arrowWall = createCustomArrow(
      new THREE.Vector3(-1, 0, 0),
      new THREE.Vector3(75, 0, 0),
      arrowLen,
      0xf59e0b,
      "External: Chamber Wall Reaction (-X)"
    );
    arrowWall.userData.element = "Chamber Enclosure Walls";
    forceGroup.add(arrowWall);
  }

  // --- Helper: Clean 3D Arrow Helper ---
  function createCustomArrow(dir, origin, length, hexColor, labelText) {
    const group = new THREE.Group();
    group.position.copy(origin);

    const normDir = dir.clone().normalize();
    const arrowLength = Math.max(length, 2);
    const headLength = Math.min(arrowLength * 0.35, 6);
    const shaftLength = arrowLength - headLength;
    const shaftRadius = 0.75;
    const headRadius = 1.75;

    // Shaft
    const shaftGeo = new THREE.CylinderGeometry(shaftRadius, shaftRadius, shaftLength, 12);
    shaftGeo.translate(0, shaftLength / 2, 0);
    const mat = new THREE.MeshStandardMaterial({
      color: hexColor,
      roughness: 0.3,
      metalness: 0.6,
      emissive: hexColor,
      emissiveIntensity: 0.3
    });
    const shaft = new THREE.Mesh(shaftGeo, mat);

    // Cone Head
    const headGeo = new THREE.ConeGeometry(headRadius, headLength, 16);
    headGeo.translate(0, shaftLength + headLength / 2, 0);
    const head = new THREE.Mesh(headGeo, mat);

    group.add(shaft);
    group.add(head);

    const up = new THREE.Vector3(0, 1, 0);
    const quaternion = new THREE.Quaternion().setFromUnitVectors(up, normDir);
    group.quaternion.copy(quaternion);

    group.userData = {
      isArrow: true,
      label: labelText,
      arrowLength: arrowLength,
      dirX: normDir.x,
      dirY: normDir.y,
      dirZ: normDir.z
    };
    return group;
  }

  // --- Populate UI from Provenance Data ---
  function populateUI() {
    // 1. Component List in Layers Tab
    const compListContainer = document.getElementById('component-list');
    if (compListContainer && provenanceData.components) {
      compListContainer.innerHTML = '';
      provenanceData.components.forEach(comp => {
        const btn = document.createElement('button');
        btn.className = 'component-item-btn';
        btn.dataset.id = comp.id;
        btn.innerHTML = `
          <span>${comp.name}</span>
          <span class="provenance-pill ${getPillClass(comp.provenance_badge)}">${comp.provenance_badge}</span>
        `;
        btn.addEventListener('click', () => selectComponent(comp.id));
        compListContainer.appendChild(btn);
      });
    }

    // 2. Whole-Body Force Ledger Tables (DUT vs External Environment)
    const dutTbody = document.getElementById('ledger-dut-tbody');
    const extTbody = document.getElementById('ledger-ext-tbody');

    if (dutTbody && extTbody && provenanceData.components) {
      dutTbody.innerHTML = '';
      extTbody.innerHTML = '';

      provenanceData.components.forEach(comp => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><strong>${comp.name}</strong></td>
          <td style="font-family:var(--font-mono);color:#38bdf8">${comp.schematic_direction}</td>
          <td style="color:var(--text-secondary)">${comp.force_nature}</td>
        `;

        if (comp.system_boundary === "DEVICE_UNDER_TEST") {
          dutTbody.appendChild(tr);
        } else {
          extTbody.appendChild(tr);
        }
      });
    }

    // 3. Null Controls List
    const nullControlsList = document.getElementById('null-controls-list');
    if (nullControlsList && provenanceData.null_controls) {
      nullControlsList.innerHTML = '';
      provenanceData.null_controls.forEach(ctrl => {
        const li = document.createElement('li');
        li.innerHTML = `<strong>${ctrl.name}:</strong> ${ctrl.purpose} <em>(${ctrl.reference})</em>`;
        nullControlsList.appendChild(li);
      });
    }
  }

  function getPillClass(badge) {
    switch (badge) {
      case 'ESTABLISHED MODEL': return 'pill-established';
      case 'PUBLISHED HYPOTHESIS': return 'pill-hypothesis';
      case 'WHAT-IF PARAMETER': return 'pill-whatif';
      case 'UNVERIFIED NUMERICAL OUTPUT': return 'pill-unverified';
      default: return 'pill-provisional';
    }
  }

  // --- Dynamic Centralized UI State Update ---
  // Remediated for V0-R1-M1: synchronizes all labels, legends, and inspector fields
  function updateUIState() {
    // 1. Legend labels
    const lBlade = document.getElementById('legend-blade-label');
    const lGround = document.getElementById('legend-ground-label');
    const lDiel = document.getElementById('legend-dielectric-label');
    const lField = document.getElementById('legend-field-label');
    const lForce = document.getElementById('legend-force-label');

    if (lBlade) {
      lBlade.textContent = currentVoltageKV > 0
        ? `Blade (-${currentVoltageKV.toFixed(1)} kV)`
        : `Blade (0.0 kV — OFF)`;
    }
    if (lGround) lGround.textContent = `Ground (0.0 V)`;
    if (lDiel) lDiel.textContent = `Dielectric (ε_r = ${currentEpsR.toFixed(1)} — Visual Proxy Only)`;
    if (lField) {
      lField.textContent = currentVoltageKV > 0
        ? `Electric Field E (Ground 0 V → Blade -${currentVoltageKV.toFixed(0)} kV)`
        : `Electric Field E (OFF at 0 V)`;
    }
    if (lForce) {
      lForce.textContent = currentVoltageKV > 0
        ? `Schematic Vectors: Direction only (bounded 6–30 mm, F ∝ V²)`
        : `Schematic Vectors (0 at 0 V)`;
    }

    // 2. Update Inspector if currently selected
    if (selectedComponentId) {
      renderInspectorCard(selectedComponentId);
    }
  }

  // --- Select & Inspect Component ---
  function selectComponent(id) {
    selectedComponentId = id;

    // Highlight in component list
    const items = document.querySelectorAll('.component-item-btn');
    items.forEach(el => {
      el.classList.toggle('selected', el.dataset.id === id);
    });

    renderInspectorCard(id);
    switchTab('tab-inspector');
    highlightMesh(id);

    const comp = provenanceData.components.find(c => c.id === id);
    if (comp) {
      showBanner(`Inspecting: ${comp.name} (${comp.provenance_badge})`);
    }
  }

  function renderInspectorCard(id) {
    const comp = provenanceData.components.find(c => c.id === id);
    if (!comp) return;

    document.getElementById('inspector-name').textContent = comp.name;
    const badge = document.getElementById('inspector-badge');
    badge.textContent = comp.provenance_badge;
    badge.className = `provenance-pill ${getPillClass(comp.provenance_badge)}`;

    document.getElementById('inspector-role').textContent = comp.role;
    document.getElementById('inspector-citation').textContent = comp.citation || '—';
    document.getElementById('inspector-boundary').textContent = comp.system_boundary === "DEVICE_UNDER_TEST"
      ? "Boundary A: Suspended Test Article (DUT)"
      : "Boundary B: External Test Environment";

    document.getElementById('inspector-material').textContent = comp.material || '—';

    // Dynamic potential based on slider
    let potText = 'Non-conductive / N/A';
    if (comp.id === 'blade_electrode') {
      potText = currentVoltageKV > 0 ? `-${currentVoltageKV.toFixed(1)} kV (Cathode)` : '0.0 kV (OFF)';
    } else if (comp.id === 'ground_electrode' || comp.id === 'enclosure_walls') {
      potText = '0.0 V (Reference Ground)';
    }
    document.getElementById('inspector-potential').textContent = potText;

    const dims = comp.dimensions_mm;
    let dimStr = dims ? `${dims.width} × ${dims.height} × ${(dims.thickness || dims.depth || 0)} mm` : '—';
    if (comp.id === 'blade_electrode') {
      dimStr += ` (Tip radius: 0.1 mm source metadata; idealized knife-edge vertex in V0 mesh)`;
    } else if (comp.id === 'ground_electrode') {
      dimStr += ` (Surface Gap d = ${currentGapMM.toFixed(1)} mm)`;
    } else if (comp.id === 'dielectric_block') {
      dimStr += ` (Permittivity ε_r = ${currentEpsR.toFixed(1)}: visual material proxy in V0)`;
    }
    document.getElementById('inspector-dimensions').textContent = dimStr;

    // Schematic force vector description (Remediated for V0-R4-M3)
    // Explicitly distinguishes physical scaling trend (F ∝ V²) from the bounded perceptual visual arrow encoding (6–30 mm).
    let arrowLenMM = 0;
    if (currentVoltageKV > 0) {
      if (currentVoltageKV <= 20.0) {
        arrowLenMM = 6.0 + 10.0 * Math.pow(currentVoltageKV / 20.0, 2);
      } else {
        const ratioUpper = (currentVoltageKV * currentVoltageKV - 400.0) / (2500.0 - 400.0);
        arrowLenMM = 16.0 + 14.0 * Math.min(1.0, Math.max(0.0, ratioUpper));
      }
    }
    const forceStr = currentVoltageKV > 0
      ? `${comp.schematic_direction} [Physical Trend: (V/20)² = ${(Math.pow(currentVoltageKV/20, 2)).toFixed(2)}x | Visual Arrow: ${arrowLenMM.toFixed(1)} mm bounded legibility]`
      : '0.0 (Field OFF at 0 V)';
    document.getElementById('inspector-force').textContent = forceStr;

    document.getElementById('inspector-status').textContent = comp.status || '—';
    document.getElementById('inspector-explanation').innerHTML = `
      <strong>Physical Context:</strong> ${comp.force_nature}.<br>
      <em>Note: V0 displays schematic directions only. Quantitative force magnitudes require qualified mesh-converged simulation.</em>
    `;
  }

  function highlightMesh(id) {
    Object.keys(componentMeshes).forEach(key => {
      const mesh = componentMeshes[key];
      const isTarget = key === id;
      if (mesh.material && mesh.material.emissive) {
        mesh.material.emissiveIntensity = isTarget ? 0.8 : 0.2;
      }
    });
  }

  function showBanner(text) {
    const banner = document.getElementById('scene-banner');
    const bannerText = document.getElementById('banner-text');
    if (banner && bannerText) {
      bannerText.textContent = text;
      banner.style.opacity = '1';
    }
  }

  // --- Tab Switching ---
  function switchTab(tabId) {
    const tabs = document.querySelectorAll('.tab-btn');
    const panels = document.querySelectorAll('.tab-panel');

    tabs.forEach(tab => {
      const isActive = tab.dataset.tab === tabId;
      tab.classList.toggle('active', isActive);
      tab.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });

    panels.forEach(panel => {
      panel.classList.toggle('active', panel.id === tabId);
    });
  }

  // --- Camera View Presets ---
  function setViewPreset(preset, instant = false) {
    const dist = 140;
    const target = new THREE.Vector3(0, 0, 0);
    let newPos;
    let newUp = new THREE.Vector3(0, 1, 0);

    switch (preset) {
      case 'isometric':
        newPos = new THREE.Vector3(90, 60, 110);
        break;
      case 'side': // X-Y
        newPos = new THREE.Vector3(0, 0, dist);
        break;
      case 'front': // Y-Z
        newPos = new THREE.Vector3(dist, 0, 0);
        break;
      case 'top': // X-Z
        newPos = new THREE.Vector3(0, dist, 0.001);
        newUp = new THREE.Vector3(0, 0, -1);
        break;
      default:
        newPos = new THREE.Vector3(90, 60, 110);
    }

    if (instant) {
      camera.position.copy(newPos);
      camera.up.copy(newUp);
      controls.target.copy(target);
      camera.lookAt(target);
      controls.update();
    } else {
      camera.up.copy(newUp);
      animateCameraTo(newPos, target);
    }
  }

  function animateCameraTo(targetPos, targetLookAt, durationMs = 500) {
    const startPos = camera.position.clone();
    const startTarget = controls.target.clone();
    const startTime = performance.now();

    function update() {
      const elapsed = performance.now() - startTime;
      const t = Math.min(elapsed / durationMs, 1.0);
      const ease = t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;

      camera.position.lerpVectors(startPos, targetPos, ease);
      controls.target.lerpVectors(startTarget, targetLookAt, ease);
      controls.update();

      if (t < 1.0) {
        requestAnimationFrame(update);
      }
    }
    requestAnimationFrame(update);
  }

  // --- Supported Keyboard Camera Navigation ---
  // Remediated for V0-R1-F3: mathematically computes spherical camera offsets around controls.target
  function orbitCamera(deltaTheta, deltaPhi) {
    const offset = camera.position.clone().sub(controls.target);

    // Azimuthal rotation around world Y
    if (deltaTheta !== 0) {
      offset.applyAxisAngle(new THREE.Vector3(0, 1, 0), deltaTheta);
    }

    // Polar rotation around camera right vector
    if (deltaPhi !== 0) {
      const right = new THREE.Vector3().crossVectors(offset, camera.up).normalize();
      offset.applyAxisAngle(right, deltaPhi);
    }

    camera.position.copy(controls.target).add(offset);
    camera.lookAt(controls.target);
    controls.update();
  }

  function dollyCamera(factor) {
    const offset = camera.position.clone().sub(controls.target);
    const currentDist = offset.length();
    const newDist = Math.max(controls.minDistance, Math.min(controls.maxDistance, currentDist * factor));
    offset.setLength(newDist);
    camera.position.copy(controls.target).add(offset);
    controls.update();
  }

  // --- Modal Focus Trap Management ---
  function trapFocus(modalElement) {
    lastFocusedElement = document.activeElement;
    const focusable = modalElement.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
    if (focusable.length > 0) {
      focusable[0].focus();
    }

    modalElement.addEventListener('keydown', function handleTab(e) {
      if (e.key !== 'Tab') return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (e.shiftKey) {
        if (document.activeElement === first) {
          last.focus();
          e.preventDefault();
        }
      } else {
        if (document.activeElement === last) {
          first.focus();
          e.preventDefault();
        }
      }
    });
  }

  function releaseFocus() {
    if (lastFocusedElement && typeof lastFocusedElement.focus === 'function') {
      lastFocusedElement.focus();
    }
  }

  // --- Tour Functions ---
  function openTour(stepIndex = 0) {
    tourCurrentStep = stepIndex;
    const modal = document.getElementById('tour-modal');
    if (modal) {
      modal.classList.remove('hidden');
      trapFocus(modal);
    }
    renderTourStep();
  }

  function closeTour() {
    const modal = document.getElementById('tour-modal');
    if (modal) {
      modal.classList.add('hidden');
      releaseFocus();
    }
  }

  function renderTourStep() {
    const step = tourSteps[tourCurrentStep];
    if (!step) return;

    document.getElementById('tour-step-count').textContent = `Step ${tourCurrentStep + 1} of ${tourSteps.length}`;
    document.getElementById('tour-step-title').textContent = step.title;
    document.getElementById('tour-step-body').innerHTML = step.body;

    const dots = document.querySelectorAll('.tour-dots .dot');
    dots.forEach((dot, idx) => dot.classList.toggle('active', idx === tourCurrentStep));

    const prevBtn = document.getElementById('tour-btn-prev');
    const nextBtn = document.getElementById('tour-btn-next');
    prevBtn.disabled = tourCurrentStep === 0;
    nextBtn.textContent = tourCurrentStep === tourSteps.length - 1 ? 'Finish Tour' : 'Next';

    if (step.cameraPos && step.target) {
      animateCameraTo(
        new THREE.Vector3(step.cameraPos.x, step.cameraPos.y, step.cameraPos.z),
        new THREE.Vector3(step.target.x, step.target.y, step.target.z),
        600
      );
    }

    if (step.highlight) {
      selectComponent(step.highlight);
    }
  }

  function nextTourStep() {
    if (tourCurrentStep < tourSteps.length - 1) {
      tourCurrentStep++;
      renderTourStep();
    } else {
      closeTour();
      showBanner("Tour complete! Explore the layers and What-If sandbox controls.");
    }
  }

  function prevTourStep() {
    if (tourCurrentStep > 0) {
      tourCurrentStep--;
      renderTourStep();
    }
  }

  // --- Event Listeners Setup ---
  function setupEventListeners() {
    window.addEventListener('resize', onWindowResize);

    const container = document.getElementById('viewport-container');
    container.addEventListener('pointerdown', onPointerDown);
    container.addEventListener('pointermove', onPointerMove);

    // Preset HUD Buttons
    document.querySelectorAll('.view-preset-hud .hud-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        document.querySelectorAll('.view-preset-hud .hud-btn').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        setViewPreset(e.target.dataset.view);
      });
    });

    // Reset View Button
    document.getElementById('btn-reset-view').addEventListener('click', () => {
      setViewPreset('isometric');
      showBanner("Camera reset to default isometric view.");
    });

    // Tour Buttons
    document.getElementById('btn-start-tour').addEventListener('click', () => openTour(0));
    document.getElementById('tour-btn-close').addEventListener('click', closeTour);
    document.getElementById('tour-btn-next').addEventListener('click', nextTourStep);
    document.getElementById('tour-btn-prev').addEventListener('click', prevTourStep);

    // Help Modal
    const helpModal = document.getElementById('help-modal');
    document.getElementById('btn-toggle-help').addEventListener('click', () => {
      helpModal.classList.remove('hidden');
      trapFocus(helpModal);
    });
    document.getElementById('help-btn-close').addEventListener('click', () => {
      helpModal.classList.add('hidden');
      releaseFocus();
    });

    // Sidebar Tab Switching
    document.querySelectorAll('.sidebar-tabs .tab-btn').forEach(btn => {
      btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    // Layer Toggles
    document.getElementById('toggle-geometry').addEventListener('change', (e) => {
      geometryGroup.visible = e.target.checked;
    });
    document.getElementById('toggle-fields').addEventListener('change', (e) => {
      if (currentVoltageKV > 0) {
        fieldGroup.visible = e.target.checked;
      }
    });
    document.getElementById('toggle-forces').addEventListener('change', (e) => {
      if (currentVoltageKV > 0) {
        forceGroup.visible = e.target.checked;
      }
    });
    document.getElementById('toggle-enclosure').addEventListener('change', (e) => {
      enclosureGroup.visible = e.target.checked;
    });
    document.getElementById('toggle-wireframe').addEventListener('change', (e) => {
      const isWire = e.target.checked;
      Object.values(componentMeshes).forEach(mesh => {
        if (mesh.material) mesh.material.wireframe = isWire;
      });
    });

    // What-If Sliders
    const sliderVoltage = document.getElementById('slider-voltage');
    const valVoltage = document.getElementById('val-voltage');
    sliderVoltage.addEventListener('input', (e) => {
      currentVoltageKV = parseFloat(e.target.value);
      valVoltage.textContent = currentVoltageKV > 0 ? `-${currentVoltageKV.toFixed(1)} kV` : "0.0 kV (OFF)";
      updateFieldLines();
      updateForceVectors();
      updateUIState();
    });

    const sliderEps = document.getElementById('slider-eps');
    const valEps = document.getElementById('val-eps');
    sliderEps.addEventListener('input', (e) => {
      currentEpsR = parseFloat(e.target.value);
      valEps.textContent = `${currentEpsR.toFixed(1)} (${currentEpsR < 1.5 ? 'Air/Vacuum' : 'Epoxy/FR4'})`;
      if (componentMeshes["dielectric_block"]) {
        componentMeshes["dielectric_block"].material.opacity = 0.25 + (currentEpsR / 5.0) * 0.45;
      }
      updateForceVectors();
      updateUIState();
    });

    const sliderGap = document.getElementById('slider-gap');
    const valGap = document.getElementById('val-gap');
    sliderGap.addEventListener('input', (e) => {
      currentGapMM = Math.max(16.0, parseFloat(e.target.value));
      valGap.textContent = `${currentGapMM.toFixed(1)} mm`;
      if (componentMeshes["ground_electrode"]) {
        componentMeshes["ground_electrode"].position.x = currentGapMM + 2.0;
      }
      updateFieldLines();
      updateForceVectors();
      updateUIState();
    });

    document.getElementById('btn-reset-sandbox').addEventListener('click', () => {
      sliderVoltage.value = 20;
      sliderVoltage.dispatchEvent(new Event('input'));
      sliderEps.value = 3.8;
      sliderEps.dispatchEvent(new Event('input'));
      sliderGap.value = 25;
      sliderGap.dispatchEvent(new Event('input'));
      showBanner("Sandbox parameters reset to default baseline.");
    });

    // Keyboard Shortcuts
    window.addEventListener('keydown', (e) => {
      if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;

      switch (e.key) {
        case 'ArrowLeft':
          orbitCamera(0.08, 0);
          e.preventDefault();
          break;
        case 'ArrowRight':
          orbitCamera(-0.08, 0);
          e.preventDefault();
          break;
        case 'ArrowUp':
          orbitCamera(0, -0.06);
          e.preventDefault();
          break;
        case 'ArrowDown':
          orbitCamera(0, 0.06);
          e.preventDefault();
          break;
        case '+':
        case '=':
          dollyCamera(0.88);
          e.preventDefault();
          break;
        case '-':
        case '_':
          dollyCamera(1.12);
          e.preventDefault();
          break;
        case 'r':
        case 'R':
          setViewPreset('isometric');
          break;
        case '1':
          const tGeom = document.getElementById('toggle-geometry');
          tGeom.checked = !tGeom.checked;
          tGeom.dispatchEvent(new Event('change'));
          break;
        case '2':
          const tField = document.getElementById('toggle-fields');
          tField.checked = !tField.checked;
          tField.dispatchEvent(new Event('change'));
          break;
        case '3':
          const tForce = document.getElementById('toggle-forces');
          tForce.checked = !tForce.checked;
          tForce.dispatchEvent(new Event('change'));
          break;
        case 'Escape':
          closeTour();
          helpModal.classList.add('hidden');
          releaseFocus();
          break;
      }
    });
  }

  // --- Helper: Screen Coordinate Projection for 3D Components ---
  // Remediated for V0-R3-F1: Projects unoccluded 3D surface points to client viewport coordinates
  // allowing automated Playwright tests to exercise real canvas pointer hover & click paths.
  function getComponentScreenCoords(id) {
    if (!renderer || !camera) return null;
    const rect = renderer.domElement.getBoundingClientRect();

    let targetWorldPoint;
    switch (id) {
      case 'blade_electrode':
        targetWorldPoint = new THREE.Vector3(-22, 10, 0);
        break;
      case 'dielectric_block':
        targetWorldPoint = new THREE.Vector3(3, 4, 12);
        break;
      case 'ground_electrode':
        // Near face is at x = currentGapMM, center is at x = currentGapMM + 2.0
        targetWorldPoint = new THREE.Vector3(currentGapMM + 2.0, 2, 12);
        break;
      case 'support_mount':
        targetWorldPoint = new THREE.Vector3(-25, -20, 25);
        break;
      case 'enclosure_walls':
        if (Math.abs(camera.position.y) > 100) {
          // Top view: pick point in front of all interior components (Z = 55 > 45)
          targetWorldPoint = new THREE.Vector3(0, 0, 55);
        } else if (Math.abs(camera.position.z) > 100) {
          // Side view (X-Y plane): pick point above all interior components (Y = 38 > 20)
          targetWorldPoint = new THREE.Vector3(0, 38, 0);
        } else {
          // Default isometric view: pick upper chamber point above interior assembly
          targetWorldPoint = new THREE.Vector3(0, 42, 45);
        }
        break;
      default:
        if (componentMeshes[id]) {
          targetWorldPoint = componentMeshes[id].position.clone();
        } else {
          return null;
        }
    }

    const v = targetWorldPoint.clone().project(camera);
    if (v.z > 1.0) return null; // Behind camera

    return {
      clientX: ((v.x + 1) / 2) * rect.width + rect.left,
      clientY: ((-v.y + 1) / 2) * rect.height + rect.top,
      worldPoint: { x: targetWorldPoint.x, y: targetWorldPoint.y, z: targetWorldPoint.z }
    };
  }

  // --- Raycasting for 3D Component Picking & Hover ---
  // Remediated for V0-R2-F1: Prioritizes visible interior components over the outer chamber box.
  // The outer chamber is only selected if no interior component is intersected along the ray.
  function getPickedObject(event) {
    if (!renderer || !camera) return null;
    const rect = renderer.domElement.getBoundingClientRect();
    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObjects(pickableObjects, true);

    const isGeomVisible = geometryGroup && geometryGroup.visible;
    const isEnclVisible = enclosureGroup && enclosureGroup.visible;

    let closestInterior = null;
    let closestEnclosure = null;

    for (let i = 0; i < intersects.length; i++) {
      let targetObj = intersects[i].object;
      while (targetObj && (!targetObj.userData || !targetObj.userData.id)) {
        targetObj = targetObj.parent;
      }
      if (!targetObj || !targetObj.userData || !targetObj.userData.id) continue;

      const id = targetObj.userData.id;
      if (id === "enclosure_walls") {
        if (isEnclVisible && !closestEnclosure) {
          closestEnclosure = targetObj;
        }
      } else {
        if (isGeomVisible && !closestInterior) {
          closestInterior = targetObj;
        }
      }
      if (closestInterior) break;
    }

    return closestInterior || closestEnclosure || null;
  }

  function onPointerDown(event) {
    const picked = getPickedObject(event);
    if (picked && picked.userData && picked.userData.id) {
      selectComponent(picked.userData.id);
    }
  }

  function onPointerMove(event) {
    const container = document.getElementById('viewport-container');
    const picked = getPickedObject(event);

    if (picked && picked.userData && picked.userData.id) {
      container.style.cursor = 'pointer';
      if (hoveredObject !== picked) {
        hoveredObject = picked;
        showBanner(`Hover: ${picked.userData.name} — Click to inspect`);
      }
      return;
    }

    container.style.cursor = 'default';
    hoveredObject = null;
  }

  function onWindowResize() {
    const container = document.getElementById('viewport-container');
    if (!container || !renderer || !camera) return;

    const width = container.clientWidth || window.innerWidth;
    const height = container.clientHeight || 500;

    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
  }

  // --- Animation Loop ---
  function animate() {
    requestAnimationFrame(animate);

    controls.update();

    // Subtle flux oscillation only when energized (currentVoltageKV > 0)
    if (currentVoltageKV > 0 && fieldGroup && fieldGroup.visible) {
      const time = performance.now() * 0.0015;
      fieldGroup.children.forEach((child, idx) => {
        if (child.isLine && child.userData.baseOpacity) {
          child.material.opacity = Math.max(0.1, child.userData.baseOpacity + Math.sin(time * 2 + idx) * 0.1);
        }
      });
    }

    renderer.render(scene, camera);
  }

  // Run on DOM Ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
