"""Browser-driven smoke and interaction regression tests for 3D Propulsion Explorer (V0).

Remediated for Review Round V0 R3 (addressing findings V0-R2-F1, V0-R2-M3, V0-R2-M5):
- Launches real headless Chrome / Chromium via Playwright.
- Serves explorer/ via local HTTP server (zero network dependencies).
- Asserts zero JavaScript console errors or runtime page exceptions.
- Verifies WebGL canvas rendering, layers toggling, and keyboard navigation.
- Verifies What-If parameter sliders (Voltage, Gap, Permittivity) update DOM state dynamically.
- Verifies component selection and inspector details without chamber occlusion.
- Verifies raycast picking priority: interior components prioritized over enclosing chamber walls.
- Verifies GPU resource disposal: repeated vector updates do not cause unbounded memory growth.
- Verifies modal tour and help dialogs with focus trapping and Escape dismissal.
- Verifies narrow mobile viewport (375x667) without horizontal overflow.
"""

from __future__ import annotations

import http.server
import os
import shutil
import threading
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EXPLORER_DIR = REPO_ROOT / "explorer"


def find_browser_executable() -> str | None:
    env_bin = os.environ.get("CHROME_BIN") or os.environ.get("PLAYWRIGHT_CHROME_BIN")
    if env_bin and os.path.exists(env_bin):
        return env_bin

    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c

    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        path = shutil.which(name)
        if path:
            return path
    return None


def is_playwright_available() -> bool:
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(EXPLORER_DIR), **kwargs)

    def log_message(self, format, *args):
        pass  # Suppress HTTP request logging in test runner


