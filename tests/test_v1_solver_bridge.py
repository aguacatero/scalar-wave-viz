"""Unit, golden-vector, adversarial domain/topology, and V1-A worker dispatch tests for V1-B Slice B1."""

from __future__ import annotations

import http.client
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from unittest import mock

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _list_open_pipe_inodes() -> dict[int, int]:
    import stat

    pipes: dict[int, int] = {}
    for fd_dir in ("/proc/self/fd", "/dev/fd"):
        if os.path.isdir(fd_dir):
            for entry in os.listdir(fd_dir):
                if entry.isdigit():
                    fd = int(entry)
                    try:
                        st = os.fstat(fd)
                    except OSError:
                        continue
                    if stat.S_ISFIFO(st.st_mode):
                        pipes[fd] = st.st_ino
            return pipes
    raise RuntimeError("No /proc/self/fd or /dev/fd available")


class V1SolverAdapterTests(unittest.TestCase):
    """Canonical schemas, IEEE-754 golden vectors, P0/P1 adapters, and topology/closure gates."""

    def test_kernel_blob_hashes_and_strict_zero_p2_imports(self):
        import v1_solver_adapter as adapter

        hashes = adapter.verify_frozen_kernel_hashes()
        self.assertEqual(hashes["electrostatics_baseline"], "97f65dfa25db7730323edd5e52c98b17371fdeaa")
        self.assertEqual(hashes["electrostatics_numerics"], "a29f1f3a55946f33760179677dd3dbeb6a2ebde2")

        src = (REPO_ROOT / "v1_solver_adapter.py").read_text(encoding="utf-8")
        # Direct scipy imports and P2 / Exodus imports must remain absent
        self.assertNotIn("import scipy", src)
        self.assertNotIn("from scipy", src)
        self.assertNotIn("p2_", src)
        self.assertNotIn("Eq. (11)", src)

        # Kernel tamper detection must fail closed
        with mock.patch.object(adapter, "compute_git_blob_sha1", return_value="0" * 40):
            with self.assertRaises(RuntimeError):
                adapter.verify_frozen_kernel_hashes()

    def test_canonical_fingerprint_normative_golden_vectors_and_negzero_defaults(self):
        import v1_solver_adapter as adapter

        # Vector 1: solve + parallel_plate_1d
        req1 = adapter.validate_and_normalize_request(
            "/api/v1/solve",
            {
                "request_id": 1,
                "mode": "parallel_plate_1d",
                "parameters": {"voltage_v": 1000, "gap_m": 0.01, "area_m2": 0.01},
            },
        )
        expected_ascii_1 = (
            "v=1\n"
            "endpoint=s:solve\n"
            "mode=s:parallel_plate_1d\n"
            "parameters.area_m2=f64:3f847ae147ae147b\n"
            "parameters.gap_m=f64:3f847ae147ae147b\n"
            "parameters.voltage_v=f64:408f400000000000"
        )
        self.assertEqual(adapter.build_canonical_fingerprint_ascii(req1), expected_ascii_1)
        self.assertEqual(
            adapter.compute_input_fingerprint(req1),
            "0d200ce79da9b282f5f5b50bce58522416472cf51b9b7ce90c791f6a03b5a940",
        )

        # Vector 2: solve + grounded_box_2d omitted defaults vs explicit -0.0 and int 500/-500
        req2_omitted = adapter.validate_and_normalize_request(
            "/api/v1/solve",
            {
                "request_id": 42,
                "mode": "grounded_box_2d",
                "parameters": {
                    "n": 101,
                    "box_width_m": 0.04,
                    "left_electrode": {"center_x_m": -0.008, "center_y_m": 0.0, "radius_m": 0.003, "voltage_v": 500},
                    "right_electrode": {"center_x_m": 0.008, "center_y_m": 0.0, "radius_m": 0.003, "voltage_v": -500},
                },
            },
        )
        req2_negzero = adapter.validate_and_normalize_request(
            "/api/v1/solve",
            {
                "request_id": 999999999999,
                "mode": "grounded_box_2d",
                "parameters": {
                    "n": 101.0,
                    "box_width_m": 0.04,
                    "left_electrode": {"center_x_m": -0.008, "center_y_m": -0.0, "radius_m": 0.003, "voltage_v": 500.0},
                    "right_electrode": {"center_x_m": 0.008, "center_y_m": -0.0, "radius_m": 0.003, "voltage_v": -500.0},
                },
                "probe_xy_m": [-0.0, -0.0],
                "include_convergence_study": False,
            },
        )
        expected_ascii_2 = (
            "v=1\n"
            "endpoint=s:solve\n"
            "mode=s:grounded_box_2d\n"
            "include_convergence_study=b:false\n"
            "parameters.box_width_m=f64:3fa47ae147ae147b\n"
            "parameters.left_electrode.center_x_m=f64:bf80624dd2f1a9fc\n"
            "parameters.left_electrode.center_y_m=f64:0000000000000000\n"
            "parameters.left_electrode.radius_m=f64:3f689374bc6a7efa\n"
            "parameters.left_electrode.voltage_v=f64:407f400000000000\n"
            "parameters.n=i:101\n"
            "parameters.right_electrode.center_x_m=f64:3f80624dd2f1a9fc\n"
            "parameters.right_electrode.center_y_m=f64:0000000000000000\n"
            "parameters.right_electrode.radius_m=f64:3f689374bc6a7efa\n"
            "parameters.right_electrode.voltage_v=f64:c07f400000000000\n"
            "probe_xy_m=[f64:0000000000000000,f64:0000000000000000]"
        )
        expected_sha2 = "aeee31480630d8b59a38764137e6543be6280d1b9c08cf4dee9bf9aeec87f610"
        self.assertEqual(adapter.build_canonical_fingerprint_ascii(req2_omitted), expected_ascii_2)
        self.assertEqual(adapter.build_canonical_fingerprint_ascii(req2_negzero), expected_ascii_2)
        self.assertEqual(adapter.compute_input_fingerprint(req2_omitted), expected_sha2)
        self.assertEqual(adapter.compute_input_fingerprint(req2_negzero), expected_sha2)

        # Vector 3: solve + grounded_box_2d with include_convergence_study=True
        req3 = adapter.validate_and_normalize_request(
            "/api/v1/solve",
            {
                "request_id": 7,
                "mode": "grounded_box_2d",
                "parameters": {
                    "n": 101,
                    "box_width_m": 0.04,
                    "left_electrode": {"center_x_m": -0.008, "center_y_m": 0.0, "radius_m": 0.003, "voltage_v": 500},
                    "right_electrode": {"center_x_m": 0.008, "center_y_m": 0.0, "radius_m": 0.003, "voltage_v": -500},
                },
                "include_convergence_study": True,
            },
        )
        self.assertEqual(
            adapter.compute_input_fingerprint(req3),
            "6e410a24260b147966be7eaf1736af1055c0bd92315e8c19a64a38bb331651b5",
        )

        # Vector 4: study + grounded_box_2d omitted defaults
        req4 = adapter.validate_and_normalize_request(
            "/api/v1/study",
            {
                "request_id": 8,
                "mode": "grounded_box_2d",
                "parameters": {
                    "n": 101,
                    "box_width_m": 0.04,
                    "left_electrode": {"center_x_m": -0.008, "center_y_m": 0.0, "radius_m": 0.003, "voltage_v": 500},
                    "right_electrode": {"center_x_m": 0.008, "center_y_m": 0.0, "radius_m": 0.003, "voltage_v": -500},
                },
            },
        )
        expected_ascii_4 = (
            "v=1\n"
            "endpoint=s:study\n"
            "mode=s:grounded_box_2d\n"
            "parameters.box_width_m=f64:3fa47ae147ae147b\n"
            "parameters.left_electrode.center_x_m=f64:bf80624dd2f1a9fc\n"
            "parameters.left_electrode.center_y_m=f64:0000000000000000\n"
            "parameters.left_electrode.radius_m=f64:3f689374bc6a7efa\n"
            "parameters.left_electrode.voltage_v=f64:407f400000000000\n"
            "parameters.n=i:101\n"
            "parameters.right_electrode.center_x_m=f64:3f80624dd2f1a9fc\n"
            "parameters.right_electrode.center_y_m=f64:0000000000000000\n"
            "parameters.right_electrode.radius_m=f64:3f689374bc6a7efa\n"
            "parameters.right_electrode.voltage_v=f64:c07f400000000000\n"
            "probe_xy_m=[f64:0000000000000000,f64:0000000000000000]\n"
            "study_n_list=[i:41,i:81,i:101]"
        )
        self.assertEqual(adapter.build_canonical_fingerprint_ascii(req4), expected_ascii_4)
        self.assertEqual(
            adapter.compute_input_fingerprint(req4),
            "55c589b7628ab14016df2aefbd969f055b56a77947ee86df576f1e4423b9890b",
        )

    def test_parallel_plate_1d_parity_fringing_and_no_cross_mode_synthesis(self):
        import electrostatics_baseline as base
        import v1_solver_adapter as adapter

        # Valid 1D solve + parity against frozen P0 kernel
        status, payload = adapter.execute_ipc_request(
            "/api/v1/solve",
            {
                "request_id": 10,
                "mode": "parallel_plate_1d",
                "parameters": {"voltage_v": 1000.0, "gap_m": 0.01, "area_m2": 0.01},
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["model_id"], "parallel_plate_1d")
        self.assertEqual(payload["epistemic_label"], "ESTABLISHED MODEL")
        self.assertEqual(payload["provenance"]["whole_body_thrust_status"], "NOT MEASURED / NOT ESTABLISHED")
        self.assertEqual(payload["constants"]["epsilon_0_f_per_m"], 8.8541878188e-12)
        ref = base.parallel_plate_benchmark(1000.0, 0.01, 0.01)
        self.assertEqual(payload["electric_field_v_per_m"], ref.electric_field_v_per_m)
        self.assertEqual(payload["pressure_pa"], ref.pressure_pa)
        self.assertEqual(payload["force_on_positive_plate_n"], ref.force_on_positive_plate_n)
        self.assertEqual(payload["force_on_negative_plate_n"], ref.force_on_negative_plate_n)
        self.assertEqual(payload["net_pair_force_n"], 0.0)
        self.assertFalse(payload["fringing_warning"])  # sqrt(0.01)/0.01 = 10 >= 5

        # No cross-mode 2D fields
        for forbidden_2d in ("potential_v", "max_discrete_stencil_defect_v", "force_budget", "solution", "probe"):
            self.assertNotIn(forbidden_2d, payload)

        # Fringing warning when sqrt(A)/d < 5 (e.g. area=0.0004, sqrt=0.02, d=0.05 -> 0.4 < 5)
        st_f, p_f = adapter.execute_ipc_request(
            "/api/v1/solve",
            {
                "request_id": 11,
                "mode": "parallel_plate_1d",
                "parameters": {"voltage_v": 0.0, "gap_m": 0.05, "area_m2": 0.0004},
            },
        )
        self.assertEqual(st_f, 200)
        self.assertTrue(p_f["fringing_warning"])
        self.assertEqual(p_f["pressure_pa"], 0.0)
        self.assertEqual(p_f["force_on_positive_plate_n"], 0.0)
        self.assertEqual(p_f["net_pair_force_n"], 0.0)

        # Cross-mode fields rejected on 1D
        for bad_key, bad_val in (("probe_xy_m", [0.0, 0.0]), ("include_convergence_study", False)):
            st_b, err_b = adapter.execute_ipc_request(
                "/api/v1/solve",
                {
                    "request_id": 12,
                    "mode": "parallel_plate_1d",
                    "parameters": {"voltage_v": 100.0, "gap_m": 0.01, "area_m2": 0.01},
                    bad_key: bad_val,
                },
            )
            self.assertEqual(st_b, 400)
            self.assertEqual(err_b["error"]["code"], "UNSUPPORTED_FIELD_FOR_MODE")

    def test_presets_across_all_grids_slider_extrema_and_off_axis_nonzero_fy(self):
        import v1_solver_adapter as adapter

        for preset_name, preset in adapter.V1_PRESETS.items():
            gap_min_m, gap_max_m = preset["gap_range_mm"][0] / 1000.0, preset["gap_range_mm"][1] / 1000.0
            r = preset["left_electrode"]["radius_m"]
            for gap_m in (gap_min_m, gap_max_m):
                half_sep = gap_m / 2.0 + r
                for n in (41, 81, 101):
                    with self.subTest(preset=preset_name, gap_m=gap_m, n=n):
                        params = {
                            "n": n,
                            "box_width_m": preset["box_width_m"],
                            "left_electrode": {
                                **preset["left_electrode"],
                                "center_x_m": -half_sep,
                            },
                            "right_electrode": {
                                **preset["right_electrode"],
                                "center_x_m": half_sep,
                            },
                        }
                        st, body = adapter.execute_ipc_request(
                            "/api/v1/solve",
                            {
                                "request_id": 100 + n,
                                "mode": "grounded_box_2d",
                                "parameters": params,
                                "probe_xy_m": preset["probe_xy_m"],
                            },
                        )
                        self.assertEqual(st, 200)
                        self.assertEqual(body["force_budget_status"], "COMPUTED")
                        self.assertIsNotNone(body["force_budget"])
                        self.assertEqual(body["force_budget"]["units"], "N/m")
                        # Zero 1D fields in 2D output
                        for forbidden_1d in ("pressure_pa", "stored_energy_j", "virtual_work"):
                            self.assertNotIn(forbidden_1d, body)

        # Eligible off-axis geometry yields nonzero Fy
        st_off, body_off = adapter.execute_ipc_request(
            "/api/v1/solve",
            {
                "request_id": 200,
                "mode": "grounded_box_2d",
                "parameters": {
                    "n": 41,
                    "box_width_m": 0.080,
                    "left_electrode": {"center_x_m": -0.015, "center_y_m": 0.008, "radius_m": 0.007, "voltage_v": -20000.0},
                    "right_electrode": {"center_x_m": 0.015, "center_y_m": -0.008, "radius_m": 0.007, "voltage_v": 0.0},
                },
            },
        )
        self.assertEqual(st_off, 200)
        self.assertEqual(body_off["force_budget_status"], "COMPUTED")
        self.assertGreater(abs(body_off["force_budget"]["left_electrode_fy_n_per_m"]), 1e-6)
        self.assertGreater(abs(body_off["force_budget"]["enclosure_reaction_fy_n_per_m"]), 1e-6)

    def test_contour_tie_parity_and_dual_probe_validity_both_directions(self):
        import electrostatics_baseline as base
        import electrostatics_numerics as num
        import v1_solver_adapter as adapter

        # (a) Exact floating-point contour snap tie test (W = 0.04008, n = 41)
        cfg_tie = base.GroundedBoxConfig(
            n=41,
            box_width_m=0.04008,
            left_electrode=base.ElectrodeConfig(-0.008, 0.0, 0.003, 500.0),
            right_electrode=base.ElectrodeConfig(0.008, 0.0, 0.003, -500.0),
        )
        sol_tie = base.electrode_pair_in_grounded_box(config=cfg_tie)
        ok_tie, diag_tie = adapter.validate_snapped_contour_topology(sol_tie, cfg_tie)
        self.assertTrue(ok_tie, msg=diag_tie)
        # Verify kernel compute_maxwell_stress_contour succeeds identically on the same tie case
        budget_tie = num.evaluate_whole_apparatus_force_budget(sol_tie)
        self.assertTrue(math.isfinite(budget_tie.left_electrode_fx_n_per_m))

        # (b) Dual probe validity direction 1: physically outside conductor yet snaps onto conductor lattice node
        # W=0.04, n=41 (h=0.001), r=0.0032, left=(-0.008, 0): requested (-0.00479, 0.0) has d=0.00321 > 0.0032, snaps to (-0.005, 0) (d=0.003 <= 0.0032)
        st1, p1 = adapter.execute_ipc_request(
            "/api/v1/solve",
            {
                "request_id": 301,
                "mode": "grounded_box_2d",
                "parameters": {
                    "n": 41,
                    "box_width_m": 0.04,
                    "left_electrode": {"center_x_m": -0.008, "center_y_m": 0.0, "radius_m": 0.0032, "voltage_v": 500.0},
                    "right_electrode": {"center_x_m": 0.008, "center_y_m": 0.0, "radius_m": 0.0032, "voltage_v": -500.0},
                },
                "probe_xy_m": [-0.00479, 0.0],
            },
        )
        self.assertEqual(st1, 200)
        self.assertTrue(p1["probe"]["requested_probe_in_vacuum"])
        self.assertFalse(p1["probe"]["sampled_node_in_vacuum"])
        self.assertFalse(p1["probe"]["probe_in_vacuum"])
        self.assertEqual(p1["probe"]["probe_status"], "NON_VACUUM")
        self.assertIsNone(p1["probe"]["probe_ex_v_per_m"])
        self.assertIsNone(p1["probe"]["probe_ey_v_per_m"])
        self.assertEqual(p1["probe"]["sampled_node_potential_v"], 500.0)

        # (c) Dual probe validity direction 2: physically inside conductor yet snaps onto vacuum lattice node
        # Left circle center (-0.008, 0), r=0.00349, at n=41 (h=0.001): node at (-0.004, 0) has d=0.004 > 0.00349 (vacuum!),
        # while requested (-0.00452, 0) has d=0.00348 <= 0.00349 (physically inside left electrode!) and snaps to (-0.005? wait: -0.00449 -> -0.004)
        st2, p2 = adapter.execute_ipc_request(
            "/api/v1/solve",
            {
                "request_id": 302,
                "mode": "grounded_box_2d",
                "parameters": {
                    "n": 41,
                    "box_width_m": 0.04,
                    "left_electrode": {"center_x_m": -0.008, "center_y_m": 0.0, "radius_m": 0.0036, "voltage_v": 500.0},
                    "right_electrode": {"center_x_m": 0.008, "center_y_m": 0.0, "radius_m": 0.0036, "voltage_v": -500.0},
                },
                "probe_xy_m": [-0.00445, 0.0],
            },
        )
        self.assertEqual(st2, 200)
        self.assertFalse(p2["probe"]["requested_probe_in_vacuum"])
        self.assertTrue(p2["probe"]["sampled_node_in_vacuum"])
        self.assertFalse(p2["probe"]["probe_in_vacuum"])
        self.assertEqual(p2["probe"]["probe_status"], "NON_VACUUM")
        self.assertIsNone(p2["probe"]["probe_ex_v_per_m"])
        self.assertIsNone(p2["probe"]["probe_ey_v_per_m"])

    def test_schema_400_presolve_invalid_force_domain_and_diagonal_rejection(self):
        import v1_solver_adapter as adapter

        valid_params_41 = {
            "n": 41,
            "box_width_m": 0.04,
            "left_electrode": {"center_x_m": -0.008, "center_y_m": 0.0, "radius_m": 0.003, "voltage_v": 500.0},
            "right_electrode": {"center_x_m": 0.008, "center_y_m": 0.0, "radius_m": 0.003, "voltage_v": -500.0},
        }

        bad_schema_cases = [
            ("/api/v1/solve", {"request_id": 0, "mode": "grounded_box_2d", "parameters": valid_params_41}),
            ("/api/v1/solve", {"request_id": 9007199254740992, "mode": "grounded_box_2d", "parameters": valid_params_41}),
            ("/api/v1/solve", {"request_id": True, "mode": "grounded_box_2d", "parameters": valid_params_41}),
            ("/api/v1/solve", {"request_id": 1, "mode": "grounded_box_2d", "parameters": {**valid_params_41, "n": 121}}),
            ("/api/v1/solve", {"request_id": 1, "mode": "grounded_box_2d", "parameters": {**valid_params_41, "n": 41.5}}),
            (
                "/api/v1/solve",
                {
                    "request_id": 1,
                    "mode": "grounded_box_2d",
                    "parameters": {
                        **valid_params_41,
                        "left_electrode": {**valid_params_41["left_electrode"], "radius_m": 0.0005},
                    },
                },
            ),
            (
                "/api/v1/solve",
                {"request_id": 1, "mode": "grounded_box_2d", "parameters": valid_params_41, "probe_xy_m": [0.025, 0.0]},
            ),
            (
                "/api/v1/solve",
                {"request_id": 1, "mode": "grounded_box_2d", "parameters": valid_params_41, "extra_field": 1},
            ),
            (
                "/api/v1/solve",
                {"request_id": 1, "mode": "grounded_box_2d", "parameters": valid_params_41, "study_n_list": [41, 81, 101]},
            ),
            (
                "/api/v1/study",
                {
                    "request_id": 1,
                    "mode": "grounded_box_2d",
                    "parameters": valid_params_41,
                    "include_convergence_study": True,
                },
            ),
            (
                "/api/v1/study",
                {"request_id": 1, "mode": "grounded_box_2d", "parameters": valid_params_41, "study_n_list": [41, 81, 161]},
            ),
        ]
        for ep, body in bad_schema_cases:
            st, payload = adapter.execute_ipc_request(ep, body)
            self.assertEqual(st, 400, msg=f"Expected 400 for {ep} {body}, got {st} {payload}")
            self.assertIn("error", payload)

        # NaN rejected in strict serialization and input parsing
        st_nan, _ = adapter.execute_ipc_request(
            "/api/v1/solve",
            {
                "request_id": 1,
                "mode": "parallel_plate_1d",
                "parameters": {"voltage_v": float("nan"), "gap_m": 0.01, "area_m2": 0.01},
            },
        )
        self.assertEqual(st_nan, 400)

        # Pre-solve 400 INVALID_FORCE_DOMAIN cases:
        domain_rejects = [
            # r=0.002 at W=0.080, n=41 -> 3h = 0.006 > r
            {
                "n": 41,
                "box_width_m": 0.080,
                "left_electrode": {"center_x_m": -0.015, "center_y_m": 0.0, "radius_m": 0.002, "voltage_v": 500.0},
                "right_electrode": {"center_x_m": 0.015, "center_y_m": 0.0, "radius_m": 0.002, "voltage_v": -500.0},
            },
            # < 6h wall clearance (W=0.04, n=41 -> h=0.001, 6h=0.006; wall=0.02-(0.012+0.003)=0.005 < 0.006)
            {
                "n": 41,
                "box_width_m": 0.040,
                "left_electrode": {"center_x_m": -0.012, "center_y_m": 0.0, "radius_m": 0.003, "voltage_v": 500.0},
                "right_electrode": {"center_x_m": 0.012, "center_y_m": 0.0, "radius_m": 0.003, "voltage_v": -500.0},
            },
            # Swapped left/right electrodes
            {
                "n": 41,
                "box_width_m": 0.040,
                "left_electrode": {"center_x_m": 0.008, "center_y_m": 0.0, "radius_m": 0.003, "voltage_v": 500.0},
                "right_electrode": {"center_x_m": -0.008, "center_y_m": 0.0, "radius_m": 0.003, "voltage_v": -500.0},
            },
            # Diagonal/off-axis negative test (Euclidean sep > 2r + 6h, x-projection gap < 6h)
            {
                "n": 41,
                "box_width_m": 0.080,
                "left_electrode": {"center_x_m": -0.002, "center_y_m": -0.012, "radius_m": 0.006, "voltage_v": 500.0},
                "right_electrode": {"center_x_m": 0.002, "center_y_m": 0.012, "radius_m": 0.006, "voltage_v": -500.0},
            },
        ]
        for dom_p in domain_rejects:
            st, payload = adapter.execute_ipc_request(
                "/api/v1/solve",
                {"request_id": 55, "mode": "grounded_box_2d", "parameters": dom_p},
            )
            self.assertEqual(st, 400)
            self.assertEqual(payload["error"]["code"], "INVALID_FORCE_DOMAIN")

    def test_post_solve_withheld_invalid_contour_topology_including_minus_O(self):
        script = (
            "import sys\n"
            "sys.path.insert(0, %r)\n"
            "import electrostatics_baseline as base\n"
            "import v1_solver_adapter as adapter\n"
            "def _require(cond, msg):\n"
            "    if not cond:\n"
            "        raise RuntimeError(msg)\n"
            # Un-gated diagonal FieldSolution with overlapping x/y bounding boxes violates contour disjointness
            "cfg = base.GroundedBoxConfig(n=41, box_width_m=0.080, "
            "left_electrode=base.ElectrodeConfig(-0.004, -0.005, 0.006, 500.0), "
            "right_electrode=base.ElectrodeConfig(0.004, 0.005, 0.006, -500.0))\n"
            "sol = base.electrode_pair_in_grounded_box(config=cfg)\n"
            "fb, status, diag = adapter.evaluate_post_solve_force_budget_only(sol, cfg)\n"
            "_require(fb is None, f'Expected fb is None, got {fb!r}')\n"
            "_require(status == 'WITHHELD_INVALID_CONTOUR_TOPOLOGY', f'Expected WITHHELD_INVALID_CONTOUR_TOPOLOGY, got {status!r}')\n"
            "_require(bool(diag) and any(tok in diag for tok in ('disjoint', 'intersects non-vacuum node', 'captures')), f'Unexpected diag: {diag!r}')\n"
            # Corrupted wrong-enclosure mask must also withhold even under python -O
            "cfg_ok = base.GroundedBoxConfig(n=41, box_width_m=0.040)\n"
            "sol_ok = base.electrode_pair_in_grounded_box(config=cfg_ok)\n"
            "bad_cond = sol_ok.conductor_mask.copy()\n"
            "bad_cond[20, 20] = True\n"
            "import dataclasses\n"
            "sol_bad = dataclasses.replace(sol_ok, conductor_mask=bad_cond)\n"
            "fb2, st2, diag2 = adapter.evaluate_post_solve_force_budget_only(sol_bad, cfg_ok)\n"
            "_require(fb2 is None and st2 == 'WITHHELD_INVALID_CONTOUR_TOPOLOGY', f'Expected withheld on corrupted mask, got {fb2!r}, {st2!r}, {diag2!r}')\n"
        ) % str(REPO_ROOT)

        # Verify positive withholding under BOTH standard python and `python -O`
        for flags in ([], ["-O"]):
            res = subprocess.run([sys.executable, *flags, "-c", script], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, msg=f"flags={flags} stderr={res.stderr}")

        # V1-B-R1-F3 negative control: monkeypatch evaluate_post_solve_force_budget_only to return a non-null budget
        # and prove the runtime check fails (returncode != 0) under BOTH standard python and `python -O`.
        mutated_script = (
            "import sys\n"
            "sys.path.insert(0, %r)\n"
            "import v1_solver_adapter as adapter\n"
            "adapter.evaluate_post_solve_force_budget_only = lambda sol, cfg: ({'units': 'N/m'}, 'COMPUTED', None)\n"
        ) % str(REPO_ROOT) + script
        for flags in ([], ["-O"]):
            res_mut = subprocess.run([sys.executable, *flags, "-c", mutated_script], capture_output=True, text=True)
            self.assertNotEqual(res_mut.returncode, 0, msg=f"Mutation unexpectedly passed under flags={flags}")
            self.assertIn("RuntimeError: Expected fb is None", res_mut.stderr)

    def test_v1_b_r1_f1_study_withholds_primary_force_budget_when_primary_grid_ineligible(self):
        import v1_solver_adapter as adapter

        # Reproducer from V1-B-R1-F1: n=41, box_width_m=0.080 -> h=0.002 m; r=0.003 m < 3h=0.006 m.
        # Snapped-contour topology passes at n=41, but pre-solve grid eligibility fails at primary n=41.
        ineligible_primary_params = {
            "n": 41,
            "box_width_m": 0.080,
            "left_electrode": {"center_x_m": -0.012, "center_y_m": 0.0, "radius_m": 0.003, "voltage_v": 500.0},
            "right_electrode": {"center_x_m": 0.012, "center_y_m": 0.0, "radius_m": 0.003, "voltage_v": -500.0},
        }
        # Confirm pre-solve eligibility fails while snapped-contour topology passes on this exact grid
        ok_pre, reason_pre = adapter.check_presolve_domain_eligibility(ineligible_primary_params)
        self.assertFalse(ok_pre)
        self.assertIn("< 3h", reason_pre or "")

        st_study, body_study = adapter.execute_ipc_request(
            "/api/v1/study",
            {
                "request_id": 701,
                "mode": "grounded_box_2d",
                "parameters": ineligible_primary_params,
            },
        )
        self.assertEqual(st_study, 200)
        self.assertIsNone(body_study["solution"])
        self.assertIsNone(body_study["probe"])
        self.assertIsNone(body_study["force_budget"])
        self.assertEqual(body_study["force_budget_status"], "WITHHELD_INELIGIBLE_PRIMARY_GRID")
        self.assertTrue(body_study["force_budget_diagnostic"])
        self.assertIn("< 3h", body_study["force_budget_diagnostic"])
        self.assertEqual(body_study["force_study"]["status"], "WITHHELD_INELIGIBLE_MESH_LEVEL")
        self.assertEqual(body_study["force_study"]["rows"], [])
        self.assertIsNone(body_study["force_study"]["derived_sensitivity"])
        self.assertEqual(body_study["probe_study"]["status"], "WITHHELD_INELIGIBLE_MESH_LEVEL")
        self.assertEqual(body_study["probe_study"]["rows"], [])
        self.assertIsNone(body_study["probe_study"]["assessment"])

        # V1-B-R2-M1 negative control: primary field solver must NEVER be invoked on ineligible primary /study
        with mock.patch.object(
            adapter,
            "electrode_pair_in_grounded_box",
            side_effect=AssertionError("Primary field solver must not run when primary grid fails pre-solve eligibility"),
        ) as mocked_solver:
            st_m1, body_m1 = adapter.execute_ipc_request(
                "/api/v1/study",
                {
                    "request_id": 704,
                    "mode": "grounded_box_2d",
                    "parameters": ineligible_primary_params,
                },
            )
            self.assertEqual(mocked_solver.call_count, 0)
            self.assertEqual(st_m1, 200)
            self.assertIsNone(body_m1["solution"])
            self.assertIsNone(body_m1["probe"])
            self.assertIsNone(body_m1["force_budget"])
            self.assertEqual(body_m1["force_budget_status"], "WITHHELD_INELIGIBLE_PRIMARY_GRID")
            self.assertIn("< 3h", body_m1["force_budget_diagnostic"] or "")
            self.assertEqual(body_m1["force_study"]["status"], "WITHHELD_INELIGIBLE_MESH_LEVEL")
            self.assertEqual(body_m1["force_study"]["rows"], [])
            self.assertIsNone(body_m1["force_study"]["derived_sensitivity"])
            self.assertEqual(body_m1["probe_study"]["status"], "WITHHELD_INELIGIBLE_MESH_LEVEL")
            self.assertEqual(body_m1["probe_study"]["rows"], [])
            self.assertIsNone(body_m1["probe_study"]["assessment"])

        # Same invalid primary grid on /api/v1/solve must still reject pre-solve with HTTP 400 INVALID_FORCE_DOMAIN
        st_solve, body_solve = adapter.execute_ipc_request(
            "/api/v1/solve",
            {
                "request_id": 702,
                "mode": "grounded_box_2d",
                "parameters": ineligible_primary_params,
            },
        )
        self.assertEqual(st_solve, 400)
        self.assertEqual(body_solve["error"]["code"], "INVALID_FORCE_DOMAIN")

        # Valid-primary (n=101, h=0.0008, 3h=0.0024 <= r=0.003) / invalid-coarse (n=41) preserves primary solution, probe, and force_budget
        valid_primary_params = {**ineligible_primary_params, "n": 101}
        st_vp_study, body_vp_study = adapter.execute_ipc_request(
            "/api/v1/study",
            {
                "request_id": 703,
                "mode": "grounded_box_2d",
                "parameters": valid_primary_params,
            },
        )
        self.assertEqual(st_vp_study, 200)
        self.assertIsNotNone(body_vp_study["solution"])
        self.assertIsNotNone(body_vp_study["probe"])
        self.assertEqual(body_vp_study["force_budget_status"], "COMPUTED")
        self.assertIsNotNone(body_vp_study["force_budget"])
        self.assertEqual(body_vp_study["force_study"]["status"], "WITHHELD_INELIGIBLE_MESH_LEVEL")
        self.assertEqual(body_vp_study["force_study"]["rows"], [])
        self.assertIsNone(body_vp_study["force_study"]["derived_sensitivity"])

    def test_v1_b_r1_f2_oversized_json_integers_rejected_with_structured_400_invalid_schema(self):
        import v1_solver_adapter as adapter

        huge_pos = int("9" * 350)
        huge_neg = -int("8" * 380)
        huge_400 = 10**400

        base_2d = {
            "n": 41,
            "box_width_m": 0.04,
            "left_electrode": {"center_x_m": -0.008, "center_y_m": 0.0, "radius_m": 0.003, "voltage_v": 500.0},
            "right_electrode": {"center_x_m": 0.008, "center_y_m": 0.0, "radius_m": 0.003, "voltage_v": -500.0},
        }
        cases = [
            (
                711,
                "parameters.voltage_v",
                {
                    "request_id": 711,
                    "mode": "parallel_plate_1d",
                    "parameters": {"voltage_v": huge_400, "gap_m": 0.01, "area_m2": 0.01},
                },
            ),
            (
                712,
                "parameters.left_electrode.voltage_v",
                {
                    "request_id": 712,
                    "mode": "grounded_box_2d",
                    "parameters": {
                        **base_2d,
                        "left_electrode": {**base_2d["left_electrode"], "voltage_v": huge_neg},
                    },
                },
            ),
            (
                713,
                "parameters.right_electrode.radius_m",
                {
                    "request_id": 713,
                    "mode": "grounded_box_2d",
                    "parameters": {
                        **base_2d,
                        "right_electrode": {**base_2d["right_electrode"], "radius_m": huge_pos},
                    },
                },
            ),
            (
                714,
                "probe_xy_m[0]",
                {
                    "request_id": 714,
                    "mode": "grounded_box_2d",
                    "parameters": base_2d,
                    "probe_xy_m": [huge_pos, 0.0],
                },
            ),
            (
                715,
                "probe_xy_m[1]",
                {
                    "request_id": 715,
                    "mode": "grounded_box_2d",
                    "parameters": base_2d,
                    "probe_xy_m": [0.0, huge_neg],
                },
            ),
        ]

        for req_id, expected_field, payload in cases:
            with self.subTest(req_id=req_id, field=expected_field):
                st, err = adapter.execute_ipc_request("/api/v1/solve", payload)
                self.assertEqual(st, 400)
                self.assertEqual(err["error"]["code"], "INVALID_SCHEMA")
                self.assertEqual(err["error"]["field"], expected_field)
                self.assertEqual(err["request_id"], req_id)

                res = adapter.validate_v1_request_for_manager("/api/v1/solve", payload)
                self.assertIsNotNone(res)
                self.assertEqual(res.status_code, 400)
                self.assertEqual(res.payload["error"]["code"], "INVALID_SCHEMA")
                self.assertEqual(res.payload["error"]["field"], expected_field)
                self.assertEqual(res.payload["request_id"], req_id)

    def test_v1_b_r2_m2_unexpected_internal_validation_fault_returns_sanitized_500(self):
        import v1_solver_adapter as adapter

        sample_payload = {
            "request_id": 731,
            "mode": "parallel_plate_1d",
            "parameters": {"voltage_v": 1000.0, "gap_m": 0.01, "area_m2": 0.01},
        }
        with mock.patch.object(
            adapter,
            "validate_and_normalize_request",
            side_effect=RuntimeError("internal-sentinel"),
        ):
            st_ipc, body_ipc = adapter.execute_ipc_request("/api/v1/solve", sample_payload)
            self.assertEqual(st_ipc, 500)
            self.assertNotEqual(body_ipc["error"]["code"], "INVALID_SCHEMA")
            self.assertEqual(body_ipc["error"]["code"], "INTERNAL_VALIDATION_ERROR")
            self.assertEqual(body_ipc["request_id"], 731)
            self.assertNotIn("internal-sentinel", json.dumps(body_ipc))

            res_mgr = adapter.validate_v1_request_for_manager("/api/v1/solve", sample_payload)
            self.assertIsNotNone(res_mgr)
            self.assertEqual(res_mgr.status_code, 500)
            self.assertNotEqual(res_mgr.payload["error"]["code"], "INVALID_SCHEMA")
            self.assertEqual(res_mgr.payload["error"]["code"], "INTERNAL_VALIDATION_ERROR")
            self.assertEqual(res_mgr.payload["request_id"], 731)
            self.assertNotIn("internal-sentinel", json.dumps(res_mgr.payload))

        # Genuine schema errors and oversized integer rejection remain HTTP 400 INVALID_SCHEMA
        st_bad, body_bad = adapter.execute_ipc_request(
            "/api/v1/solve",
            {
                "request_id": 732,
                "mode": "parallel_plate_1d",
                "parameters": {"voltage_v": 10**350, "gap_m": 0.01, "area_m2": 0.01},
            },
        )
        self.assertEqual(st_bad, 400)
        self.assertEqual(body_bad["error"]["code"], "INVALID_SCHEMA")
        self.assertEqual(body_bad["error"]["field"], "parameters.voltage_v")
        self.assertEqual(body_bad["request_id"], 732)

    def test_multigrid_gating_order_suppression_provenance_and_strict_tolerance(self):
        import electrostatics_numerics as num
        import v1_solver_adapter as adapter

        # Valid-fine / invalid-coarse: W=0.080, r=0.003, cx=-/+0.012, cy=0.0, n=101
        valid_fine_params = {
            "n": 101,
            "box_width_m": 0.080,
            "left_electrode": {"center_x_m": -0.012, "center_y_m": 0.0, "radius_m": 0.003, "voltage_v": 500.0},
            "right_electrode": {"center_x_m": 0.012, "center_y_m": 0.0, "radius_m": 0.003, "voltage_v": -500.0},
        }
        st_s, p_s = adapter.execute_ipc_request(
            "/api/v1/solve",
            {"request_id": 401, "mode": "grounded_box_2d", "parameters": valid_fine_params},
        )
        self.assertEqual(st_s, 200)
        self.assertEqual(p_s["force_mesh_sensitivity_status"], "NOT_ASSESSED")
        self.assertEqual(p_s["probe_stability_status"], "NOT_ASSESSED")
        self.assertEqual(p_s["force_budget_status"], "COMPUTED")

        # /solve with include_convergence_study=True retains primary solution + force_budget while withholding study
        st_si, p_si = adapter.execute_ipc_request(
            "/api/v1/solve",
            {"request_id": 402, "mode": "grounded_box_2d", "parameters": valid_fine_params, "include_convergence_study": True},
        )
        self.assertEqual(st_si, 200)
        self.assertIsNotNone(p_si["force_budget"])
        self.assertEqual(p_si["force_study"]["status"], "WITHHELD_INELIGIBLE_MESH_LEVEL")
        self.assertEqual(p_si["force_study"]["rows"], [])
        self.assertIsNone(p_si["force_study"]["derived_sensitivity"])

        # /study returns 200 WITHHELD_INELIGIBLE_MESH_LEVEL
        st_st, p_st = adapter.execute_ipc_request(
            "/api/v1/study",
            {"request_id": 403, "mode": "grounded_box_2d", "parameters": valid_fine_params},
        )
        self.assertEqual(st_st, 200)
        self.assertEqual(p_st["force_study"]["status"], "WITHHELD_INELIGIBLE_MESH_LEVEL")
        self.assertEqual(p_st["force_study"]["rows"], [])

        # Valid full (41, 81, 101) study suppresses observed orders and reports all 6 diffs + explicit thresholds
        canon_p = {
            k: adapter.V1_PRESETS["p0_p1_canonical_40mm"][k]
            for k in ("n", "box_width_m", "left_electrode", "right_electrode")
        }
        st_full, p_full = adapter.execute_ipc_request(
            "/api/v1/study",
            {"request_id": 404, "mode": "grounded_box_2d", "parameters": canon_p},
        )
        self.assertEqual(st_full, 200)
        fs = p_full["force_study"]
        self.assertEqual(len(fs["rows"]), 3)
        self.assertEqual(fs["observed_order_status"], "NOT_COMPUTED_NONUNIFORM_H_RATIO")
        self.assertIsNone(fs["observed_order_left_electrode"])
        self.assertIsNone(fs["observed_order_right_electrode"])
        self.assertIsNone(fs["observed_order_enclosure"])
        self.assertIsNone(fs["observed_orders_by_component"])
        for comp in fs["component_assessments"].values():
            self.assertIsNone(comp["observed_order"])
        diffs = fs["derived_sensitivity"]["per_component_last_step_diff_n_per_m"]
        self.assertEqual(set(diffs.keys()), {"left_fx", "left_fy", "right_fx", "right_fy", "box_fx", "box_fy"})
        self.assertFalse(p_full["probe_study"]["assessment"]["is_converged"])

        # Strict `<` boundary check: norm == tolerance_n_per_m yields False
        import electrostatics_baseline as base

        cfg_b = base.GroundedBoxConfig(n=41, box_width_m=0.04)
        sol_b = base.electrode_pair_in_grounded_box(config=cfg_b)
        fake_budget = num.WholeApparatusForceBudget(
            left_electrode_fx_n_per_m=1.0,
            left_electrode_fy_n_per_m=0.0,
            right_electrode_fx_n_per_m=-1.0,
            right_electrode_fy_n_per_m=0.0,
            enclosure_reaction_fx_n_per_m=0.0,
            enclosure_reaction_fy_n_per_m=1e-4,
            net_electrostatic_force_fx_n_per_m=0.0,
            net_electrostatic_force_fy_n_per_m=1e-4,
            is_force_balanced_to_tolerance=True,
            unmodeled_reaction_explanation="raw note",
        )
        with mock.patch.object(adapter, "evaluate_whole_apparatus_force_budget", return_value=fake_budget):
            fb_eq = adapter.build_force_budget_payload(sol_b, cfg_b)
            self.assertFalse(fb_eq["is_force_balanced_to_tolerance"])
            self.assertEqual(fb_eq["force_closure_status"], "UNBALANCED_EXCEEDS_TOLERANCE")

        # Unbalanced n=41 -20 kV honest reporting and V^2 scaling check
        asym_base = {
            k: adapter.V1_PRESETS["asymmetric_hv_80mm_bench"][k]
            for k in ("box_width_m", "left_electrode", "right_electrode")
        }
        st_u, p_u = adapter.execute_ipc_request(
            "/api/v1/solve",
            {"request_id": 405, "mode": "grounded_box_2d", "parameters": {"n": 41, **asym_base}},
        )
        self.assertEqual(st_u, 200)
        self.assertEqual(p_u["force_budget"]["force_closure_status"], "UNBALANCED_EXCEEDS_TOLERANCE")
        self.assertIn("continuum_and_unmodeled_supports_note", p_u["force_budget"])
        self.assertIn("V^2", p_u["force_budget"]["discrete_closure_verdict"])

        # Halving voltage scales |F_net| by 1/4 (V^2)
        half_v_left = {**asym_base["left_electrode"], "voltage_v": -10000.0}
        _, p_half = adapter.execute_ipc_request(
            "/api/v1/solve",
            {
                "request_id": 406,
                "mode": "grounded_box_2d",
                "parameters": {"n": 41, "box_width_m": 0.080, "left_electrode": half_v_left, "right_electrode": asym_base["right_electrode"]},
            },
        )
        ratio = p_u["force_budget"]["net_electrostatic_force_norm_n_per_m"] / p_half["force_budget"]["net_electrostatic_force_norm_n_per_m"]
        self.assertAlmostEqual(ratio, 4.0, places=6)


class V1SolverBridgeWorkerIntegrationTests(unittest.TestCase):
    """End-to-end HTTP + POSIX spawn IPC dispatch integration preserving all V1-A invariants."""

    def test_v1_b_worker_dispatch_http_roundtrip_and_pre_admission_isolation(self):
        import v1_solver_adapter as adapter

        baseline_pipes = _list_open_pipe_inodes()
        server, port = adapter.create_solver_server(
            "127.0.0.1",
            0,
            response_deadline_s=5.0,
            worker_reap_timeout_s=2.0,
        )
        th = threading.Thread(target=server.serve_forever, daemon=True)
        th.start()

        def _post(path: str, obj: dict) -> tuple[int, dict]:
            raw = json.dumps(obj, allow_nan=False).encode("utf-8")
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=6.0)
            try:
                conn.request(
                    "POST",
                    path,
                    body=raw,
                    headers={
                        "Host": f"127.0.0.1:{port}",
                        "Origin": f"http://127.0.0.1:{port}",
                        "Content-Type": "application/json",
                        "Content-Length": str(len(raw)),
                    },
                )
                resp = conn.getresponse()
                return resp.status, json.loads(resp.read().decode("utf-8"))
            finally:
                conn.close()

        try:
            mgr = server.worker_manager
            # 1. Invalid domain rejected 400 BEFORE spawning any cold worker
            st0, p0 = _post(
                "/api/v1/solve",
                {
                    "request_id": 1,
                    "mode": "grounded_box_2d",
                    "parameters": {
                        "n": 41,
                        "box_width_m": 0.080,
                        "left_electrode": {"center_x_m": -0.015, "center_y_m": 0.0, "radius_m": 0.002, "voltage_v": 500.0},
                        "right_electrode": {"center_x_m": 0.015, "center_y_m": 0.0, "radius_m": 0.002, "voltage_v": -500.0},
                    },
                },
            )
            self.assertEqual(st0, 400)
            self.assertEqual(p0["error"]["code"], "INVALID_FORCE_DOMAIN")
            self.assertEqual(mgr.spawned_pids, [])

            # 2. Live 1D solve spawns single isolated worker over POSIX pipes
            st1, p1 = _post(
                "/api/v1/solve",
                {
                    "request_id": 2,
                    "mode": "parallel_plate_1d",
                    "parameters": {"voltage_v": 1000.0, "gap_m": 0.01, "area_m2": 0.01},
                },
            )
            self.assertEqual(st1, 200)
            self.assertEqual(p1["input_fingerprint"], "0d200ce79da9b282f5f5b50bce58522416472cf51b9b7ce90c791f6a03b5a940")
            self.assertEqual(p1["provenance"]["kernel_blob_sha1"]["electrostatics_baseline"], adapter.EXPECTED_BASELINE_BLOB_SHA1)
            self.assertEqual(len(mgr.spawned_pids), 1)
            worker_pid = mgr.spawned_pids[0]

            # 3. Warmed worker handles 2D study + invalid pre-admission does not disturb worker PID
            st_bad, _ = _post(
                "/api/v1/study",
                {"request_id": 3, "mode": "parallel_plate_1d", "parameters": {"voltage_v": 100.0, "gap_m": 0.01, "area_m2": 0.01}},
            )
            self.assertEqual(st_bad, 400)
            self.assertEqual(mgr.spawned_pids, [worker_pid])

            st2, p2 = _post(
                "/api/v1/study",
                {
                    "request_id": 4,
                    "mode": "grounded_box_2d",
                    "parameters": {
                        k: adapter.V1_PRESETS["p0_p1_canonical_40mm"][k]
                        for k in ("n", "box_width_m", "left_electrode", "right_electrode")
                    },
                },
            )
            self.assertEqual(st2, 200)
            self.assertEqual(p2["force_study"]["observed_order_status"], "NOT_COMPUTED_NONUNIFORM_H_RATIO")
            self.assertEqual(mgr.spawned_pids, [worker_pid])

            # 3b. V1-B-R1-F1 + V1-B-R2-M1 over live HTTP worker: ineligible primary grid at n=41 withholds primary solution, probe, and force_budget
            st_f1, p_f1 = _post(
                "/api/v1/study",
                {
                    "request_id": 701,
                    "mode": "grounded_box_2d",
                    "parameters": {
                        "n": 41,
                        "box_width_m": 0.080,
                        "left_electrode": {"center_x_m": -0.012, "center_y_m": 0.0, "radius_m": 0.003, "voltage_v": 500.0},
                        "right_electrode": {"center_x_m": 0.012, "center_y_m": 0.0, "radius_m": 0.003, "voltage_v": -500.0},
                    },
                },
            )
            self.assertEqual(st_f1, 200)
            self.assertIsNone(p_f1["solution"])
            self.assertIsNone(p_f1["probe"])
            self.assertIsNone(p_f1["force_budget"])
            self.assertEqual(p_f1["force_budget_status"], "WITHHELD_INELIGIBLE_PRIMARY_GRID")
            self.assertIn("< 3h", p_f1["force_budget_diagnostic"] or "")
            self.assertEqual(p_f1["force_study"]["status"], "WITHHELD_INELIGIBLE_MESH_LEVEL")
            self.assertEqual(p_f1["force_study"]["rows"], [])
            self.assertIsNone(p_f1["force_study"]["derived_sensitivity"])
            self.assertEqual(p_f1["probe_study"]["status"], "WITHHELD_INELIGIBLE_MESH_LEVEL")
            self.assertEqual(p_f1["probe_study"]["rows"], [])
            self.assertIsNone(p_f1["probe_study"]["assessment"])
            self.assertEqual(mgr.spawned_pids, [worker_pid])

            # 3c. V1-B-R1-F2 over live HTTP server: 300-400 digit integers in voltage, radius, and probe_xy_m return 400 INVALID_SCHEMA
            base_2d_http = {
                "n": 41,
                "box_width_m": 0.04,
                "left_electrode": {"center_x_m": -0.008, "center_y_m": 0.0, "radius_m": 0.003, "voltage_v": 500.0},
                "right_electrode": {"center_x_m": 0.008, "center_y_m": 0.0, "radius_m": 0.003, "voltage_v": -500.0},
            }
            for req_id_big, expected_field_big, big_payload in (
                (
                    721,
                    "parameters.left_electrode.voltage_v",
                    {
                        "request_id": 721,
                        "mode": "grounded_box_2d",
                        "parameters": {
                            **base_2d_http,
                            "left_electrode": {**base_2d_http["left_electrode"], "voltage_v": 10**350},
                        },
                    },
                ),
                (
                    722,
                    "parameters.right_electrode.radius_m",
                    {
                        "request_id": 722,
                        "mode": "grounded_box_2d",
                        "parameters": {
                            **base_2d_http,
                            "right_electrode": {**base_2d_http["right_electrode"], "radius_m": 10**360},
                        },
                    },
                ),
                (
                    723,
                    "probe_xy_m[0]",
                    {
                        "request_id": 723,
                        "mode": "grounded_box_2d",
                        "parameters": base_2d_http,
                        "probe_xy_m": [-(10**390), 0.0],
                    },
                ),
            ):
                st_big, p_big = _post("/api/v1/solve", big_payload)
                self.assertEqual(st_big, 400)
                self.assertEqual(p_big["error"]["code"], "INVALID_SCHEMA")
                self.assertEqual(p_big["error"]["field"], expected_field_big)
                self.assertEqual(p_big["request_id"], req_id_big)
                self.assertEqual(mgr.spawned_pids, [worker_pid])

            # 4. Verify inherited V1-A HTTP framing checks (bad Origin -> 403, bad Content-Type -> 415)
            raw_probe = b'{"request_id": 5, "mode": "parallel_plate_1d", "parameters": {"voltage_v": 100.0, "gap_m": 0.01, "area_m2": 0.01}}'
            for hdrs, expected_status in (
                ({"Host": f"127.0.0.1:{port}", "Origin": "https://evil.example", "Content-Type": "application/json", "Content-Length": str(len(raw_probe))}, 403),
                ({"Host": f"127.0.0.1:{port}", "Origin": f"http://127.0.0.1:{port}", "Content-Type": "text/plain", "Content-Length": str(len(raw_probe))}, 415),
            ):
                c_err = http.client.HTTPConnection("127.0.0.1", port, timeout=4.0)
                try:
                    c_err.request("POST", "/api/v1/solve", body=raw_probe, headers=hdrs)
                    self.assertEqual(c_err.getresponse().status, expected_status)
                finally:
                    c_err.close()
        finally:
            server.shutdown()
            server.server_close()
            th.join(timeout=3.0)

        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)


