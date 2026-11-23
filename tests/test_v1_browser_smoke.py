"""Playwright end-to-end browser integration tests for V1-B Slice B3 (Explorer UI Integration).

Covers Section 6.1 of the accepted V1 Solver Integration Specification R5:
1. Live run_explorer.py bridge: 1D slider sweeps, exact 0 V null parity, fringing warning,
   #slider-eps visual-proxy invariance, and zero cross-mode synthesis.
2. Live 2D benchmark presets (p0_p1_canonical_40mm, asymmetric_hv_80mm_bench, bipolar_hv_80mm_bench),
   honest coarse n=41 UNBALANCED_EXCEEDS_TOLERANCE warning, 6-component N/m budget,
   non-blank 2D cross-section canvas, hidden 3D forceGroup separation, and (41, 81, 101)
   convergence study with NOT_COMPUTED_NONUNIFORM_H_RATIO order suppression.
3. Concurrency, synchronous pre-debounce invalidation, and stale 200/400/500 error identity
   isolation inside the 150 ms debounce window.
4. Current HTTP 400/500/504, network rejection, and malformed JSON clean error transitions
   (never stuck in "pending").
5. Rapid A -> B -> A mode switches and Chapter 5 scalar-wave entry while solve is in flight.
6. True dual-transport offline fallback: direct file:// protocol AND static http.server
   (SOLVER BRIDGE OFFLINE banner, locked 2D parameter sliders, frozen snapshot provenance,
   closed-form 1D parity, and offline study hydration).
7. Responsive mobile layout (375x667 and 390x844) zero-overflow and 6-chapter Iceberg preservation.
"""

from __future__ import annotations

import http.server
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
EXPLORER_DIR = REPO_ROOT / "explorer"

from test_v0_browser_smoke import QuietHandler, find_browser_executable, is_playwright_available  # noqa: E402


