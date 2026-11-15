"""TDD lifecycle, POSIX spawn FD-transfer, HTTP framing, and V1-SPEC-R5-I1 fault tests for V1-A."""

from __future__ import annotations

import http.client
import json
import os
import selectors
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _list_open_fds() -> set[int]:
    """Return currently open integer file descriptors in this process (Linux/macOS)."""
    for fd_dir in ("/proc/self/fd", "/dev/fd"):
        if os.path.isdir(fd_dir):
            fds = set()
            for entry in os.listdir(fd_dir):
                if entry.isdigit():
                    fds.add(int(entry))
            return fds
    raise RuntimeError("Neither /proc/self/fd nor /dev/fd available on this host")


def _list_open_pipe_inodes() -> dict[int, int]:
    """Return {fd: st_ino} for currently open FIFO/pipe descriptors in this process."""
    import stat

    pipes: dict[int, int] = {}
    for fd in _list_open_fds():
        try:
            st = os.fstat(fd)
        except OSError:
            continue
        if stat.S_ISFIFO(st.st_mode):
            pipes[fd] = st.st_ino
    return pipes


def _is_pid_reaped(pid: int) -> bool:
    """Verify pid is dead AND reaped (no live process, no zombie)."""
    try:
        waited_pid, _ = os.waitpid(pid, os.WNOHANG)
        if waited_pid == 0:
            return False
    except ChildProcessError:
        pass
    try:
        os.kill(pid, 0)
        return False
    except ProcessLookupError:
        return True
    except PermissionError:
        return False


class V1BridgePlatformAndIsolationTests(unittest.TestCase):
    """OS compatibility, documented budget defaults, and V1-A kernel/P2 isolation."""

    def test_defaults_and_platform_constants(self):
        import v1_worker_bridge as bridge

        self.assertEqual(bridge.DEFAULT_RESPONSE_DEADLINE_S, 5.0)
        self.assertEqual(bridge.DEFAULT_WORKER_REAP_TIMEOUT_S, 2.0)
        self.assertEqual(bridge.DEFAULT_TOTAL_READ_DEADLINE_S, 2.0)
        self.assertEqual(bridge.DEFAULT_RESPONSE_WRITE_TIMEOUT_S, 2.0)
        self.assertEqual(bridge.DEFAULT_MAX_ACTIVE_HTTP_WORKERS, 8)
        self.assertEqual(bridge.DEFAULT_MAX_CONCURRENT_COMPUTES, 1)
        self.assertEqual(bridge.MAX_HTTP_BODY_BYTES, 8192)
        self.assertEqual(bridge.MAX_IPC_REQUEST_BYTES, 16384)
        self.assertEqual(bridge.MAX_IPC_RESPONSE_BYTES, 8388608)
        self.assertIn("Linux", bridge.SUPPORTED_SYSTEMS)
        self.assertIn("Darwin", bridge.SUPPORTED_SYSTEMS)
        bridge.ensure_supported_platform()

    def test_windows_platform_rejected_explicitly(self):
        import v1_worker_bridge as bridge

        with mock.patch("v1_worker_bridge.os.name", "nt"):
            with self.assertRaises(RuntimeError) as ctx:
                bridge.ensure_supported_platform()
            self.assertIn("POSIX", str(ctx.exception))

        with mock.patch("v1_worker_bridge.platform.system", return_value="Windows"):
            with self.assertRaises(RuntimeError) as ctx:
                bridge.ensure_supported_platform()
            self.assertIn("Windows", str(ctx.exception))

    def test_v1_a_has_zero_physics_or_p2_imports(self):
        """V1-A builds only transport/lifecycle before V1-B adapters or P2 isolation."""
        for filename in ("v1_worker_bridge.py", "run_explorer.py"):
            source = (REPO_ROOT / filename).read_text(encoding="utf-8")
            self.assertNotIn("electrostatics_baseline", source)
            self.assertNotIn("electrostatics_numerics", source)
            self.assertNotIn("exodus", source.lower())


