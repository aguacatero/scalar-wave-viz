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
WORKER_MODULE_PATH = Path(__file__).resolve()

MAX_HTTP_BODY_BYTES = 8192
MAX_IPC_REQUEST_BYTES = 16384
MAX_IPC_RESPONSE_BYTES = 8388608
MAX_CLIENT_JSON_DEPTH = 64
MAX_JSON_DEPTH = MAX_CLIENT_JSON_DEPTH
MAX_IPC_ENVELOPE_DEPTH = MAX_CLIENT_JSON_DEPTH + 4

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
    """Raised when IPC startup/write/read/decode exceeds the monotonic deadline."""


class _IpcEofError(EOFError):
    """Raised when the worker pipe hits unexpected EOF or broken pipe."""


class _IpcProtocolError(ValueError):
    """Raised on malformed frame lengths, UTF-8/JSON errors, or token mismatch."""


class _WorkerCancelledError(Exception):
    """Raised when manager shutdown cancels an in-flight selector or wait."""


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


def _is_exact_int(val: Any) -> bool:
    """Return True strictly for `int` values, excluding `bool` (`True == 1`) and `float` (`1.0 == 1`)."""
    return type(val) is int


def _no_duplicates_object_pairs_hook(
    pairs: list[tuple[str, Any]],
    *,
    tick: Callable[[], None] | None = None,
) -> dict[str, Any]:
    if tick is not None:
        tick()
    obj: dict[str, Any] = {}
    for key, val in pairs:
        if key in obj:
            raise DuplicateKeyError(f"Duplicate JSON key: {key!r}")
        obj[key] = val
    return obj


def _reject_non_finite_constant(token: str) -> Any:
    raise ValueError(f"Non-finite JSON constant is not allowed: {token!r}")


def _strict_parse_float(token: str, *, tick: Callable[[], None] | None = None) -> float:
    if tick is not None:
        tick()
    val = float(token)
    if not math.isfinite(val):
        raise ValueError(f"Overflow or non-finite JSON float literal: {token!r}")
    return val


def _validate_json_depth_and_finiteness(
    value: Any,
    *,
    max_depth: int = MAX_JSON_DEPTH,
    tick: Callable[[], None] | None = None,
) -> None:
    """Iteratively validate strict JSON value types, string keys, nesting depth, UTF-8 encodability, and finite floats."""
    if not isinstance(value, dict):
        raise ValueError("JSON request payload must be a dict object")
    stack: list[tuple[Any, int]] = [(value, 1)]
    while stack:
        if tick is not None:
            tick()
        current, depth = stack.pop()
        if depth > max_depth:
            raise ValueError(f"JSON nesting depth exceeds limit ({max_depth})")
        t = type(current)
        if t is dict:
            for k, v in current.items():
                if type(k) is not str:
                    raise ValueError(f"JSON object key must be strictly a string, got {type(k).__name__}")
                k.encode("utf-8", errors="strict")
                stack.append((v, depth + 1))
        elif t is list:
            for item in current:
                stack.append((item, depth + 1))
        elif t is str:
            current.encode("utf-8", errors="strict")
        elif t is float:
            if not math.isfinite(current):
                raise ValueError("Non-finite float value is not allowed in JSON")
        elif t is int or t is bool or current is None:
            continue
        else:
            raise ValueError(f"Non-JSON container or scalar type is not allowed: {t.__name__}")


def _json_values_strictly_equal(lhs: Any, rhs: Any) -> bool:
    """Compare two pre-validated JSON structures requiring identical Python types at every node.

    Unlike Python's ``==``, this rejects boolean/integer (``True`` vs ``1``, ``False`` vs ``0``),
    boolean/float, and integer/float (``1`` vs ``1.0``) cross-type coercions in both directions.
    Positive and negative floating-point zero (``+0.0`` vs ``-0.0``) are treated as distinct
    representations (requiring matching ``math.copysign`` sign bit) so raw JSON bytes cannot alter
    IEEE-754 signed zero relative to ``request_payload``. Object key ordering and JSON whitespace
    differences are permitted.
    """
    stack: list[tuple[Any, Any]] = [(lhs, rhs)]
    while stack:
        a, b = stack.pop()
        ta = type(a)
        if ta is not type(b):
            return False
        if ta is dict:
            if a.keys() != b.keys():
                return False
            for key, aval in a.items():
                stack.append((aval, b[key]))
        elif ta is list:
            if len(a) != len(b):
                return False
            for aitem, bitem in zip(a, b):
                stack.append((aitem, bitem))
        elif ta is float:
            if not (math.isfinite(a) and math.isfinite(b)):
                return False
            if a != b or math.copysign(1.0, a) != math.copysign(1.0, b):
                return False
        elif ta is str or ta is int or ta is bool or a is None:
            if a != b:
                return False
        else:
            return False
    return True


