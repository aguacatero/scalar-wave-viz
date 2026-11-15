"""Executable V1-A POSIX worker bridge, nonblocking framed IPC, and HTTP security/admission layer.

Supported OS scope: POSIX platforms (Linux, macOS / Darwin) supporting anonymous
`os.pipe()` descriptors passed explicitly via `subprocess.Popen(..., pass_fds=..., close_fds=True)`,
`os.set_blocking(fd, False)`, and `selectors.DefaultSelector` on pipe FDs.
Windows is explicitly unsupported (Windows `selectors` does not support pipe FDs and
`close_fds=True` with `pass_fds` is POSIX-only).

Latency budget separation (`V1-SPEC-R5-I1`):
- Admitted compute, IPC, startup, and teardown budget: `response_deadline_s` (5.0 s)
  + `worker_reap_timeout_s` (2.0 s) = <= 7.0 s worst case for admitted requests.
- HTTP request header + body read (`total_read_deadline_s` = 2.0 s) and HTTP
  response write (`response_write_timeout_s` = 2.0 s) are bounded separately.

Zero V1-B solver adapters or P2 modules may be imported here.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import http.server
import inspect
import io
import json
import math
import os
from pathlib import Path
import platform
import selectors
import socket
import stat
import struct
import subprocess
import sys
import threading
import time
from typing import Any, Callable


SUPPORTED_OS_NAMES = ("posix",)
SUPPORTED_SYSTEMS = ("Linux", "Darwin")
SUPPORTED_LOOPBACK_HOSTS = ("127.0.0.1", "localhost")

MAX_HTTP_BODY_BYTES = 8192
MAX_IPC_REQUEST_BYTES = 16384
MAX_IPC_RESPONSE_BYTES = 8388608

DEFAULT_TOTAL_READ_DEADLINE_S = 2.0
DEFAULT_RESPONSE_WRITE_TIMEOUT_S = 2.0
DEFAULT_RESPONSE_DEADLINE_S = 5.0
DEFAULT_WORKER_REAP_TIMEOUT_S = 2.0
DEFAULT_MAX_ACTIVE_HTTP_WORKERS = 8
DEFAULT_MAX_CONCURRENT_COMPUTES = 1

MAX_SAFE_REQUEST_ID = 9007199254740991


class DuplicateKeyError(ValueError):
    """Raised when a JSON object contains duplicate keys."""


class HttpReadTimeoutError(Exception):
    """Raised when HTTP header+body reading exceeds `total_read_deadline_s`."""


class HttpRequestError(Exception):
    """Structured HTTP validation error with status code and canonical error code."""

    def __init__(self, status_code: int, code: str, message: str, field: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.field = field


class _IpcTimeoutError(TimeoutError):
    """Raised when IPC startup/write/read exceeds the monotonic deadline."""


class _IpcEofError(EOFError):
    """Raised when the worker pipe hits unexpected EOF or broken pipe."""


class _IpcProtocolError(ValueError):
    """Raised on malformed frame lengths, UTF-8/JSON errors, or token mismatch."""


class _WorkerCancelledError(Exception):
    """Raised when manager shutdown cancels an in-flight selector wait."""


def ensure_supported_platform() -> None:
    """Verify the host OS supports POSIX pipe selectors and explicit `pass_fds` transfer."""
    sys_name = platform.system()
    if os.name not in SUPPORTED_OS_NAMES or sys_name not in SUPPORTED_SYSTEMS:
        raise RuntimeError(
            f"Unsupported platform ({os.name}/{sys_name}): V1 worker bridge requires POSIX "
            f"({', '.join(SUPPORTED_SYSTEMS)}); Windows selector-on-pipe is unsupported."
        )


def validate_loopback_host(host: str) -> str:
    """Allow strictly IPv4 loopback names (`127.0.0.1`, `localhost`)."""
    if host not in SUPPORTED_LOOPBACK_HOSTS:
        raise ValueError(
            f"Refusing non-loopback or IPv6 host {host!r}; allowed hosts are {SUPPORTED_LOOPBACK_HOSTS}"
        )
    return host


def _no_duplicates_object_pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, val in pairs:
        if key in obj:
            raise DuplicateKeyError(f"Duplicate JSON key: {key!r}")
        obj[key] = val
    return obj


def _reject_non_finite_constant(token: str) -> Any:
    raise ValueError(f"Non-finite JSON constant is not allowed: {token!r}")


def strict_json_loads(raw_bytes: bytes) -> dict[str, Any]:
    """Decode UTF-8 JSON object rejecting duplicate keys and non-finite constants."""
    text = raw_bytes.decode("utf-8")
    parsed = json.loads(
        text,
        object_pairs_hook=_no_duplicates_object_pairs_hook,
        parse_constant=_reject_non_finite_constant,
    )
    if not isinstance(parsed, dict):
        raise ValueError("JSON request payload must be an object")
    return parsed


def strict_json_dumps(payload: Any) -> bytes:
    """Serialize strictly compliant RFC 8259 UTF-8 JSON bytes (`allow_nan=False`)."""
    return json.dumps(payload, allow_nan=False, separators=(",", ":")).encode("utf-8")


def extract_safe_request_id(payload: Any) -> int | None:
    """Extract JSON safe integer `request_id` in `[1, 9007199254740991]` or `None`."""
    if not isinstance(payload, dict):
        return None
    req_id = payload.get("request_id")
    if isinstance(req_id, bool) or not isinstance(req_id, int):
        return None
    if 1 <= req_id <= MAX_SAFE_REQUEST_ID:
        return req_id
    return None


def make_error_payload(
    code: str,
    message: str,
    *,
    field: str | None = None,
    request_id: int | None = None,
) -> dict[str, Any]:
    """Build canonical structured V1 JSON error response envelope."""
    return {
        "error": {
            "code": code,
            "message": message,
            "field": field,
        },
        "request_id": request_id,
    }


def _safe_close_fd(fd: int | None) -> None:
    if fd is None:
        return
    try:
        os.close(fd)
    except OSError:
        pass


def _is_fd_open(fd: int) -> bool:
    try:
        os.fstat(fd)
        return True
    except OSError:
        return False


def _pack_frame(payload_bytes: bytes, max_bytes: int) -> bytes:
    if len(payload_bytes) == 0 or len(payload_bytes) > max_bytes:
        raise _IpcProtocolError(f"Frame length {len(payload_bytes)} outside [1, {max_bytes}]")
    return struct.pack(">I", len(payload_bytes)) + payload_bytes


@dataclass
class BridgeResult:
    """HTTP-ready result returned by `WorkerManager.execute`."""

    status_code: int
    payload: dict[str, Any]


class _WorkerHandle:
    """Owns one spawned worker process and its parent-side pipe descriptors."""

    def __init__(
        self,
        proc: subprocess.Popen[bytes],
        req_w: int,
        resp_r: int,
        expected_req_ino: int,
        expected_resp_ino: int,
        parent_closed_unused_ends: bool,
    ) -> None:
        self.lock = threading.Lock()
        self.proc: subprocess.Popen[bytes] | None = proc
        self.pid: int = proc.pid
        self.req_w: int | None = req_w
        self.resp_r: int | None = resp_r
        self.expected_req_ino = expected_req_ino
        self.expected_resp_ino = expected_resp_ino
        self.parent_closed_unused_ends = parent_closed_unused_ends
        self.reaped: bool = False

    def close_fds(self) -> None:
        """Close parent pipe FDs at most once."""
        with self.lock:
            rw = self.req_w
            rr = self.resp_r
            self.req_w = None
            self.resp_r = None
        _safe_close_fd(rw)
        _safe_close_fd(rr)


class _LaunchSlot:
    """Synchronizes bounded asynchronous child launch and late-child ownership."""

    def __init__(self, child_fds: tuple[int, int], parent_fds: tuple[int, int]) -> None:
        self.lock = threading.Lock()
        self.done_event = threading.Event()
        self.abandoned: bool = False
        self.child_fds: tuple[int | None, int | None] = child_fds
        self.parent_fds: tuple[int | None, int | None] = parent_fds
        self.proc: subprocess.Popen[bytes] | None = None
        self.error: BaseException | None = None
        self.thread: threading.Thread | None = None

    def close_child_fds(self) -> None:
        with self.lock:
            c0, c1 = self.child_fds
            self.child_fds = (None, None)
        _safe_close_fd(c0)
        _safe_close_fd(c1)

    def close_parent_fds(self) -> None:
        with self.lock:
            p0, p1 = self.parent_fds
            self.parent_fds = (None, None)
        _safe_close_fd(p0)
        _safe_close_fd(p1)


class WorkerManager:
    """Fail-closed single-worker POSIX process supervisor with bounded nonblocking IPC."""

    def __init__(
        self,
        *,
        response_deadline_s: float = DEFAULT_RESPONSE_DEADLINE_S,
        worker_reap_timeout_s: float = DEFAULT_WORKER_REAP_TIMEOUT_S,
        custom_worker_cmd: list[str] | None = None,
        launch_fn: Callable[..., subprocess.Popen[bytes]] | None = None,
        kill_fn: Callable[[subprocess.Popen[bytes]], None] | None = None,
    ) -> None:
        ensure_supported_platform()
        if response_deadline_s <= 0 or worker_reap_timeout_s <= 0:
            raise ValueError("Worker deadlines must be strictly positive")

        self.response_deadline_s = float(response_deadline_s)
        self.worker_reap_timeout_s = float(worker_reap_timeout_s)
        self.custom_worker_cmd = custom_worker_cmd
        self._launch_fn = launch_fn
        self._kill_fn = kill_fn

        self._admission_lock = threading.Lock()
        self._worker_poisoned: bool = False
        self._poison_reason: str | None = None
        self._shutting_down: bool = False
        self._compute_in_progress: bool = False
        self._ipc_token_counter: int = 0

        self._active_worker: _WorkerHandle | None = None
        self._active_launch: _LaunchSlot | None = None
        self.spawned_pids: list[int] = []

        # Nonblocking self-pipe wakes active selectors immediately on shutdown()
        self._cancel_r: int | None
        self._cancel_w: int | None
        cr, cw = os.pipe()
        os.set_blocking(cr, False)
        os.set_blocking(cw, False)
        self._cancel_r = cr
        self._cancel_w = cw
        self._shutdown_done = False

    def _wake_cancel_pipe(self) -> None:
        cw = self._cancel_w
        if cw is None:
            return
        try:
            os.write(cw, b"x")
        except OSError:
            pass

    def _next_ipc_token(self) -> int:
        with self._admission_lock:
            self._ipc_token_counter += 1
            return self._ipc_token_counter

    def _poison(self, reason: str) -> None:
        with self._admission_lock:
            self._worker_poisoned = True
            self._poison_reason = reason

    def _kill_and_reap_proc(self, proc: subprocess.Popen[bytes], close_cb: Callable[[], None]) -> bool:
        """Kill child, join within `worker_reap_timeout_s`, close pipes, verify reaped."""
        kill_failed = False
        try:
            if proc.poll() is None:
                if self._kill_fn is not None:
                    self._kill_fn(proc)
                else:
                    proc.kill()
        except OSError:
            kill_failed = True
        except Exception:
            kill_failed = True
        finally:
            close_cb()

        if kill_failed and proc.poll() is None:
            return False

        try:
            proc.wait(timeout=self.worker_reap_timeout_s)
        except subprocess.TimeoutExpired:
            return False
        except OSError:
            return False

        return proc.poll() is not None and proc.returncode is not None

    def _terminate_and_verify_handle(self, handle: _WorkerHandle) -> bool:
        """Teardown an active `_WorkerHandle`; return True iff verified dead & reaped."""
        with self._admission_lock:
            if self._active_worker is handle:
                self._active_worker = None
        if handle.proc is None:
            handle.close_fds()
            return True
        reaped = self._kill_and_reap_proc(handle.proc, handle.close_fds)
        handle.reaped = reaped
        if not reaped:
            self._poison("WORKER_TEARDOWN_UNVERIFIED")
        return reaped

    def _invoke_launcher(
        self,
        cmd: list[str],
        req_r: int,
        resp_w: int,
        slot: _LaunchSlot,
    ) -> subprocess.Popen[bytes]:
        def register_pid(proc: subprocess.Popen[bytes]) -> None:
            with slot.lock:
                slot.proc = proc
            with self._admission_lock:
                if proc.pid not in self.spawned_pids:
                    self.spawned_pids.append(proc.pid)

        if self._launch_fn is None:
            proc = subprocess.Popen(
                cmd,
                pass_fds=(req_r, resp_w),
                close_fds=True,
                stdin=subprocess.DEVNULL,
            )
            register_pid(proc)
            return proc

        sig = inspect.signature(self._launch_fn)
        if "register_pid" in sig.parameters:
            proc = self._launch_fn(cmd, (req_r, resp_w), register_pid=register_pid)
        else:
            proc = self._launch_fn(cmd, (req_r, resp_w))
        if proc is not None:
            register_pid(proc)
        return proc

    def _build_worker_command(self, req_r: int, resp_w: int) -> list[str]:
        if self.custom_worker_cmd is not None:
            return [*self.custom_worker_cmd, "--req-fd", str(req_r), "--resp-fd", str(resp_w)]
        return [
            sys.executable,
            "-m",
            "v1_worker_bridge",
            "--worker",
            "--req-fd",
            str(req_r),
            "--resp-fd",
            str(resp_w),
        ]

    def _spawn_and_handshake(self, deadline: float, req_id: int | None) -> _WorkerHandle | BridgeResult:
        """Launch one fresh child process + dedicated pipes and verify READY handshake."""
        req_r, req_w = os.pipe()
        resp_r, resp_w = os.pipe()
        os.set_blocking(req_w, False)
        os.set_blocking(resp_r, False)
        expected_req_ino = os.fstat(req_r).st_ino
        expected_resp_ino = os.fstat(resp_w).st_ino

        cmd = self._build_worker_command(req_r, resp_w)
        slot = _LaunchSlot((req_r, resp_w), (req_w, resp_r))
        with self._admission_lock:
            self._active_launch = slot

        def _launch_runner() -> None:
            late_proc: subprocess.Popen[bytes] | None = None
            try:
                with slot.lock:
                    if slot.abandoned:
                        return
                proc = self._invoke_launcher(cmd, req_r, resp_w, slot)
                with slot.lock:
                    if slot.abandoned:
                        late_proc = proc
            except BaseException as exc:  # noqa: BLE001 - captured fail-closed for supervisor
                with slot.lock:
                    slot.error = exc
            finally:
                # Parent MUST close child pipe ends immediately after fork/exec or failure
                # so parent observes true EOF on child exit and broken pipe on send.
                slot.close_child_fds()
                if late_proc is not None:
                    self._kill_and_reap_proc(late_proc, slot.close_parent_fds)
                slot.done_event.set()

        th = threading.Thread(target=_launch_runner, daemon=True)
        slot.thread = th
        th.start()

        remaining = max(0.0, deadline - time.monotonic())
        finished = slot.done_event.wait(timeout=remaining)

        if not finished:
            with slot.lock:
                slot.abandoned = True
                early_proc = slot.proc
            # Launch itself stalled past deadline: launch thread status is uncertain -> poison fail closed.
            self._poison("WORKER_STARTUP_LAUNCH_TIMEOUT")
            if early_proc is not None:
                self._kill_and_reap_proc(early_proc, slot.close_parent_fds)
            return BridgeResult(
                503,
                make_error_payload(
                    "WORKER_UNAVAILABLE_POISONED",
                    "Worker launch stalled past deadline; bridge poisoned fail closed.",
                    request_id=req_id,
                ),
            )

        with slot.lock:
            launch_err = slot.error
            proc = slot.proc

        with self._admission_lock:
            if self._active_launch is slot:
                self._active_launch = None
            shutting_down = self._shutting_down

        if launch_err is not None or proc is None:
            if proc is not None:
                if not self._kill_and_reap_proc(proc, slot.close_parent_fds):
                    self._poison("WORKER_LAUNCH_CLEANUP_UNVERIFIED")
            else:
                slot.close_parent_fds()
            return BridgeResult(
                503,
                make_error_payload(
                    "WORKER_STARTUP_FAILED",
                    f"Worker failed to start: {launch_err}",
                    request_id=req_id,
                ),
            )

        parent_closed_unused = (not _is_fd_open(req_r)) and (not _is_fd_open(resp_w))
        handle = _WorkerHandle(
            proc=proc,
            req_w=req_w,
            resp_r=resp_r,
            expected_req_ino=expected_req_ino,
            expected_resp_ino=expected_resp_ino,
            parent_closed_unused_ends=parent_closed_unused,
        )

        if shutting_down:
            self._terminate_and_verify_handle(handle)
            return BridgeResult(
                503,
                make_error_payload("SERVER_SHUTTING_DOWN", "Bridge shutting down.", request_id=req_id),
            )

        # Wait for worker READY handshake within the SAME monotonic deadline
        try:
            ready_bytes = self._recv_frame_before(resp_r, deadline, max_bytes=MAX_IPC_REQUEST_BYTES)
            ready = strict_json_loads(ready_bytes)
            if (
                ready.get("type") != "READY"
                or ready.get("pid") != proc.pid
                or ready.get("req_ino") != expected_req_ino
                or ready.get("resp_ino") != expected_resp_ino
            ):
                raise _IpcProtocolError(
                    "READY handshake failed descriptor identity verification"
                )
        except _IpcTimeoutError:
            if not self._terminate_and_verify_handle(handle):
                return BridgeResult(
                    503,
                    make_error_payload(
                        "WORKER_UNAVAILABLE_POISONED",
                        "Worker handshake timed out and teardown could not be verified.",
                        request_id=req_id,
                    ),
                )
            return BridgeResult(
                504,
                make_error_payload(
                    "SOLVE_DEADLINE_EXCEEDED",
                    "Worker handshake exceeded admitted startup/IPC deadline.",
                    request_id=req_id,
                ),
            )
        except _WorkerCancelledError:
            self._terminate_and_verify_handle(handle)
            return BridgeResult(
                503,
                make_error_payload("SERVER_SHUTTING_DOWN", "Bridge shutting down.", request_id=req_id),
            )
        except (_IpcEofError, _IpcProtocolError, ValueError, UnicodeDecodeError) as exc:
            if not self._terminate_and_verify_handle(handle):
                return BridgeResult(
                    503,
                    make_error_payload(
                        "WORKER_UNAVAILABLE_POISONED",
                        "Worker startup handshake failed and teardown could not be verified.",
                        request_id=req_id,
                    ),
                )
            return BridgeResult(
                503,
                make_error_payload(
                    "WORKER_STARTUP_FAILED",
                    f"Worker startup handshake failed: {exc}",
                    request_id=req_id,
                ),
            )

        with self._admission_lock:
            if self._shutting_down or self._worker_poisoned:
                poisoned = self._worker_poisoned
                self._terminate_and_verify_handle(handle)
                code = "WORKER_UNAVAILABLE_POISONED" if poisoned else "SERVER_SHUTTING_DOWN"
                return BridgeResult(503, make_error_payload(code, "Bridge unavailable.", request_id=req_id))
            self._active_worker = handle
        return handle

    def _select_ready(self, fd: int, events: int, deadline: float) -> None:
        cancel_r = self._cancel_r
        with selectors.DefaultSelector() as sel:
            sel.register(fd, events, data="io")
            if cancel_r is not None:
                sel.register(cancel_r, selectors.EVENT_READ, data="cancel")
            remaining = deadline - time.monotonic()
            if remaining <= 0.0:
                raise _IpcTimeoutError("Admitted compute/IPC deadline exceeded")
            ready = sel.select(timeout=remaining)
            if not ready:
                raise _IpcTimeoutError("Admitted compute/IPC deadline exceeded")
            for key, _ in ready:
                if key.data == "cancel":
                    raise _WorkerCancelledError("Cancelled by bridge shutdown")

    def _send_frame_before(self, req_w: int, frame: bytes, deadline: float) -> None:
        mv = memoryview(frame)
        sent = 0
        while sent < len(frame):
            if time.monotonic() >= deadline:
                raise _IpcTimeoutError("Blocked request write exceeded deadline")
            self._select_ready(req_w, selectors.EVENT_WRITE, deadline)
            try:
                n = os.write(req_w, mv[sent:])
                if n == 0:
                    raise _IpcEofError("Worker request pipe closed during write")
                sent += n
            except BlockingIOError:
                continue
            except (BrokenPipeError, ConnectionResetError) as exc:
                raise _IpcEofError("Worker pipe broken during write") from exc
            except OSError as exc:
                raise _IpcEofError(f"Worker pipe write OS error: {exc}") from exc

    def _recv_exact_before(self, resp_r: int, n_bytes: int, deadline: float) -> bytes:
        buf = bytearray()
        while len(buf) < n_bytes:
            if time.monotonic() >= deadline:
                raise _IpcTimeoutError("Response read exceeded deadline")
            self._select_ready(resp_r, selectors.EVENT_READ, deadline)
            try:
                chunk = os.read(resp_r, n_bytes - len(buf))
            except BlockingIOError:
                continue
            except (BrokenPipeError, ConnectionResetError) as exc:
                raise _IpcEofError("Worker pipe broken during read") from exc
            except OSError as exc:
                raise _IpcEofError(f"Worker pipe read OS error: {exc}") from exc
            if chunk == b"":
                raise _IpcEofError("Unexpected EOF from worker process")
            buf.extend(chunk)
        return bytes(buf)

    def _recv_frame_before(self, resp_r: int, deadline: float, *, max_bytes: int) -> bytes:
        hdr = self._recv_exact_before(resp_r, 4, deadline)
        (frame_len,) = struct.unpack(">I", hdr)
        if frame_len == 0 or frame_len > max_bytes:
            raise _IpcProtocolError(f"Invalid IPC response frame length {frame_len} (max={max_bytes})")
        return self._recv_exact_before(resp_r, frame_len, deadline)

    def execute(self, endpoint: str, request_payload: dict[str, Any]) -> BridgeResult:
        """Admit, supervise, and execute one bounded IPC request against the single worker."""
        req_id = extract_safe_request_id(request_payload)

        with self._admission_lock:
            if self._shutting_down:
                return BridgeResult(
                    503,
                    make_error_payload("SERVER_SHUTTING_DOWN", "Bridge is shutting down.", request_id=req_id),
                )
            if self._worker_poisoned:
                return BridgeResult(
                    503,
                    make_error_payload(
                        "WORKER_UNAVAILABLE_POISONED",
                        "Worker bridge is poisoned fail closed until process restart.",
                        request_id=req_id,
                    ),
                )
            if self._compute_in_progress:
                return BridgeResult(
                    429,
                    make_error_payload(
                        "TOO_MANY_REQUESTS",
                        "Single compute slot is busy; retry later.",
                        request_id=req_id,
                    ),
                )
            self._compute_in_progress = True

        try:
            deadline = time.monotonic() + self.response_deadline_s
            with self._admission_lock:
                handle = self._active_worker

            if handle is None:
                spawned = self._spawn_and_handshake(deadline, req_id)
                if isinstance(spawned, BridgeResult):
                    return spawned
                handle = spawned

            ipc_token = self._next_ipc_token()
            ipc_request = {
                "ipc_token": ipc_token,
                "endpoint": endpoint,
                "request": request_payload,
                "expected_req_ino": handle.expected_req_ino,
                "expected_resp_ino": handle.expected_resp_ino,
                "parent_closed_unused_ends": handle.parent_closed_unused_ends,
            }
            frame = _pack_frame(strict_json_dumps(ipc_request), MAX_IPC_REQUEST_BYTES)

            if handle.req_w is None or handle.resp_r is None:
                raise _IpcEofError("Worker pipe descriptor closed")

            self._send_frame_before(handle.req_w, frame, deadline)
            raw_resp = self._recv_frame_before(handle.resp_r, deadline, max_bytes=MAX_IPC_RESPONSE_BYTES)
            resp_obj = strict_json_loads(raw_resp)
            if resp_obj.get("ipc_token") != ipc_token:
                raise _IpcProtocolError(
                    f"IPC token mismatch: expected {ipc_token}, got {resp_obj.get('ipc_token')!r}"
                )
            return BridgeResult(200, resp_obj)

        except _IpcTimeoutError:
            assert handle is not None
            if not self._terminate_and_verify_handle(handle):
                return BridgeResult(
                    503,
                    make_error_payload(
                        "WORKER_UNAVAILABLE_POISONED",
                        "Worker timed out and kill/reap verification failed; bridge poisoned.",
                        request_id=req_id,
                    ),
                )
            return BridgeResult(
                504,
                make_error_payload(
                    "SOLVE_DEADLINE_EXCEEDED",
                    "Admitted compute/IPC/startup deadline exceeded; worker cleanly killed and reaped.",
                    request_id=req_id,
                ),
            )
        except _WorkerCancelledError:
            if handle is not None:
                self._terminate_and_verify_handle(handle)
            return BridgeResult(
                503,
                make_error_payload("SERVER_SHUTTING_DOWN", "Bridge shutting down.", request_id=req_id),
            )
        except _IpcEofError as exc:
            if handle is not None and not self._terminate_and_verify_handle(handle):
                return BridgeResult(
                    503,
                    make_error_payload(
                        "WORKER_UNAVAILABLE_POISONED",
                        "Worker crashed and teardown could not be verified.",
                        request_id=req_id,
                    ),
                )
            return BridgeResult(
                500,
                make_error_payload("WORKER_CRASHED", str(exc), request_id=req_id),
            )
        except (_IpcProtocolError, ValueError, UnicodeDecodeError) as exc:
            if handle is not None and not self._terminate_and_verify_handle(handle):
                return BridgeResult(
                    503,
                    make_error_payload(
                        "WORKER_UNAVAILABLE_POISONED",
                        "Worker IPC protocol error and teardown could not be verified.",
                        request_id=req_id,
                    ),
                )
            return BridgeResult(
                500,
                make_error_payload("IPC_PROTOCOL_ERROR", str(exc), request_id=req_id),
            )
        finally:
            with self._admission_lock:
                # Keep slot withheld if poisoned; release only when healthy/cleanly reaped
                if not self._worker_poisoned:
                    self._compute_in_progress = False

    def shutdown(self) -> None:
        """Synchronized shutdown: block new spawns/requests, kill+reap active child, close FDs."""
        with self._admission_lock:
            self._shutting_down = True
            handle = self._active_worker
            self._active_worker = None
            launch_slot = self._active_launch
            self._active_launch = None
            cancel_r = self._cancel_r
            cancel_w = self._cancel_w

        self._wake_cancel_pipe()

        if handle is not None:
            self._terminate_and_verify_handle(handle)

        if launch_slot is not None:
            with launch_slot.lock:
                launch_slot.abandoned = True
                early_proc = launch_slot.proc
                th = launch_slot.thread
            if early_proc is not None:
                self._kill_and_reap_proc(early_proc, launch_slot.close_parent_fds)
            if th is not None and th.is_alive():
                th.join(timeout=self.worker_reap_timeout_s)
                if th.is_alive():
                    self._poison("SHUTDOWN_LAUNCH_THREAD_STILL_ALIVE")

        with self._admission_lock:
            if not self._shutdown_done:
                self._shutdown_done = True
                cr, cw = self._cancel_r, self._cancel_w
                self._cancel_r = None
                self._cancel_w = None
                _safe_close_fd(cr)
                _safe_close_fd(cw)


class _DeadlineSocketRawIO(io.RawIOBase):
    """Socket reader enforcing one wall-clock deadline across HTTP headers and body."""

    def __init__(self, sock: socket.socket, deadline: float) -> None:
        super().__init__()
        self._sock = sock
        self._deadline = deadline

    def readable(self) -> bool:
        return True

    def readinto(self, buffer: bytearray | memoryview) -> int:  # type: ignore[override]
        mv = memoryview(buffer)
        with selectors.DefaultSelector() as sel:
            sel.register(self._sock, selectors.EVENT_READ)
            while True:
                remaining = self._deadline - time.monotonic()
                if remaining <= 0.0:
                    raise HttpReadTimeoutError("HTTP request read deadline exceeded")
                events = sel.select(timeout=remaining)
                if not events:
                    raise HttpReadTimeoutError("HTTP request read deadline exceeded")
                try:
                    n = self._sock.recv_into(mv)
                    return n
                except BlockingIOError:
                    continue
                except (TimeoutError, socket.timeout) as exc:
                    raise HttpReadTimeoutError("HTTP socket recv timed out") from exc


class ExplorerHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Serves V0-V0.2 static assets plus hardened V1-A `POST /api/v1/*` JSON endpoints."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["directory"] = str(self.server_directory) if hasattr(self, "server_directory") else kwargs.get("directory")
        super().__init__(*args, **kwargs)

    def setup(self) -> None:
        self.request.settimeout(self.server.total_read_deadline_s)  # type: ignore[attr-defined]
        super().setup()

    def handle_one_request(self) -> None:
        self._read_deadline = time.monotonic() + self.server.total_read_deadline_s  # type: ignore[attr-defined]
        self.rfile = io.BufferedReader(_DeadlineSocketRawIO(self.connection, self._read_deadline), buffer_size=8192)
        try:
            super().handle_one_request()
        except HttpReadTimeoutError:
            self.close_connection = True
            self._send_json_response(
                408,
                make_error_payload("REQUEST_READ_TIMEOUT", "HTTP request header/body read deadline exceeded."),
            )

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        if sys.stderr.isatty():
            sys.stderr.write(f"[Propulsion Explorer] {self.address_string()} - {format % args}\n")

    def _send_json_response(self, status_code: int, payload: dict[str, Any]) -> None:
        body = strict_json_dumps(payload)
        try:
            self.connection.settimeout(self.server.response_write_timeout_s)  # type: ignore[attr-defined]
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)
            self.wfile.flush()
        except (OSError, TimeoutError):
            pass

    def _validate_host_and_origin(self) -> None:
        bound_host, bound_port = self.server.bound_loopback_host, self.server.server_port  # type: ignore[attr-defined]
        allowed_hosts = {f"{bound_host}:{bound_port}", f"localhost:{bound_port}"} if bound_host == "127.0.0.1" else {f"localhost:{bound_port}"}
        host_vals = self.headers.get_all("Host") or []
        if len(host_vals) != 1 or host_vals[0].strip() not in allowed_hosts:
            raise HttpRequestError(403, "FORBIDDEN_HOST", "Invalid or missing Host header", field="Host")

        allowed_origins = {f"http://127.0.0.1:{bound_port}", f"http://localhost:{bound_port}"}
        origin_vals = self.headers.get_all("Origin") or []
        if len(origin_vals) != 1 or origin_vals[0].strip() not in allowed_origins:
            raise HttpRequestError(403, "FORBIDDEN_ORIGIN", "Invalid or missing same-origin Origin header", field="Origin")

    def _validate_framing_and_read_json(self) -> dict[str, Any]:
        if self.headers.get_all("Transfer-Encoding"):
            raise HttpRequestError(501, "UNSUPPORTED_TRANSFER_ENCODING", "Transfer-Encoding is not supported")

        ct_raw = self.headers.get("Content-Type") or ""
        media_type = ct_raw.split(";", 1)[0].strip().lower()
        if media_type != "application/json":
            raise HttpRequestError(415, "UNSUPPORTED_MEDIA_TYPE", "Content-Type must be application/json", field="Content-Type")

        cl_vals = self.headers.get_all("Content-Length") or []
        if len(cl_vals) == 0:
            raise HttpRequestError(411, "CONTENT_LENGTH_REQUIRED", "Content-Length header is required", field="Content-Length")
        if len(cl_vals) > 1:
            raise HttpRequestError(400, "INVALID_CONTENT_LENGTH", "Duplicate Content-Length header", field="Content-Length")
        cl_str = cl_vals[0].strip()
        if not cl_str.isdigit():
            raise HttpRequestError(400, "INVALID_CONTENT_LENGTH", "Content-Length must be a non-negative integer", field="Content-Length")
        content_length = int(cl_str)
        if content_length > MAX_HTTP_BODY_BYTES:
            raise HttpRequestError(413, "PAYLOAD_TOO_LARGE", f"Body length {content_length} exceeds {MAX_HTTP_BODY_BYTES} bytes", field="Content-Length")

        body_bytes = self.rfile.read(content_length)
        if len(body_bytes) != content_length:
            raise HttpRequestError(400, "INCOMPLETE_BODY", "Client disconnected before sending full Content-Length")

        try:
            return strict_json_loads(body_bytes)
        except DuplicateKeyError as exc:
            raise HttpRequestError(400, "DUPLICATE_KEY", str(exc)) from exc
        except (ValueError, UnicodeDecodeError) as exc:
            raise HttpRequestError(400, "INVALID_JSON", f"Malformed or non-finite JSON payload: {exc}") from exc

    def do_POST(self) -> None:  # noqa: N802 - http.server method name
        self.close_connection = True
        if self.path not in ("/api/v1/solve", "/api/v1/study"):
            self._send_json_response(404, make_error_payload("NOT_FOUND", f"Unknown API endpoint: {self.path}"))
            return

        try:
            self._validate_host_and_origin()
            payload = self._validate_framing_and_read_json()
        except HttpReadTimeoutError:
            self._send_json_response(
                408,
                make_error_payload("REQUEST_READ_TIMEOUT", "HTTP request header/body read deadline exceeded."),
            )
            return
        except HttpRequestError as exc:
            self._send_json_response(exc.status_code, make_error_payload(exc.code, exc.message, field=exc.field))
            return

        result = self.server.worker_manager.execute(self.path, payload)  # type: ignore[attr-defined]
        self._send_json_response(result.status_code, result.payload)


class ReusableV1ThreadingHTTPServer(http.server.ThreadingHTTPServer):
    """IPv4 loopback ThreadingHTTPServer with pre-thread semaphore & fail-closed worker shutdown."""

    address_family = socket.AF_INET
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        server_address: tuple[str, int],
        handler_class: type[http.server.BaseHTTPRequestHandler],
        *,
        worker_manager: WorkerManager,
        total_read_deadline_s: float = DEFAULT_TOTAL_READ_DEADLINE_S,
        response_write_timeout_s: float = DEFAULT_RESPONSE_WRITE_TIMEOUT_S,
        max_active_http_workers: int = DEFAULT_MAX_ACTIVE_HTTP_WORKERS,
    ) -> None:
        self.bound_loopback_host = server_address[0]
        self.worker_manager = worker_manager
        self.total_read_deadline_s = float(total_read_deadline_s)
        self.response_write_timeout_s = float(response_write_timeout_s)
        self.max_active_http_workers = int(max_active_http_workers)
        self._http_semaphore = threading.BoundedSemaphore(self.max_active_http_workers)
        super().__init__(server_address, handler_class)

    def _reject_http_saturated(self, request: socket.socket) -> None:
        body = strict_json_dumps(
            make_error_payload("HTTP_ADMISSION_SATURATED", "Too many concurrent HTTP requests; retry shortly.")
        )
        resp = (
            b"HTTP/1.1 503 Service Unavailable\r\n"
            b"Content-Type: application/json; charset=utf-8\r\n"
            + f"Content-Length: {len(body)}\r\nConnection: close\r\n\r\n".encode("ascii")
            + body
        )
        try:
            request.settimeout(0.25)
            request.sendall(resp)
        except OSError:
            pass
        finally:
            self.shutdown_request(request)

    def process_request(self, request: socket.socket, client_address: tuple[str, int]) -> None:
        if not self._http_semaphore.acquire(blocking=False):
            self._reject_http_saturated(request)
            return
        t = threading.Thread(target=self._process_request_guarded, args=(request, client_address))
        t.daemon = self.daemon_threads
        try:
            t.start()
        except Exception:
            self._http_semaphore.release()
            self.shutdown_request(request)
            raise

    def _process_request_guarded(self, request: socket.socket, client_address: tuple[str, int]) -> None:
        try:
            self.process_request_thread(request, client_address)
        finally:
            self._http_semaphore.release()

    def shutdown(self) -> None:
        try:
            self.worker_manager.shutdown()
        finally:
            super().shutdown()

    def server_close(self) -> None:
        try:
            self.worker_manager.shutdown()
        finally:
            super().server_close()


def _find_available_loopback_port(host: str, start_port: int, max_attempts: int = 50) -> int:
    if start_port == 0:
        return 0
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((host, port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"Could not find an available port on {host} between {start_port} and {start_port + max_attempts}")


def create_v1_http_server(
    host: str,
    port: int,
    *,
    directory: Path | str,
    worker_manager: WorkerManager | None = None,
    total_read_deadline_s: float = DEFAULT_TOTAL_READ_DEADLINE_S,
    response_write_timeout_s: float = DEFAULT_RESPONSE_WRITE_TIMEOUT_S,
    response_deadline_s: float = DEFAULT_RESPONSE_DEADLINE_S,
    worker_reap_timeout_s: float = DEFAULT_WORKER_REAP_TIMEOUT_S,
    max_active_http_workers: int = DEFAULT_MAX_ACTIVE_HTTP_WORKERS,
) -> tuple[ReusableV1ThreadingHTTPServer, int]:
    """Create a hardened IPv4-loopback V1-A server bound to `(host, selected_port)`."""
    ensure_supported_platform()
    validated_host = validate_loopback_host(host)
    selected_port = _find_available_loopback_port(validated_host, port)

    owns_manager = worker_manager is None
    mgr = worker_manager or WorkerManager(
        response_deadline_s=response_deadline_s,
        worker_reap_timeout_s=worker_reap_timeout_s,
    )

    dir_str = str(directory)

    class _BoundHandler(ExplorerHTTPRequestHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            kwargs["directory"] = dir_str
            super().__init__(*args, **kwargs)

    try:
        server = ReusableV1ThreadingHTTPServer(
            (validated_host, selected_port),
            _BoundHandler,
            worker_manager=mgr,
            total_read_deadline_s=total_read_deadline_s,
            response_write_timeout_s=response_write_timeout_s,
            max_active_http_workers=max_active_http_workers,
        )
    except Exception:
        if owns_manager:
            mgr.shutdown()
        raise
    return server, server.server_address[1]


def _worker_read_exact(fd: int, n_bytes: int) -> bytes:
    buf = bytearray()
    while len(buf) < n_bytes:
        chunk = os.read(fd, n_bytes - len(buf))
        if chunk == b"":
            raise EOFError("Parent request pipe reached EOF")
        buf.extend(chunk)
    return bytes(buf)


def _worker_write_all(fd: int, data: bytes) -> None:
    mv = memoryview(data)
    sent = 0
    while sent < len(data):
        n = os.write(fd, mv[sent:])
        if n == 0:
            raise BrokenPipeError("Parent response pipe write returned 0")
        sent += n


def _worker_open_nonstd_pipe_inos(req_fd: int, resp_fd: int) -> list[int]:
    """List open FIFO pipe inodes for fd > 2 (excluding stdin/stdout/stderr harness pipes)."""
    inos: list[int] = []
    for fd_dir in ("/proc/self/fd", "/dev/fd"):
        if os.path.isdir(fd_dir):
            for name in os.listdir(fd_dir):
                if not name.isdigit():
                    continue
                fd = int(name)
                if fd <= 2:
                    continue
                try:
                    st = os.fstat(fd)
                except OSError:
                    continue
                if stat.S_ISFIFO(st.st_mode):
                    inos.append(st.st_ino)
            return sorted(inos)
    return sorted([os.fstat(req_fd).st_ino, os.fstat(resp_fd).st_ino])


def _run_worker_loop(req_fd: int, resp_fd: int) -> int:
    """Child process IPC loop for V1-A transport and lifecycle execution."""
    ensure_supported_platform()
    req_stat = os.fstat(req_fd)
    resp_stat = os.fstat(resp_fd)
    if not stat.S_ISFIFO(req_stat.st_mode) or not stat.S_ISFIFO(resp_stat.st_mode):
        raise RuntimeError("Worker descriptors must reference POSIX pipe FIFOs")

    ready_payload = strict_json_dumps(
        {
            "type": "READY",
            "pid": os.getpid(),
            "req_fd": req_fd,
            "resp_fd": resp_fd,
            "req_ino": req_stat.st_ino,
            "resp_ino": resp_stat.st_ino,
        }
    )
    _worker_write_all(resp_fd, _pack_frame(ready_payload, MAX_IPC_REQUEST_BYTES))

    while True:
        try:
            hdr = _worker_read_exact(req_fd, 4)
        except EOFError:
            return 0
        (frame_len,) = struct.unpack(">I", hdr)
        if frame_len == 0 or frame_len > MAX_IPC_REQUEST_BYTES:
            return 2
        msg = strict_json_loads(_worker_read_exact(req_fd, frame_len))
        req_body = msg.get("request") if isinstance(msg.get("request"), dict) else {}

        delay_s = req_body.get("delay_s")
        if isinstance(delay_s, (int, float)) and not isinstance(delay_s, bool) and math.isfinite(delay_s) and 0 < delay_s <= 10.0:
            time.sleep(float(delay_s))

        response_obj = {
            "ipc_token": msg["ipc_token"],
            "status": "V1_A_TRANSPORT_ONLY",
            "scientific_status": "NO_SOLVER_ADAPTER_IN_V1_A",
            "endpoint": msg.get("endpoint"),
            "request_id": extract_safe_request_id(req_body),
            "worker_pid": os.getpid(),
            "child_req_ino": req_stat.st_ino,
            "child_resp_ino": resp_stat.st_ino,
            "expected_req_ino": msg.get("expected_req_ino"),
            "expected_resp_ino": msg.get("expected_resp_ino"),
            "parent_closed_unused_ends": msg.get("parent_closed_unused_ends"),
            "child_open_pipe_inos": _worker_open_nonstd_pipe_inos(req_fd, resp_fd),
        }
        out_frame = _pack_frame(strict_json_dumps(response_obj), MAX_IPC_RESPONSE_BYTES)
        _worker_write_all(resp_fd, out_frame)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="V1-A isolated worker entrypoint.")
    parser.add_argument("--worker", action="store_true", required=True)
    parser.add_argument("--req-fd", type=int, required=True)
    parser.add_argument("--resp-fd", type=int, required=True)
    args = parser.parse_args(argv)
    return _run_worker_loop(args.req_fd, args.resp_fd)


if __name__ == "__main__":
    raise SystemExit(main())