class V1ReferenceSnapshotsB2Tests(unittest.TestCase):
    """V1-B Slice B2 tests: deterministic offline snapshots, Python/JS IEEE-754 parity, 1D closed-form parity, and file:// compatibility."""

    def test_snapshot_artifacts_exist_deterministic_idempotent_and_strict_json(self):
        from scripts import generate_v1_snapshots as gen
        import v1_solver_adapter as adapter

        js_path = REPO_ROOT / "explorer" / "v1_reference_snapshots.js"
        json_path = REPO_ROOT / "explorer" / "v1_reference_snapshots.json"
        self.assertTrue(js_path.exists(), f"Missing {js_path}")
        self.assertTrue(json_path.exists(), f"Missing {json_path}")

        # Verify CLI --check mode succeeds on committed artifacts
        self.assertEqual(gen.main(["--check"]), 0)

        disk_json_text = json_path.read_text(encoding="utf-8")
        disk_js_text = js_path.read_text(encoding="utf-8")
        bundle = json.loads(disk_json_text)

        # Regenerate in memory and assert byte-for-byte determinism
        regen_bundle = gen.build_reference_snapshot_bundle()
        regen_json_text, regen_js_text = gen.render_snapshot_artifacts(regen_bundle)
        self.assertEqual(disk_json_text, regen_json_text)
        self.assertEqual(disk_js_text, regen_js_text)

        # Strict RFC 8259 compliance & frozen kernel/spec provenance
        adapter.strict_rfc8259_dumps(bundle)
        meta = bundle["metadata"]
        self.assertEqual(meta["epistemic_label"], "ESTABLISHED MODEL")
        self.assertEqual(meta["whole_body_thrust_status"], "NOT MEASURED / NOT ESTABLISHED")
        self.assertEqual(meta["offline_banner"], "SOLVER BRIDGE OFFLINE")
        self.assertEqual(meta["source_head_sha"], gen.FROZEN_B1_ACCEPTED_SOURCE_SHA)
        self.assertEqual(meta["v1_spec_blob_sha1"], "3ccf8ae0e8caa4d367d93eddd173dda98a13f00a")
        self.assertEqual(
            meta["kernel_blob_sha1"],
            {
                "electrostatics_baseline": "97f65dfa25db7730323edd5e52c98b17371fdeaa",
                "electrostatics_numerics": "a29f1f3a55946f33760179677dd3dbeb6a2ebde2",
            },
        )

        # Zero P2 or Exodus 3D leakage in generator or snapshot artifacts
        gen_src = (REPO_ROOT / "scripts" / "generate_v1_snapshots.py").read_text(encoding="utf-8")
        for forbidden in ("import scipy", "from scipy", "p2_", "Eq. (11)", "FIG. 21"):
            self.assertNotIn(forbidden, gen_src)

    def test_snapshot_presets_gate_enforcement_unbalanced_n41_and_provenance(self):
        json_path = REPO_ROOT / "explorer" / "v1_reference_snapshots.json"
        bundle = json.loads(json_path.read_text(encoding="utf-8"))
        presets = bundle["presets_2d"]
        self.assertEqual(
            set(presets.keys()),
            {"p0_p1_canonical_40mm", "asymmetric_hv_80mm_bench", "bipolar_hv_80mm_bench"},
        )

        for preset_id, preset_data in presets.items():
            conv = preset_data["convergence_study"]
            for st_obj in (conv["force_study"],):
                self.assertEqual(len(st_obj["rows"]), 3)
                self.assertEqual(st_obj["observed_order_status"], "NOT_COMPUTED_NONUNIFORM_H_RATIO")
                self.assertIsNone(st_obj["observed_order_left_electrode"])
                self.assertIsNone(st_obj["observed_order_right_electrode"])
                self.assertIsNone(st_obj["observed_order_enclosure"])
                self.assertIsNone(st_obj["observed_orders_by_component"])
                for ca in st_obj["component_assessments"].values():
                    self.assertIsNone(ca["observed_order"])

            for n_str in ("41", "81", "101"):
                solve_fp = preset_data["solve_fingerprints_by_n"][n_str]
                study_fp = preset_data["study_fingerprints_by_n"][n_str]
                solve_st_fp = preset_data["solve_with_study_fingerprints_by_n"][n_str]

                self.assertIn(solve_fp, bundle["by_fingerprint"])
                self.assertIn(study_fp, bundle["by_fingerprint"])
                self.assertIn(solve_st_fp, bundle["by_fingerprint"])

                solve_snap = bundle["by_fingerprint"][solve_fp]
                self.assertEqual(solve_snap["model_id"], "grounded_box_2d")
                self.assertEqual(solve_snap["epistemic_label"], "ESTABLISHED MODEL")
                self.assertEqual(solve_snap["provenance"]["whole_body_thrust_status"], "NOT MEASURED / NOT ESTABLISHED")
                self.assertEqual(
                    solve_snap["provenance"]["kernel_blob_sha1"]["electrostatics_baseline"],
                    "97f65dfa25db7730323edd5e52c98b17371fdeaa",
                )
                self.assertEqual(
                    solve_snap["provenance"]["kernel_blob_sha1"]["electrostatics_numerics"],
                    "a29f1f3a55946f33760179677dd3dbeb6a2ebde2",
                )
                self.assertEqual(solve_snap["force_budget_status"], "COMPUTED")
                self.assertIsNotNone(solve_snap["force_budget"])
                self.assertEqual(solve_snap["force_budget"]["units"], "N/m")
                self.assertEqual(solve_snap["force_mesh_sensitivity_status"], "NOT_ASSESSED")
                self.assertEqual(solve_snap["probe_stability_status"], "NOT_ASSESSED")
                self.assertIsNone(solve_snap["force_study"])

        # Spec Section 3.2: asymmetric_hv_80mm_bench is BALANCED_WITHIN_TOLERANCE at n=101, 81
        # and honestly UNBALANCED_EXCEEDS_TOLERANCE at coarse n=41
        asym_fps = presets["asymmetric_hv_80mm_bench"]["solve_fingerprints_by_n"]
        asym_101 = bundle["by_fingerprint"][asym_fps["101"]]
        asym_81 = bundle["by_fingerprint"][asym_fps["81"]]
        asym_41 = bundle["by_fingerprint"][asym_fps["41"]]
        self.assertEqual(asym_101["force_budget"]["force_closure_status"], "BALANCED_WITHIN_TOLERANCE")
        self.assertTrue(asym_101["force_budget"]["is_force_balanced_to_tolerance"])
        self.assertEqual(asym_81["force_budget"]["force_closure_status"], "BALANCED_WITHIN_TOLERANCE")
        self.assertTrue(asym_81["force_budget"]["is_force_balanced_to_tolerance"])
        self.assertEqual(asym_41["force_budget"]["force_closure_status"], "UNBALANCED_EXCEEDS_TOLERANCE")
        self.assertFalse(asym_41["force_budget"]["is_force_balanced_to_tolerance"])
        self.assertGreaterEqual(asym_41["force_budget"]["net_electrostatic_force_norm_n_per_m"], 1e-4)
        self.assertIn("V^2", asym_41["force_budget"]["discrete_closure_verdict"])

        # Generator fail-closed gate check: if a preset fails pre-solve domain eligibility, generation raises RuntimeError
        from scripts import generate_v1_snapshots as gen

        with mock.patch("v1_solver_adapter.check_presolve_domain_eligibility", return_value=(False, "synthetic 3h failure")):
            with self.assertRaises(RuntimeError) as ctx:
                gen.build_reference_snapshot_bundle()
            self.assertIn("failed Section 3.1 pre-solve domain eligibility", str(ctx.exception))

    def test_javascript_python_canonical_fingerprint_and_1d_closed_form_parity(self):
        import shutil
        import v1_solver_adapter as adapter

        node_bin = shutil.which("node")
        if not node_bin:
            for cand in (
                os.path.expanduser("~/.local/bin/node"),
                "/usr/local/bin/node",
                "/opt/homebrew/bin/node",
                "/usr/bin/node",
            ):
                if os.path.exists(cand):
                    node_bin = cand
                    break

        js_path = REPO_ROOT / "explorer" / "v1_reference_snapshots.js"
        node_body = r"""
  const h = snap.helpers;

  function assertEq(actual, expected, label) {
    if (actual !== expected) {
      throw new Error(label + ": expected " + expected + ", got " + actual);
    }
  }

  // 1. All 4 normative golden vectors + -0.0 / integer coercion equivalence
  const v1Ascii = h.buildCanonicalFingerprintAscii("/api/v1/solve", {
    mode: "parallel_plate_1d",
    parameters: { voltage_v: 1000, gap_m: 0.01, area_m2: 0.01 }
  });
  const v1Sha = h.computeInputFingerprint("/api/v1/solve", {
    mode: "parallel_plate_1d",
    parameters: { voltage_v: 1000, gap_m: 0.01, area_m2: 0.01 }
  });
  assertEq(v1Sha, "0d200ce79da9b282f5f5b50bce58522416472cf51b9b7ce90c791f6a03b5a940", "Vector 1 SHA");

  const base2dOmitted = {
    mode: "grounded_box_2d",
    parameters: {
      n: 101,
      box_width_m: 0.04,
      left_electrode: { center_x_m: -0.008, center_y_m: 0.0, radius_m: 0.003, voltage_v: 500 },
      right_electrode: { center_x_m: 0.008, center_y_m: 0.0, radius_m: 0.003, voltage_v: -500 }
    }
  };
  const base2dNegZero = {
    mode: "grounded_box_2d",
    parameters: {
      n: 101.0,
      box_width_m: 0.04,
      left_electrode: { center_x_m: -0.008, center_y_m: -0.0, radius_m: 0.003, voltage_v: 500.0 },
      right_electrode: { center_x_m: 0.008, center_y_m: -0.0, radius_m: 0.003, voltage_v: -500.0 }
    },
    probe_xy_m: [-0.0, -0.0],
    include_convergence_study: false
  };
  const v2ShaOmitted = h.computeInputFingerprint("/api/v1/solve", base2dOmitted);
  const v2ShaNegZero = h.computeInputFingerprint("/api/v1/solve", base2dNegZero);
  assertEq(v2ShaOmitted, "aeee31480630d8b59a38764137e6543be6280d1b9c08cf4dee9bf9aeec87f610", "Vector 2 omitted SHA");
  assertEq(v2ShaNegZero, "aeee31480630d8b59a38764137e6543be6280d1b9c08cf4dee9bf9aeec87f610", "Vector 2 negzero SHA");

  const v3Sha = h.computeInputFingerprint("/api/v1/solve", Object.assign({}, base2dOmitted, { include_convergence_study: true }));
  assertEq(v3Sha, "6e410a24260b147966be7eaf1736af1055c0bd92315e8c19a64a38bb331651b5", "Vector 3 SHA");

  const v4Sha = h.computeInputFingerprint("/api/v1/study", base2dOmitted);
  assertEq(v4Sha, "55c589b7628ab14016df2aefbd969f055b56a77947ee86df576f1e4423b9890b", "Vector 4 SHA");

  // 2. Verify every snapshot in by_fingerprint hydrates cleanly and matches JS recomputed fingerprint
  for (const fp of Object.keys(snap.by_fingerprint)) {
    const lookedUp = h.lookupOfflineSnapshotByFingerprint(fp);
    if (!lookedUp) {
      throw new Error("Failed to hydrate snapshot for fingerprint " + fp);
    }
    assertEq(lookedUp.input_fingerprint, fp, "lookupOfflineSnapshotByFingerprint");
    if (lookedUp.model_id === "parallel_plate_1d") {
      const jsFp = h.computeInputFingerprint("/api/v1/solve", {
        mode: "parallel_plate_1d",
        parameters: lookedUp.parameters
      });
      assertEq(jsFp, fp, "1D snapshot fingerprint match");
    } else {
      if (!lookedUp.solution || !lookedUp.force_budget) {
        throw new Error("Hydrated 2D snapshot missing solution or force_budget for " + fp);
      }
    }
  }

  // 3. Evaluate 1D test cases and return JSON for Python comparison
  const testCases1D = [
    { voltage_v: 0.0, gap_m: 0.01, area_m2: 0.01 },
    { voltage_v: -0.0, gap_m: 0.016, area_m2: 0.005 },
    { voltage_v: 1000.0, gap_m: 0.01, area_m2: 0.01 },
    { voltage_v: 20000.0, gap_m: 0.016, area_m2: 0.01 },
    { voltage_v: 50000.0, gap_m: 0.005, area_m2: 0.05 },
    { voltage_v: 1234.5, gap_m: 0.05, area_m2: 0.0004 }
  ];
  const results1D = testCases1D.map((p, idx) => h.evaluateParallelPlate1D(p, idx + 1));
  return { v1Ascii, results1D };
"""
        if node_bin:
            node_script = f"const snap = require({str(js_path)!r});\nconst out = (function() {{{node_body}}})();\nconsole.log(JSON.stringify(out));"
            proc = subprocess.run([node_bin, "-e", node_script], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, msg=f"Node parity script failed: {proc.stderr}")
            js_out = json.loads(proc.stdout.strip())
        else:
            from playwright.sync_api import sync_playwright
            from test_v0_browser_smoke import find_browser_executable

            with sync_playwright() as pw:
                browser_exe = find_browser_executable()
                launch_kwargs = {"headless": True, "args": ["--no-sandbox", "--disable-setuid-sandbox"]}
                if browser_exe:
                    launch_kwargs["executable_path"] = browser_exe
                browser = pw.chromium.launch(**launch_kwargs)
                try:
                    page = browser.new_page()
                    page.add_script_tag(path=str(js_path))
                    js_out = page.evaluate(f"() => {{ const snap = window.V1_REFERENCE_SNAPSHOTS; {node_body} }}")
                finally:
                    browser.close()

        for js_res in js_out["results1D"]:
            params = js_res["parameters"]
            st, py_res = adapter.execute_ipc_request(
                "/api/v1/solve",
                {
                    "request_id": js_res["request_id"],
                    "mode": "parallel_plate_1d",
                    "parameters": params,
                },
            )
            self.assertEqual(st, 200)
            self.assertEqual(js_res["input_fingerprint"], py_res["input_fingerprint"])
            self.assertEqual(js_res["fringing_warning"], py_res["fringing_warning"])
            self.assertEqual(js_res["constants"]["epsilon_0_f_per_m"], 8.8541878188e-12)

            scalar_keys = (
                "electric_field_v_per_m",
                "pressure_pa",
                "force_on_positive_plate_n",
                "force_on_negative_plate_n",
                "net_pair_force_n",
                "stored_energy_j",
                "fringing_aspect_ratio",
            )
            for k in scalar_keys:
                jv = float(js_res[k])
                pv = float(py_res[k])
                if params["voltage_v"] == 0.0 and k != "fringing_aspect_ratio":
                    self.assertEqual(jv, 0.0, msg=f"Expected exact 0.0 at 0 V for {k}")
                    self.assertEqual(pv, 0.0)
                else:
                    tol = max(1e-15, 1e-12 * max(abs(jv), abs(pv)))
                    self.assertLessEqual(abs(jv - pv), tol, msg=f"1D parity mismatch on {k}: js={jv} py={pv}")

            for vk, pv_vw in py_res["virtual_work"].items():
                jv_vw = float(js_res["virtual_work"][vk])
                pv_vw_f = float(pv_vw)
                if params["voltage_v"] == 0.0:
                    self.assertEqual(jv_vw, 0.0, msg=f"Expected exact 0.0 at 0 V for virtual_work.{vk}")
                else:
                    tol = max(1e-15, 1e-12 * max(abs(jv_vw), abs(pv_vw_f)))
                    self.assertLessEqual(abs(jv_vw - pv_vw_f), tol, msg=f"1D virtual_work mismatch on {vk}")

    def test_file_protocol_browser_loads_v1_reference_snapshots_offline(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.skipTest("Playwright not installed")

        from test_v0_browser_smoke import find_browser_executable

        js_path = (REPO_ROOT / "explorer" / "v1_reference_snapshots.js").resolve()
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><script src="{js_path.as_uri()}"></script></head>
<body><script>
window.__b2_check = (function() {{
  const s = window.V1_REFERENCE_SNAPSHOTS;
  if (!s || !s.helpers) return {{ ok: false, reason: "missing V1_REFERENCE_SNAPSHOTS" }};
  const fp = s.helpers.computeInputFingerprint("/api/v1/solve", {{
    mode: "grounded_box_2d",
    parameters: {{
      n: 101,
      box_width_m: 0.04,
      left_electrode: {{ center_x_m: -0.008, center_y_m: 0.0, radius_m: 0.003, voltage_v: 500 }},
      right_electrode: {{ center_x_m: 0.008, center_y_m: 0.0, radius_m: 0.003, voltage_v: -500 }}
    }}
  }});
  const snap = s.helpers.lookupOfflineSnapshotByFingerprint(fp);
  const zero1d = s.helpers.evaluateParallelPlate1D({{ voltage_v: 0, gap_m: 0.01, area_m2: 0.01 }}, 1);
  return {{
    ok: Boolean(snap && snap.force_budget && zero1d.pressure_pa === 0.0),
    fp: fp,
    thrust_status: snap ? snap.provenance.whole_body_thrust_status : null,
    unbalanced_41: s.helpers.getPresetSnapshot("asymmetric_hv_80mm_bench", 41, "solve").force_budget.force_closure_status
  }};
}})();
</script></body></html>"""

        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".html", dir=str(REPO_ROOT / "explorer"), delete=False, encoding="utf-8") as tf:
            tf.write(html)
            temp_html_path = Path(tf.name)

        try:
            with sync_playwright() as pw:
                browser_exe = find_browser_executable()
                args = ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--allow-file-access-from-files"]
                launch_kwargs = {"headless": True, "args": args}
                if browser_exe:
                    launch_kwargs["executable_path"] = browser_exe
                browser = pw.chromium.launch(**launch_kwargs)
                try:
                    page = browser.new_page()
                    page.goto(temp_html_path.resolve().as_uri())
                    res = page.evaluate("() => window.__b2_check")
                    self.assertTrue(res["ok"], msg=f"file:// check failed: {res}")
                    self.assertEqual(
                        res["fp"],
                        "aeee31480630d8b59a38764137e6543be6280d1b9c08cf4dee9bf9aeec87f610",
                    )
                    self.assertEqual(res["thrust_status"], "NOT MEASURED / NOT ESTABLISHED")
                    self.assertEqual(res["unbalanced_41"], "UNBALANCED_EXCEEDS_TOLERANCE")
                finally:
                    browser.close()
        finally:
            temp_html_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
