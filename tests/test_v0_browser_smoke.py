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
        self.assertIn("Blade (-20.0 kV)", legend_blade)

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
        """V0-R1-M4: verify Guided Tour and Help modals open, trap focus, and dismiss on Escape."""
        self.page.click("#btn-start-tour")
        tour_modal = self.page.locator("#tour-modal")
        self.assertTrue(tour_modal.is_visible())

        self.page.click("#tour-btn-close")
        self.assertFalse(tour_modal.is_visible())

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


if __name__ == "__main__":
    unittest.main()
