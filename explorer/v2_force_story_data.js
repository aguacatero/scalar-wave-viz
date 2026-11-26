/**
 * Propulsion Explorer V2-A — Force Story Data, Epistemic Crosswalk, Typed Ledgers & Validators
 *
 * Implements frozen V2 Design Specification R4 (docs/V2_FORCE_STORY_SPEC.md, blob 7d4b66be574b937f3750d135f351d3b1e6e3f142):
 * - Section 2.1: 7-class EpistemicClass <-> 5-category Scientific Charter crosswalk
 * - Section 2.2-2.5: Segregated Surface A (qualitative 3D Exodus DUT H0/H1/H2) vs Surface B (separate 1D/2D P0/P1 analogues)
 * - Section 3.1-3.2: Boundary A/B/C definitions & lossless native V1 status/error/study mapping
 * - Section 7.1.1: 8-predicate atomic V1 -> V2 synchronization & transport-epoch validation
 * - Section 7.3: Exhaustive discriminated LedgerRowValue, ConvergenceStudyStatusRecord, ForceLedgerSnapshot schemas & validators
 *
 * Non-negotiable scientific constraints:
 * - Strict unit segregation: 1D (N), 2D (N/m), 3D Exodus (PENDING_SCIENTIFIC_ACCEPTANCE)
 * - Numerical closure residual is NEVER labeled propellantless thrust
 * - NEVER coerce unknowns, withheld values, errors, or pending states to numeric 0.0
 * - Zero unaccepted Track B P2 code, meshes, or outputs
 * - WHOLE-BODY THRUST: NOT MEASURED / NOT ESTABLISHED
 */

