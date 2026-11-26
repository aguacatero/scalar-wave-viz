"""Contract & cross-language (Python + Node/JS) unit tests for Slice V2-A (Whole-Device Force Story).

Verifies frozen V2 Design Specification R4 (docs/V2_FORCE_STORY_SPEC.md, blob 7d4b66be574b937f3750d135f351d3b1e6e3f142):
- Cross-geometry non-conflation (V2-SPEC-R1-M1): Surface A vs Surface B separation, 3D PENDING_SCIENTIFIC_ACCEPTANCE.
- Exhaustive discriminated LedgerRowValue schema & rejection tests (V2-SPEC-R1-M2): signed 2D (Fx, Fy) vectors,
  no scalar coercion, no 0.0 coercion on null-value statuses, no cross-unit N vs N/m mixing, lossless native V1 codes.
- Simultaneous COMPUTED primary force budget + WITHHELD_INELIGIBLE_MESH_LEVEL study provenance using an ACTUAL
  adapter-generated HTTP-200 /api/v1/study payload preserving native { n, reason }[] verbatim (V2-SPEC-R2-L1, R3-M1).
- 8-predicate V1 -> V2 atomic sync & transport-epoch validation (V2-SPEC-R1-M3, V2-SPEC-R2-M1).
- 7-class <-> 5-category Scientific Charter crosswalk (V2-SPEC-R1-L1).
- Cryptographic frozen baseline SHA-1 verification and zero Track B P2 leakage.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import electrostatics_baseline as eb  # noqa: E402
import electrostatics_numerics as en  # noqa: E402
import v1_solver_adapter as adapter  # noqa: E402

EXPLORER_DIR = REPO_ROOT / "explorer"
V2_DATA_JS = EXPLORER_DIR / "v2_force_story_data.js"
V2_UI_JS = EXPLORER_DIR / "v2_force_story_ui.js"
INDEX_HTML = EXPLORER_DIR / "index.html"

EXPECTED_FROZEN_BLOBS = {
    "electrostatics_baseline.py": "97f65dfa25db7730323edd5e52c98b17371fdeaa",
    "electrostatics_numerics.py": "a29f1f3a55946f33760179677dd3dbeb6a2ebde2",
    "docs/V1_SOLVER_INTEGRATION_SPEC.md": "3ccf8ae0e8caa4d367d93eddd173dda98a13f00a",
    "docs/V2_FORCE_STORY_SPEC.md": "7d4b66be574b937f3750d135f351d3b1e6e3f142",
}


def git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("utf-8")
    return hashlib.sha1(header + data).hexdigest()


def run_node_v2(js_body: str, payload: dict | None = None) -> dict:
    node_bin = shutil.which("node")
    if not node_bin:
        raise unittest.SkipTest("Node.js runtime not available")
    wrapper = (
        f"const D = require({json.dumps(str(V2_DATA_JS))});\n"
        "const input = JSON.parse(require('fs').readFileSync(0, 'utf8') || '{}');\n"
        "const result = (() => {\n"
        + js_body
        + "\n})();\n"
        "process.stdout.write(JSON.stringify(result));\n"
    )
    proc = subprocess.run(
        [node_bin, "-e", wrapper],
        input=json.dumps(payload or {}),
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(f"Node script failed (rc={proc.returncode}): {proc.stderr}")
    return json.loads(proc.stdout)


class V2ForceStoryContractTests(unittest.TestCase):
    """Contract, schema-rejection, adapter-provenance, and isolation tests for Slice V2-A."""

    def test_frozen_baseline_blobs_and_zero_p2_leakage(self):
        """Frozen P0/P1 kernels, accepted V1 Spec R5, and accepted V2 Spec R4 must be byte-for-byte unchanged."""
        for rel_path, expected_sha in EXPECTED_FROZEN_BLOBS.items():
            actual = git_blob_sha1(REPO_ROOT / rel_path)
            self.assertEqual(actual, expected_sha, f"Frozen blob mismatch for {rel_path}")

        forbidden_p2_tokens = (
            "exodus_hypothesis_evaluator",
            "exodus_patent_geometry",
            "p2_exodus",
            "p2_geometry",
            "p2_solver",
        )
        for src_path in (V2_DATA_JS, V2_UI_JS):
            txt = src_path.read_text(encoding="utf-8")
            for tok in forbidden_p2_tokens:
                self.assertNotIn(tok, txt, f"Forbidden Track B P2 reference '{tok}' found in {src_path.name}")

        # Zero raw LaTeX delimiters in V2 data/UI/HTML
        raw_latex_pat = re.compile(r"\\(?:frac|nabla|varepsilon|propto|oint|partial)\b")
        for path in (V2_DATA_JS, V2_UI_JS, INDEX_HTML):
            text = path.read_text(encoding="utf-8")
            self.assertIsNone(raw_latex_pat.search(text), f"Raw LaTeX delimiter leaked into {path.name}")

    def test_cross_geometry_non_conflation_and_charter_crosswalk(self):
        """V2-SPEC-R1-M1 & L1: Surface A/B separation, 3D P2 pending slots, and 7-to-5 Charter crosswalk."""
        res = run_node_v2(
            """
            const surfA = D.SURFACE_A_QUALITATIVE_3D_DUT;
            const surfB = D.SURFACE_B_QUANTITATIVE_ANALOGUES;
            const snap3d = D.buildForceLedgerSnapshot({
              activeModelMode: 'schematic_3d',
              activeViewContext: '3d_schematic',
              transportMode: 'live',
              transportEpoch: 0,
              solveState: 'idle',
              clientStateGeneration: 1,
              lastRenderedResponse: null,
              lastRenderedOrigin: null,
              lastError: null
            }, 0);
            const snap3dErrs = D.validateForceLedgerSnapshot(snap3d);

            // Reject schematic_3d_exodus masquerading as quantitative_p0_p1_analogues
            const badSurfaceSnap = JSON.parse(JSON.stringify(snap3d));
            badSurfaceSnap.comparison_surface = 'quantitative_p0_p1_analogues';
            const badSurfaceErrs = D.validateForceLedgerSnapshot(badSurfaceSnap);

            // Charter crosswalk completeness
            const covered = new Set();
            const cwIssues = [];
            for (const cls of D.EPISTEMIC_CLASSES) {
              const entry = D.EPISTEMIC_CROSSWALK[cls];
              if (!entry || !Array.isArray(entry.charter_categories) || entry.charter_categories.length === 0) {
                cwIssues.push('Missing crosswalk for ' + cls);
                continue;
              }
              for (const cat of entry.charter_categories) {
                if (!D.CHARTER_CATEGORIES.includes(cat)) cwIssues.push('Unknown category ' + cat);
                covered.add(cat);
              }
            }

            // CONDITIONAL_ESTIMATE without what_if_parameters must be rejected
            const condMissingWhatIf = D.validateLedgerRowValue({
              status: 'CONDITIONAL_ESTIMATE',
              value_n: 5e-3,
              unit: 'N',
              validity_regime: 'atmospheric_1atm_collisional',
              assumptions: ['1 atm collisional air'],
              what_if_parameters: []
            }, 'N', 'comparator_estimate');

            return {
              surfA,
              surfB,
              snap3d,
              snap3dErrs,
              badSurfaceErrs,
              covered: Array.from(covered),
              allCharter: Array.from(D.CHARTER_CATEGORIES),
              cwIssues,
              condMissingWhatIf,
              audit: D.H1_CONTESTED_DERIVATION_AUDIT
            };
            """
        )

        self.assertEqual(res["snap3dErrs"], [])
        self.assertGreater(len(res["badSurfaceErrs"]), 0)
        self.assertEqual(res["cwIssues"], [])
        self.assertEqual(set(res["covered"]), set(res["allCharter"]))
        self.assertGreater(len(res["condMissingWhatIf"]), 0)

        # Surface A must have zero 1D N / 2D N/m numerical benchmark strings
        surf_a_json = json.dumps(res["surfA"])
        self.assertIn("QUALITATIVE 3D EXODUS COMPARISON", res["surfA"]["banner"])
        self.assertIn("SEPARATE IDEALIZED P0/P1 BENCHMARK ANALOGUE", res["surfB"]["banner"])
        self.assertNotIn("N/m", surf_a_json)
        self.assertIsNone(re.search(r"[+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?\s*N(?:/m)?\b", surf_a_json))
        self.assertNotIn("8.38e-2", surf_a_json)

        # H0 and H1 3D slots must be PENDING_SCIENTIFIC_ACCEPTANCE
        hyps = {h["id"]: h for h in res["surfA"]["hypotheses"]}
        self.assertEqual(hyps["H0"]["quantitative_3d_status"], "PENDING_SCIENTIFIC_ACCEPTANCE")
        self.assertEqual(hyps["H1"]["quantitative_3d_status"], "PENDING_SCIENTIFIC_ACCEPTANCE")

        # Eq. (4) & Eq. (11) audit ledger present
        refs = [a["equation_ref"] for a in res["audit"]]
        self.assertIn("US11511891B2 Eq. (4)", refs)
        self.assertIn("US11511891B2 Eq. (11)", refs)

        # 3D snapshot must have NONE unit domain, zero computed rows, and invariant thrust disclaimer
        self.assertEqual(res["snap3d"]["unit_domain"], "NONE")
        self.assertEqual(res["snap3d"]["whole_body_thrust_status"], "NOT MEASURED / NOT ESTABLISHED")
        self.assertEqual(res["snap3d"]["p2_scientific_status"], "PENDING_SCIENTIFIC_ACCEPTANCE")
        for row in res["snap3d"]["rows"]:
            self.assertNotIn(row["quantity"]["status"], ("COMPUTED_SCALAR_1D", "COMPUTED_VECTOR_2D", "COMPUTED_RESIDUAL_2D"))
            self.assertIsNone(row["quantity"]["value"])

    def test_typed_schema_rejection_matrix(self):
        """V2-SPEC-R1-M2 & R3-M1: Reject scalar coercion, 0.0 coercion of nulls, cross-unit mixing, and lossy failed_levels."""
        res = run_node_v2(
            """
            const checks = {};

            // 1. Scalar-only value on 2D vector row rejected
            checks.scalarOn2D = D.validateLedgerRowValue({
              status: 'COMPUTED_VECTOR_2D',
              value: 0.05,
              fx_n_per_m: 0.05,
              fy_n_per_m: 0.0,
              magnitude_n_per_m: 0.05,
              unit: 'N/m',
              uncertainty: { status: 'NUMERICAL_RESIDUAL_ONLY', value: null, unit: 'N/m', note: 'test' }
            }, 'N/m', 'primary_force_budget');

            // 2. Omitting signed fy_n_per_m rejected
            checks.missingFy = D.validateLedgerRowValue({
              status: 'COMPUTED_VECTOR_2D',
              fx_n_per_m: 0.05,
              magnitude_n_per_m: 0.05,
              unit: 'N/m',
              uncertainty: { status: 'NUMERICAL_RESIDUAL_ONLY', value: null, unit: 'N/m', note: 'test' }
            }, 'N/m', 'primary_force_budget');

            // 3. Cross-unit (1D scalar in N/m context & 2D vector in N context) rejected
            checks.crossUnit1Din2D = D.validateLedgerRowValue({
              status: 'COMPUTED_SCALAR_1D',
              value_n: 1.0,
              unit: 'N',
              uncertainty: { status: 'NOT_ASSESSED', value: null, unit: 'N', note: 'test' }
            }, 'N/m', 'primary_force_budget');

            checks.crossUnit2Din1D = D.validateLedgerRowValue({
              status: 'COMPUTED_VECTOR_2D',
              fx_n_per_m: 1.0,
              fy_n_per_m: 0.0,
              magnitude_n_per_m: 1.0,
              unit: 'N/m',
              uncertainty: { status: 'NUMERICAL_RESIDUAL_ONLY', value: null, unit: 'N/m', note: 'test' }
            }, 'N', 'primary_force_budget');

            // 4. Numeric 0.0 on EVERY null-value status MUST be rejected
            const nullZeroRejections = {};
            const nullStatuses = [
              { status: 'UNKNOWN_UNMODELED', value: 0.0, reason_code: 'R', note: 'N' },
              { status: 'OUT_OF_MODEL_VALIDITY_REGIME', value: 0.0, reason_code: 'R', note: 'N' },
              { status: 'INVALID_COMPARATOR_INPUT', value: 0.0, reason_code: 'R', note: 'N' },
              { status: 'NOT_APPLICABLE_VACUUM_MODEL', value: 0.0, reason_code: 'R', note: 'N' },
              { status: 'NOT_APPLICABLE_OPEN_1D_LIMIT', value: 0.0, reason_code: 'R', note: 'N' },
              { status: 'CLEARED_PENDING_OR_INACTIVE', value: 0.0, reason_code: 'R', note: 'N' },
              { status: 'NOT_RUN_SWEEP_TERMINATED', value: 0.0, reason_code: 'R', note: 'N' },
              { status: 'PENDING_SCIENTIFIC_ACCEPTANCE', value: 0.0, blocking_gate: 'TRACK_B_P2', note: 'N' },
              { status: 'WITHHELD_INVALID_CONTOUR_TOPOLOGY', value: 0.0, http_status: 200, native_v1_code: 'WITHHELD_INVALID_CONTOUR_TOPOLOGY', diagnostic: 'D' },
              { status: 'WITHHELD_INELIGIBLE_PRIMARY_GRID', value: 0.0, http_status: 200, native_v1_code: 'WITHHELD_INELIGIBLE_PRIMARY_GRID', diagnostic: 'D' },
              { status: 'WITHHELD_INELIGIBLE_MESH_LEVEL', value: 0.0, http_status: 200, native_v1_code: 'WITHHELD_INELIGIBLE_MESH_LEVEL', failed_levels: [{ n: 41, reason: 'r' }], diagnostic: 'D' },
              { status: 'REJECTED_INVALID_FORCE_DOMAIN', value: 0.0, http_status: 400, native_v1_code: 'INVALID_FORCE_DOMAIN', diagnostic: 'D' },
              { status: 'UNAVAILABLE_SOLVER_ERROR', value: 0.0, http_status: 500, native_v1_code: 'HTTP_500', diagnostic: 'D' }
            ];
            for (const item of nullStatuses) {
              const scope = item.status === 'WITHHELD_INELIGIBLE_MESH_LEVEL' ? 'convergence_study' : 'primary_force_budget';
              nullZeroRejections[item.status] = D.validateLedgerRowValue(item, 'N/m', scope);
            }
            checks.nullZeroRejections = nullZeroRejections;

            // 5. WITHHELD_INELIGIBLE_MESH_LEVEL on primary_force_budget MUST be rejected
            checks.studyStatusOnPrimary = D.validateLedgerRowValue({
              status: 'WITHHELD_INELIGIBLE_MESH_LEVEL',
              value: null,
              http_status: 200,
              native_v1_code: 'WITHHELD_INELIGIBLE_MESH_LEVEL',
              failed_levels: [{ n: 41, reason: 'too coarse' }],
              diagnostic: 'D'
            }, 'N/m', 'primary_force_budget');

            // 6. Lossy failed_levels: [41] number-only array MUST be rejected on BOTH row and study record
            checks.lossyNumberArrayRow = D.validateLedgerRowValue({
              status: 'WITHHELD_INELIGIBLE_MESH_LEVEL',
              value: null,
              http_status: 200,
              native_v1_code: 'WITHHELD_INELIGIBLE_MESH_LEVEL',
              failed_levels: [41],
              diagnostic: 'D'
            }, 'N/m', 'convergence_study');

            checks.lossyNumberArrayStudy = D.validateConvergenceStudyRecord({
              source_scope: 'convergence_study',
              status: 'WITHHELD_INELIGIBLE_MESH_LEVEL',
              force_mesh_sensitivity_status: 'WITHHELD_INELIGIBLE_MESH_LEVEL',
              study_n_list: [41, 81, 101],
              failed_levels: [41],
              rows: [],
              derived_sensitivity: null,
              native_v1_code: 'WITHHELD_INELIGIBLE_MESH_LEVEL',
              value: null
            });

            // 7. Fabricated study rows or 0.0 placeholder on withheld study MUST be rejected
            checks.fabricatedStudyRows = D.validateConvergenceStudyRecord({
              source_scope: 'convergence_study',
              status: 'WITHHELD_INELIGIBLE_MESH_LEVEL',
              force_mesh_sensitivity_status: 'WITHHELD_INELIGIBLE_MESH_LEVEL',
              study_n_list: [41, 81, 101],
              failed_levels: [{ n: 41, reason: 'r < 3h' }],
              rows: [{ n: 41, left_electrode_fx_n_per_m: 0.0 }],
              derived_sensitivity: null,
              native_v1_code: 'WITHHELD_INELIGIBLE_MESH_LEVEL',
              value: null
            });

            checks.zeroPlaceholderStudy = D.validateConvergenceStudyRecord({
              source_scope: 'convergence_study',
              status: 'WITHHELD_INELIGIBLE_MESH_LEVEL',
              force_mesh_sensitivity_status: 'WITHHELD_INELIGIBLE_MESH_LEVEL',
              study_n_list: [41, 81, 101],
              failed_levels: [{ n: 41, reason: 'r < 3h' }],
              rows: [],
              derived_sensitivity: null,
              native_v1_code: 'WITHHELD_INELIGIBLE_MESH_LEVEL',
              value: 0.0
            });

            return checks;
            """
        )

        self.assertGreater(len(res["scalarOn2D"]), 0)
        self.assertGreater(len(res["missingFy"]), 0)
        self.assertGreater(len(res["crossUnit1Din2D"]), 0)
        self.assertGreater(len(res["crossUnit2Din1D"]), 0)
        self.assertGreater(len(res["studyStatusOnPrimary"]), 0)
        self.assertGreater(len(res["lossyNumberArrayRow"]), 0)
        self.assertGreater(len(res["lossyNumberArrayStudy"]), 0)
        self.assertGreater(len(res["fabricatedStudyRows"]), 0)
        self.assertGreater(len(res["zeroPlaceholderStudy"]), 0)
        for st_name, errs in res["nullZeroRejections"].items():
            self.assertGreater(len(errs), 0, f"Status {st_name} failed to reject value: 0.0")

    def test_real_adapter_simultaneous_computed_primary_and_withheld_study_provenance(self):
        """V2-SPEC-R2-L1 & R3-M1: Actual HTTP-200 /api/v1/study payload preserves primary N/m vectors & verbatim { n, reason }."""
        req = {
            "request_id": 19,
            "mode": "grounded_box_2d",
            "parameters": {
                "n": 101,
                "box_width_m": 0.160,
                "left_electrode": {"center_x_m": -0.015, "center_y_m": 0.0, "radius_m": 0.007, "voltage_v": -20000.0},
                "right_electrode": {"center_x_m": 0.015, "center_y_m": 0.0, "radius_m": 0.007, "voltage_v": 0.0},
            },
            "probe_xy_m": [0.0, 0.0],
            "study_n_list": [41, 81, 101],
        }
        norm = adapter.validate_and_normalize_request("/api/v1/study", req)
        http_status, real_resp = adapter.solve_normalized_request(norm)

        self.assertEqual(http_status, 200)
        self.assertEqual(real_resp["force_budget_status"], "COMPUTED")
        self.assertEqual(real_resp["force_study"]["status"], "WITHHELD_INELIGIBLE_MESH_LEVEL")
        self.assertIsInstance(real_resp["force_study"]["failed_levels"], list)
        self.assertEqual(len(real_resp["force_study"]["failed_levels"]), 1)
        expected_failed = real_resp["force_study"]["failed_levels"][0]
        self.assertEqual(expected_failed["n"], 41)
        self.assertIn("< 3h", expected_failed["reason"])

        # Strip large solution matrices for snappy JSON stdin handoff while keeping every force/study/provenance field verbatim
        trimmed_resp = {k: v for k, v in real_resp.items() if k != "solution"}
        res = run_node_v2(
            """
            const resp = input.resp;
            const v1State = {
              activeModelMode: 'grounded_box_2d',
              activeViewContext: 'v1_2d',
              activeEndpoint: '/api/v1/study',
              transportMode: 'live',
              transportEpoch: 2,
              solveState: 'ready',
              clientStateGeneration: 5,
              currentCanonicalFingerprint: resp.input_fingerprint,
              latestDispatchedRequestId: resp.request_id,
              isComputed2DActive: true,
              lastRenderedResponse: resp,
              lastRenderedOrigin: { transportMode: 'live', transportEpoch: 2 },
              lastError: null
            };
            const snap = D.buildForceLedgerSnapshot(v1State, 4);
            const errs = D.validateForceLedgerSnapshot(snap);

            // Also test WITHHELD_INVALID_CONTOUR_TOPOLOGY study record preservation
            const topoResp = JSON.parse(JSON.stringify(resp));
            topoResp.force_mesh_sensitivity_status = 'WITHHELD_INVALID_CONTOUR_TOPOLOGY';
            topoResp.force_study = {
              status: 'WITHHELD_INVALID_CONTOUR_TOPOLOGY',
              study_n_list: [41, 81, 101],
              failed_levels: [{ n: 41, reason: 'Snapped contour intersected conductor mask at n=41' }],
              rows: [],
              derived_sensitivity: null
            };
            const topoState = Object.assign({}, v1State, { lastRenderedResponse: topoResp });
            const topoSnap = D.buildForceLedgerSnapshot(topoState, 4);
            const topoErrs = D.validateForceLedgerSnapshot(topoSnap);

            return { snap, errs, topoSnap, topoErrs };
            """,
            {"resp": trimmed_resp},
        )

        self.assertEqual(res["errs"], [])
        self.assertEqual(res["topoErrs"], [])
        snap = res["snap"]
        fb = real_resp["force_budget"]

        # Primary rows preserved untouched under source_scope === "primary_force_budget"
        rows_by_id = {r["row_id"]: r for r in snap["rows"]}
        self.assertEqual(rows_by_id["dut_active_electrode"]["source_scope"], "primary_force_budget")
        self.assertEqual(rows_by_id["dut_active_electrode"]["quantity"]["status"], "COMPUTED_VECTOR_2D")
        self.assertAlmostEqual(rows_by_id["dut_active_electrode"]["quantity"]["fx_n_per_m"], fb["left_electrode_fx_n_per_m"], places=12)
        self.assertAlmostEqual(rows_by_id["dut_active_electrode"]["quantity"]["fy_n_per_m"], fb["left_electrode_fy_n_per_m"], places=12)
        self.assertEqual(rows_by_id["boundary_b_enclosure_reaction"]["quantity"]["status"], "COMPUTED_VECTOR_2D")
        self.assertAlmostEqual(rows_by_id["boundary_b_enclosure_reaction"]["quantity"]["fx_n_per_m"], fb["enclosure_reaction_fx_n_per_m"], places=12)
        self.assertEqual(rows_by_id["boundary_c_closure_residual"]["quantity"]["status"], "COMPUTED_RESIDUAL_2D")
        self.assertEqual(rows_by_id["boundary_c_closure_residual"]["quantity"]["force_closure_status"], "BALANCED_WITHIN_TOLERANCE")

        # Independent study record preserves native { n, reason } verbatim with zero fabricated study rows or 0.0
        sp = snap["convergence_study_provenance"]
        self.assertEqual(sp["source_scope"], "convergence_study")
        self.assertEqual(sp["status"], "WITHHELD_INELIGIBLE_MESH_LEVEL")
        self.assertEqual(sp["native_v1_code"], "WITHHELD_INELIGIBLE_MESH_LEVEL")
        self.assertEqual(sp["rows"], [])
        self.assertIsNone(sp["derived_sensitivity"])
        self.assertIsNone(sp["value"])
        self.assertEqual(sp["failed_levels"], [expected_failed])

        # Topology study withholding also preserves primary vectors and verbatim reason
        tsp = res["topoSnap"]["convergence_study_provenance"]
        self.assertEqual(tsp["status"], "WITHHELD_INVALID_CONTOUR_TOPOLOGY")
        self.assertEqual(tsp["failed_levels"], [{"n": 41, "reason": "Snapped contour intersected conductor mask at n=41"}])
        self.assertEqual(res["topoSnap"]["rows"][0]["quantity"]["status"], "COMPUTED_VECTOR_2D")

    def test_lossless_v1_withheld_error_and_eight_predicate_transport_sync(self):
        """V2-SPEC-R1-M2, R1-M3, R2-M1: Lossless native statuses and 8-predicate transport-epoch clearing."""
        res = run_node_v2(
            """
            const baseResp = {
              request_id: 11,
              input_fingerprint: 'fp-abc',
              model_id: 'grounded_box_2d',
              force_budget_status: 'COMPUTED',
              force_budget: {
                left_electrode_fx_n_per_m: 0.08,
                left_electrode_fy_n_per_m: 0.0,
                right_electrode_fx_n_per_m: -0.16,
                right_electrode_fy_n_per_m: 0.0,
                enclosure_reaction_fx_n_per_m: 0.08,
                enclosure_reaction_fy_n_per_m: 0.0,
                net_electrostatic_force_fx_n_per_m: 1e-6,
                net_electrostatic_force_fy_n_per_m: 0.0,
                net_electrostatic_force_norm_n_per_m: 1e-6,
                relative_closure_residual: 1e-5,
                tolerance_n_per_m: 1e-4,
                is_force_balanced_to_tolerance: true,
                force_closure_status: 'BALANCED_WITHIN_TOLERANCE'
              },
              force_study: null,
              provenance: { source_head_sha: 'abc123', kernel_blob_sha1: D.FROZEN_KERNEL_BLOB_SHA1 }
            };
            const readyState = {
              activeModelMode: 'grounded_box_2d',
              activeViewContext: 'v1_2d',
              activeEndpoint: '/api/v1/solve',
              transportMode: 'live',
              transportEpoch: 3,
              solveState: 'ready',
              clientStateGeneration: 10,
              currentCanonicalFingerprint: 'fp-abc',
              latestDispatchedRequestId: 11,
              isComputed2DActive: true,
              lastRenderedResponse: baseResp,
              lastRenderedOrigin: { transportMode: 'live', transportEpoch: 3 },
              lastError: null
            };

            // 1. Valid 8/8 predicates
            const okPred = D.evaluateV1SyncPredicates(readyState, 10);

            // 2. Transport mode switched live -> offline with stale lastRenderedOrigin -> MUST fail predicate 8
            const mismatchTransport = Object.assign({}, readyState, { transportMode: 'offline', transportEpoch: 4 });
            const predMismatch = D.evaluateV1SyncPredicates(mismatchTransport, 10);
            const clearedSnap = D.buildForceLedgerSnapshot(mismatchTransport, 10);
            const clearedErrs = D.validateForceLedgerSnapshot(clearedSnap);

            // 3. Same transportMode ('live') after live->offline->live roundtrip (epoch 3 vs 5) -> MUST fail predicate 8
            const roundtripEpoch = Object.assign({}, readyState, { transportMode: 'live', transportEpoch: 5 });
            const predRoundtrip = D.evaluateV1SyncPredicates(roundtripEpoch, 10);

            // 4. Forged computed snapshot with mismatched response_origin_transport MUST be rejected by validator
            const forged = D.buildForceLedgerSnapshot(readyState, 10);
            forged.transport_mode = 'offline';
            const forgedErrs = D.validateForceLedgerSnapshot(forged);

            // 5. Lossless native 400 INVALID_FORCE_DOMAIN
            const errDomainState = Object.assign({}, readyState, {
              solveState: 'error',
              lastRenderedResponse: null,
              lastRenderedOrigin: null,
              lastError: { code: 'INVALID_FORCE_DOMAIN', message: 'r < 3h', httpStatus: 400 }
            });
            const errDomainSnap = D.buildForceLedgerSnapshot(errDomainState, 10);

            // 6. Lossless native 200 WITHHELD_INVALID_CONTOUR_TOPOLOGY & WITHHELD_INELIGIBLE_PRIMARY_GRID
            const topoResp = Object.assign({}, baseResp, {
              force_budget: null,
              force_budget_status: 'WITHHELD_INVALID_CONTOUR_TOPOLOGY',
              force_budget_diagnostic: 'Snapped contour invalid'
            });
            const topoSnap = D.buildForceLedgerSnapshot(Object.assign({}, readyState, { lastRenderedResponse: topoResp }), 10);

            const primIneligResp = Object.assign({}, baseResp, {
              force_budget: null,
              force_budget_status: 'WITHHELD_INELIGIBLE_PRIMARY_GRID',
              force_budget_diagnostic: 'Primary grid n=41 ineligible'
            });
            const primIneligSnap = D.buildForceLedgerSnapshot(Object.assign({}, readyState, { lastRenderedResponse: primIneligResp }), 10);

            return {
              okPred,
              predMismatch,
              clearedStatus: clearedSnap.rows[0].quantity.status,
              clearedReason: clearedSnap.rows[0].quantity.reason_code,
              clearedErrs,
              predRoundtrip,
              forgedErrs,
              errDomainQty: errDomainSnap.rows[0].quantity,
              errDomainErrs: D.validateForceLedgerSnapshot(errDomainSnap),
              topoQty: topoSnap.rows[0].quantity,
              topoErrs: D.validateForceLedgerSnapshot(topoSnap),
              primIneligQty: primIneligSnap.rows[0].quantity,
              primIneligErrs: D.validateForceLedgerSnapshot(primIneligSnap)
            };
            """
        )

        self.assertTrue(res["okPred"]["ok"])
        self.assertFalse(res["predMismatch"]["ok"])
        self.assertEqual(res["predMismatch"]["failedPredicate"], 8)
        self.assertEqual(res["predMismatch"]["reasonCode"], "TRANSPORT_EPOCH_MISMATCH")
        self.assertEqual(res["clearedStatus"], "CLEARED_PENDING_OR_INACTIVE")
        self.assertEqual(res["clearedReason"], "TRANSPORT_EPOCH_MISMATCH")
        self.assertEqual(res["clearedErrs"], [])
        self.assertFalse(res["predRoundtrip"]["ok"])
        self.assertEqual(res["predRoundtrip"]["reasonCode"], "TRANSPORT_EPOCH_MISMATCH")
        self.assertGreater(len(res["forgedErrs"]), 0)

        self.assertEqual(res["errDomainQty"]["status"], "REJECTED_INVALID_FORCE_DOMAIN")
        self.assertEqual(res["errDomainQty"]["native_v1_code"], "INVALID_FORCE_DOMAIN")
        self.assertIsNone(res["errDomainQty"]["value"])
        self.assertEqual(res["errDomainErrs"], [])

        self.assertEqual(res["topoQty"]["status"], "WITHHELD_INVALID_CONTOUR_TOPOLOGY")
        self.assertIsNone(res["topoQty"]["value"])
        self.assertEqual(res["topoErrs"], [])

        self.assertEqual(res["primIneligQty"]["status"], "WITHHELD_INELIGIBLE_PRIMARY_GRID")
        self.assertIsNone(res["primIneligQty"]["value"])
        self.assertEqual(res["primIneligErrs"], [])

    def test_exact_p1_integration_contour_parity_and_withheld_suppression(self):
        """V2-A-R1-M1: JS snapped P1 contours match frozen electrostatics_numerics.py across unequal radii, off-axis, n, W; withheld budgets return null."""
        cases = [
            {
                "name": "unequal_radii_off_axis_80mm_n81",
                "n": 81,
                "box_width_m": 0.080,
                "left": (-0.016, 0.006, 0.005, -20000.0),
                "right": (0.015, -0.004, 0.009, 0.0),
            },
            {
                "name": "asymmetric_hv_bench_80mm_n101",
                "n": 101,
                "box_width_m": 0.080,
                "left": (-0.015, 0.0, 0.007, -20000.0),
                "right": (0.015, 0.0, 0.007, 0.0),
            },
            {
                "name": "wide_160mm_unequal_off_axis_n101",
                "n": 101,
                "box_width_m": 0.160,
                "left": (-0.015, 0.008, 0.007, -20000.0),
                "right": (0.018, -0.005, 0.008, 0.0),
            },
            {
                "name": "tight_40mm_dynamic_margin_n61",
                "n": 61,
                "box_width_m": 0.040,
                "left": (-0.010, 0.003, 0.004, -5000.0),
                "right": (0.010, -0.002, 0.0035, 5000.0),
            },
        ]

        py_payload = []
        py_expected = {}
        orig_contour_fn = en.compute_maxwell_stress_contour
        for c in cases:
            lx, ly, lr, lv = c["left"]
            rx, ry, rr, rv = c["right"]
            cfg = eb.GroundedBoxConfig(
                n=c["n"],
                box_width_m=c["box_width_m"],
                left_electrode=eb.ElectrodeConfig(center_x_m=lx, center_y_m=ly, radius_m=lr, voltage_v=lv),
                right_electrode=eb.ElectrodeConfig(center_x_m=rx, center_y_m=ry, radius_m=rr, voltage_v=rv),
            )
            sol = eb.electrode_pair_in_grounded_box(config=cfg)
            captured = []

            def _spy_contour(*args, **kwargs):
                res_c = orig_contour_fn(*args, **kwargs)
                captured.append(res_c)
                return res_c

            en.compute_maxwell_stress_contour = _spy_contour
            try:
                fb = en.evaluate_whole_apparatus_force_budget(sol)
            finally:
                en.compute_maxwell_stress_contour = orig_contour_fn
            self.assertEqual(len(captured), 3)
            c_left_py, c_right_py, c_enc_py = captured
            py_expected[c["name"]] = {
                "c_left": {
                    "indices": list(c_left_py.contour_indices),
                    "x_range": list(c_left_py.contour_x_range_m),
                    "y_range": list(c_left_py.contour_y_range_m),
                },
                "c_right": {
                    "indices": list(c_right_py.contour_indices),
                    "x_range": list(c_right_py.contour_x_range_m),
                    "y_range": list(c_right_py.contour_y_range_m),
                },
                "c_enclosure_inner": {
                    "indices": list(c_enc_py.contour_indices),
                    "x_range": list(c_enc_py.contour_x_range_m),
                    "y_range": list(c_enc_py.contour_y_range_m),
                },
            }
            py_payload.append({
                "name": c["name"],
                "resp": {
                    "force_budget_status": "COMPUTED",
                    "force_budget": {"left_electrode_fx_n_per_m": fb.left_electrode_fx_n_per_m},
                    "parameters": {
                        "n": c["n"],
                        "box_width_m": c["box_width_m"],
                        "left_electrode": {"center_x_m": lx, "center_y_m": ly, "radius_m": lr, "voltage_v": lv},
                        "right_electrode": {"center_x_m": rx, "center_y_m": ry, "radius_m": rr, "voltage_v": rv},
                    },
                    "solution": {"grid_spacing_m": float(sol.grid_spacing_m)},
                },
            })

        res = run_node_v2(
            """
            const computed = {};
            for (const item of input.cases) {
              computed[item.name] = D.computeExactP1IntegrationContours(item.resp);
            }
            const sample = input.cases[0].resp;
            const withheldTopo = D.computeExactP1IntegrationContours(Object.assign({}, sample, {
              force_budget_status: 'WITHHELD_INVALID_CONTOUR_TOPOLOGY',
              force_budget: null
            }));
            const withheldPrimary = D.computeExactP1IntegrationContours(Object.assign({}, sample, {
              force_budget_status: 'WITHHELD_INELIGIBLE_PRIMARY_GRID',
              force_budget: null
            }));
            const missingBudget = D.computeExactP1IntegrationContours(Object.assign({}, sample, {
              force_budget: null
            }));
            return { computed, withheldTopo, withheldPrimary, missingBudget };
            """,
            {"cases": py_payload},
        )

        for name, exp in py_expected.items():
            got = res["computed"][name]
            self.assertIsNotNone(got, f"Expected non-null contours for {name}")
            for cname in ("c_left", "c_right", "c_enclosure_inner"):
                self.assertEqual(
                    got[cname]["contour_indices"],
                    exp[cname]["indices"],
                    f"Contour index mismatch for {name}.{cname}",
                )
                for idx in (0, 1):
                    self.assertAlmostEqual(got[cname]["contour_x_range_m"][idx], exp[cname]["x_range"][idx], delta=1e-12)
                    self.assertAlmostEqual(got[cname]["contour_y_range_m"][idx], exp[cname]["y_range"][idx], delta=1e-12)

        # Unequal radii case must produce distinct contour spans for left vs right electrode
        unequal = res["computed"]["unequal_radii_off_axis_80mm_n81"]
        left_span = unequal["c_left"]["contour_x_range_m"][1] - unequal["c_left"]["contour_x_range_m"][0]
        right_span = unequal["c_right"]["contour_x_range_m"][1] - unequal["c_right"]["contour_x_range_m"][0]
        self.assertGreater(right_span, left_span)

        # Withheld / unavailable budgets MUST return null (suppressing contours)
        self.assertIsNone(res["withheldTopo"])
        self.assertIsNone(res["withheldPrimary"])
        self.assertIsNone(res["missingBudget"])

    def test_exhaustive_schema_validation_counterexamples(self):
        """V2-A-R1-M2: Reject every §7.3 counterexample from Review #6080392750 (uncertainty, vector/residual norms, units, study_n_list, crosswalk, snapshot provenance)."""
        res = run_node_v2(
            """
            const out = {};

            // 1. COMPUTED_VECTOR_2D inconsistent magnitude_n_per_m AND mismatched uncertainty.unit ('N' inside 'N/m')
            out.vecBadMagAndUncUnit = D.validateLedgerRowValue({
              status: 'COMPUTED_VECTOR_2D',
              fx_n_per_m: 3.0,
              fy_n_per_m: 4.0,
              magnitude_n_per_m: 99.0,
              unit: 'N/m',
              uncertainty: { status: 'NOT_ASSESSED', value: null, unit: 'N', note: 'wrong unit' }
            }, 'N/m', 'primary_force_budget');

            out.vecValid = D.validateLedgerRowValue({
              status: 'COMPUTED_VECTOR_2D',
              fx_n_per_m: 3.0,
              fy_n_per_m: 4.0,
              magnitude_n_per_m: 5.0,
              unit: 'N/m',
              uncertainty: { status: 'NUMERICAL_RESIDUAL_ONLY', value: null, unit: 'N/m', note: 'valid' }
            }, 'N/m', 'primary_force_budget');

            // 2. NullableUncertainty edge cases: NOT_ASSESSED/UNBOUNDED_UNKNOWN with 0.0, negative BOUNDED, invalid status
            out.uncNotAssessedZero = D.validateNullableUncertainty({ status: 'NOT_ASSESSED', value: 0.0, unit: 'N', note: 'bad' }, 'N');
            out.uncUnboundedZero = D.validateNullableUncertainty({ status: 'UNBOUNDED_UNKNOWN', value: 0.0, unit: 'N/m', note: 'bad' }, 'N/m');
            out.uncNegBounded = D.validateNullableUncertainty({ status: 'BOUNDED', value: -1e-4, unit: 'N/m', note: 'bad' }, 'N/m');
            out.uncBadStatus = D.validateNullableUncertainty({ status: 'APPROX', value: 1e-4, unit: 'N/m', note: 'bad' }, 'N/m');

            // 3. COMPUTED_RESIDUAL_2D inconsistent norm and negative relative_closure_residual
            out.resBadNorm = D.validateLedgerRowValue({
              status: 'COMPUTED_RESIDUAL_2D',
              net_fx_n_per_m: 3e-5,
              net_fy_n_per_m: 4e-5,
              norm_n_per_m: 9e-5,
              relative_closure_residual: 1e-4,
              tolerance_n_per_m: 1e-4,
              is_force_balanced_to_tolerance: true,
              force_closure_status: 'BALANCED_WITHIN_TOLERANCE',
              unit: 'N/m'
            }, 'N/m', 'primary_force_budget');

            out.resNegRel = D.validateLedgerRowValue({
              status: 'COMPUTED_RESIDUAL_2D',
              net_fx_n_per_m: 3e-5,
              net_fy_n_per_m: 4e-5,
              norm_n_per_m: 5e-5,
              relative_closure_residual: -0.05,
              tolerance_n_per_m: 1e-4,
              is_force_balanced_to_tolerance: true,
              force_closure_status: 'BALANCED_WITHIN_TOLERANCE',
              unit: 'N/m'
            }, 'N/m', 'primary_force_budget');

            // 4. CONDITIONAL_ESTIMATE (unit 'N') inside 'N/m' domain MUST be rejected; non-string assumptions rejected; valid 'N' accepted
            out.condIn2DDomain = D.validateLedgerRowValue({
              status: 'CONDITIONAL_ESTIMATE',
              value_n: 5e-3,
              unit: 'N',
              validity_regime: 'atmospheric_1atm_collisional',
              assumptions: ['1 atm air'],
              what_if_parameters: ['corona_current_ua']
            }, 'N/m', 'comparator_estimate');

            out.condNonStringWhatIf = D.validateLedgerRowValue({
              status: 'CONDITIONAL_ESTIMATE',
              value_n: 5e-3,
              unit: 'N',
              validity_regime: 'atmospheric_1atm_collisional',
              assumptions: ['1 atm air'],
              what_if_parameters: [42]
            }, 'N', 'comparator_estimate');

            out.condValid1D = D.validateLedgerRowValue({
              status: 'CONDITIONAL_ESTIMATE',
              value_n: 5e-3,
              unit: 'N',
              validity_regime: 'atmospheric_1atm_collisional',
              assumptions: ['1 atm air'],
              what_if_parameters: ['corona_current_ua']
            }, 'N', 'comparator_estimate');

            // 5. ConvergenceStudyStatusRecord.study_n_list non-integer elements ["41", true] & n < 3 MUST be rejected
            out.studyBadNListWithheld = D.validateConvergenceStudyRecord({
              source_scope: 'convergence_study',
              status: 'WITHHELD_INELIGIBLE_MESH_LEVEL',
              force_mesh_sensitivity_status: 'WITHHELD_INELIGIBLE_MESH_LEVEL',
              study_n_list: ['41', true],
              failed_levels: [{ n: 41, reason: 'r < 3h' }],
              rows: [],
              derived_sensitivity: null,
              native_v1_code: 'WITHHELD_INELIGIBLE_MESH_LEVEL',
              value: null
            });

            out.studyBadNListComputed = D.validateConvergenceStudyRecord({
              source_scope: 'convergence_study',
              status: 'STABLE_WITHIN_STUDY_TOLERANCE',
              force_mesh_sensitivity_status: 'STABLE_WITHIN_STUDY_TOLERANCE',
              study_n_list: ['41', true],
              failed_levels: [],
              observed_order_status: 'NOT_COMPUTED_NONUNIFORM_H_RATIO'
            });

            out.studySmallN = D.validateConvergenceStudyRecord({
              source_scope: 'convergence_study',
              status: 'STABLE_WITHIN_STUDY_TOLERANCE',
              force_mesh_sensitivity_status: 'STABLE_WITHIN_STUDY_TOLERANCE',
              study_n_list: [2, 41],
              failed_levels: [],
              observed_order_status: 'NOT_COMPUTED_NONUNIFORM_H_RATIO'
            });

            // 6. ForceLedgerSnapshot crosswalk mismatch, transport_mode, sync_identity, and provenance tampering
            const baseSnap = D.buildForceLedgerSnapshot({
              activeModelMode: 'schematic_3d',
              activeViewContext: '3d_schematic',
              transportMode: 'live',
              transportEpoch: 0,
              solveState: 'idle',
              clientStateGeneration: 1,
              lastRenderedResponse: null,
              lastRenderedOrigin: null,
              lastError: null
            }, 0);

            const badCrosswalk = JSON.parse(JSON.stringify(baseSnap));
            badCrosswalk.rows[0].epistemic_class = 'PUBLISHED_HYPOTHESIS';
            badCrosswalk.rows[0].charter_categories = ['EXPERIMENTAL MEASUREMENT'];
            out.snapBadCrosswalk = D.validateForceLedgerSnapshot(badCrosswalk);

            const badCondCrosswalk = JSON.parse(JSON.stringify(baseSnap));
            badCondCrosswalk.rows[6].epistemic_class = 'CONDITIONAL_CONFOUNDER_MODEL';
            badCondCrosswalk.rows[6].charter_categories = ['ESTABLISHED MODEL'];
            out.snapMissingWhatIfCrosswalk = D.validateForceLedgerSnapshot(badCondCrosswalk);

            const badTransport = JSON.parse(JSON.stringify(baseSnap));
            badTransport.transport_mode = 'cached';
            out.snapBadTransport = D.validateForceLedgerSnapshot(badTransport);

            const bad3DTransport = JSON.parse(JSON.stringify(baseSnap));
            bad3DTransport.transport_mode = 'live';
            out.snap3DLiveTransport = D.validateForceLedgerSnapshot(bad3DTransport);

            const badKernelSha = JSON.parse(JSON.stringify(baseSnap));
            badKernelSha.provenance.kernel_blob_sha1.electrostatics_numerics = 'deadbeef';
            out.snapBadKernelSha = D.validateForceLedgerSnapshot(badKernelSha);

            const badNegEpoch = JSON.parse(JSON.stringify(baseSnap));
            badNegEpoch.sync_identity.transport_epoch = -1;
            out.snapNegEpoch = D.validateForceLedgerSnapshot(badNegEpoch);

            const badOrigin = JSON.parse(JSON.stringify(baseSnap));
            badOrigin.sync_identity.response_origin_transport = 'bogus';
            out.snapBadOrigin = D.validateForceLedgerSnapshot(badOrigin);

            const badRowBoundary = JSON.parse(JSON.stringify(baseSnap));
            badRowBoundary.rows[0].boundary = 'boundary_z_fake';
            out.snapBadBoundary = D.validateForceLedgerSnapshot(badRowBoundary);

            return out;
            """
        )

        # Counterexample 1: BOTH magnitude mismatch and uncertainty unit mismatch must be flagged
        self.assertGreaterEqual(len(res["vecBadMagAndUncUnit"]), 2)
        self.assertTrue(any("magnitude_n_per_m" in e for e in res["vecBadMagAndUncUnit"]))
        self.assertTrue(any("uncertainty.unit" in e for e in res["vecBadMagAndUncUnit"]))
        self.assertEqual(res["vecValid"], [])

        # Counterexample 2: NullableUncertainty checks
        self.assertGreater(len(res["uncNotAssessedZero"]), 0)
        self.assertGreater(len(res["uncUnboundedZero"]), 0)
        self.assertGreater(len(res["uncNegBounded"]), 0)
        self.assertGreater(len(res["uncBadStatus"]), 0)

        # Counterexample 3: COMPUTED_RESIDUAL_2D checks
        self.assertTrue(any("norm_n_per_m" in e for e in res["resBadNorm"]))
        self.assertTrue(any("relative_closure_residual" in e for e in res["resNegRel"]))

        # Counterexample 4: CONDITIONAL_ESTIMATE unit-domain & string[] checks
        self.assertTrue(any("Cross-unit" in e for e in res["condIn2DDomain"]))
        self.assertGreater(len(res["condNonStringWhatIf"]), 0)
        self.assertEqual(res["condValid1D"], [])

        # Counterexample 5: study_n_list element-level integer >= 3 checks
        self.assertGreaterEqual(len(res["studyBadNListWithheld"]), 2)
        self.assertGreaterEqual(len(res["studyBadNListComputed"]), 2)
        self.assertGreater(len(res["studySmallN"]), 0)

        # Counterexample 6: Snapshot crosswalk, transport_mode, sync_identity, provenance, boundary
        self.assertTrue(any("crosswalk" in e for e in res["snapBadCrosswalk"]))
        self.assertTrue(any("crosswalk" in e for e in res["snapMissingWhatIfCrosswalk"]))
        self.assertGreater(len(res["snapBadTransport"]), 0)
        self.assertGreater(len(res["snap3DLiveTransport"]), 0)
        self.assertTrue(any("electrostatics_numerics" in e for e in res["snapBadKernelSha"]))
        self.assertGreater(len(res["snapNegEpoch"]), 0)
        self.assertGreater(len(res["snapBadOrigin"]), 0)
        self.assertGreater(len(res["snapBadBoundary"]), 0)


if __name__ == "__main__":
    unittest.main()