@unittest.skipUnless(is_playwright_available(), "Playwright is not installed")
class V1ExplorerBrowserIntegrationTests(unittest.TestCase):
    """End-to-end Playwright regressions for V1-B Slice B3 against live bridge, static HTTP, and file://."""

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

        import v1_solver_adapter as adapter

        # 1. Real V1 live solver bridge server (accepted B1 create_solver_server over run_explorer.py + v1_worker_bridge)
        cls.live_server, cls.live_port = adapter.create_solver_server("127.0.0.1", 0)
        cls.live_thread = threading.Thread(target=cls.live_server.serve_forever, daemon=True)
        cls.live_thread.start()

        # 2. Static HTTP server (no POST /api/v1/* support -> 501) for static-HTTP offline fallback
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
        vp = viewport or {"width": 1280, "height": 840}
        context = self.browser.new_context(viewport=vp)
        page = context.new_page()
        page_errors: list[str] = []
        page.on("pageerror", lambda err: page_errors.append(str(err)))
        page.goto(url)
        page.wait_for_selector("#webgl-canvas")
        page.wait_for_selector("#loading-overlay.hidden")
        page.wait_for_function("() => Boolean(window.__v1SolverUI && window.V1_REFERENCE_SNAPSHOTS)")
        return context, page, page_errors

    def _wait_solve_state(self, page, expected_state: str, timeout_ms: int = 12000):
        page.wait_for_function(
            "(st) => window.__v1SolverUI && window.__v1SolverUI.getState().solveState === st",
            arg=expected_state,
            timeout=timeout_ms,
        )

    def test_live_1d_slider_sweeps_zero_volt_null_and_eps_proxy_invariance(self):
        """Live bridge 1D sweeps, exact 0 V null parity, fringing warning, and #slider-eps VISUAL PROXY ONLY invariance."""
        url = f"http://127.0.0.1:{self.live_port}/index.html"
        ctx, page, errors = self._open_page(url)
        try:
            page.click("#tab-btn-solver")
            page.click("#v1-mode-1d")
            self._wait_solve_state(page, "ready")

            state = page.evaluate("() => window.__v1SolverUI.getState()")
            self.assertEqual(state["transportMode"], "live")
            self.assertEqual(state["activeModelMode"], "parallel_plate_1d")
            self.assertEqual(
                state["currentCanonicalFingerprint"],
                "0d200ce79da9b282f5f5b50bce58522416472cf51b9b7ce90c791f6a03b5a940",
            )
            self.assertIn("ESTABLISHED MODEL", page.locator("#v1-mode-epistemic-badge").inner_text())
            self.assertIn("NOT MEASURED / NOT ESTABLISHED", page.locator("#v1-prov-thrust").inner_text())
            self.assertIn("8.8541878188e-12", page.locator("#v1-1d-epsilon0").inner_text())
            self.assertIn("0.0 N", page.locator("#v1-1d-net-force").inner_text())
            self.assertTrue(page.locator("#v1-1d-fringing-warning").is_hidden())

            # Sweep voltage to 0 V -> exact 0.0 outputs
            page.fill("#v1-1d-voltage", "0")
            page.dispatch_event("#v1-1d-voltage", "input")
            self._wait_solve_state(page, "ready")
            self.assertEqual(page.locator("#v1-1d-e-field").inner_text(), "0.0 V/m")
            self.assertEqual(page.locator("#v1-1d-pressure").inner_text(), "0.0 Pa")
            self.assertEqual(page.locator("#v1-1d-force-pos").inner_text(), "0.0 N")
            self.assertEqual(page.locator("#v1-1d-force-neg").inner_text(), "0.0 N")
            self.assertEqual(page.locator("#v1-1d-energy").inner_text(), "0.0 J")
            self.assertEqual(page.locator("#v1-1d-vw-fixed-v").inner_text(), "0.0 N")

            # Sweep to high aspect-ratio fringing regime: 20 kV, d = 50 mm, A = 4 cm^2 -> sqrt(A)/d = 0.4 < 5.0
            page.fill("#v1-1d-voltage", "20000")
            page.dispatch_event("#v1-1d-voltage", "input")
            page.fill("#v1-1d-gap", "50")
            page.dispatch_event("#v1-1d-gap", "input")
            page.fill("#v1-1d-area", "4")
            page.dispatch_event("#v1-1d-area", "input")
            self._wait_solve_state(page, "ready")
            self.assertTrue(page.locator("#v1-1d-fringing-warning").is_visible())
            self.assertIn("0.400", page.locator("#v1-1d-aspect-ratio").inner_text())

            # Verify #slider-eps is labeled VISUAL PROXY ONLY and altering it leaves 1D readout & fingerprint unchanged
            self.assertEqual(page.locator("#v1-eps-proxy-badge").inner_text().strip(), "VISUAL PROXY ONLY")
            before_fp = page.evaluate("() => window.__v1SolverUI.getState().currentCanonicalFingerprint")
            before_p = page.locator("#v1-1d-pressure").inner_text()

            page.click("#tab-btn-sandbox")
            page.locator("#slider-eps").evaluate("el => { el.value = '1.0'; el.dispatchEvent(new Event('input')); }")
            page.wait_for_timeout(200)
            page.click("#tab-btn-solver")
            after_fp = page.evaluate("() => window.__v1SolverUI.getState().currentCanonicalFingerprint")
            after_p = page.locator("#v1-1d-pressure").inner_text()
            self.assertEqual(before_fp, after_fp)
            self.assertEqual(before_p, after_p)

            self.assertEqual(errors, [], f"Unexpected page errors: {errors}")
        finally:
            ctx.close()

    def test_live_2d_presets_unbalanced_n41_banner_canvas_separation_and_study(self):
        """Live 2D presets, honest n=41 UNBALANCED_EXCEEDS_TOLERANCE banner, hidden 3D forceGroup, and (41, 81, 101) study."""
        url = f"http://127.0.0.1:{self.live_port}/index.html"
        ctx, page, errors = self._open_page(url)
        try:
            # First turn on Chapter 3 forces so 3D forceGroup is visible before entering 2D mode
            page.click("button.chapter-step-btn[data-chapter='2']")
            page.wait_for_timeout(120)
            self.assertTrue(page.evaluate("() => window.__explorer.forceGroup.visible"))

            # Switch to V1 Solver -> 2D Grounded Box
            page.click("#tab-btn-solver")
            page.click("#v1-mode-2d")
            self._wait_solve_state(page, "ready")

            # Strict Section 5 visual separation: dedicated 2D viewport visible AND 3D forceGroup hidden
            self.assertTrue(page.locator("#v1-2d-viewport").is_visible())
            self.assertFalse(page.evaluate("() => window.__explorer.forceGroup.visible"))

            # Verify 2D canvas drew non-blank heatmap/vectors
            non_bg_pixels = page.evaluate("""() => {
              const c = document.getElementById('v1-2d-canvas');
              const data = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
              let count = 0;
              for (let i = 0; i < data.length; i += 4) {
                if (data[i] !== 5 || data[i+1] !== 8 || data[i+2] !== 13) count++;
              }
              return count;
            }""")
            self.assertGreater(non_bg_pixels, 5000, "2D cross-section canvas appears blank")

            # Default p0_p1_canonical_40mm n=101 should be BALANCED_WITHIN_TOLERANCE
            self.assertIn("BALANCED_WITHIN_TOLERANCE", page.locator("#v1-2d-closure-status-label").inner_text())
            self.assertEqual(page.locator("#v1-2d-mesh-sens-status").inner_text(), "NOT_ASSESSED")

            # Live non-vacuum probe check ([-8, 0] mm lies inside left conductor) -> NON_VACUUM & N/A Ex/Ey
            page.fill("#v1-2d-probe-x", "-8")
            page.dispatch_event("#v1-2d-probe-x", "input")
            self._wait_solve_state(page, "ready")
            self.assertEqual(page.locator("#v1-2d-probe-status").inner_text(), "NON_VACUUM")
            self.assertEqual(page.locator("#v1-2d-probe-ex").inner_text(), "N/A (NON_VACUUM)")
            self.assertIn("sampled lattice node", page.locator("#v1-2d-probe-phi").inner_text())

            # Live off-axis cy = +4.0 mm -> nonzero Fy rendered in 6-component budget
            page.fill("#v1-2d-probe-x", "0")
            page.dispatch_event("#v1-2d-probe-x", "input")
            page.fill("#v1-2d-cy", "4")
            page.dispatch_event("#v1-2d-cy", "input")
            self._wait_solve_state(page, "ready")
            fy_left = page.evaluate("() => window.__v1SolverUI.getState().lastRenderedResponse.force_budget.left_electrode_fy_n_per_m")
            self.assertNotAlmostEqual(fy_left, 0.0, places=9)
            self.assertNotEqual(page.locator("#v1-2d-fy-left").inner_text(), "0.0")

            # Switch to asymmetric_hv_80mm_bench at coarse n=41 -> honest UNBALANCED_EXCEEDS_TOLERANCE warning
            page.select_option("#v1-2d-preset", "asymmetric_hv_80mm_bench")
            self._wait_solve_state(page, "ready")
            page.select_option("#v1-2d-grid-n", "41")
            self._wait_solve_state(page, "ready")

            banner_cls = page.locator("#v1-2d-closure-banner").get_attribute("class") or ""
            self.assertIn("v1-banner-unbalanced", banner_cls)
            self.assertIn("UNBALANCED_EXCEEDS_TOLERANCE", page.locator("#v1-2d-closure-status-label").inner_text())
            verdict_text = page.locator("#v1-2d-closure-verdict").inner_text()
            self.assertIn("V^2", verdict_text)
            self.assertNotIn("balanced within tolerance", verdict_text.lower())

            # Run (41, 81, 101) convergence study
            page.click("#v1-2d-btn-study")
            self._wait_solve_state(page, "ready", timeout_ms=20000)
            self.assertTrue(page.locator("#v1-2d-study-card").is_visible())
            self.assertEqual(page.locator("#v1-2d-study-rows tr").count(), 3)
            self.assertIn("NOT_COMPUTED_NONUNIFORM_H_RATIO", page.locator("#v1-2d-study-order-status").inner_text())
            self.assertIn("study_row=1e-3", page.locator("#v1-2d-study-thresholds").inner_text())

            # Switch back to 3D Schematic -> 2D viewport hidden & 3D forceGroup restored
            page.click("#v1-mode-schematic")
            self.assertTrue(page.locator("#v1-2d-viewport").is_hidden())
            self.assertTrue(page.evaluate("() => window.__explorer.forceGroup.visible"))

            self.assertEqual(errors, [], f"Unexpected page errors: {errors}")
        finally:
            ctx.close()

    def test_concurrency_stale_200_and_stale_400_500_inside_debounce_window(self):
        """Section 6.1 R2-M2/R3-M2: delayed 200 AND delayed 400/500 arriving inside 150 ms debounce never overwrite newer state."""
        url = f"http://127.0.0.1:{self.live_port}/index.html"
        ctx, page, errors = self._open_page(url)
        try:
            page.click("#tab-btn-solver")
            page.click("#v1-mode-1d")
            self._wait_solve_state(page, "ready")

            # Use in-page fetch interception so we can hold and release exact promises deterministically inside the 150 ms debounce window
            page.evaluate("""() => {
              window.__origFetch = window.fetch.bind(window);
              window.__heldRequests = [];
              window.fetch = function(input, init) {
                const urlStr = typeof input === 'string' ? input : input.url;
                if (urlStr.includes('/api/v1/solve') && window.__interceptMode) {
                  const mode = window.__interceptMode;
                  window.__interceptMode = null;
                  const bodyObj = JSON.parse(init.body);
                  return new Promise((resolve, reject) => {
                    window.__heldRequests.push({ mode, bodyObj, resolve, reject });
                  });
                }
                return window.__origFetch(input, init);
              };
            }""")

            # 1. Delayed 200 arriving inside 150 ms debounce window after newer slider move
            page.evaluate("() => { window.__interceptMode = 'hold_200'; }")
            page.fill("#v1-1d-voltage", "2000")
            page.dispatch_event("#v1-1d-voltage", "input")
            page.wait_for_function("() => window.__heldRequests.length === 1")

            # Move slider to 15000 V (synchronous pre-debounce invalidation runs immediately; 150 ms timer starts)
            page.fill("#v1-1d-voltage", "15000")
            page.dispatch_event("#v1-1d-voltage", "input")

            # Release stale 200 response for 2000 V IMMEDIATELY while 15000 V is still inside 150 ms debounce window
            page.evaluate("""() => {
              const held = window.__heldRequests.shift();
              const snapRes = window.V1_REFERENCE_SNAPSHOTS.helpers.evaluateParallelPlate1D(held.bodyObj.parameters, held.bodyObj.request_id);
              held.resolve(new Response(JSON.stringify(snapRes), {
                status: 200,
                headers: { 'Content-Type': 'application/json' }
              }));
            }""")
            # Immediately after stale 200 resolves, UI must STILL be pending (never overwritten by stale 2000 V result)
            page.wait_for_timeout(30)
            self.assertEqual(page.evaluate("() => window.__v1SolverUI.getState().solveState"), "pending")
            self.assertEqual(page.locator("#v1-1d-e-field").inner_text(), "—")

            # Wait for newer 15000 V live solve to finish -> 15000 / 0.01 = 1.5e6 V/m
            self._wait_solve_state(page, "ready")
            self.assertIn("1.5000e+6", page.locator("#v1-1d-e-field").inner_text())

            # 2. Delayed 500 AND delayed 400 arriving inside 150 ms debounce window -> stale error NEVER clears or shows error banner
            for err_status, err_code, v_old, v_new in (
                (500, "STALE_INTERNAL_ERR", "3000", "25000"),
                (400, "STALE_SCHEMA_ERR", "4000", "30000"),
            ):
                page.evaluate("() => { window.__interceptMode = 'hold_err'; }")
                page.fill("#v1-1d-voltage", v_old)
                page.dispatch_event("#v1-1d-voltage", "input")
                page.wait_for_function("() => window.__heldRequests.length === 1")

                # Trigger newer move -> starts 150 ms debounce
                page.fill("#v1-1d-voltage", v_new)
                page.dispatch_event("#v1-1d-voltage", "input")

                # Release stale HTTP 500/400 INSIDE debounce window
                page.evaluate(
                    """([st, code]) => {
                      const held = window.__heldRequests.shift();
                      held.resolve(new Response(JSON.stringify({ error: { code, message: 'stale fault' }, request_id: held.bodyObj.request_id }), {
                        status: st,
                        headers: { 'Content-Type': 'application/json' }
                      }));
                    }""",
                    [err_status, err_code],
                )
                page.wait_for_timeout(30)
                self.assertEqual(page.evaluate("() => window.__v1SolverUI.getState().solveState"), "pending")
                self.assertTrue(page.locator("#v1-error-banner").is_hidden())

                # Wait for newer solve to succeed cleanly
                self._wait_solve_state(page, "ready")
                self.assertTrue(page.locator("#v1-error-banner").is_hidden())
                expected_e = float(v_new) / 0.01
                actual_v = page.evaluate("() => window.__v1SolverUI.getState().lastRenderedResponse.electric_field_v_per_m")
                self.assertAlmostEqual(actual_v, expected_e, delta=1e-6)

            self.assertEqual(errors, [], f"Unexpected page errors: {errors}")
        finally:
            ctx.close()

    def test_current_http_errors_network_rejection_and_malformed_json_never_stuck_pending(self):
        """Section 6.1: current 400/500/504, network rejection, and invalid JSON transition UI cleanly to error banner."""
        url = f"http://127.0.0.1:{self.live_port}/index.html"
        ctx, page, errors = self._open_page(url)
        try:
            page.click("#tab-btn-solver")
            page.click("#v1-mode-1d")
            self._wait_solve_state(page, "ready")

            fault_cases = [
                ("http_400", 400, '{"error":{"code":"INVALID_SCHEMA","message":"bad input"},"request_id":9}', "1100"),
                ("http_500", 500, '{"error":{"code":"WORKER_CRASHED","message":"worker crash"},"request_id":10}', "1200"),
                ("http_504", 504, '{"error":{"code":"SOLVE_DEADLINE_EXCEEDED","message":"timeout"},"request_id":11}', "1300"),
                ("bad_json", 200, "{not valid json!!!", "1400"),
                ("bad_identity", 200, '{"request_id":999999,"input_fingerprint":"0000000000000000000000000000000000000000000000000000000000000000","model_id":"parallel_plate_1d"}', "1600"),
                ("net_reject", -1, "", "1500"),
            ]

            for label, status, body, volt in fault_cases:
                def _make_handler(st, bd):
                    def _handler(route):
                        if st == -1:
                            route.abort("failed")
                        else:
                            route.fulfill(status=st, content_type="application/json", body=bd)
                    return _handler

                handler = _make_handler(status, body)
                page.route("**/api/v1/solve", handler)
                page.fill("#v1-1d-voltage", volt)
                page.dispatch_event("#v1-1d-voltage", "input")
                self._wait_solve_state(page, "error")

                self.assertTrue(page.locator("#v1-error-banner").is_visible(), f"Error banner hidden for {label}")
                self.assertEqual(page.locator("#v1-1d-e-field").inner_text(), "—")
                page.unroute("**/api/v1/solve", handler)

            # Confirm recovery on next valid live request
            page.fill("#v1-1d-voltage", "5000")
            page.dispatch_event("#v1-1d-voltage", "input")
            self._wait_solve_state(page, "ready")
            self.assertTrue(page.locator("#v1-error-banner").is_hidden())
            self.assertEqual(errors, [], f"Unexpected page errors: {errors}")
        finally:
            ctx.close()

    def test_rapid_a_to_b_to_a_mode_switch_and_chapter5_in_flight_cancellation(self):
        """Section 6.1: rapid A->B->A re-entry and Chapter 5 scalar-wave toggle while 2D solve is in flight."""
        url = f"http://127.0.0.1:{self.live_port}/index.html"
        ctx, page, errors = self._open_page(url)
        try:
            page.click("#tab-btn-solver")

            # Intercept first 2D solve to hold it in flight
            page.evaluate("""() => {
              window.__origFetch = window.fetch.bind(window);
              window.__held = [];
              window.__holdNext2D = true;
              window.fetch = function(input, init) {
                const urlStr = typeof input === 'string' ? input : input.url;
                if (urlStr.includes('/api/v1/solve') && window.__holdNext2D) {
                  const body = JSON.parse(init.body);
                  if (body.mode === 'grounded_box_2d') {
                    window.__holdNext2D = false;
                    return new Promise((resolve, reject) => {
                      window.__held.push({ body, resolve, reject });
                    });
                  }
                }
                return window.__origFetch(input, init);
              };
            }""")

            # Rapid A (2D) -> B (1D) -> A (2D) while first A is held in flight
            page.click("#v1-mode-2d")
            page.wait_for_function("() => window.__held.length === 1")
            first_req_id = page.evaluate("() => window.__held[0].body.request_id")

            page.click("#v1-mode-1d")
            page.click("#v1-mode-2d")
            self._wait_solve_state(page, "ready")
            second_req_id = page.evaluate("() => window.__v1SolverUI.getState().latestDispatchedRequestId")
            self.assertGreater(second_req_id, first_req_id)

            # Resolve stale first A with a poisoned error -> must be ignored because gen/reqId changed!
            page.evaluate("""() => {
              const h = window.__held.shift();
              h.resolve(new Response(JSON.stringify({ error: { code: 'STALE_A1', message: 'stale' } }), {
                status: 500,
                headers: { 'Content-Type': 'application/json' }
              }));
            }""")
            page.wait_for_timeout(50)
            self.assertEqual(page.evaluate("() => window.__v1SolverUI.getState().solveState"), "ready")
            self.assertTrue(page.locator("#v1-error-banner").is_hidden())

            # Now hold a 2D solve in flight and enter Chapter 5 scalar wave contrast view
            page.evaluate("() => { window.__holdNext2D = true; }")
            page.select_option("#v1-2d-preset", "bipolar_hv_80mm_bench")
            page.wait_for_function("() => window.__held.length === 1")

            # Jump to Chapter 5 and toggle Mathematical Scalar Wave Toy View while 2D solve is in flight
            page.click("button.chapter-step-btn[data-chapter='4']")
            page.click("#btn-toggle-wave-contrast")
            page.wait_for_timeout(60)

            self.assertTrue(page.locator("#v1-2d-viewport").is_hidden())
            self.assertTrue(page.locator("#scalar-wave-badge").is_visible())
            self.assertTrue(page.evaluate("() => window.__explorer.scalarWaveGroup.visible"))
            self.assertFalse(page.evaluate("() => window.__explorer.forceGroup.visible"))

            # Release the held 2D solve -> must be ignored (activeViewContext === "scalar_wave_contrast")
            page.evaluate("""() => {
              const h = window.__held.shift();
              h.resolve(new Response(JSON.stringify({ error: { code: 'STALE_CH5', message: 'stale' } }), {
                status: 500,
                headers: { 'Content-Type': 'application/json' }
              }));
            }""")
            page.wait_for_timeout(50)
            self.assertTrue(page.locator("#v1-2d-viewport").is_hidden())
            self.assertTrue(page.locator("#scalar-wave-badge").is_visible())
            self.assertTrue(page.locator("#v1-error-banner").is_hidden())
            self.assertEqual(errors, [], f"Unexpected page errors: {errors}")
        finally:
            ctx.close()

    def test_true_offline_dual_transport_file_protocol_and_static_http(self):
        """Section 6.1: both file://.../explorer/index.html and static http.server enforce truthful offline snapshot fallback."""
        file_url = (EXPLORER_DIR / "index.html").resolve().as_uri()
        static_url = f"http://127.0.0.1:{self.static_port}/index.html"

        for label, url in (("file://", file_url), ("static_http", static_url)):
            ctx, page, errors = self._open_page(url)
            try:
                page.click("#tab-btn-solver")
                page.click("#v1-mode-1d")
                self._wait_solve_state(page, "ready")

                # Both transports must be in OFFLINE mode with SOLVER BRIDGE OFFLINE banner
                self.assertEqual(
                    page.evaluate("() => window.__v1SolverUI.getState().transportMode"),
                    "offline",
                    f"Expected offline mode for {label}",
                )
                self.assertTrue(page.locator("#v1-offline-banner").is_visible(), f"Offline banner hidden for {label}")
                self.assertIn("SOLVER BRIDGE OFFLINE", page.locator("#v1-offline-banner").inner_text())

                # Exact 0 V offline 1D parity
                page.fill("#v1-1d-voltage", "0")
                page.dispatch_event("#v1-1d-voltage", "input")
                self._wait_solve_state(page, "ready")
                self.assertEqual(page.locator("#v1-1d-pressure").inner_text(), "0.0 Pa")
                self.assertEqual(page.locator("#v1-1d-net-force").inner_text(), "0.0 N (exact cancellation)")

                # Switch to 2D -> arbitrary 2D sliders MUST be disabled; frozen snapshot parameters & provenance rendered
                page.click("#v1-mode-2d")
                self._wait_solve_state(page, "ready")
                self.assertTrue(page.locator("#v1-2d-viewport").is_visible())
                self.assertFalse(page.evaluate("() => window.__explorer.forceGroup.visible"))
                for locked_id in ("#v1-2d-vleft", "#v1-2d-vright", "#v1-2d-gap", "#v1-2d-cy", "#v1-2d-probe-x", "#v1-2d-probe-y"):
                    self.assertTrue(page.locator(locked_id).is_disabled(), f"{locked_id} not locked offline under {label}")

                # Switch preset to asymmetric_hv_80mm_bench at n=41 -> honest UNBALANCED_EXCEEDS_TOLERANCE offline
                page.select_option("#v1-2d-preset", "asymmetric_hv_80mm_bench")
                self._wait_solve_state(page, "ready")
                page.select_option("#v1-2d-grid-n", "41")
                self._wait_solve_state(page, "ready")
                self.assertIn("FROZEN SNAPSHOT", page.locator("#v1-2d-rendered-params-text").inner_text())
                self.assertIn("UNBALANCED_EXCEEDS_TOLERANCE", page.locator("#v1-2d-closure-status-label").inner_text())
                self.assertIn("NOT MEASURED / NOT ESTABLISHED", page.locator("#v1-prov-thrust").inner_text())

                # Offline study hydration
                page.click("#v1-2d-btn-study")
                self._wait_solve_state(page, "ready")
                self.assertEqual(page.locator("#v1-2d-study-rows tr").count(), 3)
                self.assertIn("NOT_COMPUTED_NONUNIFORM_H_RATIO", page.locator("#v1-2d-study-order-status").inner_text())

                self.assertEqual(errors, [], f"Unexpected page errors under {label}: {errors}")
            finally:
                ctx.close()

    def test_mobile_375_and_390_v1_solver_zero_overflow_and_iceberg_preservation(self):
        """Section 6.1: 375px and 390px mobile zero horizontal overflow across 1D/2D V1 modes and preserved 6 Iceberg chapters."""
        url = f"http://127.0.0.1:{self.live_port}/index.html"
        for vp in ({"width": 375, "height": 667}, {"width": 390, "height": 844}):
            ctx, page, errors = self._open_page(url, viewport=vp)
            try:
                # 1. Verify mobile Guided Tour still exposes all 6 Iceberg chapters cleanly
                self.assertEqual(page.locator(".chapter-step-btn").count(), 6)

                # 2. Switch to Controls tab -> V1 Solver -> 1D & 2D modes
                page.click("#mobile-tab-controls")
                page.click("#tab-btn-solver")
                page.click("#v1-mode-1d")
                self._wait_solve_state(page, "ready")
                overflow_1d = page.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
                self.assertLessEqual(overflow_1d, 0, f"Horizontal overflow ({overflow_1d}px) in 1D mode at {vp}")

                page.click("#v1-mode-2d")
                self._wait_solve_state(page, "ready")
                overflow_2d = page.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
                self.assertLessEqual(overflow_2d, 0, f"Horizontal overflow ({overflow_2d}px) in 2D mode at {vp}")

                self.assertEqual(errors, [], f"Mobile errors at {vp}: {errors}")
            finally:
                ctx.close()

    def test_b3_r1_f1_documented_run_v1_solver_subprocess_live_arbitrary_2d(self):
        """B3-R1-F1 regression: subprocess launch of documented `python run_v1_solver.py` exposes live editable 2D solver."""
        launcher = REPO_ROOT / "run_v1_solver.py"
        self.assertTrue(launcher.exists(), "Missing documented live V1-B launcher run_v1_solver.py")

        # Verify launcher preserves zero direct physics/P2 imports
        launcher_src = launcher.read_text(encoding="utf-8")
        for forbidden in ("electrostatics_baseline", "electrostatics_numerics", "scipy", "p2_"):
            self.assertNotIn(forbidden, launcher_src)

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]

        env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
        env["PYTHONPATH"] = ""

        with tempfile.TemporaryDirectory() as tmp_cwd:
            proc = subprocess.Popen(
                [sys.executable, str(launcher), "--host", "127.0.0.1", "--port", str(port), "--no-browser"],
                cwd=tmp_cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                # Wait for HTTP server socket to accept connections
                deadline = time.monotonic() + 8.0
                ready = False
                while time.monotonic() < deadline:
                    if proc.poll() is not None:
                        out_err = (proc.stderr.read() if proc.stderr else b"").decode("utf-8", errors="replace")
                        self.fail(f"run_v1_solver.py exited prematurely with {proc.returncode}: {out_err}")
                    try:
                        with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                            ready = True
                            break
                    except OSError:
                        time.sleep(0.05)
                self.assertTrue(ready, "run_v1_solver.py did not bind within 8 seconds")

                url = f"http://127.0.0.1:{port}/index.html"
                ctx, page, errors = self._open_page(url)
                try:
                    page.click("#tab-btn-solver")
                    page.click("#v1-mode-2d")
                    self._wait_solve_state(page, "ready")

                    state = page.evaluate("() => window.__v1SolverUI.getState()")
                    self.assertEqual(state["transportMode"], "live")
                    self.assertTrue(page.locator("#v1-offline-banner").is_hidden())
                    for editable_id in ("#v1-2d-vleft", "#v1-2d-vright", "#v1-2d-gap", "#v1-2d-cy", "#v1-2d-probe-x", "#v1-2d-probe-y"):
                        self.assertTrue(page.locator(editable_id).is_enabled(), f"{editable_id} must be editable under run_v1_solver.py")

                    # Apply non-preset arbitrary 2D voltage (12500 V) and confirm live solve succeeds
                    page.fill("#v1-2d-vleft", "12500")
                    page.dispatch_event("#v1-2d-vleft", "input")
                    self._wait_solve_state(page, "ready")
                    rendered_txt = page.locator("#v1-2d-rendered-params-text").inner_text()
                    self.assertIn("VL=12500 V", rendered_txt)
                    self.assertIn("[LIVE SOLVE]", rendered_txt)
                    self.assertEqual(errors, [], f"Unexpected page errors under run_v1_solver.py: {errors}")
                finally:
                    ctx.close()
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=5.0)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5.0)
                if proc.stdout:
                    proc.stdout.close()
                if proc.stderr:
                    proc.stderr.close()

    def test_b3_r1_f2_ready_state_chapter_and_explore_freely_invalidation_and_reentry(self):
        """B3-R1-F2 regression: ready-state 2D -> chapter navigation and Explore Freely always invalidate, hide 2D overlay, and allow clean re-entry."""
        url = f"http://127.0.0.1:{self.live_port}/index.html"
        ctx, page, errors = self._open_page(url)
        try:
            # 1. Reach READY state in 2D mode
            page.click("#tab-btn-solver")
            page.click("#v1-mode-2d")
            self._wait_solve_state(page, "ready")
            gen_before_ch = page.evaluate("() => window.__v1SolverUI.getState().clientStateGeneration")
            self.assertTrue(page.locator("#v1-2d-viewport").is_visible())

            # 2. Navigate to Chapter 3 while in READY state -> must increment generation, clear readouts, hide 2D viewport, restore 3D forces
            page.click("button.chapter-step-btn[data-chapter='2']")
            page.wait_for_timeout(80)
            st_after_ch = page.evaluate("() => window.__v1SolverUI.getState()")
            self.assertGreater(st_after_ch["clientStateGeneration"], gen_before_ch)
            self.assertEqual(st_after_ch["activeModelMode"], "schematic_3d")
            self.assertEqual(st_after_ch["activeViewContext"], "3d_schematic")
            self.assertEqual(st_after_ch["solveState"], "idle")
            self.assertIsNone(st_after_ch["lastRenderedResponse"])
            self.assertTrue(page.locator("#v1-2d-viewport").is_hidden())
            self.assertEqual(page.locator("#v1-2d-fx-left").inner_text(), "—")
            self.assertTrue(page.evaluate("() => window.__explorer.forceGroup.visible"))

            # 3. Clean re-entry into 2D mode -> READY
            page.click("#tab-btn-solver")
            page.click("#v1-mode-2d")
            self._wait_solve_state(page, "ready")
            gen_before_free = page.evaluate("() => window.__v1SolverUI.getState().clientStateGeneration")
            self.assertTrue(page.locator("#v1-2d-viewport").is_visible())
            self.assertFalse(page.evaluate("() => window.__explorer.forceGroup.visible"))

            # 4. Enter Explore Freely while in READY state -> must increment generation, clear readouts, hide 2D viewport
            page.click("#guide-btn-free")
            page.wait_for_timeout(80)
            st_after_free = page.evaluate("() => window.__v1SolverUI.getState()")
            self.assertGreater(st_after_free["clientStateGeneration"], gen_before_free)
            self.assertEqual(st_after_free["activeModelMode"], "schematic_3d")
            self.assertEqual(st_after_free["activeViewContext"], "3d_schematic")
            self.assertEqual(st_after_free["solveState"], "idle")
            self.assertIsNone(st_after_free["lastRenderedResponse"])
            self.assertTrue(page.locator("#v1-2d-viewport").is_hidden())
            self.assertEqual(page.locator("#v1-2d-fx-left").inner_text(), "—")

            # 5. Clean re-entry into 1D mode from Explore Freely -> READY
            page.click("#tab-btn-solver")
            page.click("#v1-mode-1d")
            self._wait_solve_state(page, "ready")
            self.assertEqual(page.evaluate("() => window.__v1SolverUI.getState().activeModelMode"), "parallel_plate_1d")
            self.assertNotEqual(page.locator("#v1-1d-e-field").inner_text(), "—")

            self.assertEqual(errors, [], f"Unexpected page errors: {errors}")
        finally:
            ctx.close()

    def test_b3_r1_f3_chapter5_wave_exit_direct_chapter_and_explore_freely_no_idle_hang(self):
        """B3-R1-F3 regression: exiting Chapter 5 wave mode via direct toggle, chapter switch, or Explore Freely never self-cancels into permanent idle."""
        url = f"http://127.0.0.1:{self.live_port}/index.html"
        ctx, page, errors = self._open_page(url)
        try:
            # Instrument fetch counter to detect any stray/self-cancelled /api/v1/solve calls
            page.evaluate("""() => {
              window.__origFetchF3 = window.fetch.bind(window);
              window.__solveFetchCount = 0;
              window.__heldF3 = [];
              window.__holdNextF3 = false;
              window.fetch = function(input, init) {
                const urlStr = typeof input === 'string' ? input : input.url;
                if (urlStr.includes('/api/v1/solve')) {
                  window.__solveFetchCount += 1;
                  if (window.__holdNextF3) {
                    window.__holdNextF3 = false;
                    return new Promise((resolve, reject) => {
                      window.__heldF3.push({ resolve, reject });
                    });
                  }
                }
                return window.__origFetchF3(input, init);
              };
            }""")

            # Scenario A: On Chapter 5, hold an in-flight 2D solve, toggle wave ON (cancels old solve), then toggle wave OFF directly -> single recovery solve reaches READY
            page.click("button.chapter-step-btn[data-chapter='4']")
            page.click("#tab-btn-solver")
            page.evaluate("() => { window.__holdNextF3 = true; }")
            page.click("#v1-mode-2d")
            page.wait_for_function("() => window.__heldF3.length === 1")

            page.click("#btn-toggle-wave-contrast")
            page.wait_for_timeout(50)
            self.assertTrue(page.locator("#scalar-wave-badge").is_visible())
            self.assertTrue(page.locator("#v1-2d-viewport").is_hidden())

            # Release stale held solve as error -> must be ignored
            page.evaluate("""() => {
              const h = window.__heldF3.shift();
              h.resolve(new Response(JSON.stringify({ error: { code: 'STALE_WAVE', message: 'stale' } }), {
                status: 500, headers: { 'Content-Type': 'application/json' }
              }));
            }""")

            # Toggle wave OFF directly on Chapter 5 -> must dispatch exactly 1 fresh recovery solve and reach READY
            page.evaluate("() => { window.__solveFetchCount = 0; }")
            page.click("#btn-toggle-wave-contrast")
            self._wait_solve_state(page, "ready")
            self.assertEqual(page.evaluate("() => window.__solveFetchCount"), 1)
            self.assertTrue(page.locator("#scalar-wave-badge").is_hidden())
            self.assertTrue(page.locator("#v1-2d-viewport").is_visible())
            self.assertNotEqual(page.locator("#v1-2d-fx-left").inner_text(), "—")

            # Scenario B: Chapter 5 wave ON (from active 2D) -> navigate to Chapter 3 -> ZERO stray cancelled solves, clean 3D view, clean 2D re-entry
            page.click("#btn-toggle-wave-contrast")
            page.wait_for_timeout(40)
            self.assertTrue(page.locator("#scalar-wave-badge").is_visible())

            page.evaluate("() => { window.__solveFetchCount = 0; }")
            page.click("button.chapter-step-btn[data-chapter='2']")
            page.wait_for_timeout(80)
            self.assertEqual(page.evaluate("() => window.__solveFetchCount"), 0, "Wave->Chapter must not dispatch a self-cancelled solve")
            self.assertTrue(page.locator("#scalar-wave-badge").is_hidden())
            self.assertTrue(page.locator("#v1-2d-viewport").is_hidden())
            self.assertTrue(page.evaluate("() => window.__explorer.forceGroup.visible"))
            self.assertEqual(page.evaluate("() => window.__v1SolverUI.getState().activeModelMode"), "schematic_3d")

            # Re-enter 2D cleanly after Wave->Chapter
            page.click("#tab-btn-solver")
            page.click("#v1-mode-2d")
            self._wait_solve_state(page, "ready")
            self.assertTrue(page.locator("#v1-2d-viewport").is_visible())

            # Scenario C: Chapter 5 wave ON (from active 2D) -> Explore Freely -> ZERO stray cancelled solves, clean 3D sandbox, clean 2D re-entry
            page.click("button.chapter-step-btn[data-chapter='4']")
            page.click("#tab-btn-solver")
            page.click("#v1-mode-2d")
            self._wait_solve_state(page, "ready")
            page.click("#btn-toggle-wave-contrast")
            page.wait_for_timeout(40)
            self.assertTrue(page.locator("#scalar-wave-badge").is_visible())

            page.evaluate("() => { window.__solveFetchCount = 0; }")
            page.click("#guide-btn-free")
            page.wait_for_timeout(80)
            self.assertEqual(page.evaluate("() => window.__solveFetchCount"), 0, "Wave->Explore Freely must not dispatch a self-cancelled solve")
            self.assertTrue(page.locator("#scalar-wave-badge").is_hidden())
            self.assertTrue(page.locator("#v1-2d-viewport").is_hidden())
            self.assertEqual(page.evaluate("() => window.__v1SolverUI.getState().activeModelMode"), "schematic_3d")

            # Re-enter 2D cleanly after Wave->Explore Freely
            page.click("#tab-btn-solver")
            page.click("#v1-mode-2d")
            self._wait_solve_state(page, "ready")
            self.assertTrue(page.locator("#v1-2d-viewport").is_visible())
            self.assertNotEqual(page.locator("#v1-2d-fx-left").inner_text(), "—")

            self.assertEqual(errors, [], f"Unexpected page errors: {errors}")
        finally:
            ctx.close()


if __name__ == "__main__":
    unittest.main()