(function (root, factory) {
  var api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  if (root && typeof root === "object") {
    root.V2ForceStoryData = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : (typeof window !== "undefined" ? window : this), function () {
  "use strict";

  var SCHEMA_VERSION = "v2.0";
  var WHOLE_BODY_THRUST_STATUS = "NOT MEASURED / NOT ESTABLISHED";
  var P2_SCIENTIFIC_STATUS = "PENDING_SCIENTIFIC_ACCEPTANCE";
  var FORCE_BALANCE_TOLERANCE_N_PER_M = 1e-4;

  var FROZEN_KERNEL_BLOB_SHA1 = Object.freeze({
    electrostatics_baseline: "97f65dfa25db7730323edd5e52c98b17371fdeaa",
    electrostatics_numerics: "a29f1f3a55946f33760179677dd3dbeb6a2ebde2"
  });

  var FROZEN_SPEC_BLOB_SHA1 = Object.freeze({
    v1_solver_integration_spec: "3ccf8ae0e8caa4d367d93eddd173dda98a13f00a",
    v2_force_story_spec: "7d4b66be574b937f3750d135f351d3b1e6e3f142"
  });

  var EPISTEMIC_CLASSES = Object.freeze([
    "ESTABLISHED_MODEL",
    "PUBLISHED_HYPOTHESIS",
    "CONDITIONAL_CONFOUNDER_MODEL",
    "EXPERIMENTAL_MEASUREMENT",
    "PROVISIONAL_ILLUSTRATIVE_SCENE",
    "TOY_MATHEMATICAL_ILLUSTRATION",
    "UNVERIFIED_PENDING_P2"
  ]);

  var CHARTER_CATEGORIES = Object.freeze([
    "ESTABLISHED MODEL",
    "PUBLISHED HYPOTHESIS",
    "WHAT-IF PARAMETER",
    "EXPERIMENTAL MEASUREMENT",
    "UNVERIFIED NUMERICAL OUTPUT"
  ]);

  var EPISTEMIC_CROSSWALK = Object.freeze({
    ESTABLISHED_MODEL: Object.freeze({
      badge_label: "ESTABLISHED MODEL",
      pill_class: "pill-established",
      charter_categories: Object.freeze(["ESTABLISHED MODEL"]),
      what_if_rule: "Canonical physical constants carry no WHAT-IF tag; exploratory user inputs carry WHAT-IF PARAMETER disclosure.",
      permitted_use: "Frozen P0/P1 solver outputs (parallel_plate_1d, grounded_box_2d) and textbook conservation laws.",
      prohibited_use: "Claiming experimental validation or 3D Exodus net thrust."
    }),
    PUBLISHED_HYPOTHESIS: Object.freeze({
      badge_label: "PUBLISHED HYPOTHESIS",
      pill_class: "pill-hypothesis",
      charter_categories: Object.freeze(["PUBLISHED HYPOTHESIS"]),
      what_if_rule: "Patent-cited dimensions and voltages are flagged as sourced claims, not validated measurements.",
      permitted_use: "Cited Exodus patent claims/equations (US11511891B2, US20230121805A1, US20240011469A1) with contested-derivation audit.",
      prohibited_use: "Implying physical validation or displaying unaccepted P2 numerical outputs."
    }),
    CONDITIONAL_CONFOUNDER_MODEL: Object.freeze({
      badge_label: "CONDITIONAL CONFOUNDER MODEL",
      pill_class: "pill-whatif",
      charter_categories: Object.freeze(["ESTABLISHED MODEL", "WHAT-IF PARAMETER"]),
      what_if_rule: "Mandatory WHAT-IF PARAMETER badge on every user-adjusted unmeasured parameter.",
      permitted_use: "Validity-bounded qualitative/order-of-magnitude confounder framing (interactive comparators deferred to V2-B).",
      prohibited_use: "Presenting as calibrated apparatus measurement or extrapolating outside stated validity regime."
    }),
    EXPERIMENTAL_MEASUREMENT: Object.freeze({
      badge_label: "EXPERIMENTAL MEASUREMENT",
      pill_class: "pill-established",
      charter_categories: Object.freeze(["EXPERIMENTAL MEASUREMENT"]),
      what_if_rule: "None (peer-reviewed sourced values with apparatus and uncertainty only).",
      permitted_use: "Peer-reviewed experimental bounds such as Tajmar & Schreiber (2020) (+/-0.3 mg ~= +/-3 uN under studied configurations).",
      prohibited_use: "Synthetic or simulated data, or uncited thrust claims."
    }),
    PROVISIONAL_ILLUSTRATIVE_SCENE: Object.freeze({
      badge_label: "PROVISIONAL ILLUSTRATIVE SCENE",
      pill_class: "pill-provisional",
      charter_categories: Object.freeze(["UNVERIFIED NUMERICAL OUTPUT", "WHAT-IF PARAMETER"]),
      what_if_rule: "Mandatory WHAT-IF PARAMETER / VISUAL PROXY ONLY notice on dielectric permittivity slider.",
      permitted_use: "3D Exodus schematic geometry, schematic field/force directions, Boundary A/B visual cut-shells.",
      prohibited_use: "Attaching computed 1D N or 2D N/m values as 3D blade forces."
    }),
    TOY_MATHEMATICAL_ILLUSTRATION: Object.freeze({
      badge_label: "MATHEMATICAL TOY (ISOLATED)",
      pill_class: "pill-whatif",
      charter_categories: Object.freeze(["UNVERIFIED NUMERICAL OUTPUT", "WHAT-IF PARAMETER"]),
      what_if_rule: "Toy wave speed/frequency parameters are explicitly non-physical.",
      permitted_use: "Chapter 5 isolated 3D scalar-wave contrast view.",
      prohibited_use: "Coupling to capacitor force ledgers or propulsion claims."
    }),
    UNVERIFIED_PENDING_P2: Object.freeze({
      badge_label: "PENDING SCIENTIFIC ACCEPTANCE (P2)",
      pill_class: "pill-unverified",
      charter_categories: Object.freeze(["UNVERIFIED NUMERICAL OUTPUT"]),
      what_if_rule: "Not applicable (value is strictly null pending Track B P2 acceptance).",
      permitted_use: "3D Exodus whole-device electrostatic/dielectric force slots (value: null, blocking_gate: TRACK_B_P2).",
      prohibited_use: "Substituting 0.0 or importing unaccepted Track B P2 outputs."
    })
  });

  var NULL_VALUE_STATUSES = Object.freeze([
    "UNKNOWN_UNMODELED",
    "OUT_OF_MODEL_VALIDITY_REGIME",
    "INVALID_COMPARATOR_INPUT",
    "NOT_APPLICABLE_VACUUM_MODEL",
    "NOT_APPLICABLE_OPEN_1D_LIMIT",
    "CLEARED_PENDING_OR_INACTIVE",
    "NOT_RUN_SWEEP_TERMINATED"
  ]);

  var SOURCE_SCOPES = Object.freeze([
    "primary_force_budget",
    "convergence_study",
    "comparator_estimate",
    "qualitative_3d_dut",
    "null_control_sweep"
  ]);

  var BOUNDARY_DEFINITIONS = Object.freeze([
    Object.freeze({
      id: "boundary_a_dut",
      short_label: "Boundary A",
      title: "Boundary A — Device Under Test (DUT Control Volume)",
      color_class: "v2-bnd-a",
      control_volume: "Suspended test assembly: high-voltage electrode(s), counter-electrode, dielectric potting (3D schematic only), and internal structural mount.",
      conservation_html: "&sum; <b>F</b><sub>internal</sub> &equiv; <b>0</b> (Newton III pairwise cancellation); <b>F</b><sub>DUT,net</sub> = &conint;<sub>&part;V<sub>A</sub></sub> <b>T</b>&middot;<b>n&#770;</b> dA + <b>F</b><sub>mech,ext</sub> + <b>F</b><sub>gas/ion</sub> = <b>F</b><sub>external</sub>.",
      momentum_paths: Object.freeze([
        "Internal electrode-to-electrode attraction transmitted through structural mount (closed internally).",
        "Internal dielectric polarization stress balanced by electrodes and mount (closed internally; 3D quantitative value PENDING_SCIENTIFIC_ACCEPTANCE).",
        "External electric flux crossing Boundary A to grounded Boundary B chamber walls.",
        "External power leads, feedthroughs, or ambient gas ions crossing Boundary A."
      ])
    }),
    Object.freeze({
      id: "boundary_b_environment",
      short_label: "Boundary B",
      title: "Boundary B — Chamber & External Environment",
      color_class: "v2-bnd-b",
      control_volume: "Grounded conductive vacuum chamber / enclosure walls, laboratory ground, external power leads/feedthroughs, and ambient gas (when not in high vacuum).",
      conservation_html: "<b>F</b><sub>B</sub> = <b>F</b><sub>wall,image</sub> + <b>F</b><sub>leads,ext</sub> + <b>F</b><sub>gas,reaction</sub>.",
      momentum_paths: Object.freeze([
        "Receives equal and opposite reaction force from unbalanced external electric flux (enclosure_reaction in 2D benchmark).",
        "Receives reaction forces from high-voltage feedthroughs, cable Lorentz/electrostatic forces, or atmospheric ion-wind momentum."
      ])
    }),
    Object.freeze({
      id: "boundary_c_closed",
      short_label: "Boundary C",
      title: "Boundary C — Total Closed System",
      color_class: "v2-bnd-c",
      control_volume: "Complete isolated system enclosing Boundary A + Boundary B + electromagnetic fields (E, B -> 0 at outer boundary).",
      conservation_html: "d/dt (<b>P</b><sub>DUT</sub> + <b>P</b><sub>env</sub> + <b>P</b><sub>EM,field</sub>) = <b>0</b>; in static electrostatics (<b>B</b> = <b>0</b>), <b>F</b><sub>A</sub> + <b>F</b><sub>B</sub> = <b>0</b> identically in the continuum limit.",
      momentum_paths: Object.freeze([
        "Zero net momentum creation in closed static electrostatics.",
        "Any non-zero |F_net| on a finite 2D grid is a numerical discretization closure residual, NEVER propellantless thrust."
      ])
    })
  ]);

  var H1_CONTESTED_DERIVATION_AUDIT = Object.freeze([
    Object.freeze({
      equation_ref: "US11511891B2 Eq. (4)",
      claimed_statement_html: "Claimed d(U<sub>t</sub>) = 0 from stationary action (&delta;S = 0)",
      audit_note: "Stationary action yields dynamical equations of motion along time trajectories; it does not establish pointwise spatial energy invariance d(U_t) = 0 across configuration displacements and omits power-supply electrical work (dW = V dQ) and structural reaction forces.",
      disposition: "CONTESTED_DERIVATION_PROOF_OBLIGATION"
    }),
    Object.freeze({
      equation_ref: "US11511891B2 Eq. (11)",
      claimed_statement_html: "Claimed net force F = &epsilon;<sub>0</sub>(E<sub>2</sub><sup>2</sup>A<sub>2</sub> &minus; E<sub>1</sub><sup>2</sup>A<sub>1</sub>)",
      audit_note: "(a) Omits the standard Maxwell stress factor of 1/2 in T_n = (1/2) epsilon_0 E_n^2; (b) evaluates only two opposed electrode faces while omitting lateral/rear surfaces, feedthroughs, solid dielectric polarization stress, structural mount reactions, and return flux to external grounded boundaries.",
      disposition: "PUBLISHED_HYPOTHESIS (numerical_evaluation_status: PENDING_SCIENTIFIC_ACCEPTANCE)"
    })
  ]);

  var SURFACE_A_QUALITATIVE_3D_DUT = Object.freeze({
    comparison_surface: "qualitative_3d_dut_hypotheses",
    title: "Surface A — Qualitative 3D Exodus DUT Hypotheses (H0 / H1 / H2)",
    banner: "QUALITATIVE 3D EXODUS COMPARISON — NO ACCEPTED 3D QUANTITATIVE FORCE SOLUTION (P2 PENDING)",
    subtitle: "Compares qualitative physical explanations for the provisional 3D Exodus blade-and-dielectric geometry. Separate idealized 1D and 2D P0/P1 benchmark calculations live exclusively in Surface B.",
    hypotheses: Object.freeze([
      Object.freeze({
        id: "H0",
        title: "H0 — Conventional Electrostatics & Closed-Boundary Conservation",
        epistemic_class: "ESTABLISHED_MODEL",
        quantitative_3d_status: "PENDING_SCIENTIFIC_ACCEPTANCE",
        summary: "In vacuum Maxwell electrostatics, internal pairwise electrode and dielectric stresses sum identically to zero. Any net electrostatic force on the suspended DUT must equal external flux crossing Boundary A to surrounding chamber walls or leads.",
        boundary_expectation: "F_internal = 0; F_DUT,net = F_external (3D Exodus quantitative magnitude: PENDING_SCIENTIFIC_ACCEPTANCE under Track B P2).",
        citations_html: "Jackson, <em>Classical Electrodynamics</em>; Griffiths, <em>Introduction to Electrodynamics</em> &sect;8.2.2."
      }),
      Object.freeze({
        id: "H1",
        title: "H1 — Published Exodus Patent Hypothesis (Cited & Unvalidated)",
        epistemic_class: "PUBLISHED_HYPOTHESIS",
        quantitative_3d_status: "PENDING_SCIENTIFIC_ACCEPTANCE",
        summary: "Patents US11511891B2 (FIGS. 4–8, 6B, 21, 23A; Eqs. 4–11), US20230121805A1, and US20240011469A1 propose that asymmetric electric-field gradients across a sharp blade and dielectric produce a net unidirectional force. Both key derivation steps carry open proof obligations.",
        boundary_expectation: "Claims internal net force without propellant; USPTO patent grant is NOT mathematical or experimental validation. 3D quantitative evaluation remains PENDING_SCIENTIFIC_ACCEPTANCE.",
        citations_html: "<a href='https://patents.google.com/patent/US11511891B2/en' target='_blank' rel='noopener noreferrer'>US11511891B2</a>, <a href='https://patents.google.com/patent/US20230121805A1/en' target='_blank' rel='noopener noreferrer'>US20230121805A1</a>, <a href='https://patents.google.com/patent/US20240011469A1/en' target='_blank' rel='noopener noreferrer'>US20240011469A1</a>."
      }),
      Object.freeze({
        id: "H2",
        title: "H2 — Competing Ordinary Laboratory Mechanisms (Confounders)",
        epistemic_class: "CONDITIONAL_CONFOUNDER_MODEL",
        quantitative_3d_status: "UNKNOWN_UNMODELED",
        summary: "Ordinary lab mechanisms can imitate micro-Newton to milli-Newton forces on HV setups: atmospheric corona ion wind (valid at ~1 atm collisional air only; never extrapolated to vacuum), chamber-wall image-charge coupling, geomagnetic/electrostatic lead forces, and thermal/outgassing drift.",
        boundary_expectation: "Peer-reviewed high-vacuum null benchmark: Tajmar & Schreiber (2020) bounded force changes to +/-0.3 mg (~+/-3 uN) under studied configurations. Interactive H2 comparators and Null-Control Lab are planned for Slice V2-B (not yet implemented).",
        citations_html: "Tajmar &amp; Schreiber (2020), <a href='https://doi.org/10.1016/j.elstat.2020.103477' target='_blank' rel='noopener noreferrer'><em>J. Electrostat.</em> 107, 103477</a>."
      })
    ])
  });

  var SURFACE_B_QUANTITATIVE_ANALOGUES = Object.freeze({
    comparison_surface: "quantitative_p0_p1_analogues",
    title: "Surface B — Separate Quantitative P0/P1 Benchmark Analogues",
    banner: "SEPARATE IDEALIZED P0/P1 BENCHMARK ANALOGUE — NOT 3D EXODUS GEOMETRY",
    subtitle: "Demonstrates how closed-boundary Maxwell momentum accounting behaves quantitatively in accepted 1D infinite-plate (N) and 2D grounded-box (N/m) benchmarks without implying shared geometry with the 3D Exodus blade.",
    analogues: Object.freeze({
      parallel_plate_1d: Object.freeze({
        title: "1D Ideal Parallel-Plate Benchmark (N)",
        unit_domain: "N",
        lesson: "Opposing ideal plates experience equal and opposite electrostatic forces (+F and -F) summing identically to 0.0 N, cross-checked by fixed-V and fixed-Q virtual work. Open-limit model with no grounded chamber wall and no edge fringing."
      }),
      grounded_box_2d: Object.freeze({
        title: "2D Circular Electrodes in Grounded Square Box (N/m)",
        unit_domain: "N/m",
        lesson: "In asymmetric single-ended HV (-20 kV / 0 V), left and right electrode forces do NOT cancel pairwise because unbalanced electric flux terminates on the grounded 0 V box. Adding the enclosure reaction restores F_L + F_R + F_enc -> 0 as mesh spacing h -> 0. Any non-zero |F_net| is a discretization residual, NOT thrust."
      })
    })
  });

  function isStrictFiniteNumber(v) {
    return typeof v === "number" && Number.isFinite(v);
  }

  function isStrictInteger(v) {
    return typeof v === "number" && Number.isInteger(v);
  }

  function isPlainObject(v) {
    return Boolean(v) && typeof v === "object" && !Array.isArray(v);
  }

  function makeNullUncertainty(status, note, unit) {
    return {
      status: status,
      value: null,
      unit: unit || "NONE",
      note: note
    };
  }

  /**
   * Section 7.1.1: Evaluate ALL 8 atomic V1 -> V2 synchronization predicates.
   */
  function evaluateV1SyncPredicates(v1State, lastRenderedV2Generation) {
    var minGen = isStrictInteger(lastRenderedV2Generation) ? lastRenderedV2Generation : 0;
    if (!isPlainObject(v1State)) {
      return { ok: false, failedPredicate: 1, reasonCode: "MISSING_V1_STATE" };
    }
    if (v1State.activeViewContext === "scalar_wave_contrast") {
      return { ok: false, failedPredicate: 5, reasonCode: "SCALAR_WAVE_CONTRAST_ACTIVE" };
    }
    if (v1State.solveState !== "ready") {
      return {
        ok: false,
        failedPredicate: 1,
        reasonCode: v1State.solveState === "error" ? "SOLVER_ERROR" : "PENDING_OR_IDLE"
      };
    }
    if (!isPlainObject(v1State.lastRenderedResponse)) {
      return { ok: false, failedPredicate: 2, reasonCode: "NO_RENDERED_RESPONSE" };
    }
    if (v1State.lastRenderedResponse.request_id !== v1State.latestDispatchedRequestId) {
      return { ok: false, failedPredicate: 3, reasonCode: "REQUEST_ID_MISMATCH" };
    }
    if (v1State.lastRenderedResponse.input_fingerprint !== v1State.currentCanonicalFingerprint) {
      return { ok: false, failedPredicate: 4, reasonCode: "FINGERPRINT_MISMATCH" };
    }
    var validModeView =
      (v1State.activeModelMode === "parallel_plate_1d" && v1State.activeViewContext === "v1_1d") ||
      (v1State.activeModelMode === "grounded_box_2d" && v1State.activeViewContext === "v1_2d");
    if (!validModeView) {
      return { ok: false, failedPredicate: 5, reasonCode: "MODE_VIEW_MISMATCH" };
    }
    if (!isStrictInteger(v1State.clientStateGeneration) || v1State.clientStateGeneration < minGen) {
      return { ok: false, failedPredicate: 6, reasonCode: "STALE_CLIENT_GENERATION" };
    }
    if (!isPlainObject(v1State.lastRenderedOrigin)) {
      return { ok: false, failedPredicate: 7, reasonCode: "MISSING_RESPONSE_ORIGIN" };
    }
    if (
      v1State.lastRenderedOrigin.transportMode !== v1State.transportMode ||
      v1State.lastRenderedOrigin.transportEpoch !== v1State.transportEpoch
    ) {
      return { ok: false, failedPredicate: 8, reasonCode: "TRANSPORT_EPOCH_MISMATCH" };
    }
    return { ok: true, failedPredicate: null, reasonCode: null };
  }

  /**
   * Section 3.2 & 7.3 (V2-SPEC-R2-L1, V2-SPEC-R3-M1):
   * Build independent ConvergenceStudyStatusRecord from a 2D V1 response without mutating primary rows.
   */
  function buildConvergenceStudyProvenance(resp) {
    if (!isPlainObject(resp) || !isPlainObject(resp.force_study)) {
      return {
        source_scope: "convergence_study",
        status: "NOT_REQUESTED",
        force_mesh_sensitivity_status: "NOT_ASSESSED",
        study_n_list: null,
        failed_levels: [],
        rows: [],
        derived_sensitivity: null,
        value: null
      };
    }

    var fs = resp.force_study;
    var st = String(fs.status || "");
    var nList = Array.isArray(fs.study_n_list) ? fs.study_n_list.slice() : [];

    if (st === "WITHHELD_INELIGIBLE_MESH_LEVEL" || st === "WITHHELD_INVALID_CONTOUR_TOPOLOGY") {
      var nativeFailed = [];
      if (Array.isArray(fs.failed_levels)) {
        for (var i = 0; i < fs.failed_levels.length; i++) {
          var item = fs.failed_levels[i];
          if (isPlainObject(item) && isStrictInteger(item.n) && typeof item.reason === "string" && item.reason.length > 0) {
            nativeFailed.push({ n: item.n, reason: item.reason });
          } else {
            throw new Error("Invalid native failed_levels record in force_study: expected { n: integer, reason: non-empty string }");
          }
        }
      }
      return {
        source_scope: "convergence_study",
        status: st,
        force_mesh_sensitivity_status: String(resp.force_mesh_sensitivity_status || st),
        study_n_list: nList,
        failed_levels: nativeFailed,
        rows: [],
        derived_sensitivity: null,
        native_v1_code: st,
        value: null
      };
    }

    if (st === "STABLE_WITHIN_STUDY_TOLERANCE" || st === "SENSITIVE_OR_UNBALANCED") {
      return {
        source_scope: "convergence_study",
        status: st,
        force_mesh_sensitivity_status: String(resp.force_mesh_sensitivity_status || st),
        study_n_list: nList,
        failed_levels: [],
        observed_order_status: String(fs.observed_order_status || "NOT_COMPUTED_NONUNIFORM_H_RATIO")
      };
    }

    throw new Error("Unsupported native force_study.status: " + st);
  }

  function makeRow(rowId, sourceScope, boundary, label, epistemicClass, quantity, direction, citation) {
    var xw = EPISTEMIC_CROSSWALK[epistemicClass];
    return {
      row_id: rowId,
      source_scope: sourceScope,
      boundary: boundary,
      component_label: label,
      epistemic_class: epistemicClass,
      charter_categories: xw ? xw.charter_categories.slice() : ["UNVERIFIED NUMERICAL OUTPUT"],
      quantity: quantity,
      qualitative_direction: direction,
      source_citation: citation
    };
  }

  function buildErrorQuantity(lastError) {
    var code = isPlainObject(lastError) && lastError.code ? String(lastError.code) : "SOLVER_ERROR";
    var msg = isPlainObject(lastError) && lastError.message ? String(lastError.message) : "Solver request failed.";
    var httpStatus = isPlainObject(lastError) && isStrictInteger(lastError.httpStatus) ? lastError.httpStatus : null;

    if (code === "INVALID_FORCE_DOMAIN") {
      return {
        status: "REJECTED_INVALID_FORCE_DOMAIN",
        value: null,
        http_status: 400,
        native_v1_code: "INVALID_FORCE_DOMAIN",
        diagnostic: msg
      };
    }
    return {
      status: "UNAVAILABLE_SOLVER_ERROR",
      value: null,
      http_status: httpStatus,
      native_v1_code: code,
      diagnostic: msg
    };
  }

  function buildClearedQuantity(reasonCode, note) {
    return {
      status: "CLEARED_PENDING_OR_INACTIVE",
      value: null,
      reason_code: reasonCode || "PENDING_OR_INVALIDATED",
      note: note || "Cleared pending a fresh verified solver response under the current state and transport epoch."
    };
  }

  function extractProvenance(resp) {
    var prov = isPlainObject(resp) && isPlainObject(resp.provenance) ? resp.provenance : {};
    var k = isPlainObject(prov.kernel_blob_sha1) ? prov.kernel_blob_sha1 : FROZEN_KERNEL_BLOB_SHA1;
    return {
      source_head_sha: typeof prov.source_head_sha === "string" ? prov.source_head_sha : null,
      kernel_blob_sha1: {
        electrostatics_baseline: String(k.electrostatics_baseline || FROZEN_KERNEL_BLOB_SHA1.electrostatics_baseline),
        electrostatics_numerics: String(k.electrostatics_numerics || FROZEN_KERNEL_BLOB_SHA1.electrostatics_numerics)
      }
    };
  }

  function build3DSchematicSnapshot(v1State) {
    var pendingP2 = function (note) {
      return {
        status: "PENDING_SCIENTIFIC_ACCEPTANCE",
        value: null,
        blocking_gate: "TRACK_B_P2",
        note: note
      };
    };
    var unknownUnmodeled = function (reason, note) {
      return {
        status: "UNKNOWN_UNMODELED",
        value: null,
        reason_code: reason,
        note: note
      };
    };

    var rows = [
      makeRow(
        "dut_active_electrode", "qualitative_3d_dut", "boundary_a_dut",
        "Active Blade Cathode (3D Schematic)", "UNVERIFIED_PENDING_P2",
        pendingP2("3D Exodus blade electrostatic traction awaits accepted Track B P2 solver baseline."),
        "+X (toward ground collector; schematic direction only)",
        "US11511891B2 FIGS. 4-8; docs/EXODUS_MODEL_CONTRACT.md"
      ),
      makeRow(
        "dut_counter_electrode", "qualitative_3d_dut", "boundary_a_dut",
        "Ground Counter-Electrode (3D Schematic)", "UNVERIFIED_PENDING_P2",
        pendingP2("3D Exodus ground counter-electrode reaction awaits accepted Track B P2 baseline."),
        "-X (opposing blade traction; schematic direction only)",
        "US11511891B2 FIGS. 4-8; docs/EXODUS_MODEL_CONTRACT.md"
      ),
      makeRow(
        "dut_dielectric_potting", "qualitative_3d_dut", "boundary_a_dut",
        "Dielectric Potting Block (Visual Proxy Only)", "UNVERIFIED_PENDING_P2",
        pendingP2("3D dielectric polarization stress awaits accepted Track B P2 baseline; sandbox epsilon_r slider is VISUAL PROXY ONLY."),
        "Internal polarization stress balancing electrodes",
        "US11511891B2 FIGS. 6B/21/23A; docs/SCIENCE_CHARTER.md"
      ),
      makeRow(
        "dut_support_mount", "qualitative_3d_dut", "boundary_a_dut",
        "Internal Support Mount", "PROVISIONAL_ILLUSTRATIVE_SCENE",
        unknownUnmodeled("STRUCTURAL_MOUNT_UNMODELED", "Mechanical standoffs and elastic load paths are not solved quantitatively."),
        "Internal structural equilibrium reaction",
        "Newton III (Lex III); docs/V2_FORCE_STORY_SPEC.md"
      ),
      makeRow(
        "boundary_a_dut_net_flux", "qualitative_3d_dut", "boundary_a_dut",
        "Boundary A DUT Net Electrostatic Flux", "UNVERIFIED_PENDING_P2",
        pendingP2("Closed-surface Boundary A flux for 3D Exodus DUT is unknown pending calibrated Track B P2 geometry."),
        "External wall-coupled flux only (NOT propellantless thrust)",
        "Griffiths §8.2.2; docs/V2_FORCE_STORY_SPEC.md §3.1"
      ),
      makeRow(
        "boundary_b_enclosure_reaction", "qualitative_3d_dut", "boundary_b_environment",
        "Boundary B Chamber / Enclosure Wall Reaction", "UNVERIFIED_PENDING_P2",
        pendingP2("3D chamber image-charge reaction awaits accepted Track B P2 boundary study."),
        "Opposes any unbalanced external electric flux from DUT",
        "Jackson Ch. 1; docs/V2_FORCE_STORY_SPEC.md §3.1"
      ),
      makeRow(
        "boundary_b_leads_and_gas", "qualitative_3d_dut", "boundary_b_environment",
        "Boundary B Power Leads & Ambient Gas / Ion Coupling", "CONDITIONAL_CONFOUNDER_MODEL",
        unknownUnmodeled("EXTERNAL_CONFOUNDERS_UNCALIBRATED", "Feedthrough forces, cable hysteresis, and ambient gas coupling depend on specific apparatus."),
        "Apparatus-dependent confounder path",
        "Tajmar & Schreiber (2020), J. Electrostat. 107, 103477"
      ),
      makeRow(
        "boundary_c_closure_residual", "qualitative_3d_dut", "boundary_c_closed",
        "Boundary C Closed-System Numerical Residual", "UNVERIFIED_PENDING_P2",
        pendingP2("No accepted 3D Exodus numerical solution exists yet under Track B P2."),
        "Continuum closed-system momentum conservation = 0",
        "docs/V2_FORCE_STORY_SPEC.md §3.1-3.2"
      )
    ];

    return {
      schema_version: SCHEMA_VERSION,
      comparison_surface: "qualitative_3d_dut_hypotheses",
      context_id: "schematic_3d_exodus",
      unit_domain: "NONE",
      transport_mode: "static_schematic",
      sync_identity: {
        client_state_generation: isPlainObject(v1State) && isStrictInteger(v1State.clientStateGeneration) ? v1State.clientStateGeneration : 0,
        transport_epoch: isPlainObject(v1State) && isStrictInteger(v1State.transportEpoch) ? v1State.transportEpoch : 0,
        response_origin_transport: null,
        input_fingerprint: null,
        request_id: null
      },
      convergence_study_provenance: null,
      whole_body_thrust_status: WHOLE_BODY_THRUST_STATUS,
      p2_scientific_status: P2_SCIENTIFIC_STATUS,
      provenance: extractProvenance(null),
      rows: rows
    };
  }

  function build1DSnapshot(v1State, syncCheck) {
    var transport = v1State.transportMode === "offline" ? "offline" : "live";
    var resp = syncCheck.ok ? v1State.lastRenderedResponse : null;
    var isErr = !syncCheck.ok && v1State.solveState === "error";

    function primaryQty(valN, note) {
      if (resp && isStrictFiniteNumber(valN)) {
        return {
          status: "COMPUTED_SCALAR_1D",
          value_n: valN,
          unit: "N",
          uncertainty: makeNullUncertainty("NOT_ASSESSED", note, "N")
        };
      }
      if (isErr) return buildErrorQuantity(v1State.lastError);
      return buildClearedQuantity(
        syncCheck.reasonCode,
        syncCheck.reasonCode === "TRANSPORT_EPOCH_MISMATCH"
          ? "Transport mode changed; previous 1D response cleared until verified under the new transport epoch."
          : "Awaiting verified 1D analytic P0 response."
      );
    }

    var rows = [
      makeRow(
        "dut_active_electrode", "primary_force_budget", "boundary_a_dut",
        "Positive Plate (+V)", "ESTABLISHED_MODEL",
        primaryQty(resp ? resp.force_on_positive_plate_n : null, "Analytic ideal infinite-plate limit (neglects edge fringing)."),
        "+X (toward negative plate)",
        "electrostatics_baseline.parallel_plate_benchmark (P0)"
      ),
      makeRow(
        "dut_counter_electrode", "primary_force_budget", "boundary_a_dut",
        "Negative Plate (0 V)", "ESTABLISHED_MODEL",
        primaryQty(resp ? resp.force_on_negative_plate_n : null, "Analytic ideal infinite-plate limit (neglects edge fringing)."),
        "-X (opposing positive plate)",
        "electrostatics_baseline.parallel_plate_benchmark (P0)"
      ),
      makeRow(
        "dut_dielectric_potting", "primary_force_budget", "boundary_a_dut",
        "Dielectric Potting", "ESTABLISHED_MODEL",
        { status: "NOT_APPLICABLE_VACUUM_MODEL", value: null, reason_code: "VACUUM_EPSILON_R_1", note: "1D P0 benchmark models vacuum (epsilon_r = 1.0) only." },
        "Not applicable in vacuum model",
        "docs/V2_FORCE_STORY_SPEC.md §3.2"
      ),
      makeRow(
        "dut_support_mount", "primary_force_budget", "boundary_a_dut",
        "Internal Support Mount", "ESTABLISHED_MODEL",
        { status: "UNKNOWN_UNMODELED", value: null, reason_code: "STRUCTURAL_STRUT_UNMODELED", note: "Equal and opposite mechanical strut load required to hold plate gap d is not explicitly solved." },
        "Opposes electrostatic attraction to hold gap d",
        "Newton III (Lex III); docs/V2_FORCE_STORY_SPEC.md §3.2"
      ),
      makeRow(
        "boundary_a_dut_net_flux", "primary_force_budget", "boundary_a_dut",
        "Boundary A DUT Net Pair Force", "ESTABLISHED_MODEL",
        primaryQty(resp ? resp.net_pair_force_n : null, "Exact analytic cancellation of ideal parallel plates (0.0 N)."),
        "Exact cancellation (0.0 N in ideal 1D limit)",
        "electrostatics_baseline.parallel_plate_benchmark (P0)"
      ),
      makeRow(
        "boundary_b_enclosure_reaction", "primary_force_budget", "boundary_b_environment",
        "Boundary B Enclosure / Wall Reaction", "ESTABLISHED_MODEL",
        { status: "NOT_APPLICABLE_OPEN_1D_LIMIT", value: null, reason_code: "OPEN_INFINITE_PLATE_LIMIT", note: "Ideal 1D parallel plates confine all flux between plates; no outer chamber wall exists." },
        "Not applicable in open 1D limit",
        "docs/V2_FORCE_STORY_SPEC.md §3.2"
      ),
      makeRow(
        "boundary_b_leads_and_gas", "primary_force_budget", "boundary_b_environment",
        "Boundary B Power Leads & Gas/Ion Coupling", "ESTABLISHED_MODEL",
        { status: "UNKNOWN_UNMODELED", value: null, reason_code: "LEADS_AND_GAS_UNMODELED", note: "External leads and ambient gas are excluded from ideal vacuum 1D model." },
        "Unmodeled external coupling",
        "docs/V2_FORCE_STORY_SPEC.md §3.2"
      ),
      makeRow(
        "boundary_c_closure_residual", "primary_force_budget", "boundary_c_closed",
        "Boundary C Closed-System Residual", "ESTABLISHED_MODEL",
        primaryQty(resp ? resp.net_pair_force_n : null, "Exact analytic closure (0.0 N)."),
        "Exact analytic cancellation",
        "electrostatics_baseline.parallel_plate_benchmark (P0)"
      )
    ];

    return {
      schema_version: SCHEMA_VERSION,
      comparison_surface: "quantitative_p0_p1_analogues",
      context_id: "parallel_plate_1d",
      unit_domain: "N",
      transport_mode: transport,
      sync_identity: {
        client_state_generation: isStrictInteger(v1State.clientStateGeneration) ? v1State.clientStateGeneration : 0,
        transport_epoch: isStrictInteger(v1State.transportEpoch) ? v1State.transportEpoch : 0,
        response_origin_transport: resp && v1State.lastRenderedOrigin ? v1State.lastRenderedOrigin.transportMode : null,
        input_fingerprint: resp ? resp.input_fingerprint : null,
        request_id: resp ? resp.request_id : null
      },
      convergence_study_provenance: null,
      whole_body_thrust_status: WHOLE_BODY_THRUST_STATUS,
      p2_scientific_status: P2_SCIENTIFIC_STATUS,
      provenance: extractProvenance(resp),
      rows: rows
    };
  }

  function build2DSnapshot(v1State, syncCheck) {
    var transport = v1State.transportMode === "offline" ? "offline" : "live";
    var resp = syncCheck.ok ? v1State.lastRenderedResponse : null;
    var isErr = !syncCheck.ok && v1State.solveState === "error";
    var fb = resp && isPlainObject(resp.force_budget) ? resp.force_budget : null;
    var fbStatus = resp ? String(resp.force_budget_status || "") : "";
    var fbDiag = resp && typeof resp.force_budget_diagnostic === "string" ? resp.force_budget_diagnostic : "";

    function primaryVectorQty(fx, fy, uncNote) {
      if (resp) {
        if (fbStatus === "COMPUTED" && fb && isStrictFiniteNumber(fx) && isStrictFiniteNumber(fy)) {
          return {
            status: "COMPUTED_VECTOR_2D",
            fx_n_per_m: fx,
            fy_n_per_m: fy,
            magnitude_n_per_m: Math.hypot(fx, fy),
            unit: "N/m",
            uncertainty: makeNullUncertainty("NUMERICAL_RESIDUAL_ONLY", uncNote, "N/m")
          };
        }
        if (fbStatus === "WITHHELD_INVALID_CONTOUR_TOPOLOGY") {
          return {
            status: "WITHHELD_INVALID_CONTOUR_TOPOLOGY",
            value: null,
            http_status: 200,
            native_v1_code: "WITHHELD_INVALID_CONTOUR_TOPOLOGY",
            diagnostic: fbDiag || "Post-solve snapped-contour topology gate failed; force budget withheld."
          };
        }
        if (fbStatus === "WITHHELD_INELIGIBLE_PRIMARY_GRID") {
          return {
            status: "WITHHELD_INELIGIBLE_PRIMARY_GRID",
            value: null,
            http_status: 200,
            native_v1_code: "WITHHELD_INELIGIBLE_PRIMARY_GRID",
            diagnostic: fbDiag || "Primary grid failed pre-solve domain eligibility; force budget withheld."
          };
        }
        return {
          status: "UNAVAILABLE_SOLVER_ERROR",
          value: null,
          http_status: 200,
          native_v1_code: fbStatus || "UNEXPECTED_FORCE_BUDGET_STATUS",
          diagnostic: fbDiag || "Primary force budget unavailable."
        };
      }
      if (isErr) return buildErrorQuantity(v1State.lastError);
      return buildClearedQuantity(
        syncCheck.reasonCode,
        syncCheck.reasonCode === "TRANSPORT_EPOCH_MISMATCH"
          ? "Transport mode changed; previous 2D ledger cleared until a verified response publishes under the new transport epoch."
          : "Awaiting verified 2D P0/P1 solver response."
      );
    }

    function primaryResidualQty() {
      if (resp) {
        if (
          fbStatus === "COMPUTED" &&
          fb &&
          isStrictFiniteNumber(fb.net_electrostatic_force_fx_n_per_m) &&
          isStrictFiniteNumber(fb.net_electrostatic_force_fy_n_per_m) &&
          isStrictFiniteNumber(fb.net_electrostatic_force_norm_n_per_m)
        ) {
          var norm = fb.net_electrostatic_force_norm_n_per_m;
          var balanced = norm < FORCE_BALANCE_TOLERANCE_N_PER_M;
          return {
            status: "COMPUTED_RESIDUAL_2D",
            net_fx_n_per_m: fb.net_electrostatic_force_fx_n_per_m,
            net_fy_n_per_m: fb.net_electrostatic_force_fy_n_per_m,
            norm_n_per_m: norm,
            relative_closure_residual: isStrictFiniteNumber(fb.relative_closure_residual) ? fb.relative_closure_residual : null,
            tolerance_n_per_m: FORCE_BALANCE_TOLERANCE_N_PER_M,
            is_force_balanced_to_tolerance: balanced,
            force_closure_status: balanced ? "BALANCED_WITHIN_TOLERANCE" : "UNBALANCED_EXCEEDS_TOLERANCE",
            unit: "N/m"
          };
        }
        return primaryVectorQty(null, null, "");
      }
      if (isErr) return buildErrorQuantity(v1State.lastError);
      return buildClearedQuantity(
        syncCheck.reasonCode,
        syncCheck.reasonCode === "TRANSPORT_EPOCH_MISMATCH"
          ? "Transport mode changed; previous 2D closure residual cleared."
          : "Awaiting verified 2D closure residual."
      );
    }

    var dutNetFx = fb && isStrictFiniteNumber(fb.left_electrode_fx_n_per_m) && isStrictFiniteNumber(fb.right_electrode_fx_n_per_m)
      ? fb.left_electrode_fx_n_per_m + fb.right_electrode_fx_n_per_m
      : null;
    var dutNetFy = fb && isStrictFiniteNumber(fb.left_electrode_fy_n_per_m) && isStrictFiniteNumber(fb.right_electrode_fy_n_per_m)
      ? fb.left_electrode_fy_n_per_m + fb.right_electrode_fy_n_per_m
      : null;

    var rows = [
      makeRow(
        "dut_active_electrode", "primary_force_budget", "boundary_a_dut",
        "Left Electrode (2D Cylinder)", "ESTABLISHED_MODEL",
        primaryVectorQty(fb ? fb.left_electrode_fx_n_per_m : null, fb ? fb.left_electrode_fy_n_per_m : null, "2D finite-difference O(h) staircase contour stress integral."),
        "Signed 2D vector (Fx, Fy) in N/m",
        "electrostatics_numerics.evaluate_whole_apparatus_force_budget (P1)"
      ),
      makeRow(
        "dut_counter_electrode", "primary_force_budget", "boundary_a_dut",
        "Right Electrode (2D Cylinder)", "ESTABLISHED_MODEL",
        primaryVectorQty(fb ? fb.right_electrode_fx_n_per_m : null, fb ? fb.right_electrode_fy_n_per_m : null, "2D finite-difference O(h) staircase contour stress integral."),
        "Signed 2D vector (Fx, Fy) in N/m",
        "electrostatics_numerics.evaluate_whole_apparatus_force_budget (P1)"
      ),
      makeRow(
        "dut_dielectric_potting", "primary_force_budget", "boundary_a_dut",
        "Dielectric Potting", "ESTABLISHED_MODEL",
        { status: "NOT_APPLICABLE_VACUUM_MODEL", value: null, reason_code: "VACUUM_EPSILON_R_1", note: "2D P0/P1 grounded-box solver models homogeneous vacuum (epsilon_r = 1.0) only." },
        "Not applicable in vacuum model",
        "docs/V2_FORCE_STORY_SPEC.md §3.2"
      ),
      makeRow(
        "dut_support_mount", "primary_force_budget", "boundary_a_dut",
        "Internal Support Mount", "ESTABLISHED_MODEL",
        { status: "UNKNOWN_UNMODELED", value: null, reason_code: "MECHANICAL_STANDOFFS_UNMODELED", note: "Mechanical standoffs holding electrode separation are outside the 2D Laplace model." },
        "Unmodeled structural constraint",
        "docs/V2_FORCE_STORY_SPEC.md §3.2"
      ),
      makeRow(
        "boundary_a_dut_net_flux", "primary_force_budget", "boundary_a_dut",
        "Boundary A DUT Net Electrostatic Flux (F_L + F_R — External Wall-Coupled Flux, NOT Isolated Thrust)", "ESTABLISHED_MODEL",
        primaryVectorQty(dutNetFx, dutNetFy, "Vector sum F_L + F_R equals external wall-coupled flux crossing Boundary A to grounded box."),
        "External wall-coupled DUT flux (N/m), NOT propellantless thrust",
        "electrostatics_numerics.evaluate_whole_apparatus_force_budget (P1)"
      ),
      makeRow(
        "boundary_b_enclosure_reaction", "primary_force_budget", "boundary_b_environment",
        "Boundary B Grounded Enclosure Reaction (F_enc)", "ESTABLISHED_MODEL",
        primaryVectorQty(fb ? fb.enclosure_reaction_fx_n_per_m : null, fb ? fb.enclosure_reaction_fy_n_per_m : null, "Inner-box contour integral capturing image-charge wall reaction."),
        "Opposes unbalanced DUT external flux (N/m)",
        "electrostatics_numerics.evaluate_whole_apparatus_force_budget (P1)"
      ),
      makeRow(
        "boundary_b_leads_and_gas", "primary_force_budget", "boundary_b_environment",
        "Boundary B Power Leads & Gas/Ion Coupling", "ESTABLISHED_MODEL",
        { status: "UNKNOWN_UNMODELED", value: null, reason_code: "LEADS_AND_GAS_UNMODELED", note: "Feedthroughs and gas ions are unmodeled in 2D vacuum Laplace benchmark." },
        "Unmodeled external coupling",
        "docs/V2_FORCE_STORY_SPEC.md §3.2"
      ),
      makeRow(
        "boundary_c_closure_residual", "primary_force_budget", "boundary_c_closed",
        "Boundary C Numerical Closure Residual (DISCRETIZATION RESIDUAL, NOT THRUST)", "ESTABLISHED_MODEL",
        primaryResidualQty(),
        "F_L + F_R + F_enc discretization residual (vanishes as h -> 0)",
        "electrostatics_numerics.evaluate_whole_apparatus_force_budget (P1)"
      )
    ];

    return {
      schema_version: SCHEMA_VERSION,
      comparison_surface: "quantitative_p0_p1_analogues",
      context_id: "grounded_box_2d",
      unit_domain: "N/m",
      transport_mode: transport,
      sync_identity: {
        client_state_generation: isStrictInteger(v1State.clientStateGeneration) ? v1State.clientStateGeneration : 0,
        transport_epoch: isStrictInteger(v1State.transportEpoch) ? v1State.transportEpoch : 0,
        response_origin_transport: resp && v1State.lastRenderedOrigin ? v1State.lastRenderedOrigin.transportMode : null,
        input_fingerprint: resp ? resp.input_fingerprint : null,
        request_id: resp ? resp.request_id : null
      },
      convergence_study_provenance: resp ? buildConvergenceStudyProvenance(resp) : null,
      whole_body_thrust_status: WHOLE_BODY_THRUST_STATUS,
      p2_scientific_status: P2_SCIENTIFIC_STATUS,
      provenance: extractProvenance(resp),
      rows: rows
    };
  }

  /**
   * V2-A-R1-M1: Compute exact snapped P1 Maxwell-stress integration contours (c_left, c_right, c_enclosure_inner)
   * matching frozen electrostatics_numerics.py (lines 292-304, 408-445) and v1_solver_adapter.py (lines 795-837).
   *
   * Returns null (suppressing any purported integration-path overlay) whenever the primary force budget is
   * withheld, unavailable, non-COMPUTED, or has invalid geometry parameters.
   */
  function computeExactP1IntegrationContours(resp) {
    if (!isPlainObject(resp)) return null;
    if (resp.force_budget_status !== "COMPUTED" || !isPlainObject(resp.force_budget)) {
      return null;
    }
    var p = resp.parameters;
    if (!isPlainObject(p)) return null;
    var le = p.left_electrode;
    var re = p.right_electrode;
    if (!isPlainObject(le) || !isPlainObject(re)) return null;

    var n = p.n;
    var w = p.box_width_m;
    if (!isStrictInteger(n) || n < 5) return null;
    if (!isStrictFiniteNumber(w) || w <= 0) return null;

    var lcx = le.center_x_m;
    var lcy = le.center_y_m;
    var lr = le.radius_m;
    var rcx = re.center_x_m;
    var rcy = re.center_y_m;
    var rr = re.radius_m;
    if (
      !isStrictFiniteNumber(lcx) || !isStrictFiniteNumber(lcy) || !isStrictFiniteNumber(lr) || lr <= 0 ||
      !isStrictFiniteNumber(rcx) || !isStrictFiniteNumber(rcy) || !isStrictFiniteNumber(rr) || rr <= 0
    ) {
      return null;
    }

    var h = (isPlainObject(resp.solution) && isStrictFiniteNumber(resp.solution.grid_spacing_m) && resp.solution.grid_spacing_m > 0)
      ? resp.solution.grid_spacing_m
      : (w / (n - 1));
    var wContour = (n - 1) * h;

    // Exact np.linspace(-wContour / 2.0, wContour / 2.0, n) lattice coordinates
    var coords = new Array(n);
    var start = -wContour / 2.0;
    var step = wContour / (n - 1);
    for (var i = 0; i < n; i++) {
      coords[i] = i === n - 1 ? (wContour / 2.0) : (start + i * step);
    }

    // Exact frozen P1 dynamic vacuum margins (electrostatics_numerics.py lines 414-424, 440)
    var sep = Math.abs(rcx - lcx);
    var dInter = sep - (lr + rr);
    var dLeftWall = (lcx - lr) - (-w / 2.0);
    var dRightWall = (w / 2.0) - (rcx + rr);
    var dVert = (w / 2.0) - Math.max(Math.abs(lcy) + lr, Math.abs(rcy) + rr);

    var marginX = Math.max(Math.min(dInter * 0.35, dLeftWall * 0.35, dRightWall * 0.35, 0.003), 1.5 * h);
    var marginY = Math.max(Math.min(dVert * 0.35, 0.003), 1.5 * h);
    var wallMargin = 2.5 * h;

    // Exact np.clip(np.argmin(np.abs(coords - target)), 1, n - 2) tie-breaking (lowest index wins on strict <)
    function snapIdx(target) {
      var bestIdx = 0;
      var bestDist = Math.abs(coords[0] - target);
      for (var k = 1; k < n; k++) {
        var d = Math.abs(coords[k] - target);
        if (d < bestDist) {
          bestDist = d;
          bestIdx = k;
        }
      }
      if (bestIdx < 1) return 1;
      if (bestIdx > n - 2) return n - 2;
      return bestIdx;
    }

    function snapRect(xLo, xHi, yLo, yHi) {
      var ixMin = snapIdx(xLo);
      var ixMax = snapIdx(xHi);
      var iyMin = snapIdx(yLo);
      var iyMax = snapIdx(yHi);
      if (ixMin >= ixMax || iyMin >= iyMax) return null;
      return {
        contour_indices: [ixMin, ixMax, iyMin, iyMax],
        contour_x_range_m: [coords[ixMin], coords[ixMax]],
        contour_y_range_m: [coords[iyMin], coords[iyMax]]
      };
    }

    var cLeft = snapRect(lcx - lr - marginX, lcx + lr + marginX, lcy - lr - marginY, lcy + lr + marginY);
    var cRight = snapRect(rcx - rr - marginX, rcx + rr + marginX, rcy - rr - marginY, rcy + rr + marginY);
    var cEnc = snapRect(-w / 2.0 + wallMargin, w / 2.0 - wallMargin, -w / 2.0 + wallMargin, w / 2.0 - wallMargin);

    if (!cLeft || !cRight || !cEnc) return null;

    return {
      n: n,
      box_width_m: w,
      grid_spacing_m: h,
      margin_x_m: marginX,
      margin_y_m: marginY,
      wall_margin_m: wallMargin,
      c_left: cLeft,
      c_right: cRight,
      c_enclosure_inner: cEnc
    };
  }

  /**
   * Build a schema-valid ForceLedgerSnapshot directly from window.__v1SolverUI.getState().
   */
  function buildForceLedgerSnapshot(v1State, lastRenderedV2Generation) {
    if (!isPlainObject(v1State)) {
      return build3DSchematicSnapshot(null);
    }

    if (v1State.activeViewContext === "scalar_wave_contrast") {
      var waveSnap = build3DSchematicSnapshot(v1State);
      waveSnap.rows = waveSnap.rows.map(function (r) {
        return makeRow(
          r.row_id,
          r.source_scope,
          r.boundary,
          r.component_label,
          "TOY_MATHEMATICAL_ILLUSTRATION",
          buildClearedQuantity("SCALAR_WAVE_CONTRAST_ACTIVE", "Chapter 5 mathematical scalar-wave toy view is isolated from electrostatic force ledgers."),
          "Isolated abstract scalar wave view",
          "docs/V2_FORCE_STORY_SPEC.md §6"
        );
      });
      return waveSnap;
    }

    if (v1State.activeModelMode === "parallel_plate_1d" && v1State.activeViewContext === "v1_1d") {
      return build1DSnapshot(v1State, evaluateV1SyncPredicates(v1State, lastRenderedV2Generation));
    }

    if (v1State.activeModelMode === "grounded_box_2d" && v1State.activeViewContext === "v1_2d") {
      return build2DSnapshot(v1State, evaluateV1SyncPredicates(v1State, lastRenderedV2Generation));
    }

    return build3DSchematicSnapshot(v1State);
  }

  var UNCERTAINTY_STATUSES = Object.freeze([
    "BOUNDED",
    "NUMERICAL_RESIDUAL_ONLY",
    "NOT_ASSESSED",
    "UNBOUNDED_UNKNOWN"
  ]);

  var UNIT_DOMAINS = Object.freeze(["N", "N/m", "NONE"]);
  var TRANSPORT_MODES = Object.freeze(["live", "offline", "static_schematic"]);
  var BOUNDARY_IDS = Object.freeze(["boundary_a_dut", "boundary_b_environment", "boundary_c_closed"]);

  function isNonEmptyString(v) {
    return typeof v === "string" && v.trim().length > 0;
  }

  /**
   * Exhaustive strict validator for nested NullableUncertainty (§7.3, V2-A-R1-M2).
   */
  function validateNullableUncertainty(unc, expectedUnit) {
    var errors = [];
    if (!isPlainObject(unc)) {
      return ["uncertainty must be a NullableUncertainty object."];
    }
    if (UNCERTAINTY_STATUSES.indexOf(unc.status) === -1) {
      errors.push("uncertainty.status invalid: " + String(unc.status));
    }
    if (UNIT_DOMAINS.indexOf(unc.unit) === -1) {
      errors.push("uncertainty.unit invalid: " + String(unc.unit));
    } else if (expectedUnit && unc.unit !== expectedUnit) {
      errors.push("uncertainty.unit '" + String(unc.unit) + "' must match row unit '" + String(expectedUnit) + "'.");
    }
    if (unc.status === "NOT_ASSESSED" || unc.status === "UNBOUNDED_UNKNOWN") {
      if (unc.value !== null) {
        errors.push("uncertainty.value must be null when uncertainty.status is " + String(unc.status) + " (never 0.0).");
      }
    } else if (unc.value !== null && (!isStrictFiniteNumber(unc.value) || unc.value < 0)) {
      errors.push("uncertainty.value must be null or a non-negative finite number.");
    }
    if (!isNonEmptyString(unc.note)) {
      errors.push("uncertainty.note must be a non-empty string.");
    }
    return errors;
  }

  /**
   * Exhaustive strict validator for LedgerRowValue discriminated union (§7.3, V2-A-R1-M2).
   */
  function validateLedgerRowValue(val, expectedUnitDomain, sourceScope) {
    var errors = [];
    if (!isPlainObject(val) || typeof val.status !== "string") {
      return ["LedgerRowValue must be an object with string status."];
    }

    var st = val.status;

    if (st === "COMPUTED_SCALAR_1D") {
      if (!isStrictFiniteNumber(val.value_n)) errors.push("COMPUTED_SCALAR_1D requires finite numeric value_n.");
      if (val.unit !== "N") errors.push("COMPUTED_SCALAR_1D requires unit === 'N'.");
      if (expectedUnitDomain && expectedUnitDomain !== "N") errors.push("Cross-unit violation: COMPUTED_SCALAR_1D not permitted in unit_domain " + expectedUnitDomain);
      if (Object.prototype.hasOwnProperty.call(val, "fx_n_per_m") || Object.prototype.hasOwnProperty.call(val, "fy_n_per_m")) {
        errors.push("COMPUTED_SCALAR_1D must not contain 2D vector fields.");
      }
      errors = errors.concat(validateNullableUncertainty(val.uncertainty, "N"));
      return errors;
    }

    if (st === "COMPUTED_VECTOR_2D") {
      if (Object.prototype.hasOwnProperty.call(val, "value") || Object.prototype.hasOwnProperty.call(val, "value_n")) {
        errors.push("COMPUTED_VECTOR_2D must not coerce 2D signed vectors into scalar value/value_n.");
      }
      var fxOk = isStrictFiniteNumber(val.fx_n_per_m);
      var fyOk = isStrictFiniteNumber(val.fy_n_per_m);
      var magOk = isStrictFiniteNumber(val.magnitude_n_per_m) && val.magnitude_n_per_m >= 0;
      if (!fxOk) errors.push("COMPUTED_VECTOR_2D requires finite signed fx_n_per_m.");
      if (!fyOk) errors.push("COMPUTED_VECTOR_2D requires finite signed fy_n_per_m.");
      if (!magOk) {
        errors.push("COMPUTED_VECTOR_2D requires non-negative finite magnitude_n_per_m.");
      } else if (fxOk && fyOk) {
        var expectedMag = Math.hypot(val.fx_n_per_m, val.fy_n_per_m);
        var magTol = Math.max(1e-12, 1e-9 * Math.max(expectedMag, val.magnitude_n_per_m));
        if (Math.abs(val.magnitude_n_per_m - expectedMag) > magTol) {
          errors.push("COMPUTED_VECTOR_2D magnitude_n_per_m (" + String(val.magnitude_n_per_m) + ") inconsistent with hypot(fx, fy) (" + String(expectedMag) + ").");
        }
      }
      if (val.unit !== "N/m") errors.push("COMPUTED_VECTOR_2D requires unit === 'N/m'.");
      if (expectedUnitDomain && expectedUnitDomain !== "N/m") errors.push("Cross-unit violation: COMPUTED_VECTOR_2D not permitted in unit_domain " + expectedUnitDomain);
      errors = errors.concat(validateNullableUncertainty(val.uncertainty, "N/m"));
      return errors;
    }

    if (st === "COMPUTED_RESIDUAL_2D") {
      var nfxOk = isStrictFiniteNumber(val.net_fx_n_per_m);
      var nfyOk = isStrictFiniteNumber(val.net_fy_n_per_m);
      var normOk = isStrictFiniteNumber(val.norm_n_per_m) && val.norm_n_per_m >= 0;
      if (!nfxOk || !nfyOk) {
        errors.push("COMPUTED_RESIDUAL_2D requires finite net_fx_n_per_m and net_fy_n_per_m.");
      }
      if (!normOk) {
        errors.push("COMPUTED_RESIDUAL_2D requires non-negative finite norm_n_per_m.");
      } else if (nfxOk && nfyOk) {
        var expectedNorm = Math.hypot(val.net_fx_n_per_m, val.net_fy_n_per_m);
        var normTol = Math.max(1e-12, 1e-9 * Math.max(expectedNorm, val.norm_n_per_m));
        if (Math.abs(val.norm_n_per_m - expectedNorm) > normTol) {
          errors.push("COMPUTED_RESIDUAL_2D norm_n_per_m (" + String(val.norm_n_per_m) + ") inconsistent with hypot(net_fx, net_fy) (" + String(expectedNorm) + ").");
        }
      }
      if (val.relative_closure_residual !== null && (!isStrictFiniteNumber(val.relative_closure_residual) || val.relative_closure_residual < 0)) {
        errors.push("COMPUTED_RESIDUAL_2D relative_closure_residual must be non-negative finite number or null.");
      }
      if (val.tolerance_n_per_m !== FORCE_BALANCE_TOLERANCE_N_PER_M) {
        errors.push("COMPUTED_RESIDUAL_2D requires tolerance_n_per_m === 1e-4.");
      }
      if (typeof val.is_force_balanced_to_tolerance !== "boolean") {
        errors.push("COMPUTED_RESIDUAL_2D requires boolean is_force_balanced_to_tolerance.");
      } else if (normOk) {
        var expectedBalanced = val.norm_n_per_m < FORCE_BALANCE_TOLERANCE_N_PER_M;
        if (val.is_force_balanced_to_tolerance !== expectedBalanced) {
          errors.push("COMPUTED_RESIDUAL_2D is_force_balanced_to_tolerance must follow strict norm < 1e-4.");
        }
        var expectedStatus = expectedBalanced ? "BALANCED_WITHIN_TOLERANCE" : "UNBALANCED_EXCEEDS_TOLERANCE";
        if (val.force_closure_status !== expectedStatus) {
          errors.push("COMPUTED_RESIDUAL_2D force_closure_status mismatch.");
        }
      }
      if (val.unit !== "N/m") errors.push("COMPUTED_RESIDUAL_2D requires unit === 'N/m'.");
      if (expectedUnitDomain && expectedUnitDomain !== "N/m") errors.push("Cross-unit violation: COMPUTED_RESIDUAL_2D not permitted in unit_domain " + expectedUnitDomain);
      return errors;
    }

    if (st === "CONDITIONAL_ESTIMATE") {
      if (!isStrictFiniteNumber(val.value_n)) errors.push("CONDITIONAL_ESTIMATE requires finite numeric value_n.");
      if (val.unit !== "N") errors.push("CONDITIONAL_ESTIMATE requires unit === 'N'.");
      if (expectedUnitDomain && expectedUnitDomain !== "N") {
        errors.push("Cross-unit violation: CONDITIONAL_ESTIMATE (unit 'N') not permitted in unit_domain " + expectedUnitDomain);
      }
      if (!isNonEmptyString(val.validity_regime)) errors.push("CONDITIONAL_ESTIMATE requires non-empty validity_regime.");
      if (!Array.isArray(val.assumptions) || val.assumptions.length === 0 || !val.assumptions.every(isNonEmptyString)) {
        errors.push("CONDITIONAL_ESTIMATE requires non-empty string[] assumptions.");
      }
      if (!Array.isArray(val.what_if_parameters) || val.what_if_parameters.length === 0 || !val.what_if_parameters.every(isNonEmptyString)) {
        errors.push("CONDITIONAL_ESTIMATE requires non-empty string[] what_if_parameters (Charter WHAT-IF PARAMETER disclosure).");
      }
      return errors;
    }

    if (st === "WITHHELD_INVALID_CONTOUR_TOPOLOGY") {
      if (val.value !== null) errors.push("WITHHELD_INVALID_CONTOUR_TOPOLOGY must have value === null (NEVER 0.0).");
      if (val.http_status !== 200) errors.push("WITHHELD_INVALID_CONTOUR_TOPOLOGY requires http_status === 200.");
      if (val.native_v1_code !== "WITHHELD_INVALID_CONTOUR_TOPOLOGY") errors.push("native_v1_code must equal WITHHELD_INVALID_CONTOUR_TOPOLOGY.");
      if (!isNonEmptyString(val.diagnostic)) errors.push("WITHHELD_INVALID_CONTOUR_TOPOLOGY requires non-empty string diagnostic.");
      return errors;
    }

    if (st === "REJECTED_INVALID_FORCE_DOMAIN") {
      if (val.value !== null) errors.push("REJECTED_INVALID_FORCE_DOMAIN must have value === null (NEVER 0.0).");
      if (val.http_status !== 400) errors.push("REJECTED_INVALID_FORCE_DOMAIN requires http_status === 400.");
      if (val.native_v1_code !== "INVALID_FORCE_DOMAIN") errors.push("native_v1_code must equal INVALID_FORCE_DOMAIN.");
      if (!isNonEmptyString(val.diagnostic)) errors.push("REJECTED_INVALID_FORCE_DOMAIN requires non-empty string diagnostic.");
      return errors;
    }

    if (st === "WITHHELD_INELIGIBLE_PRIMARY_GRID") {
      if (val.value !== null) errors.push("WITHHELD_INELIGIBLE_PRIMARY_GRID must have value === null (NEVER 0.0).");
      if (val.http_status !== 200) errors.push("WITHHELD_INELIGIBLE_PRIMARY_GRID requires http_status === 200.");
      if (val.native_v1_code !== "WITHHELD_INELIGIBLE_PRIMARY_GRID") errors.push("native_v1_code must equal WITHHELD_INELIGIBLE_PRIMARY_GRID.");
      if (!isNonEmptyString(val.diagnostic)) errors.push("WITHHELD_INELIGIBLE_PRIMARY_GRID requires non-empty string diagnostic.");
      return errors;
    }

    if (st === "WITHHELD_INELIGIBLE_MESH_LEVEL") {
      if (sourceScope && sourceScope !== "convergence_study") {
        errors.push("WITHHELD_INELIGIBLE_MESH_LEVEL is permitted ONLY when source_scope === 'convergence_study'.");
      }
      if (val.value !== null) errors.push("WITHHELD_INELIGIBLE_MESH_LEVEL must have value === null (NEVER 0.0).");
      if (val.http_status !== 200) errors.push("WITHHELD_INELIGIBLE_MESH_LEVEL requires http_status === 200.");
      if (val.native_v1_code !== "WITHHELD_INELIGIBLE_MESH_LEVEL") errors.push("native_v1_code must equal WITHHELD_INELIGIBLE_MESH_LEVEL.");
      if (!isNonEmptyString(val.diagnostic)) errors.push("WITHHELD_INELIGIBLE_MESH_LEVEL requires non-empty string diagnostic.");
      if (!Array.isArray(val.failed_levels) || val.failed_levels.length === 0) {
        errors.push("WITHHELD_INELIGIBLE_MESH_LEVEL requires non-empty failed_levels: StudyFailedLevelRecord[].");
      } else {
        for (var i = 0; i < val.failed_levels.length; i++) {
          var fl = val.failed_levels[i];
          if (!isPlainObject(fl) || !isStrictInteger(fl.n) || fl.n < 3 || !isNonEmptyString(fl.reason)) {
            errors.push("failed_levels[" + i + "] must be lossless { n: integer >= 3, reason: non-empty string } (never number-only array).");
          }
        }
      }
      return errors;
    }

    if (st === "UNAVAILABLE_SOLVER_ERROR") {
      if (val.value !== null) errors.push("UNAVAILABLE_SOLVER_ERROR must have value === null (NEVER 0.0).");
      if (val.http_status !== null && !isStrictInteger(val.http_status)) errors.push("http_status must be integer or null.");
      if (!isNonEmptyString(val.native_v1_code)) errors.push("UNAVAILABLE_SOLVER_ERROR requires non-empty native_v1_code.");
      if (!isNonEmptyString(val.diagnostic)) errors.push("UNAVAILABLE_SOLVER_ERROR requires non-empty diagnostic.");
      return errors;
    }

    if (st === "PENDING_SCIENTIFIC_ACCEPTANCE") {
      if (val.value !== null) errors.push("PENDING_SCIENTIFIC_ACCEPTANCE must have value === null (NEVER 0.0).");
      if (val.blocking_gate !== "TRACK_B_P2") errors.push("PENDING_SCIENTIFIC_ACCEPTANCE requires blocking_gate === 'TRACK_B_P2'.");
      if (!isNonEmptyString(val.note)) errors.push("PENDING_SCIENTIFIC_ACCEPTANCE requires non-empty note.");
      return errors;
    }

    if (NULL_VALUE_STATUSES.indexOf(st) !== -1) {
      if (val.value !== null) errors.push(st + " must have value === null (NEVER 0.0).");
      if (!isNonEmptyString(val.reason_code)) errors.push(st + " requires non-empty reason_code.");
      if (!isNonEmptyString(val.note)) errors.push(st + " requires non-empty note.");
      return errors;
    }

    return ["Unknown LedgerRowValue status: " + st];
  }

  function validateStudyNList(list, label) {
    var errs = [];
    if (!Array.isArray(list) || list.length === 0) {
      return [label + " requires non-empty integer[] study_n_list."];
    }
    for (var i = 0; i < list.length; i++) {
      if (!isStrictInteger(list[i]) || list[i] < 3) {
        errs.push(label + " study_n_list[" + i + "] must be an integer >= 3 (got " + JSON.stringify(list[i]) + ").");
      }
    }
    return errs;
  }

  /**
   * Exhaustive strict validator for ConvergenceStudyStatusRecord (§7.3, V2-SPEC-R3-M1, V2-A-R1-M2).
   */
  function validateConvergenceStudyRecord(rec) {
    var errors = [];
    if (rec === null) return errors;
    if (!isPlainObject(rec)) return ["convergence_study_provenance must be object or null."];
    if (rec.source_scope !== "convergence_study") errors.push("convergence_study_provenance requires source_scope === 'convergence_study'.");

    if (rec.status === "NOT_REQUESTED") {
      if (rec.force_mesh_sensitivity_status !== "NOT_ASSESSED") errors.push("NOT_REQUESTED requires force_mesh_sensitivity_status === 'NOT_ASSESSED'.");
      if (rec.study_n_list !== null) errors.push("NOT_REQUESTED requires study_n_list === null.");
      if (!Array.isArray(rec.failed_levels) || rec.failed_levels.length !== 0) errors.push("NOT_REQUESTED requires failed_levels === [].");
      if (!Array.isArray(rec.rows) || rec.rows.length !== 0) errors.push("NOT_REQUESTED requires rows === [].");
      if (rec.derived_sensitivity !== null) errors.push("NOT_REQUESTED requires derived_sensitivity === null.");
      if (rec.value !== null) errors.push("NOT_REQUESTED requires value === null.");
      return errors;
    }

    if (rec.status === "STABLE_WITHIN_STUDY_TOLERANCE" || rec.status === "SENSITIVE_OR_UNBALANCED") {
      if (rec.force_mesh_sensitivity_status !== rec.status) errors.push("Computed study force_mesh_sensitivity_status must match status.");
      errors = errors.concat(validateStudyNList(rec.study_n_list, "Computed study"));
      if (!Array.isArray(rec.failed_levels) || rec.failed_levels.length !== 0) errors.push("Computed study requires failed_levels === [].");
      if (!isNonEmptyString(rec.observed_order_status)) errors.push("Computed study requires non-empty observed_order_status.");
      return errors;
    }

    if (rec.status === "WITHHELD_INELIGIBLE_MESH_LEVEL" || rec.status === "WITHHELD_INVALID_CONTOUR_TOPOLOGY") {
      if (rec.force_mesh_sensitivity_status !== rec.status) errors.push("Withheld study force_mesh_sensitivity_status must match status.");
      if (rec.native_v1_code !== rec.status) errors.push("Withheld study native_v1_code must match status.");
      errors = errors.concat(validateStudyNList(rec.study_n_list, "Withheld study"));
      if (!Array.isArray(rec.rows) || rec.rows.length !== 0) errors.push("Withheld study MUST have empty rows: [] (never synthesize study rows).");
      if (rec.derived_sensitivity !== null) errors.push("Withheld study MUST have derived_sensitivity === null.");
      if (rec.value !== null) errors.push("Withheld study MUST have value === null (NEVER 0.0).");
      if (!Array.isArray(rec.failed_levels) || rec.failed_levels.length === 0) {
        errors.push("Withheld study requires non-empty native failed_levels: StudyFailedLevelRecord[].");
      } else {
        for (var i = 0; i < rec.failed_levels.length; i++) {
          var fl = rec.failed_levels[i];
          if (!isPlainObject(fl) || !isStrictInteger(fl.n) || fl.n < 3 || !isNonEmptyString(fl.reason)) {
            errors.push("Withheld study failed_levels[" + i + "] must be lossless { n: integer >= 3, reason: non-empty string } (rejects number-only arrays).");
          }
        }
      }
      return errors;
    }

    return ["Unknown ConvergenceStudyStatusRecord status: " + String(rec.status)];
  }

  function hasExactCharterCrosswalk(epistemicClass, charterCategories) {
    var entry = EPISTEMIC_CROSSWALK[epistemicClass];
    if (!entry || !Array.isArray(charterCategories)) return false;
    var expected = entry.charter_categories;
    if (charterCategories.length !== expected.length) return false;
    for (var i = 0; i < expected.length; i++) {
      if (charterCategories.indexOf(expected[i]) === -1) return false;
    }
    // Reject duplicates as well
    for (var j = 0; j < charterCategories.length; j++) {
      if (charterCategories.indexOf(charterCategories[j]) !== j) return false;
    }
    return true;
  }

  /**
   * Exhaustive strict validator for ForceLedgerSnapshot (§7.3, V2-A-R1-M2).
   */
  function validateForceLedgerSnapshot(snap) {
    var errors = [];
    if (!isPlainObject(snap)) return ["ForceLedgerSnapshot must be an object."];
    if (snap.schema_version !== SCHEMA_VERSION) errors.push("schema_version must equal 'v2.0'.");
    if (snap.whole_body_thrust_status !== WHOLE_BODY_THRUST_STATUS) {
      errors.push("whole_body_thrust_status must equal 'NOT MEASURED / NOT ESTABLISHED'.");
    }
    if (snap.p2_scientific_status !== P2_SCIENTIFIC_STATUS) {
      errors.push("p2_scientific_status must equal 'PENDING_SCIENTIFIC_ACCEPTANCE'.");
    }

    var expectedUnitByContext = {
      parallel_plate_1d: "N",
      grounded_box_2d: "N/m",
      schematic_3d_exodus: "NONE"
    };
    var expectedUnit = expectedUnitByContext[snap.context_id];
    if (!expectedUnit) {
      errors.push("Invalid context_id: " + String(snap.context_id));
    } else if (snap.unit_domain !== expectedUnit) {
      errors.push("unit_domain " + String(snap.unit_domain) + " does not match context_id " + String(snap.context_id) + " (expected " + expectedUnit + ").");
    }

    if (TRANSPORT_MODES.indexOf(snap.transport_mode) === -1) {
      errors.push("Invalid transport_mode: " + String(snap.transport_mode));
    } else {
      if (snap.context_id === "schematic_3d_exodus" && snap.transport_mode !== "static_schematic") {
        errors.push("schematic_3d_exodus requires transport_mode === 'static_schematic'.");
      }
      if ((snap.context_id === "parallel_plate_1d" || snap.context_id === "grounded_box_2d") && snap.transport_mode === "static_schematic") {
        errors.push("1D/2D contexts require transport_mode 'live' or 'offline' (not 'static_schematic').");
      }
    }

    if (snap.context_id === "schematic_3d_exodus" && snap.comparison_surface !== "qualitative_3d_dut_hypotheses") {
      errors.push("schematic_3d_exodus must use comparison_surface 'qualitative_3d_dut_hypotheses'.");
    }
    if ((snap.context_id === "parallel_plate_1d" || snap.context_id === "grounded_box_2d") && snap.comparison_surface !== "quantitative_p0_p1_analogues") {
      errors.push("1D/2D contexts must use comparison_surface 'quantitative_p0_p1_analogues'.");
    }

    if (!isPlainObject(snap.sync_identity)) {
      errors.push("sync_identity is required.");
    } else {
      if (!isStrictInteger(snap.sync_identity.client_state_generation) || snap.sync_identity.client_state_generation < 0) {
        errors.push("sync_identity.client_state_generation must be non-negative integer.");
      }
      if (!isStrictInteger(snap.sync_identity.transport_epoch) || snap.sync_identity.transport_epoch < 0) {
        errors.push("sync_identity.transport_epoch must be non-negative integer.");
      }
      var origT = snap.sync_identity.response_origin_transport;
      if (origT !== null && origT !== "live" && origT !== "offline") {
        errors.push("sync_identity.response_origin_transport must be 'live', 'offline', or null.");
      }
      var fp = snap.sync_identity.input_fingerprint;
      if (fp !== null && !isNonEmptyString(fp)) {
        errors.push("sync_identity.input_fingerprint must be non-empty string or null.");
      }
      var reqId = snap.sync_identity.request_id;
      if (reqId !== null && (!isStrictInteger(reqId) || reqId < 0)) {
        errors.push("sync_identity.request_id must be non-negative integer or null.");
      }
    }

    if (!isPlainObject(snap.provenance)) {
      errors.push("provenance object is required.");
    } else {
      if (snap.provenance.source_head_sha !== null && !isNonEmptyString(snap.provenance.source_head_sha)) {
        errors.push("provenance.source_head_sha must be non-empty string or null.");
      }
      if (!isPlainObject(snap.provenance.kernel_blob_sha1)) {
        errors.push("provenance.kernel_blob_sha1 object is required.");
      } else {
        if (snap.provenance.kernel_blob_sha1.electrostatics_baseline !== FROZEN_KERNEL_BLOB_SHA1.electrostatics_baseline) {
          errors.push("provenance.kernel_blob_sha1.electrostatics_baseline does not match frozen P0 SHA-1.");
        }
        if (snap.provenance.kernel_blob_sha1.electrostatics_numerics !== FROZEN_KERNEL_BLOB_SHA1.electrostatics_numerics) {
          errors.push("provenance.kernel_blob_sha1.electrostatics_numerics does not match frozen P1 SHA-1.");
        }
      }
    }

    errors = errors.concat(validateConvergenceStudyRecord(snap.convergence_study_provenance));

    if (!Array.isArray(snap.rows) || snap.rows.length === 0) {
      errors.push("rows must be a non-empty array.");
      return errors;
    }

    var hasComputedRow = false;
    for (var i = 0; i < snap.rows.length; i++) {
      var r = snap.rows[i];
      if (!isPlainObject(r)) {
        errors.push("rows[" + i + "] must be an object.");
        continue;
      }
      if (!isNonEmptyString(r.row_id)) errors.push("rows[" + i + "] requires non-empty row_id.");
      if (!isNonEmptyString(r.component_label)) errors.push("rows[" + i + "] requires non-empty component_label.");
      if (!isNonEmptyString(r.qualitative_direction)) errors.push("rows[" + i + "] requires non-empty qualitative_direction.");
      if (!isNonEmptyString(r.source_citation)) errors.push("rows[" + i + "] requires non-empty source_citation.");
      if (BOUNDARY_IDS.indexOf(r.boundary) === -1) {
        errors.push("rows[" + i + "] invalid boundary: " + String(r.boundary));
      }
      if (SOURCE_SCOPES.indexOf(r.source_scope) === -1) {
        errors.push("rows[" + i + "] invalid source_scope: " + String(r.source_scope));
      }
      if (EPISTEMIC_CLASSES.indexOf(r.epistemic_class) === -1) {
        errors.push("rows[" + i + "] invalid epistemic_class: " + String(r.epistemic_class));
      } else if (!hasExactCharterCrosswalk(r.epistemic_class, r.charter_categories)) {
        errors.push(
          "rows[" + i + "] charter_categories " + JSON.stringify(r.charter_categories) +
          " does not match exact Scientific Charter crosswalk for epistemic_class " + String(r.epistemic_class) +
          " (expected " + JSON.stringify(EPISTEMIC_CROSSWALK[r.epistemic_class].charter_categories) + ")."
        );
      }

      var qErrs = validateLedgerRowValue(r.quantity, expectedUnit, r.source_scope);
      for (var qe = 0; qe < qErrs.length; qe++) {
        errors.push("rows[" + i + "] (" + String(r.row_id) + "): " + qErrs[qe]);
      }
      if (isPlainObject(r.quantity) && r.quantity.status === "CONDITIONAL_ESTIMATE") {
        if (!Array.isArray(r.charter_categories) || r.charter_categories.indexOf("WHAT-IF PARAMETER") === -1) {
          errors.push("rows[" + i + "] CONDITIONAL_ESTIMATE requires 'WHAT-IF PARAMETER' in charter_categories.");
        }
      }
      if (
        isPlainObject(r.quantity) &&
        (r.quantity.status === "COMPUTED_SCALAR_1D" ||
          r.quantity.status === "COMPUTED_VECTOR_2D" ||
          r.quantity.status === "COMPUTED_RESIDUAL_2D")
      ) {
        hasComputedRow = true;
      }
    }

    if (hasComputedRow && isPlainObject(snap.sync_identity)) {
      if (snap.sync_identity.response_origin_transport !== snap.transport_mode) {
        errors.push("Computed snapshot sync_identity.response_origin_transport must match transport_mode (V2-SPEC-R2-M1).");
      }
      if (!isNonEmptyString(snap.sync_identity.input_fingerprint)) {
        errors.push("Computed snapshot requires non-empty sync_identity.input_fingerprint.");
      }
      if (!isStrictInteger(snap.sync_identity.request_id) || snap.sync_identity.request_id < 0) {
        errors.push("Computed snapshot requires non-negative integer sync_identity.request_id.");
      }
    }

    return errors;
  }

  return Object.freeze({
    SCHEMA_VERSION: SCHEMA_VERSION,
    WHOLE_BODY_THRUST_STATUS: WHOLE_BODY_THRUST_STATUS,
    P2_SCIENTIFIC_STATUS: P2_SCIENTIFIC_STATUS,
    FORCE_BALANCE_TOLERANCE_N_PER_M: FORCE_BALANCE_TOLERANCE_N_PER_M,
    FROZEN_KERNEL_BLOB_SHA1: FROZEN_KERNEL_BLOB_SHA1,
    FROZEN_SPEC_BLOB_SHA1: FROZEN_SPEC_BLOB_SHA1,
    EPISTEMIC_CLASSES: EPISTEMIC_CLASSES,
    CHARTER_CATEGORIES: CHARTER_CATEGORIES,
    EPISTEMIC_CROSSWALK: EPISTEMIC_CROSSWALK,
    SOURCE_SCOPES: SOURCE_SCOPES,
    BOUNDARY_DEFINITIONS: BOUNDARY_DEFINITIONS,
    H1_CONTESTED_DERIVATION_AUDIT: H1_CONTESTED_DERIVATION_AUDIT,
    SURFACE_A_QUALITATIVE_3D_DUT: SURFACE_A_QUALITATIVE_3D_DUT,
    SURFACE_B_QUANTITATIVE_ANALOGUES: SURFACE_B_QUANTITATIVE_ANALOGUES,
    evaluateV1SyncPredicates: evaluateV1SyncPredicates,
    computeExactP1IntegrationContours: computeExactP1IntegrationContours,
    buildConvergenceStudyProvenance: buildConvergenceStudyProvenance,
    buildForceLedgerSnapshot: buildForceLedgerSnapshot,
    validateNullableUncertainty: validateNullableUncertainty,
    validateLedgerRowValue: validateLedgerRowValue,
    validateConvergenceStudyRecord: validateConvergenceStudyRecord,
    validateForceLedgerSnapshot: validateForceLedgerSnapshot
  });
});
