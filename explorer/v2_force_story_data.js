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

  /**
   * Exhaustive strict validator for LedgerRowValue discriminated union (§7.3).
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
      if (!isPlainObject(val.uncertainty)) errors.push("COMPUTED_SCALAR_1D requires uncertainty object.");
      return errors;
    }

    if (st === "COMPUTED_VECTOR_2D") {
      if (Object.prototype.hasOwnProperty.call(val, "value") || Object.prototype.hasOwnProperty.call(val, "value_n")) {
        errors.push("COMPUTED_VECTOR_2D must not coerce 2D signed vectors into scalar value/value_n.");
      }
      if (!isStrictFiniteNumber(val.fx_n_per_m)) errors.push("COMPUTED_VECTOR_2D requires finite signed fx_n_per_m.");
      if (!isStrictFiniteNumber(val.fy_n_per_m)) errors.push("COMPUTED_VECTOR_2D requires finite signed fy_n_per_m.");
      if (!isStrictFiniteNumber(val.magnitude_n_per_m) || val.magnitude_n_per_m < 0) {
        errors.push("COMPUTED_VECTOR_2D requires non-negative finite magnitude_n_per_m.");
      }
      if (val.unit !== "N/m") errors.push("COMPUTED_VECTOR_2D requires unit === 'N/m'.");
      if (expectedUnitDomain && expectedUnitDomain !== "N/m") errors.push("Cross-unit violation: COMPUTED_VECTOR_2D not permitted in unit_domain " + expectedUnitDomain);
      if (!isPlainObject(val.uncertainty)) errors.push("COMPUTED_VECTOR_2D requires uncertainty object.");
      return errors;
    }

    if (st === "COMPUTED_RESIDUAL_2D") {
      if (!isStrictFiniteNumber(val.net_fx_n_per_m) || !isStrictFiniteNumber(val.net_fy_n_per_m)) {
        errors.push("COMPUTED_RESIDUAL_2D requires finite net_fx_n_per_m and net_fy_n_per_m.");
      }
      if (!isStrictFiniteNumber(val.norm_n_per_m) || val.norm_n_per_m < 0) {
        errors.push("COMPUTED_RESIDUAL_2D requires non-negative finite norm_n_per_m.");
      }
      if (val.relative_closure_residual !== null && !isStrictFiniteNumber(val.relative_closure_residual)) {
        errors.push("COMPUTED_RESIDUAL_2D relative_closure_residual must be finite number or null.");
      }
      if (val.tolerance_n_per_m !== FORCE_BALANCE_TOLERANCE_N_PER_M) {
        errors.push("COMPUTED_RESIDUAL_2D requires tolerance_n_per_m === 1e-4.");
      }
      if (typeof val.is_force_balanced_to_tolerance !== "boolean") {
        errors.push("COMPUTED_RESIDUAL_2D requires boolean is_force_balanced_to_tolerance.");
      } else {
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
      if (typeof val.validity_regime !== "string" || !val.validity_regime) errors.push("CONDITIONAL_ESTIMATE requires validity_regime.");
      if (!Array.isArray(val.assumptions) || val.assumptions.length === 0) errors.push("CONDITIONAL_ESTIMATE requires non-empty assumptions.");
      if (!Array.isArray(val.what_if_parameters) || val.what_if_parameters.length === 0) {
        errors.push("CONDITIONAL_ESTIMATE requires non-empty what_if_parameters (Charter WHAT-IF PARAMETER disclosure).");
      }
      return errors;
    }

    if (st === "WITHHELD_INVALID_CONTOUR_TOPOLOGY") {
      if (val.value !== null) errors.push("WITHHELD_INVALID_CONTOUR_TOPOLOGY must have value === null (NEVER 0.0).");
      if (val.http_status !== 200) errors.push("WITHHELD_INVALID_CONTOUR_TOPOLOGY requires http_status === 200.");
      if (val.native_v1_code !== "WITHHELD_INVALID_CONTOUR_TOPOLOGY") errors.push("native_v1_code must equal WITHHELD_INVALID_CONTOUR_TOPOLOGY.");
      if (typeof val.diagnostic !== "string") errors.push("WITHHELD_INVALID_CONTOUR_TOPOLOGY requires string diagnostic.");
      return errors;
    }

    if (st === "REJECTED_INVALID_FORCE_DOMAIN") {
      if (val.value !== null) errors.push("REJECTED_INVALID_FORCE_DOMAIN must have value === null (NEVER 0.0).");
      if (val.http_status !== 400) errors.push("REJECTED_INVALID_FORCE_DOMAIN requires http_status === 400.");
      if (val.native_v1_code !== "INVALID_FORCE_DOMAIN") errors.push("native_v1_code must equal INVALID_FORCE_DOMAIN.");
      if (typeof val.diagnostic !== "string") errors.push("REJECTED_INVALID_FORCE_DOMAIN requires string diagnostic.");
      return errors;
    }

    if (st === "WITHHELD_INELIGIBLE_PRIMARY_GRID") {
      if (val.value !== null) errors.push("WITHHELD_INELIGIBLE_PRIMARY_GRID must have value === null (NEVER 0.0).");
      if (val.http_status !== 200) errors.push("WITHHELD_INELIGIBLE_PRIMARY_GRID requires http_status === 200.");
      if (val.native_v1_code !== "WITHHELD_INELIGIBLE_PRIMARY_GRID") errors.push("native_v1_code must equal WITHHELD_INELIGIBLE_PRIMARY_GRID.");
      if (typeof val.diagnostic !== "string") errors.push("WITHHELD_INELIGIBLE_PRIMARY_GRID requires string diagnostic.");
      return errors;
    }

    if (st === "WITHHELD_INELIGIBLE_MESH_LEVEL") {
      if (sourceScope && sourceScope !== "convergence_study") {
        errors.push("WITHHELD_INELIGIBLE_MESH_LEVEL is permitted ONLY when source_scope === 'convergence_study'.");
      }
      if (val.value !== null) errors.push("WITHHELD_INELIGIBLE_MESH_LEVEL must have value === null (NEVER 0.0).");
      if (val.http_status !== 200) errors.push("WITHHELD_INELIGIBLE_MESH_LEVEL requires http_status === 200.");
      if (val.native_v1_code !== "WITHHELD_INELIGIBLE_MESH_LEVEL") errors.push("native_v1_code must equal WITHHELD_INELIGIBLE_MESH_LEVEL.");
      if (!Array.isArray(val.failed_levels) || val.failed_levels.length === 0) {
        errors.push("WITHHELD_INELIGIBLE_MESH_LEVEL requires non-empty failed_levels: StudyFailedLevelRecord[].");
      } else {
        for (var i = 0; i < val.failed_levels.length; i++) {
          var fl = val.failed_levels[i];
          if (!isPlainObject(fl) || !isStrictInteger(fl.n) || typeof fl.reason !== "string" || fl.reason.length === 0) {
            errors.push("failed_levels[" + i + "] must be lossless { n: integer, reason: non-empty string } (never number-only array).");
          }
        }
      }
      return errors;
    }

    if (st === "UNAVAILABLE_SOLVER_ERROR") {
      if (val.value !== null) errors.push("UNAVAILABLE_SOLVER_ERROR must have value === null (NEVER 0.0).");
      if (val.http_status !== null && !isStrictInteger(val.http_status)) errors.push("http_status must be integer or null.");
      if (typeof val.native_v1_code !== "string" || !val.native_v1_code) errors.push("UNAVAILABLE_SOLVER_ERROR requires non-empty native_v1_code.");
      return errors;
    }

    if (st === "PENDING_SCIENTIFIC_ACCEPTANCE") {
      if (val.value !== null) errors.push("PENDING_SCIENTIFIC_ACCEPTANCE must have value === null (NEVER 0.0).");
      if (val.blocking_gate !== "TRACK_B_P2") errors.push("PENDING_SCIENTIFIC_ACCEPTANCE requires blocking_gate === 'TRACK_B_P2'.");
      if (typeof val.note !== "string" || !val.note) errors.push("PENDING_SCIENTIFIC_ACCEPTANCE requires note.");
      return errors;
    }

    if (NULL_VALUE_STATUSES.indexOf(st) !== -1) {
      if (val.value !== null) errors.push(st + " must have value === null (NEVER 0.0).");
      if (typeof val.reason_code !== "string" || !val.reason_code) errors.push(st + " requires non-empty reason_code.");
      if (typeof val.note !== "string" || !val.note) errors.push(st + " requires non-empty note.");
      return errors;
    }

    return ["Unknown LedgerRowValue status: " + st];
  }

  /**
   * Exhaustive strict validator for ConvergenceStudyStatusRecord (§7.3, V2-SPEC-R3-M1).
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
      if (!Array.isArray(rec.study_n_list) || rec.study_n_list.length === 0) errors.push("Computed study requires non-empty study_n_list.");
      if (!Array.isArray(rec.failed_levels) || rec.failed_levels.length !== 0) errors.push("Computed study requires failed_levels === [].");
      if (typeof rec.observed_order_status !== "string" || !rec.observed_order_status) errors.push("Computed study requires observed_order_status.");
      return errors;
    }

    if (rec.status === "WITHHELD_INELIGIBLE_MESH_LEVEL" || rec.status === "WITHHELD_INVALID_CONTOUR_TOPOLOGY") {
      if (rec.force_mesh_sensitivity_status !== rec.status) errors.push("Withheld study force_mesh_sensitivity_status must match status.");
      if (rec.native_v1_code !== rec.status) errors.push("Withheld study native_v1_code must match status.");
      if (!Array.isArray(rec.study_n_list) || rec.study_n_list.length === 0) errors.push("Withheld study requires study_n_list.");
      if (!Array.isArray(rec.rows) || rec.rows.length !== 0) errors.push("Withheld study MUST have empty rows: [] (never synthesize study rows).");
      if (rec.derived_sensitivity !== null) errors.push("Withheld study MUST have derived_sensitivity === null.");
      if (rec.value !== null) errors.push("Withheld study MUST have value === null (NEVER 0.0).");
      if (!Array.isArray(rec.failed_levels) || rec.failed_levels.length === 0) {
        errors.push("Withheld study requires non-empty native failed_levels: StudyFailedLevelRecord[].");
      } else {
        for (var i = 0; i < rec.failed_levels.length; i++) {
          var fl = rec.failed_levels[i];
          if (!isPlainObject(fl) || !isStrictInteger(fl.n) || typeof fl.reason !== "string" || fl.reason.length === 0) {
            errors.push("Withheld study failed_levels[" + i + "] must be lossless { n: integer, reason: non-empty string } (rejects number-only arrays).");
          }
        }
      }
      return errors;
    }

    return ["Unknown ConvergenceStudyStatusRecord status: " + String(rec.status)];
  }

  /**
   * Exhaustive strict validator for ForceLedgerSnapshot (§7.3).
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

    if (snap.context_id === "schematic_3d_exodus" && snap.comparison_surface !== "qualitative_3d_dut_hypotheses") {
      errors.push("schematic_3d_exodus must use comparison_surface 'qualitative_3d_dut_hypotheses'.");
    }
    if ((snap.context_id === "parallel_plate_1d" || snap.context_id === "grounded_box_2d") && snap.comparison_surface !== "quantitative_p0_p1_analogues") {
      errors.push("1D/2D contexts must use comparison_surface 'quantitative_p0_p1_analogues'.");
    }

    if (!isPlainObject(snap.sync_identity)) {
      errors.push("sync_identity is required.");
    } else {
      if (!isStrictInteger(snap.sync_identity.client_state_generation)) errors.push("sync_identity.client_state_generation must be integer.");
      if (!isStrictInteger(snap.sync_identity.transport_epoch)) errors.push("sync_identity.transport_epoch must be integer.");
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
      if (SOURCE_SCOPES.indexOf(r.source_scope) === -1) {
        errors.push("rows[" + i + "] invalid source_scope: " + String(r.source_scope));
      }
      if (EPISTEMIC_CLASSES.indexOf(r.epistemic_class) === -1) {
        errors.push("rows[" + i + "] invalid epistemic_class: " + String(r.epistemic_class));
      }
      if (!Array.isArray(r.charter_categories) || r.charter_categories.length === 0) {
        errors.push("rows[" + i + "] requires non-empty charter_categories.");
      } else {
        for (var c = 0; c < r.charter_categories.length; c++) {
          if (CHARTER_CATEGORIES.indexOf(r.charter_categories[c]) === -1) {
            errors.push("rows[" + i + "] invalid Charter category: " + String(r.charter_categories[c]));
          }
        }
      }

      var qErrs = validateLedgerRowValue(r.quantity, expectedUnit, r.source_scope);
      for (var qe = 0; qe < qErrs.length; qe++) {
        errors.push("rows[" + i + "] (" + String(r.row_id) + "): " + qErrs[qe]);
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
    buildConvergenceStudyProvenance: buildConvergenceStudyProvenance,
    buildForceLedgerSnapshot: buildForceLedgerSnapshot,
    validateLedgerRowValue: validateLedgerRowValue,
    validateConvergenceStudyRecord: validateConvergenceStudyRecord,
    validateForceLedgerSnapshot: validateForceLedgerSnapshot
  });
});