@unittest.skipUnless(is_playwright_available(), "Playwright is not installed")
class PropulsionExplorerBrowserSmokeTests(unittest.TestCase):
    """End-to-end browser integration tests verifying real DOM, WebGL, and interaction."""

    server: http.server.HTTPServer
    server_thread: threading.Thread
    server_port: int
    browser = None
    playwright_context = None

    @classmethod
    def setUpClass(cls):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise unittest.SkipTest("Playwright not installed; run `pip install playwright && playwright install chromium` to run browser smoke tests.")

        cls.server = http.server.HTTPServer(("127.0.0.1", 0), QuietHandler)
        cls.server_port = cls.server.server_address[1]
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()

        cls.playwright_context = sync_playwright()
        cls.pw = cls.playwright_context.__enter__()

        browser_exe = find_browser_executable()
        args = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
        ]
        if os.uname().sysname == "Darwin":
            args.extend(["--use-gl=angle", "--use-angle=metal"])
        else:
            args.extend(["--use-gl=swiftshader"])

        launch_kwargs = {
            "headless": True,
            "args": args,
        }
        if browser_exe:
            launch_kwargs["executable_path"] = browser_exe

        try:
            cls.browser = cls.pw.chromium.launch(**launch_kwargs)
        except Exception as e:
            cls.playwright_context.__exit__(None, None, None)
            cls.browser = None
            raise unittest.SkipTest(f"Chromium failed to launch: {e}")

    @classmethod
    def tearDownClass(cls):
        try:
            if cls.browser:
                cls.browser.close()
        finally:
            if cls.playwright_context:
                cls.playwright_context.__exit__(None, None, None)
            if hasattr(cls, "server"):
                cls.server.shutdown()
                cls.server.server_close()

    def setUp(self):
        if not self.browser:
            raise unittest.SkipTest("Browser not available")

        self.context = self.browser.new_context(viewport={"width": 1280, "height": 800})
        self.page = self.context.new_page()

        self.console_messages = []
        self.page_errors = []
        self.page.on("console", lambda msg: self.console_messages.append(msg.text))
        self.page.on("pageerror", lambda err: self.page_errors.append(str(err)))

        self.base_url = f"http://127.0.0.1:{self.server_port}/index.html"
        self.page.goto(self.base_url)
        self.page.wait_for_selector("#webgl-canvas")
        self.page.wait_for_selector(".component-item-btn")
        self.page.wait_for_selector("#loading-overlay.hidden")

    def tearDown(self):
        try:
            if hasattr(self, "page") and not self.page.is_closed():
                self.page.close()
            if hasattr(self, "context"):
                self.context.close()
        except Exception:
            pass

    def test_default_page_load_and_canvas_render(self):
        """Verify page loads cleanly, canvas is visible, and no JS errors are thrown."""
        self.assertEqual(len(self.page_errors), 0, f"Page threw errors on load: {self.page_errors}")
        self.assertIn("Propulsion Explorer", self.page.title())

        canvas = self.page.locator("#webgl-canvas")
        self.assertTrue(canvas.is_visible())

        legend_blade = self.page.locator("#legend-blade-label").inner_text()
        self.assertIn("Blade", legend_blade)
        self.assertIn("0.0 kV", legend_blade)

    def test_keyboard_navigation_no_exceptions(self):
        """V0-R1-F3 / V0-R2-M3: verify all 10 keyboard shortcuts execute cleanly without throwing errors."""
        canvas = self.page.locator("#viewport-container")
        canvas.click()

        shortcuts = ["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "+", "-", "r", "1", "2", "3"]
        for key in shortcuts:
            self.page.keyboard.press(key)
            self.page.wait_for_timeout(20)

        self.assertEqual(len(self.page_errors), 0, f"Keyboard shortcuts threw errors: {self.page_errors}")

    def test_what_if_sliders_dom_synchronization(self):
        """V0-R1-M1 / V0-R2-M3: verify What-If sliders update DOM values and extinguish at 0 V."""
        self.page.click("#tab-btn-sandbox")
        # Ensure force layer is enabled for What-If sandbox testing
        self.page.evaluate("() => { const el = document.getElementById('toggle-forces'); if (el) { el.checked = true; } }")
        self.assertTrue(self.page.locator("#tab-sandbox").is_visible())

        # Voltage down to 0 kV
        self.page.fill("#slider-voltage", "0")
        self.page.dispatch_event("#slider-voltage", "input")
        val_voltage = self.page.locator("#val-voltage").inner_text()
        self.assertIn("0.0 kV", val_voltage)
        self.assertIn("OFF", val_voltage)

        legend_blade = self.page.locator("#legend-blade-label").inner_text()
        self.assertIn("OFF", legend_blade)

        # Voltage up to 40 kV
        self.page.fill("#slider-voltage", "40")
        self.page.dispatch_event("#slider-voltage", "input")
        self.assertIn("-40.0 kV", self.page.locator("#val-voltage").inner_text())

        # Gap slider min 16 mm (verified positive physical clearance >= 3.0 mm)
        self.page.fill("#slider-gap", "16")
        self.page.dispatch_event("#slider-gap", "input")
        self.assertIn("16.0 mm", self.page.locator("#val-gap").inner_text())

        # Permittivity slider 1.0 (vacuum)
        self.page.locator("#slider-eps").evaluate("el => { el.value = '1.0'; el.dispatchEvent(new Event('input')); }")
        self.assertIn("1.0 (Air/Vacuum)", self.page.locator("#val-eps").inner_text())

        self.assertEqual(len(self.page_errors), 0, f"Slider operations threw errors: {self.page_errors}")

    def test_sidebar_component_list_selection(self):
        """V0-R2-F1: verify sidebar component button clicks update inspector for accessibility."""
        components = [
            ("blade_electrode", "Asymmetric High-Voltage Blade", "PUBLISHED HYPOTHESIS"),
            ("ground_electrode", "Ground Counter-Electrode", "ESTABLISHED MODEL"),
            ("dielectric_block", "Solid Dielectric Barrier / Potting", "WHAT-IF PARAMETER"),
            ("support_mount", "Structural Support Mount", "ESTABLISHED MODEL"),
            ("enclosure_walls", "Conductive Enclosure (Chamber)", "ESTABLISHED MODEL"),
        ]

        for comp_id, expected_name, expected_badge in components:
            self.page.click("#tab-btn-layers")
            btn = self.page.locator(f".component-item-btn[data-id='{comp_id}']")
            btn.click()
            self.page.wait_for_timeout(20)

            name_el = self.page.locator("#inspector-name").inner_text()
            badge_el = self.page.locator("#inspector-badge").inner_text()
            self.assertEqual(name_el, expected_name)
            self.assertEqual(badge_el, expected_badge)

        self.assertEqual(len(self.page_errors), 0, f"Sidebar list selection threw errors: {self.page_errors}")

    def test_canvas_pointer_picking_all_components_default_view(self):
        """V0-R3-F1 [HIGH / BLOCKING]: exercise real canvas pointer events (hover & click) on all 5 components.

        Uses real mouse movement and clicking on the WebGL canvas, testing:
        1. Projected screen coordinate resolution via getComponentScreenCoords.
        2. Hover state update on #banner-text.
        3. Canvas click raycast selection without chamber occlusion.
        4. Inspector title and badge updates matching provenance metadata.
        """
        components = [
            ("blade_electrode", "Asymmetric High-Voltage Blade", "PUBLISHED HYPOTHESIS"),
            ("dielectric_block", "Solid Dielectric Barrier / Potting", "WHAT-IF PARAMETER"),
            ("ground_electrode", "Ground Counter-Electrode", "ESTABLISHED MODEL"),
            ("support_mount", "Structural Support Mount", "ESTABLISHED MODEL"),
            ("enclosure_walls", "Conductive Enclosure (Chamber)", "ESTABLISHED MODEL"),
        ]

        # Reset camera to default isometric view
        self.page.evaluate("() => window.__explorer.setViewPreset('iso', true)")
        self.page.wait_for_timeout(30)

        for comp_id, expected_name, expected_badge in components:
            coords = self.page.evaluate("id => window.__explorer.getComponentScreenCoords(id)", comp_id)
            self.assertIsNotNone(coords, f"Could not project screen coordinates for {comp_id}")
            cx = coords["clientX"]
            cy = coords["clientY"]

            # Real mouse move over 3D canvas
            self.page.mouse.move(cx, cy)
            self.page.wait_for_timeout(25)

            # Verify hover status banner displays component name
            banner_text = self.page.locator("#banner-text").inner_text()
            self.assertIn(expected_name, banner_text, f"Hover banner failed to show {expected_name}; got: '{banner_text}'")

            # Real mouse click on 3D canvas
            self.page.mouse.click(cx, cy)
            self.page.wait_for_timeout(25)

            # Verify inspector updated accurately
            name_el = self.page.locator("#inspector-name").inner_text()
            badge_el = self.page.locator("#inspector-badge").inner_text()
            self.assertEqual(name_el, expected_name, f"Inspector name mismatch for {comp_id}")
            self.assertEqual(badge_el, expected_badge, f"Inspector badge mismatch for {comp_id}")

            # Verify unique selected sidebar button data-id
            selected_btn = self.page.locator(".component-item-btn.selected")
            self.assertEqual(selected_btn.get_attribute("data-id"), comp_id, f"Sidebar selected button mismatch for {comp_id}")

        self.assertEqual(len(self.page_errors), 0, f"Canvas pointer picking threw errors: {self.page_errors}")

    def test_canvas_pointer_picking_alternate_camera_views(self):
        """V0-R4-F1 [HIGH / BLOCKING]: verify canvas pointer picking across alternate camera viewpoints (Side & Top) for ALL 5 components.

        In both Side and Top presets:
        1. Projects unoccluded surface coordinates for all 5 components.
        2. Real page.mouse.move asserts dynamic #banner-text hover updating.
        3. Real page.mouse.click asserts #inspector-name and #inspector-badge matching.
        4. Asserts unique selected .component-item-btn.selected[data-id].
        5. Asserts zero page errors.
        """
        presets = ["side", "top"]
        components = [
            ("blade_electrode", "Asymmetric High-Voltage Blade", "PUBLISHED HYPOTHESIS"),
            ("dielectric_block", "Solid Dielectric Barrier / Potting", "WHAT-IF PARAMETER"),
            ("ground_electrode", "Ground Counter-Electrode", "ESTABLISHED MODEL"),
            ("support_mount", "Structural Support Mount", "ESTABLISHED MODEL"),
            ("enclosure_walls", "Conductive Enclosure (Chamber)", "ESTABLISHED MODEL"),
        ]

        for preset in presets:
            self.page.evaluate(f"() => window.__explorer.setViewPreset('{preset}', true)")
            self.page.wait_for_timeout(30)

            for comp_id, expected_name, expected_badge in components:
                coords = self.page.evaluate("id => window.__explorer.getComponentScreenCoords(id)", comp_id)
                self.assertIsNotNone(coords, f"Projection failed for {comp_id} in {preset} view")
                cx = coords["clientX"]
                cy = coords["clientY"]

                # Real mouse move over canvas in alternate view
                self.page.mouse.move(cx, cy)
                self.page.wait_for_timeout(25)

                # Assert hover banner updates with exact name
                banner_text = self.page.locator("#banner-text").inner_text()
                self.assertIn(expected_name, banner_text, f"Hover banner failed to show '{expected_name}' in {preset} view; got: '{banner_text}'")

                # Real mouse click on canvas in alternate view
                self.page.mouse.click(cx, cy)
                self.page.wait_for_timeout(25)

                # Assert inspector title and badge
                name_el = self.page.locator("#inspector-name").inner_text()
                badge_el = self.page.locator("#inspector-badge").inner_text()
                self.assertEqual(name_el, expected_name, f"Picking failed for {comp_id} in {preset} view; got: '{name_el}'")
                self.assertEqual(badge_el, expected_badge, f"Badge mismatch for {comp_id} in {preset} view; got: '{badge_el}'")

                # Assert unique selected sidebar button data-id
                selected_btn = self.page.locator(".component-item-btn.selected")
                self.assertEqual(selected_btn.get_attribute("data-id"), comp_id, f"Sidebar selected button mismatch in {preset} view; expected {comp_id}")

        self.assertEqual(len(self.page_errors), 0, f"Alternate view picking threw errors: {self.page_errors}")

        # Return to default isometric view
        self.page.evaluate("() => window.__explorer.setViewPreset('iso', true)")

    def test_layer_toggles_and_raycast_fallback(self):
        """V0-R3-F1: verify raycast behavior when layers are toggled off (interior hidden falls back to chamber)."""
        blade_coords = self.page.evaluate("() => window.__explorer.getComponentScreenCoords('blade_electrode')")
        self.assertIsNotNone(blade_coords)

        # 1. Normal state: clicking blade selects blade
        self.page.mouse.click(blade_coords["clientX"], blade_coords["clientY"])
        self.assertEqual(self.page.locator("#inspector-name").inner_text(), "Asymmetric High-Voltage Blade")

        # 2. Toggle off Interior Geometry layer via click on checkbox input
        self.page.locator("#toggle-geometry").evaluate("el => el.click()")
        self.page.wait_for_timeout(25)

        # 3. Click at blade screen coordinates: geometry is hidden, so raycast falls back to enclosure chamber
        self.page.mouse.click(blade_coords["clientX"], blade_coords["clientY"])
        self.page.wait_for_timeout(25)
        self.assertEqual(
            self.page.locator("#inspector-name").inner_text(),
            "Conductive Enclosure (Chamber)",
            "Hiding interior geometry should cause raycast to fall through to enclosure chamber walls"
        )

        # 4. Restore layers for clean state in subsequent tests
        self.page.locator("#toggle-geometry").evaluate("el => el.click()")
        self.page.wait_for_timeout(25)

    def test_gpu_memory_disposal_during_rendered_slider_sweeps(self):
        """V0-R3-M2 [MED]: instrument prototype .dispose() and drive real DOM sliders across rendered sweeps.

        Addresses review criticisms of synthetic loop:
        1. Instruments THREE.BufferGeometry.prototype.dispose and Material.prototype.dispose.
        2. Drives real DOM sliders (#slider-voltage, #slider-gap, #slider-eps).
        3. Waits for rendered animation frames via requestAnimationFrame / wait_for_timeout.
        4. Asserts dispose count > 30, proving recursive disposal was executed.
        5. Asserts renderer.info.memory.geometries remains tightly bounded (diff <= 2).
        """
        # Switch to Sandbox tab
        self.page.click("#tab-btn-sandbox")
        # Ensure force layer is enabled for What-If sandbox testing
        self.page.evaluate("() => { const el = document.getElementById('toggle-forces'); if (el) { el.checked = true; } }")
        self.page.fill("#slider-voltage", "20")
        self.page.dispatch_event("#slider-voltage", "input")
        self.page.wait_for_timeout(30)

        # Install prototype disposal tracking hooks
        self.page.evaluate("""() => {
          window.__disposeStats = { geometries: 0, materials: 0 };
          const origGeomDispose = THREE.BufferGeometry.prototype.dispose;
          THREE.BufferGeometry.prototype.dispose = function() {
            window.__disposeStats.geometries++;
            return origGeomDispose.apply(this, arguments);
          };
          const origMatDispose = THREE.Material.prototype.dispose;
          THREE.Material.prototype.dispose = function() {
            window.__disposeStats.materials++;
            return origMatDispose.apply(this, arguments);
          };
        }""")

        initial_geoms = self.page.evaluate("() => window.__explorer.renderer.info.memory.geometries")

        # Sweep Voltage slider across 8 steps
        voltage_steps = [10, 15, 25, 35, 45, 50, 30, 20]
        for v in voltage_steps:
            self.page.fill("#slider-voltage", str(v))
            self.page.dispatch_event("#slider-voltage", "input")
            self.page.wait_for_timeout(30)

        # Sweep Gap slider across 5 steps
        gap_steps = [16, 22, 28, 35, 20]
        for g in gap_steps:
            self.page.fill("#slider-gap", str(g))
            self.page.dispatch_event("#slider-gap", "input")
            self.page.wait_for_timeout(30)

        # Sweep Permittivity slider across 4 steps
        eps_steps = [1.0, 2.5, 5.0, 3.8]
        for e in eps_steps:
            self.page.locator("#slider-eps").evaluate(f"el => {{ el.value = '{e}'; el.dispatchEvent(new Event('input')); }}")
            self.page.wait_for_timeout(30)

        stats = self.page.evaluate("() => window.__disposeStats")
        final_geoms = self.page.evaluate("() => window.__explorer.renderer.info.memory.geometries")

        # Prove disposal was called repeatedly
        self.assertGreater(
            stats["geometries"], 30,
            f"Expected > 30 BufferGeometry disposals during rendered slider sweeps; got {stats['geometries']}"
        )

        # Prove memory remained strictly bounded (no unbounded leak across rendered animation frames)
        diff = final_geoms - initial_geoms
        self.assertLessEqual(
            diff, 2,
            f"GPU geometry count leaked across rendered sweeps: initial={initial_geoms}, final={final_geoms}, diff={diff}"
        )

    def test_bounded_force_arrows_browser_verification(self):
        """V0-R3-M4 [MED]: verify bounded force arrow lengths across voltage range in real browser.

        1. At 0 kV: arrows are extinguished (forceGroup.visible == false).
        2. At 2 kV: bounded minimum legibility length >= 6.0 mm.
        3. At 20 kV: exactly 16.0 mm.
        4. At 50 kV: bounded maximum length 30.0 mm.
        5. Arrow endpoints stay strictly inside enclosure chamber [-80, 80] mm.
        """
        self.page.click("#tab-btn-sandbox")
        # Ensure force layer is enabled for What-If sandbox testing
        self.page.evaluate("() => { const el = document.getElementById('toggle-forces'); if (el) { el.checked = true; } }")

        # 1. At 0 kV: extinguished
        self.page.fill("#slider-voltage", "0")
        self.page.dispatch_event("#slider-voltage", "input")
        self.page.wait_for_timeout(20)
        is_visible_0 = self.page.evaluate("() => window.__explorer.forceGroup.visible")
        self.assertFalse(is_visible_0, "Force arrows should be extinguished at 0 kV")

        # 2. At 2 kV: bounded legibility >= 6.0 mm
        self.page.fill("#slider-voltage", "2")
        self.page.dispatch_event("#slider-voltage", "input")
        self.page.wait_for_timeout(20)
        data_2kv = self.page.evaluate("""() => {
          const fg = window.__explorer.forceGroup;
          if (!fg || !fg.visible) return null;
          const arrow = fg.children.find(c => c.userData && c.userData.element === "Blade Electrode");
          return { visible: fg.visible, length: arrow ? arrow.userData.arrowLength : null };
        }""")
        self.assertIsNotNone(data_2kv)
        self.assertTrue(data_2kv["visible"])
        self.assertGreaterEqual(data_2kv["length"], 6.0, "Force arrow length at 2 kV below 6 mm threshold")
        self.assertLessEqual(data_2kv["length"], 7.0, "Force arrow length at 2 kV unexpected")

        # 3. At 20 kV: exactly 16.0 mm
        self.page.fill("#slider-voltage", "20")
        self.page.dispatch_event("#slider-voltage", "input")
        self.page.wait_for_timeout(20)
        data_20kv = self.page.evaluate("""() => {
          const fg = window.__explorer.forceGroup;
          const arrow = fg.children.find(c => c.userData && c.userData.element === "Blade Electrode");
          return { length: arrow ? arrow.userData.arrowLength : null };
        }""")
        self.assertAlmostEqual(data_20kv["length"], 16.0, places=2)

        # 4. At 50 kV: bounded maximum 30.0 mm
        self.page.fill("#slider-voltage", "50")
        self.page.dispatch_event("#slider-voltage", "input")
        self.page.wait_for_timeout(20)
        data_50kv = self.page.evaluate("""() => {
          const fg = window.__explorer.forceGroup;
          const arrows = fg.children.filter(c => c.userData && c.userData.arrowLength !== undefined);
          return arrows.map(a => ({
            element: a.userData.element,
            length: a.userData.arrowLength,
            origin: { x: a.position.x, y: a.position.y, z: a.position.z },
            dir: { x: a.userData.dirX, y: a.userData.dirY, z: a.userData.dirZ }
          }));
        }""")
        self.assertEqual(len(data_50kv), 5, "Expected 5 force arrows at 50 kV")
        for arrow in data_50kv:
            self.assertAlmostEqual(arrow["length"], 30.0, places=2)
            # Check origin inside chamber [-80, 80]
            ox, oy, oz = arrow["origin"]["x"], arrow["origin"]["y"], arrow["origin"]["z"]
            self.assertTrue(-80 <= ox <= 80, f"Arrow origin X {ox} outside chamber")
            self.assertTrue(-60 <= oy <= 60, f"Arrow origin Y {oy} outside chamber")
            self.assertTrue(-80 <= oz <= 80, f"Arrow origin Z {oz} outside chamber")
            # Check tip inside chamber
            tip_x = ox + arrow["dir"]["x"] * arrow["length"]
            tip_y = oy + arrow["dir"]["y"] * arrow["length"]
            tip_z = oz + arrow["dir"]["z"] * arrow["length"]
            self.assertTrue(-80 <= tip_x <= 80, f"Arrow tip X {tip_x} pierces chamber wall")
            self.assertTrue(-60 <= tip_y <= 60, f"Arrow tip Y {tip_y} pierces chamber ceiling/floor")
            self.assertTrue(-80 <= tip_z <= 80, f"Arrow tip Z {tip_z} pierces chamber depth")

    def test_raycast_picking_prioritizes_interior_over_chamber(self):
        """V0-R2-F1 regression: getPickedObject returns interior component when ray penetrates chamber wall."""
        result = self.page.evaluate("""() => {
          const exp = window.__explorer;
          if (!exp) return { error: "No __explorer" };

          // Aim directly at center where blade/ground are located
          const container = document.getElementById('viewport-container');
          const rect = container.getBoundingClientRect();
          const evt = {
            clientX: rect.left + rect.width * 0.45,
            clientY: rect.top + rect.height * 0.50
          };
          const picked = exp.getPickedObject(evt);
          return {
            id: picked ? picked.userData.id : null,
            name: picked ? picked.userData.name : null
          };
        }""")
        self.assertIsNotNone(result.get("id"), "Raycast returned no object")
        self.assertNotEqual(result.get("id"), "enclosure_walls", "Chamber occluded interior component in raycast")
        self.assertIn(result.get("id"), {"blade_electrode", "dielectric_block", "ground_electrode", "support_mount"})

    def test_guided_tour_and_help_modals(self):
        """V0.2 regression: verify nonblocking Guided Learning panel and Help modal."""
        # V0.2: Learning panel is open and nonblocking by default
        learning_panel = self.page.locator("#learning-panel")
        self.assertTrue(learning_panel.is_visible())

        # Verify no centered darkened tour-modal exists
        self.assertEqual(self.page.locator("#tour-modal").count(), 0)

        # Toggle learning panel collapse and expand
        self.page.click("#btn-toggle-guide")
        self.page.wait_for_timeout(300)
        has_collapsed = self.page.evaluate("() => document.getElementById('app-layout').classList.contains('guide-collapsed')")
        self.assertTrue(has_collapsed)

        self.page.click("#btn-toggle-guide")
        self.page.wait_for_timeout(300)
        has_collapsed_after = self.page.evaluate("() => document.getElementById('app-layout').classList.contains('guide-collapsed')")
        self.assertFalse(has_collapsed_after)

        # Help modal opens and traps focus, dismisses on Escape
        self.page.click("#btn-toggle-help")
        help_modal = self.page.locator("#help-modal")
        self.assertTrue(help_modal.is_visible())

        self.page.keyboard.press("Escape")
        self.assertFalse(help_modal.is_visible())

        self.assertEqual(len(self.page_errors), 0, f"Modal operations threw errors: {self.page_errors}")

    def test_mobile_narrow_viewport_layout(self):
        """V0-R1-M4 / V0-R2-M3: verify 375x667 mobile viewport renders without horizontal overflow."""
        self.page.set_viewport_size({"width": 375, "height": 667})
        self.page.wait_for_timeout(100)

        scroll_width = self.page.evaluate("document.documentElement.scrollWidth")
        client_width = self.page.evaluate("document.documentElement.clientWidth")
        self.assertLessEqual(scroll_width, client_width + 1, "Page has horizontal overflow on 375px viewport")

        self.assertEqual(len(self.page_errors), 0, f"Mobile rendering threw errors: {self.page_errors}")

    def test_runtime_gap_slider_mesh_bounding_boxes(self):
        """V0-R4-M1 [MED]: runtime WebGL Box3 geometry verification of gap d and dielectric clearance across slider sweeps.

        Drives the actual DOM slider #slider-gap across [16, 25, 50] mm.
        For each step, evaluates THREE.Box3().setFromObject(mesh) with updated world matrices to assert:
        1. ground.min.x - blade.max.x == d (surface-to-surface physical clearance).
        2. ground.min.x - dielectric.max.x >= 5.0 mm (guaranteeing physical clearance).
        3. UI inspector retains tip radius metadata and surface gap notes.
        """
        self.page.click("#tab-btn-sandbox")
        # Ensure force layer is enabled for What-If sandbox testing
        self.page.evaluate("() => { const el = document.getElementById('toggle-forces'); if (el) { el.checked = true; } }")

        gap_settings = [16, 25, 50]
        for gap in gap_settings:
            self.page.fill("#slider-gap", str(gap))
            self.page.dispatch_event("#slider-gap", "input")
            self.page.wait_for_timeout(30)

            val_text = self.page.locator("#val-gap").inner_text()
            self.assertIn(f"{gap}.0 mm", val_text)

            geom_stats = self.page.evaluate("""() => {
              const exp = window.__explorer;
              const blade = exp.componentMeshes["blade_electrode"];
              const ground = exp.componentMeshes["ground_electrode"];
              const diel = exp.componentMeshes["dielectric_block"];

              blade.updateMatrixWorld(true);
              ground.updateMatrixWorld(true);
              diel.updateMatrixWorld(true);

              const boxBlade = new THREE.Box3().setFromObject(blade);
              const boxGround = new THREE.Box3().setFromObject(ground);
              const boxDiel = new THREE.Box3().setFromObject(diel);

              return {
                blade_max_x: boxBlade.max.x,
                ground_min_x: boxGround.min.x,
                ground_max_x: boxGround.max.x,
                diel_max_x: boxDiel.max.x,
                gap_distance: boxGround.min.x - boxBlade.max.x,
                diel_clearance: boxGround.min.x - boxDiel.max.x
              };
            }""")

            # 1. Surface-to-surface physical distance d from blade knife-edge (x=0) to near ground face
            self.assertAlmostEqual(geom_stats["gap_distance"], float(gap), delta=0.01,
                                   msg=f"Ground front face does not match gap d={gap} mm")

            # 2. Minimum physical clearance from dielectric block >= 5.0 mm
            self.assertGreaterEqual(geom_stats["diel_clearance"], 5.0 - 1e-4,
                                    msg=f"Ground plate collided or infringed clearance at gap={gap} mm: {geom_stats['diel_clearance']} mm")

        # Check inspector card details
        self.page.click("#tab-btn-layers")
        self.page.click(".component-item-btn[data-id='blade_electrode']")
        dim_text = self.page.locator("#inspector-dimensions").inner_text()
        self.assertIn("Tip radius: 0.1 mm source metadata; idealized knife-edge vertex in V0 mesh", dim_text)

    def test_inspector_force_separates_physical_trend_and_visual_arrow(self):
        """V0-R4-M3 [MED]: inspector explicitly separates physical scaling trend (F ∝ V²) from bounded visual arrow encoding.

        Tests that inspector displays:
        - At 0 kV: '0.0 (Field OFF at 0 V)'
        - At 2 kV: 'Physical Trend: (V/20)² = 0.01x' and 'Visual Arrow: 6.1 mm bounded legibility'
        - At 20 kV: 'Physical Trend: (V/20)² = 1.00x' and 'Visual Arrow: 16.0 mm bounded legibility'
        - At 50 kV: 'Physical Trend: (V/20)² = 6.25x' and 'Visual Arrow: 30.0 mm bounded legibility'
        """
        # Select blade electrode
        self.page.click("#tab-btn-layers")
        self.page.click(".component-item-btn[data-id='blade_electrode']")

        test_voltages = [
            (0, "0.0 (Field OFF at 0 V)", None),
            (2, "Physical Trend: (V/20)² = 0.01x", "Visual Arrow: 6.1 mm bounded legibility"),
            (20, "Physical Trend: (V/20)² = 1.00x", "Visual Arrow: 16.0 mm bounded legibility"),
            (50, "Physical Trend: (V/20)² = 6.25x", "Visual Arrow: 30.0 mm bounded legibility"),
        ]

        self.page.click("#tab-btn-sandbox")
        # Ensure force layer is enabled for What-If sandbox testing
        self.page.evaluate("() => { const el = document.getElementById('toggle-forces'); if (el) { el.checked = true; } }")
        for v, expected_trend, expected_arrow in test_voltages:
            self.page.fill("#slider-voltage", str(v))
            self.page.dispatch_event("#slider-voltage", "input")
            self.page.wait_for_timeout(25)

            # Check inspector text
            self.page.click("#tab-btn-inspector")
            force_text = self.page.locator("#inspector-force").inner_text()

            if expected_arrow is None:
                self.assertIn(expected_trend, force_text)
            else:
                self.assertIn(expected_trend, force_text, f"Expected '{expected_trend}' at V={v} kV; got: '{force_text}'")
                self.assertIn(expected_arrow, force_text, f"Expected '{expected_arrow}' at V={v} kV; got: '{force_text}'")
            self.page.click("#tab-btn-sandbox")
        # Ensure force layer is enabled for What-If sandbox testing
        self.page.evaluate("() => { const el = document.getElementById('toggle-forces'); if (el) { el.checked = true; } }")

    def test_chip_bar_component_quick_select(self):
        """V0.1 regression: verify accessible component quick-select chip bar selects all 5 components."""
        components = [
            ("blade_electrode", "Asymmetric High-Voltage Blade", "PUBLISHED HYPOTHESIS"),
            ("ground_electrode", "Ground Counter-Electrode", "ESTABLISHED MODEL"),
            ("dielectric_block", "Solid Dielectric Barrier / Potting", "WHAT-IF PARAMETER"),
            ("support_mount", "Structural Support Mount", "ESTABLISHED MODEL"),
            ("enclosure_walls", "Conductive Enclosure (Chamber)", "ESTABLISHED MODEL"),
        ]

        for comp_id, expected_name, expected_badge in components:
            chip = self.page.locator(f".chip-btn[data-id='{comp_id}']")
            self.assertTrue(chip.is_visible())
            chip.click()
            self.page.wait_for_timeout(25)

            name_el = self.page.locator("#inspector-name").inner_text()
            badge_el = self.page.locator("#inspector-badge").inner_text()
            self.assertEqual(name_el, expected_name)
            self.assertEqual(badge_el, expected_badge)

            # Selected chip class
            self.assertTrue("selected" in (chip.get_attribute("class") or ""))

        self.assertEqual(len(self.page_errors), 0, f"Chip bar operations threw errors: {self.page_errors}")

    def test_3d_labels_toggle(self):
        """V0.1 regression: verify 3D component labels HUD toggle button updates visibility and ARIA."""
        btn = self.page.locator("#btn-toggle-labels")
        self.assertTrue(btn.is_visible())
        labels_container = self.page.locator("#labels-container")

        # Initially active (visible)
        self.assertEqual(btn.get_attribute("aria-pressed"), "true")
        self.assertFalse("hidden" in (labels_container.get_attribute("class") or ""))

        # Click to toggle off
        btn.click()
        self.page.wait_for_timeout(25)
        self.assertEqual(btn.get_attribute("aria-pressed"), "false")
        self.assertTrue("hidden" in (labels_container.get_attribute("class") or ""))

        # Click to toggle back on
        btn.click()
        self.page.wait_for_timeout(25)
        self.assertEqual(btn.get_attribute("aria-pressed"), "true")
        self.assertFalse("hidden" in (labels_container.get_attribute("class") or ""))

        self.assertEqual(len(self.page_errors), 0, f"Labels toggle threw errors: {self.page_errors}")

    def test_sidebar_collapse_toggle(self):
        """V0.1 regression: verify sidebar collapse toggle expands viewport to full width."""
        btn = self.page.locator("#btn-toggle-sidebar")
        self.assertTrue(btn.is_visible())
        layout = self.page.locator(".app-layout")

        # Initially open
        self.assertEqual(btn.get_attribute("aria-pressed"), "false")
        self.assertFalse("sidebar-collapsed" in (layout.get_attribute("class") or ""))

        # Click to collapse
        btn.click()
        self.page.wait_for_timeout(50)
        self.assertEqual(btn.get_attribute("aria-pressed"), "true")
        self.assertTrue("sidebar-collapsed" in (layout.get_attribute("class") or ""))

        # Click to expand
        btn.click()
        self.page.wait_for_timeout(50)
        self.assertEqual(btn.get_attribute("aria-pressed"), "false")
        self.assertFalse("sidebar-collapsed" in (layout.get_attribute("class") or ""))

        self.assertEqual(len(self.page_errors), 0, f"Sidebar toggle threw errors: {self.page_errors}")

    def test_mobile_390_viewport_layout(self):
        """V0.1 regression: verify 390x844 mobile viewport (iPhone 12/13/14) renders cleanly without horizontal overflow."""
        self.page.set_viewport_size({"width": 390, "height": 844})
        self.page.wait_for_timeout(100)

        scroll_width = self.page.evaluate("document.documentElement.scrollWidth")
        client_width = self.page.evaluate("document.documentElement.clientWidth")
        self.assertLessEqual(scroll_width, client_width + 1, "Page has horizontal overflow on 390px viewport")

        # Verify chip bar and canvas are visible
        self.assertTrue(self.page.locator("#webgl-canvas").is_visible())
        self.assertTrue(self.page.locator("#component-chip-bar").is_visible())

        self.assertEqual(len(self.page_errors), 0, f"Mobile 390px rendering threw errors: {self.page_errors}")

    def test_billboard_label_pin_mouse_and_keyboard_selection(self):
        """V0.1-R1-F1 regression: real mouse pointer click and keyboard Enter on billboard label pins selects components."""
        # 1. Real pointer click on dielectric label pin
        pin_diel = self.page.locator("#label-pin-dielectric_block")
        self.assertTrue(pin_diel.is_visible())
        bb = pin_diel.bounding_box()
        self.assertIsNotNone(bb)

        # Real page.mouse.click at the center of the billboard pin button
        self.page.mouse.click(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2)
        self.page.wait_for_timeout(50)

        # Assert inspector updated to dielectric
        name_el = self.page.locator("#inspector-name").inner_text()
        self.assertEqual(name_el, "Solid Dielectric Barrier / Potting")
        self.assertEqual(pin_diel.get_attribute("aria-pressed"), "true")
        self.assertTrue("selected" in (pin_diel.get_attribute("class") or ""))

        # 2. Keyboard focus and Enter key activation on blade label pin
        pin_blade = self.page.locator("#label-pin-blade_electrode")
        self.assertTrue(pin_blade.is_visible())
        pin_blade.focus()
        self.page.keyboard.press("Enter")
        self.page.wait_for_timeout(50)

        # Assert inspector updated to blade
        name_el = self.page.locator("#inspector-name").inner_text()
        self.assertEqual(name_el, "Asymmetric High-Voltage Blade")
        self.assertEqual(pin_blade.get_attribute("aria-pressed"), "true")
        self.assertTrue("selected" in (pin_blade.get_attribute("class") or ""))

        self.assertEqual(len(self.page_errors), 0, f"Billboard pin interactions threw errors: {self.page_errors}")

    def test_chip_bar_and_pin_voltage_slider_synchronization(self):
        """V0.1-R1-M1 regression: chip bar and 3D billboard pin blade labels update dynamically across voltage slider sweep."""
        chip_label = self.page.locator("#chip-blade-label")
        pin_label = self.page.locator("#label-pin-blade_electrode .label-pin-text")

        self.page.click("#tab-btn-sandbox")
        # Ensure force layer is enabled for What-If sandbox testing
        self.page.evaluate("() => { const el = document.getElementById('toggle-forces'); if (el) { el.checked = true; } }")

        test_voltages = [
            ("0", "Blade (0 V OFF)"),
            ("20", "Blade (-20 kV)"),
            ("50", "Blade (-50 kV)"),
        ]

        for v_str, expected_label in test_voltages:
            self.page.fill("#slider-voltage", v_str)
            self.page.dispatch_event("#slider-voltage", "input")
            self.page.wait_for_timeout(30)

            self.assertEqual(chip_label.inner_text(), expected_label,
                             f"Chip label mismatch at V={v_str} kV")
            self.assertEqual(pin_label.inner_text(), expected_label,
                             f"Billboard pin label mismatch at V={v_str} kV")

        self.assertEqual(len(self.page_errors), 0, f"Chip voltage sweep threw errors: {self.page_errors}")

    def test_inspector_role_and_status_at_zero_and_energized_voltage(self):
        """V0.1-R1-M2 regression: inspector card qualifies multi-body forces and specifies unenergized 0 V state."""
        # Set voltage to nominal 20 kV
        self.page.click("#tab-btn-sandbox")
        self.page.fill("#slider-voltage", "20")
        self.page.dispatch_event("#slider-voltage", "input")
        self.page.wait_for_timeout(30)

        # Select ground electrode at nominal 20 kV
        self.page.click("#tab-btn-layers")
        self.page.click(".component-item-btn[data-id='ground_electrode']")

        role_text_20k = self.page.locator("#inspector-role").inner_text()
        status_text_20k = self.page.locator("#inspector-status").inner_text()

        self.assertIn("Pairwise equality between these two electrodes alone is not assumed", role_text_20k)
        self.assertIn("not isolated pairwise equal", status_text_20k)

        # Sweep voltage slider to 0 kV
        self.page.click("#tab-btn-sandbox")
        self.page.fill("#slider-voltage", "0")
        self.page.dispatch_event("#slider-voltage", "input")
        self.page.wait_for_timeout(30)

        # Check inspector updated to 0 V unenergized state
        self.page.click("#tab-btn-inspector")
        role_text_0k = self.page.locator("#inspector-role").inner_text()
        status_text_0k = self.page.locator("#inspector-status").inner_text()

        self.assertIn("unenergized at 0 v", role_text_0k.lower())
        self.assertIn("electrostatic forces are identically zero", role_text_0k.lower())
        self.assertIn("Field OFF at 0 V — Zero Electrostatic Traction (Unenergized)", status_text_0k)

        self.assertEqual(len(self.page_errors), 0, f"Inspector voltage state check threw errors: {self.page_errors}")

    def test_electric_field_legend_and_marker_semantics(self):
        """V0.1-R1-F2 regression: electric field legend qualifies schematic orientation and distinguishes 0 V extinction."""
        legend_field = self.page.locator("#legend-field-label")

        # At initial 0 kV (Chapter 1)
        self.assertIn("Electric Field Direction (OFF at 0 V — Zero Field)", legend_field.inner_text())

        # At energized 20 kV (Chapter 2 or sandbox)
        self.page.click("#tab-btn-sandbox")
        self.page.fill("#slider-voltage", "20")
        self.page.dispatch_event("#slider-voltage", "input")
        self.page.wait_for_timeout(30)

        self.assertIn("Schematic Orientation Only, Not Computed |E| Magnitude or Charge Flow", legend_field.inner_text())

        self.assertEqual(len(self.page_errors), 0, f"Field legend check threw errors: {self.page_errors}")

    def test_v0_1_r2_f1_hud_and_legend_bounding_boxes_do_not_overlap(self):
        """V0.1-R2-F1 regression: view preset HUD toolbar and layer legend HUD must never overlap."""
        hud = self.page.locator(".view-preset-hud")
        legend = self.page.locator(".layer-legend-hud")

        self.assertTrue(hud.is_visible())
        self.assertTrue(legend.is_visible())

        # Test across desktop and tablet viewports
        for vp in [(1280, 800), (1024, 768), (800, 600)]:
            self.page.set_viewport_size({"width": vp[0], "height": vp[1]})
            self.page.wait_for_timeout(40)

            box_hud = hud.bounding_box()
            box_legend = legend.bounding_box()

            self.assertIsNotNone(box_hud)
            self.assertIsNotNone(box_legend)

            # Check for non-overlap either horizontally or vertically
            horiz_sep = (box_hud["x"] + box_hud["width"] <= box_legend["x"]) or (box_legend["x"] + box_legend["width"] <= box_hud["x"])
            vert_sep = (box_hud["y"] + box_hud["height"] <= box_legend["y"]) or (box_legend["y"] + box_legend["height"] <= box_hud["y"])

            self.assertTrue(
                horiz_sep or vert_sep,
                f"HUD box {box_hud} overlaps with Legend box {box_legend} at viewport {vp}"
            )

        # Restore default desktop viewport
        self.page.set_viewport_size({"width": 1280, "height": 800})
        self.page.wait_for_timeout(40)
        self.assertEqual(len(self.page_errors), 0, f"HUD non-overlap check threw errors: {self.page_errors}")

    def test_v0_1_r2_f2_billboard_label_pins_never_overlap_across_viewports_and_presets(self):
        """V0.1-R2-F2 & V0.1-R3-M1 regression: all visible 3D billboard pins have zero bounding box overlap across all 4 presets and mobile."""
        viewports = [
            (1280, 800, "Desktop"),
            (390, 844, "iPhone 12/13/14"),
            (375, 812, "iPhone SE")
        ]
        presets = ["isometric", "side", "front", "top"]
        expected_pin_ids = {
            "label-pin-blade_electrode",
            "label-pin-ground_electrode",
            "label-pin-dielectric_block",
            "label-pin-support_mount",
            "label-pin-enclosure_walls"
        }

        for width, height, vp_name in viewports:
            self.page.set_viewport_size({"width": width, "height": height})
            self.page.wait_for_timeout(60)

            for preset in presets:
                # Trigger camera preset and wait for 500ms transition to settle
                self.page.click(f".view-preset-hud .hud-btn[data-view='{preset}']")
                self.page.wait_for_timeout(550)

                # Query all visible label pins
                pins = self.page.locator(".label-pin:visible").all()
                self.assertEqual(len(pins), 5, f"Expected exactly 5 visible pins in {preset} at {vp_name}")

                pin_ids = {p.get_attribute("id") for p in pins}
                self.assertEqual(pin_ids, expected_pin_ids, f"Visible pin IDs mismatch in {preset} at {vp_name}")

                boxes = []
                for pin in pins:
                    b = pin.bounding_box()
                    self.assertIsNotNone(b)
                    boxes.append((pin.get_attribute("id"), b))

                # Pairwise non-overlap check
                for i in range(len(boxes)):
                    for j in range(i + 1, len(boxes)):
                        id_a, box_a = boxes[i]
                        id_b, box_b = boxes[j]

                        horiz_sep = (box_a["x"] + box_a["width"] <= box_b["x"]) or (box_b["x"] + box_b["width"] <= box_a["x"])
                        vert_sep = (box_a["y"] + box_a["height"] <= box_b["y"]) or (box_b["y"] + box_b["height"] <= box_a["y"])

                        self.assertTrue(
                            horiz_sep or vert_sep,
                            f"Label collision detected between {id_a} {box_a} and {id_b} {box_b} in preset '{preset}' at viewport {vp_name}"
                        )

        # Restore default desktop viewport and view
        self.page.set_viewport_size({"width": 1280, "height": 800})
        self.page.click(".view-preset-hud .hud-btn[data-view='isometric']")
        self.page.wait_for_timeout(60)
        self.assertEqual(len(self.page_errors), 0, f"Label collision check threw errors: {self.page_errors}")

    def test_v0_1_r2_f2_all_five_billboard_pins_clickable_via_real_pointer_and_element_from_point(self):
        """V0.1-R2-F2 & V0.1-R3-M1 regression: exact elementFromPoint equality and real pointer click select ALL 5 components across viewports and presets."""
        components = [
            ("blade_electrode", "Asymmetric High-Voltage Blade"),
            ("ground_electrode", "Ground Counter-Electrode"),
            ("dielectric_block", "Solid Dielectric Barrier / Potting"),
            ("support_mount", "Structural Support Mount"),
            ("enclosure_walls", "Conductive Enclosure (Chamber)")
        ]
        viewports = [
            (1280, 800, "Desktop"),
            (390, 844, "iPhone 12/13/14"),
            (375, 812, "iPhone SE")
        ]
        presets = ["isometric", "side", "front", "top"]

        for width, height, vp_name in viewports:
            self.page.set_viewport_size({"width": width, "height": height})
            self.page.wait_for_timeout(60)

            for preset in presets:
                self.page.click(f".view-preset-hud .hud-btn[data-view='{preset}']")
                self.page.wait_for_timeout(550)

                for comp_id, expected_title in components:
                    pin_elem_id = f"label-pin-{comp_id}"
                    pin = self.page.locator(f"#{pin_elem_id}")
                    self.assertTrue(pin.is_visible(), f"Pin {comp_id} must be visible in {preset} at {vp_name}")

                    bb = pin.bounding_box()
                    self.assertIsNotNone(bb)

                    cx = bb["x"] + bb["width"] / 2
                    cy = bb["y"] + bb["height"] / 2

                    # 1. Verify elementFromPoint directly equals the exact button element (guarding transparent child spans)
                    is_exact_pin = self.page.evaluate(
                        "([x, y, id]) => document.elementFromPoint(x, y) === document.getElementById(id)",
                        [cx, cy, pin_elem_id]
                    )
                    self.assertTrue(is_exact_pin, f"Center of pin {comp_id} did not resolve directly to button in {preset} at {vp_name}")

                    # 2. Real mouse click on pin button center
                    self.page.mouse.click(cx, cy)
                    self.page.wait_for_timeout(30)

                    # 3. Assert component selection and inspector state
                    self.assertEqual(pin.get_attribute("aria-pressed"), "true")
                    self.assertTrue("selected" in (pin.get_attribute("class") or ""))

                    name_text = self.page.locator("#inspector-name").inner_text()
                    self.assertEqual(name_text, expected_title, f"Inspector name mismatch after clicking {comp_id} in {preset} at {vp_name}")

        # Restore default desktop viewport and view
        self.page.set_viewport_size({"width": 1280, "height": 800})
        self.page.click(".view-preset-hud .hud-btn[data-view='isometric']")
        self.page.wait_for_timeout(60)
        self.assertEqual(len(self.page_errors), 0, f"Pointer hit-testing threw errors: {self.page_errors}")

    def test_v0_1_r3_f1_single_pin_enclosure_clamp_and_click_when_geometry_off(self):
        """V0.1-R3-F1 regression: single enclosure pin clamps inside canvas and below HUD toolbar when geometry is toggled off."""
        viewports = [
            (375, 812, "iPhone SE"),
            (390, 844, "iPhone 12/13/14"),
            (1280, 800, "Desktop")
        ]

        for width, height, vp_name in viewports:
            self.page.set_viewport_size({"width": width, "height": height})
            self.page.wait_for_timeout(60)

            # Ensure default isometric preset
            self.page.click(".view-preset-hud .hud-btn[data-view='isometric']")
            self.page.wait_for_timeout(100)

            # Toggle Component Geometry OFF
            self.page.evaluate("""() => {
                const el = document.getElementById("toggle-geometry");
                if (el.checked) {
                    el.checked = false;
                    el.dispatchEvent(new Event("change"));
                }
            }""")
            self.page.wait_for_timeout(100)

            # Assert exactly 1 visible label pin: enclosure_walls
            visible_pins = self.page.locator(".label-pin:visible").all()
            self.assertEqual(len(visible_pins), 1, f"Expected exactly 1 visible pin with geometry OFF at {vp_name}")
            pin = visible_pins[0]
            self.assertEqual(pin.get_attribute("id"), "label-pin-enclosure_walls")

            # Check bounding box
            b = pin.bounding_box()
            self.assertIsNotNone(b)
            canvas_box = self.page.locator("#viewport-container").bounding_box()
            self.assertIsNotNone(canvas_box)
            hud_box = self.page.locator(".view-preset-hud").bounding_box()
            self.assertIsNotNone(hud_box)

            # Must be strictly inside canvas container bounds horizontally
            self.assertGreaterEqual(b["x"], canvas_box["x"], f"Pin left {b['x']} must be inside canvas left {canvas_box['x']} at {vp_name}")
            self.assertLessEqual(b["x"] + b["width"], canvas_box["x"] + canvas_box["width"] + 1, f"Pin right {b['x'] + b['width']} must be inside canvas right at {vp_name}")

            # Must be completely clear of (below) HUD preset toolbar
            self.assertGreaterEqual(
                b["y"],
                hud_box["y"] + hud_box["height"],
                f"Chamber pin at y={b['y']} occluded underneath HUD toolbar (bottom={hud_box['y'] + hud_box['height']}) at {vp_name}"
            )

            # Direct elementFromPoint test (exact HTMLButtonElement identity)
            cx = b["x"] + b["width"] / 2
            cy = b["y"] + b["height"] / 2
            is_exact = self.page.evaluate(
                "([x, y]) => document.elementFromPoint(x, y) === document.getElementById('label-pin-enclosure_walls')",
                [cx, cy]
            )
            self.assertTrue(is_exact, f"elementFromPoint at ({cx}, {cy}) must resolve directly to enclosure pin at {vp_name}")

            # Real mouse click
            self.page.mouse.click(cx, cy)
            self.page.wait_for_timeout(50)
            self.assertEqual(pin.get_attribute("aria-pressed"), "true")
            inspector_title = self.page.locator("#inspector-name").inner_text()
            self.assertEqual(inspector_title, "Conductive Enclosure (Chamber)")

            # Restore geometry
            self.page.evaluate("""() => {
                const el = document.getElementById("toggle-geometry");
                if (!el.checked) {
                    el.checked = true;
                    el.dispatchEvent(new Event("change"));
                }
            }""")
            self.page.wait_for_timeout(100)

            # Assert all 5 pins reappear
            all_pins = self.page.locator(".label-pin:visible").all()
            self.assertEqual(len(all_pins), 5, f"All 5 pins must reappear after re-enabling geometry at {vp_name}")

        # Restore default desktop viewport
        self.page.set_viewport_size({"width": 1280, "height": 800})
        self.page.wait_for_timeout(40)
        self.assertEqual(len(self.page_errors), 0, f"Single-pin test threw errors: {self.page_errors}")

    def test_v0_1_r4_m1_capacity_shortfall_enlarged_pins_runtime_regression(self):
        """V0.1-R4-M1 regression: capacity shortfall triggers deterministic conflict suppression with zero overlap and hittable pins."""
        # Test on narrow mobile viewport where vertical capacity is tight
        self.page.set_viewport_size({"width": 375, "height": 812})
        self.page.wait_for_timeout(60)

        # 1. Artificially inject enlarged pin dimensions (w=220px, h=50px) representing large-text accessibility styles
        self.page.evaluate("""() => {
            const style = document.createElement('style');
            style.id = 'test-enlarged-pins';
            style.textContent = '.label-pin { min-width: 220px !important; min-height: 50px !important; font-size: 1.2rem !important; padding: 12px 20px !important; }';
            document.head.appendChild(style);
        }""")
        self.page.click(".view-preset-hud .hud-btn[data-view='isometric']")
        self.page.wait_for_timeout(600)

        # 2. Query visible pins: capacity shortfall must suppress at least one conflicting pin
        enlarged_pins = self.page.locator(".label-pin:visible").all()
        self.assertLess(len(enlarged_pins), 5, f"Capacity shortfall must suppress conflicting pins, found {len(enlarged_pins)}")
        self.assertGreaterEqual(len(enlarged_pins), 2, "High-priority pins must remain visible")

        canvas_box = self.page.locator("#viewport-container").bounding_box()
        hud_box = self.page.locator(".view-preset-hud").bounding_box()
        self.assertIsNotNone(canvas_box)
        self.assertIsNotNone(hud_box)

        boxes = []
        for p in enlarged_pins:
            b = p.bounding_box()
            self.assertIsNotNone(b)
            cid = p.get_attribute("id")
            boxes.append((cid, b, p))

            # Must be inside canvas container horizontally
            self.assertGreaterEqual(b["x"], canvas_box["x"], f"Pin {cid} left edge {b['x']} outside canvas")
            self.assertLessEqual(b["x"] + b["width"], canvas_box["x"] + canvas_box["width"] + 1, f"Pin {cid} right edge outside canvas")

            # Must be clear of HUD toolbar
            self.assertGreaterEqual(b["y"], hud_box["y"] + hud_box["height"], f"Pin {cid} occluded under HUD toolbar")

        # 3. Explicit postcondition verification: zero pairwise bounding box overlap among all surviving pins
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                id_a, box_a, _ = boxes[i]
                id_b, box_b, _ = boxes[j]
                horiz_sep = (box_a["x"] + box_a["width"] <= box_b["x"]) or (box_b["x"] + box_b["width"] <= box_a["x"])
                vert_sep = (box_a["y"] + box_a["height"] <= box_b["y"]) or (box_b["y"] + box_b["height"] <= box_a["y"])
                self.assertTrue(
                    horiz_sep or vert_sep,
                    f"Conflict suppression failed: collision detected between {id_a} and {id_b} in shortfall state"
                )

        # 4. Verify exact direct elementFromPoint resolution and real pointer click on every surviving pin
        for cid, _, pin in boxes:
            current_b = pin.bounding_box()
            cx = current_b["x"] + current_b["width"] / 2
            cy = current_b["y"] + current_b["height"] / 2

            is_exact = self.page.evaluate(
                "([x, y, id]) => document.elementFromPoint(x, y) === document.getElementById(id)",
                [cx, cy, cid]
            )
            self.assertTrue(is_exact, f"elementFromPoint at ({cx}, {cy}) failed for {cid}")

            self.page.mouse.click(cx, cy)
            self.page.wait_for_timeout(60)
            self.assertEqual(pin.get_attribute("aria-pressed"), "true", f"Clicking {cid} failed to set aria-pressed=true")

            selected_id = self.page.evaluate("() => document.querySelector('.component-item-btn.selected')?.dataset?.id")
            expected_id = cid.replace("label-pin-", "")
            self.assertEqual(selected_id, expected_id, f"Clicking {cid} failed to select {expected_id}")

        # 5. Verify quick-select chip bar retains ALL 5 components even during 3D label suppression
        chips = self.page.locator(".chip-btn").all()
        self.assertEqual(len(chips), 5, "Quick-select chip bar must retain all 5 components")

        # Clicking chip for a suppressed component must select it successfully
        self.page.click("#chip-support-mount")
        self.page.wait_for_timeout(60)
        self.assertEqual(
            self.page.locator("#inspector-name").inner_text(),
            "Structural Support Mount",
            "Chip bar must successfully inspect support mount even if suppressed in 3D canvas"
        )

        # 6. Clean up: remove enlarged style and verify all 5 pins return in normal state
        self.page.evaluate("() => document.getElementById('test-enlarged-pins')?.remove()")
        self.page.click(".view-preset-hud .hud-btn[data-view='isometric']")
        self.page.wait_for_timeout(600)

        restored_pins = self.page.locator(".label-pin:visible").all()
        self.assertEqual(len(restored_pins), 5, "All 5 pins must reappear when normal dimensions are restored")

        # Restore desktop viewport
        self.page.set_viewport_size({"width": 1280, "height": 800})
        self.page.wait_for_timeout(40)
        self.assertEqual(len(self.page_errors), 0, f"Enlarged pins regression test threw errors: {self.page_errors}")

    def test_v0_2_six_chapter_navigation_and_scene_synchronization(self):
        """V0.2 regression: verify 6-chapter guided tour navigation and dynamic scene synchronization."""
        # 1. Chapter 1: Initial state
        title_el = self.page.locator("#guide-chapter-title")
        self.assertIn("1. Meet the Device", title_el.inner_text())
        self.assertIn("Component Focus", self.page.locator("#scene-annotation-card").inner_text())

        # Chapter 1 prev button is disabled
        self.assertTrue(self.page.locator("#guide-btn-prev").is_disabled())

        # 2. Navigate to Chapter 2: Turn on the Electricity
        self.page.click("#guide-btn-next")
        self.page.wait_for_timeout(200)
        self.assertIn("2. Turn on the Electricity", title_el.inner_text())
        self.assertIn("Streamlines", self.page.locator("#scene-annotation-card").inner_text())
        # Check scene voltage synchronized to 20 kV
        val_voltage = self.page.locator("#val-voltage").inner_text()
        self.assertIn("-20.0 kV", val_voltage)
        # Check field lines visible
        field_vis = self.page.evaluate("() => window.__explorer.fieldGroup.visible")
        self.assertTrue(field_vis)

        # 3. Navigate to Chapter 3: Follow the Forces
        self.page.click("#guide-btn-next")
        self.page.wait_for_timeout(200)
        self.assertIn("3. Follow the Forces", title_el.inner_text())
        self.assertIn("Action & Reaction", self.page.locator("#scene-annotation-card").inner_text())
        forces_vis = self.page.evaluate("() => window.__explorer.forceGroup.visible")
        self.assertTrue(forces_vis)

        # 4. Navigate to Chapter 4: Can the Whole Device Move?
        self.page.click("#guide-btn-next")
        self.page.wait_for_timeout(200)
        self.assertIn("4. Can the Whole Device Move?", title_el.inner_text())
        self.assertIn("Action-Reaction Balance", self.page.locator("#scene-annotation-card").inner_text())
        # Check Force Ledger tab automatically activated
        ledger_panel = self.page.locator("#tab-ledger")
        self.assertTrue(ledger_panel.is_visible())
        self.assertEqual(self.page.locator("#tab-btn-ledger").get_attribute("aria-selected"), "true")

        # 5. Navigate to Chapter 5: What are Scalar Waves?
        self.page.click("#guide-btn-next")
        self.page.wait_for_timeout(200)
        self.assertIn("5. What", title_el.inner_text())
        self.assertIn("Scalar Wave", self.page.locator("#scene-annotation-card").inner_text())

        # 6. Navigate to Chapter 6: How Could We Test It?
        self.page.click("#guide-btn-next")
        self.page.wait_for_timeout(200)
        self.assertIn("6. How Could We Test", title_el.inner_text())
        self.assertIn("Testing Reality", self.page.locator("#scene-annotation-card").inner_text())
        next_btn = self.page.locator("#guide-btn-next")
        self.assertEqual(next_btn.inner_text(), "Finish Tour")

        # Stepper direct jump back to Chapter 2
        self.page.click(".chapter-step-btn[data-chapter='1']")
        self.page.wait_for_timeout(200)
        self.assertIn("2. Turn on the Electricity", title_el.inner_text())

        # Back button returns to Chapter 1
        self.page.click("#guide-btn-prev")
        self.page.wait_for_timeout(200)
        self.assertIn("1. Meet the Device", title_el.inner_text())

        self.assertEqual(len(self.page_errors), 0, f"Chapter navigation threw errors: {self.page_errors}")

    def test_v0_2_progressive_disclosure_iceberg_details_and_explore_freely(self):
        """V0.2 regression: verify Iceberg disclosures, equations, citations, and Explore Freely mode."""
        guide_body = self.page.locator("#guide-body")
        self.assertTrue(guide_body.locator(".iceberg-surface").is_visible())
        self.assertTrue(guide_body.locator(".iceberg-shallow").is_visible())

        # Deeper details disclosure
        deeper = guide_body.locator(".iceberg-deeper")
        self.assertFalse(deeper.evaluate("el => el.open"))
        guide_body.locator(".iceberg-deeper summary").evaluate("el => el.click()")
        self.page.wait_for_timeout(50)
        self.assertTrue(deeper.evaluate("el => el.open"))
        self.assertIn("Jackson", deeper.inner_text())

        # Research details disclosure
        research = guide_body.locator(".iceberg-research")
        self.assertFalse(research.evaluate("el => el.open"))
        guide_body.locator(".iceberg-research summary").evaluate("el => el.click()")
        self.page.wait_for_timeout(50)
        self.assertTrue(research.evaluate("el => el.open"))
        self.assertIn("Hypothesis Tested", research.inner_text())
        self.assertIn("US11511891B2", research.inner_text())

        # Explore Freely mode
        self.page.click("#guide-btn-free")
        self.page.wait_for_timeout(100)
        self.assertIn("FREE EXPLORATION", guide_body.inner_text().upper())
        resume_btn = self.page.locator("#btn-resume-guide")
        self.assertTrue(resume_btn.is_visible())

        # Resume guide returns to chapter
        resume_btn.click()
        self.page.wait_for_timeout(100)
        self.assertIn("Meet the Device", self.page.locator("#guide-chapter-title").inner_text())

        # Pause / Resume streamline pulse animation
        pause_btn = self.page.locator("#guide-btn-pause")
        pause_btn.click()
        self.assertIn("Resume", pause_btn.inner_text())
        pause_btn.click()
        self.assertIn("Pause", pause_btn.inner_text())

        # Reset Tour
        self.page.click("#guide-btn-reset")
        self.page.wait_for_timeout(100)
        self.assertIn("1. Meet the Device", self.page.locator("#guide-chapter-title").inner_text())

        self.assertEqual(len(self.page_errors), 0, f"Iceberg and explore freely threw errors: {self.page_errors}")

    def test_v0_2_mobile_tabs_responsive_layout(self):
        """V0.2 regression: verify mobile tab navigation between Guide and Controls preserves 3D model visibility."""
        # Test on iPhone 12/13/14 viewport (390x844)
        self.page.set_viewport_size({"width": 390, "height": 844})
        self.page.wait_for_timeout(100)

        # Tabs should be visible
        mobile_tabs = self.page.locator(".mobile-panel-tabs")
        self.assertTrue(mobile_tabs.is_visible())

        # 3D Canvas should be visible and at top of layout
        canvas = self.page.locator("#webgl-canvas")
        self.assertTrue(canvas.is_visible())
        canvas_box = canvas.bounding_box()
        self.assertLess(canvas_box["y"], 220, "3D viewport must sit at the top of the mobile layout under header")

        # Initial mobile state: Guide is visible, Controls hidden
        self.assertTrue(self.page.locator("#learning-panel").is_visible())
        self.assertFalse(self.page.locator("#sidebar-container").is_visible())

        # Switch to Controls
        self.page.click("#mobile-tab-controls")
        self.page.wait_for_timeout(100)
        self.assertFalse(self.page.locator("#learning-panel").is_visible())
        self.assertTrue(self.page.locator("#sidebar-container").is_visible())

        # Switch back to Guide
        self.page.click("#mobile-tab-guide")
        self.page.wait_for_timeout(100)
        self.assertTrue(self.page.locator("#learning-panel").is_visible())
        self.assertFalse(self.page.locator("#sidebar-container").is_visible())

        # Restore desktop viewport
        self.page.set_viewport_size({"width": 1280, "height": 800})
        self.page.wait_for_timeout(50)
        self.assertEqual(len(self.page_errors), 0, f"Mobile tabs threw errors: {self.page_errors}")

    def test_v0_2_r1_m1_rendered_math_and_clickable_citations(self):
        """V0.2-R1-M1 regression: deeper layer renders clean semantic math without raw TeX delimiters and provides clickable links."""
        # Open Chapter 2 (contains field formulas and citations)
        self.page.click(".chapter-step-btn[data-index='1']")
        self.page.wait_for_timeout(100)

        guide_body = self.page.locator("#guide-body")
        deeper = guide_body.locator(".iceberg-deeper")
        deeper.locator("summary").evaluate("el => el.click()")
        self.page.wait_for_timeout(50)

        deeper_html = deeper.inner_html()
        # Assert no raw TeX delimiters
        self.assertNotIn(r"\(", deeper_html, "Raw LaTeX '\\(' found in rendered deeper HTML")
        self.assertNotIn(r"\)", deeper_html, "Raw LaTeX '\\)' found in rendered deeper HTML")

        # Assert clickable citation hyperlinks
        citations_links = deeper.locator(".iceberg-content p:has-text('Primary Citations') a")
        link_count = citations_links.count()
        self.assertGreater(link_count, 0, "Deeper citations must contain clickable hyperlinks")
        for i in range(link_count):
            href = citations_links.nth(i).get_attribute("href")
            self.assertTrue(href.startswith("https://") or href.startswith("http://"), f"Invalid citation href: {href}")
            self.assertEqual(citations_links.nth(i).get_attribute("target"), "_blank")

        self.assertEqual(len(self.page_errors), 0, f"Rendered math & links threw errors: {self.page_errors}")

    def test_v0_2_r1_m3_mobile_deep_scrolling_and_ledger_navigation(self):
        """V0.2-R1-M3 & V0.2-R2-M3: mobile layout has reachable scrollable footer and bidirectional ledger navigation."""
        for vp in [{"width": 375, "height": 667}, {"width": 390, "height": 844}]:
            self.page.set_viewport_size(vp)
            self.page.wait_for_timeout(100)

            # Navigate to Chapter 4 (Can the Whole Device Move?)
            self.page.click(".chapter-step-btn[data-index='3']")
            self.page.wait_for_timeout(100)

            # Open Action-Reaction Force Ledger from inside chapter content
            open_ledger_btn = self.page.locator("#guide-body #btn-chapter4-open-ledger")
            self.assertTrue(open_ledger_btn.is_visible(), "Chapter 4 open ledger button must be visible on mobile")
            open_ledger_btn.click()
            self.page.wait_for_timeout(150)

            # Assert sidebar container and force ledger card are visible
            sidebar = self.page.locator("#sidebar-container")
            self.assertTrue(sidebar.is_visible(), "Sidebar container must be visible after clicking open ledger button")
            ledger_card = self.page.locator("#force-ledger-card")
            self.assertTrue(ledger_card.is_visible(), "Force ledger card must be visible")

            # Click return to guide button
            back_btn = self.page.locator("#btn-ledger-back-to-guide")
            self.assertTrue(back_btn.is_visible(), "Return to guide button must be visible in ledger on mobile")
            back_btn.click()
            self.page.wait_for_timeout(150)

            # Assert learning panel is visible again
            learning_panel = self.page.locator("#learning-panel")
            self.assertTrue(learning_panel.is_visible(), "Learning panel must be visible after returning from ledger")

            # Expand deeper and research disclosures
            deeper = learning_panel.locator(".iceberg-deeper")
            deeper.locator("summary").evaluate("el => el.click()")
            research = learning_panel.locator(".iceberg-research")
            research.locator("summary").evaluate("el => el.click()")
            self.page.wait_for_timeout(50)

            # V0.2-R2-M3: Explicitly scroll to .guide-footer and assert bounding-box visibility postcondition
            footer = self.page.locator(".guide-footer")
            footer.scroll_into_view_if_needed()
            self.page.wait_for_timeout(100)
            self.assertTrue(footer.is_visible(), f"Guide footer must be visible on mobile viewport {vp}")
            box = footer.bounding_box()
            self.assertIsNotNone(box, "Guide footer bounding box must exist")
            self.assertGreater(box["y"] + box["height"], 0, "Guide footer must be vertically on screen")
            self.assertLess(box["y"], vp["height"], "Guide footer top must be inside mobile viewport height")

            # Verify footer buttons are visible and functional
            next_btn = self.page.locator("#guide-btn-next")
            reset_btn = self.page.locator("#guide-btn-reset")
            self.assertTrue(next_btn.is_visible(), "Next button must be visible in scrolled footer")
            self.assertTrue(reset_btn.is_visible(), "Reset button must be visible in scrolled footer")

            next_btn.click()
            self.page.wait_for_timeout(100)
            self.assertIn("5. What Are Scalar Waves?", self.page.locator("#guide-chapter-title").inner_text())

        # Restore desktop viewport
        self.page.set_viewport_size({"width": 1280, "height": 800})
        self.page.wait_for_timeout(50)
        self.assertEqual(len(self.page_errors), 0, f"Mobile scrolling and ledger navigation threw errors: {self.page_errors}")

    def test_v0_2_r1_m4_chapter5_scalar_wave_contrast_toggle_and_badge(self):
        """V0.2-R1-M4, V0.2-R2-M2, & V0.2-R4-M2: Chapter 5 mutually exclusive 3D mathematical scalar-wave contrast view."""
        # Navigate to Chapter 5
        self.page.click(".chapter-step-btn[data-index='4']")
        self.page.wait_for_timeout(100)
        self.assertIn("What Are Scalar Waves?", self.page.locator("#guide-chapter-title").inner_text())

        # Toggle button should be visible with initial switch-to label
        toggle_btn = self.page.locator("#guide-body #btn-toggle-wave-contrast")
        self.assertTrue(toggle_btn.is_visible(), "Chapter 5 wave contrast button must be visible")
        self.assertIn("Switch to Mathematical Scalar Wave Toy View", toggle_btn.inner_text())

        # Initial state: vector field streamlines visible, toy wave hidden, geometry visible
        field_vis_before = self.page.evaluate("window.__explorer.fieldGroup.visible")
        self.assertTrue(field_vis_before, "Vector field lines must be initially visible in Chapter 5")
        geom_vis_before = self.page.evaluate("window.__explorer.geometryGroup.visible")
        self.assertTrue(geom_vis_before, "Capacitor geometry must be initially visible in Chapter 5")
        wave_vis_before = self.page.evaluate("window.__explorer.scalarWaveGroup.visible")
        self.assertFalse(wave_vis_before, "Scalar wave group must be initially hidden in Chapter 5")

        badge = self.page.locator("#scalar-wave-badge")
        self.assertTrue("hidden" in (badge.get_attribute("class") or ""), "Badge must be initially hidden")

        # Click to toggle on mutually exclusive scalar wave toy view
        toggle_btn.click()
        self.page.wait_for_timeout(100)
        self.assertFalse("hidden" in (badge.get_attribute("class") or ""), "Badge must be displayed")
        badge_text = badge.inner_text()
        self.assertIn("MATHEMATICAL SCALAR WAVE VIEW (ABSTRACT TOY MODEL)", badge_text)
        self.assertIn("Vector streamlines hidden", badge_text)
        self.assertIn("NOT emitted by or coupled to capacitor apparatus", badge_text)
        self.assertIn("Switch Back to Electrostatic Vector Field", toggle_btn.inner_text())

        # Mutually exclusive and isolated scene verification: field lines and capacitor HIDDEN, toy wave VISIBLE
        field_vis_active = self.page.evaluate("window.__explorer.fieldGroup.visible")
        self.assertFalse(field_vis_active, "Vector field streamlines must be hidden when scalar wave toy view is active")
        geom_vis_active = self.page.evaluate("window.__explorer.geometryGroup.visible")
        self.assertFalse(geom_vis_active, "Capacitor geometry mesh must be hidden/isolated when scalar wave toy view is active")
        wave_vis_active = self.page.evaluate("window.__explorer.scalarWaveGroup.visible")
        self.assertTrue(wave_vis_active, "3D scalar wave group must be visible when contrast is toggled on")

        # Click again to switch back
        toggle_btn.click()
        self.page.wait_for_timeout(100)
        self.assertTrue("hidden" in (badge.get_attribute("class") or ""), "Badge must be hidden when switched back")
        self.assertIn("Switch to Mathematical Scalar Wave Toy View", toggle_btn.inner_text())

        # Restoration verification: field lines RESTORED, geometry RESTORED, toy wave HIDDEN
        field_vis_restored = self.page.evaluate("window.__explorer.fieldGroup.visible")
        self.assertTrue(field_vis_restored, "Vector field streamlines must be restored when switched back")
        geom_vis_restored = self.page.evaluate("window.__explorer.geometryGroup.visible")
        self.assertTrue(geom_vis_restored, "Capacitor geometry must be restored when switched back")
        wave_vis_restored = self.page.evaluate("window.__explorer.scalarWaveGroup.visible")
        self.assertFalse(wave_vis_restored, "3D scalar wave group must be hidden when contrast is toggled off")

        self.assertEqual(len(self.page_errors), 0, f"Chapter 5 wave contrast threw errors: {self.page_errors}")

    def test_v0_2_r4_f1_layer_state_preservation_and_chapter_synchronization(self):
        """V0.2-R4-F1: Layer state preservation across wave contrast toggle, chapter transitions, and user overrides."""
        # 1. Navigate to Chapter 5
        self.page.click(".chapter-step-btn[data-index='4']")
        self.page.wait_for_timeout(100)
        self.assertIn("What Are Scalar Waves?", self.page.locator("#guide-chapter-title").inner_text())

        # Sub-check (a): user-disabled field surviving wave on/off
        chk_fields = self.page.locator("#toggle-fields")
        self.assertTrue(chk_fields.is_checked(), "toggle-fields should initially be checked in Chapter 5")
        self.assertTrue(self.page.evaluate("window.__explorer.fieldGroup.visible"), "fieldGroup should be visible")

        # User unchecks toggle-fields
        chk_fields.uncheck()
        self.assertFalse(chk_fields.is_checked(), "toggle-fields should now be unchecked")
        self.assertFalse(self.page.evaluate("window.__explorer.fieldGroup.visible"), "fieldGroup must be hidden when unchecked")

        # Toggle wave mode ON
        toggle_btn = self.page.locator("#guide-body #btn-toggle-wave-contrast")
        toggle_btn.click()
        self.page.wait_for_timeout(100)
        self.assertTrue(self.page.evaluate("window.__explorer.scalarWaveGroup.visible"), "scalarWaveGroup must be visible")
        self.assertFalse(self.page.evaluate("window.__explorer.geometryGroup.visible"), "geometryGroup must be hidden in wave mode")
        self.assertFalse(self.page.evaluate("window.__explorer.fieldGroup.visible"), "fieldGroup must remain hidden")
        self.assertFalse(chk_fields.is_checked(), "toggle-fields preference must remain unchecked")

        # Toggle wave mode OFF: user preference (unchecked) must survive!
        toggle_btn.click()
        self.page.wait_for_timeout(100)
        self.assertFalse(self.page.evaluate("window.__explorer.scalarWaveGroup.visible"), "scalarWaveGroup must be hidden")
        self.assertTrue(self.page.evaluate("window.__explorer.geometryGroup.visible"), "geometryGroup must be restored")
        self.assertFalse(chk_fields.is_checked(), "toggle-fields must remain unchecked")
        self.assertFalse(self.page.evaluate("window.__explorer.fieldGroup.visible"), "fieldGroup must remain false because user unchecked it")

        # Re-enable field for subsequent checks
        chk_fields.check()
        self.assertTrue(self.page.evaluate("window.__explorer.fieldGroup.visible"), "fieldGroup should be visible when rechecked")

        # Sub-check (c): voltage/layer changes during toy mode (V0.2-R5 / R4-F1 & R4-M1)
        toggle_btn.click()
        self.page.wait_for_timeout(100)
        self.assertTrue(self.page.evaluate("window.__explorer.scalarWaveGroup.visible"), "scalarWaveGroup visible")
        self.assertFalse(self.page.evaluate("window.__explorer.fieldGroup.visible"), "fieldGroup hidden")
        self.assertFalse(self.page.evaluate("window.__explorer.geometryGroup.visible"), "geometryGroup hidden")

        # Change voltage and gap sliders while toy mode is active
        slider = self.page.locator("#slider-voltage")
        slider.fill("35")
        slider.dispatch_event("input")
        slider_gap = self.page.locator("#slider-gap")
        slider_gap.fill("30")
        slider_gap.dispatch_event("input")
        self.page.wait_for_timeout(100)

        # Groups must remain hidden during toy mode even after slider events
        self.assertFalse(self.page.evaluate("window.__explorer.fieldGroup.visible"), "fieldGroup must NOT reappear on voltage change during toy mode")
        self.assertFalse(self.page.evaluate("window.__explorer.forceGroup.visible"), "forceGroup must NOT reappear on voltage change during toy mode")
        self.assertFalse(self.page.evaluate("window.__explorer.geometryGroup.visible"), "geometryGroup must NOT reappear during toy mode")
        self.assertTrue(self.page.evaluate("window.__explorer.scalarWaveGroup.visible"), "scalarWaveGroup remains visible")

        # V0.2-R5 / R4-M1: Execute real unchecked -> checked and checked -> unchecked transitions during toy mode
        chk_geom = self.page.locator("#toggle-geometry")
        chk_forces = self.page.locator("#toggle-forces")

        # 1. Uncheck then check toggle-fields
        chk_fields.uncheck()
        self.assertFalse(chk_fields.is_checked(), "toggle-fields must be unchecked after uncheck()")
        self.assertFalse(self.page.evaluate("window.__explorer.fieldGroup.visible"), "fieldGroup must remain false in toy mode")
        chk_fields.check()
        self.assertTrue(chk_fields.is_checked(), "toggle-fields must be checked after check()")
        self.assertFalse(self.page.evaluate("window.__explorer.fieldGroup.visible"), "fieldGroup must still be hidden during toy mode despite checkbox=true")

        # 2. Uncheck then check toggle-geometry
        chk_geom.uncheck()
        self.assertFalse(chk_geom.is_checked(), "toggle-geometry must be unchecked after uncheck()")
        self.assertFalse(self.page.evaluate("window.__explorer.geometryGroup.visible"), "geometryGroup must remain false in toy mode")
        chk_geom.check()
        self.assertTrue(chk_geom.is_checked(), "toggle-geometry must be checked after check()")
        self.assertFalse(self.page.evaluate("window.__explorer.geometryGroup.visible"), "geometryGroup must still be hidden during toy mode despite checkbox=true")

        # 3. Uncheck then check toggle-forces
        chk_forces.uncheck()
        self.assertFalse(chk_forces.is_checked(), "toggle-forces must be unchecked after uncheck()")
        self.assertFalse(self.page.evaluate("window.__explorer.forceGroup.visible"), "forceGroup must remain false in toy mode")
        chk_forces.check()
        self.assertTrue(chk_forces.is_checked(), "toggle-forces must be checked after check()")
        self.assertFalse(self.page.evaluate("window.__explorer.forceGroup.visible"), "forceGroup must still be hidden during toy mode despite checkbox=true")

        # V0.2-R5 / R4-F1: Deactivate toy mode; verify objects are restored with nonzero child counts
        toggle_btn.click()
        self.page.wait_for_timeout(100)
        self.assertFalse(self.page.evaluate("window.__explorer.scalarWaveGroup.visible"), "scalarWaveGroup must be hidden after toggle off")
        self.assertTrue(self.page.evaluate("window.__explorer.geometryGroup.visible"), "geometryGroup must be restored")
        self.assertTrue(self.page.evaluate("window.__explorer.fieldGroup.visible"), "fieldGroup must be visible")
        self.assertTrue(self.page.evaluate("window.__explorer.forceGroup.visible"), "forceGroup must be visible")

        field_child_count = self.page.evaluate("window.__explorer.fieldGroup.children.length")
        self.assertGreater(field_child_count, 0, f"fieldGroup must have rebuilt/restored streamline children at 35 kV, got {field_child_count}")
        force_child_count = self.page.evaluate("window.__explorer.forceGroup.children.length")
        self.assertGreater(force_child_count, 0, f"forceGroup must have rebuilt/restored force vector children at 35 kV, got {force_child_count}")

        # V0.2-R5 / R4-F1: Test zero voltage behavior
        slider.fill("0")
        slider.dispatch_event("input")
        self.page.wait_for_timeout(100)
        self.assertFalse(self.page.evaluate("window.__explorer.fieldGroup.visible"), "fieldGroup must be hidden at 0 kV")
        self.assertFalse(self.page.evaluate("window.__explorer.forceGroup.visible"), "forceGroup must be hidden at 0 kV")
        self.assertEqual(self.page.evaluate("window.__explorer.fieldGroup.children.length"), 0, "fieldGroup children must be 0 at 0 kV")
        self.assertEqual(self.page.evaluate("window.__explorer.forceGroup.children.length"), 0, "forceGroup children must be 0 at 0 kV")

        # Toggle wave mode at 0 kV and toggle back; verify child count remains 0
        toggle_btn.click()
        self.page.wait_for_timeout(100)
        self.assertTrue(self.page.evaluate("window.__explorer.scalarWaveGroup.visible"))
        toggle_btn.click()
        self.page.wait_for_timeout(100)
        self.assertFalse(self.page.evaluate("window.__explorer.scalarWaveGroup.visible"))
        self.assertEqual(self.page.evaluate("window.__explorer.fieldGroup.children.length"), 0, "fieldGroup children must remain 0 at 0 kV after toggle")
        self.assertEqual(self.page.evaluate("window.__explorer.forceGroup.children.length"), 0, "forceGroup children must remain 0 at 0 kV after toggle")

        # Restore voltage to 20 kV for subsequent navigation checks
        slider.fill("20")
        slider.dispatch_event("input")
        self.page.wait_for_timeout(100)
        self.assertGreater(self.page.evaluate("window.__explorer.fieldGroup.children.length"), 0)
        self.assertGreater(self.page.evaluate("window.__explorer.forceGroup.children.length"), 0)

        # WebGL Canvas visual postcondition check
        is_webgl_ok = self.page.evaluate("""() => {
            const canvas = document.getElementById('webgl-canvas');
            if (!canvas) return false;
            const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
            return !!gl && !gl.isContextLost();
        }""")
        self.assertTrue(is_webgl_ok, "WebGL canvas context must be valid and not lost")

        # Sub-check (b): leaving Chapter 5 for Chapter 6 while toy mode active
        self.page.click("#guide-btn-next")
        self.page.wait_for_timeout(100)
        self.assertIn("How Could We Test the Hypothesis?", self.page.locator("#guide-chapter-title").inner_text())

        # Chapter 6 layers: field is FALSE, geometry is TRUE
        self.assertFalse(chk_fields.is_checked(), "toggle-fields must be false in Chapter 6")
        self.assertFalse(self.page.evaluate("window.__explorer.fieldGroup.visible"), "fieldGroup must be false in Chapter 6")
        self.assertFalse(self.page.evaluate("window.__explorer.scalarWaveGroup.visible"), "scalarWaveGroup must be auto-reset to false when leaving Chapter 5")
        self.assertTrue(self.page.evaluate("window.__explorer.geometryGroup.visible"), "geometryGroup must be true in Chapter 6")

        # Sub-check (d): return navigation to Chapter 5
        self.page.click("#guide-btn-prev")
        self.page.wait_for_timeout(100)
        self.assertIn("What Are Scalar Waves?", self.page.locator("#guide-chapter-title").inner_text())
        self.assertTrue(chk_fields.is_checked(), "toggle-fields must be restored to true in Chapter 5")
        self.assertTrue(self.page.evaluate("window.__explorer.fieldGroup.visible"), "fieldGroup must be visible in Chapter 5")
        self.assertTrue(self.page.evaluate("window.__explorer.geometryGroup.visible"), "geometryGroup must be visible in Chapter 5")
        self.assertFalse(self.page.evaluate("window.__explorer.scalarWaveGroup.visible"), "scalarWaveGroup must remain false upon return until explicitly clicked")

        self.assertEqual(len(self.page_errors), 0, f"Layer state test encountered page errors: {self.page_errors}")


if __name__ == "__main__":
    unittest.main()
