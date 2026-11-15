#!/usr/bin/env python3
"""run_explorer.py - Zero-friction local launcher for the Propulsion Explorer 3D (V0).

Serves the explorer web directory using Python's standard library http.server,
automatically finds an open port if needed, and launches the default web browser.

Usage:
    python run_explorer.py [--port PORT] [--no-browser] [--host HOST]
"""

from __future__ import annotations

import argparse
import http.server
import os
import socket
import socketserver
import sys
import threading
import time
import webbrowser
from pathlib import Path


EXPLORER_DIR = Path(__file__).resolve().parent / "explorer"


class ExplorerHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom request handler serving from the explorer directory with caching headers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(EXPLORER_DIR), **kwargs)

    def end_headers(self):
        # Prevent aggressive browser caching during local development
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, format, *args):
        # Concise logging
        if sys.stderr.isatty():
            sys.stderr.write(f"[Propulsion Explorer] {self.address_string()} - {format % args}\n")


def is_port_available(host: str, port: int) -> bool:
    """Check if a local TCP port is available for binding."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            return True
        except OSError:
            return False


def find_available_port(host: str, start_port: int, max_attempts: int = 50) -> int:
    """Find the next open port starting from start_port."""
    for p in range(start_port, start_port + max_attempts):
        if is_port_available(host, p):
            return p
    raise RuntimeError(f"Could not find an available port on {host} between {start_port} and {start_port + max_attempts}")


from v1_worker_bridge import (  # noqa: E402 - local bridge module
    ExplorerHTTPRequestHandler,
    create_v1_http_server,
    validate_loopback_host,
)


def create_server(host: str, port: int, **kwargs):
    """Create a hardened IPv4-loopback server bound to host and port."""
    validate_loopback_host(host)
    selected_port = find_available_port(host, port)
    return create_v1_http_server(host, selected_port, directory=EXPLORER_DIR, **kwargs)


def main():
    parser = argparse.ArgumentParser(
        description="Launch the 3D Propulsion Explorer (V0/V1-A bridge) in your web browser."
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to serve on (default: 8000). Falls back to next open port if busy.",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="IPv4 loopback host interface to bind to (default: 127.0.0.1; supported: 127.0.0.1, localhost).",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Start the server without automatically launching the web browser.",
    )
    args = parser.parse_args()

    validate_loopback_host(args.host)

    if not EXPLORER_DIR.exists() or not (EXPLORER_DIR / "index.html").exists():
        print(f"Error: Explorer directory or index.html not found at {EXPLORER_DIR}", file=sys.stderr)
        sys.exit(1)

    server, port = create_server(args.host, args.port)
    url = f"http://{args.host}:{port}"

    print("=" * 70)
    print("  PROPULSION EXPLORER 3D — SCALAR WAVE VIZ")
    print("  Educational 3D Laboratory for Field & Force Understanding")
    print("=" * 70)
    print(f"  • Serving from:   {EXPLORER_DIR}")
    print(f"  • Local URL:      {url}")
    print("  • Bridge Stage:   V1-A (Transport & Worker Lifecycle Only)")
    print("  • Scientific Status: PROVISIONAL EDUCATIONAL SCENE")
    print("  • Net Thrust:     NOT MEASURED / NOT ESTABLISHED")
    print("=" * 70)
    print("  Press Ctrl+C to stop the server.\n")

    if not args.no_browser:
        def open_browser():
            time.sleep(0.5)
            webbrowser.open(url)
        threading.Thread(target=open_browser, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[Propulsion Explorer] Shutting down gracefully...")
    finally:
        server.server_close()
        print("[Propulsion Explorer] Server stopped.")


if __name__ == "__main__":
    main()
