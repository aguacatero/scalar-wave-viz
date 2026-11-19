"""TDD lifecycle, POSIX spawn FD-transfer, HTTP framing, and V1-SPEC-R5-I1 fault tests for V1-A."""

from __future__ import annotations

import http.client
import errno
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
            buf = bytearray()
            while True:
                try:
                    data = sock.recv(4096)
                except ConnectionResetError:
                    if buf:
                        break
                    raise
                if not data:
                    break
                buf.extend(data)
                if b"\r\n\r\n" in buf:
                    head_raw, _, body_part = bytes(buf).partition(b"\r\n\r\n")
                    for hline in head_raw.decode("iso-8859-1").split("\r\n")[1:]:
                        if hline.lower().startswith("content-length:"):
                            cl = int(hline.split(":", 1)[1].strip())
                            if len(body_part) >= cl:
                                break
                    else:
                        continue
                    break
        raw_resp = bytes(buf)
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

        # NaN / exponent overflow / nested overflow -> 400 INVALID_JSON BEFORE worker admission
        for bad_json in (
            b'{"request_id": 1, "x": NaN}',
            b'{"request_id": 1, "x": 1e309}',
            b'{"request_id": 1, "x": -1e309}',
            b'{"request_id": 1, "nested": [{"val": 1e309}]}',
        ):
            code, _, resp_body = self._raw_http_exchange(
                self._valid_post_headers(len(bad_json)).encode("ascii") + bad_json
            )
            self.assertEqual(code, 400, f"Failed for payload {bad_json!r}")
            self.assertEqual(json.loads(resp_body)["error"]["code"], "INVALID_JSON")

        # Deeply nested JSON -> 400 INVALID_JSON without killing healthy worker
        deep_json = (b'{"request_id": 1, "d": ' + b"[" * 80 + b"1" + b"]" * 80 + b"}")
        code, _, resp_body = self._raw_http_exchange(
            self._valid_post_headers(len(deep_json)).encode("ascii") + deep_json
        )
        self.assertEqual(code, 400)
        self.assertEqual(json.loads(resp_body)["error"]["code"], "INVALID_JSON")

        # Unicode superscript digit in Content-Length -> 400 INVALID_CONTENT_LENGTH
        unicode_cl_req = (
            f"POST /api/v1/solve HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{self.port}\r\n"
            f"Origin: http://127.0.0.1:{self.port}\r\n"
            f"Content-Type: application/json\r\n"
            "Content-Length: \u00b2\r\n"
            f"Connection: close\r\n\r\n{{}}"
        ).encode("latin-1")
        code, _, resp_body = self._raw_http_exchange(unicode_cl_req)
        self.assertEqual(code, 400)
        self.assertEqual(json.loads(resp_body)["error"]["code"], "INVALID_CONTENT_LENGTH")

        # Huge 5000-digit Content-Length -> 413 PAYLOAD_TOO_LARGE (no CPython int digit limit crash)
        huge_cl_req = self._valid_post_headers(2).replace("Content-Length: 2", "Content-Length: " + ("9" * 5000)).encode("ascii") + b"{}"
        code, _, resp_body = self._raw_http_exchange(huge_cl_req)
        self.assertEqual(code, 413)
        self.assertEqual(json.loads(resp_body)["error"]["code"], "PAYLOAD_TOO_LARGE")

        # None of the above malformed HTTP requests should have spawned a worker
        self.assertEqual(len(self.server.worker_manager.spawned_pids), 0)

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
        ready_published_ev = threading.Event()
        write_stalled_ev = threading.Event()
        first_handle_box: list[Any] = []

        def on_ready_publish(handle):
            first_handle_box.append(handle)
            ready_published_ev.set()

        mgr = bridge.WorkerManager(
            response_deadline_s=0.45,
            worker_reap_timeout_s=0.8,
            custom_worker_cmd=stall_script,
            on_before_ready_publish=on_ready_publish,
        )
        orig_os_write = os.write

        def stalled_req_write(fd, data):
            if ready_published_ev.is_set() and first_handle_box and fd == first_handle_box[0].req_w:
                write_stalled_ev.set()
                raise BlockingIOError(errno.EAGAIN, "Simulated request pipe backpressure")
            return orig_os_write(fd, data)

        try:
            # Force pipe backpressure (BlockingIOError on write) strictly on worker req_w after READY
            t0 = time.monotonic()
            with mock.patch("v1_worker_bridge.os.write", side_effect=stalled_req_write):
                res = mgr.execute("/api/v1/solve", {"request_id": 1})
            fault_elapsed = time.monotonic() - t0
            self.assertTrue(ready_published_ev.is_set(), "Fault worker did not reach READY publication")
            self.assertTrue(write_stalled_ev.is_set(), "Injected blocked-send stall was not exercised")
            self.assertEqual(res.status_code, 504)
            self.assertEqual(res.payload["error"]["code"], "SOLVE_DEADLINE_EXCEEDED")
            # Real-clock watchdog bounded far below the child's 5.0 s sleep
            self.assertGreaterEqual(fault_elapsed, 0.35)
            self.assertLess(fault_elapsed, 1.50)

            first_handle = first_handle_box[0]
            first_pid = mgr.spawned_pids[0]
            self.assertTrue(_is_pid_reaped(first_pid))
            self.assertIsNone(first_handle.req_w)
            self.assertIsNone(first_handle.resp_r)

            # Switch to normal worker with a separate reasonable execution budget for recovery
            mgr.custom_worker_cmd = None
            mgr.on_before_ready_publish = None
            mgr.response_deadline_s = 2.0
            res2 = mgr.execute("/api/v1/solve", {"request_id": 2})
            self.assertEqual(res2.status_code, 200)
            second_pid = res2.payload["worker_pid"]
            self.assertNotEqual(first_pid, second_pid)
            self.assertEqual(len(mgr.spawned_pids), 2)
            self.assertEqual(res2.payload["child_req_ino"], res2.payload["expected_req_ino"])
            self.assertEqual(res2.payload["child_resp_ino"], res2.payload["expected_resp_ino"])
            self.assertTrue(res2.payload["parent_closed_unused_ends"])
            self.assertEqual(
                sorted(res2.payload["child_open_pipe_inos"]),
                sorted([res2.payload["child_req_ino"], res2.payload["child_resp_ino"]]),
            )
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

    def test_r1_f1_barrier_shutdown_before_ready_publish_and_selector_register(self):
        """V1-A-R1-F1: barrier shutdown before READY publish & before selector register never deadlocks or leaks."""
        import v1_worker_bridge as bridge

        baseline_pipes = _list_open_pipe_inodes()

        # Case A: Shutdown racing while execute() is paused immediately BEFORE READY publication
        reached_publish = threading.Event()
        release_publish = threading.Event()
        mgr_a = bridge.WorkerManager(
            response_deadline_s=2.0,
            worker_reap_timeout_s=0.8,
            on_before_ready_publish=lambda _h: (reached_publish.set(), release_publish.wait(timeout=3.0)),
        )
        exec_res_a: list = []

        def run_a():
            exec_res_a.append(mgr_a.execute("/api/v1/solve", {"request_id": 1}))

        th_a = threading.Thread(target=run_a)
        th_a.start()
        self.assertTrue(reached_publish.wait(timeout=2.0))

        # shutdown() MUST return cleanly WITHOUT deadlocking while execute paused before publish
        t_shut = time.monotonic()
        mgr_a.shutdown()
        self.assertLess(time.monotonic() - t_shut, 1.5)
        release_publish.set()
        th_a.join(timeout=2.0)

        self.assertEqual(len(exec_res_a), 1)
        self.assertEqual(exec_res_a[0].status_code, 503)
        self.assertEqual(exec_res_a[0].payload["error"]["code"], "SERVER_SHUTTING_DOWN")
        self.assertIsNone(mgr_a._active_worker)
        for pid in mgr_a.spawned_pids:
            self.assertTrue(_is_pid_reaped(pid))
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

        # Case B: Shutdown racing immediately BEFORE selector registration on warmed worker
        reached_sel = threading.Event()
        release_sel = threading.Event()
        gate_armed = [False]

        def before_sel(_h):
            if gate_armed[0]:
                reached_sel.set()
                release_sel.wait(timeout=3.0)

        mgr_b = bridge.WorkerManager(
            response_deadline_s=2.0,
            worker_reap_timeout_s=0.8,
            on_before_selector_register=before_sel,
        )
        warm = mgr_b.execute("/api/v1/solve", {"request_id": 10})
        self.assertEqual(warm.status_code, 200)
        gate_armed[0] = True
        exec_res_b: list = []

        th_b = threading.Thread(target=lambda: exec_res_b.append(mgr_b.execute("/api/v1/solve", {"request_id": 11})))
        th_b.start()
        self.assertTrue(reached_sel.wait(timeout=2.0))
        mgr_b.shutdown()
        release_sel.set()
        th_b.join(timeout=2.0)

        self.assertEqual(len(exec_res_b), 1)
        self.assertEqual(exec_res_b[0].status_code, 503)
        self.assertEqual(exec_res_b[0].payload["error"]["code"], "SERVER_SHUTTING_DOWN")
        for pid in mgr_b.spawned_pids:
            self.assertTrue(_is_pid_reaped(pid))
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

        # Case C: Shutdown racing concurrently with active teardown owner (single kill/reap only)
        in_kill = threading.Event()
        release_kill = threading.Event()
        kill_count = [0]

        def barrier_kill(proc):
            kill_count[0] += 1
            in_kill.set()
            release_kill.wait(timeout=3.0)
            proc.kill()

        mgr_c = bridge.WorkerManager(response_deadline_s=0.2, worker_reap_timeout_s=1.0, kill_fn=barrier_kill)
        exec_res_c: list = []
        th_c = threading.Thread(
            target=lambda: exec_res_c.append(mgr_c.execute("/api/v1/solve", {"request_id": 12, "delay_s": 2.0}))
        )
        th_c.start()
        self.assertTrue(in_kill.wait(timeout=2.0))
        shut_done = threading.Event()

        def run_shut():
            mgr_c.shutdown()
            shut_done.set()

        th_s = threading.Thread(target=run_shut)
        th_s.start()
        release_kill.set()
        th_c.join(timeout=2.0)
        th_s.join(timeout=2.0)
        self.assertTrue(shut_done.is_set())
        self.assertEqual(exec_res_c[0].status_code, 504)
        self.assertEqual(kill_count[0], 1)
        for pid in mgr_c.spawned_pids:
            self.assertTrue(_is_pid_reaped(pid))
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

    def test_r1_f2_abandoned_launch_raises_and_partial_pipe_and_pre_slot_shutdown(self):
        """V1-A-R1-F2: abandoned launch exception before/after PID, pre-slot shutdown, partial pipe cleanup."""
        import v1_worker_bridge as bridge

        baseline_pipes = _list_open_pipe_inodes()

        # Case A: delayed launch raises WITHOUT returning PID after caller timed out & abandoned slot
        allow_fail = threading.Event()
        runner_failed = threading.Event()

        def delayed_fail_no_pid(cmd, pass_fds):
            allow_fail.wait(timeout=2.0)
            runner_failed.set()
            raise RuntimeError("delayed fork/exec failure after abandonment")

        mgr_a = bridge.WorkerManager(response_deadline_s=0.15, worker_reap_timeout_s=0.8, launch_fn=delayed_fail_no_pid)
        res_a = mgr_a.execute("/api/v1/solve", {"request_id": 1})
        self.assertEqual(res_a.status_code, 503)
        self.assertEqual(res_a.payload["error"]["code"], "WORKER_UNAVAILABLE_POISONED")
        allow_fail.set()
        self.assertTrue(runner_failed.wait(timeout=2.0))
        mgr_a.shutdown()
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

        # Case B: delayed launch calls register_pid(proc) AFTER timeout abandonment, then raises
        allow_reg_raise = threading.Event()
        reg_proc: list[subprocess.Popen] = []

        def delayed_register_then_raise(cmd, pass_fds, register_pid=None):
            allow_reg_raise.wait(timeout=2.0)
            proc = subprocess.Popen(cmd, pass_fds=pass_fds, close_fds=True)
            reg_proc.append(proc)
            if register_pid is not None:
                register_pid(proc)
            raise RuntimeError("post-PID failure after timeout abandonment")

        mgr_b = bridge.WorkerManager(
            response_deadline_s=0.15, worker_reap_timeout_s=0.8, launch_fn=delayed_register_then_raise
        )
        res_b = mgr_b.execute("/api/v1/solve", {"request_id": 2})
        self.assertEqual(res_b.status_code, 503)
        self.assertEqual(res_b.payload["error"]["code"], "WORKER_UNAVAILABLE_POISONED")
        allow_reg_raise.set()
        mgr_b.shutdown()
        self.assertEqual(len(reg_proc), 1)
        self.assertTrue(_is_pid_reaped(reg_proc[0].pid))
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

        # Case C: shutdown races BEFORE launch slot publication -> zero spawns, 503 SERVER_SHUTTING_DOWN
        reached_pre_slot = threading.Event()
        release_pre_slot = threading.Event()
        mgr_c = bridge.WorkerManager(
            response_deadline_s=1.0,
            worker_reap_timeout_s=0.6,
            on_before_launch_slot_publish=lambda: (reached_pre_slot.set(), release_pre_slot.wait(timeout=2.0)),
        )
        res_c_box: list = []
        th_c = threading.Thread(target=lambda: res_c_box.append(mgr_c.execute("/api/v1/solve", {"request_id": 3})))
        th_c.start()
        self.assertTrue(reached_pre_slot.wait(timeout=2.0))
        mgr_c.shutdown()
        release_pre_slot.set()
        th_c.join(timeout=2.0)
        self.assertEqual(res_c_box[0].status_code, 503)
        self.assertEqual(res_c_box[0].payload["error"]["code"], "SERVER_SHUTTING_DOWN")
        self.assertEqual(mgr_c.spawned_pids, [])
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

        # Case D: partial pipe allocation failure cleans up first pipe FDs cleanly
        real_pipe = os.pipe
        calls = [0]

        def fail_second_pipe():
            calls[0] += 1
            if calls[0] == 1:
                return real_pipe()
            raise OSError("simulated EMFILE on second pipe")

        mgr_d = bridge.WorkerManager(response_deadline_s=1.0, worker_reap_timeout_s=0.6)
        try:
            with mock.patch("v1_worker_bridge.os.pipe", side_effect=fail_second_pipe):
                res_d = mgr_d.execute("/api/v1/solve", {"request_id": 4})
            self.assertEqual(res_d.status_code, 503)
            self.assertEqual(res_d.payload["error"]["code"], "WORKER_STARTUP_FAILED")
        finally:
            mgr_d.shutdown()
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

    def test_r1_f3_post_final_byte_and_decode_deadline_enforcement(self):
        """V1-A-R1-F3: expiry after final frame byte or during JSON decode/validation returns 504, never 200."""
        import v1_worker_bridge as bridge

        baseline_pipes = _list_open_pipe_inodes()

        # Case A: clock expires right AFTER final response byte is read, BEFORE JSON decode/200
        now = [100.0]
        mgr_a = bridge.WorkerManager(
            response_deadline_s=5.0,
            worker_reap_timeout_s=0.8,
            clock=lambda: now[0],
        )
        warm = mgr_a.execute("/api/v1/solve", {"request_id": 1})
        self.assertEqual(warm.status_code, 200)
        mgr_a._on_after_raw_read = lambda _c: now.__setitem__(0, 200.0) if len(_c) > 10 else None
        try:
            res_expired = mgr_a.execute("/api/v1/solve", {"request_id": 2})
            self.assertEqual(res_expired.status_code, 504)
            self.assertEqual(res_expired.payload["error"]["code"], "SOLVE_DEADLINE_EXCEEDED")
            self.assertTrue(_is_pid_reaped(mgr_a.spawned_pids[0]))
        finally:
            mgr_a.shutdown()
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

        # Case B: stalled / slow decode past deadline (simulating near-max response decode expiry)
        now_b = [500.0]
        mgr_b = bridge.WorkerManager(
            response_deadline_s=0.35,
            worker_reap_timeout_s=0.8,
            clock=lambda: now_b[0],
        )
        warm_b = mgr_b.execute("/api/v1/solve", {"request_id": 10})
        self.assertEqual(warm_b.status_code, 200)
        mgr_b._on_decode_transform = lambda obj: (now_b.__setitem__(0, 600.0), obj)[1]
        try:
            res_dec = mgr_b.execute("/api/v1/solve", {"request_id": 11})
            self.assertEqual(res_dec.status_code, 504)
            self.assertEqual(res_dec.payload["error"]["code"], "SOLVE_DEADLINE_EXCEEDED")
            self.assertTrue(_is_pid_reaped(mgr_b.spawned_pids[0]))
        finally:
            mgr_b.shutdown()
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

    def test_r1_f4_poison_precedence_and_quarantined_process_ownership(self):
        """V1-A-R1-F4: post-PID launch & cancel teardown failures poison and retain quarantine for shutdown."""
        import v1_worker_bridge as bridge

        baseline_pipes = _list_open_pipe_inodes()

        # Case A: launcher registers sleeping child PID then raises, AND kill fails -> 503 POISONED + retained quarantine
        kill_should_fail = [True]
        leaked_procs: list[subprocess.Popen] = []
        sleeping_cmd = self._make_fault_worker_script("import time\ntime.sleep(5)\n")

        def launch_reg_then_raise(cmd, pass_fds, register_pid=None):
            proc = subprocess.Popen(sleeping_cmd, pass_fds=pass_fds, close_fds=True)
            leaked_procs.append(proc)
            if register_pid is not None:
                register_pid(proc)
            raise RuntimeError("boom after register_pid")

        def flaky_kill(proc):
            if kill_should_fail[0]:
                raise PermissionError("simulated EPERM on initial teardown")
            proc.kill()

        mgr_a = bridge.WorkerManager(
            response_deadline_s=0.6,
            worker_reap_timeout_s=0.6,
            launch_fn=launch_reg_then_raise,
            kill_fn=flaky_kill,
        )
        res_a = mgr_a.execute("/api/v1/solve", {"request_id": 1})
        self.assertEqual(res_a.status_code, 503)
        self.assertEqual(res_a.payload["error"]["code"], "WORKER_UNAVAILABLE_POISONED")
        self.assertEqual(mgr_a.quarantined_pids, [leaked_procs[0].pid])

        # Subsequent call sees 503 POISONED before anything else
        res_a2 = mgr_a.execute("/api/v1/solve", {"request_id": 2})
        self.assertEqual(res_a2.status_code, 503)
        self.assertEqual(res_a2.payload["error"]["code"], "WORKER_UNAVAILABLE_POISONED")

        # Clear transient kill fault -> shutdown() retries quarantined handle and reaps child, yet remains poisoned
        kill_should_fail[0] = False
        mgr_a.shutdown()
        self.assertEqual(mgr_a.quarantined_pids, [])
        self.assertTrue(_is_pid_reaped(leaked_procs[0].pid))
        self.assertTrue(mgr_a._worker_poisoned)
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

        # Case B: cancellation teardown failure returns WORKER_UNAVAILABLE_POISONED (not SERVER_SHUTTING_DOWN)
        kill_should_fail_b = [True]

        def flaky_kill_b(proc):
            if kill_should_fail_b[0]:
                raise PermissionError("simulated cancel teardown EPERM")
            proc.kill()

        reached_sel = threading.Event()
        release_sel = threading.Event()
        armed = [False]
        mgr_b = bridge.WorkerManager(
            response_deadline_s=1.5,
            worker_reap_timeout_s=0.5,
            kill_fn=flaky_kill_b,
            on_before_selector_register=lambda _h: (reached_sel.set(), release_sel.wait(timeout=2.0)) if armed[0] else None,
        )
        self.assertEqual(mgr_b.execute("/api/v1/solve", {"request_id": 10}).status_code, 200)
        armed[0] = True
        box_b: list = []
        th_b = threading.Thread(target=lambda: box_b.append(mgr_b.execute("/api/v1/solve", {"request_id": 11})))
        th_b.start()
        self.assertTrue(reached_sel.wait(timeout=2.0))
        mgr_b.shutdown()
        release_sel.set()
        th_b.join(timeout=2.0)

        self.assertEqual(box_b[0].status_code, 503)
        self.assertEqual(box_b[0].payload["error"]["code"], "WORKER_UNAVAILABLE_POISONED")
        kill_should_fail_b[0] = False
        mgr_b.shutdown()
        for pid in mgr_b.spawned_pids:
            self.assertTrue(_is_pid_reaped(pid))
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

    def test_r1_m1_worker_overflow_json_reaps_cleanly(self):
        """V1-A-R1-M1: malformed/overflowing worker JSON triggers 500 IPC_PROTOCOL_ERROR & reaps worker."""
        import v1_worker_bridge as bridge

        baseline_pipes = _list_open_pipe_inodes()
        bad_worker = self._make_fault_worker_script(
            "import argparse, json, os, struct\n"
            "def read_exact(fd, n):\n"
            "  b = bytearray()\n"
            "  while len(b) < n:\n"
            "    c = os.read(fd, n - len(b))\n"
            "    if not c: raise EOFError()\n"
            "    b.extend(c)\n"
            "  return bytes(b)\n"
            "p = argparse.ArgumentParser()\n"
            "p.add_argument('--req-fd', type=int); p.add_argument('--resp-fd', type=int)\n"
            "a, _ = p.parse_known_args()\n"
            "ready = json.dumps({'type':'READY','pid':os.getpid(),'req_ino':os.fstat(a.req_fd).st_ino,'resp_ino':os.fstat(a.resp_fd).st_ino}).encode()\n"
            "os.write(a.resp_fd, struct.pack('>I', len(ready)) + ready)\n"
            "n = struct.unpack('>I', read_exact(a.req_fd, 4))[0]\n"
            "req = json.loads(read_exact(a.req_fd, n).decode())\n"
            "bad = f'{{\"ipc_token\":{req[\"ipc_token\"]},\"val\":1e309}}'.encode()\n"
            "os.write(a.resp_fd, struct.pack('>I', len(bad)) + bad)\n"
        )
        mgr = bridge.WorkerManager(response_deadline_s=1.0, worker_reap_timeout_s=0.6, custom_worker_cmd=bad_worker)
        try:
            res = mgr.execute("/api/v1/solve", {"request_id": 1})
            self.assertEqual(res.status_code, 500)
            self.assertEqual(res.payload["error"]["code"], "IPC_PROTOCOL_ERROR")
            self.assertTrue(_is_pid_reaped(mgr.spawned_pids[0]))
        finally:
            mgr.shutdown()
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

    def test_r1_m2_cwd_independent_launcher_execution(self):
        """V1-A-R1-M2: launching run_explorer.py from an isolated temp CWD with sanitized PYTHONPATH succeeds."""
        launcher_path = Path(__file__).resolve().parent.parent / "run_explorer.py"
        with tempfile.TemporaryDirectory() as tmp_cwd:
            # Find a free port without polluting cwd
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", 0))
                port = s.getsockname()[1]

            env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
            env["PYTHONPATH"] = ""
            proc = subprocess.Popen(
                [sys.executable, str(launcher_path), "--host", "127.0.0.1", "--port", str(port), "--no-browser"],
                cwd=tmp_cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                # Wait briefly for HTTP bind from unrelated CWD
                deadline = time.monotonic() + 3.0
                last_err = None
                resp_payload = None
                while time.monotonic() < deadline:
                    try:
                        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=1.0)
                        body = json.dumps({"request_id": 77}).encode("utf-8")
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
                        resp_payload = (resp.status, json.loads(resp.read().decode("utf-8")))
                        conn.close()
                        break
                    except OSError as exc:
                        last_err = exc
                        time.sleep(0.05)

                self.assertIsNotNone(resp_payload, f"Server failed to bind from temp CWD: {last_err}")
                status, payload = resp_payload
                self.assertEqual(status, 200)
                self.assertEqual(payload["status"], "V1_A_TRANSPORT_ONLY")
                self.assertEqual(payload["request_id"], 77)
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=3.0)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=3.0)
                if proc.stdout:
                    proc.stdout.close()
                if proc.stderr:
                    proc.stderr.close()

    def test_r2_f1_shutdown_during_live_pre_and_post_pid_launch_no_deadlock(self):
        """V1-A-R2-F1: shutdown while pre-PID or post-PID launch is still running never self-deadlocks."""
        import v1_worker_bridge as bridge

        baseline_pipes = _list_open_pipe_inodes()

        # Case A: live pre-PID launch stalled on barrier when shutdown starts
        pre_entered = threading.Event()
        pre_release = threading.Event()

        def stalled_pre_pid(cmd, pass_fds):
            pre_entered.set()
            pre_release.wait(timeout=3.0)
            raise RuntimeError("pre-PID launch released after shutdown")

        mgr_a = bridge.WorkerManager(response_deadline_s=5.0, worker_reap_timeout_s=0.4, launch_fn=stalled_pre_pid)
        res_a_box: list = []
        th_exec_a = threading.Thread(target=lambda: res_a_box.append(mgr_a.execute("/api/v1/solve", {"request_id": 1})))
        th_exec_a.start()
        self.assertTrue(pre_entered.wait(timeout=2.0))

        shut_a_done = threading.Event()
        th_shut_a = threading.Thread(target=lambda: (mgr_a.shutdown(), shut_a_done.set()))
        th_shut_a.start()
        # Allow execute to observe _shutting_down BEFORE releasing launcher
        time.sleep(0.05)
        pre_release.set()

        th_exec_a.join(timeout=2.5)
        th_shut_a.join(timeout=2.5)
        self.assertFalse(th_exec_a.is_alive(), "execute() deadlocked during live pre-PID launch shutdown")
        self.assertFalse(th_shut_a.is_alive(), "shutdown() deadlocked during live pre-PID launch shutdown")
        self.assertEqual(res_a_box[0].status_code, 503)
        self.assertEqual(mgr_a.spawned_pids, [])
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

        # Case B: live post-PID launch stalled after register_pid(proc) while shutdown runs
        post_entered = threading.Event()
        post_release = threading.Event()
        procs_b: list[subprocess.Popen] = []

        def stalled_post_pid(cmd, pass_fds, register_pid=None):
            proc = subprocess.Popen(cmd, pass_fds=pass_fds, close_fds=True)
            procs_b.append(proc)
            if register_pid is not None:
                register_pid(proc)
            post_entered.set()
            post_release.wait(timeout=3.0)
            return proc

        mgr_b = bridge.WorkerManager(response_deadline_s=5.0, worker_reap_timeout_s=0.6, launch_fn=stalled_post_pid)
        res_b_box: list = []
        th_exec_b = threading.Thread(target=lambda: res_b_box.append(mgr_b.execute("/api/v1/solve", {"request_id": 2})))
        th_exec_b.start()
        self.assertTrue(post_entered.wait(timeout=2.0))

        shut_b_done = threading.Event()
        th_shut_b = threading.Thread(target=lambda: (mgr_b.shutdown(), shut_b_done.set()))
        th_shut_b.start()
        time.sleep(0.05)
        post_release.set()

        th_exec_b.join(timeout=2.5)
        th_shut_b.join(timeout=2.5)
        self.assertFalse(th_exec_b.is_alive())
        self.assertFalse(th_shut_b.is_alive())
        self.assertEqual(res_b_box[0].status_code, 503)
        self.assertEqual(len(procs_b), 1)
        self.assertTrue(_is_pid_reaped(procs_b[0].pid))
        # No respawn after shutdown
        self.assertEqual(mgr_b.execute("/api/v1/solve", {"request_id": 3}).status_code, 503)
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

    def test_r2_f2_atomic_slot_transfer_and_sentinel_fd_reuse_safety(self):
        """V1-A-R2-F2: slot-to-handle barriers & cancel-pipe writer lease never close/write unrelated sentinel FDs."""
        import v1_worker_bridge as bridge

        baseline_pipes = _list_open_pipe_inodes()

        # (a) Shutdown between _active_launch commit & runner start, with numeric FD reuse sentinel
        sentinel_a: list[tuple[int, int]] = []
        at_a = threading.Event()
        rel_a = threading.Event()

        def hook_after_commit(_slot):
            at_a.set()
            rel_a.wait(timeout=2.0)

        mgr_a = bridge.WorkerManager(
            response_deadline_s=2.0,
            worker_reap_timeout_s=0.6,
            on_after_slot_publish_before_runner=hook_after_commit,
        )
        res_a: list = []
        th_a = threading.Thread(target=lambda: res_a.append(mgr_a.execute("/api/v1/solve", {"request_id": 1})))
        th_a.start()
        self.assertTrue(at_a.wait(timeout=2.0))
        mgr_a.shutdown()
        # Allocate unrelated sentinel pipe reusing freed FD numbers
        sr, sw = os.pipe()
        sentinel_a.append((sr, sw))
        try:
            rel_a.set()
            th_a.join(timeout=2.0)
            self.assertEqual(res_a[0].status_code, 503)
            self.assertTrue(bridge._is_fd_open(sr))
            self.assertTrue(bridge._is_fd_open(sw))
            self.assertEqual(mgr_a.spawned_pids, [])
        finally:
            os.close(sr)
            os.close(sw)
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

        # (b) Shutdown between registered PID & done AND before slot-to-pending handoff, with sentinel FDs
        at_pid = threading.Event()
        rel_pid = threading.Event()
        mgr_b = bridge.WorkerManager(
            response_deadline_s=2.0,
            worker_reap_timeout_s=0.6,
            on_after_runner_pid_before_done=lambda _p: (at_pid.set(), rel_pid.wait(timeout=2.0)),
        )
        res_b: list = []
        th_b = threading.Thread(target=lambda: res_b.append(mgr_b.execute("/api/v1/solve", {"request_id": 2})))
        th_b.start()
        self.assertTrue(at_pid.wait(timeout=2.0))
        th_shut_b = threading.Thread(target=mgr_b.shutdown)
        th_shut_b.start()
        time.sleep(0.05)
        rel_pid.set()
        th_shut_b.join(timeout=2.0)
        sr2, sw2 = os.pipe()
        try:
            th_b.join(timeout=2.0)
            self.assertEqual(res_b[0].status_code, 503)
            self.assertTrue(bridge._is_fd_open(sr2))
            self.assertTrue(bridge._is_fd_open(sw2))
            for pid in mgr_b.spawned_pids:
                self.assertTrue(_is_pid_reaped(pid))
        finally:
            os.close(sr2)
            os.close(sw2)
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

        # (c) Barrier between slot done & pending handoff
        at_handoff = threading.Event()
        rel_handoff = threading.Event()
        mgr_c = bridge.WorkerManager(
            response_deadline_s=2.0,
            worker_reap_timeout_s=0.6,
            on_before_slot_to_pending_handoff=lambda _s: (at_handoff.set(), rel_handoff.wait(timeout=2.0)),
        )
        res_c: list = []
        th_c = threading.Thread(target=lambda: res_c.append(mgr_c.execute("/api/v1/solve", {"request_id": 3})))
        th_c.start()
        self.assertTrue(at_handoff.wait(timeout=2.0))
        mgr_c.shutdown()
        sr3, sw3 = os.pipe()
        try:
            rel_handoff.set()
            th_c.join(timeout=2.0)
            self.assertEqual(res_c[0].status_code, 503)
            self.assertTrue(bridge._is_fd_open(sr3))
            self.assertTrue(bridge._is_fd_open(sw3))
            for pid in mgr_c.spawned_pids:
                self.assertTrue(_is_pid_reaped(pid))
        finally:
            os.close(sr3)
            os.close(sw3)
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

        # (d) Barrier between cancel_w capture and write: shutdown holds writer lease so cancel pipe cannot be closed/reused early
        in_cancel = threading.Event()
        rel_cancel = threading.Event()
        mgr_d = bridge.WorkerManager(
            response_deadline_s=2.0,
            worker_reap_timeout_s=0.6,
            on_before_cancel_write=lambda: (in_cancel.set(), rel_cancel.wait(timeout=2.0)),
        )
        self.assertEqual(mgr_d.execute("/api/v1/solve", {"request_id": 4}).status_code, 200)
        th_shut_d = threading.Thread(target=mgr_d.shutdown)
        th_shut_d.start()
        self.assertTrue(in_cancel.wait(timeout=2.0))
        # Cancel pipe MUST still be open (active_cancel_writers == 1) until rel_cancel.set()
        self.assertFalse(mgr_d._cancel_closed)
        rel_cancel.set()
        th_shut_d.join(timeout=2.0)
        self.assertTrue(mgr_d._cancel_closed)
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

    def test_r2_f3_post_write_expiry_and_ready_linearization_deadline(self):
        """V1-A-R2-F3: post-write clock expiry yields 504 (not 500 EOF), and READY expiry checks under lock."""
        import v1_worker_bridge as bridge

        baseline_pipes = _list_open_pipe_inodes()

        # Case A: clock advances past deadline right AFTER final os.write on request frame
        now_a = [100.0]
        mgr_a = bridge.WorkerManager(response_deadline_s=5.0, worker_reap_timeout_s=0.8, clock=lambda: now_a[0])
        self.assertEqual(mgr_a.execute("/api/v1/solve", {"request_id": 1}).status_code, 200)
        real_write = os.write

        def expire_after_req_write(fd: int, data: bytes) -> int:
            n = real_write(fd, data)
            if len(data) > 20:
                now_a[0] = 200.0
            return n

        try:
            with mock.patch("v1_worker_bridge.os.write", side_effect=expire_after_req_write):
                res_post_write = mgr_a.execute("/api/v1/solve", {"request_id": 2})
            self.assertEqual(res_post_write.status_code, 504)
            self.assertEqual(res_post_write.payload["error"]["code"], "SOLVE_DEADLINE_EXCEEDED")
            self.assertTrue(_is_pid_reaped(mgr_a.spawned_pids[0]))

            # Clean recovery respawn after post-write 504
            now_a[0] = 300.0
            res_rec = mgr_a.execute("/api/v1/solve", {"request_id": 3})
            self.assertEqual(res_rec.status_code, 200)
        finally:
            mgr_a.shutdown()
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

        # Case B: clock expires DURING on_before_ready_publish -> linearized lock check rejects publication -> 504
        now_b = [100.0]
        mgr_b = bridge.WorkerManager(
            response_deadline_s=2.0,
            worker_reap_timeout_s=0.6,
            clock=lambda: now_b[0],
            on_before_ready_publish=lambda _h: now_b.__setitem__(0, 200.0),
        )
        try:
            res_ready_exp = mgr_b.execute("/api/v1/solve", {"request_id": 4})
            self.assertEqual(res_ready_exp.status_code, 504)
            self.assertEqual(res_ready_exp.payload["error"]["code"], "SOLVE_DEADLINE_EXCEEDED")
            self.assertIsNone(mgr_b._active_worker)
            self.assertTrue(_is_pid_reaped(mgr_b.spawned_pids[0]))
        finally:
            mgr_b.shutdown()
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

    def test_r2_f4_single_teardown_budget_and_real_large_bounded_decode(self):
        """V1-A-R2-F4: single absolute reap budget across lock/drain/reap + real multi-MB decode & uncooperative decoder poison."""
        import v1_worker_bridge as bridge

        baseline_pipes = _list_open_pipe_inodes()

        # Case A: single absolute teardown budget (delay in kill + delay in wait > worker_reap_timeout_s triggers timeout once)
        def slow_kill(proc):
            time.sleep(0.30)
            proc.kill()

        slow_exit_cmd = self._make_fault_worker_script(
            "import argparse, json, os, signal, struct, time\n"
            "signal.signal(signal.SIGKILL if False else signal.SIGTERM, lambda *_: None)\n"
            "def read_exact(fd, n):\n"
            "  b = bytearray()\n"
            "  while len(b) < n:\n"
            "    c = os.read(fd, n - len(b))\n"
            "    if not c: raise EOFError()\n"
            "    b.extend(c)\n"
            "  return bytes(b)\n"
            "p = argparse.ArgumentParser()\n"
            "p.add_argument('--req-fd', type=int); p.add_argument('--resp-fd', type=int)\n"
            "a, _ = p.parse_known_args()\n"
            "ready = json.dumps({'type':'READY','pid':os.getpid(),'req_ino':os.fstat(a.req_fd).st_ino,'resp_ino':os.fstat(a.resp_fd).st_ino}).encode()\n"
            "os.write(a.resp_fd, struct.pack('>I', len(ready)) + ready)\n"
            "n = struct.unpack('>I', read_exact(a.req_fd, 4))[0]\n"
            "read_exact(a.req_fd, n)\n"
            "time.sleep(5)\n"
        )
        # Reap budget 0.55s shared between teardown_exec_lock contender + kill delay + proc.wait
        mgr_a = bridge.WorkerManager(response_deadline_s=0.15, worker_reap_timeout_s=0.55, custom_worker_cmd=slow_exit_cmd, kill_fn=slow_kill)
        try:
            t0 = time.monotonic()
            res_a = mgr_a.execute("/api/v1/solve", {"request_id": 1})
            dt = time.monotonic() - t0
            self.assertEqual(res_a.status_code, 504)
            # Total time must reflect ONE deadline (~0.15s) + single teardown (<0.55s)
            self.assertLess(dt, 0.90)
        finally:
            mgr_a.shutdown()
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

        # Case B: real ~5MB large JSON frame passes inside budget AND aborts mid-parse when deadline expires
        big_worker = self._make_fault_worker_script(
            "import argparse, json, os, struct\n"
            "def read_exact(fd, n):\n"
            "  b = bytearray()\n"
            "  while len(b) < n:\n"
            "    c = os.read(fd, n - len(b))\n"
            "    if not c: raise EOFError()\n"
            "    b.extend(c)\n"
            "  return bytes(b)\n"
            "p = argparse.ArgumentParser()\n"
            "p.add_argument('--req-fd', type=int); p.add_argument('--resp-fd', type=int)\n"
            "a, _ = p.parse_known_args()\n"
            "ready = json.dumps({'type':'READY','pid':os.getpid(),'req_ino':os.fstat(a.req_fd).st_ino,'resp_ino':os.fstat(a.resp_fd).st_ino}).encode()\n"
            "os.write(a.resp_fd, struct.pack('>I', len(ready)) + ready)\n"
            "arr_json = '[' + ','.join(['1.25'] * 700000) + ']'\n"
            "while True:\n"
            "  try: hdr = read_exact(a.req_fd, 4)\n"
            "  except EOFError: break\n"
            "  n = struct.unpack('>I', hdr)[0]\n"
            "  req = json.loads(read_exact(a.req_fd, n).decode())\n"
            "  out = ('{\"ipc_token\":' + str(req['ipc_token']) + ',\"data\":' + arr_json + '}').encode()\n"
            "  mv = memoryview(struct.pack('>I', len(out)) + out)\n"
            "  sent = 0\n"
            "  while sent < len(mv): sent += os.write(a.resp_fd, mv[sent:])\n"
        )
        now_b = [100.0]

        def clock_b():
            return now_b[0]

        # Advance mock clock after first 256 parse tokens? Keep clock advancing slowly by tick calls when requested
        expire_mid_parse = [False]
        token_checks = [0]

        def clock_mid_parse():
            if expire_mid_parse[0]:
                token_checks[0] += 1
                if token_checks[0] >= 50:
                    return 200.0
            return 100.0

        mgr_b = bridge.WorkerManager(
            response_deadline_s=5.0,
            worker_reap_timeout_s=0.8,
            custom_worker_cmd=big_worker,
            clock=clock_mid_parse,
        )
        try:
            ok_big = mgr_b.execute("/api/v1/solve", {"request_id": 10})
            self.assertEqual(ok_big.status_code, 200)
            self.assertEqual(len(ok_big.payload["data"]), 700000)

            expire_mid_parse[0] = True
            tmo_big = mgr_b.execute("/api/v1/solve", {"request_id": 11})
            self.assertEqual(tmo_big.status_code, 504)
            self.assertEqual(tmo_big.payload["error"]["code"], "SOLVE_DEADLINE_EXCEEDED")
            self.assertTrue(_is_pid_reaped(mgr_b.spawned_pids[0]))

            expire_mid_parse[0] = False
            mgr_b.custom_worker_cmd = None
            rec_big = mgr_b.execute("/api/v1/solve", {"request_id": 12})
            self.assertEqual(rec_big.status_code, 200)
        finally:
            mgr_b.shutdown()
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

        # Case C: uncooperative stalled decoder cannot be joined -> poisons fail closed, admission stays closed
        stall_release = threading.Event()

        def blocking_decode(obj):
            stall_release.wait(timeout=2.0)
            return obj

        mgr_c = bridge.WorkerManager(
            response_deadline_s=1.0,
            worker_reap_timeout_s=0.2,
        )
        try:
            self.assertEqual(mgr_c.execute("/api/v1/solve", {"request_id": 20}).status_code, 200)
            mgr_c.response_deadline_s = 0.12
            mgr_c._on_decode_transform = blocking_decode
            res_c = mgr_c.execute("/api/v1/solve", {"request_id": 21})
            self.assertEqual(res_c.status_code, 503)
            self.assertEqual(res_c.payload["error"]["code"], "WORKER_UNAVAILABLE_POISONED")
            # Must stay poisoned / never reopen while abandoned decode persisted
            res_c2 = mgr_c.execute("/api/v1/solve", {"request_id": 22})
            self.assertEqual(res_c2.status_code, 503)
            self.assertEqual(res_c2.payload["error"]["code"], "WORKER_UNAVAILABLE_POISONED")
            self.assertEqual(len(mgr_c.spawned_pids), 1)
        finally:
            stall_release.set()
            mgr_c.shutdown()
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

    def test_r2_m1_rejects_bool_and_float_identity_tokens(self):
        """V1-A-R2-M1: bool (`True == 1`) and float (`1.0 == 1`) in ipc_token or READY identity are rejected."""
        import v1_worker_bridge as bridge

        baseline_pipes = _list_open_pipe_inodes()

        bool_token_cmd = self._make_fault_worker_script(
            "import argparse, json, os, struct\n"
            "def read_exact(fd, n):\n"
            "  b = bytearray()\n"
            "  while len(b) < n:\n"
            "    c = os.read(fd, n - len(b))\n"
            "    if not c: raise EOFError()\n"
            "    b.extend(c)\n"
            "  return bytes(b)\n"
            "p = argparse.ArgumentParser()\n"
            "p.add_argument('--req-fd', type=int); p.add_argument('--resp-fd', type=int)\n"
            "a, _ = p.parse_known_args()\n"
            "ready = json.dumps({'type':'READY','pid':os.getpid(),'req_ino':os.fstat(a.req_fd).st_ino,'resp_ino':os.fstat(a.resp_fd).st_ino}).encode()\n"
            "os.write(a.resp_fd, struct.pack('>I', len(ready)) + ready)\n"
            "n = struct.unpack('>I', read_exact(a.req_fd, 4))[0]\n"
            "read_exact(a.req_fd, n)\n"
            "bad = json.dumps({'ipc_token': True, 'status': 'SPOOF'}).encode()\n"
            "os.write(a.resp_fd, struct.pack('>I', len(bad)) + bad)\n"
        )
        float_token_cmd = self._make_fault_worker_script(
            "import argparse, json, os, struct\n"
            "def read_exact(fd, n):\n"
            "  b = bytearray()\n"
            "  while len(b) < n:\n"
            "    c = os.read(fd, n - len(b))\n"
            "    if not c: raise EOFError()\n"
            "    b.extend(c)\n"
            "  return bytes(b)\n"
            "p = argparse.ArgumentParser()\n"
            "p.add_argument('--req-fd', type=int); p.add_argument('--resp-fd', type=int)\n"
            "a, _ = p.parse_known_args()\n"
            "ready = json.dumps({'type':'READY','pid':os.getpid(),'req_ino':os.fstat(a.req_fd).st_ino,'resp_ino':os.fstat(a.resp_fd).st_ino}).encode()\n"
            "os.write(a.resp_fd, struct.pack('>I', len(ready)) + ready)\n"
            "n = struct.unpack('>I', read_exact(a.req_fd, 4))[0]\n"
            "req = json.loads(read_exact(a.req_fd, n).decode())\n"
            "bad = json.dumps({'ipc_token': float(req['ipc_token']), 'status': 'SPOOF'}).encode()\n"
            "os.write(a.resp_fd, struct.pack('>I', len(bad)) + bad)\n"
        )
        float_ready_cmd = self._make_fault_worker_script(
            "import argparse, json, os, struct\n"
            "p = argparse.ArgumentParser()\n"
            "p.add_argument('--req-fd', type=int); p.add_argument('--resp-fd', type=int)\n"
            "a, _ = p.parse_known_args()\n"
            "ready = json.dumps({'type':'READY','pid':float(os.getpid()),'req_ino':os.fstat(a.req_fd).st_ino,'resp_ino':os.fstat(a.resp_fd).st_ino}).encode()\n"
            "os.write(a.resp_fd, struct.pack('>I', len(ready)) + ready)\n"
        )

        for label, cmd, exp_status in (
            ("bool_ipc_token", bool_token_cmd, 500),
            ("float_ipc_token", float_token_cmd, 500),
            ("float_ready_pid", float_ready_cmd, 503),
        ):
            with self.subTest(case=label):
                mgr = bridge.WorkerManager(response_deadline_s=1.0, worker_reap_timeout_s=0.6, custom_worker_cmd=cmd)
                try:
                    res = mgr.execute("/api/v1/solve", {"request_id": 1})
                    self.assertEqual(res.status_code, exp_status)
                    self.assertTrue(_is_pid_reaped(mgr.spawned_pids[0]))
                finally:
                    mgr.shutdown()
                self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

    def test_r2_m2_utf8_within_http_limit_and_surrogate_rejection(self):
        """V1-A-R2-M2: multi-byte UTF-8 within 8192 HTTP limit succeeds without ASCII expansion; surrogates get 400."""
        import v1_worker_bridge as bridge
        from run_explorer import create_server

        baseline_pipes = _list_open_pipe_inodes()
        mgr = bridge.WorkerManager(response_deadline_s=2.0, worker_reap_timeout_s=0.8)
        server, port = create_server("127.0.0.1", 0, worker_manager=mgr)
        th = threading.Thread(target=server.serve_forever, daemon=True)
        th.start()
        try:
            # 1. Valid UTF-8 payload: 4000 x 'é' -> 8023 bytes <= 8192 (previously expanded > 16384!)
            utf8_body = json.dumps({"request_id": 1, "x": "\u00e9" * 4000}, ensure_ascii=False).encode("utf-8")
            self.assertLessEqual(len(utf8_body), bridge.MAX_HTTP_BODY_BYTES)
            conn1 = http.client.HTTPConnection("127.0.0.1", port, timeout=3.0)
            try:
                conn1.request(
                    "POST",
                    "/api/v1/solve",
                    body=utf8_body,
                    headers={
                        "Host": f"127.0.0.1:{port}",
                        "Origin": f"http://127.0.0.1:{port}",
                        "Content-Type": "application/json; charset=utf-8",
                        "Content-Length": str(len(utf8_body)),
                    },
                )
                r1 = conn1.getresponse()
                p1 = json.loads(r1.read().decode("utf-8"))
                self.assertEqual(r1.status, 200)
                first_pid = p1["worker_pid"]
            finally:
                conn1.close()

            # 2. Lone surrogate escape -> rejected BEFORE admission with 400 INVALID_JSON; healthy worker untouched
            surrogate_body = b'{"request_id": 2, "x": "\\ud800"}'
            conn2 = http.client.HTTPConnection("127.0.0.1", port, timeout=3.0)
            try:
                conn2.request(
                    "POST",
                    "/api/v1/solve",
                    body=surrogate_body,
                    headers={
                        "Host": f"127.0.0.1:{port}",
                        "Origin": f"http://127.0.0.1:{port}",
                        "Content-Type": "application/json",
                        "Content-Length": str(len(surrogate_body)),
                    },
                )
                r2 = conn2.getresponse()
                p2 = json.loads(r2.read().decode("utf-8"))
                self.assertEqual(r2.status, 400)
                self.assertEqual(p2["error"]["code"], "INVALID_JSON")
            finally:
                conn2.close()

            # 3. Follow-up request reuses exact same healthy worker PID
            body3 = json.dumps({"request_id": 3}).encode("utf-8")
            conn3 = http.client.HTTPConnection("127.0.0.1", port, timeout=3.0)
            try:
                conn3.request(
                    "POST",
                    "/api/v1/solve",
                    body=body3,
                    headers={
                        "Host": f"127.0.0.1:{port}",
                        "Origin": f"http://127.0.0.1:{port}",
                        "Content-Type": "application/json",
                        "Content-Length": str(len(body3)),
                    },
                )
                r3 = conn3.getresponse()
                p3 = json.loads(r3.read().decode("utf-8"))
                self.assertEqual(r3.status, 200)
                self.assertEqual(p3["worker_pid"], first_pid)
                self.assertEqual(len(mgr.spawned_pids), 1)
            finally:
                conn3.close()
        finally:
            server.shutdown()
            server.server_close()
            th.join(timeout=2.0)

        self.assertTrue(_is_pid_reaped(first_pid))
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

    def test_r3_f1_launch_cleanup_wait_exhaustion_poisons_and_blocks_admission(self):
        """V1-A-R3-F1: unfinished cleanup owner at deadline poisons synchronously, retains PID, blocks concurrent respawn."""
        import v1_worker_bridge as bridge

        baseline_pipes = _list_open_pipe_inodes()
        sleeping_cmd = self._make_fault_worker_script("import time\ntime.sleep(5)\n")
        live_procs: list[subprocess.Popen] = []

        kill_entered = threading.Event()
        kill_release = threading.Event()
        runner_returned_ev = threading.Event()
        allow_fail = [True]

        def launch_reg_then_raise(cmd, pass_fds, register_pid=None):
            proc = subprocess.Popen(sleeping_cmd, pass_fds=pass_fds, close_fds=True)
            live_procs.append(proc)
            if register_pid is not None:
                register_pid(proc)
            raise RuntimeError("injected post-PID failure")

        def slow_failing_kill(proc):
            if allow_fail[0]:
                kill_entered.set()
                kill_release.wait(timeout=3.0)
                raise PermissionError("simulated slow EPERM teardown owner")
            proc.kill()

        mgr = bridge.WorkerManager(
            response_deadline_s=1.0,
            worker_reap_timeout_s=0.20,
            launch_fn=launch_reg_then_raise,
            kill_fn=slow_failing_kill,
            on_after_runner_returned_before_cleanup=lambda _s: runner_returned_ev.set(),
        )
        # Hold main caller right before handoff until runner claims cleanup_started and stalls inside kill_fn
        handoff_wait_ev = threading.Event()
        def hold_handoff(_slot):
            self.assertTrue(kill_entered.wait(timeout=2.0))
            handoff_wait_ev.set()

        mgr._on_before_slot_to_pending_handoff = hold_handoff

        res_box: list = []
        th = threading.Thread(target=lambda: res_box.append(mgr.execute("/api/v1/solve", {"request_id": 1})))
        th.start()
        self.assertTrue(runner_returned_ev.wait(timeout=2.0))
        self.assertTrue(handoff_wait_ev.wait(timeout=2.0))

        # Main thread hits cleanup_done_cond.wait timeout (~0.20s) while runner STILL holds cleanup_started=True
        th.join(timeout=2.0)
        self.assertFalse(th.is_alive())
        self.assertEqual(len(res_box), 1)
        self.assertEqual(res_box[0].status_code, 503)
        self.assertEqual(res_box[0].payload["error"]["code"], "WORKER_UNAVAILABLE_POISONED")
        self.assertTrue(mgr._worker_poisoned)
        self.assertEqual(mgr.quarantined_pids, [live_procs[0].pid])

        # Concurrent/subsequent admission MUST immediately get 503 POISONED with ZERO duplicate children
        res2 = mgr.execute("/api/v1/solve", {"request_id": 2})
        self.assertEqual(res2.status_code, 503)
        self.assertEqual(res2.payload["error"]["code"], "WORKER_UNAVAILABLE_POISONED")
        self.assertEqual(len(mgr.spawned_pids), 1)

        # Release stalled cleanup owner & clear transient kill fault -> shutdown cleanly reaps quarantined child
        kill_release.set()
        allow_fail[0] = False
        mgr.shutdown()
        self.assertEqual(mgr.quarantined_pids, [])
        self.assertTrue(_is_pid_reaped(live_procs[0].pid))
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

    def test_r3_f2_single_absolute_budget_contention_max_response_and_true_mid_parse_expiry(self):
        """V1-A-R3-F2: single budget across lock+drain+reap+decode, near-8MiB string/bool JSON, real mid-parse expiry."""
        import v1_worker_bridge as bridge

        baseline_pipes = _list_open_pipe_inodes()

        # (a) Contention across kill/reap + I/O drain shares ONE teardown deadline
        def slow_kill(proc):
            time.sleep(0.18)
            proc.kill()

        mgr_a = bridge.WorkerManager(response_deadline_s=0.20, worker_reap_timeout_s=0.40, kill_fn=slow_kill)
        try:
            t0 = time.monotonic()
            res_a = mgr_a.execute("/api/v1/solve", {"request_id": 1, "delay_s": 1.0})
            elapsed = time.monotonic() - t0
            self.assertEqual(res_a.status_code, 504)
            # Single deadline (~0.20s) + single teardown (~0.40s) + scheduler tolerance
            self.assertLess(elapsed, 0.80)
        finally:
            mgr_a.shutdown()
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

        # (b) Near-8MiB string/bool-heavy JSON succeeds inside budget, AND parser-entry clock expiry fires INSIDE parser
        big_str_bool_worker = self._make_fault_worker_script(
            "import argparse, json, os, struct\n"
            "def read_exact(fd, n):\n"
            "  b = bytearray()\n"
            "  while len(b) < n:\n"
            "    c = os.read(fd, n - len(b))\n"
            "    if not c: raise EOFError()\n"
            "    b.extend(c)\n"
            "  return bytes(b)\n"
            "p = argparse.ArgumentParser()\n"
            "p.add_argument('--req-fd', type=int); p.add_argument('--resp-fd', type=int)\n"
            "a, _ = p.parse_known_args()\n"
            "ready = json.dumps({'type':'READY','pid':os.getpid(),'req_ino':os.fstat(a.req_fd).st_ino,'resp_ino':os.fstat(a.resp_fd).st_ino}).encode()\n"
            "os.write(a.resp_fd, struct.pack('>I', len(ready)) + ready)\n"
            "payload_str = 'x' * 7500000\n"
            "while True:\n"
            "  try: hdr = read_exact(a.req_fd, 4)\n"
            "  except EOFError: break\n"
            "  n = struct.unpack('>I', hdr)[0]\n"
            "  req = json.loads(read_exact(a.req_fd, n).decode())\n"
            "  if req['request'].get('mode') == 'nums':\n"
            "    out = ('{\"ipc_token\":' + str(req['ipc_token']) + ',\"arr\":[' + ','.join(['1']*50000) + ']}').encode()\n"
            "  else:\n"
            "    out = json.dumps({'ipc_token': req['ipc_token'], 'flags': [True, False]*5000, 'blob': payload_str}).encode()\n"
            "  mv = memoryview(struct.pack('>I', len(out)) + out)\n"
            "  sent = 0\n"
            "  while sent < len(mv): sent += os.write(a.resp_fd, mv[sent:])\n"
        )
        now_b = [100.0]
        parser_entered = [False]

        def parse_entry_expire():
            if len(mgr_b.spawned_pids) > 0:
                parser_entered[0] = True
                now_b[0] = 200.0

        mgr_b = bridge.WorkerManager(
            response_deadline_s=5.0,
            worker_reap_timeout_s=0.6,
            custom_worker_cmd=big_str_bool_worker,
            clock=lambda: now_b[0],
        )
        try:
            res_big = mgr_b.execute("/api/v1/solve", {"request_id": 10})
            self.assertEqual(res_big.status_code, 200)
            self.assertGreater(len(res_big.payload["blob"]), 7000000)
            self.assertLessEqual(len(res_big.payload["blob"]), bridge.MAX_IPC_RESPONSE_BYTES)

            # Now attach parser-entry expiry strictly AFTER full IPC read succeeds, BEFORE json.loads finishes
            mgr_b._on_json_parse_entry = parse_entry_expire
            res_parse_exp = mgr_b.execute("/api/v1/solve", {"request_id": 11, "mode": "nums"})
            self.assertTrue(parser_entered[0], "Parser entry hook must execute strictly after IPC read")
            self.assertEqual(res_parse_exp.status_code, 504)
            self.assertEqual(res_parse_exp.payload["error"]["code"], "SOLVE_DEADLINE_EXCEEDED")
            self.assertTrue(_is_pid_reaped(mgr_b.spawned_pids[0]))

            mgr_b._on_json_parse_entry = None
            mgr_b.custom_worker_cmd = None
            now_b[0] = 300.0
            res_clean = mgr_b.execute("/api/v1/solve", {"request_id": 12})
            self.assertEqual(res_clean.status_code, 200)
        finally:
            mgr_b.shutdown()
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

        # (c) Uncooperative stalled decoder aborts strictly within response_deadline + worker_reap_timeout (no +50ms grace)
        stall_ev = threading.Event()
        mgr_c = bridge.WorkerManager(response_deadline_s=1.0, worker_reap_timeout_s=0.20)
        try:
            self.assertEqual(mgr_c.execute("/api/v1/solve", {"request_id": 20}).status_code, 200)
            mgr_c.response_deadline_s = 0.15
            mgr_c._on_decode_transform = lambda obj: (stall_ev.wait(timeout=2.0), obj)[1]
            t_start = time.monotonic()
            res_c = mgr_c.execute("/api/v1/solve", {"request_id": 21})
            dt_c = time.monotonic() - t_start
            self.assertEqual(res_c.status_code, 503)
            self.assertEqual(res_c.payload["error"]["code"], "WORKER_UNAVAILABLE_POISONED")
            # 0.15s deadline + 0.20s reap = 0.35s + small scheduler slack (<0.60s)
            self.assertLess(dt_c, 0.60)
            self.assertEqual(len(mgr_c.spawned_pids), 1)
        finally:
            stall_ev.set()
            mgr_c.shutdown()
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

    def test_r3_m1_http_float_expansion_exact_depth_and_oversized_int_delay(self):
        """V1-A-R3-M1: short float expansion, depth=64 payload, 400-digit int delay_s, and over-limit rejection."""
        import v1_worker_bridge as bridge
        from run_explorer import create_server

        baseline_pipes = _list_open_pipe_inodes()
        mgr = bridge.WorkerManager(response_deadline_s=2.0, worker_reap_timeout_s=0.8)
        server, port = create_server("127.0.0.1", 0, worker_manager=mgr)
        th = threading.Thread(target=server.serve_forever, daemon=True)
        th.start()
        try:
            def post_raw(raw_bytes: bytes) -> tuple[int, dict]:
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3.0)
                try:
                    conn.request(
                        "POST",
                        "/api/v1/solve",
                        body=raw_bytes,
                        headers={
                            "Host": f"127.0.0.1:{port}",
                            "Origin": f"http://127.0.0.1:{port}",
                            "Content-Type": "application/json",
                            "Content-Length": str(len(raw_bytes)),
                        },
                    )
                    resp = conn.getresponse()
                    return resp.status, json.loads(resp.read().decode("utf-8"))
                finally:
                    conn.close()

            # 1. Exact short-exponent float array (8022 bytes <= 8192 HTTP limit) -> MUST return 200 without 30KB expansion
            floats_body = b'{"request_id":1,"x":[' + b",".join([b"1e15"] * 1600) + b"]}"
            self.assertLessEqual(len(floats_body), bridge.MAX_HTTP_BODY_BYTES)
            s1, p1 = post_raw(floats_body)
            self.assertEqual(s1, 200)
            first_pid = p1["worker_pid"]

            # 2. Exact depth 64 client object ({"request_id":2,"x":[[...[0]...]]} with 62 lists -> depth 64) -> MUST succeed (envelope depth 65 <= 68)
            depth64_body = b'{"request_id":2,"x":' + b"[" * 62 + b"0" + b"]" * 62 + b"}"
            s2, p2 = post_raw(depth64_body)
            self.assertEqual(s2, 200)
            self.assertEqual(p2["worker_pid"], first_pid)

            # 3. Depth 65 client payload -> rejected pre-admission with 400 INVALID_JSON; worker untouched
            depth65_body = b'{"request_id":3,"x":' + b"[" * 63 + b"0" + b"]" * 63 + b"}"
            s3, p3 = post_raw(depth65_body)
            self.assertEqual(s3, 400)
            self.assertEqual(p3["error"]["code"], "INVALID_JSON")

            # 4. Huge 400-digit integer delay_s -> NO OverflowError worker crash; healthy worker preserved
            huge_delay_body = b'{"request_id":4,"delay_s":' + b"1" + b"0" * 400 + b"}"
            s4, p4 = post_raw(huge_delay_body)
            self.assertEqual(s4, 200)
            self.assertEqual(p4["worker_pid"], first_pid)

            # 5. Direct Python WorkerManager.execute over IPC size limit -> rejected 413 pre-admission without touching worker
            big_direct = mgr.execute("/api/v1/solve", {"request_id": 5, "pad": "a" * 20000})
            self.assertEqual(big_direct.status_code, 413)
            self.assertEqual(len(mgr.spawned_pids), 1)
        finally:
            server.shutdown()
            server.server_close()
            th.join(timeout=2.0)

        self.assertTrue(_is_pid_reaped(first_pid))
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

    def test_r3_m2_healthy_handoff_under_reused_numeric_fd_keeps_true_closure_proof(self):
        """V1-A-R3-M2: numeric FD reuse between child_fd close and handoff still reports true closure proof & leaves sentinel untouched."""
        import v1_worker_bridge as bridge

        baseline_pipes = _list_open_pipe_inodes()
        # Allocate a low sentinel pipe FIRST only to know we can refill closed child FD slots cleanly
        held_sentinels: list[tuple[int, int]] = []
        original_child_fds: list[int] = []

        def capture_original_child_fds(slot):
            original_child_fds.extend([fd for fd in slot.child_fds if fd is not None])

        def occupy_closed_fds(_slot):
            # Create multiple pipes right after launch_runner closed child_fds so freed numeric FD slots are occupied
            for _ in range(4):
                sr, sw = os.pipe()
                os.write(sw, b"ok")
                held_sentinels.append((sr, sw))

        mgr = bridge.WorkerManager(
            response_deadline_s=2.0,
            worker_reap_timeout_s=0.8,
            on_after_slot_publish_before_runner=capture_original_child_fds,
            on_before_slot_to_pending_handoff=occupy_closed_fds,
        )
        try:
            res = mgr.execute("/api/v1/solve", {"request_id": 1})
            self.assertEqual(res.status_code, 200)
            self.assertEqual(len(original_child_fds), 2)
            reused_fds = {fd for pair in held_sentinels for fd in pair}
            self.assertTrue(
                set(original_child_fds).issubset(reused_fds),
                f"Expected original child FDs {original_child_fds} to be reused by sentinels {reused_fds}",
            )
            self.assertTrue(res.payload["parent_closed_unused_ends"])
            self.assertEqual(
                sorted(res.payload["child_open_pipe_inos"]),
                sorted([res.payload["child_req_ino"], res.payload["child_resp_ino"]]),
            )
            # Every sentinel pipe MUST remain open and still contain its byte untouched
            for sr, sw in held_sentinels:
                self.assertTrue(bridge._is_fd_open(sr))
                self.assertTrue(bridge._is_fd_open(sw))
                self.assertEqual(os.read(sr, 2), b"ok")
        finally:
            for sr, sw in held_sentinels:
                os.close(sr)
                os.close(sw)
            mgr.shutdown()

        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

    def test_r4_f1_caller_owned_kill_stall_watchdog_post_pid_launch_and_warmed_worker(self):
        """V1-A-R4-F1: caller-owned blocking kill_fn on post-PID launch stall and warmed worker timeout returns bounded 503 POISONED before kill releases, preserves single supervisor, blocks concurrent admission, and reaps on release."""
        import v1_worker_bridge as bridge

        baseline_pipes = _list_open_pipe_inodes()
        sleeping_cmd = self._make_fault_worker_script("import time\ntime.sleep(5)\n")

        # (a) Post-PID launch stall where execute thread itself enters _abort_launch_slot and triggers kill_fn that blocks past reap deadline
        launch_release_ev = threading.Event()
        kill_entered_a = threading.Event()
        kill_release_a = threading.Event()
        pid_registered_a = threading.Event()
        kill_calls_a = [0]
        live_procs_a: list[subprocess.Popen] = []

        def stalled_post_pid_launch_a(cmd, pass_fds, register_pid=None):
            proc = subprocess.Popen(sleeping_cmd, pass_fds=pass_fds, close_fds=True)
            live_procs_a.append(proc)
            if register_pid is not None:
                register_pid(proc)
            pid_registered_a.set()
            launch_release_ev.wait(timeout=3.0)
            return proc

        def blocking_kill_a(proc):
            kill_calls_a[0] += 1
            kill_entered_a.set()
            kill_release_a.wait(timeout=3.0)
            proc.kill()

        mgr_a = bridge.WorkerManager(
            response_deadline_s=0.15,
            worker_reap_timeout_s=0.18,
            launch_fn=stalled_post_pid_launch_a,
            kill_fn=blocking_kill_a,
        )
        res_a_box: list = []
        th_a = threading.Thread(target=lambda: res_a_box.append(mgr_a.execute("/api/v1/solve", {"request_id": 1})))
        t0_a = time.monotonic()
        th_a.start()
        self.assertTrue(pid_registered_a.wait(timeout=2.0))
        self.assertTrue(kill_entered_a.wait(timeout=2.0))

        # Must return BridgeResult strictly BEFORE kill_release_a or launch_release_ev is set!
        th_a.join(timeout=1.2)
        elapsed_a = time.monotonic() - t0_a
        self.assertFalse(th_a.is_alive(), "execute() hung on caller-owned blocking kill_fn during launch abort")
        self.assertFalse(kill_release_a.is_set())
        self.assertLess(elapsed_a, 0.70)
        self.assertEqual(len(res_a_box), 1)
        self.assertEqual(res_a_box[0].status_code, 503)
        self.assertEqual(res_a_box[0].payload["error"]["code"], "WORKER_UNAVAILABLE_POISONED")
        self.assertTrue(mgr_a._worker_poisoned)
        self.assertEqual(mgr_a.quarantined_pids, [live_procs_a[0].pid])
        self.assertEqual(kill_calls_a[0], 1)

        # Concurrent/subsequent callers while kill is still blocked get immediate 503 WORKER_UNAVAILABLE_POISONED and zero respawn
        conc_a = mgr_a.execute("/api/v1/study", {"request_id": 2})
        self.assertEqual(conc_a.status_code, 503)
        self.assertEqual(conc_a.payload["error"]["code"], "WORKER_UNAVAILABLE_POISONED")
        self.assertEqual(len(mgr_a.spawned_pids), 1)

        # Release stalled launcher and kill -> shutdown reuses the same authoritative supervisor (no duplicate kill) and reaps child
        launch_release_ev.set()
        kill_release_a.set()
        mgr_a.shutdown()
        self.assertEqual(kill_calls_a[0], 1)
        self.assertEqual(mgr_a.quarantined_pids, [])
        self.assertTrue(_is_pid_reaped(live_procs_a[0].pid))
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

        # (b) Warmed worker whose IPC times out while kill_fn blocks past worker_reap_timeout_s on execute's thread
        kill_entered_b = threading.Event()
        kill_release_b = threading.Event()
        kill_calls_b = [0]

        def blocking_kill_b(proc):
            kill_calls_b[0] += 1
            kill_entered_b.set()
            kill_release_b.wait(timeout=3.0)
            proc.kill()

        mgr_b = bridge.WorkerManager(
            response_deadline_s=1.0,
            worker_reap_timeout_s=0.18,
            kill_fn=blocking_kill_b,
        )
        warm_res = mgr_b.execute("/api/v1/solve", {"request_id": 10})
        self.assertEqual(warm_res.status_code, 200)
        warm_pid = warm_res.payload["worker_pid"]

        mgr_b.response_deadline_s = 0.15
        res_b_box: list = []
        th_b = threading.Thread(
            target=lambda: res_b_box.append(mgr_b.execute("/api/v1/solve", {"request_id": 11, "delay_s": 2.0}))
        )
        t0_b = time.monotonic()
        th_b.start()
        self.assertTrue(kill_entered_b.wait(timeout=2.0))

        # Must return 503 WORKER_UNAVAILABLE_POISONED strictly BEFORE kill_release_b is set!
        th_b.join(timeout=1.2)
        elapsed_b = time.monotonic() - t0_b
        self.assertFalse(th_b.is_alive(), "execute() hung on caller-owned blocking kill_fn during warmed worker timeout")
        self.assertFalse(kill_release_b.is_set())
        self.assertLess(elapsed_b, 0.70)
        self.assertEqual(len(res_b_box), 1)
        self.assertEqual(res_b_box[0].status_code, 503)
        self.assertEqual(res_b_box[0].payload["error"]["code"], "WORKER_UNAVAILABLE_POISONED")
        self.assertTrue(mgr_b._worker_poisoned)
        self.assertEqual(mgr_b.quarantined_pids, [warm_pid])
        self.assertEqual(kill_calls_b[0], 1)

        # Concurrent caller while kill is still blocked gets 503 POISONED, never 429, zero duplicate workers
        conc_b = mgr_b.execute("/api/v1/solve", {"request_id": 12})
        self.assertEqual(conc_b.status_code, 503)
        self.assertEqual(conc_b.payload["error"]["code"], "WORKER_UNAVAILABLE_POISONED")
        self.assertEqual(len(mgr_b.spawned_pids), 1)

        # Even if shutdown() is called while kill_fn is blocked, shutdown() itself is bounded by worker_reap_timeout_s!
        t0_shut = time.monotonic()
        mgr_b.shutdown()
        self.assertLess(time.monotonic() - t0_shut, 0.50)
        self.assertEqual(kill_calls_b[0], 1)

        # Now release blocking kill and run final shutdown to reap cleanly
        kill_release_b.set()
        mgr_b.shutdown()
        self.assertEqual(kill_calls_b[0], 1)
        self.assertEqual(mgr_b.quarantined_pids, [])
        self.assertTrue(_is_pid_reaped(warm_pid))
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

    def test_r4_f1_real_teardown_lock_and_active_io_contention_and_expired_handoff_shared_budget(self):
        """V1-A-R4-F1: real teardown_exec_lock contender + delayed active_io lease drain + reap share one deadline, real monotonic parser-entry expiry & near-limit 5s success, and expired handoff cleanup budget."""
        import v1_worker_bridge as bridge

        baseline_pipes = _list_open_pipe_inodes()

        # (a) Real teardown_exec_lock contender + active_io lease holder + kill/reap sharing ONE teardown deadline
        mgr_a = bridge.WorkerManager(response_deadline_s=1.0, worker_reap_timeout_s=0.45)
        try:
            warm_a = mgr_a.execute("/api/v1/solve", {"request_id": 1})
            self.assertEqual(warm_a.status_code, 200)
            handle_a = mgr_a._active_worker
            self.assertIsNotNone(handle_a)

            # Hold teardown_exec_lock for 0.12s AND hold an active_io lease for 0.22s concurrently after timeout starts
            lock_holder_ready = threading.Event()
            io_holder_ready = threading.Event()
            teardown_started = threading.Event()

            orig_ensure_cleanup = mgr_a._ensure_cleanup_deadline
            captured_td_a: list[float] = []

            def spy_ensure_cleanup(cleanup_box):
                td = orig_ensure_cleanup(cleanup_box)
                captured_td_a.append(td)
                teardown_started.set()
                return td

            mgr_a._ensure_cleanup_deadline = spy_ensure_cleanup

            def hold_lock_and_io():
                assert handle_a is not None
                handle_a.teardown_exec_lock.acquire()
                with mgr_a._admission_lock:
                    handle_a.active_io += 1
                lock_holder_ready.set()
                io_holder_ready.set()
                teardown_started.wait(timeout=2.0)
                time.sleep(0.10)
                handle_a.teardown_exec_lock.release()
                time.sleep(0.10)
                with mgr_a._admission_lock:
                    handle_a.active_io -= 1
                    mgr_a._state_cond.notify_all()

            contender_th = threading.Thread(target=hold_lock_and_io, daemon=True)
            contender_th.start()
            self.assertTrue(lock_holder_ready.wait(timeout=1.0))
            self.assertTrue(io_holder_ready.wait(timeout=1.0))

            mgr_a.response_deadline_s = 0.15
            t0_a = time.monotonic()
            res_a = mgr_a.execute("/api/v1/solve", {"request_id": 2, "delay_s": 1.0})
            t_end_a = time.monotonic()
            contender_th.join(timeout=1.0)

            self.assertEqual(res_a.status_code, 504)
            self.assertEqual(len(set(captured_td_a)), 1, "All teardown steps must share one exact deadline")
            # Remaining budget after lock (0.10s) and active_io drain (+0.10s = 0.20s total) completed well before single 0.45s deadline
            self.assertLessEqual(t_end_a, captured_td_a[0] + 0.08)
            self.assertLess(t_end_a - t0_a, 0.70)
            self.assertTrue(_is_pid_reaped(warm_a.payload["worker_pid"]))
        finally:
            mgr_a.shutdown()
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

        # (b) Real monotonic clock: near-8MiB response succeeds inside 5.0s, and real monotonic expiry at parser entry aborts mid-parse
        big_real_worker = self._make_fault_worker_script(
            "import argparse, json, os, struct, time\n"
            "def read_exact(fd, n):\n"
            "  b = bytearray()\n"
            "  while len(b) < n:\n"
            "    c = os.read(fd, n - len(b))\n"
            "    if not c: raise EOFError()\n"
            "    b.extend(c)\n"
            "  return bytes(b)\n"
            "p = argparse.ArgumentParser()\n"
            "p.add_argument('--req-fd', type=int); p.add_argument('--resp-fd', type=int)\n"
            "a, _ = p.parse_known_args()\n"
            "ready = json.dumps({'type':'READY','pid':os.getpid(),'req_ino':os.fstat(a.req_fd).st_ino,'resp_ino':os.fstat(a.resp_fd).st_ino}).encode()\n"
            "os.write(a.resp_fd, struct.pack('>I', len(ready)) + ready)\n"
            "payload_str = 'y' * 7500000\n"
            "nums_str = '[' + ','.join(['1']*60000) + ']'\n"
            "while True:\n"
            "  try: hdr = read_exact(a.req_fd, 4)\n"
            "  except EOFError: break\n"
            "  n = struct.unpack('>I', hdr)[0]\n"
            "  req = json.loads(read_exact(a.req_fd, n).decode())\n"
            "  if req['request'].get('mode') == 'expire_in_parse':\n"
            "    out = ('{\"ipc_token\":' + str(req['ipc_token']) + ',\"arr\":' + nums_str + '}').encode()\n"
            "  else:\n"
            "    out = json.dumps({'ipc_token': req['ipc_token'], 'flags': [True, False]*5000, 'blob': payload_str}).encode()\n"
            "  mv = memoryview(struct.pack('>I', len(out)) + out)\n"
            "  sent = 0\n"
            "  while sent < len(mv): sent += os.write(a.resp_fd, mv[sent:])\n"
        )
        # Note: NO mock clock passed here — uses real time.monotonic!
        mgr_b = bridge.WorkerManager(
            response_deadline_s=5.0,
            worker_reap_timeout_s=0.5,
            custom_worker_cmd=big_real_worker,
        )
        try:
            t0_big = time.monotonic()
            res_big = mgr_b.execute("/api/v1/solve", {"request_id": 10})
            dt_big = time.monotonic() - t0_big
            self.assertEqual(res_big.status_code, 200)
            self.assertLess(dt_big, 5.0)
            self.assertEqual(len(res_big.payload["blob"]), 7500000)

            # Now test real monotonic expiry after full raw frame read at parser entry
            mgr_b.response_deadline_s = 0.18
            parse_entry_times: list[float] = []

            def sleep_past_real_deadline_at_parse_entry():
                parse_entry_times.append(time.monotonic())
                time.sleep(0.20)

            mgr_b._on_json_parse_entry = sleep_past_real_deadline_at_parse_entry
            res_exp = mgr_b.execute("/api/v1/solve", {"request_id": 11, "mode": "expire_in_parse"})
            self.assertEqual(len(parse_entry_times), 1)
            self.assertEqual(res_exp.status_code, 504)
            self.assertEqual(res_exp.payload["error"]["code"], "SOLVE_DEADLINE_EXCEEDED")
            self.assertTrue(_is_pid_reaped(mgr_b.spawned_pids[0]))
        finally:
            mgr_b.shutdown()
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

        # (c) Expired slot-to-pending handoff shares ONE cleanup_box deadline across _abort_launch_slot and outer _IpcTimeoutError catch
        handoff_cleanup_boxes: list[float] = []
        abort_deadlines_seen: list[float] = []

        mgr_c = bridge.WorkerManager(
            response_deadline_s=0.12,
            worker_reap_timeout_s=0.30,
            on_before_slot_to_pending_handoff=lambda _s: time.sleep(0.16),
        )
        orig_ensure_c = mgr_c._ensure_cleanup_deadline
        orig_abort_c = mgr_c._abort_launch_slot

        def spy_ensure_c(box):
            td = orig_ensure_c(box)
            handoff_cleanup_boxes.append(td)
            return td

        def spy_abort_c(slot, *, deadline, reason, wait_for_runner):
            abort_deadlines_seen.append(deadline)
            return orig_abort_c(slot, deadline=deadline, reason=reason, wait_for_runner=wait_for_runner)

        mgr_c._ensure_cleanup_deadline = spy_ensure_c
        mgr_c._abort_launch_slot = spy_abort_c
        try:
            res_c = mgr_c.execute("/api/v1/solve", {"request_id": 30})
            self.assertEqual(res_c.status_code, 504)
            self.assertEqual(res_c.payload["error"]["code"], "SOLVE_DEADLINE_EXCEEDED")
            # Both handoff cleanup and outer catch must reference the exact same single cleanup deadline!
            self.assertGreaterEqual(len(handoff_cleanup_boxes), 2)
            self.assertEqual(len(set(handoff_cleanup_boxes)), 1)
            self.assertEqual(abort_deadlines_seen, [handoff_cleanup_boxes[0]])
            self.assertTrue(_is_pid_reaped(mgr_c.spawned_pids[0]))
        finally:
            mgr_c.shutdown()
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

    def test_r4_m1_direct_execute_coercion_duplicate_keys_tuple_depth_and_raw_bytes_invariants(self):
        """V1-A-R4-M1: direct execute rejects int/str key coercion collisions, non-string keys, tuple nesting/depth, and invalid/mismatched raw_request_bytes before admission without touching healthy worker."""
        import v1_worker_bridge as bridge

        baseline_pipes = _list_open_pipe_inodes()
        mgr = bridge.WorkerManager(response_deadline_s=2.0, worker_reap_timeout_s=0.6)
        try:
            # Warm healthy worker first
            warm = mgr.execute("/api/v1/solve", {"request_id": 1})
            self.assertEqual(warm.status_code, 200)
            healthy_pid = warm.payload["worker_pid"]
            self.assertEqual(len(mgr.spawned_pids), 1)

            # 1. Key-coercion duplicate collision: {1: 'a', '1': 'b'} -> 400 pre-admission
            res_collision = mgr.execute("/api/v1/solve", {"request_id": 2, "x": {1: "a", "1": "b"}})
            self.assertEqual(res_collision.status_code, 400)
            self.assertIn(res_collision.payload["error"]["code"], ("INVALID_JSON", "DUPLICATE_KEY"))
            self.assertEqual(res_collision.payload["request_id"], 2)

            # 2. Non-string key even without collision: {1: 'a'} -> 400 INVALID_JSON pre-admission
            res_non_str_key = mgr.execute("/api/v1/solve", {"request_id": 3, "x": {1: "a"}})
            self.assertEqual(res_non_str_key.status_code, 400)
            self.assertEqual(res_non_str_key.payload["error"]["code"], "INVALID_JSON")

            # 3. Tuple container & deep tuple nesting (>64) -> 400 INVALID_JSON pre-admission
            res_tuple = mgr.execute("/api/v1/solve", {"request_id": 4, "x": (1, 2, 3)})
            self.assertEqual(res_tuple.status_code, 400)
            self.assertEqual(res_tuple.payload["error"]["code"], "INVALID_JSON")

            deep_tuple: Any = 0
            for _ in range(70):
                deep_tuple = (deep_tuple,)
            res_deep_tuple = mgr.execute("/api/v1/solve", {"request_id": 5, "x": deep_tuple})
            self.assertEqual(res_deep_tuple.status_code, 400)
            self.assertEqual(res_deep_tuple.payload["error"]["code"], "INVALID_JSON")

            # 4. Direct raw_request_bytes bypass attempts: duplicate keys, invalid JSON, depth 65, and payload mismatch -> 400
            for req_id, payload, raw_b, exp_status, exp_code in (
                (6, {"request_id": 6, "a": 1}, b'{"request_id":6,"a":1,"a":2}', 400, "DUPLICATE_KEY"),
                (7, {"request_id": 7, "a": 1}, b'{"request_id":7,"a":NaN}', 400, "INVALID_JSON"),
                (8, {"request_id": 8, "a": 1}, b'{"request_id":8,"a":' + b"[" * 63 + b"0" + b"]" * 63 + b"}", 400, "INVALID_JSON"),
                (9, {"request_id": 9, "a": 1}, b'{"request_id":9,"a":2}', 400, "INVALID_JSON"),
                (10, {"request_id": 10, "pad": "x" * 16300}, b'{"request_id":10,"pad":"' + b"x" * 16300 + b'"}', 413, "PAYLOAD_TOO_LARGE"),
            ):
                res_raw = mgr.execute("/api/v1/solve", payload, raw_request_bytes=raw_b)
                self.assertEqual(res_raw.status_code, exp_status, f"Failed for req_id={req_id}")
                self.assertEqual(res_raw.payload["error"]["code"], exp_code, f"Failed code for req_id={req_id}")

            # 5. Boundary payload size where request_bytes + max metadata > 16384 -> 413 PAYLOAD_TOO_LARGE pre-admission
            boundary_pad = "z" * (bridge.MAX_IPC_REQUEST_BYTES - 150)
            res_bound = mgr.execute("/api/v1/solve", {"request_id": 11, "pad": boundary_pad})
            self.assertEqual(res_bound.status_code, 413)
            self.assertEqual(res_bound.payload["error"]["code"], "PAYLOAD_TOO_LARGE")

            # Healthy worker MUST still have the exact same PID, zero respawns, zero teardowns
            after = mgr.execute("/api/v1/solve", {"request_id": 12})
            self.assertEqual(after.status_code, 200)
            self.assertEqual(after.payload["worker_pid"], healthy_pid)
            self.assertEqual(len(mgr.spawned_pids), 1)
        finally:
            mgr.shutdown()

        self.assertTrue(_is_pid_reaped(healthy_pid))
        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

    def test_r5_exact_json_representation_equality_and_pre_admission_isolation(self):
        """V1-A R5: strict type-identical JSON representation equality rejects bool/int/float/signed-zero/order mismatches before worker admission without spawning cold workers or harming warmed workers."""
        import v1_worker_bridge as bridge

        baseline_pipes = _list_open_pipe_inodes()

        rejected_cases: list[tuple[str, dict[str, Any], bytes, int, str]] = [
            # Boolean vs integer in both directions
            ("true_vs_1", {"request_id": 1, "flag": True}, b'{"request_id":1,"flag":1}', 400, "INVALID_JSON"),
            ("1_vs_true", {"request_id": 2, "flag": 1}, b'{"request_id":2,"flag":true}', 400, "INVALID_JSON"),
            ("false_vs_0", {"request_id": 3, "flag": False}, b'{"request_id":3,"flag":0}', 400, "INVALID_JSON"),
            ("0_vs_false", {"request_id": 4, "flag": 0}, b'{"request_id":4,"flag":false}', 400, "INVALID_JSON"),
            # Integer vs float in both directions
            ("1_vs_1.0", {"request_id": 5, "v": 1}, b'{"request_id":5,"v":1.0}', 400, "INVALID_JSON"),
            ("1.0_vs_1", {"request_id": 6, "v": 1.0}, b'{"request_id":6,"v":1}', 400, "INVALID_JSON"),
            # Boolean vs float in both directions
            ("true_vs_1.0", {"request_id": 7, "v": True}, b'{"request_id":7,"v":1.0}', 400, "INVALID_JSON"),
            ("1.0_vs_true", {"request_id": 8, "v": 1.0}, b'{"request_id":8,"v":true}', 400, "INVALID_JSON"),
            ("false_vs_0.0", {"request_id": 9, "v": False}, b'{"request_id":9,"v":0.0}', 400, "INVALID_JSON"),
            ("0.0_vs_false", {"request_id": 10, "v": 0.0}, b'{"request_id":10,"v":false}', 400, "INVALID_JSON"),
            # Boolean vs numeric request_id (including False vs 0 where extract_safe_request_id returns None for both)
            ("reqid_true_vs_1", {"request_id": True}, b'{"request_id":1}', 400, "INVALID_JSON"),
            ("reqid_1_vs_true", {"request_id": 1}, b'{"request_id":true}', 400, "INVALID_JSON"),
            ("reqid_false_vs_0", {"request_id": False}, b'{"request_id":0}', 400, "INVALID_JSON"),
            ("reqid_0_vs_false", {"request_id": 0}, b'{"request_id":false}', 400, "INVALID_JSON"),
            # Nested dict/list type mismatches & list ordering mismatch
            (
                "nested_mismatch",
                {"request_id": 11, "nested": {"items": [1, {"ok": False}]}},
                b'{"request_id":11,"nested":{"items":[true,{"ok":0}]}}',
                400,
                "INVALID_JSON",
            ),
            ("list_order_mismatch", {"request_id": 12, "arr": [1, 2]}, b'{"request_id":12,"arr":[2,1]}', 400, "INVALID_JSON"),
            ("dict_key_mismatch", {"request_id": 13, "a": 1}, b'{"request_id":13,"b":1}', 400, "INVALID_JSON"),
            # Signed zero (+0.0 vs -0.0) in both directions under strict signed-zero representation contract
            ("pos_zero_vs_neg_zero", {"request_id": 14, "z": 0.0}, b'{"request_id":14,"z":-0.0}', 400, "INVALID_JSON"),
            ("neg_zero_vs_pos_zero", {"request_id": 15, "z": -0.0}, b'{"request_id":15,"z":0.0}', 400, "INVALID_JSON"),
            # Duplicate keys, non-finite literals, excessive depth (>64), non-JSON types, oversized payload
            ("dup_key", {"request_id": 16, "a": 1}, b'{"request_id":16,"a":1,"a":2}', 400, "DUPLICATE_KEY"),
            ("non_finite", {"request_id": 17, "a": 1}, b'{"request_id":17,"a":Infinity}', 400, "INVALID_JSON"),
            (
                "excessive_depth",
                {"request_id": 18, "a": 1},
                b'{"request_id":18,"a":' + b"[" * 63 + b"0" + b"]" * 63 + b"}",
                400,
                "INVALID_JSON",
            ),
            (
                "oversized",
                {"request_id": 19, "pad": "x" * 16300},
                b'{"request_id":19,"pad":"' + b"x" * 16300 + b'"}',
                413,
                "PAYLOAD_TOO_LARGE",
            ),
        ]

        # 1. Cold manager: zero workers ever spawned for any rejected request (including tuple/non-str key direct calls)
        cold_mgr = bridge.WorkerManager(response_deadline_s=2.0, worker_reap_timeout_s=0.6)
        try:
            for label, payload, raw_b, exp_status, exp_code in rejected_cases:
                res = cold_mgr.execute("/api/v1/solve", payload, raw_request_bytes=raw_b)
                self.assertEqual(res.status_code, exp_status, f"Cold status mismatch for {label}")
                self.assertEqual(res.payload["error"]["code"], exp_code, f"Cold code mismatch for {label}")
            for label, payload in (
                ("tuple_val", {"request_id": 20, "x": (1, 2)}),
                ("non_str_key", {"request_id": 21, "x": {1: "a"}}),
                ("nan_float", {"request_id": 22, "x": float("nan")}),
            ):
                res = cold_mgr.execute("/api/v1/solve", payload)
                self.assertEqual(res.status_code, 400, f"Cold direct status mismatch for {label}")
                self.assertEqual(res.payload["error"]["code"], "INVALID_JSON", f"Cold direct code mismatch for {label}")
            self.assertEqual(cold_mgr.spawned_pids, [])
            self.assertIsNone(cold_mgr._active_worker)
            self.assertEqual(cold_mgr._ipc_token_counter, 0)
        finally:
            cold_mgr.shutdown()

        # 2. Warmed manager with IPC-logging worker: rejected requests never reach IPC and never disrupt healthy PID
        with tempfile.TemporaryDirectory() as tmpdir:
            ipc_log_path = Path(tmpdir) / "ipc_requests.jsonl"
            spying_worker_cmd = self._make_fault_worker_script(
                "import argparse, json, os, struct\n"
                "def read_exact(fd, n):\n"
                "  b = bytearray()\n"
                "  while len(b) < n:\n"
                "    c = os.read(fd, n - len(b))\n"
                "    if not c: raise EOFError()\n"
                "    b.extend(c)\n"
                "  return bytes(b)\n"
                "p = argparse.ArgumentParser()\n"
                "p.add_argument('--req-fd', type=int); p.add_argument('--resp-fd', type=int)\n"
                "a, _ = p.parse_known_args()\n"
                "ready = json.dumps({'type':'READY','pid':os.getpid(),'req_ino':os.fstat(a.req_fd).st_ino,'resp_ino':os.fstat(a.resp_fd).st_ino}).encode()\n"
                "os.write(a.resp_fd, struct.pack('>I', len(ready)) + ready)\n"
                f"log_path = {str(ipc_log_path)!r}\n"
                "while True:\n"
                "  try: hdr = read_exact(a.req_fd, 4)\n"
                "  except EOFError: break\n"
                "  n = struct.unpack('>I', hdr)[0]\n"
                "  raw = read_exact(a.req_fd, n)\n"
                "  with open(log_path, 'ab') as fp:\n"
                "    fp.write(raw + b'\\n')\n"
                "  msg = json.loads(raw.decode('utf-8'))\n"
                "  req = msg.get('request', {})\n"
                "  rid = req.get('request_id')\n"
                "  if type(rid) is not int or rid < 1: rid = None\n"
                "  out = json.dumps({'ipc_token': msg['ipc_token'], 'worker_pid': os.getpid(), 'request_id': rid}).encode()\n"
                "  os.write(a.resp_fd, struct.pack('>I', len(out)) + out)\n"
            )
            warm_mgr = bridge.WorkerManager(
                response_deadline_s=2.0,
                worker_reap_timeout_s=0.6,
                custom_worker_cmd=spying_worker_cmd,
            )
            try:
                warm = warm_mgr.execute("/api/v1/solve", {"request_id": 100})
                self.assertEqual(warm.status_code, 200)
                healthy_pid = warm.payload["worker_pid"]
                self.assertEqual(warm_mgr.spawned_pids, [healthy_pid])

                # Run all rejected cases against warmed worker
                for label, payload, raw_b, exp_status, exp_code in rejected_cases:
                    res = warm_mgr.execute("/api/v1/solve", payload, raw_request_bytes=raw_b)
                    self.assertEqual(res.status_code, exp_status, f"Warm status mismatch for {label}")
                    self.assertEqual(res.payload["error"]["code"], exp_code, f"Warm code mismatch for {label}")

                # Equivalent JSON with different key order, whitespace, and same-sign float zeros MUST succeed
                accepted_cases: list[tuple[str, dict[str, Any], bytes]] = [
                    (
                        "key_order",
                        {"request_id": 101, "a": 1, "b": [True, 1.0, None]},
                        b'{"b":[true,1.0,null],"a":1,"request_id":101}',
                    ),
                    (
                        "whitespace",
                        {"request_id": 102, "a": [1, False, 2.5]},
                        b' { "request_id" : 102 , "a" : [ 1 , false , 2.5 ] } ',
                    ),
                    (
                        "same_sign_zeros",
                        {"request_id": 103, "pos": 0.0, "neg": -0.0},
                        b'{"request_id":103,"pos":0.00,"neg":-0.00}',
                    ),
                ]
                for label, payload, raw_b in accepted_cases:
                    res_ok = warm_mgr.execute("/api/v1/solve", payload, raw_request_bytes=raw_b)
                    self.assertEqual(res_ok.status_code, 200, f"Accepted case failed for {label}: {res_ok.payload}")
                    self.assertEqual(res_ok.payload["worker_pid"], healthy_pid)

                # Verify healthy worker was never terminated or respawned
                self.assertFalse(_is_pid_reaped(healthy_pid))
                self.assertEqual(warm_mgr.spawned_pids, [healthy_pid])
                self.assertIsNotNone(warm_mgr._active_worker)
                self.assertEqual(warm_mgr._active_worker.pid, healthy_pid)
                self.assertEqual(warm_mgr._ipc_token_counter, 4)

                # Verify only the 4 valid requests ever reached worker IPC
                logged_lines = ipc_log_path.read_text(encoding="utf-8").splitlines()
                self.assertEqual(len(logged_lines), 4)
                logged_req_ids = [json.loads(line)["request"]["request_id"] for line in logged_lines]
                self.assertEqual(logged_req_ids, [100, 101, 102, 103])
            finally:
                warm_mgr.shutdown()

            self.assertTrue(_is_pid_reaped(healthy_pid))

        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

    def test_r5_f1_supervisor_thread_start_failure_warmed_timeout_launch_abort_and_shutdown(self):
        """V1-A-R5-F1: one-shot Thread.start failure in kill supervisor poisons synchronously, retains PID, closes FDs, blocks duplicate workers, and reaps on bounded shutdown retry."""
        import v1_worker_bridge as bridge

        baseline_pipes = _list_open_pipe_inodes()
        orig_thread_start = threading.Thread.start
        fail_remaining = [0]

        def patched_thread_start(th_self, *args, **kwargs):
            target = getattr(th_self, "_target", None)
            if (
                fail_remaining[0] > 0
                and target is not None
                and getattr(target, "__qualname__", "") == "_ProcKillReapSupervisor._run_kill_loop"
            ):
                fail_remaining[0] -= 1
                raise RuntimeError("can't start new thread")
            return orig_thread_start(th_self, *args, **kwargs)

        sleeping_cmd = self._make_fault_worker_script("import time\ntime.sleep(5)\n")

        with mock.patch.object(threading.Thread, "start", autospec=True, side_effect=patched_thread_start):
            # (a) Warmed-worker timeout under one-shot supervisor Thread.start failure
            mgr_a = bridge.WorkerManager(response_deadline_s=2.0, worker_reap_timeout_s=0.4)
            warm_a = mgr_a.execute("/api/v1/solve", {"request_id": 1})
            self.assertEqual(warm_a.status_code, 200)
            warm_pid_a = warm_a.payload["worker_pid"]
            handle_a = mgr_a._active_worker
            self.assertIsNotNone(handle_a)

            mgr_a.response_deadline_s = 0.15
            fail_remaining[0] = 1
            res_a = mgr_a.execute("/api/v1/solve", {"request_id": 2, "delay_s": 2.0})
            self.assertEqual(res_a.status_code, 503)
            self.assertEqual(res_a.payload["error"]["code"], "WORKER_UNAVAILABLE_POISONED")
            self.assertTrue(mgr_a._worker_poisoned)
            self.assertEqual(mgr_a.quarantined_pids, [warm_pid_a])
            self.assertIsNone(mgr_a._active_worker)
            self.assertIsNone(handle_a.req_w)
            self.assertIsNone(handle_a.resp_r)

            # Subsequent admission sees sticky 503 POISONED and spawns zero duplicate workers
            conc_a = mgr_a.execute("/api/v1/study", {"request_id": 3})
            self.assertEqual(conc_a.status_code, 503)
            self.assertEqual(conc_a.payload["error"]["code"], "WORKER_UNAVAILABLE_POISONED")
            self.assertEqual(mgr_a.spawned_pids, [warm_pid_a])

            # Restored thread startup allows bounded shutdown() retry to reap retained PID cleanly
            t0_shut_a = time.monotonic()
            mgr_a.shutdown()
            self.assertLess(time.monotonic() - t0_shut_a, 1.0)
            self.assertEqual(mgr_a.quarantined_pids, [])
            self.assertTrue(_is_pid_reaped(warm_pid_a))
            self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

            # (b1) Post-PID launch abort (runner raises after registering PID) under one-shot supervisor start failure
            procs_b1: list[subprocess.Popen] = []

            def launch_reg_then_raise(cmd, pass_fds, register_pid=None):
                proc = subprocess.Popen(sleeping_cmd, pass_fds=pass_fds, close_fds=True)
                procs_b1.append(proc)
                if register_pid is not None:
                    register_pid(proc)
                raise RuntimeError("simulated launch failure after PID creation")

            mgr_b1 = bridge.WorkerManager(
                response_deadline_s=1.0,
                worker_reap_timeout_s=0.4,
                launch_fn=launch_reg_then_raise,
            )
            fail_remaining[0] = 1
            res_b1 = mgr_b1.execute("/api/v1/solve", {"request_id": 10})
            self.assertEqual(res_b1.status_code, 503)
            self.assertEqual(res_b1.payload["error"]["code"], "WORKER_UNAVAILABLE_POISONED")
            self.assertTrue(mgr_b1._worker_poisoned)
            self.assertEqual(len(procs_b1), 1)
            self.assertEqual(mgr_b1.quarantined_pids, [procs_b1[0].pid])
            expected_cancel_pipes = dict(baseline_pipes)
            assert mgr_b1._cancel_r is not None and mgr_b1._cancel_w is not None
            expected_cancel_pipes[mgr_b1._cancel_r] = os.fstat(mgr_b1._cancel_r).st_ino
            expected_cancel_pipes[mgr_b1._cancel_w] = os.fstat(mgr_b1._cancel_w).st_ino
            self.assertEqual(_list_open_pipe_inodes(), expected_cancel_pipes)

            conc_b1 = mgr_b1.execute("/api/v1/solve", {"request_id": 11})
            self.assertEqual(conc_b1.status_code, 503)
            self.assertEqual(conc_b1.payload["error"]["code"], "WORKER_UNAVAILABLE_POISONED")
            self.assertEqual(mgr_b1.spawned_pids, [procs_b1[0].pid])

            mgr_b1.shutdown()
            self.assertEqual(mgr_b1.quarantined_pids, [])
            self.assertTrue(_is_pid_reaped(procs_b1[0].pid))
            self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

            # (b2) Post-PID launch timeout stall (runner still blocked past deadline) under one-shot start failure
            procs_b2: list[subprocess.Popen] = []
            launch_rel_b2 = threading.Event()
            pid_reg_b2 = threading.Event()
            slot_b2_box: list[Any] = []
            orig_parent_fds_b2: list[tuple[int, int]] = []
            orig_child_fds_b2: list[tuple[int, int]] = []
            orig_child_inos_b2: list[tuple[int, int]] = []

            def capture_slot_b2(slot):
                slot_b2_box.append(slot)
                p0, p1 = slot.parent_fds
                c0, c1 = slot.child_fds
                assert p0 is not None and p1 is not None and c0 is not None and c1 is not None
                orig_parent_fds_b2.append((p0, p1))
                orig_child_fds_b2.append((c0, c1))
                orig_child_inos_b2.append((os.fstat(c0).st_ino, os.fstat(c1).st_ino))

            def launch_reg_then_stall(cmd, pass_fds, register_pid=None):
                proc = subprocess.Popen(sleeping_cmd, pass_fds=pass_fds, close_fds=True)
                procs_b2.append(proc)
                if register_pid is not None:
                    register_pid(proc)
                pid_reg_b2.set()
                launch_rel_b2.wait(timeout=3.0)
                return proc

            mgr_b2 = bridge.WorkerManager(
                response_deadline_s=0.15,
                worker_reap_timeout_s=0.25,
                launch_fn=launch_reg_then_stall,
                on_after_slot_publish_before_runner=capture_slot_b2,
            )
            fail_remaining[0] = 1
            t0_b2 = time.monotonic()
            res_b2 = mgr_b2.execute("/api/v1/solve", {"request_id": 20})
            elapsed_b2 = time.monotonic() - t0_b2
            self.assertTrue(pid_reg_b2.is_set())
            self.assertLess(elapsed_b2, 1.0)
            self.assertEqual(res_b2.status_code, 503)
            self.assertEqual(res_b2.payload["error"]["code"], "WORKER_UNAVAILABLE_POISONED")
            self.assertTrue(mgr_b2._worker_poisoned)
            self.assertEqual(mgr_b2.quarantined_pids, [procs_b2[0].pid])
            self.assertEqual(mgr_b2.spawned_pids, [procs_b2[0].pid])

            # V1-A-R6-M1: BEFORE releasing launcher or invoking shutdown(), parent pipes MUST be closed immediately
            # while launcher-owned child_fds remain safely untouched until runner returns.
            slot_b2 = slot_b2_box[0]
            orig_req_w, orig_resp_r = orig_parent_fds_b2[0]
            orig_req_r, orig_resp_w = orig_child_fds_b2[0]
            orig_req_r_ino, orig_resp_w_ino = orig_child_inos_b2[0]
            self.assertEqual(slot_b2.parent_fds, (None, None))
            self.assertFalse(bridge._is_fd_open(orig_req_w))
            self.assertFalse(bridge._is_fd_open(orig_resp_r))
            open_pipes_mid = _list_open_pipe_inodes()
            self.assertNotIn(orig_req_w, open_pipes_mid)
            self.assertNotIn(orig_resp_r, open_pipes_mid)
            expected_mid_pipes = dict(baseline_pipes)
            assert mgr_b2._cancel_r is not None and mgr_b2._cancel_w is not None
            expected_mid_pipes[mgr_b2._cancel_r] = os.fstat(mgr_b2._cancel_r).st_ino
            expected_mid_pipes[mgr_b2._cancel_w] = os.fstat(mgr_b2._cancel_w).st_ino
            expected_mid_pipes[orig_req_r] = orig_req_r_ino
            expected_mid_pipes[orig_resp_w] = orig_resp_w_ino
            self.assertEqual(open_pipes_mid, expected_mid_pipes)
            self.assertEqual(slot_b2.child_fds, (orig_req_r, orig_resp_w))
            self.assertTrue(bridge._is_fd_open(orig_req_r))
            self.assertTrue(bridge._is_fd_open(orig_resp_w))

            conc_b2 = mgr_b2.execute("/api/v1/solve", {"request_id": 21})
            self.assertEqual(conc_b2.status_code, 503)
            self.assertEqual(conc_b2.payload["error"]["code"], "WORKER_UNAVAILABLE_POISONED")
            self.assertEqual(mgr_b2.spawned_pids, [procs_b2[0].pid])

            # Overlapping shutdown() with repeated Thread.start failure while runner still blocked remains bounded and retains PID
            fail_remaining[0] = 1
            t0_shut_b2 = time.monotonic()
            mgr_b2.shutdown()
            self.assertLess(time.monotonic() - t0_shut_b2, 0.8)
            self.assertEqual(mgr_b2.quarantined_pids, [procs_b2[0].pid])

            launch_rel_b2.set()
            mgr_b2.shutdown()
            self.assertEqual(mgr_b2.quarantined_pids, [])
            self.assertTrue(_is_pid_reaped(procs_b2[0].pid))
            self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

            # (c) Shutdown under one-shot supervisor Thread.start failure
            mgr_c = bridge.WorkerManager(response_deadline_s=2.0, worker_reap_timeout_s=0.4)
            warm_c = mgr_c.execute("/api/v1/solve", {"request_id": 30})
            self.assertEqual(warm_c.status_code, 200)
            warm_pid_c = warm_c.payload["worker_pid"]
            handle_c = mgr_c._active_worker
            self.assertIsNotNone(handle_c)

            fail_remaining[0] = 1
            t0_shut_c = time.monotonic()
            mgr_c.shutdown()
            self.assertLess(time.monotonic() - t0_shut_c, 0.8)
            self.assertTrue(mgr_c._worker_poisoned)
            self.assertEqual(mgr_c.quarantined_pids, [warm_pid_c])
            self.assertIsNone(handle_c.req_w)
            self.assertIsNone(handle_c.resp_r)

            conc_c = mgr_c.execute("/api/v1/solve", {"request_id": 31})
            self.assertEqual(conc_c.status_code, 503)
            self.assertEqual(conc_c.payload["error"]["code"], "WORKER_UNAVAILABLE_POISONED")
            self.assertEqual(mgr_c.spawned_pids, [warm_pid_c])

            # Second shutdown after thread creation recovers kills and reaps retained worker cleanly
            mgr_c.shutdown()
            self.assertEqual(mgr_c.quarantined_pids, [])
            self.assertTrue(_is_pid_reaped(warm_pid_c))
            self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

    def test_r5_m1_immutable_raw_snapshot_subclass_rejection_and_removed_fast_path(self):
        """V1-A-R5-M1: single immutable snapshot prevents bytearray mutation TOCTOU, rejects bytes/bytearray subclasses, removes unchecked private fast path, and isolates cold/warmed managers."""
        import v1_worker_bridge as bridge

        baseline_pipes = _list_open_pipe_inodes()

        # Verify unchecked _ValidatedRawRequest fast path is completely eliminated
        self.assertFalse(hasattr(bridge, "_ValidatedRawRequest"))

        class SwappingByteArray(bytearray):
            def __init__(self, first: bytes, second: bytes) -> None:
                super().__init__(first)
                self._first = first
                self._second = second
                self._calls = 0

            def __bytes__(self) -> bytes:
                self._calls += 1
                return self._first if self._calls == 1 else self._second

        class SwappingBytes(bytes):
            def __new__(cls, first: bytes):
                return super().__new__(cls, first)

        rejected_raw_inputs: list[tuple[str, dict[str, Any], Any, str]] = [
            (
                "swapping_bytearray_mismatched_second",
                {"request_id": 1},
                SwappingByteArray(b'{"request_id":1}', b'{"request_id":2}'),
                "INVALID_JSON",
            ),
            (
                "swapping_bytearray_duplicate_second",
                {"request_id": 1, "a": 1},
                SwappingByteArray(b'{"request_id":1,"a":1}', b'{"request_id":1,"a":1,"a":2}'),
                "INVALID_JSON",
            ),
            (
                "swapping_bytearray_invalid_second",
                {"request_id": 1, "a": 1},
                SwappingByteArray(b'{"request_id":1,"a":1}', b'{"request_id":1,"a":NaN}'),
                "INVALID_JSON",
            ),
            (
                "bytes_subclass",
                {"request_id": 1},
                SwappingBytes(b'{"request_id":1}'),
                "INVALID_JSON",
            ),
            (
                "memoryview_rejected",
                {"request_id": 1},
                memoryview(b'{"request_id":1}'),
                "INVALID_JSON",
            ),
        ]

        # 1. Cold manager: all subclass/mutable-bypass inputs rejected pre-admission with zero worker spawns
        cold_mgr = bridge.WorkerManager(response_deadline_s=2.0, worker_reap_timeout_s=0.6)
        try:
            for label, payload, raw_val, exp_code in rejected_raw_inputs:
                res = cold_mgr.execute("/api/v1/solve", payload, raw_request_bytes=raw_val)
                self.assertEqual(res.status_code, 400, f"Cold status mismatch for {label}")
                self.assertEqual(res.payload["error"]["code"], exp_code, f"Cold code mismatch for {label}")
            with self.assertRaises(TypeError):
                cold_mgr.execute("/api/v1/solve", {"request_id": 1}, _validated_raw=object())  # type: ignore[call-arg]
            self.assertEqual(cold_mgr.spawned_pids, [])
            self.assertIsNone(cold_mgr._active_worker)
            self.assertEqual(cold_mgr._ipc_token_counter, 0)
        finally:
            cold_mgr.shutdown()

        # 2. Warmed IPC-logging manager: zero rejected requests reach IPC, plain bytearray snapshotted once safely
        with tempfile.TemporaryDirectory() as tmpdir:
            ipc_log_path = Path(tmpdir) / "ipc_r5_m1.jsonl"
            spying_worker_cmd = self._make_fault_worker_script(
                "import argparse, json, os, struct\n"
                "def read_exact(fd, n):\n"
                "  b = bytearray()\n"
                "  while len(b) < n:\n"
                "    c = os.read(fd, n - len(b))\n"
                "    if not c: raise EOFError()\n"
                "    b.extend(c)\n"
                "  return bytes(b)\n"
                "p = argparse.ArgumentParser()\n"
                "p.add_argument('--req-fd', type=int); p.add_argument('--resp-fd', type=int)\n"
                "a, _ = p.parse_known_args()\n"
                "ready = json.dumps({'type':'READY','pid':os.getpid(),'req_ino':os.fstat(a.req_fd).st_ino,'resp_ino':os.fstat(a.resp_fd).st_ino}).encode()\n"
                "os.write(a.resp_fd, struct.pack('>I', len(ready)) + ready)\n"
                f"log_path = {str(ipc_log_path)!r}\n"
                "while True:\n"
                "  try: hdr = read_exact(a.req_fd, 4)\n"
                "  except EOFError: break\n"
                "  n = struct.unpack('>I', hdr)[0]\n"
                "  raw = read_exact(a.req_fd, n)\n"
                "  with open(log_path, 'ab') as fp:\n"
                "    fp.write(raw + b'\\n')\n"
                "  msg = json.loads(raw.decode('utf-8'))\n"
                "  req = msg.get('request', {})\n"
                "  out = json.dumps({'ipc_token': msg['ipc_token'], 'worker_pid': os.getpid(), 'request_id': req.get('request_id')}).encode()\n"
                "  os.write(a.resp_fd, struct.pack('>I', len(out)) + out)\n"
            )
            mutable_ba = bytearray(b'{"request_id":201,"flag":true}')
            mutate_armed = [False]

            def mutate_ba_if_reached(_slot_or_handle=None):
                if mutate_armed[0]:
                    mutable_ba[:] = b'{"request_id":999,"flag":false}'

            warm_mgr = bridge.WorkerManager(
                response_deadline_s=2.0,
                worker_reap_timeout_s=0.6,
                custom_worker_cmd=spying_worker_cmd,
                on_before_selector_register=mutate_ba_if_reached,
            )
            try:
                warm = warm_mgr.execute("/api/v1/solve", {"request_id": 200})
                self.assertEqual(warm.status_code, 200)
                healthy_pid = warm.payload["worker_pid"]

                for label, payload, raw_val, exp_code in rejected_raw_inputs:
                    res = warm_mgr.execute("/api/v1/solve", payload, raw_request_bytes=raw_val)
                    self.assertEqual(res.status_code, 400, f"Warm status mismatch for {label}")
                    self.assertEqual(res.payload["error"]["code"], exp_code, f"Warm code mismatch for {label}")

                # Plain bytearray is snapshotted once before admission; later mutation cannot alter sent IPC frame
                mutate_armed[0] = True
                res_ba = warm_mgr.execute("/api/v1/solve", {"request_id": 201, "flag": True}, raw_request_bytes=mutable_ba)
                self.assertEqual(res_ba.status_code, 200)
                self.assertEqual(res_ba.payload["request_id"], 201)
                self.assertEqual(res_ba.payload["worker_pid"], healthy_pid)

                self.assertFalse(_is_pid_reaped(healthy_pid))
                self.assertEqual(warm_mgr.spawned_pids, [healthy_pid])
                self.assertEqual(warm_mgr._ipc_token_counter, 2)

                logged = [json.loads(line) for line in ipc_log_path.read_text(encoding="utf-8").splitlines()]
                self.assertEqual(len(logged), 2)
                self.assertEqual(logged[1]["request"], {"request_id": 201, "flag": True})
            finally:
                warm_mgr.shutdown()

            self.assertTrue(_is_pid_reaped(healthy_pid))

        self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

    def test_r6_f1_thread_constructor_failures_across_supervisor_launcher_and_decode(self):
        """V1-A-R6-F1: Thread constructor failures (MemoryError/RuntimeError) across kill supervisor, launch runner, and decode runner are transactional, never detach live PIDs/FDs or leak slots, and allow bounded recovery/reap."""
        import v1_worker_bridge as bridge

        baseline_pipes = _list_open_pipe_inodes()
        orig_thread_cls = threading.Thread
        ctor_fail_qualname: list[str | None] = [None]
        ctor_fail_remaining = [0]

        def fault_thread_ctor(*args, **kwargs):
            target = kwargs.get("target")
            if target is None and len(args) >= 2:
                target = args[1]
            qual = getattr(target, "__qualname__", "") if target is not None else ""
            if (
                ctor_fail_remaining[0] > 0
                and ctor_fail_qualname[0] is not None
                and ctor_fail_qualname[0] in qual
            ):
                ctor_fail_remaining[0] -= 1
                raise MemoryError(f"simulated Thread.__init__ failure for {qual}")
            return orig_thread_cls(*args, **kwargs)

        with mock.patch("v1_worker_bridge.threading.Thread", side_effect=fault_thread_ctor):
            # (a) Kill supervisor thread constructor failure on warmed-worker timeout + repeated shutdown failure
            mgr_a = bridge.WorkerManager(response_deadline_s=2.0, worker_reap_timeout_s=0.4)
            warm_a = mgr_a.execute("/api/v1/solve", {"request_id": 1})
            self.assertEqual(warm_a.status_code, 200)
            warm_pid_a = warm_a.payload["worker_pid"]
            handle_a = mgr_a._active_worker
            self.assertIsNotNone(handle_a)
            sup_a = handle_a.supervisor
            self.assertIsNotNone(sup_a)

            mgr_a.response_deadline_s = 0.15
            ctor_fail_qualname[0] = "_ProcKillReapSupervisor._run_kill_loop"
            ctor_fail_remaining[0] = 1
            res_a = mgr_a.execute("/api/v1/solve", {"request_id": 2, "delay_s": 2.0})
            self.assertEqual(res_a.status_code, 503)
            self.assertEqual(res_a.payload["error"]["code"], "WORKER_UNAVAILABLE_POISONED")
            self.assertTrue(mgr_a._worker_poisoned)
            self.assertEqual(mgr_a.quarantined_pids, [warm_pid_a])
            self.assertIsNone(mgr_a._active_worker)
            self.assertIsNone(mgr_a._pending_handle)
            self.assertIsNone(handle_a.req_w)
            self.assertIsNone(handle_a.resp_r)
            # No phantom in-flight kill owner left behind
            assert sup_a is not None
            self.assertFalse(sup_a.kill_started)
            self.assertFalse(sup_a.kill_completed)
            self.assertIsNone(sup_a._worker_thread)

            # Subsequent admission sees sticky poison and spawns zero duplicate workers
            conc_a = mgr_a.execute("/api/v1/study", {"request_id": 3})
            self.assertEqual(conc_a.status_code, 503)
            self.assertEqual(conc_a.payload["error"]["code"], "WORKER_UNAVAILABLE_POISONED")
            self.assertEqual(mgr_a.spawned_pids, [warm_pid_a])

            # Even if shutdown hits another supervisor constructor fault, it stays bounded and retains PID; next shutdown reaps cleanly
            ctor_fail_remaining[0] = 1
            t0_s1 = time.monotonic()
            mgr_a.shutdown()
            self.assertLess(time.monotonic() - t0_s1, 0.8)
            self.assertEqual(mgr_a.quarantined_pids, [warm_pid_a])

            mgr_a.shutdown()
            self.assertEqual(mgr_a.quarantined_pids, [])
            self.assertTrue(_is_pid_reaped(warm_pid_a))
            self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

            # (b) Launch runner thread constructor failure after slot publication rolls back slot & closes all 4 launch pipes
            mgr_b = bridge.WorkerManager(response_deadline_s=2.0, worker_reap_timeout_s=0.4)
            try:
                ctor_fail_qualname[0] = "_launch_runner"
                ctor_fail_remaining[0] = 1
                res_b = mgr_b.execute("/api/v1/solve", {"request_id": 10})
                self.assertEqual(res_b.status_code, 503)
                self.assertEqual(res_b.payload["error"]["code"], "WORKER_STARTUP_FAILED")
                self.assertIsNone(mgr_b._active_launch)
                self.assertEqual(mgr_b.spawned_pids, [])

                # Only mgr_b's own cancel pipe remains open (all 4 launch pipes were closed immediately)
                expected_b_pipes = dict(baseline_pipes)
                assert mgr_b._cancel_r is not None and mgr_b._cancel_w is not None
                expected_b_pipes[mgr_b._cancel_r] = os.fstat(mgr_b._cancel_r).st_ino
                expected_b_pipes[mgr_b._cancel_w] = os.fstat(mgr_b._cancel_w).st_ino
                self.assertEqual(_list_open_pipe_inodes(), expected_b_pipes)

                # Subsequent request recovers cleanly with a healthy worker
                res_b2 = mgr_b.execute("/api/v1/solve", {"request_id": 11})
                self.assertEqual(res_b2.status_code, 200)
                self.assertEqual(len(mgr_b.spawned_pids), 1)
                pid_b = res_b2.payload["worker_pid"]
            finally:
                mgr_b.shutdown()
            self.assertTrue(_is_pid_reaped(pid_b))
            self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

            # (c1) Decode runner thread constructor failure on large (>64 KiB) worker response enters structured teardown
            large_resp_cmd = self._make_fault_worker_script(
                "import argparse, json, os, struct\n"
                "def read_exact(fd, n):\n"
                "  b = bytearray()\n"
                "  while len(b) < n:\n"
                "    c = os.read(fd, n - len(b))\n"
                "    if not c: raise EOFError()\n"
                "    b.extend(c)\n"
                "  return bytes(b)\n"
                "p = argparse.ArgumentParser()\n"
                "p.add_argument('--req-fd', type=int); p.add_argument('--resp-fd', type=int)\n"
                "a, _ = p.parse_known_args()\n"
                "ready = json.dumps({'type':'READY','pid':os.getpid(),'req_ino':os.fstat(a.req_fd).st_ino,'resp_ino':os.fstat(a.resp_fd).st_ino}).encode()\n"
                "os.write(a.resp_fd, struct.pack('>I', len(ready)) + ready)\n"
                "blob = 'x' * 70000\n"
                "while True:\n"
                "  try: hdr = read_exact(a.req_fd, 4)\n"
                "  except EOFError: break\n"
                "  n = struct.unpack('>I', hdr)[0]\n"
                "  msg = json.loads(read_exact(a.req_fd, n).decode('utf-8'))\n"
                "  out = json.dumps({'ipc_token': msg['ipc_token'], 'worker_pid': os.getpid(), 'blob': blob}).encode()\n"
                "  mv = memoryview(struct.pack('>I', len(out)) + out)\n"
                "  sent = 0\n"
                "  while sent < len(mv): sent += os.write(a.resp_fd, mv[sent:])\n"
            )
            mgr_c1 = bridge.WorkerManager(
                response_deadline_s=2.0,
                worker_reap_timeout_s=0.5,
                custom_worker_cmd=large_resp_cmd,
            )
            try:
                ok_c1 = mgr_c1.execute("/api/v1/solve", {"request_id": 20})
                self.assertEqual(ok_c1.status_code, 200)
                pid_c1_first = ok_c1.payload["worker_pid"]

                ctor_fail_qualname[0] = "_decode_and_verify_before.<locals>._runner"
                ctor_fail_remaining[0] = 1
                err_c1 = mgr_c1.execute("/api/v1/solve", {"request_id": 21})
                self.assertEqual(err_c1.status_code, 500)
                self.assertEqual(err_c1.payload["error"]["code"], "IPC_PROTOCOL_ERROR")
                self.assertEqual(mgr_c1._active_decode_threads, set())
                self.assertEqual(mgr_c1._active_decode_cancels, set())
                self.assertIsNone(mgr_c1._active_worker)
                self.assertTrue(_is_pid_reaped(pid_c1_first))

                # Fresh worker spawns cleanly on subsequent healthy request
                ok_c1_next = mgr_c1.execute("/api/v1/solve", {"request_id": 22})
                self.assertEqual(ok_c1_next.status_code, 200)
                pid_c1_second = ok_c1_next.payload["worker_pid"]
                self.assertNotEqual(pid_c1_first, pid_c1_second)
            finally:
                mgr_c1.shutdown()
            self.assertTrue(_is_pid_reaped(pid_c1_second))
            self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

            # (c2) Decode runner thread constructor failure during READY handshake tears down child & FDs cleanly
            mgr_c2 = bridge.WorkerManager(
                response_deadline_s=2.0,
                worker_reap_timeout_s=0.5,
                on_decode_transform=lambda obj: obj,
            )
            try:
                ctor_fail_qualname[0] = "_decode_and_verify_before.<locals>._runner"
                ctor_fail_remaining[0] = 1
                err_c2 = mgr_c2.execute("/api/v1/solve", {"request_id": 30})
                self.assertEqual(err_c2.status_code, 503)
                self.assertEqual(err_c2.payload["error"]["code"], "WORKER_STARTUP_FAILED")
                self.assertEqual(mgr_c2._active_decode_threads, set())
                self.assertEqual(mgr_c2._active_decode_cancels, set())
                self.assertEqual(len(mgr_c2.spawned_pids), 1)
                self.assertTrue(_is_pid_reaped(mgr_c2.spawned_pids[0]))
                self.assertIsNone(mgr_c2._pending_handle)
                self.assertIsNone(mgr_c2._active_worker)
            finally:
                mgr_c2.shutdown()
            self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

    def test_r7_f1_exceptional_teardown_preserves_active_io_lease(self):
        """V1-A-R7-F1: exceptional teardown (e.g. callback-registration MemoryError) poisons/quarantines first, preserves active_io lease drain within the same deadline, never closes FDs while active_io > 0, prevents sentinel FD hijack, and reaps cleanly after lease release."""
        import v1_worker_bridge as bridge

        baseline_pipes = _list_open_pipe_inodes()
        orig_os_write = os.write
        orig_register_cb = bridge._ProcKillReapSupervisor.register_close_callback

        # (a) Paused leased writer held past shutdown deadline while register_close_callback fails
        mgr = bridge.WorkerManager(response_deadline_s=2.0, worker_reap_timeout_s=0.18)
        warm = mgr.execute("/api/v1/solve", {"request_id": 1})
        self.assertEqual(warm.status_code, 200)
        warm_pid = warm.payload["worker_pid"]
        handle = mgr._active_worker
        self.assertIsNotNone(handle)
        assert handle is not None
        orig_req_w = handle.req_w
        orig_resp_r = handle.resp_r
        self.assertIsNotNone(orig_req_w)
        self.assertIsNotNone(orig_resp_r)
        assert orig_req_w is not None and orig_resp_r is not None

        writer_in_lease = threading.Event()
        release_writer = threading.Event()
        arm_writer_pause = [True]
        fail_reg_cb = [0]

        def paused_os_write(fd, data):
            if arm_writer_pause[0] and fd == orig_req_w:
                arm_writer_pause[0] = False
                writer_in_lease.set()
                release_writer.wait(timeout=3.0)
            return orig_os_write(fd, data)

        def failing_register_cb(sup_self, cb):
            if fail_reg_cb[0] > 0:
                fail_reg_cb[0] -= 1
                raise MemoryError("simulated register_close_callback allocation failure")
            return orig_register_cb(sup_self, cb)

        req_box: list[Any] = []
        with mock.patch("v1_worker_bridge.os.write", side_effect=paused_os_write), mock.patch.object(
            bridge._ProcKillReapSupervisor,
            "register_close_callback",
            autospec=True,
            side_effect=failing_register_cb,
        ):
            th_req = threading.Thread(
                target=lambda: req_box.append(mgr.execute("/api/v1/solve", {"request_id": 2}))
            )
            th_req.start()
            self.assertTrue(writer_in_lease.wait(timeout=2.0))
            self.assertEqual(handle.active_io, 1)

            fail_reg_cb[0] = 1
            t0_shut = time.monotonic()
            mgr.shutdown()
            shut_elapsed = time.monotonic() - t0_shut

            # Bounded by the single worker_reap_timeout_s deadline (~0.18s), no extra interval allocated
            self.assertLess(shut_elapsed, 0.70)
            self.assertTrue(mgr._worker_poisoned)
            self.assertEqual(mgr.quarantined_pids, [warm_pid])
            self.assertEqual(len(mgr.spawned_pids), 1)
            self.assertIsNone(mgr._active_worker)

            # Descriptors MUST NOT be closed while active_io > 0
            self.assertEqual(handle.active_io, 1)
            self.assertEqual(handle.req_w, orig_req_w)
            self.assertEqual(handle.resp_r, orig_resp_r)
            self.assertTrue(bridge._is_fd_open(orig_req_w))
            self.assertTrue(bridge._is_fd_open(orig_resp_r))

            # Forced numeric FD reuse attempt (sentinel pipe) cannot claim orig_req_w / orig_resp_r
            sr, sw = os.pipe()
            try:
                os.write(sw, b"sentinel")
                self.assertNotIn(sr, (orig_req_w, orig_resp_r))
                self.assertNotIn(sw, (orig_req_w, orig_resp_r))

                # Resume paused writer while sentinel pipe is live: writer writes strictly to original pipe, never sentinel
                release_writer.set()
                th_req.join(timeout=2.0)
                self.assertFalse(th_req.is_alive())
                self.assertEqual(os.read(sr, 8), b"sentinel")
            finally:
                os.close(sr)
                os.close(sw)

            self.assertEqual(len(req_box), 1)
            self.assertEqual(req_box[0].status_code, 503)

            # Subsequent admission sees sticky poison and spawns zero duplicate workers
            conc = mgr.execute("/api/v1/study", {"request_id": 3})
            self.assertEqual(conc.status_code, 503)
            self.assertEqual(conc.payload["error"]["code"], "WORKER_UNAVAILABLE_POISONED")
            self.assertEqual(mgr.spawned_pids, [warm_pid])

            # After lease released (active_io == 0), subsequent shutdown kills, reaps, and restores FD baseline
            self.assertEqual(handle.active_io, 0)
            mgr.shutdown()
            self.assertEqual(mgr.quarantined_pids, [])
            self.assertTrue(_is_pid_reaped(warm_pid))
            self.assertIsNone(handle.req_w)
            self.assertIsNone(handle.resp_r)
            self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)

        # (b) Exceptional teardown where active_io drains within the SAME deadline closes FDs safely after drain,
        # retains PID & sticky poison, and next shutdown reaps cleanly
        mgr_b = bridge.WorkerManager(response_deadline_s=2.0, worker_reap_timeout_s=0.40)
        warm_b = mgr_b.execute("/api/v1/solve", {"request_id": 10})
        self.assertEqual(warm_b.status_code, 200)
        warm_pid_b = warm_b.payload["worker_pid"]
        handle_b = mgr_b._active_worker
        self.assertIsNotNone(handle_b)
        assert handle_b is not None
        orig_req_w_b = handle_b.req_w
        assert orig_req_w_b is not None

        writer_in_lease_b = threading.Event()
        release_writer_b = threading.Event()
        arm_pause_b = [True]
        fail_reg_cb_b = [0]

        def paused_os_write_b(fd, data):
            if arm_pause_b[0] and fd == orig_req_w_b:
                arm_pause_b[0] = False
                writer_in_lease_b.set()
                release_writer_b.wait(timeout=3.0)
            return orig_os_write(fd, data)

        def failing_register_cb_b(sup_self, cb):
            if fail_reg_cb_b[0] > 0:
                fail_reg_cb_b[0] -= 1
                raise MemoryError("simulated register_close_callback allocation failure b")
            return orig_register_cb(sup_self, cb)

        req_box_b: list[Any] = []
        with mock.patch("v1_worker_bridge.os.write", side_effect=paused_os_write_b), mock.patch.object(
            bridge._ProcKillReapSupervisor,
            "register_close_callback",
            autospec=True,
            side_effect=failing_register_cb_b,
        ):
            th_req_b = threading.Thread(
                target=lambda: req_box_b.append(mgr_b.execute("/api/v1/solve", {"request_id": 11}))
            )
            th_req_b.start()
            self.assertTrue(writer_in_lease_b.wait(timeout=2.0))

            # Release the paused writer 0.08s after shutdown enters exceptional drain (well before 0.40s deadline)
            def delayed_release_b():
                time.sleep(0.08)
                release_writer_b.set()

            rel_th_b = threading.Thread(target=delayed_release_b, daemon=True)
            rel_th_b.start()

            fail_reg_cb_b[0] = 2
            t0_shut_b = time.monotonic()
            mgr_b.shutdown()
            shut_elapsed_b = time.monotonic() - t0_shut_b
            th_req_b.join(timeout=2.0)
            rel_th_b.join(timeout=1.0)

            self.assertLess(shut_elapsed_b, 0.70)
            self.assertEqual(handle_b.active_io, 0)
            self.assertTrue(mgr_b._worker_poisoned)
            self.assertEqual(mgr_b.quarantined_pids, [warm_pid_b])
            self.assertIsNone(handle_b.req_w)
            self.assertIsNone(handle_b.resp_r)

            mgr_b.shutdown()
            self.assertEqual(mgr_b.quarantined_pids, [])
            self.assertTrue(_is_pid_reaped(warm_pid_b))
            self.assertEqual(_list_open_pipe_inodes(), baseline_pipes)


if __name__ == "__main__":
    unittest.main()
