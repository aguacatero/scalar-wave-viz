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
            # Un-gated diagonal FieldSolution with overlapping x/y bounding boxes violates contour disjointness
            "cfg = base.GroundedBoxConfig(n=41, box_width_m=0.080, "
            "left_electrode=base.ElectrodeConfig(-0.004, -0.005, 0.006, 500.0), "
            "right_electrode=base.ElectrodeConfig(0.004, 0.005, 0.006, -500.0))\n"
            "sol = base.electrode_pair_in_grounded_box(config=cfg)\n"
            "fb, status, diag = adapter.evaluate_post_solve_force_budget_only(sol, cfg)\n"
            "assert fb is None, fb\n"
            "assert status == 'WITHHELD_INVALID_CONTOUR_TOPOLOGY', status\n"
            "assert diag and any(tok in diag for tok in ('disjoint', 'intersects non-vacuum node', 'captures')), diag\n"
            # Corrupted wrong-enclosure mask must also withhold even under python -O
            "cfg_ok = base.GroundedBoxConfig(n=41, box_width_m=0.040)\n"
            "sol_ok = base.electrode_pair_in_grounded_box(config=cfg_ok)\n"
            "bad_cond = sol_ok.conductor_mask.copy()\n"
            "bad_cond[20, 20] = True\n"
            "import dataclasses\n"
            "sol_bad = dataclasses.replace(sol_ok, conductor_mask=bad_cond)\n"
            "fb2, st2, _ = adapter.evaluate_post_solve_force_budget_only(sol_bad, cfg_ok)\n"
            "assert fb2 is None and st2 == 'WITHHELD_INVALID_CONTOUR_TOPOLOGY'\n"
        ) % str(REPO_ROOT)

        # Verify under BOTH standard python and `python -O` (optimizations strip `assert` only)
        for flags in ([], ["-O"]):
            res = subprocess.run([sys.executable, *flags, "-c", script], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, msg=f"flags={flags} stderr={res.stderr}")

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


if __name__ == "__main__":
    unittest.main()
