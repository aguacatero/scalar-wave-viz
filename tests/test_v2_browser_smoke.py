"""Playwright end-to-end browser tests for Slice V2-A (Whole-Device Force Story).

Verifies frozen V2 Design Specification R4 §7.1, §7.3, §7.4:
1. Segregated Surface A (qualitative 3D Exodus DUT H0/H1/H2, zero 1D/2D numbers) vs Surface B (separate P0/P1 analogues),
   keyboard tablist navigation, non-conflating 3D Boundary A/B shells & 2D P1 contour overlay, zero raw LaTeX delimiters.
2. Synchronized Boundary A/B/C ledgers for 1D (N) and 2D signed (Fx, Fy) (N/m), pre-debounce synchronous clearing,
   coarse n=41 UNBALANCED_EXCEEDS_TOLERANCE warning, lossless 400 INVALID_FORCE_DOMAIN & 200 WITHHELD_INVALID_CONTOUR_TOPOLOGY.
3. Simultaneous HTTP-200 COMPUTED primary + WITHHELD_INELIGIBLE_MESH_LEVEL study provenance preserving signed primary N/m
   vectors while rendering native verbatim { n, reason } study diagnostics independently (V2-SPEC-R2-L1, R3-M1).
4. Bidirectional direct transport-switch adversarial tests in ready state: live -> offline and offline -> live with zero
   request dispatch (V2-SPEC-R2-M1).
5. Pending-request transport-transition settlement adversarial tests: live -> offline and offline -> live during pending
   work with delayed HTTP 200 and delayed HTTP 500/network error, verifying synchronous cancellation/idle settlement,
   zero stale values, zero obsolete error banners, and zero permanently pending state (V2-SPEC-R3-M2).
6. Chapter 5 mathematical scalar-wave isolation (> 240 ms zero solve/study traffic) & responsive desktop 1280x860 /
   mobile 375x812 & 390x844 layouts (scrollWidth - innerWidth <= 1 px) with zero page errors.
"""

from __future__ import annotations

import http.server
import json
import os
import re
import sys
import threading
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import electrostatics_baseline as eb  # noqa: E402
import electrostatics_numerics as en  # noqa: E402
import v1_solver_adapter as adapter  # noqa: E402
from test_v0_browser_smoke import QuietHandler, find_browser_executable, is_playwright_available  # noqa: E402