class V1BridgeHTTPFramingAndSecurityTests(unittest.TestCase):
    """Strict IPv4 loopback binding, Host/Origin, framing, slow-read, and admission limits."""

    def setUp(self):
        from run_explorer import create_server

        self.server, self.port = create_server(
            "127.0.0.1",
            0,
            total_read_deadline_s=0.35,
            response_deadline_s=0.8,
            worker_reap_timeout_s=0.8,
            max_active_http_workers=4,
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2.0)

    def _raw_http_exchange(self, raw_bytes: bytes, timeout: float = 3.0) -> tuple[int, dict[str, str], bytes]:
        with socket.create_connection(("127.0.0.1", self.port), timeout=timeout) as sock:
            sock.sendall(raw_bytes)
            chunks = []
            while True:
                data = sock.recv(4096)
                if not data:
                    break
                chunks.append(data)
        raw_resp = b"".join(chunks)
        head, _, body = raw_resp.partition(b"\r\n\r\n")
        lines = head.decode("iso-8859-1").split("\r\n")
        status_code = int(lines[0].split(" ", 2)[1])
        headers = {}
        for line in lines[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()
        return status_code, headers, body

    def _valid_post_headers(self, body_len: int, content_type: str = "application/json") -> str:
        return (
            f"POST /api/v1/solve HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{self.port}\r\n"
            f"Origin: http://127.0.0.1:{self.port}\r\n"
            f"Content-Type: {content_type}\r\n"
            f"Content-Length: {body_len}\r\n"
            f"Connection: close\r\n\r\n"
        )

    def test_ipv4_loopback_allowlist_rejects_ipv6_wildcard_and_external(self):
        from run_explorer import create_server

        for bad_host in ("::1", "0.0.0.0", "192.168.1.10", "example.com", ""):
            with self.assertRaises(ValueError):
                create_server(bad_host, 0)

    def test_host_and_origin_validation_and_no_cors_wildcard(self):
        body = json.dumps({"request_id": 1, "ping": True}).encode("utf-8")

        # External Host -> 403
        raw_bad_host = (
            f"POST /api/v1/solve HTTP/1.1\r\n"
            f"Host: evil.example:{self.port}\r\n"
            f"Origin: http://127.0.0.1:{self.port}\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Connection: close\r\n\r\n"
        ).encode("ascii") + body
        code, headers, _ = self._raw_http_exchange(raw_bad_host)
        self.assertEqual(code, 403)
        self.assertNotIn("access-control-allow-origin", headers)

        # Missing / external / null Origin -> 403
        for bad_origin in (None, "https://evil.example", "null", f"https://127.0.0.1:{self.port}", f"http://127.0.0.1:{self.port + 1}"):
            origin_line = "" if bad_origin is None else f"Origin: {bad_origin}\r\n"
            req = (
                f"POST /api/v1/solve HTTP/1.1\r\n"
                f"Host: 127.0.0.1:{self.port}\r\n"
                f"{origin_line}"
                f"Content-Type: application/json\r\n"
                f"Content-Length: {len(body)}\r\n"
                f"Connection: close\r\n\r\n"
            ).encode("ascii") + body
            code, headers, _ = self._raw_http_exchange(req)
            self.assertEqual(code, 403, f"Failed for origin={bad_origin!r}")
            self.assertNotEqual(headers.get("access-control-allow-origin"), "*")

    def test_content_type_length_chunked_and_json_validation(self):
        # Non-JSON -> 415
        body = b"hello=world"
        code, _, _ = self._raw_http_exchange(
            self._valid_post_headers(len(body), "text/plain").encode("ascii") + body
        )
        self.assertEqual(code, 415)

        # Transfer-Encoding: chunked -> 501
        chunked_req = (
            f"POST /api/v1/solve HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{self.port}\r\n"
            f"Origin: http://127.0.0.1:{self.port}\r\n"
            f"Content-Type: application/json\r\n"
            f"Transfer-Encoding: chunked\r\n"
            f"Connection: close\r\n\r\n"
            f"2\r\n{{}}\r\n0\r\n\r\n"
        ).encode("ascii")
        code, _, _ = self._raw_http_exchange(chunked_req)
        self.assertEqual(code, 501)

        # Missing Content-Length -> 411
        no_len_req = (
            f"POST /api/v1/solve HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{self.port}\r\n"
            f"Origin: http://127.0.0.1:{self.port}\r\n"
            f"Content-Type: application/json\r\n"
            f"Connection: close\r\n\r\n"
        ).encode("ascii")
        code, _, _ = self._raw_http_exchange(no_len_req)
        self.assertEqual(code, 411)

        # Duplicate / negative / non-digit Content-Length -> 400
        dup_len_req = (
            f"POST /api/v1/solve HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{self.port}\r\n"
            f"Origin: http://127.0.0.1:{self.port}\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: 2\r\n"
            f"Content-Length: 2\r\n"
            f"Connection: close\r\n\r\n{{}}"
        ).encode("ascii")
        code, _, _ = self._raw_http_exchange(dup_len_req)
        self.assertEqual(code, 400)

        neg_len_req = self._valid_post_headers(2).replace("Content-Length: 2", "Content-Length: -5").encode("ascii") + b"{}"
        code, _, _ = self._raw_http_exchange(neg_len_req)
        self.assertEqual(code, 400)

        # > 8192 bytes -> 413
        code, _, _ = self._raw_http_exchange(self._valid_post_headers(8193).encode("ascii") + b"{}")
        self.assertEqual(code, 413)

        # Duplicate JSON key -> 400 DUPLICATE_KEY
        dup_json = b'{"request_id": 1, "request_id": 2}'
        code, _, resp_body = self._raw_http_exchange(self._valid_post_headers(len(dup_json)).encode("ascii") + dup_json)
        self.assertEqual(code, 400)
        self.assertEqual(json.loads(resp_body)["error"]["code"], "DUPLICATE_KEY")

        # NaN constant -> 400
        nan_json = b'{"request_id": 1, "x": NaN}'
        code, _, _ = self._raw_http_exchange(self._valid_post_headers(len(nan_json)).encode("ascii") + nan_json)
        self.assertEqual(code, 400)

    def test_slow_trickle_header_and_body_rejected_with_408_within_deadline(self):
        # Slow-trickle header
        t0 = time.monotonic()
        with socket.create_connection(("127.0.0.1", self.port), timeout=2.0) as sock:
            sock.sendall(b"POST /api/v1/solve HTTP/1.1\r\nHost: 127.0.0.")
            time.sleep(0.5)
            chunks = []
            while True:
                data = sock.recv(4096)
                if not data:
                    break
                chunks.append(data)
        elapsed = time.monotonic() - t0
        self.assertLess(elapsed, 1.5)
        raw = b"".join(chunks)
        self.assertIn(b"408", raw.split(b"\r\n", 1)[0])

        # Slow-trickle body after full headers
        t1 = time.monotonic()
        body = b'{"request_id": 1, "echo": "slow"}'
        hdr = self._valid_post_headers(len(body)).encode("ascii")
        with socket.create_connection(("127.0.0.1", self.port), timeout=2.0) as sock:
            sock.sendall(hdr + body[:5])
            time.sleep(0.5)
            chunks = []
            while True:
                data = sock.recv(4096)
                if not data:
                    break
                chunks.append(data)
        elapsed_body = time.monotonic() - t1
        self.assertLess(elapsed_body, 1.5)
        self.assertIn(b"408", b"".join(chunks).split(b"\r\n", 1)[0])

    def test_http_worker_semaphore_saturation_returns_503(self):
        # Occupy all 4 HTTP worker slots with open half-sent POST bodies (which hold up to 0.35s)
        held_sockets = []
        try:
            body_hdr = self._valid_post_headers(100).encode("ascii")
            for _ in range(4):
                s = socket.create_connection(("127.0.0.1", self.port), timeout=2.0)
                s.sendall(body_hdr + b"{")
                held_sockets.append(s)
            time.sleep(0.08)

            # 5th concurrent HTTP connection should be immediately rejected with 503
            payload = b'{"request_id": 9}'
            code, _, resp_body = self._raw_http_exchange(
                self._valid_post_headers(len(payload)).encode("ascii") + payload,
                timeout=1.5,
            )
            self.assertEqual(code, 503)
            self.assertEqual(json.loads(resp_body)["error"]["code"], "HTTP_ADMISSION_SATURATED")
        finally:
            for s in held_sockets:
                s.close()


class V1WorkerLifecycleAndR5I1Tests(unittest.TestCase):
    """Executable POSIX spawn FD transfer, bounded startup, IPC framing, poison, and race tests."""

    def setUp(self):
        self._tmp_files: list[Path] = []

    def tearDown(self):
        for p in self._tmp_files:
            try:
                p.unlink()
            except OSError:
                pass

    def _make_fault_worker_script(self, script_body: str) -> list[str]:
        fd, path_str = tempfile.mkstemp(prefix="v1_fault_worker_", suffix=".py")
        os.close(fd)
        p = Path(path_str)
        p.write_text(script_body, encoding="utf-8")
        self._tmp_files.append(p)
        return [sys.executable, str(p)]

    def test_real_posix_spawn_fd_transfer_ownership_reuse_and_no_leaks(self):
        """V1-SPEC-R5-I1: explicit FD transfer preserves pipe inodes, closes unused ends, zero FD leaks."""
        import v1_worker_bridge as bridge

        baseline_pipes = _list_open_pipe_inodes()
        mgr = bridge.WorkerManager(response_deadline_s=2.0, worker_reap_timeout_s=1.0)
        try:
            r1 = mgr.execute("/api/v1/solve", {"request_id": 1, "action": "inspect_fds"})
            self.assertEqual(r1.status_code, 200)
            p1 = r1.payload
            self.assertEqual(p1["status"], "V1_A_TRANSPORT_ONLY")
            pid1 = p1["worker_pid"]
            self.assertGreater(pid1, 0)
            self.assertTrue(p1["parent_closed_unused_ends"])
            # Child received exact same pipe inodes created in parent
            self.assertEqual(p1["child_req_ino"], p1["expected_req_ino"])
            self.assertEqual(p1["child_resp_ino"], p1["expected_resp_ino"])
            self.assertNotEqual(p1["child_req_ino"], p1["child_resp_ino"])
            # Child does NOT hold parent write/read pipe ends or parent extra pipes
            self.assertEqual(sorted(p1["child_open_pipe_inos"]), sorted([p1["child_req_ino"], p1["child_resp_ino"]]))

            # Sequential second request reuses exact same healthy worker + channel
            r2 = mgr.execute("/api/v1/study", {"request_id": 2, "action": "inspect_fds"})
            self.assertEqual(r2.status_code, 200)
            self.assertEqual(r2.payload["worker_pid"], pid1)
            self.assertEqual(r2.payload["ipc_token"], p1["ipc_token"] + 1)
        finally:
            mgr.shutdown()

        self.assertTrue(_is_pid_reaped(pid1))
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

    def test_stalled_launch_before_pid_bounded_poison_and_late_child_reaped(self):
        """V1-SPEC-R5-I1: launch stall before PID creation bounds caller, poisons fail-closed, reaps late child."""
        import v1_worker_bridge as bridge

        baseline_pipes = _list_open_pipe_inodes()
        late_proc_holder: list[subprocess.Popen] = []
        launch_released = threading.Event()

        def stalled_pre_pid_launch(cmd, pass_fds):
            # Simulate Popen blocking beyond deadline before returning child
            time.sleep(0.45)
            proc = subprocess.Popen(cmd, pass_fds=pass_fds, close_fds=True)
            late_proc_holder.append(proc)
            launch_released.set()
            return proc

        mgr = bridge.WorkerManager(
            response_deadline_s=0.18,
            worker_reap_timeout_s=0.5,
            launch_fn=stalled_pre_pid_launch,
        )
        try:
            t0 = time.monotonic()
            res = mgr.execute("/api/v1/solve", {"request_id": 1})
            elapsed = time.monotonic() - t0
            self.assertLess(elapsed, 0.35)
            self.assertEqual(res.status_code, 503)
            self.assertEqual(res.payload["error"]["code"], "WORKER_UNAVAILABLE_POISONED")

            # Subsequent request immediately fails closed with poison (never spawns second worker)
            res2 = mgr.execute("/api/v1/solve", {"request_id": 2})
            self.assertEqual(res2.status_code, 503)
            self.assertEqual(res2.payload["error"]["code"], "WORKER_UNAVAILABLE_POISONED")

            self.assertTrue(launch_released.wait(timeout=1.5))
            time.sleep(0.15)
            self.assertEqual(len(late_proc_holder), 1)
            self.assertTrue(_is_pid_reaped(late_proc_holder[0].pid))
        finally:
            mgr.shutdown()

        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

    def test_stalled_launch_after_pid_creation_and_handshake_stall(self):
        """V1-SPEC-R5-I1: stalls after PID creation (both in launch hook and child READY) reap child with zero orphans."""
        import v1_worker_bridge as bridge

        baseline_pipes = _list_open_pipe_inodes()

        # Case A: Handshake stall in real child after PID creation -> 504 + verified reap + clean recovery possible
        silent_cmd = self._make_fault_worker_script(
            "import time\n"
            "time.sleep(5)\n"
        )
        mgr_a = bridge.WorkerManager(
            response_deadline_s=0.2,
            worker_reap_timeout_s=0.5,
            custom_worker_cmd=silent_cmd,
        )
        try:
            t0 = time.monotonic()
            res = mgr_a.execute("/api/v1/solve", {"request_id": 1})
            elapsed = time.monotonic() - t0
            self.assertEqual(res.status_code, 504)
            self.assertEqual(res.payload["error"]["code"], "SOLVE_DEADLINE_EXCEEDED")
            self.assertLess(elapsed, 0.75)
            self.assertEqual(len(mgr_a.spawned_pids), 1)
            self.assertTrue(_is_pid_reaped(mgr_a.spawned_pids[0]))
        finally:
            mgr_a.shutdown()
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

        # Case B: Launch hook registers PID then stalls past deadline -> child reaped, launch status poisoned cleanly
        hook_proc: list[subprocess.Popen] = []

        def post_pid_stalled_launch(cmd, pass_fds, register_pid=None):
            proc = subprocess.Popen(cmd, pass_fds=pass_fds, close_fds=True)
            hook_proc.append(proc)
            if register_pid is not None:
                register_pid(proc)
            time.sleep(0.45)
            return proc

        mgr_b = bridge.WorkerManager(
            response_deadline_s=0.18,
            worker_reap_timeout_s=0.5,
            launch_fn=post_pid_stalled_launch,
        )
        try:
            res_b = mgr_b.execute("/api/v1/solve", {"request_id": 2})
            self.assertEqual(res_b.status_code, 503)
            self.assertEqual(res_b.payload["error"]["code"], "WORKER_UNAVAILABLE_POISONED")
            time.sleep(0.45)
            self.assertEqual(len(hook_proc), 1)
            self.assertTrue(_is_pid_reaped(hook_proc[0].pid))
        finally:
            mgr_b.shutdown()
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

    def test_blocked_send_stall_aborts_reaps_and_respawns_fresh_pipes(self):
        """V1-SPEC-R4-M1 / R5-I1: blocked request write aborts at deadline, reaps, respawns once with new pipes."""
        import v1_worker_bridge as bridge

        baseline_pipes = _list_open_pipe_inodes()

        # Worker sends READY cleanly, then sleeps without reading stdin pipe while parent encounters backpressure
        stall_script = self._make_fault_worker_script(
            "import argparse, json, os, struct, time\n"
            "p = argparse.ArgumentParser()\n"
            "p.add_argument('--req-fd', type=int); p.add_argument('--resp-fd', type=int)\n"
            "a, _ = p.parse_known_args()\n"
            "ready = json.dumps({'type':'READY','pid':os.getpid(),'req_ino':os.fstat(a.req_fd).st_ino,'resp_ino':os.fstat(a.resp_fd).st_ino}).encode()\n"
            "os.write(a.resp_fd, struct.pack('>I', len(ready)) + ready)\n"
            "time.sleep(5)\n"
        )
        mgr = bridge.WorkerManager(
            response_deadline_s=0.25,
            worker_reap_timeout_s=0.6,
            custom_worker_cmd=stall_script,
        )
        try:
            # Force pipe backpressure (BlockingIOError on write) even for small payload after READY
            with mock.patch("v1_worker_bridge.os.write", side_effect=BlockingIOError):
                res = mgr.execute("/api/v1/solve", {"request_id": 1})
            self.assertEqual(res.status_code, 504)
            self.assertEqual(res.payload["error"]["code"], "SOLVE_DEADLINE_EXCEEDED")
            first_pid = mgr.spawned_pids[0]
            self.assertTrue(_is_pid_reaped(first_pid))

            # Switch to normal worker on next request (simulating recovery cleanly after faulty worker reaped)
            mgr.custom_worker_cmd = None
            res2 = mgr.execute("/api/v1/solve", {"request_id": 2})
            self.assertEqual(res2.status_code, 200)
            second_pid = res2.payload["worker_pid"]
            self.assertNotEqual(first_pid, second_pid)
            self.assertTrue(_is_pid_reaped(first_pid))
        finally:
            mgr.shutdown()

        self.assertTrue(_is_pid_reaped(second_pid))
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

    def test_partial_header_and_partial_body_stalls_timeout_and_recover(self):
        """V1-SPEC-R4-M1: 1-3 byte partial header stall and incomplete body stall both return 504 cleanly."""
        import v1_worker_bridge as bridge

        baseline_pipes = _list_open_pipe_inodes()

        partial_header_cmd = self._make_fault_worker_script(
            "import argparse, json, os, struct, time\n"
            "def read_exact(fd, n):\n"
            "  buf = bytearray()\n"
            "  while len(buf) < n:\n"
            "    c = os.read(fd, n - len(buf))\n"
            "    if not c: raise EOFError()\n"
            "    buf.extend(c)\n"
            "  return bytes(buf)\n"
            "p = argparse.ArgumentParser()\n"
            "p.add_argument('--req-fd', type=int); p.add_argument('--resp-fd', type=int)\n"
            "a, _ = p.parse_known_args()\n"
            "ready = json.dumps({'type':'READY','pid':os.getpid(),'req_ino':os.fstat(a.req_fd).st_ino,'resp_ino':os.fstat(a.resp_fd).st_ino}).encode()\n"
            "os.write(a.resp_fd, struct.pack('>I', len(ready)) + ready)\n"
            "n = struct.unpack('>I', read_exact(a.req_fd, 4))[0]\n"
            "read_exact(a.req_fd, n)\n"
            "os.write(a.resp_fd, b'\\x00\\x00')\n"
            "time.sleep(5)\n"
        )
        partial_body_cmd = self._make_fault_worker_script(
            "import argparse, json, os, struct, time\n"
            "def read_exact(fd, n):\n"
            "  buf = bytearray()\n"
            "  while len(buf) < n:\n"
            "    c = os.read(fd, n - len(buf))\n"
            "    if not c: raise EOFError()\n"
            "    buf.extend(c)\n"
            "  return bytes(buf)\n"
            "p = argparse.ArgumentParser()\n"
            "p.add_argument('--req-fd', type=int); p.add_argument('--resp-fd', type=int)\n"
            "a, _ = p.parse_known_args()\n"
            "ready = json.dumps({'type':'READY','pid':os.getpid(),'req_ino':os.fstat(a.req_fd).st_ino,'resp_ino':os.fstat(a.resp_fd).st_ino}).encode()\n"
            "os.write(a.resp_fd, struct.pack('>I', len(ready)) + ready)\n"
            "n = struct.unpack('>I', read_exact(a.req_fd, 4))[0]\n"
            "read_exact(a.req_fd, n)\n"
            "os.write(a.resp_fd, struct.pack('>I', 500) + b'partial')\n"
            "time.sleep(5)\n"
        )

        for label, cmd in (("partial_header", partial_header_cmd), ("partial_body", partial_body_cmd)):
            with self.subTest(case=label):
                mgr = bridge.WorkerManager(
                    response_deadline_s=0.25,
                    worker_reap_timeout_s=0.6,
                    custom_worker_cmd=cmd,
                )
                try:
                    t0 = time.monotonic()
                    res = mgr.execute("/api/v1/solve", {"request_id": 1})
                    elapsed = time.monotonic() - t0
                    self.assertEqual(res.status_code, 504)
                    self.assertEqual(res.payload["error"]["code"], "SOLVE_DEADLINE_EXCEEDED")
                    self.assertLess(elapsed, 0.85)
                    self.assertTrue(_is_pid_reaped(mgr.spawned_pids[0]))

                    mgr.custom_worker_cmd = None
                    res2 = mgr.execute("/api/v1/solve", {"request_id": 2})
                    self.assertEqual(res2.status_code, 200)
                finally:
                    mgr.shutdown()
                for pid in mgr.spawned_pids:
                    self.assertTrue(_is_pid_reaped(pid))
                self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

    def test_eof_crash_zero_oversize_frame_and_token_mismatch_recovery(self):
        """Worker crash (EOF), 0-length, >MAX_IPC_RESPONSE_BYTES, and ipc_token mismatch recover without leaks."""
        import v1_worker_bridge as bridge

        baseline_pipes = _list_open_pipe_inodes()

        eof_cmd = self._make_fault_worker_script(
            "import argparse, json, os, struct\n"
            "p = argparse.ArgumentParser()\n"
            "p.add_argument('--req-fd', type=int); p.add_argument('--resp-fd', type=int)\n"
            "a, _ = p.parse_known_args()\n"
            "ready = json.dumps({'type':'READY','pid':os.getpid(),'req_ino':os.fstat(a.req_fd).st_ino,'resp_ino':os.fstat(a.resp_fd).st_ino}).encode()\n"
            "os.write(a.resp_fd, struct.pack('>I', len(ready)) + ready)\n"
            "os._exit(2)\n"
        )
        zero_frame_cmd = self._make_fault_worker_script(
            "import argparse, json, os, struct\n"
            "p = argparse.ArgumentParser()\n"
            "p.add_argument('--req-fd', type=int); p.add_argument('--resp-fd', type=int)\n"
            "a, _ = p.parse_known_args()\n"
            "ready = json.dumps({'type':'READY','pid':os.getpid(),'req_ino':os.fstat(a.req_fd).st_ino,'resp_ino':os.fstat(a.resp_fd).st_ino}).encode()\n"
            "os.write(a.resp_fd, struct.pack('>I', len(ready)) + ready)\n"
            "os.read(a.req_fd, 4096)\n"
            "os.write(a.resp_fd, struct.pack('>I', 0))\n"
        )
        oversize_frame_cmd = self._make_fault_worker_script(
            "import argparse, json, os, struct\n"
            "p = argparse.ArgumentParser()\n"
            "p.add_argument('--req-fd', type=int); p.add_argument('--resp-fd', type=int)\n"
            "a, _ = p.parse_known_args()\n"
            "ready = json.dumps({'type':'READY','pid':os.getpid(),'req_ino':os.fstat(a.req_fd).st_ino,'resp_ino':os.fstat(a.resp_fd).st_ino}).encode()\n"
            "os.write(a.resp_fd, struct.pack('>I', len(ready)) + ready)\n"
            "os.read(a.req_fd, 4096)\n"
            "os.write(a.resp_fd, struct.pack('>I', 9_000_000))\n"
        )
        bad_token_cmd = self._make_fault_worker_script(
            "import argparse, json, os, struct\n"
            "p = argparse.ArgumentParser()\n"
            "p.add_argument('--req-fd', type=int); p.add_argument('--resp-fd', type=int)\n"
            "a, _ = p.parse_known_args()\n"
            "ready = json.dumps({'type':'READY','pid':os.getpid(),'req_ino':os.fstat(a.req_fd).st_ino,'resp_ino':os.fstat(a.resp_fd).st_ino}).encode()\n"
            "os.write(a.resp_fd, struct.pack('>I', len(ready)) + ready)\n"
            "os.read(a.req_fd, 4096)\n"
            "bad = json.dumps({'ipc_token': 999999, 'status': 'OK'}).encode()\n"
            "os.write(a.resp_fd, struct.pack('>I', len(bad)) + bad)\n"
        )

        for label, cmd, expected_code in (
            ("eof_crash", eof_cmd, "WORKER_CRASHED"),
            ("zero_frame", zero_frame_cmd, "IPC_PROTOCOL_ERROR"),
            ("oversize_frame", oversize_frame_cmd, "IPC_PROTOCOL_ERROR"),
            ("token_mismatch", bad_token_cmd, "IPC_PROTOCOL_ERROR"),
        ):
            with self.subTest(case=label):
                mgr = bridge.WorkerManager(response_deadline_s=1.0, worker_reap_timeout_s=0.6, custom_worker_cmd=cmd)
                try:
                    res = mgr.execute("/api/v1/solve", {"request_id": 1})
                    self.assertEqual(res.status_code, 500)
                    self.assertEqual(res.payload["error"]["code"], expected_code)
                    self.assertTrue(_is_pid_reaped(mgr.spawned_pids[0]))

                    mgr.custom_worker_cmd = None
                    res_ok = mgr.execute("/api/v1/solve", {"request_id": 2})
                    self.assertEqual(res_ok.status_code, 200)
                finally:
                    mgr.shutdown()
                for pid in mgr.spawned_pids:
                    self.assertTrue(_is_pid_reaped(pid))
                self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

    def test_failed_kill_or_reap_poisons_and_precedes_429_for_concurrent_callers(self):
        """Failed proc.kill() / failed reap permanently poisons worker; 503 strictly precedes 429."""
        import v1_worker_bridge as bridge
        from run_explorer import create_server

        hang_cmd = self._make_fault_worker_script(
            "import time\n"
            "time.sleep(5)\n"
        )

        # Simulate proc.kill() raising OSError and reaping failing, while test cleans up real PID afterwards
        real_procs: list[subprocess.Popen] = []

        def track_launch(cmd, pass_fds):
            p = subprocess.Popen(cmd, pass_fds=pass_fds, close_fds=True)
            real_procs.append(p)
            return p

        def failing_kill(proc):
            raise OSError("Simulated EPERM killing child")

        mgr = bridge.WorkerManager(
            response_deadline_s=0.15,
            worker_reap_timeout_s=0.15,
            custom_worker_cmd=hang_cmd,
            launch_fn=track_launch,
            kill_fn=failing_kill,
        )
        server, port = create_server(
            "127.0.0.1",
            0,
            worker_manager=mgr,
            total_read_deadline_s=1.0,
        )
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        try:
            def post_solve(req_id: int) -> tuple[int, dict]:
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3.0)
                try:
                    body = json.dumps({"request_id": req_id}).encode("utf-8")
                    conn.request(
                        "POST",
                        "/api/v1/solve",
                        body=body,
                        headers={
                            "Host": f"127.0.0.1:{port}",
                            "Origin": f"http://127.0.0.1:{port}",
                            "Content-Type": "application/json",
                            "Content-Length": str(len(body)),
                        },
                    )
                    resp = conn.getresponse()
                    return resp.status, json.loads(resp.read().decode("utf-8"))
                finally:
                    conn.close()

            status1, payload1 = post_solve(1)
            self.assertEqual(status1, 503)
            self.assertEqual(payload1["error"]["code"], "WORKER_UNAVAILABLE_POISONED")
            self.assertEqual(len(real_procs), 1)

            # Hammer with concurrent callers — ALL must receive 503 WORKER_UNAVAILABLE_POISONED, NEVER 429
            results: list[tuple[int, dict]] = []
            lock = threading.Lock()

            def caller(i: int):
                r = post_solve(i)
                with lock:
                    results.append(r)

            threads = [threading.Thread(target=caller, args=(i,)) for i in range(2, 8)]
            for th in threads:
                th.start()
            for th in threads:
                th.join(timeout=3.0)

            self.assertEqual(len(results), 6)
            for st, pl in results:
                self.assertEqual(st, 503)
                self.assertEqual(pl["error"]["code"], "WORKER_UNAVAILABLE_POISONED")
            # Zero duplicate workers spawned
            self.assertEqual(len(mgr.spawned_pids), 1)
        finally:
            server.shutdown()
            server.server_close()
            t.join(timeout=2.0)
            for p in real_procs:
                if p.poll() is None:
                    p.kill()
                    p.wait(timeout=2.0)

    def test_concurrent_solve_and_study_returns_429_with_single_active_worker(self):
        """Concurrent /api/v1/solve + /api/v1/study rejects second request with 429 while first gets 200."""
        import v1_worker_bridge as bridge
        from run_explorer import create_server

        slow_ok_cmd = self._make_fault_worker_script(
            "import argparse, json, os, struct, time\n"
            "def read_exact(fd, n):\n"
            "  buf = bytearray()\n"
            "  while len(buf) < n:\n"
            "    c = os.read(fd, n - len(buf))\n"
            "    if not c: raise EOFError()\n"
            "    buf.extend(c)\n"
            "  return bytes(buf)\n"
            "p = argparse.ArgumentParser()\n"
            "p.add_argument('--req-fd', type=int); p.add_argument('--resp-fd', type=int)\n"
            "a, _ = p.parse_known_args()\n"
            "ready = json.dumps({'type':'READY','pid':os.getpid(),'req_ino':os.fstat(a.req_fd).st_ino,'resp_ino':os.fstat(a.resp_fd).st_ino}).encode()\n"
            "os.write(a.resp_fd, struct.pack('>I', len(ready)) + ready)\n"
            "while True:\n"
            "  try: hdr = read_exact(a.req_fd, 4)\n"
            "  except EOFError: break\n"
            "  n = struct.unpack('>I', hdr)[0]\n"
            "  req = json.loads(read_exact(a.req_fd, n).decode())\n"
            "  time.sleep(0.35)\n"
            "  out = json.dumps({'ipc_token': req['ipc_token'], 'status': 'V1_A_TRANSPORT_ONLY', 'worker_pid': os.getpid()}).encode()\n"
            "  os.write(a.resp_fd, struct.pack('>I', len(out)) + out)\n"
        )
        baseline_pipes = _list_open_pipe_inodes()
        mgr = bridge.WorkerManager(response_deadline_s=2.0, worker_reap_timeout_s=0.6, custom_worker_cmd=slow_ok_cmd)
        server, port = create_server("127.0.0.1", 0, worker_manager=mgr)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        try:
            outcomes: dict[str, tuple[int, dict]] = {}

            def hit(endpoint: str, req_id: int):
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3.0)
                try:
                    body = json.dumps({"request_id": req_id}).encode("utf-8")
                    conn.request(
                        "POST",
                        endpoint,
                        body=body,
                        headers={
                            "Host": f"127.0.0.1:{port}",
                            "Origin": f"http://127.0.0.1:{port}",
                            "Content-Type": "application/json",
                            "Content-Length": str(len(body)),
                        },
                    )
                    resp = conn.getresponse()
                    outcomes[endpoint] = (resp.status, json.loads(resp.read().decode("utf-8")))
                finally:
                    conn.close()

            t1 = threading.Thread(target=hit, args=("/api/v1/solve", 1))
            t1.start()
            time.sleep(0.10)
            t2 = threading.Thread(target=hit, args=("/api/v1/study", 2))
            t2.start()
            t1.join(timeout=3.0)
            t2.join(timeout=3.0)

            self.assertEqual(outcomes["/api/v1/solve"][0], 200)
            self.assertEqual(outcomes["/api/v1/study"][0], 429)
            self.assertEqual(len(mgr.spawned_pids), 1)
        finally:
            server.shutdown()
            server.server_close()
            t.join(timeout=2.0)

        for pid in mgr.spawned_pids:
            self.assertTrue(_is_pid_reaped(pid))
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

    def test_shutdown_and_respawn_race_containment_zero_orphans_or_leaks(self):
        """Shutdown racing against active compute/respawn raises no unhandled errors and leaves 0 orphans/leaks."""
        import v1_worker_bridge as bridge

        baseline_pipes = _list_open_pipe_inodes()
        mgr = bridge.WorkerManager(response_deadline_s=2.0, worker_reap_timeout_s=0.6)

        res1 = mgr.execute("/api/v1/solve", {"request_id": 1})
        self.assertEqual(res1.status_code, 200)

        results: list[int] = []

        def storm_call(req_id: int):
            r = mgr.execute("/api/v1/solve", {"request_id": req_id, "delay_s": 0.4})
            results.append(r.status_code)

        th = threading.Thread(target=storm_call, args=(2,))
        th.start()
        time.sleep(0.08)
        mgr.shutdown()
        th.join(timeout=2.0)

        self.assertEqual(len(results), 1)
        self.assertIn(results[0], (500, 503))

        # Calls after shutdown immediately fail closed
        after = mgr.execute("/api/v1/solve", {"request_id": 3})
        self.assertEqual(after.status_code, 503)
        for pid in mgr.spawned_pids:
            self.assertTrue(_is_pid_reaped(pid))
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

    def test_http_response_write_timeout_does_not_poison_or_kill_worker(self):
        """Slow/broken HTTP response socket write is separated from worker compute/teardown budgets."""
        import v1_worker_bridge as bridge
        from run_explorer import create_server

        baseline_pipes = _list_open_pipe_inodes()
        mgr = bridge.WorkerManager(response_deadline_s=2.0, worker_reap_timeout_s=0.6)
        server, port = create_server(
            "127.0.0.1",
            0,
            worker_manager=mgr,
            response_write_timeout_s=0.05,
        )
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        try:
            body = json.dumps({"request_id": 10}).encode("utf-8")
            with mock.patch.object(
                bridge.ExplorerHTTPRequestHandler,
                "_send_json_response",
                side_effect=TimeoutError("simulated client write stall"),
            ):
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2.0)
                try:
                    conn.request(
                        "POST",
                        "/api/v1/solve",
                        body=body,
                        headers={
                            "Host": f"127.0.0.1:{port}",
                            "Origin": f"http://127.0.0.1:{port}",
                            "Content-Type": "application/json",
                            "Content-Length": str(len(body)),
                        },
                    )
                    with self.assertRaises((http.client.HTTPException, OSError)):
                        conn.getresponse()
                finally:
                    conn.close()

            self.assertEqual(len(mgr.spawned_pids), 1)
            first_pid = mgr.spawned_pids[0]

            # Healthy worker must remain alive, unpoisoned, and reusable on the next HTTP call
            conn2 = http.client.HTTPConnection("127.0.0.1", port, timeout=2.0)
            try:
                body2 = json.dumps({"request_id": 11}).encode("utf-8")
                conn2.request(
                    "POST",
                    "/api/v1/solve",
                    body=body2,
                    headers={
                        "Host": f"127.0.0.1:{port}",
                        "Origin": f"http://127.0.0.1:{port}",
                        "Content-Type": "application/json",
                        "Content-Length": str(len(body2)),
                    },
                )
                resp2 = conn2.getresponse()
                payload2 = json.loads(resp2.read().decode("utf-8"))
                self.assertEqual(resp2.status, 200)
                self.assertEqual(payload2["worker_pid"], first_pid)
            finally:
                conn2.close()
        finally:
            server.shutdown()
            server.server_close()
            t.join(timeout=2.0)

        self.assertTrue(_is_pid_reaped(first_pid))
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

    def test_multi_cycle_fault_stress_zero_duplicate_workers_or_leaks(self):
        """Alternating worker crashes/timeouts/valid executes maintains <=1 live worker and zero leaks."""
        import v1_worker_bridge as bridge

        baseline_pipes = _list_open_pipe_inodes()
        eof_cmd = self._make_fault_worker_script(
            "import argparse, json, os, struct\n"
            "p = argparse.ArgumentParser()\n"
            "p.add_argument('--req-fd', type=int); p.add_argument('--resp-fd', type=int)\n"
            "a, _ = p.parse_known_args()\n"
            "ready = json.dumps({'type':'READY','pid':os.getpid(),'req_ino':os.fstat(a.req_fd).st_ino,'resp_ino':os.fstat(a.resp_fd).st_ino}).encode()\n"
            "os.write(a.resp_fd, struct.pack('>I', len(ready)) + ready)\n"
            "os.read(a.req_fd, 4096)\n"
            "os._exit(3)\n"
        )
        mgr = bridge.WorkerManager(response_deadline_s=0.35, worker_reap_timeout_s=0.6)
        try:
            for idx in range(3):
                mgr.custom_worker_cmd = None
                res_ok = mgr.execute("/api/v1/solve", {"request_id": idx * 2 + 1})
                self.assertEqual(res_ok.status_code, 200)
                live_pids = [p for p in mgr.spawned_pids if not _is_pid_reaped(p)]
                self.assertLessEqual(len(live_pids), 1)

                res_timeout = mgr.execute("/api/v1/study", {"request_id": idx * 2 + 2, "delay_s": 1.0})
                self.assertEqual(res_timeout.status_code, 504)
                live_pids = [p for p in mgr.spawned_pids if not _is_pid_reaped(p)]
                self.assertEqual(len(live_pids), 0)

                mgr.custom_worker_cmd = eof_cmd
                res_eof = mgr.execute("/api/v1/solve", {"request_id": idx * 2 + 100})
                self.assertEqual(res_eof.status_code, 500)
                live_pids = [p for p in mgr.spawned_pids if not _is_pid_reaped(p)]
                self.assertEqual(len(live_pids), 0)
        finally:
            mgr.shutdown()

        for pid in mgr.spawned_pids:
            self.assertTrue(_is_pid_reaped(pid))
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)


if __name__ == "__main__":
    unittest.main()
