#!/usr/bin/env python3
"""Capture high-resolution screenshots of Propulsion Explorer V0 for assets/ and documentation.

Remediated for Review Round V0 R3 (V0-R2-M3):
- Captures default interactive state with 3D scene, field lines, and force vectors visible.
- Captures Guided Tour modal.
- Captures Whole-Body Force Ledger (Boundary A/B/C separation).
- Captures What-If Sandbox.
- Captures Component Inspector.
- Captures 375x667 Mobile viewport.
"""

from __future__ import annotations

import functools
import http.server
import os
import socket
import socketserver
import sys
import threading
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
EXPLORER_DIR = REPO_ROOT / "explorer"
ASSETS_DIR = REPO_ROOT / "assets"


def find_browser_executable() -> str | None:
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def start_server(port: int) -> http.server.HTTPServer:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(EXPLORER_DIR))
    server = ReusableTCPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def capture_all():
    port = find_free_port()
    server = start_server(port)
    base_url = f"http://127.0.0.1:{port}/index.html"
    print(f"Serving {EXPLORER_DIR} at {base_url}")

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
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

        browser = p.chromium.launch(**launch_kwargs)

        # 1. Desktop context (1280x800)
        context = browser.new_context(viewport={"width": 1280, "height": 800}, device_scale_factor=2)
        page = context.new_page()

        print("Navigating to page...")
        page.goto(base_url)
        page.wait_for_selector("#webgl-canvas")
        page.wait_for_selector(".component-item-btn")
        page.wait_for_selector("#loading-overlay.hidden")
        # Give WebGL and animations 1000ms to settle
        time.sleep(1.0)

        # Verify default toggles are checked
        t_geom = page.locator("#toggle-geometry").is_checked()
        t_field = page.locator("#toggle-fields").is_checked()
        t_force = page.locator("#toggle-forces").is_checked()
        print(f"Default layer states: Geometry={t_geom}, Fields={t_field}, Forces={t_force}")

        # Capture 1: Default 3D scene preview (with all layers ON)
        preview_path = ASSETS_DIR / "propulsion_explorer_v0_preview.png"
        page.screenshot(path=str(preview_path), full_page=False)
        print(f"Captured: {preview_path} ({preview_path.stat().st_size} bytes)")

        # Capture 2: Guided Tour Modal
        page.click("#btn-start-tour")
        page.wait_for_selector("#tour-modal:not(.hidden)")
        time.sleep(0.3)
        tour_path = ASSETS_DIR / "propulsion_explorer_v0_tour.png"
        page.screenshot(path=str(tour_path), full_page=False)
        print(f"Captured: {tour_path} ({tour_path.stat().st_size} bytes)")
        page.keyboard.press("Escape")
        time.sleep(0.3)

        # Capture 3: Force Ledger Tab
        page.click("#tab-btn-ledger")
        page.wait_for_selector("#tab-ledger:not(.hidden)")
        time.sleep(0.3)
        ledger_path = ASSETS_DIR / "propulsion_explorer_v0_ledger.png"
        page.screenshot(path=str(ledger_path), full_page=False)
        print(f"Captured: {ledger_path} ({ledger_path.stat().st_size} bytes)")

        # Capture 4: What-If Sandbox Tab
        page.click("#tab-btn-sandbox")
        page.wait_for_selector("#tab-sandbox:not(.hidden)")
        time.sleep(0.3)
        sandbox_path = ASSETS_DIR / "propulsion_explorer_v0_sandbox.png"
        page.screenshot(path=str(sandbox_path), full_page=False)
        print(f"Captured: {sandbox_path} ({sandbox_path.stat().st_size} bytes)")

        # Capture 5: Component Inspector Tab (select Blade Electrode)
        page.click("#tab-btn-layers")
        time.sleep(0.2)
        page.click(".component-item-btn[data-id='blade_electrode']")
        page.wait_for_selector("#tab-inspector:not(.hidden)")
        time.sleep(0.3)
        inspector_path = ASSETS_DIR / "propulsion_explorer_v0_inspector.png"
        page.screenshot(path=str(inspector_path), full_page=False)
        print(f"Captured: {inspector_path} ({inspector_path.stat().st_size} bytes)")

        context.close()

        # 6. Mobile context (375x667 - iPhone SE / standard narrow)
        mobile_context = browser.new_context(viewport={"width": 375, "height": 667}, device_scale_factor=2)
        mobile_page = mobile_context.new_page()
        mobile_page.goto(base_url)
        mobile_page.wait_for_selector("#webgl-canvas")
        mobile_page.wait_for_selector("#loading-overlay.hidden")
        time.sleep(1.0)
        mobile_path = ASSETS_DIR / "propulsion_explorer_v0_mobile.png"
        mobile_page.screenshot(path=str(mobile_path), full_page=False)
        print(f"Captured: {mobile_path} ({mobile_path.stat().st_size} bytes)")
        mobile_context.close()

        # 7. Mobile context (390x844 - iPhone 12/13/14)
        mobile_390_context = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        mobile_390_page = mobile_390_context.new_page()
        mobile_390_page.goto(base_url)
        mobile_390_page.wait_for_selector("#webgl-canvas")
        mobile_390_page.wait_for_selector("#loading-overlay.hidden")
        time.sleep(1.0)
        mobile_390_path = ASSETS_DIR / "propulsion_explorer_v0_mobile_390.png"
        mobile_390_page.screenshot(path=str(mobile_390_path), full_page=False)
        print(f"Captured: {mobile_390_path} ({mobile_390_path.stat().st_size} bytes)")
        mobile_390_context.close()
        browser.close()

    server.shutdown()
    server.server_close()
    print("All screenshots captured successfully.")


if __name__ == "__main__":
    capture_all()
