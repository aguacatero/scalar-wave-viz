/**
 * Propulsion Explorer 3D (V0) — Interactive 3D Laboratory
 * Scalar Wave Viz — Visualizing Fields, Forces, and Whole-Body Conservation
 */

(function () {
  'use strict';

  // --- Embedded Fallback Provenance Data (used if fetch fails on file://) ---
  const DEFAULT_PROVENANCE_DATA = {
    metadata: {
      project: "Scalar Wave Viz",
      application: "Propulsion Explorer 3D (V0)",
      version: "0.1.0",
      citation: "Exodus Propulsion Technologies US11511891B2 FIGS. 4-8",
      scientific_disposition: "EDUCATIONAL_3D_EXPLORER_NO_UNVERIFIED_THRUST",
      evidence_grade: "PROVISIONAL_ILLUSTRATIVE_SCENE"
    },
    four_questions: {
      what_am_i_seeing: "A 3D representation of an asymmetric electrostatic electrode pair inspired by Exodus Propulsion Technologies patent US11511891B2 (FIGS. 4–8). It features an asymmetric high-voltage blade cathode with a sharp leading edge, a planar ground counter-electrode, solid dielectric barrier potting, and an enclosing conductive boundary (vacuum chamber walls).",
      why_does_it_happen: "Sharp conductor geometries concentrate electric field lines (E ~ 1/r), creating high local Maxwell electrostatic tension (T_xx = 0.5 * eps_0 * E_x^2) that pulls forward on the blade edge. In a closed electrostatic system, Newton's third law and Maxwell stress surface closure require that equal and opposite forces act on the ground electrode, dielectric, and surrounding enclosure, resulting in zero net force.",
      what_changes_it: "Electrostatic forces scale quadratically with voltage (F ~ V^2). Sharper blade tips increase peak field gradients. Changing the dielectric material changes interface polarization. Bringing chamber walls closer alters boundary image charges and capacitive coupling.",
      how_could_we_test_it: "A true propellantless thruster must accelerate the center of mass of the entire closed system without expelling mass or radiating net momentum. Discriminating tests require operating in high vacuum (< 10^-5 Torr) on a calibrated micro-Newton torsion balance to eliminate corona ion wind, with polarity reversal and chamber clearance sweeps (Tajmar & Schreiber 2020)."
    },
    components: [
      {
        id: "blade_electrode",
        name: "Asymmetric High-Voltage Blade",
        role: "Active high-voltage cathode with tapered asymmetric cross-section",
        citation: "US11511891B2, FIGS. 4–8 (tapered blade cathode)",
        material: "High-conductivity copper / brass",
        default_potential_v: -20000.0,
        provenance_badge: "PUBLISHED HYPOTHESIS",
        dimensions_mm: { width: 50.8, height: 25.4, thickness: 1.27, tip_radius: 0.1 },
        force_description: "Local attractive electrostatic traction pulling forward toward ground electrode (+X direction)",
        nominal_force_n: 0.045,
        force_vector: [0.045, 0.0, 0.0],
        status: "LOCAL TRACTION PRESENT (DOES NOT IMPLY WHOLE-BODY THRUST)"
      },
      {
        id: "ground_electrode",
        name: "Ground Counter-Electrode",
        role: "Planar collector electrode held at reference ground potential (0 V)",
        citation: "US11511891B2, FIGS. 4–8; col. 6 lines 46–60",
        material: "Polished aluminum plate / collector mesh",
        default_potential_v: 0.0,
        provenance_badge: "ESTABLISHED MODEL",
        dimensions_mm: { width: 60.0, height: 40.0, thickness: 2.0 },
        force_description: "Equal and opposite reaction traction pulling backward toward blade electrode (-X direction)",
        nominal_force_n: -0.038,
        force_vector: [-0.038, 0.0, 0.0],
        status: "REACTION FORCE OBSERVED"
      },
      {
        id: "dielectric_block",
        name: "Solid Dielectric Barrier / Potting",
        role: "High-voltage breakdown suppression and dielectric polarization region",
        citation: "US11511891B2, FIG. 7 (dielectric potting)",
        material: "Epoxy resin / PTFE / FR-4",
        default_eps_r: 3.8,
        provenance_badge: "WHAT-IF PARAMETER",
        dimensions_mm: { width: 70.0, height: 45.0, depth: 50.8 },
        force_description: "Dielectric virtual-work polarization traction directed toward high-field region",
        nominal_force_n: -0.005,
        force_vector: [-0.005, 0.0, 0.0],
        status: "POLARIZATION STRESS BALANCED BY INTERNAL MATERIAL STRAIN"
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
        force_description: "Internal mechanical constraint force holding electrodes apart against electrostatic attraction",
        nominal_force_n: 0.0,
        force_vector: [0.0, 0.0, 0.0],
        status: "STRUCTURAL CONSTRAINT FORCE"
      },
      {
        id: "enclosure_walls",
        name: "Conductive Enclosure (Chamber)",
        role: "Faraday shield, vacuum chamber boundary, and capacitive return wall",
        citation: "Standard vacuum chamber / grounded enclosure",
        material: "Stainless steel chamber",
        default_potential_v: 0.0,
        provenance_badge: "ESTABLISHED MODEL",
        dimensions_mm: { width: 160.0, height: 120.0, depth: 160.0 },
        force_description: "Wall reaction traction from image charges induced by high-voltage blade",
        nominal_force_n: -0.002,
        force_vector: [-0.002, 0.0, 0.0],
        status: "EXTERNAL BOUNDARY COUPLING"
      }
    ],
    whole_body_ledger: {
      blade_traction_n: 0.045,
      ground_reaction_n: -0.038,
      dielectric_traction_n: -0.005,
      enclosure_reaction_n: -0.002,
      net_closed_system_force_n: 0.000,
      whole_body_thrust_status: "NOT MEASURED / NOT ESTABLISHED",
      conservation_law: "Newton's Third Law & Maxwell Stress Surface Integral (sum F_x = 0)",
      scientific_statement: "In conventional electrodynamics, internal electrostatic forces and mechanical reactions on a closed rigid system sum identically to zero. Local asymmetry in electric field strength does NOT produce net propellantless thrust."
    },
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
  let fieldGroup, forceGroup, geometryGroup, enclosureGroup;
  let selectedComponentId = null;
  let hoveredMesh = null;

  // Parameters
  let currentVoltageKV = 20.0;
  let currentEpsR = 3.8;
  let currentGapMM = 25.0;

  // Tour State
  let tourCurrentStep = 0;
  const tourSteps = [
    {
      title: "1. What am I seeing?",
      body: `
        <p>You are viewing an <strong>asymmetric high-voltage electrode assembly</strong> inspired by Exodus patent US11511891B2 (FIGS. 4–8).</p>
        <p>The <strong style="color:var(--color-blade)">red knife-edge blade</strong> is charged to -20 kV opposite the <strong style="color:var(--color-ground)">green ground plate</strong> at 0 V. A semitransparent <strong style="color:var(--color-dielectric)">dielectric potting block</strong> sits between them inside a grounded stainless steel chamber.</p>
        <p><em>Click and drag anywhere to rotate the 3D model, or pinch/scroll to zoom.</em></p>
      `,
      cameraPos: { x: 90, y: 55, z: 110 },
      target: { x: 0, y: 0, z: 0 },
      highlight: "blade_electrode"
    },
    {
      title: "2. Why does it happen?",
      body: `
        <p><strong>Electric Field Concentration:</strong> The sharp wedge of the blade creates an intense electric field gradient near its tip ($E \\propto 1/r$).</p>
        <p><strong>Maxwell Electrostatic Stress:</strong> Electric field lines act like stretched elastic cords under tension ($T_{xx} = \\frac{1}{2}\\varepsilon_0 E_x^2$). This exerts a strong forward pull on the blade edge.</p>
        <p>Notice the cyan field streamlines flowing from the high-voltage blade tip across to the planar ground collector.</p>
      `,
      cameraPos: { x: 30, y: 20, z: 50 },
      target: { x: 5, y: 0, z: 0 },
      highlight: "blade_electrode"
    },
    {
      title: "3. What changes it?",
      body: `
        <p><strong>Quadratic Voltage Scaling:</strong> Electrostatic force scales strictly with $V^2$. Doubling voltage quadruples the force.</p>
        <p><strong>Action and Reaction:</strong> Look at the <strong style="color:var(--color-force)">golden force arrows</strong>. While the blade is pulled forward, the ground plate is pulled backward with an equal and opposite attraction!</p>
        <p>Dielectric polarization stress and chamber wall coupling absorb the remaining balance. Internal forces sum identically to <strong>zero</strong>.</p>
      `,
      cameraPos: { x: 0, y: 70, z: 90 },
      target: { x: 0, y: 0, z: 0 },
      highlight: "ground_electrode"
    },
    {
      title: "4. How could we test it?",
      body: `
        <p><strong>Testing for Real Propellantless Thrust:</strong> To prove whether net propulsion exists, we must measure the <em>entire closed system</em> on a micro-Newton torsion pendulum in high vacuum ($< 10^{-5}\\text{ Torr}$).</p>
        <p><strong>Crucial Null Controls:</strong></p>
        <ul>
          <li>Eliminate ion wind (corona discharge into air) via deep vacuum.</li>
          <li>Invert polarity: electrostatic force is symmetric ($V^2$), while discharge drifts asymmetrically.</li>
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

    const width = container.clientWidth;
    const height = container.clientHeight;

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
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.45);
    scene.add(ambientLight);

    const mainLight = new THREE.DirectionalLight(0xffffff, 0.85);
    mainLight.position.set(80, 120, 90);
    mainLight.castShadow = true;
    mainLight.shadow.mapSize.width = 1024;
    mainLight.shadow.mapSize.height = 1024;
    scene.add(mainLight);

    const fillLight = new THREE.DirectionalLight(0x38bdf8, 0.35);
    fillLight.position.set(-80, -40, -60);
    scene.add(fillLight);

    // Tip Accent Glow Light
    const bladeGlow = new THREE.PointLight(0xf43f5e, 1.2, 50);
    bladeGlow.position.set(0, 15, 0);
    scene.add(bladeGlow);

    // Subtle coordinate ground grid
    const gridHelper = new THREE.GridHelper(160, 32, 0x273545, 0x16202c);
    gridHelper.position.y = -25;
    scene.add(gridHelper);

    // Coordinate Axes Helper (small in bottom corner)
    const axesHelper = new THREE.AxesHelper(15);
    axesHelper.position.set(-70, -24, -70);
    scene.add(axesHelper);

    // Groups
    geometryGroup = new THREE.Group();
    fieldGroup = new THREE.Group();
    forceGroup = new THREE.Group();
    enclosureGroup = new THREE.Group();

    scene.add(geometryGroup);
    scene.add(fieldGroup);
    scene.add(forceGroup);
    scene.add(enclosureGroup);
  }

  // --- Build 3D Scene Elements ---
  function buildScene() {
    // 1. Blade Electrode (Asymmetric Tapered Wedge - US11511891B2 FIGS. 4–8)
    // Modeled with sharp front edge at +X, thick back spine at -X
    const bladeGeo = createBladeWedgeGeometry(30, 20, 2);
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

    // 2. Ground Counter-Electrode (Planar Collector at +X)
    const groundGeo = new THREE.BoxGeometry(4, 35, 45);
    const groundMat = new THREE.MeshStandardMaterial({
      color: 0x10b981,
      roughness: 0.25,
      metalness: 0.9,
      emissive: 0x064e3b,
      emissiveIntensity: 0.2
    });
    const groundMesh = new THREE.Mesh(groundGeo, groundMat);
    groundMesh.position.set(currentGapMM, 0, 0);
    groundMesh.castShadow = true;
    groundMesh.receiveShadow = true;
    groundMesh.userData = { id: "ground_electrode", name: "Ground Counter-Electrode" };
    geometryGroup.add(groundMesh);
    componentMeshes["ground_electrode"] = groundMesh;

    // 3. Dielectric Block (Epoxy / PTFE Potting Barrier)
    const dielGeo = new THREE.BoxGeometry(36, 26, 40);
    const dielMat = new THREE.MeshPhysicalMaterial({
      color: 0x818cf8,
      roughness: 0.15,
      metalness: 0.05,
      transmission: 0.75, // Glassy/refractive appearance
      transparent: true,
      opacity: 0.55,
      ior: 1.55
    });
    const dielMesh = new THREE.Mesh(dielGeo, dielMat);
    dielMesh.position.set(5, 0, 0);
    dielMesh.receiveShadow = true;
    dielMesh.userData = { id: "dielectric_block", name: "Solid Dielectric Barrier / Potting" };
    geometryGroup.add(dielMesh);
    componentMeshes["dielectric_block"] = dielMesh;

    // 4. Structural Support Stand (Delrin/PEEK Insulating Base)
    const mountGeo = new THREE.BoxGeometry(85, 6, 70);
    const mountMat = new THREE.MeshStandardMaterial({
      color: 0x475569,
      roughness: 0.7,
      metalness: 0.1
    });
    const mountMesh = new THREE.Mesh(mountGeo, mountMat);
    mountMesh.position.set(5, -20, 0);
    mountMesh.receiveShadow = true;
    mountMesh.userData = { id: "support_mount", name: "Structural Support Mount" };
    geometryGroup.add(mountMesh);
    componentMeshes["support_mount"] = mountMesh;

    // 5. Conductive Enclosure / Chamber Walls
    const chamberGeo = new THREE.BoxGeometry(130, 90, 110);
    const chamberWire = new THREE.WireframeGeometry(chamberGeo);
    const chamberLine = new THREE.LineSegments(chamberWire);
    chamberLine.material.color.setHex(0x334155);
    chamberLine.material.transparent = true;
    chamberLine.material.opacity = 0.45;

    // Subtle translucent chamber box
    const chamberSolidMat = new THREE.MeshBasicMaterial({
      color: 0x1e293b,
      transparent: true,
      opacity: 0.08,
      side: THREE.BackSide
    });
    const chamberMesh = new THREE.Mesh(chamberGeo, chamberSolidMat);
    chamberMesh.userData = { id: "enclosure_walls", name: "Conductive Enclosure (Chamber)" };
    chamberMesh.add(chamberLine);
    enclosureGroup.add(chamberMesh);
    componentMeshes["enclosure_walls"] = chamberMesh;

    // Build Electric Field Streamlines
    updateFieldLines();

    // Build Force Vectors
    updateForceVectors();
  }

  // --- Helper: Tapered Blade Wedge Geometry ---
  function createBladeWedgeGeometry(lengthX, heightY, spineZ) {
    const geom = new THREE.BufferGeometry();
    const halfH = heightY / 2;
    const halfZ = spineZ / 2;

    // 6 Vertices defining a triangular prism knife-edge:
    // 0: tip top (+X, +Y, 0)
    // 1: tip bottom (+X, -Y, 0)
    // 2: spine top-front (-X, +Y, +Z)
    // 3: spine bottom-front (-X, -Y, +Z)
    // 4: spine top-back (-X, +Y, -Z)
    // 5: spine bottom-back (-X, -Y, -Z)
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
      // Top face
      0, 2, 4,
      // Bottom face
      1, 5, 3,
      // Front side (+Z slant)
      0, 1, 3,
      0, 3, 2,
      // Back side (-Z slant)
      0, 4, 5,
      0, 5, 1,
      // Back spine flat face
      2, 3, 5,
      2, 5, 4
    ];

    geom.setAttribute('position', new THREE.BufferAttribute(vertices, 3));
    geom.setIndex(indices);
    geom.computeVertexNormals();
    return geom;
  }

  // --- Build / Update Electric Field Streamlines ---
  function updateFieldLines() {
    while (fieldGroup.children.length > 0) {
      const obj = fieldGroup.children[0];
      fieldGroup.remove(obj);
      if (obj.geometry) obj.geometry.dispose();
      if (obj.material) obj.material.dispose();
    }

    const voltageRatio = currentVoltageKV / 20.0;
    const opacity = Math.min(0.9, 0.4 + voltageRatio * 0.4);
    const bladeTipX = 0; // Blade tip position
    const groundX = currentGapMM;

    // Generate curvilinear field lines from blade tip spreading toward ground plate
    const numLines = 28;
    for (let i = 0; i < numLines; i++) {
      const angle = (i / numLines) * Math.PI * 2;
      const spreadY = Math.sin(angle) * (6 + (i % 3) * 5);
      const spreadZ = Math.cos(angle) * (8 + (i % 4) * 6);

      // 3-point Bezier quadratic curve
      const p0 = new THREE.Vector3(bladeTipX, 0, 0); // Origin at sharp tip
      const p1 = new THREE.Vector3((bladeTipX + groundX) * 0.4, spreadY * 1.3, spreadZ * 1.3); // Mid outward bow
      const p2 = new THREE.Vector3(groundX, spreadY * 0.85, spreadZ * 0.85); // Terminal at ground plate

      const curve = new THREE.QuadraticBezierCurve3(p0, p1, p2);
      const points = curve.getPoints(24);
      const geom = new THREE.BufferGeometry().setFromPoints(points);

      // Color gradient from high potential (magenta) to ground (cyan)
      const colors = [];
      const cStart = new THREE.Color(0xf43f5e);
      const cEnd = new THREE.Color(0x38bdf8);
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
      fieldGroup.add(line);
    }

    // Add Equipotential Rings around the blade tip
    const ringRadii = [4, 8, 14, 22];
    ringRadii.forEach((r, idx) => {
      const ringGeo = new THREE.RingGeometry(r - 0.2, r + 0.2, 32);
      const ringMat = new THREE.MeshBasicMaterial({
        color: 0x38bdf8,
        transparent: true,
        opacity: Math.max(0.1, 0.45 - idx * 0.09) * voltageRatio,
        side: THREE.DoubleSide
      });
      const ringMesh = new THREE.Mesh(ringGeo, ringMat);
      ringMesh.rotation.y = Math.PI / 2;
      ringMesh.position.set(bladeTipX + (idx + 1) * 2, 0, 0);
      fieldGroup.add(ringMesh);
    });
  }

  // --- Build / Update Force Vectors ---
  function updateForceVectors() {
    while (forceGroup.children.length > 0) {
      const obj = forceGroup.children[0];
      forceGroup.remove(obj);
      if (obj.geometry) obj.geometry.dispose();
      if (obj.material) obj.material.dispose();
    }

    // Force scales quadratically with voltage: F ~ (V / V0)^2
    const scaleFactor = Math.pow(currentVoltageKV / 20.0, 2);

    // 1. Blade Attractive Force (Traction toward ground: +X)
    const bladeForceMag = 25 * scaleFactor;
    if (bladeForceMag > 0.5) {
      const arrowBlade = createCustomArrow(
        new THREE.Vector3(1, 0, 0),
        new THREE.Vector3(0, 0, 0),
        bladeForceMag,
        0xfacc15,
        "F_blade (+X attraction)"
      );
      forceGroup.add(arrowBlade);
    }

    // 2. Ground Reaction Force (Traction toward blade: -X)
    const groundForceMag = 22 * scaleFactor;
    if (groundForceMag > 0.5) {
      const arrowGround = createCustomArrow(
        new THREE.Vector3(-1, 0, 0),
        new THREE.Vector3(currentGapMM, 0, 0),
        groundForceMag,
        0xfacc15,
        "F_ground (-X reaction)"
      );
      forceGroup.add(arrowGround);
    }

    // 3. Dielectric Polarization Stress (Virtual-work pull: -X)
    const dielForceMag = 5 * scaleFactor * (currentEpsR / 3.8);
    if (dielForceMag > 0.5) {
      const arrowDiel = createCustomArrow(
        new THREE.Vector3(-1, 0, 0),
        new THREE.Vector3(10, 16, 0),
        dielForceMag,
        0x818cf8,
        "F_dielectric (polarization)"
      );
      forceGroup.add(arrowDiel);
    }

    // 4. Mount Reaction Force (Balancing internal traction)
    const mountForceMag = 18 * scaleFactor;
    if (mountForceMag > 0.5) {
      const arrowMount = createCustomArrow(
        new THREE.Vector3(1, 0, 0),
        new THREE.Vector3(5, -20, 0),
        mountForceMag,
        0x64748b,
        "F_mount (mechanical constraint)"
      );
      forceGroup.add(arrowMount);
    }
  }

  // --- Helper: Clean 3D Arrow with Mesh Cylinder and Cone ---
  function createCustomArrow(dir, origin, length, hexColor, labelText) {
    const group = new THREE.Group();
    group.position.copy(origin);

    const normDir = dir.clone().normalize();
    const arrowLength = Math.max(length, 2);
    const headLength = Math.min(arrowLength * 0.3, 6);
    const shaftLength = arrowLength - headLength;
    const shaftRadius = 0.7;
    const headRadius = 1.6;

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

    // Orient arrow along dir
    const up = new THREE.Vector3(0, 1, 0);
    const quaternion = new THREE.Quaternion().setFromUnitVectors(up, normDir);
    group.quaternion.copy(quaternion);

    group.userData = { isArrow: true, label: labelText };
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
        btn.setAttribute('role', 'option');
        btn.dataset.id = comp.id;
        btn.innerHTML = `
          <span>${comp.name}</span>
          <span class="provenance-pill ${getPillClass(comp.provenance_badge)}">${comp.provenance_badge}</span>
        `;
        btn.addEventListener('click', () => selectComponent(comp.id));
        compListContainer.appendChild(btn);
      });
    }

    // 2. Whole-Body Force Ledger Table
    const ledgerTableBody = document.getElementById('ledger-table-body');
    if (ledgerTableBody && provenanceData.components) {
      ledgerTableBody.innerHTML = '';
      provenanceData.components.forEach(comp => {
        const tr = document.createElement('tr');
        const forceStr = comp.nominal_force_n !== undefined && comp.nominal_force_n !== null
          ? `${(comp.nominal_force_n >= 0 ? '+' : '')}${comp.nominal_force_n.toFixed(3)} N`
          : '—';
        tr.innerHTML = `
          <td><strong>${comp.name}</strong></td>
          <td style="font-family:var(--font-mono)">${forceStr}</td>
          <td style="color:var(--text-secondary)">${comp.role}</td>
        `;
        ledgerTableBody.appendChild(tr);
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

  // --- Select & Inspect Component ---
  function selectComponent(id) {
    selectedComponentId = id;

    // Highlight in listbox
    const items = document.querySelectorAll('.component-item-btn');
    items.forEach(el => {
      if (el.dataset.id === id) {
        el.classList.add('selected');
        el.setAttribute('aria-selected', 'true');
      } else {
        el.classList.remove('selected');
        el.setAttribute('aria-selected', 'false');
      }
    });

    // Switch to inspector tab
    switchTab('tab-inspector');

    // Find component data
    const comp = provenanceData.components.find(c => c.id === id);
    if (!comp) return;

    // Update Inspector Card
    document.getElementById('inspector-name').textContent = comp.name;
    const badge = document.getElementById('inspector-badge');
    badge.textContent = comp.provenance_badge;
    badge.className = `provenance-pill ${getPillClass(comp.provenance_badge)}`;

    document.getElementById('inspector-role').textContent = comp.role;
    document.getElementById('inspector-citation').textContent = comp.citation || '—';
    document.getElementById('inspector-material').textContent = comp.material || '—';
    document.getElementById('inspector-potential').textContent = comp.default_potential_v !== null
      ? `${(comp.default_potential_v / 1000).toFixed(1)} kV`
      : 'Non-conductive / N/A';

    const dims = comp.dimensions_mm;
    document.getElementById('inspector-dimensions').textContent = dims
      ? `${dims.width} × ${dims.height} × ${(dims.thickness || dims.depth || 0)} mm`
      : '—';

    document.getElementById('inspector-force').textContent = comp.nominal_force_n !== undefined
      ? `${(comp.nominal_force_n >= 0 ? '+' : '')}${comp.nominal_force_n.toFixed(3)} N`
      : '0.000 N';

    document.getElementById('inspector-status').textContent = comp.status || '—';
    document.getElementById('inspector-explanation').innerHTML = `
      <strong>Physical Context:</strong> ${comp.force_description}
    `;

    // Highlight 3D mesh
    highlightMesh(id);

    // Show temporary banner notification
    showBanner(`Inspecting: ${comp.name} (${comp.provenance_badge})`);
  }

  function highlightMesh(id) {
    Object.keys(componentMeshes).forEach(key => {
      const mesh = componentMeshes[key];
      if (key === id) {
        if (mesh.material && mesh.material.emissive) {
          mesh.material.emissiveIntensity = 0.75;
        }
      } else {
        if (mesh.material && mesh.material.emissive) {
          mesh.material.emissiveIntensity = 0.2;
        }
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
  function setViewPreset(preset) {
    const dist = 140;
    const target = new THREE.Vector3(0, 0, 0);
    let newPos;

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
        newPos = new THREE.Vector3(0, dist, 0);
        break;
      default:
        newPos = new THREE.Vector3(90, 60, 110);
    }

    animateCameraTo(newPos, target);
  }

  function animateCameraTo(targetPos, targetLookAt, durationMs = 600) {
    const startPos = camera.position.clone();
    const startTarget = controls.target.clone();
    const startTime = performance.now();

    function update() {
      const elapsed = performance.now() - startTime;
      const t = Math.min(elapsed / durationMs, 1.0);
      const ease = t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t; // Smooth quadratic ease

      camera.position.lerpVectors(startPos, targetPos, ease);
      controls.target.lerpVectors(startTarget, targetLookAt, ease);
      controls.update();

      if (t < 1.0) {
        requestAnimationFrame(update);
      }
    }
    requestAnimationFrame(update);
  }

  // --- Tour Functions ---
  function openTour(stepIndex = 0) {
    tourCurrentStep = stepIndex;
    const modal = document.getElementById('tour-modal');
    if (modal) modal.classList.remove('hidden');
    renderTourStep();
  }

  function closeTour() {
    const modal = document.getElementById('tour-modal');
    if (modal) modal.classList.add('hidden');
  }

  function renderTourStep() {
    const step = tourSteps[tourCurrentStep];
    if (!step) return;

    document.getElementById('tour-step-count').textContent = `Step ${tourCurrentStep + 1} of ${tourSteps.length}`;
    document.getElementById('tour-step-title').textContent = step.title;
    document.getElementById('tour-step-body').innerHTML = step.body;

    // Update dots
    const dots = document.querySelectorAll('.tour-dots .dot');
    dots.forEach((dot, idx) => dot.classList.toggle('active', idx === tourCurrentStep));

    // Update prev/next buttons
    const prevBtn = document.getElementById('tour-btn-prev');
    const nextBtn = document.getElementById('tour-btn-next');
    prevBtn.disabled = tourCurrentStep === 0;
    nextBtn.textContent = tourCurrentStep === tourSteps.length - 1 ? 'Finish Tour' : 'Next';

    // Move camera to step viewpoint
    if (step.cameraPos && step.target) {
      animateCameraTo(
        new THREE.Vector3(step.cameraPos.x, step.cameraPos.y, step.cameraPos.z),
        new THREE.Vector3(step.target.x, step.target.y, step.target.z),
        800
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

    // Canvas Raycaster Clicking
    const container = document.getElementById('viewport-container');
    container.addEventListener('pointerdown', onPointerDown);

    // Preset HUD Buttons
    document.querySelectorAll('.view-preset-hud .hud-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        document.querySelectorAll('.view-preset-hud .hud-btn').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        setViewPreset(e.target.dataset.view);
      });
    });

    // Reset View Button in Header
    document.getElementById('btn-reset-view').addEventListener('click', () => {
      setViewPreset('isometric');
      showBanner("Camera reset to default isometric view.");
    });

    // Start Tour Button in Header
    document.getElementById('btn-start-tour').addEventListener('click', () => openTour(0));
    document.getElementById('tour-btn-close').addEventListener('click', closeTour);
    document.getElementById('tour-btn-next').addEventListener('click', nextTourStep);
    document.getElementById('tour-btn-prev').addEventListener('click', prevTourStep);

    // Help Modal
    const helpModal = document.getElementById('help-modal');
    document.getElementById('btn-toggle-help').addEventListener('click', () => {
      helpModal.classList.remove('hidden');
    });
    document.getElementById('help-btn-close').addEventListener('click', () => {
      helpModal.classList.add('hidden');
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
      fieldGroup.visible = e.target.checked;
    });
    document.getElementById('toggle-forces').addEventListener('change', (e) => {
      forceGroup.visible = e.target.checked;
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
      valVoltage.textContent = `-${currentVoltageKV.toFixed(1)} kV`;
      updateFieldLines();
      updateForceVectors();
    });

    const sliderEps = document.getElementById('slider-eps');
    const valEps = document.getElementById('val-eps');
    sliderEps.addEventListener('input', (e) => {
      currentEpsR = parseFloat(e.target.value);
      valEps.textContent = `${currentEpsR.toFixed(1)} (${currentEpsR < 1.5 ? 'Air/Vacuum' : 'Epoxy/FR4'})`;
      if (componentMeshes["dielectric_block"]) {
        componentMeshes["dielectric_block"].material.opacity = 0.3 + (currentEpsR / 5.0) * 0.45;
      }
      updateForceVectors();
    });

    const sliderGap = document.getElementById('slider-gap');
    const valGap = document.getElementById('val-gap');
    sliderGap.addEventListener('input', (e) => {
      currentGapMM = parseFloat(e.target.value);
      valGap.textContent = `${currentGapMM.toFixed(1)} mm`;
      if (componentMeshes["ground_electrode"]) {
        componentMeshes["ground_electrode"].position.x = currentGapMM;
      }
      updateFieldLines();
      updateForceVectors();
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
      // Don't intercept if focused on inputs
      if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;

      switch (e.key) {
        case 'ArrowLeft':
          controls.rotateLeft(0.08);
          break;
        case 'ArrowRight':
          controls.rotateLeft(-0.08);
          break;
        case 'ArrowUp':
          controls.rotateUp(0.08);
          break;
        case 'ArrowDown':
          controls.rotateUp(-0.08);
          break;
        case '+':
        case '=':
          controls.dollyIn(1.15);
          break;
        case '-':
        case '_':
          controls.dollyOut(1.15);
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
          break;
      }
    });
  }

  // --- Raycasting for 3D Component Picking ---
  function onPointerDown(event) {
    const rect = renderer.domElement.getBoundingClientRect();
    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObjects(geometryGroup.children, true);

    if (intersects.length > 0) {
      let targetObj = intersects[0].object;
      while (targetObj && (!targetObj.userData || !targetObj.userData.id)) {
        targetObj = targetObj.parent;
      }
      if (targetObj && targetObj.userData && targetObj.userData.id) {
        selectComponent(targetObj.userData.id);
      }
    }
  }

  function onWindowResize() {
    const container = document.getElementById('viewport-container');
    if (!container || !renderer || !camera) return;

    const width = container.clientWidth;
    const height = container.clientHeight;

    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
  }

  // --- Animation Loop ---
  function animate() {
    requestAnimationFrame(animate);

    controls.update();

    // Subtle gentle field line oscillation to evoke dynamic electric flux
    const time = performance.now() * 0.0015;
    if (fieldGroup && fieldGroup.visible) {
      fieldGroup.children.forEach((child, idx) => {
        if (child.isLine) {
          child.material.opacity = 0.35 + Math.sin(time * 2 + idx) * 0.12;
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