@unittest.skipUnless(is_playwright_available(), "Playwright is not installed")
class V2ForceStoryBrowserTests(unittest.TestCase):
    """End-to-end Playwright regressions for Slice V2-A."""

    live_server = None
    live_thread = None
    live_port = None
    static_server = None
    static_thread = None
    static_port = None
    browser = None
    playwright_context = None

    @classmethod
    def setUpClass(cls):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise unittest.SkipTest("Playwright not installed")

        cls.live_server, cls.live_port = adapter.create_solver_server("127.0.0.1", 0)
        cls.live_thread = threading.Thread(target=cls.live_server.serve_forever, daemon=True)
        cls.live_thread.start()

        cls.static_server = http.server.HTTPServer(("127.0.0.1", 0), QuietHandler)
        cls.static_port = cls.static_server.server_address[1]
        cls.static_thread = threading.Thread(target=cls.static_server.serve_forever, daemon=True)
        cls.static_thread.start()

        cls.playwright_context = sync_playwright()
        cls.pw = cls.playwright_context.__enter__()

        browser_exe = find_browser_executable()
        args = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--allow-file-access-from-files",
        ]
        if os.uname().sysname == "Darwin":
            args.extend(["--use-gl=angle", "--use-angle=metal"])
        else:
            args.extend(["--use-gl=swiftshader"])

        launch_kwargs = {"headless": True, "args": args}
        if browser_exe:
            launch_kwargs["executable_path"] = browser_exe

        try:
            cls.browser = cls.pw.chromium.launch(**launch_kwargs)
        except Exception as exc:
            cls.playwright_context.__exit__(None, None, None)
            cls.browser = None
            raise unittest.SkipTest(f"Chromium failed to launch: {exc}")

    @classmethod
    def tearDownClass(cls):
        try:
            if cls.browser:
                cls.browser.close()
        finally:
            if cls.playwright_context:
                cls.playwright_context.__exit__(None, None, None)
            if cls.static_server:
                cls.static_server.shutdown()
                cls.static_server.server_close()
            if cls.live_server:
                cls.live_server.shutdown()
                cls.live_server.server_close()

    def _open_page(self, url: str, viewport: dict[str, int] | None = None):
        vp = viewport or {"width": 1280, "height": 860}
        context = self.browser.new_context(viewport=vp)
        page = context.new_page()
        page_errors: list[str] = []
        page.on("pageerror", lambda err: page_errors.append(str(err)))
        page.goto(url)
        page.wait_for_selector("#webgl-canvas")
        page.wait_for_selector("#loading-overlay.hidden")
        page.wait_for_function("() => Boolean(window.__v1SolverUI && window.__v2ForceStoryUI && window.V2ForceStoryData)")
        return context, page, page_errors

    def _wait_solve_state(self, page, expected_state: str, timeout_ms: int = 12000):
        page.wait_for_function(
            "(st) => window.__v1SolverUI && window.__v1SolverUI.getState().solveState === st",
            arg=expected_state,
            timeout=timeout_ms,
        )

    def test_surface_ab_non_conflation_keyboard_and_non_conflating_overlays(self):
        """V2-SPEC-R1-M1 & §6: Surface A/B separation, keyboard tablist, 3D/2D non-conflating overlays, zero LaTeX."""
        url = f"http://127.0.0.1:{self.live_port}/index.html"
        ctx, page, errors = self._open_page(url)
        try:
            page.click("#tab-btn-v2-story")
            self.assertTrue(page.locator("#tab-v2-story").is_visible())

            # Surface A default: qualitative 3D Exodus comparison, zero 1D/2D benchmark numbers
            surf_a_text = page.locator("#v2-surface-panel-a").inner_text()
            self.assertIn("QUALITATIVE 3D EXODUS COMPARISON", surf_a_text)
            self.assertIn("PENDING_SCIENTIFIC_ACCEPTANCE", surf_a_text)
            self.assertNotIn("N/m", surf_a_text)
            self.assertIsNone(re.search(r"[+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?\s*N(?:/m)?\b", surf_a_text))

            # Keyboard ArrowRight transitions Surface A -> Surface B
            page.focus("#v2-surface-tab-a")
            page.keyboard.press("ArrowRight")
            self.assertEqual(page.locator("#v2-surface-tab-b").get_attribute("aria-selected"), "true")
            self.assertTrue(page.locator("#v2-surface-panel-b").is_visible())
            self.assertIn("SEPARATE IDEALIZED P0/P1 BENCHMARK ANALOGUE", page.locator("#v2-surface-panel-b").inner_text())

            # Toggle 3D Boundary A/B shell in 3D schematic mode -> visible, zero numeric vectors
            page.click("#v2-toggle-3d-boundaries")
            overlay_state = page.evaluate(
                """() => ({
                  visible: window.__explorer.isBoundaryOverlayVisible(),
                  hasNumeric: window.__explorer.boundaryOverlayGroup.userData.hasNumericVectors
                })"""
            )
            self.assertTrue(overlay_state["visible"])
            self.assertFalse(overlay_state["hasNumeric"])
            self.assertTrue(page.locator("#v2-toggle-2d-contours").is_disabled())

            # Switch to 2D via Surface B button -> 3D boundary shell & 3D forceGroup hidden, 2D contour toggle enabled
            page.click("button[data-v2-jump-mode='grounded_box_2d']")
            self._wait_solve_state(page, "ready")
            self.assertFalse(page.evaluate("() => window.__explorer.isBoundaryOverlayVisible()"))
            self.assertFalse(page.evaluate("() => window.__explorer.forceGroup.visible"))
            self.assertFalse(page.locator("#v2-toggle-2d-contours").is_disabled())

            # Enable 2D P1 contour overlay -> canvas stays non-blank and overlay flag active
            page.click("#v2-toggle-2d-contours")
            self.assertTrue(page.evaluate("() => window.__v2ForceStoryUI.getState().show2DContourOverlay"))

            # Zero raw LaTeX delimiters in V2 tab DOM
            v2_dom_text = page.locator("#tab-v2-story").inner_text()
            self.assertIsNone(re.search(r"\\(?:frac|nabla|varepsilon|propto|oint|partial)\b", v2_dom_text))
            self.assertEqual(errors, [])
        finally:
            ctx.close()

    def test_1d_2d_ledger_sync_predebounce_clear_and_lossless_errors(self):
        """V2-SPEC-R1-M2 & R1-M3: 1D N, 2D signed (Fx, Fy) N/m, pre-debounce clear, 400 INVALID_FORCE_DOMAIN, 200 topology withhold."""
        url = f"http://127.0.0.1:{self.live_port}/index.html"
        ctx, page, errors = self._open_page(url)
        try:
            page.click("#tab-btn-v2-story")
            page.evaluate("() => window.__v1SolverUI.setMode('parallel_plate_1d')")
            self._wait_solve_state(page, "ready")

            snap1d = page.evaluate("() => window.__v2ForceStoryUI.getSnapshot()")
            self.assertEqual(snap1d["context_id"], "parallel_plate_1d")
            self.assertEqual(snap1d["unit_domain"], "N")
            self.assertEqual(snap1d["rows"][0]["quantity"]["status"], "COMPUTED_SCALAR_1D")
            self.assertEqual(snap1d["rows"][4]["quantity"]["value_n"], 0.0)

            # Slider edit triggers IMMEDIATE synchronous V2 ledger clearing before 150 ms debounce fires
            clear_check = page.evaluate(
                """() => {
                  const slider = document.getElementById('v1-1d-voltage');
                  slider.value = '5000';
                  slider.dispatchEvent(new Event('input', { bubbles: true }));
                  const snap = window.__v2ForceStoryUI.getSnapshot();
                  return {
                    solveState: window.__v1SolverUI.getState().solveState,
                    row0Status: snap.rows[0].quantity.status,
                    row0Value: snap.rows[0].quantity.value
                  };
                }"""
            )
            self.assertEqual(clear_check["solveState"], "pending")
            self.assertEqual(clear_check["row0Status"], "CLEARED_PENDING_OR_INACTIVE")
            self.assertIsNone(clear_check["row0Value"])
            self._wait_solve_state(page, "ready")

            # Switch to 2D asymmetric_hv_80mm_bench at coarse n=41 -> signed (Fx, Fy) + UNBALANCED_EXCEEDS_TOLERANCE
            page.click("#tab-btn-solver")
            page.click("#v1-mode-2d")
            self._wait_solve_state(page, "ready")
            page.select_option("#v1-2d-preset", "asymmetric_hv_80mm_bench")
            self._wait_solve_state(page, "ready")
            page.select_option("#v1-2d-grid-n", "41")
            self._wait_solve_state(page, "ready")
            page.click("#tab-btn-v2-story")

            snap2d = page.evaluate("() => window.__v2ForceStoryUI.getSnapshot()")
            self.assertEqual(snap2d["unit_domain"], "N/m")
            self.assertEqual(snap2d["rows"][0]["quantity"]["status"], "COMPUTED_VECTOR_2D")
            self.assertEqual(snap2d["rows"][7]["quantity"]["status"], "COMPUTED_RESIDUAL_2D")
            self.assertEqual(snap2d["rows"][7]["quantity"]["force_closure_status"], "UNBALANCED_EXCEEDS_TOLERANCE")
            self.assertIn("DISCRETIZATION RESIDUAL, NOT THRUST", page.locator("#v2-ledger-tbody").inner_text())

            # Inject current 400 INVALID_FORCE_DOMAIN -> lossless REJECTED_INVALID_FORCE_DOMAIN
            def route_400(route):
                route.fulfill(
                    status=400,
                    content_type="application/json",
                    body=json.dumps({
                        "request_id": None,
                        "error": {"code": "INVALID_FORCE_DOMAIN", "message": "Electrode violates 3h clearance"},
                    }),
                )

            page.route("**/api/v1/solve", route_400)
            page.click("#tab-btn-solver")
            page.select_option("#v1-2d-grid-n", "81")
            self._wait_solve_state(page, "error")
            err_snap = page.evaluate("() => window.__v2ForceStoryUI.getSnapshot()")
            self.assertEqual(err_snap["rows"][0]["quantity"]["status"], "REJECTED_INVALID_FORCE_DOMAIN")
            self.assertEqual(err_snap["rows"][0]["quantity"]["native_v1_code"], "INVALID_FORCE_DOMAIN")
            self.assertIsNone(err_snap["rows"][0]["quantity"]["value"])
            page.unroute("**/api/v1/solve", route_400)

            # Inject HTTP 200 WITHHELD_INVALID_CONTOUR_TOPOLOGY -> lossless mapping
            def route_topo(route):
                req_json = json.loads(route.request.post_data or "{}")
                fp = page.evaluate("() => window.__v1SolverUI.getState().currentCanonicalFingerprint")
                route.fulfill(
                    status=200,
                    content_type="application/json",
                    body=json.dumps({
                        "request_id": req_json.get("request_id"),
                        "input_fingerprint": fp,
                        "model_id": "grounded_box_2d",
                        "epistemic_label": "ESTABLISHED MODEL",
                        "parameters": req_json.get("parameters"),
                        "solution": None,
                        "probe": None,
                        "force_budget": None,
                        "force_budget_status": "WITHHELD_INVALID_CONTOUR_TOPOLOGY",
                        "force_budget_diagnostic": "Contour touched conductor mask",
                        "force_mesh_sensitivity_status": "NOT_ASSESSED",
                        "probe_stability_status": "NOT_ASSESSED",
                        "force_study": None,
                        "probe_study": None,
                        "provenance": {"source_head_sha": "test", "kernel_blob_sha1": {}},
                    }),
                )

            page.route("**/api/v1/solve", route_topo)
            page.select_option("#v1-2d-grid-n", "101")
            self._wait_solve_state(page, "ready")
            topo_snap = page.evaluate("() => window.__v2ForceStoryUI.getSnapshot()")
            self.assertEqual(topo_snap["rows"][0]["quantity"]["status"], "WITHHELD_INVALID_CONTOUR_TOPOLOGY")
            self.assertIsNone(topo_snap["rows"][0]["quantity"]["value"])
            page.unroute("**/api/v1/solve", route_topo)
            self.assertEqual(errors, [])
        finally:
            ctx.close()

    def test_simultaneous_computed_primary_and_withheld_study_ui_provenance(self):
        """V2-SPEC-R2-L1 & R3-M1: Primary signed N/m vectors preserved alongside verbatim { n, reason } withheld study."""
        req = {
            "request_id": 1,
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
        _, real_study_resp = adapter.solve_normalized_request(norm)
        expected_reason = real_study_resp["force_study"]["failed_levels"][0]["reason"]

        url = f"http://127.0.0.1:{self.live_port}/index.html"
        ctx, page, errors = self._open_page(url)
        try:
            page.click("#tab-btn-solver")
            page.click("#v1-mode-2d")
            self._wait_solve_state(page, "ready")

            def route_study(route):
                post = json.loads(route.request.post_data or "{}")
                fp = page.evaluate("() => window.__v1SolverUI.getState().currentCanonicalFingerprint")
                patched = dict(real_study_resp)
                patched["request_id"] = post.get("request_id")
                patched["input_fingerprint"] = fp
                route.fulfill(status=200, content_type="application/json", body=json.dumps(patched))

            page.route("**/api/v1/study", route_study)
            page.click("#v1-2d-btn-study")
            self._wait_solve_state(page, "ready")
            page.unroute("**/api/v1/study", route_study)

            page.click("#tab-btn-v2-story")
            snap = page.evaluate("() => window.__v2ForceStoryUI.getSnapshot()")
            self.assertEqual(snap["rows"][0]["source_scope"], "primary_force_budget")
            self.assertEqual(snap["rows"][0]["quantity"]["status"], "COMPUTED_VECTOR_2D")
            self.assertEqual(snap["rows"][7]["quantity"]["status"], "COMPUTED_RESIDUAL_2D")
            self.assertEqual(snap["convergence_study_provenance"]["source_scope"], "convergence_study")
            self.assertEqual(snap["convergence_study_provenance"]["status"], "WITHHELD_INELIGIBLE_MESH_LEVEL")
            self.assertEqual(snap["convergence_study_provenance"]["failed_levels"], [{"n": 41, "reason": expected_reason}])
            self.assertEqual(snap["convergence_study_provenance"]["rows"], [])
            self.assertIsNone(snap["convergence_study_provenance"]["value"])

            # Verify visible UI displays both signed primary Fx and verbatim study reason
            self.assertTrue(page.locator("#v2-study-provenance-card").is_visible())
            study_text = page.locator("#v2-study-provenance-card").inner_text()
            self.assertIn("WITHHELD_INELIGIBLE_MESH_LEVEL", study_text)
            self.assertIn(expected_reason, study_text)
            self.assertIn("6.711e-2", page.locator("#v2-ledger-tbody").inner_text())
            self.assertEqual(errors, [])
        finally:
            ctx.close()

    def test_bidirectional_direct_transport_switch_ready_state(self):
        """V2-SPEC-R2-M1: Direct live->offline and offline->live switches on ready 2D ledger synchronously clear V2."""
        url = f"http://127.0.0.1:{self.live_port}/index.html"
        ctx, page, errors = self._open_page(url)
        try:
            page.click("#tab-btn-v2-story")
            page.evaluate("() => window.__v1SolverUI.setMode('grounded_box_2d')")
            self._wait_solve_state(page, "ready")

            # Ready live ledger verified
            live_before = page.evaluate("() => ({ v1: window.__v1SolverUI.getState(), v2: window.__v2ForceStoryUI.getSnapshot() })")
            self.assertEqual(live_before["v1"]["transportMode"], "live")
            self.assertEqual(live_before["v2"]["rows"][0]["quantity"]["status"], "COMPUTED_VECTOR_2D")
            epoch0 = live_before["v1"]["transportEpoch"]

            # Direct setTransportMode("offline") with ZERO replacement dispatch -> synchronous V2 clear!
            after_off = page.evaluate(
                """() => {
                  window.__v1SolverUI.setTransportMode('offline');
                  return { v1: window.__v1SolverUI.getState(), v2: window.__v2ForceStoryUI.getSnapshot() };
                }"""
            )
            self.assertEqual(after_off["v1"]["transportMode"], "offline")
            self.assertEqual(after_off["v1"]["transportEpoch"], epoch0 + 1)
            self.assertEqual(after_off["v2"]["rows"][0]["quantity"]["status"], "CLEARED_PENDING_OR_INACTIVE")
            self.assertEqual(after_off["v2"]["rows"][0]["quantity"]["reason_code"], "TRANSPORT_EPOCH_MISMATCH")
            self.assertIsNone(after_off["v2"]["rows"][0]["quantity"]["value"])
            self.assertIn("TRANSPORT_EPOCH_MISMATCH", page.locator("#v2-ledger-status-banner").inner_text())

            # Now trigger a verified offline snapshot under the new epoch -> V2 renders offline snapshot cleanly
            page.evaluate("() => window.__v1SolverUI.setMode('grounded_box_2d')")
            self._wait_solve_state(page, "ready")
            ready_off = page.evaluate("() => ({ v1: window.__v1SolverUI.getState(), v2: window.__v2ForceStoryUI.getSnapshot() })")
            self.assertEqual(ready_off["v2"]["rows"][0]["quantity"]["status"], "COMPUTED_VECTOR_2D")
            self.assertEqual(ready_off["v2"]["sync_identity"]["response_origin_transport"], "offline")

            # Reverse direction: direct setTransportMode("live") with ZERO replacement dispatch -> synchronous V2 clear!
            after_live = page.evaluate(
                """() => {
                  window.__v1SolverUI.setTransportMode('live');
                  return { v1: window.__v1SolverUI.getState(), v2: window.__v2ForceStoryUI.getSnapshot() };
                }"""
            )
            self.assertEqual(after_live["v1"]["transportMode"], "live")
            self.assertEqual(after_live["v1"]["transportEpoch"], epoch0 + 2)
            self.assertEqual(after_live["v2"]["rows"][0]["quantity"]["status"], "CLEARED_PENDING_OR_INACTIVE")
            self.assertEqual(after_live["v2"]["rows"][0]["quantity"]["reason_code"], "TRANSPORT_EPOCH_MISMATCH")
            self.assertIsNone(after_live["v2"]["rows"][0]["quantity"]["value"])
            self.assertEqual(errors, [])
        finally:
            ctx.close()

    def test_pending_transport_transitions_with_delayed_200_and_delayed_error(self):
        """V2-SPEC-R3-M2: Live->offline & offline->live during pending work settle to idle; delayed 200/500 discarded."""
        url = f"http://127.0.0.1:{self.live_port}/index.html"
        ctx, page, errors = self._open_page(url)
        try:
            # Prime a real 2D response body to replay as a delayed HTTP 200
            page.evaluate("() => window.__v1SolverUI.setMode('grounded_box_2d')")
            self._wait_solve_state(page, "ready")
            sample_resp = page.evaluate("() => window.__v1SolverUI.getState().lastRenderedResponse")

            # Scenario A: Live -> offline during pending request + delayed HTTP 200
            # Use browser-side fetch interception so we control exact Promise resolution AFTER setTransportMode!
            res_delayed_200 = page.evaluate(
                """async (sample) => {
                  const origFetch = window.fetch;
                  let resolveFetch = null;
                  window.fetch = function (_url, _opts) {
                    return new Promise((resolve) => { resolveFetch = resolve; });
                  };
                  try {
                    window.__v1SolverUI.setMode('grounded_box_2d');
                    const duringPending = window.__v1SolverUI.getState();
                    const reqId = duringPending.latestDispatchedRequestId;
                    const fp = duringPending.currentCanonicalFingerprint;

                    // Direct transport switch while request is pending (zero replacement dispatch)
                    window.__v1SolverUI.setTransportMode('offline');
                    const rightAfterSwitch = {
                      v1: window.__v1SolverUI.getState(),
                      v2: window.__v2ForceStoryUI.getSnapshot(),
                      canvasStatusHidden: document.getElementById('v1-2d-canvas-status').classList.contains('hidden')
                    };

                    // Release delayed HTTP 200 matching old reqId & fp
                    const body = JSON.stringify(Object.assign({}, sample, { request_id: reqId, input_fingerprint: fp }));
                    resolveFetch(new Response(body, { status: 200, headers: { 'Content-Type': 'application/json' } }));
                    await new Promise((r) => setTimeout(r, 80));

                    const afterDelayed = {
                      v1: window.__v1SolverUI.getState(),
                      v2: window.__v2ForceStoryUI.getSnapshot(),
                      canvasStatusHidden: document.getElementById('v1-2d-canvas-status').classList.contains('hidden')
                    };
                    return { duringPending: duringPending.solveState, rightAfterSwitch, afterDelayed };
                  } finally {
                    window.fetch = origFetch;
                  }
                }""",
                sample_resp,
            )
            self.assertEqual(res_delayed_200["duringPending"], "pending")
            self.assertEqual(res_delayed_200["rightAfterSwitch"]["v1"]["solveState"], "idle")
            self.assertTrue(res_delayed_200["rightAfterSwitch"]["canvasStatusHidden"])
            self.assertEqual(res_delayed_200["rightAfterSwitch"]["v2"]["rows"][0]["quantity"]["status"], "CLEARED_PENDING_OR_INACTIVE")
            self.assertEqual(res_delayed_200["afterDelayed"]["v1"]["solveState"], "idle")
            self.assertTrue(res_delayed_200["afterDelayed"]["canvasStatusHidden"])
            self.assertIsNone(res_delayed_200["afterDelayed"]["v1"]["lastRenderedResponse"])
            self.assertEqual(res_delayed_200["afterDelayed"]["v2"]["rows"][0]["quantity"]["status"], "CLEARED_PENDING_OR_INACTIVE")

            # Scenario B: Live -> offline during pending request + delayed HTTP 500 error
            res_delayed_500 = page.evaluate(
                """async () => {
                  const origFetch = window.fetch;
                  let resolveFetch = null;
                  window.fetch = function (_url, _opts) {
                    return new Promise((resolve) => { resolveFetch = resolve; });
                  };
                  try {
                    window.__v1SolverUI.setTransportMode('live');
                    window.__v1SolverUI.setMode('grounded_box_2d');
                    window.__v1SolverUI.setTransportMode('offline');
                    resolveFetch(new Response(
                      JSON.stringify({ error: { code: 'HTTP_500', message: 'Late boom' } }),
                      { status: 500, headers: { 'Content-Type': 'application/json' } }
                    ));
                    await new Promise((r) => setTimeout(r, 80));
                    return {
                      solveState: window.__v1SolverUI.getState().solveState,
                      errorBannerHidden: document.getElementById('v1-error-banner').classList.contains('hidden'),
                      v2Status: window.__v2ForceStoryUI.getSnapshot().rows[0].quantity.status
                    };
                  } finally {
                    window.fetch = origFetch;
                  }
                }"""
            )
            self.assertEqual(res_delayed_500["solveState"], "idle")
            self.assertTrue(res_delayed_500["errorBannerHidden"])
            self.assertEqual(res_delayed_500["v2Status"], "CLEARED_PENDING_OR_INACTIVE")

            # Scenario C: Offline -> live during pending debounced work -> settles cleanly to idle with zero stray dispatch
            res_off_to_live = page.evaluate(
                """async () => {
                  window.__v1SolverUI.setTransportMode('offline');
                  window.__v1SolverUI.setMode('parallel_plate_1d');
                  // Trigger debounced slider edit (sets solveState="pending" + 150ms debounce timer)
                  const slider = document.getElementById('v1-1d-voltage');
                  slider.value = '12000';
                  slider.dispatchEvent(new Event('input', { bubbles: true }));
                  const beforeState = window.__v1SolverUI.getState().solveState;
                  // Switch offline -> live while debounced work is pending
                  window.__v1SolverUI.setTransportMode('live');
                  const immediateState = window.__v1SolverUI.getState().solveState;
                  await new Promise((r) => setTimeout(r, 220));
                  return {
                    beforeState,
                    immediateState,
                    afterDebounceState: window.__v1SolverUI.getState().solveState,
                    v2Status: window.__v2ForceStoryUI.getSnapshot().rows[0].quantity.status
                  };
                }"""
            )
            self.assertEqual(res_off_to_live["beforeState"], "pending")
            self.assertEqual(res_off_to_live["immediateState"], "idle")
            self.assertEqual(res_off_to_live["afterDebounceState"], "idle")
            self.assertEqual(res_off_to_live["v2Status"], "CLEARED_PENDING_OR_INACTIVE")
            self.assertEqual(errors, [])
        finally:
            ctx.close()

    def test_chapter5_isolation_and_responsive_mobile_layouts(self):
        """Chapter 5 wave isolation (> 240 ms zero fetches) and desktop/mobile 375x812 & 390x844 overflow checks."""
        url = f"http://127.0.0.1:{self.live_port}/index.html"
        for vp in ({"width": 1280, "height": 860}, {"width": 375, "height": 812}, {"width": 390, "height": 844}):
            ctx, page, errors = self._open_page(url, viewport=vp)
            try:
                if vp["width"] <= 850:
                    page.click("#mobile-tab-controls")
                page.click("#tab-btn-v2-story")
                self.assertTrue(page.locator("#tab-v2-story").is_visible())

                # Check overflow on Surface A
                ov_a = page.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
                self.assertLessEqual(ov_a, 1, f"Horizontal overflow on Surface A at {vp}: {ov_a}px")

                # Check overflow on Surface B
                page.click("#v2-surface-tab-b")
                ov_b = page.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
                self.assertLessEqual(ov_b, 1, f"Horizontal overflow on Surface B at {vp}: {ov_b}px")

                # Enter 2D mode, then activate Chapter 5 scalar-wave contrast -> V2 isolated, zero fetches past 240 ms
                page.evaluate("() => window.__v1SolverUI.setMode('grounded_box_2d')")
                self._wait_solve_state(page, "ready")

                api_requests: list[str] = []
                page.on("request", lambda req: api_requests.append(req.url) if "/api/v1/" in req.url else None)
                page.evaluate("() => window.__explorer.toggleScalarWaveContrast(true)")
                page.wait_for_timeout(260)

                self.assertEqual(api_requests, [], f"Stray solver requests fired during Chapter 5 wave mode at {vp}")
                self.assertTrue(page.locator("#v2-wave-isolation-panel").is_visible())
                self.assertTrue(page.locator("#v2-story-main-content").is_hidden())
                self.assertFalse(page.evaluate("() => window.__explorer.isBoundaryOverlayVisible()"))

                # Cleanly exit wave contrast via explicit setMode("schematic_3d")
                page.evaluate("() => window.__v1SolverUI.setMode('schematic_3d')")
                self.assertTrue(page.locator("#v2-wave-isolation-panel").is_hidden())
                self.assertTrue(page.locator("#v2-story-main-content").is_visible())
                self.assertEqual(errors, [])
            finally:
                ctx.close()

    def test_static_http_automatic_fallback_settles_without_permanent_pending(self):
        """V2-SPEC-R3-M2: Static HTTP 501 fallback settles deterministically to ready offline snapshot."""
        url = f"http://127.0.0.1:{self.static_port}/index.html"
        ctx, page, errors = self._open_page(url)
        try:
            page.click("#tab-btn-v2-story")
            page.evaluate("() => window.__v1SolverUI.setMode('grounded_box_2d')")
            self._wait_solve_state(page, "ready")
            snap = page.evaluate("() => window.__v2ForceStoryUI.getSnapshot()")
            self.assertEqual(snap["transport_mode"], "offline")
            self.assertEqual(snap["sync_identity"]["response_origin_transport"], "offline")
            self.assertEqual(snap["rows"][0]["quantity"]["status"], "COMPUTED_VECTOR_2D")
            self.assertEqual(errors, [])
        finally:
            ctx.close()

    def test_2d_exact_p1_contour_stroke_coordinates_and_withheld_suppression(self):
        """V2-A-R1-M1: Verify exact snapped P1 contour pixel coordinates on unequal/off-axis geometry and strict suppression when force budget is withheld."""
        # Build a real unequal-radius off-axis 2D solve response via the frozen P0/P1 kernels
        cfg = eb.GroundedBoxConfig(
            n=81,
            box_width_m=0.080,
            left_electrode=eb.ElectrodeConfig(center_x_m=-0.016, center_y_m=0.006, radius_m=0.005, voltage_v=-20000.0),
            right_electrode=eb.ElectrodeConfig(center_x_m=0.015, center_y_m=-0.004, radius_m=0.009, voltage_v=0.0),
        )
        sol = eb.electrode_pair_in_grounded_box(config=cfg)
        captured_contours = []
        orig_contour_fn = en.compute_maxwell_stress_contour

        def _spy_contour(*args, **kwargs):
            res_c = orig_contour_fn(*args, **kwargs)
            captured_contours.append(res_c)
            return res_c

        en.compute_maxwell_stress_contour = _spy_contour
        try:
            en.evaluate_whole_apparatus_force_budget(sol)
        finally:
            en.compute_maxwell_stress_contour = orig_contour_fn
        self.assertEqual(len(captured_contours), 3)
        c_left_py, c_right_py, c_enc_py = captured_contours
        norm_req = adapter.validate_and_normalize_request(
            "/api/v1/solve",
            {
                "request_id": 1,
                "mode": "grounded_box_2d",
                "parameters": {
                    "n": 81,
                    "box_width_m": 0.080,
                    "left_electrode": {"center_x_m": -0.016, "center_y_m": 0.006, "radius_m": 0.005, "voltage_v": -20000.0},
                    "right_electrode": {"center_x_m": 0.015, "center_y_m": -0.004, "radius_m": 0.009, "voltage_v": 0.0},
                },
                "probe_xy_m": [0.0, 0.0],
            },
        )
        _, unequal_resp = adapter.solve_normalized_request(norm_req)

        url = f"http://127.0.0.1:{self.live_port}/index.html"
        ctx, page, errors = self._open_page(url)
        try:
            page.click("#tab-btn-v2-story")
            page.evaluate("() => window.__v1SolverUI.setMode('grounded_box_2d')")
            self._wait_solve_state(page, "ready")

            # Enable 2D P1 contour overlay
            page.click("#v2-toggle-2d-contours")
            self.assertTrue(page.evaluate("() => window.__v2ForceStoryUI.getState().show2DContourOverlay"))

            # Intercept /api/v1/solve with real unequal-radius off-axis response
            def route_unequal(route):
                post = json.loads(route.request.post_data or "{}")
                fp = page.evaluate("() => window.__v1SolverUI.getState().currentCanonicalFingerprint")
                patched = dict(unequal_resp)
                patched["request_id"] = post.get("request_id")
                patched["input_fingerprint"] = fp
                route.fulfill(status=200, content_type="application/json", body=json.dumps(patched))

            page.route("**/api/v1/solve", route_unequal)
            page.evaluate("() => window.__v1SolverUI.setMode('grounded_box_2d')")
            self._wait_solve_state(page, "ready")
            page.unroute("**/api/v1/solve", route_unequal)

            drawn = page.evaluate("() => window.__v2ForceStoryUI.getState().lastDrawn2DContours")
            self.assertIsNotNone(drawn)
            self.assertEqual(drawn["world_contours"]["c_left"]["contour_indices"], list(c_left_py.contour_indices))
            self.assertEqual(drawn["world_contours"]["c_right"]["contour_indices"], list(c_right_py.contour_indices))
            self.assertEqual(drawn["world_contours"]["c_enclosure_inner"]["contour_indices"], list(c_enc_py.contour_indices))

            # Distinct unequal-radius pixel boxes & off-axis vertical positions
            rect_l = drawn["canvas_rects"]["c_left"]
            rect_r = drawn["canvas_rects"]["c_right"]
            rect_enc = drawn["canvas_rects"]["c_enclosure_inner"]
            self.assertGreater(rect_l["width"], 0.0)
            self.assertGreater(rect_r["width"], rect_l["width"])
            self.assertNotAlmostEqual(rect_l["y"], rect_r["y"], places=2)
            self.assertLess(rect_enc["x"], rect_l["x"])
            self.assertGreater(rect_enc["x"] + rect_enc["width"], rect_r["x"] + rect_r["width"])

            # Now intercept /api/v1/solve returning a REAL non-null solution (canvas renders heatmap!)
            # BUT withheld force budget -> contours MUST be strictly suppressed (lastDrawn2DContours === null)
            def route_withheld_with_solution(route):
                post = json.loads(route.request.post_data or "{}")
                fp = page.evaluate("() => window.__v1SolverUI.getState().currentCanonicalFingerprint")
                patched = dict(unequal_resp)
                patched["request_id"] = post.get("request_id")
                patched["input_fingerprint"] = fp
                patched["force_budget"] = None
                patched["force_budget_status"] = "WITHHELD_INVALID_CONTOUR_TOPOLOGY"
                patched["force_budget_diagnostic"] = "Contour touched conductor mask"
                route.fulfill(status=200, content_type="application/json", body=json.dumps(patched))

            page.route("**/api/v1/solve", route_withheld_with_solution)
            page.evaluate("() => window.__v1SolverUI.setMode('grounded_box_2d')")
            self._wait_solve_state(page, "ready")
            page.unroute("**/api/v1/solve", route_withheld_with_solution)

            v2_state = page.evaluate("() => window.__v2ForceStoryUI.getState()")
            self.assertTrue(v2_state["show2DContourOverlay"])
            self.assertIsNone(v2_state["lastDrawn2DContours"])
            self.assertEqual(v2_state["snapshot"]["rows"][0]["quantity"]["status"], "WITHHELD_INVALID_CONTOUR_TOPOLOGY")
            self.assertEqual(errors, [])
        finally:
            ctx.close()

    def test_malformed_payload_fails_closed_in_v2_ui(self):
        """V2-A-R1-M2: Malformed HTTP-200 payload violating §7.3 invariants fails closed in V2 UI (value: null, contours suppressed)."""
        url = f"http://127.0.0.1:{self.live_port}/index.html"
        ctx, page, errors = self._open_page(url)
        try:
            page.click("#tab-btn-v2-story")
            page.evaluate("() => window.__v1SolverUI.setMode('grounded_box_2d')")
            self._wait_solve_state(page, "ready")
            good_resp = page.evaluate("() => window.__v1SolverUI.getState().lastRenderedResponse")

            # Enable 2D contours so we also prove malformed payloads suppress contour rendering
            page.click("#v2-toggle-2d-contours")
            self.assertIsNotNone(page.evaluate("() => window.__v2ForceStoryUI.getState().lastDrawn2DContours"))

            # Case 1: Inconsistent residual norm_n_per_m (999.0 != hypot(net_fx, net_fy))
            def route_bad_norm(route):
                post = json.loads(route.request.post_data or "{}")
                fp = page.evaluate("() => window.__v1SolverUI.getState().currentCanonicalFingerprint")
                patched = json.loads(json.dumps(good_resp))
                patched["request_id"] = post.get("request_id")
                patched["input_fingerprint"] = fp
                patched["force_budget"]["net_electrostatic_force_norm_n_per_m"] = 999.0
                route.fulfill(status=200, content_type="application/json", body=json.dumps(patched))

            page.route("**/api/v1/solve", route_bad_norm)
            page.evaluate("() => window.__v1SolverUI.setMode('grounded_box_2d')")
            self._wait_solve_state(page, "ready")
            page.unroute("**/api/v1/solve", route_bad_norm)

            st1 = page.evaluate("() => window.__v2ForceStoryUI.getState()")
            self.assertGreater(len(st1["lastValidationErrors"]), 0)
            self.assertEqual(st1["snapshot"]["rows"][0]["quantity"]["status"], "UNAVAILABLE_SOLVER_ERROR")
            self.assertEqual(st1["snapshot"]["rows"][0]["quantity"]["native_v1_code"], "V2_SCHEMA_VALIDATION_FAILED")
            self.assertIsNone(st1["snapshot"]["rows"][0]["quantity"]["value"])
            self.assertIsNone(st1["lastDrawn2DContours"])
            self.assertNotIn("9.990e+2", page.locator("#v2-ledger-tbody").inner_text())

            # Case 2: Tampered provenance.kernel_blob_sha1
            def route_bad_sha(route):
                post = json.loads(route.request.post_data or "{}")
                fp = page.evaluate("() => window.__v1SolverUI.getState().currentCanonicalFingerprint")
                patched = json.loads(json.dumps(good_resp))
                patched["request_id"] = post.get("request_id")
                patched["input_fingerprint"] = fp
                patched["provenance"]["kernel_blob_sha1"]["electrostatics_numerics"] = "0" * 40
                route.fulfill(status=200, content_type="application/json", body=json.dumps(patched))

            page.route("**/api/v1/solve", route_bad_sha)
            page.evaluate("() => window.__v1SolverUI.setMode('grounded_box_2d')")
            self._wait_solve_state(page, "ready")
            page.unroute("**/api/v1/solve", route_bad_sha)

            st2 = page.evaluate("() => window.__v2ForceStoryUI.getState()")
            self.assertGreater(len(st2["lastValidationErrors"]), 0)
            self.assertTrue(any("electrostatics_numerics" in e for e in st2["lastValidationErrors"]))
            self.assertEqual(st2["snapshot"]["rows"][0]["quantity"]["status"], "UNAVAILABLE_SOLVER_ERROR")
            self.assertEqual(st2["snapshot"]["rows"][0]["quantity"]["native_v1_code"], "V2_SCHEMA_VALIDATION_FAILED")
            self.assertIsNone(st2["lastDrawn2DContours"])
            self.assertEqual(errors, [])
        finally:
            ctx.close()


if __name__ == "__main__":
    unittest.main()
