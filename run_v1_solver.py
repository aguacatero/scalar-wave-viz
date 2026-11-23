#!/usr/bin/env python3
"""run_v1_solver.py - User-facing live V1-B solver launcher for Propulsion Explorer.

Launches the hardened IPv4-loopback HTTP server wired to the accepted V1-B
isolated solver worker (`v1_solver_adapter.create_solver_server`), enabling
arbitrary live 1D parallel-plate and 2D grounded-box P0/P1 solves in the
Propulsion Explorer UI while leaving `run_explorer.py` untouched for V1-A
transport-only lifecycle tests.

Usage:
    python run_v1_solver.py [--port PORT] [--no-browser] [--host HOST]
"""

from __future__ import annotations

import argparse
import signal
import sys
import threading
import time
import webbrowser
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

EXPLORER_DIR = _REPO_ROOT / "explorer"

from v1_solver_adapter import create_solver_server  # noqa: E402
from v1_worker_bridge import validate_loopback_host  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Launch Propulsion Explorer with the live validated P0/P1 V1-B solver bridge."
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
    args = parser.parse_args(argv)

    validate_loopback_host(args.host)

    if not EXPLORER_DIR.exists() or not (EXPLORER_DIR / "index.html").exists():
        print(f"Error: Explorer directory or index.html not found at {EXPLORER_DIR}", file=sys.stderr)
        return 1

    server, port = create_solver_server(args.host, args.port)
    url = f"http://{args.host}:{port}"

    def _handle_sigterm(_signum: int, _frame: object) -> None:
        threading.Thread(target=server.shutdown, daemon=True).start()

    try:
        signal.signal(signal.SIGTERM, _handle_sigterm)
    except (ValueError, OSError):
        pass

    print("=" * 70, flush=True)
    print("  PROPULSION EXPLORER (V1) — SCALAR WAVE VIZ", flush=True)
    print("  Live Validated P0/P1 Electrostatic Solver Bridge", flush=True)
    print("=" * 70, flush=True)
    print(f"  • Serving from:      {EXPLORER_DIR}", flush=True)
    print(f"  • Local URL:         {url}", flush=True)
    print("  • Bridge Stage:      V1-B Live P0/P1 Solver (1D Analytic + 2D Grounded Box)", flush=True)
    print("  • Scientific Status: ESTABLISHED MODEL (P0/P1) + PROVISIONAL 3D SCHEMATIC", flush=True)
    print("  • Whole-Body Thrust: NOT MEASURED / NOT ESTABLISHED", flush=True)
    print("=" * 70, flush=True)
    print("  Press Ctrl+C to stop the server.\n", flush=True)

    if not args.no_browser:
        def open_browser() -> None:
            time.sleep(0.5)
            webbrowser.open(url)

        threading.Thread(target=open_browser, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[Propulsion Explorer V1] Shutting down gracefully...", flush=True)
    finally:
        server.server_close()
        print("[Propulsion Explorer V1] Server stopped.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