def strict_json_loads(
    raw_bytes: bytes,
    *,
    max_depth: int = MAX_JSON_DEPTH,
    deadline_check: Callable[[], None] | None = None,
    on_parse_entry: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Decode UTF-8 JSON object rejecting duplicates, overflow/non-finite floats, surrogates, and excessive depth."""
    text = raw_bytes.decode("utf-8")
    if on_parse_entry is not None:
        on_parse_entry()
    tick: Callable[[], None] | None = None
    if deadline_check is not None:
        counter = [0]

        def _tick() -> None:
            counter[0] += 1
            if (counter[0] & 0xFF) == 0:
                deadline_check()

        tick = _tick

    json_kwargs: dict[str, Any] = {
        "object_pairs_hook": (lambda pairs: _no_duplicates_object_pairs_hook(pairs, tick=tick)) if tick else _no_duplicates_object_pairs_hook,
        "parse_constant": _reject_non_finite_constant,
        "parse_float": (lambda tok: _strict_parse_float(tok, tick=tick)) if tick else _strict_parse_float,
    }
    if tick is not None:
        def _parse_int(tok: str) -> int:
            tick()
            return int(tok)

        json_kwargs["parse_int"] = _parse_int

    try:
        parsed = json.loads(text, **json_kwargs)
    except RecursionError as exc:
        raise ValueError("JSON nesting depth exceeds parser recursion limit") from exc
    if not isinstance(parsed, dict):
        raise ValueError("JSON request payload must be an object")
    _validate_json_depth_and_finiteness(parsed, max_depth=max_depth, tick=tick)
    return parsed


def strict_json_dumps(payload: Any) -> bytes:
    """Serialize strictly compliant RFC 8259 UTF-8 JSON bytes (`allow_nan=False`, UTF-8 preserved)."""
    return json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8", errors="strict")


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


class _ProcKillReapSupervisor:
    """Authoritative single-owner kill/reap supervisor per spawned child PID (retained across quarantine)."""

    def __init__(self, proc: subprocess.Popen[bytes], kill_fn: Callable[[subprocess.Popen[bytes]], None] | None) -> None:
        self.proc = proc
        self.pid: int = proc.pid
        self._kill_fn = kill_fn
        self.lock = threading.Lock()
        self.cond = threading.Condition(self.lock)
        self.kill_started: bool = False
        self.kill_completed: bool = False
        self.kill_ok: bool | None = None
        self.reaped: bool = False
        self._retry_requested: bool = False
        self._close_cbs: list[Callable[[], None]] = []
        self._worker_thread: threading.Thread | None = None

    def register_close_callback(self, cb: Callable[[], None] | None) -> None:
        if cb is None:
            return
        with self.lock:
            self._close_cbs.append(cb)

    def _drain_close_callbacks(self) -> None:
        with self.lock:
            cbs = list(self._close_cbs)
            self._close_cbs.clear()
        for cb in cbs:
            try:
                cb()
            except Exception:
                pass

    def _run_kill_loop(self) -> None:
        while True:
            ok = False
            try:
                if self.proc.poll() is None:
                    if self._kill_fn is not None:
                        self._kill_fn(self.proc)
                    else:
                        self.proc.kill()
                ok = True
            except Exception:
                ok = self.proc.poll() is not None
            with self.lock:
                self.kill_ok = ok
                if self.proc.poll() is not None and self.proc.returncode is not None:
                    self.reaped = True
                if not ok and self.proc.poll() is None and self._retry_requested:
                    self._retry_requested = False
                    self.kill_completed = False
                    self.kill_ok = None
                    continue
                self._retry_requested = False
                self.kill_completed = True
                self.cond.notify_all()
                return

    def ensure_kill_started(self, *, request_retry_if_failed: bool = False) -> bool:
        """Transactionally start an authoritative kill thread unless already running or succeeded.

        Returns True if the process is already reaped or a kill thread is running/succeeded;
        returns False (rolling back cleanly without leaving a phantom in-flight owner) if
        thread creation/startup fails.
        """
        with self.lock:
            if self.proc.poll() is not None and self.proc.returncode is not None:
                self.kill_started = True
                self.kill_completed = True
                self.kill_ok = True
                self.reaped = True
                self.cond.notify_all()
                return True
            if self.kill_started and not self.kill_completed:
                if request_retry_if_failed:
                    self._retry_requested = True
                return True
            if self.kill_completed and self.kill_ok:
                return True
            if self.kill_completed and not self.kill_ok and not request_retry_if_failed:
                return False
            try:
                th = threading.Thread(target=self._run_kill_loop, daemon=True)
                self.kill_started = True
                self.kill_completed = False
                self.kill_ok = None
                self._retry_requested = False
                self._worker_thread = th
                th.start()
            except BaseException:
                self.kill_started = False
                self.kill_completed = False
                self.kill_ok = None
                self._retry_requested = False
                self._worker_thread = None
                self.cond.notify_all()
                return False
            return True

    def wait_kill_before(
        self,
        abs_deadline: float,
        clock: Callable[[], float] = time.monotonic,
        *,
        request_retry_if_failed: bool = False,
    ) -> bool | None:
        """Wait up to `abs_deadline` for the authoritative kill attempt to complete; return `None` if still in flight."""
        started = self.ensure_kill_started(request_retry_if_failed=request_retry_if_failed)
        with self.lock:
            if not started:
                return self.kill_ok if self.kill_completed else False
            while not self.kill_completed or self._retry_requested:
                rem = abs_deadline - clock()
                if rem <= 0.0:
                    return None
                self.cond.wait(timeout=rem)
            return self.kill_ok

    def wait_reaped_before(
        self,
        abs_deadline: float,
        close_cb: Callable[[], None] | None = None,
        clock: Callable[[], float] = time.monotonic,
        *,
        request_retry_if_failed: bool = False,
    ) -> bool:
        """Wait for kill completion, close pipes via `close_cb`, and verify child reap before `abs_deadline`."""
        self.register_close_callback(close_cb)
        kill_state = self.wait_kill_before(
            abs_deadline,
            clock=clock,
            request_retry_if_failed=request_retry_if_failed,
        )
        self._drain_close_callbacks()
        if kill_state is None:
            return False
        if not kill_state and self.proc.poll() is None:
            return False

        with self.lock:
            if self.reaped or (self.proc.poll() is not None and self.proc.returncode is not None):
                self.reaped = True
                self.cond.notify_all()
                return True

        wait_s = max(0.0, abs_deadline - clock())
        try:
            self.proc.wait(timeout=wait_s)
        except (subprocess.TimeoutExpired, OSError):
            pass

        is_reaped = self.proc.poll() is not None and self.proc.returncode is not None
        with self.lock:
            if is_reaped:
                self.reaped = True
            self.cond.notify_all()
        return is_reaped


class _WorkerHandle:
    """Owns one spawned worker process, its authoritative kill/reap supervisor, and parent pipe descriptors."""

    def __init__(
        self,
        proc: subprocess.Popen[bytes],
        req_w: int,
        resp_r: int,
        expected_req_ino: int,
        expected_resp_ino: int,
        parent_closed_unused_ends: bool,
        supervisor: _ProcKillReapSupervisor | None = None,
    ) -> None:
        self.lock = threading.Lock()
        self.teardown_exec_lock = threading.Lock()
        self.proc: subprocess.Popen[bytes] | None = proc
        self.pid: int = proc.pid
        self.supervisor: _ProcKillReapSupervisor | None = supervisor
        self.req_w: int | None = req_w
        self.resp_r: int | None = resp_r
        self.expected_req_ino = expected_req_ino
        self.expected_resp_ino = expected_resp_ino
        self.parent_closed_unused_ends = parent_closed_unused_ends
        self.closing: bool = False
        self.active_io: int = 0
        self.reaped: bool = False

    def close_fds(self) -> None:
        """Close parent pipe FDs at most once."""
        with self.lock:
            self.closing = True
            rw = self.req_w
            rr = self.resp_r
            self.req_w = None
            self.resp_r = None
        _safe_close_fd(rw)
        _safe_close_fd(rr)


class _LaunchSlot:
    """Atomic state machine owning transient child launch FDs, PID, and authoritative cleanup state."""

    def __init__(self, child_fds: tuple[int, int], parent_fds: tuple[int, int]) -> None:
        self.lock = threading.Lock()
        self.done_cond = threading.Condition(self.lock)
        self.cleanup_done_cond = threading.Condition(self.lock)
        self.state: str = "PENDING"  # PENDING -> TRANSFERRED | ABORTED
        self.abandoned: bool = False
        self.runner_returned: bool = False
        self.cleanup_started: bool = False
        self.cleanup_done: bool = False
        self.cleanup_verified: bool | None = None
        self.cleanup_deadline: float | None = None
        self.kill_attempt_started: bool = False
        self.kill_attempt_finished: bool = False
        self.kill_start_failed: bool = False
        self.child_req_fd_closed: bool = False
        self.child_resp_fd_closed: bool = False
        self.child_fds: tuple[int | None, int | None] = child_fds
        self.parent_fds: tuple[int | None, int | None] = parent_fds
        self.proc: subprocess.Popen[bytes] | None = None
        self.supervisor: _ProcKillReapSupervisor | None = None
        self.error: BaseException | None = None
        self.thread: threading.Thread | None = None

    def close_child_fds(self) -> None:
        with self.lock:
            c0, c1 = self.child_fds
            self.child_fds = (None, None)
            if c0 is None and c1 is None:
                return
        c0_closed = True
        c1_closed = True
        if c0 is not None:
            try:
                os.close(c0)
            except OSError:
                c0_closed = False
        if c1 is not None:
            try:
                os.close(c1)
            except OSError:
                c1_closed = False
        with self.lock:
            if c0 is not None:
                self.child_req_fd_closed = c0_closed
            if c1 is not None:
                self.child_resp_fd_closed = c1_closed

    def pop_parent_fds(self) -> tuple[int | None, int | None]:
        with self.lock:
            p0, p1 = self.parent_fds
            self.parent_fds = (None, None)
            return p0, p1

    def close_parent_fds(self) -> None:
        p0, p1 = self.pop_parent_fds()
        _safe_close_fd(p0)
        _safe_close_fd(p1)

    def notify(self) -> None:
        with self.lock:
            self.done_cond.notify_all()


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
        clock: Callable[[], float] | None = None,
        on_before_launch_slot_publish: Callable[[], None] | None = None,
        on_after_slot_publish_before_runner: Callable[[_LaunchSlot], None] | None = None,
        on_after_runner_pid_before_done: Callable[[subprocess.Popen[bytes]], None] | None = None,
        on_after_runner_returned_before_cleanup: Callable[[_LaunchSlot], None] | None = None,
        on_before_slot_to_pending_handoff: Callable[[_LaunchSlot], None] | None = None,
        on_before_ready_publish: Callable[[_WorkerHandle], None] | None = None,
        on_before_selector_register: Callable[[_WorkerHandle], None] | None = None,
        on_after_raw_read: Callable[[bytes], None] | None = None,
        on_json_parse_entry: Callable[[], None] | None = None,
        on_decode_transform: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        on_before_cancel_write: Callable[[], None] | None = None,
    ) -> None:
        ensure_supported_platform()
        if response_deadline_s <= 0 or worker_reap_timeout_s <= 0:
            raise ValueError("Worker deadlines must be strictly positive")

        self.response_deadline_s = float(response_deadline_s)
        self.worker_reap_timeout_s = float(worker_reap_timeout_s)
        self.custom_worker_cmd = custom_worker_cmd
        self._launch_fn = launch_fn
        self._kill_fn = kill_fn
        self._clock: Callable[[], float] = clock or time.monotonic
        self._on_before_launch_slot_publish = on_before_launch_slot_publish
        self._on_after_slot_publish_before_runner = on_after_slot_publish_before_runner
        self._on_after_runner_pid_before_done = on_after_runner_pid_before_done
        self._on_after_runner_returned_before_cleanup = on_after_runner_returned_before_cleanup
        self._on_before_slot_to_pending_handoff = on_before_slot_to_pending_handoff
        self._on_before_ready_publish = on_before_ready_publish
        self._on_before_selector_register = on_before_selector_register
        self._on_after_raw_read = on_after_raw_read
        self._on_json_parse_entry = on_json_parse_entry
        self._on_decode_transform = on_decode_transform
        self._on_before_cancel_write = on_before_cancel_write

        self._admission_lock = threading.Lock()
        self._state_cond = threading.Condition(self._admission_lock)
        self._worker_poisoned: bool = False
        self._poison_reason: str | None = None
        self._shutting_down: bool = False
        self._compute_in_progress: bool = False
        self._ipc_token_counter: int = 0
        self._active_selectors: int = 0
        self._active_cancel_writers: int = 0
        self._active_decode_threads: set[threading.Thread] = set()
        self._active_decode_cancels: set[threading.Event] = set()

        self._active_worker: _WorkerHandle | None = None
        self._pending_handle: _WorkerHandle | None = None
        self._quarantined_handles: list[_WorkerHandle] = []
        self._proc_supervisors: dict[int, _ProcKillReapSupervisor] = {}
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
        self._cancel_closed = False

    @property
    def quarantined_pids(self) -> list[int]:
        """Return PIDs currently held in quarantine awaiting verified reap."""
        with self._admission_lock:
            return [h.pid for h in self._quarantined_handles]

    def _wake_cancel_pipe(self) -> None:
        with self._admission_lock:
            if self._cancel_closed or self._cancel_w is None:
                return
            cw = self._cancel_w
            self._active_cancel_writers += 1
        try:
            if self._on_before_cancel_write is not None:
                self._on_before_cancel_write()
            os.write(cw, b"x")
        except OSError:
            pass
        finally:
            cr_to_close, cw_to_close = None, None
            with self._admission_lock:
                self._active_cancel_writers -= 1
                cr_to_close, cw_to_close = self._maybe_close_cancel_pipe_locked()
                self._state_cond.notify_all()
            _safe_close_fd(cr_to_close)
            _safe_close_fd(cw_to_close)

    def _maybe_close_cancel_pipe_locked(self) -> tuple[int | None, int | None]:
        """Detach cancel pipe descriptors only when shutting down AND zero readers/writers remain."""
        if (
            self._shutting_down
            and self._active_selectors == 0
            and self._active_cancel_writers == 0
            and not self._cancel_closed
        ):
            self._cancel_closed = True
            cr, cw = self._cancel_r, self._cancel_w
            self._cancel_r = None
            self._cancel_w = None
            return cr, cw
        return None, None

    def _next_ipc_token(self) -> int:
        with self._admission_lock:
            self._ipc_token_counter += 1
            return self._ipc_token_counter

    def _poison(self, reason: str) -> None:
        with self._admission_lock:
            self._worker_poisoned = True
            self._poison_reason = reason
            self._state_cond.notify_all()

    def _assert_before_deadline(self, deadline: float, msg: str) -> None:
        if self._clock() >= deadline:
            raise _IpcTimeoutError(msg)

    def _get_or_create_supervisor(self, proc: subprocess.Popen[bytes]) -> _ProcKillReapSupervisor:
        """Return the single authoritative `_ProcKillReapSupervisor` for `proc`."""
        with self._admission_lock:
            sup = self._proc_supervisors.get(proc.pid)
            if sup is None or sup.proc is not proc:
                sup = _ProcKillReapSupervisor(proc, self._kill_fn)
                self._proc_supervisors[proc.pid] = sup
            return sup

    def _terminate_and_verify_handle(self, handle: _WorkerHandle, *, deadline: float | None = None) -> bool:
        """Single-owner teardown bounded by ONE absolute deadline across lock, I/O drain, kill, and reap."""
        abs_deadline = deadline if deadline is not None else (time.monotonic() + self.worker_reap_timeout_s)
        lock_wait = max(0.0, abs_deadline - time.monotonic())
        if not handle.teardown_exec_lock.acquire(timeout=lock_wait):
            self._poison("WORKER_TEARDOWN_LOCK_TIMEOUT")
            with self._admission_lock:
                if not handle.reaped and handle not in self._quarantined_handles:
                    self._quarantined_handles.append(handle)
            return False

        try:
            if handle.reaped:
                with self._admission_lock:
                    if handle in self._quarantined_handles:
                        self._quarantined_handles.remove(handle)
                    self._proc_supervisors.pop(handle.pid, None)
                return True

            with self._admission_lock:
                handle.closing = True
                if self._active_worker is handle:
                    self._active_worker = None
                if self._pending_handle is handle:
                    self._pending_handle = None
                self._state_cond.notify_all()

            sup: _ProcKillReapSupervisor | None = None
            kill_start_failed = False
            if handle.proc is not None:
                sup = handle.supervisor or self._get_or_create_supervisor(handle.proc)
                handle.supervisor = sup
                sup.register_close_callback(handle.close_fds)
                kill_start_failed = not sup.ensure_kill_started(request_retry_if_failed=True)

            with self._admission_lock:
                while handle.active_io > 0:
                    rem = abs_deadline - time.monotonic()
                    if rem <= 0.0:
                        break
                    self._state_cond.wait(timeout=rem)
                io_drained = handle.active_io == 0

            if not io_drained:
                with self._admission_lock:
                    self._worker_poisoned = True
                    self._poison_reason = "WORKER_IO_DRAIN_TIMEOUT"
                    if handle not in self._quarantined_handles:
                        self._quarantined_handles.append(handle)
                    self._state_cond.notify_all()
                return False

            if handle.proc is None or sup is None:
                handle.close_fds()
                handle.reaped = True
                return True

            if kill_start_failed:
                sup._drain_close_callbacks()
                reaped = handle.proc.poll() is not None and handle.proc.returncode is not None
            else:
                reaped = sup.wait_reaped_before(
                    abs_deadline,
                    close_cb=handle.close_fds,
                    request_retry_if_failed=True,
                )
            handle.reaped = reaped
            with self._admission_lock:
                if reaped:
                    if handle in self._quarantined_handles:
                        self._quarantined_handles.remove(handle)
                    self._proc_supervisors.pop(handle.pid, None)
                else:
                    self._worker_poisoned = True
                    self._poison_reason = "WORKER_TEARDOWN_UNVERIFIED"
                    if handle not in self._quarantined_handles:
                        self._quarantined_handles.append(handle)
                self._state_cond.notify_all()
            return reaped
        except BaseException:
            handle.close_fds()
            with self._admission_lock:
                self._worker_poisoned = True
                self._poison_reason = "WORKER_TEARDOWN_UNVERIFIED"
                if not handle.reaped and handle not in self._quarantined_handles:
                    self._quarantined_handles.append(handle)
                self._state_cond.notify_all()
            return False
        finally:
            handle.teardown_exec_lock.release()

    def _quarantine_orphan_proc(
        self,
        proc: subprocess.Popen[bytes],
        req_w: int | None,
        resp_r: int | None,
        reason: str,
        *,
        supervisor: _ProcKillReapSupervisor | None = None,
    ) -> _WorkerHandle:
        """Retain process and authoritative supervisor ownership in `_quarantined_handles` and poison manager."""
        sup = supervisor or self._get_or_create_supervisor(proc)
        with self._admission_lock:
            self._worker_poisoned = True
            self._poison_reason = reason
            existing: _WorkerHandle | None = None
            for h in self._quarantined_handles:
                if h.proc is proc or h.pid == proc.pid:
                    existing = h
                    break
            if existing is not None:
                if existing.supervisor is None:
                    existing.supervisor = sup
                if req_w is not None and existing.req_w is None:
                    existing.req_w = req_w
                if resp_r is not None and existing.resp_r is None:
                    existing.resp_r = resp_r
                sup.register_close_callback(existing.close_fds)
                self._state_cond.notify_all()
                return existing

            qh = _WorkerHandle(
                proc=proc,
                req_w=req_w if req_w is not None else -1,
                resp_r=resp_r if resp_r is not None else -1,
                expected_req_ino=0,
                expected_resp_ino=0,
                parent_closed_unused_ends=True,
                supervisor=sup,
            )
            if req_w is None:
                qh.req_w = None
            if resp_r is None:
                qh.resp_r = None
            sup.register_close_callback(qh.close_fds)
            self._quarantined_handles.append(qh)
            self._state_cond.notify_all()
            return qh

    def _terminal_error_result(
        self,
        default_status: int,
        default_code: str,
        default_msg: str,
        req_id: int | None,
        *,
        handle: _WorkerHandle | None = None,
        teardown_deadline: float | None = None,
    ) -> BridgeResult:
        """Teardown handle within single deadline and enforce poison precedence strictly."""
        if handle is not None:
            self._terminate_and_verify_handle(handle, deadline=teardown_deadline)
        with self._admission_lock:
            poisoned = self._worker_poisoned
        if poisoned:
            return BridgeResult(
                503,
                make_error_payload(
                    "WORKER_UNAVAILABLE_POISONED",
                    "Worker bridge is poisoned fail closed until process restart.",
                    request_id=req_id,
                ),
            )
        return BridgeResult(default_status, make_error_payload(default_code, default_msg, request_id=req_id))

    def _invoke_launcher(
        self,
        cmd: list[str],
        req_r: int,
        resp_w: int,
        slot: _LaunchSlot,
    ) -> subprocess.Popen[bytes]:
        def register_pid(proc: subprocess.Popen[bytes]) -> None:
            sup = self._get_or_create_supervisor(proc)
            sup.register_close_callback(slot.close_parent_fds)
            with slot.lock:
                slot.proc = proc
                slot.supervisor = sup
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
            str(WORKER_MODULE_PATH),
            "--worker",
            "--req-fd",
            str(req_r),
            "--resp-fd",
            str(resp_w),
        ]

    def _drain_decode_threads(self, *, deadline: float) -> bool:
        """Signal all tracked decode tasks to cancel and join within `deadline`."""
        with self._admission_lock:
            for ev in list(self._active_decode_cancels):
                ev.set()
            threads = list(self._active_decode_threads)
        all_done = True
        for th in threads:
            rem = max(0.0, deadline - time.monotonic())
            if th.is_alive():
                th.join(timeout=rem)
            if th.is_alive():
                all_done = False
            else:
                with self._admission_lock:
                    self._active_decode_threads.discard(th)
        if not all_done:
            self._poison("DECODE_THREAD_UNBOUNDED_ABANDONMENT")
        return all_done

    def _ensure_cleanup_deadline(self, cleanup_box: list[float | None]) -> float:
        """Return ONE single shared wall-clock teardown deadline anchored at first failure/expiry."""
        if cleanup_box[0] is None:
            cleanup_box[0] = time.monotonic() + self.worker_reap_timeout_s
        return cleanup_box[0]

    def _decode_and_verify_before(
        self,
        raw_bytes: bytes,
        deadline: float,
        verifier: Callable[[dict[str, Any]], None],
        *,
        max_depth: int = MAX_IPC_ENVELOPE_DEPTH,
    ) -> dict[str, Any]:
        """Decode UTF-8/JSON cleanly inside monotonic deadline with cooperative cancel tracking."""
        self._assert_before_deadline(deadline, "Deadline already expired before frame decode")
        cancel_ev = threading.Event()

        def _deadline_check() -> None:
            if cancel_ev.is_set() or self._shutting_down:
                raise _IpcTimeoutError("Decode cancelled by timeout or shutdown")
            if self._clock() >= deadline:
                raise _IpcTimeoutError("JSON decode/verification exceeded deadline")

        def _work() -> dict[str, Any]:
            obj = strict_json_loads(
                raw_bytes,
                max_depth=max_depth,
                deadline_check=_deadline_check,
                on_parse_entry=self._on_json_parse_entry,
            )
            if self._on_decode_transform is not None:
                try:
                    sig = inspect.signature(self._on_decode_transform)
                    if "cancel_event" in sig.parameters:
                        obj = self._on_decode_transform(obj, cancel_event=cancel_ev)
                    else:
                        obj = self._on_decode_transform(obj)
                except TypeError:
                    obj = self._on_decode_transform(obj)
            _deadline_check()
            verifier(obj)
            return obj

        if len(raw_bytes) <= 65536 and self._on_decode_transform is None:
            res = _work()
            self._assert_before_deadline(deadline, "Deadline expired during JSON decode or verification")
            return res

        box: dict[str, Any] = {}
        done = threading.Event()

        def _runner() -> None:
            try:
                box["res"] = _work()
            except BaseException as exc:  # noqa: BLE001
                box["err"] = exc
            finally:
                with self._admission_lock:
                    self._active_decode_threads.discard(th)
                    self._active_decode_cancels.discard(cancel_ev)
                    self._state_cond.notify_all()
                done.set()

        th: threading.Thread | None = None
        try:
            th = threading.Thread(target=_runner, daemon=True)
            with self._admission_lock:
                self._active_decode_threads.add(th)
                self._active_decode_cancels.add(cancel_ev)
            th.start()
        except BaseException as exc:  # noqa: BLE001
            cancel_ev.set()
            with self._admission_lock:
                if th is not None:
                    self._active_decode_threads.discard(th)
                self._active_decode_cancels.discard(cancel_ev)
                self._state_cond.notify_all()
            raise _IpcProtocolError(f"Decode thread startup failed: {exc}") from exc
        try:
            while not done.is_set():
                with self._admission_lock:
                    shutting_down = self._shutting_down
                if shutting_down:
                    cancel_ev.set()
                    raise _WorkerCancelledError("Cancelled by bridge shutdown during decode")
                remaining = deadline - self._clock()
                if remaining <= 0.0:
                    cancel_ev.set()
                    raise _IpcTimeoutError("JSON decode/verification exceeded deadline")
                done.wait(timeout=min(remaining, 0.02))
            if "err" in box:
                raise box["err"]
            res = box["res"]
        finally:
            cancel_ev.set()

        self._assert_before_deadline(deadline, "Deadline expired during JSON decode or response verification")
        return res

    def _abort_launch_slot(
        self,
        slot: _LaunchSlot,
        *,
        deadline: float,
        reason: str,
        wait_for_runner: bool,
    ) -> bool:
        """Abandon `slot` with ONE authoritative owner, shared deadline, bounded kill/reap, and synchronous poison if unverified."""
        early_sup: _ProcKillReapSupervisor | None = None
        do_early_kill = False
        with slot.lock:
            slot.abandoned = True
            slot.state = "ABORTED"
            if slot.cleanup_deadline is None:
                slot.cleanup_deadline = deadline
            eff_deadline = min(deadline, slot.cleanup_deadline)
            slot.done_cond.notify_all()
            th = slot.thread
            early_proc = slot.proc
            early_sup = slot.supervisor
            if early_proc is not None:
                if not slot.kill_attempt_started or (wait_for_runner and slot.cleanup_done and not slot.cleanup_verified):
                    slot.kill_attempt_started = True
                    slot.kill_attempt_finished = False
                    slot.kill_start_failed = False
                    do_early_kill = True

        early_kill_failed = False
        if early_proc is not None:
            if early_sup is None:
                early_sup = self._get_or_create_supervisor(early_proc)
                with slot.lock:
                    slot.supervisor = early_sup
            early_sup.register_close_callback(slot.close_parent_fds)
            if do_early_kill:
                started_ok = early_sup.ensure_kill_started(request_retry_if_failed=True)
                if not started_ok:
                    self._quarantine_orphan_proc(
                        early_proc,
                        None,
                        None,
                        reason,
                        supervisor=early_sup,
                    )
                with slot.lock:
                    slot.kill_start_failed = not started_ok
                    slot.kill_attempt_finished = True
                    slot.done_cond.notify_all()
                early_kill_failed = not started_ok
            else:
                with slot.lock:
                    while slot.kill_attempt_started and not slot.kill_attempt_finished:
                        rem = eff_deadline - time.monotonic()
                        if rem <= 0.0:
                            break
                        slot.done_cond.wait(timeout=rem)
                    early_kill_failed = slot.kill_start_failed or not slot.kill_attempt_finished

        if wait_for_runner and th is not None and th.is_alive():
            join_wait = max(0.0, eff_deadline - time.monotonic())
            th.join(timeout=join_wait)

        proc_pending: subprocess.Popen[bytes] | None = None
        sup_pending: _ProcKillReapSupervisor | None = None
        with slot.lock:
            claim_close = False
            if slot.cleanup_done:
                return bool(slot.cleanup_verified)
            if slot.cleanup_started:
                while not slot.cleanup_done:
                    rem = eff_deadline - time.monotonic()
                    if rem <= 0.0:
                        break
                    slot.cleanup_done_cond.wait(timeout=rem)
                if slot.cleanup_done:
                    return bool(slot.cleanup_verified)
                # V1-A-R3-F1 / R4-F1: Exhausted wait while another cleanup owner hasn't finished -> poison synchronously & retain!
                proc_pending = slot.proc
                sup_pending = slot.supervisor
            else:
                runner_returned = slot.runner_returned
                proc_still = slot.proc
                sup_still = slot.supervisor
                if not runner_returned and th is not None:
                    proc_pending = proc_still
                    sup_pending = sup_still
                else:
                    slot.cleanup_started = True
                    p0, p1 = slot.parent_fds
                    slot.parent_fds = (None, None)
                    c0, c1 = slot.child_fds
                    slot.child_fds = (None, None)
                    claim_close = True
                    proc_pending = proc_still
                    sup_pending = sup_still

            wait_exhausted = not claim_close

        if wait_exhausted:
            self._poison("LAUNCH_CLEANUP_UNVERIFIED")
            # Slot is definitively ABORTED/nontransferable: close parent endpoints promptly and at-most-once
            # without touching launcher-owned child_fds while runner state may remain uncertain.
            slot.close_parent_fds()
            if proc_pending is not None:
                if sup_pending is None:
                    sup_pending = self._get_or_create_supervisor(proc_pending)
                sup_pending.register_close_callback(slot.close_parent_fds)
                if not (early_kill_failed and early_proc is proc_pending):
                    sup_pending.ensure_kill_started(request_retry_if_failed=True)
                self._quarantine_orphan_proc(
                    proc_pending,
                    None,
                    None,
                    reason,
                    supervisor=sup_pending,
                )
            return False

        _safe_close_fd(c0)
        _safe_close_fd(c1)

        if proc_pending is not None:
            if sup_pending is None:
                sup_pending = self._get_or_create_supervisor(proc_pending)
                with slot.lock:
                    slot.supervisor = sup_pending
            close_fn = lambda: (_safe_close_fd(p0), _safe_close_fd(p1), slot.close_parent_fds())
            if early_kill_failed and early_proc is proc_pending:
                sup_pending.register_close_callback(close_fn)
                sup_pending._drain_close_callbacks()
                verified = proc_pending.poll() is not None and proc_pending.returncode is not None
            else:
                verified = sup_pending.wait_reaped_before(
                    eff_deadline,
                    close_cb=close_fn,
                    request_retry_if_failed=True,
                )
            if verified:
                with self._admission_lock:
                    if self._active_worker is None and self._pending_handle is None:
                        for qh in list(self._quarantined_handles):
                            if qh.pid == proc_pending.pid:
                                qh.reaped = True
                                self._quarantined_handles.remove(qh)
                    self._proc_supervisors.pop(proc_pending.pid, None)
            else:
                self._quarantine_orphan_proc(
                    proc_pending,
                    None,
                    None,
                    reason,
                    supervisor=sup_pending,
                )
        else:
            _safe_close_fd(p0)
            _safe_close_fd(p1)
            verified = True

        with slot.lock:
            slot.cleanup_verified = verified
            slot.cleanup_done = True
            slot.cleanup_done_cond.notify_all()

        with self._admission_lock:
            if self._active_launch is slot and (verified or proc_pending is not None):
                # Retained in _quarantined_handles if unverified with PID; otherwise verified clean
                self._active_launch = None
            self._state_cond.notify_all()

        return verified

    def _spawn_and_handshake(
        self,
        deadline: float,
        req_id: int | None,
        cleanup_box: list[float | None],
    ) -> _WorkerHandle | BridgeResult:
        """Transactionally allocate pipes, commit launch slot atomically, launch child within deadline, and verify READY."""
        self._assert_before_deadline(deadline, "Worker startup deadline expired before pipe setup")

        req_r: int | None = None
        req_w: int | None = None
        resp_r: int | None = None
        resp_w: int | None = None

        try:
            req_r, req_w = os.pipe()
            resp_r, resp_w = os.pipe()
            os.set_blocking(req_w, False)
            os.set_blocking(resp_r, False)
            expected_req_ino = os.fstat(req_r).st_ino
            expected_resp_ino = os.fstat(resp_w).st_ino
            slot = _LaunchSlot((req_r, resp_w), (req_w, resp_r))
            cmd = self._build_worker_command(req_r, resp_w)
        except Exception as exc:
            _safe_close_fd(req_r)
            _safe_close_fd(req_w)
            _safe_close_fd(resp_r)
            _safe_close_fd(resp_w)
            return self._terminal_error_result(
                503,
                "WORKER_STARTUP_FAILED",
                f"Failed to prepare IPC pipes for worker launch: {exc}",
                req_id,
            )

        if self._on_before_launch_slot_publish is not None:
            self._on_before_launch_slot_publish()

        # Commit _active_launch ONLY if healthy, not shutting down, and strictly before deadline
        with self._admission_lock:
            poisoned = self._worker_poisoned
            shutting_down = self._shutting_down
            expired = self._clock() >= deadline
            if poisoned or shutting_down or expired:
                published = False
            else:
                self._active_launch = slot
                published = True

        if not published:
            slot.close_child_fds()
            slot.close_parent_fds()
            if expired and not poisoned and not shutting_down:
                raise _IpcTimeoutError("Worker startup deadline expired prior to slot publication")
            return self._terminal_error_result(
                503,
                "SERVER_SHUTTING_DOWN",
                "Bridge shutting down.",
                req_id,
            )

        if self._on_after_slot_publish_before_runner is not None:
            self._on_after_slot_publish_before_runner(slot)

        def _launch_runner() -> None:
            try:
                with slot.lock:
                    should_abort = slot.abandoned or slot.state != "PENDING"
                if not should_abort:
                    proc_created = self._invoke_launcher(cmd, req_r, resp_w, slot)
                    if proc_created is not None and self._on_after_runner_pid_before_done is not None:
                        self._on_after_runner_pid_before_done(proc_created)
            except BaseException as exc:  # noqa: BLE001 - captured fail-closed for supervisor
                with slot.lock:
                    slot.error = exc
            finally:
                # Child pipe ends MUST always be closed once fork/exec returns or fails.
                slot.close_child_fds()
                with slot.lock:
                    slot.runner_returned = True
                    need_cleanup = slot.abandoned or slot.state != "PENDING" or (slot.error is not None) or (slot.proc is None)
                    slot.done_cond.notify_all()
                if self._on_after_runner_returned_before_cleanup is not None:
                    self._on_after_runner_returned_before_cleanup(slot)
                if need_cleanup:
                    with slot.lock:
                        runner_dl = slot.cleanup_deadline if slot.cleanup_deadline is not None else (time.monotonic() + self.worker_reap_timeout_s)
                    self._abort_launch_slot(
                        slot,
                        deadline=runner_dl,
                        reason="ABANDONED_LAUNCH_REAP_FAILED",
                        wait_for_runner=False,
                    )

        th: threading.Thread | None = None
        launch_thread_err: BaseException | None = None
        with slot.lock:
            if slot.abandoned or slot.state != "PENDING":
                start_runner = False
            else:
                start_runner = True
                try:
                    th = threading.Thread(target=_launch_runner, daemon=True)
                    slot.thread = th
                except BaseException as exc:  # noqa: BLE001
                    slot.thread = None
                    slot.runner_returned = True
                    slot.error = exc
                    launch_thread_err = exc

        if not start_runner:
            td = self._ensure_cleanup_deadline(cleanup_box)
            self._abort_launch_slot(
                slot,
                deadline=td,
                reason="PRE_RUNNER_LAUNCH_ABORT_FAILED",
                wait_for_runner=False,
            )
            return self._terminal_error_result(503, "SERVER_SHUTTING_DOWN", "Bridge shutting down.", req_id)

        if launch_thread_err is None:
            try:
                assert th is not None
                th.start()
            except BaseException as exc:  # noqa: BLE001
                launch_thread_err = exc
                with slot.lock:
                    slot.thread = None
                    slot.runner_returned = True
                    slot.error = exc

        if launch_thread_err is not None:
            td = self._ensure_cleanup_deadline(cleanup_box)
            self._abort_launch_slot(
                slot,
                deadline=td,
                reason="LAUNCH_THREAD_START_FAILED",
                wait_for_runner=False,
            )
            return self._terminal_error_result(
                503,
                "WORKER_STARTUP_FAILED",
                f"Failed to start launch supervisor thread: {launch_thread_err}",
                req_id,
            )

        # Wait WITHOUT ever holding _admission_lock (prevents V1-A-R2-F1 self-deadlock)
        timed_out_launch = False
        while True:
            with self._admission_lock:
                shutting_down = self._shutting_down
                poisoned = self._worker_poisoned
            if shutting_down or poisoned:
                td = self._ensure_cleanup_deadline(cleanup_box)
                self._abort_launch_slot(
                    slot,
                    deadline=td,
                    reason="SHUTDOWN_LAUNCH_REAP_FAILED",
                    wait_for_runner=True,
                )
                return self._terminal_error_result(
                    503,
                    "WORKER_UNAVAILABLE_POISONED" if poisoned else "SERVER_SHUTTING_DOWN",
                    "Bridge shutting down.",
                    req_id,
                )

            with slot.lock:
                if slot.runner_returned:
                    break
                remaining = deadline - self._clock()
                if remaining <= 0.0:
                    timed_out_launch = True
                    slot.abandoned = True
                    slot.state = "ABORTED"
                    slot.done_cond.notify_all()
                    break
                slot.done_cond.wait(timeout=min(remaining, 0.02))

        if timed_out_launch:
            self._poison("WORKER_STARTUP_LAUNCH_TIMEOUT")
            td = self._ensure_cleanup_deadline(cleanup_box)
            self._abort_launch_slot(
                slot,
                deadline=td,
                reason="STALLED_LAUNCH_REAP_FAILED",
                wait_for_runner=False,
            )
            return BridgeResult(
                503,
                make_error_payload(
                    "WORKER_UNAVAILABLE_POISONED",
                    "Worker launch stalled past deadline; bridge poisoned fail closed.",
                    request_id=req_id,
                ),
            )

        if self._on_before_slot_to_pending_handoff is not None:
            self._on_before_slot_to_pending_handoff(slot)

        # Atomic linearization point: slot -> _pending_handle under one _admission_lock + slot.lock hold
        handle: _WorkerHandle | None = None
        handoff_expired = False
        handoff_error: BaseException | None = None
        with self._admission_lock:
            with slot.lock:
                handoff_error = slot.error
                poisoned = self._worker_poisoned
                shutting_down = self._shutting_down
                handoff_expired = self._clock() >= deadline
                can_transfer = (
                    not poisoned
                    and not shutting_down
                    and not handoff_expired
                    and slot.state == "PENDING"
                    and not slot.abandoned
                    and slot.error is None
                    and slot.proc is not None
                    and slot.parent_fds[0] is not None
                    and slot.parent_fds[1] is not None
                )
                if can_transfer:
                    t_req_w, t_resp_r = slot.parent_fds
                    slot.parent_fds = (None, None)
                    slot.state = "TRANSFERRED"
                    # V1-A-R3-M2: closure evidence derived strictly from verified ownership close of original child endpoints
                    parent_closed_unused = (
                        slot.child_fds == (None, None)
                        and slot.child_req_fd_closed
                        and slot.child_resp_fd_closed
                    )
                    assert slot.proc is not None and t_req_w is not None and t_resp_r is not None
                    sup = slot.supervisor
                    if sup is None:
                        sup = self._proc_supervisors.get(slot.proc.pid)
                        if sup is None or sup.proc is not slot.proc:
                            sup = _ProcKillReapSupervisor(slot.proc, self._kill_fn)
                            self._proc_supervisors[slot.proc.pid] = sup
                    handle = _WorkerHandle(
                        proc=slot.proc,
                        req_w=t_req_w,
                        resp_r=t_resp_r,
                        expected_req_ino=expected_req_ino,
                        expected_resp_ino=expected_resp_ino,
                        parent_closed_unused_ends=parent_closed_unused,
                        supervisor=sup,
                    )
                    sup.register_close_callback(handle.close_fds)
                    if self._active_launch is slot:
                        self._active_launch = None
                    self._pending_handle = handle

        if handle is None:
            td = self._ensure_cleanup_deadline(cleanup_box)
            verified_cleanup = self._abort_launch_slot(
                slot,
                deadline=td,
                reason="LAUNCH_HANDOFF_REAP_FAILED",
                wait_for_runner=True,
            )
            if handoff_expired:
                with self._admission_lock:
                    poisoned = self._worker_poisoned
                    shutting_down = self._shutting_down
                if not poisoned and not shutting_down and verified_cleanup:
                    raise _IpcTimeoutError("Worker launch deadline expired before READY handshake")
            return self._terminal_error_result(
                503,
                "WORKER_STARTUP_FAILED",
                f"Worker failed to start: {handoff_error or 'aborted or unavailable'}",
                req_id,
            )

        # Wait for worker READY handshake AND verify within the SAME monotonic deadline
        try:
            ready_bytes = self._recv_frame_before(handle, deadline, max_bytes=MAX_IPC_REQUEST_BYTES)

            def _verify_ready(ready: dict[str, Any]) -> None:
                if (
                    ready.get("type") != "READY"
                    or not _is_exact_int(ready.get("pid"))
                    or ready.get("pid") != handle.pid
                    or not _is_exact_int(ready.get("req_ino"))
                    or ready.get("req_ino") != expected_req_ino
                    or not _is_exact_int(ready.get("resp_ino"))
                    or ready.get("resp_ino") != expected_resp_ino
                ):
                    raise _IpcProtocolError("READY handshake failed descriptor identity or exact type verification")

            self._decode_and_verify_before(ready_bytes, deadline, _verify_ready, max_depth=MAX_IPC_ENVELOPE_DEPTH)
        except _IpcTimeoutError:
            td = self._ensure_cleanup_deadline(cleanup_box)
            self._drain_decode_threads(deadline=td)
            return self._terminal_error_result(
                504,
                "SOLVE_DEADLINE_EXCEEDED",
                "Worker handshake exceeded admitted startup/IPC deadline.",
                req_id,
                handle=handle,
                teardown_deadline=td,
            )
        except _WorkerCancelledError:
            td = self._ensure_cleanup_deadline(cleanup_box)
            self._drain_decode_threads(deadline=td)
            return self._terminal_error_result(
                503,
                "SERVER_SHUTTING_DOWN",
                "Bridge shutting down.",
                req_id,
                handle=handle,
                teardown_deadline=td,
            )
        except (_IpcEofError, _IpcProtocolError, ValueError, UnicodeDecodeError) as exc:
            td = self._ensure_cleanup_deadline(cleanup_box)
            return self._terminal_error_result(
                503,
                "WORKER_STARTUP_FAILED",
                f"Worker startup handshake failed: {exc}",
                req_id,
                handle=handle,
                teardown_deadline=td,
            )

        if self._on_before_ready_publish is not None:
            self._on_before_ready_publish(handle)

        # Publish atomically computing expiry AT the exact linearization point inside _admission_lock
        with self._admission_lock:
            expired = self._clock() >= deadline
            if expired or self._shutting_down or self._worker_poisoned or handle.closing:
                cannot_publish = True
            else:
                self._pending_handle = None
                self._active_worker = handle
                cannot_publish = False

        if cannot_publish:
            td = self._ensure_cleanup_deadline(cleanup_box)
            if expired:
                return self._terminal_error_result(
                    504,
                    "SOLVE_DEADLINE_EXCEEDED",
                    "Worker handshake deadline expired before READY publication.",
                    req_id,
                    handle=handle,
                    teardown_deadline=td,
                )
            return self._terminal_error_result(
                503,
                "SERVER_SHUTTING_DOWN",
                "Bridge shutting down.",
                req_id,
                handle=handle,
                teardown_deadline=td,
            )

        return handle

    def _enter_handle_io(self, handle: _WorkerHandle) -> int:
        with self._admission_lock:
            if self._shutting_down or handle.closing:
                raise _WorkerCancelledError("Cancelled by bridge shutdown or closing handle")
            if self._cancel_closed or self._cancel_r is None:
                raise _WorkerCancelledError("Cancellation descriptor closed on shutdown")
            self._active_selectors += 1
            handle.active_io += 1
            return self._cancel_r

    def _exit_handle_io(self, handle: _WorkerHandle) -> None:
        cr_to_close: int | None = None
        cw_to_close: int | None = None
        with self._admission_lock:
            handle.active_io -= 1
            self._active_selectors -= 1
            cr_to_close, cw_to_close = self._maybe_close_cancel_pipe_locked()
            self._state_cond.notify_all()
        _safe_close_fd(cr_to_close)
        _safe_close_fd(cw_to_close)

    def _select_ready(self, handle: _WorkerHandle, fd: int | None, events: int, deadline: float) -> None:
        if self._on_before_selector_register is not None:
            self._on_before_selector_register(handle)
        cancel_r = self._enter_handle_io(handle)
        try:
            if fd is None:
                raise _WorkerCancelledError("Handle pipe closed")
            with selectors.DefaultSelector() as sel:
                sel.register(fd, events, data="io")
                sel.register(cancel_r, selectors.EVENT_READ, data="cancel")
                remaining = deadline - self._clock()
                if remaining <= 0.0:
                    raise _IpcTimeoutError("Admitted compute/IPC deadline exceeded")
                ready = sel.select(timeout=remaining)
                if not ready:
                    raise _IpcTimeoutError("Admitted compute/IPC deadline exceeded")
                for key, _ in ready:
                    if key.data == "cancel":
                        raise _WorkerCancelledError("Cancelled by bridge shutdown")
                self._assert_before_deadline(deadline, "Admitted compute/IPC deadline exceeded after select")
        finally:
            self._exit_handle_io(handle)

    def _send_frame_before(self, handle: _WorkerHandle, frame: bytes, deadline: float) -> None:
        mv = memoryview(frame)
        sent = 0
        while sent < len(frame):
            self._assert_before_deadline(deadline, "Blocked request write exceeded deadline")
            self._select_ready(handle, handle.req_w, selectors.EVENT_WRITE, deadline)
            self._enter_handle_io(handle)
            try:
                req_w = handle.req_w
                if req_w is None or handle.closing:
                    raise _WorkerCancelledError("Worker pipe closed before write")
                n = os.write(req_w, mv[sent:])
                if n == 0:
                    raise _IpcEofError("Worker request pipe closed during write")
                sent += n
                self._assert_before_deadline(deadline, "Request write exceeded deadline")
            except BlockingIOError:
                continue
            except (_IpcTimeoutError, _WorkerCancelledError):
                raise
            except (BrokenPipeError, ConnectionResetError) as exc:
                raise _IpcEofError("Worker pipe broken during write") from exc
            except OSError as exc:
                raise _IpcEofError(f"Worker pipe write OS error: {exc}") from exc
            finally:
                self._exit_handle_io(handle)

    def _recv_exact_before(self, handle: _WorkerHandle, n_bytes: int, deadline: float) -> bytes:
        buf = bytearray()
        while len(buf) < n_bytes:
            self._assert_before_deadline(deadline, "Response read exceeded deadline")
            self._select_ready(handle, handle.resp_r, selectors.EVENT_READ, deadline)
            self._enter_handle_io(handle)
            try:
                resp_r = handle.resp_r
                if resp_r is None or handle.closing:
                    raise _WorkerCancelledError("Worker pipe closed before read")
                chunk = os.read(resp_r, n_bytes - len(buf))
            except BlockingIOError:
                continue
            except (_IpcTimeoutError, _WorkerCancelledError):
                raise
            except (BrokenPipeError, ConnectionResetError) as exc:
                raise _IpcEofError("Worker pipe broken during read") from exc
            except OSError as exc:
                raise _IpcEofError(f"Worker pipe read OS error: {exc}") from exc
            finally:
                self._exit_handle_io(handle)
            if chunk == b"":
                raise _IpcEofError("Unexpected EOF from worker process")
            buf.extend(chunk)
            if self._on_after_raw_read is not None:
                self._on_after_raw_read(bytes(chunk))
            self._assert_before_deadline(deadline, "Response read exceeded deadline after final chunk")
        return bytes(buf)

    def _recv_frame_before(self, handle: _WorkerHandle, deadline: float, *, max_bytes: int) -> bytes:
        hdr = self._recv_exact_before(handle, 4, deadline)
        (frame_len,) = struct.unpack(">I", hdr)
        if frame_len == 0 or frame_len > max_bytes:
            raise _IpcProtocolError(f"Invalid IPC response frame length {frame_len} (max={max_bytes})")
        return self._recv_exact_before(handle, frame_len, deadline)

    def _validate_and_serialize_request(
        self,
        endpoint: str,
        request_payload: dict[str, Any],
        raw_request_bytes: bytes | bytearray | None,
        req_id: int | None,
    ) -> bytes | BridgeResult:
        """Validate exact serialized request JSON representation before admission and return immutable JSON bytes."""
        if not isinstance(endpoint, str) or not endpoint:
            return BridgeResult(
                400,
                make_error_payload("INVALID_JSON", "Invalid endpoint string", request_id=req_id),
            )
        if not isinstance(request_payload, dict):
            return BridgeResult(
                400,
                make_error_payload("INVALID_JSON", "Request payload must be a JSON object", request_id=req_id),
            )

        if raw_request_bytes is not None:
            raw_type = type(raw_request_bytes)
            if raw_type is bytes:
                raw_snapshot = raw_request_bytes
            elif raw_type is bytearray:
                raw_snapshot = bytes(raw_request_bytes)
            else:
                return BridgeResult(
                    400,
                    make_error_payload(
                        "INVALID_JSON",
                        f"raw_request_bytes must be exact bytes or bytearray, got {raw_type.__name__}",
                        request_id=req_id,
                    ),
                )
            if len(raw_snapshot) == 0:
                return BridgeResult(
                    400,
                    make_error_payload("INVALID_JSON", "Raw request bytes must be non-empty UTF-8 JSON", request_id=req_id),
                )
            if len(raw_snapshot) > MAX_IPC_REQUEST_BYTES:
                return BridgeResult(
                    413,
                    make_error_payload(
                        "PAYLOAD_TOO_LARGE",
                        f"Raw request exceeds maximum {MAX_IPC_REQUEST_BYTES} bytes",
                        request_id=req_id,
                    ),
                )
            try:
                _validate_json_depth_and_finiteness(request_payload, max_depth=MAX_CLIENT_JSON_DEPTH)
                parsed_raw = strict_json_loads(raw_snapshot, max_depth=MAX_CLIENT_JSON_DEPTH)
            except DuplicateKeyError as exc:
                return BridgeResult(
                    400,
                    make_error_payload("DUPLICATE_KEY", str(exc), request_id=req_id),
                )
            except (ValueError, UnicodeDecodeError, UnicodeEncodeError, RecursionError, TypeError) as exc:
                return BridgeResult(
                    400,
                    make_error_payload("INVALID_JSON", f"Malformed or invalid raw request JSON: {exc}", request_id=req_id),
                )
            if not _json_values_strictly_equal(parsed_raw, request_payload) or extract_safe_request_id(parsed_raw) != req_id:
                return BridgeResult(
                    400,
                    make_error_payload(
                        "INVALID_JSON",
                        "raw_request_bytes does not match request_payload",
                        request_id=req_id,
                    ),
                )
            req_bytes = raw_snapshot
        else:
            try:
                _validate_json_depth_and_finiteness(request_payload, max_depth=MAX_CLIENT_JSON_DEPTH)
                req_bytes = strict_json_dumps(request_payload)
                # Parse exact serialized JSON bytes to guarantee zero coercion collisions or unvalidated depth
                strict_json_loads(req_bytes, max_depth=MAX_CLIENT_JSON_DEPTH)
            except DuplicateKeyError as exc:
                return BridgeResult(
                    400,
                    make_error_payload("DUPLICATE_KEY", str(exc), request_id=req_id),
                )
            except (ValueError, UnicodeDecodeError, UnicodeEncodeError, RecursionError, TypeError) as exc:
                return BridgeResult(
                    400,
                    make_error_payload("INVALID_JSON", f"Malformed or invalid request payload: {exc}", request_id=req_id),
                )

        try:
            max_meta_bytes = strict_json_dumps(
                {
                    "ipc_token": (1 << 64) - 1,
                    "endpoint": endpoint,
                    "expected_req_ino": (1 << 64) - 1,
                    "expected_resp_ino": (1 << 64) - 1,
                    "parent_closed_unused_ends": False,
                }
            )
        except (ValueError, UnicodeEncodeError, TypeError) as exc:
            return BridgeResult(
                400,
                make_error_payload("INVALID_JSON", f"Malformed request metadata: {exc}", request_id=req_id),
            )

        max_wire_len = len(max_meta_bytes) - 1 + len(b',"request":') + len(req_bytes) + 1
        if max_wire_len > MAX_IPC_REQUEST_BYTES:
            return BridgeResult(
                413,
                make_error_payload(
                    "PAYLOAD_TOO_LARGE",
                    f"Serialized IPC request ({max_wire_len} bytes) exceeds maximum {MAX_IPC_REQUEST_BYTES} bytes",
                    request_id=req_id,
                ),
            )
        return req_bytes

    def execute(
        self,
        endpoint: str,
        request_payload: dict[str, Any],
        *,
        raw_request_bytes: bytes | bytearray | None = None,
    ) -> BridgeResult:
        """Admit, supervise, and execute one bounded IPC request against the single worker."""
        req_id = extract_safe_request_id(request_payload)

        # V1-A-R3-M1 / R4-M1 / R5-M1: Validate exact immutable JSON byte snapshot BEFORE admitting or touching a worker
        validated_or_err = self._validate_and_serialize_request(
            endpoint,
            request_payload,
            raw_request_bytes,
            req_id,
        )
        if isinstance(validated_or_err, BridgeResult):
            return validated_or_err
        verified_req_bytes = validated_or_err

        with self._admission_lock:
            # Strict order: poison > shutdown > concurrency > admission
            if self._worker_poisoned:
                return BridgeResult(
                    503,
                    make_error_payload(
                        "WORKER_UNAVAILABLE_POISONED",
                        "Worker bridge is poisoned fail closed until process restart.",
                        request_id=req_id,
                    ),
                )
            if self._shutting_down:
                return BridgeResult(
                    503,
                    make_error_payload("SERVER_SHUTTING_DOWN", "Bridge is shutting down.", request_id=req_id),
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

        handle: _WorkerHandle | None = None
        cleanup_box: list[float | None] = [None]
        try:
            deadline = self._clock() + self.response_deadline_s
            with self._admission_lock:
                handle = self._active_worker

            if handle is None:
                spawned = self._spawn_and_handshake(deadline, req_id, cleanup_box)
                if isinstance(spawned, BridgeResult):
                    return spawned
                handle = spawned

            ipc_token = self._next_ipc_token()
            meta_bytes = strict_json_dumps(
                {
                    "ipc_token": ipc_token,
                    "endpoint": endpoint,
                    "expected_req_ino": handle.expected_req_ino,
                    "expected_resp_ino": handle.expected_resp_ino,
                    "parent_closed_unused_ends": handle.parent_closed_unused_ends,
                }
            )
            payload_wire_bytes = meta_bytes[:-1] + b',"request":' + verified_req_bytes + b"}"

            frame = _pack_frame(payload_wire_bytes, MAX_IPC_REQUEST_BYTES)
            self._assert_before_deadline(deadline, "Request serialization exceeded deadline")

            self._send_frame_before(handle, frame, deadline)
            raw_resp = self._recv_frame_before(handle, deadline, max_bytes=MAX_IPC_RESPONSE_BYTES)

            def _verify_resp(resp_obj: dict[str, Any]) -> None:
                tok = resp_obj.get("ipc_token")
                if not _is_exact_int(tok) or tok != ipc_token:
                    raise _IpcProtocolError(
                        f"IPC token mismatch or invalid type: expected {ipc_token}, got {tok!r}"
                    )

            resp_obj = self._decode_and_verify_before(raw_resp, deadline, _verify_resp, max_depth=MAX_IPC_ENVELOPE_DEPTH)
            with self._admission_lock:
                cancelled = self._worker_poisoned or self._shutting_down
            if cancelled:
                td = self._ensure_cleanup_deadline(cleanup_box)
                self._drain_decode_threads(deadline=td)
                return self._terminal_error_result(
                    503,
                    "SERVER_SHUTTING_DOWN",
                    "Bridge shutting down.",
                    req_id,
                    handle=handle,
                    teardown_deadline=td,
                )
            self._assert_before_deadline(deadline, "Deadline expired immediately prior to response return")
            return BridgeResult(200, resp_obj)

        except _IpcTimeoutError:
            td = self._ensure_cleanup_deadline(cleanup_box)
            self._drain_decode_threads(deadline=td)
            return self._terminal_error_result(
                504,
                "SOLVE_DEADLINE_EXCEEDED",
                "Admitted compute/IPC/startup deadline exceeded; worker cleanly killed and reaped.",
                req_id,
                handle=handle,
                teardown_deadline=td,
            )
        except _WorkerCancelledError:
            td = self._ensure_cleanup_deadline(cleanup_box)
            self._drain_decode_threads(deadline=td)
            return self._terminal_error_result(
                503,
                "SERVER_SHUTTING_DOWN",
                "Bridge shutting down.",
                req_id,
                handle=handle,
                teardown_deadline=td,
            )
        except _IpcEofError as exc:
            td = self._ensure_cleanup_deadline(cleanup_box)
            self._drain_decode_threads(deadline=td)
            return self._terminal_error_result(
                500,
                "WORKER_CRASHED",
                str(exc),
                req_id,
                handle=handle,
                teardown_deadline=td,
            )
        except (_IpcProtocolError, ValueError, UnicodeDecodeError) as exc:
            td = self._ensure_cleanup_deadline(cleanup_box)
            self._drain_decode_threads(deadline=td)
            return self._terminal_error_result(
                500,
                "IPC_PROTOCOL_ERROR",
                str(exc),
                req_id,
                handle=handle,
                teardown_deadline=td,
            )
        finally:
            with self._admission_lock:
                # Never reopen admission while poisoned or while an abandoned decode thread is still alive
                decode_still_running = any(t.is_alive() for t in self._active_decode_threads)
                if decode_still_running:
                    self._worker_poisoned = True
                    if self._poison_reason is None:
                        self._poison_reason = "DECODE_THREAD_UNBOUNDED_ABANDONMENT"
                if not self._worker_poisoned:
                    self._compute_in_progress = False
                self._state_cond.notify_all()

    def shutdown(self) -> None:
        """Synchronized shutdown bounded by ONE single `worker_reap_timeout_s` deadline."""
        shutdown_deadline = time.monotonic() + self.worker_reap_timeout_s

        with self._admission_lock:
            self._shutting_down = True
            handles_to_stop: list[_WorkerHandle] = []
            for cand in (self._active_worker, self._pending_handle, *self._quarantined_handles):
                if cand is not None and cand not in handles_to_stop:
                    handles_to_stop.append(cand)
            launch_slot = self._active_launch
            for ev in list(self._active_decode_cancels):
                ev.set()
            self._state_cond.notify_all()

        if launch_slot is not None:
            launch_slot.notify()

        self._wake_cancel_pipe()

        for handle in handles_to_stop:
            self._terminate_and_verify_handle(handle, deadline=shutdown_deadline)

        if launch_slot is not None:
            self._abort_launch_slot(
                launch_slot,
                deadline=shutdown_deadline,
                reason="SHUTDOWN_LAUNCH_REAP_FAILED",
                wait_for_runner=True,
            )

        self._drain_decode_threads(deadline=shutdown_deadline)

        # Re-check any handle published or quarantined while handles/launch were winding down
        extra_handles: list[_WorkerHandle] = []
        with self._admission_lock:
            for cand in (self._active_worker, self._pending_handle, *self._quarantined_handles):
                if cand is not None and cand not in handles_to_stop and cand not in extra_handles:
                    extra_handles.append(cand)
        for handle in extra_handles:
            self._terminate_and_verify_handle(handle, deadline=shutdown_deadline)

        # Wait bounded for active selectors and cancel-pipe writers BEFORE closing cancel pipe
        cr_to_close: int | None = None
        cw_to_close: int | None = None
        with self._admission_lock:
            while self._active_selectors > 0 or self._active_cancel_writers > 0:
                rem = shutdown_deadline - time.monotonic()
                if rem <= 0.0:
                    break
                self._state_cond.wait(timeout=rem)
            cr_to_close, cw_to_close = self._maybe_close_cancel_pipe_locked()

        _safe_close_fd(cr_to_close)
        _safe_close_fd(cw_to_close)


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
        if not cl_str or not (cl_str.isascii() and cl_str.isdigit()):
            raise HttpRequestError(
                400,
                "INVALID_CONTENT_LENGTH",
                "Content-Length must be an ASCII non-negative decimal integer",
                field="Content-Length",
            )
        normalized_cl = cl_str.lstrip("0") or "0"
        if len(normalized_cl) > 10:
            raise HttpRequestError(
                413,
                "PAYLOAD_TOO_LARGE",
                f"Content-Length exceeds maximum {MAX_HTTP_BODY_BYTES} bytes",
                field="Content-Length",
            )
        content_length = int(normalized_cl)
        if content_length > MAX_HTTP_BODY_BYTES:
            raise HttpRequestError(413, "PAYLOAD_TOO_LARGE", f"Body length {content_length} exceeds {MAX_HTTP_BODY_BYTES} bytes", field="Content-Length")

        body_bytes = self.rfile.read(content_length)
        if len(body_bytes) != content_length:
            raise HttpRequestError(400, "INCOMPLETE_BODY", "Client disconnected before sending full Content-Length")

        try:
            payload = strict_json_loads(body_bytes, max_depth=MAX_CLIENT_JSON_DEPTH)
            return payload, body_bytes
        except DuplicateKeyError as exc:
            raise HttpRequestError(400, "DUPLICATE_KEY", str(exc)) from exc
        except (ValueError, UnicodeDecodeError, UnicodeEncodeError, RecursionError) as exc:
            raise HttpRequestError(400, "INVALID_JSON", f"Malformed or non-finite JSON payload: {exc}") from exc

    def do_POST(self) -> None:  # noqa: N802 - http.server method name
        self.close_connection = True
        if self.path not in ("/api/v1/solve", "/api/v1/study"):
            self._send_json_response(404, make_error_payload("NOT_FOUND", f"Unknown API endpoint: {self.path}"))
            return

        try:
            self._validate_host_and_origin()
            payload, body_bytes = self._validate_framing_and_read_json()
        except HttpReadTimeoutError:
            self._send_json_response(
                408,
                make_error_payload("REQUEST_READ_TIMEOUT", "HTTP request header/body read deadline exceeded."),
            )
            return
        except HttpRequestError as exc:
            self._send_json_response(exc.status_code, make_error_payload(exc.code, exc.message, field=exc.field))
            return

        result = self.server.worker_manager.execute(
            self.path,
            payload,
            raw_request_bytes=body_bytes,
        )  # type: ignore[attr-defined]
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
            try:
                request.setblocking(False)
                request.recv(4096)
            except OSError:
                pass
            finally:
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
        msg = strict_json_loads(_worker_read_exact(req_fd, frame_len), max_depth=MAX_IPC_ENVELOPE_DEPTH)
        req_body = msg.get("request") if isinstance(msg.get("request"), dict) else {}

        delay_s = req_body.get("delay_s")
        if (
            (isinstance(delay_s, int) and not isinstance(delay_s, bool) and 0 < delay_s <= 10)
            or (isinstance(delay_s, float) and math.isfinite(delay_s) and 0.0 < delay_s <= 10.0)
        ):
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
