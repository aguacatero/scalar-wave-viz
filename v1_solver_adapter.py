"""Validated P0/P1 electrostatics solver adapters, canonical schemas, and IEEE-754 fingerprints (V1-B B1).

Enforces strict epistemic separation, pre-solve domain eligibility, post-solve
kernel-matched snapped-contour topology checks, dual probe validity parity,
6-component force accounting, gated multi-resolution studies, and cryptographic
preservation of frozen P0/P1 kernels (`electrostatics_baseline.py` and
`electrostatics_numerics.py`) with zero Track B P2 or Exodus dependencies.
"""

from __future__ import annotations

from functools import lru_cache
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess
from typing import Any

import numpy as np

from electrostatics_baseline import (
    EPSILON_0_F_PER_M,
    FieldSolution,
    GroundedBoxConfig,
    ElectrodeConfig,
    assess_probe_convergence,
    electrode_pair_in_grounded_box,
    electrode_pair_mesh_study,
    parallel_plate_benchmark,
    verify_plate_force_virtual_work,
)
from electrostatics_numerics import (
    evaluate_whole_apparatus_force_budget,
    force_mesh_convergence_study,
)

REPO_ROOT = Path(__file__).resolve().parent
BASELINE_PATH = REPO_ROOT / "electrostatics_baseline.py"
NUMERICS_PATH = REPO_ROOT / "electrostatics_numerics.py"

EXPECTED_BASELINE_BLOB_SHA1 = "97f65dfa25db7730323edd5e52c98b17371fdeaa"
EXPECTED_NUMERICS_BLOB_SHA1 = "a29f1f3a55946f33760179677dd3dbeb6a2ebde2"

MAX_SAFE_INTEGER = (1 << 53) - 1
ALLOWED_GRID_SIZES: tuple[int, ...] = (41, 81, 101)
REQUIRED_STUDY_N_LIST: tuple[int, int, int] = (41, 81, 101)
SINGLE_SOLVE_FORCE_TOLERANCE_N_PER_M = 1e-4
WHOLE_BODY_THRUST_STATUS = "NOT MEASURED / NOT ESTABLISHED"

V1_PRESETS: dict[str, dict[str, Any]] = {
    "p0_p1_canonical_40mm": {
        "n": 101,
        "box_width_m": 0.040,
        "left_electrode": {
            "center_x_m": -0.008,
            "center_y_m": 0.0,
            "radius_m": 0.003,
            "voltage_v": 500.0,
        },
        "right_electrode": {
            "center_x_m": 0.008,
            "center_y_m": 0.0,
            "radius_m": 0.003,
            "voltage_v": -500.0,
        },
        "probe_xy_m": [0.0, 0.0],
        "gap_range_mm": [6.0, 16.0],
    },
    "asymmetric_hv_80mm_bench": {
        "n": 101,
        "box_width_m": 0.080,
        "left_electrode": {
            "center_x_m": -0.015,
            "center_y_m": 0.0,
            "radius_m": 0.007,
            "voltage_v": -20000.0,
        },
        "right_electrode": {
            "center_x_m": 0.015,
            "center_y_m": 0.0,
            "radius_m": 0.007,
            "voltage_v": 0.0,
        },
        "probe_xy_m": [0.0, 0.0],
        "gap_range_mm": [12.0, 28.0],
    },
    "bipolar_hv_80mm_bench": {
        "n": 101,
        "box_width_m": 0.080,
        "left_electrode": {
            "center_x_m": -0.015,
            "center_y_m": 0.0,
            "radius_m": 0.007,
            "voltage_v": -10000.0,
        },
        "right_electrode": {
            "center_x_m": 0.015,
            "center_y_m": 0.0,
            "radius_m": 0.007,
            "voltage_v": 10000.0,
        },
        "probe_xy_m": [0.0, 0.0],
        "gap_range_mm": [12.0, 28.0],
    },
}


class SchemaValidationError(Exception):
    """Structured client-visible validation error for V1 solver endpoints."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        field: str | None = None,
        request_id: int | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.field = field
        self.request_id = request_id

    def to_error_payload(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "field": self.field,
            },
            "request_id": self.request_id,
        }


def compute_git_blob_sha1(path: Path) -> str:
    """Compute exact git blob SHA-1 for `path` without invoking git subprocess."""
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def verify_frozen_kernel_hashes() -> dict[str, str]:
    """Fail-closed verification that P0 and P1 kernel blobs match frozen baselines."""
    baseline_sha1 = compute_git_blob_sha1(BASELINE_PATH)
    numerics_sha1 = compute_git_blob_sha1(NUMERICS_PATH)
    if baseline_sha1 != EXPECTED_BASELINE_BLOB_SHA1:
        raise RuntimeError(
            f"Frozen P0 kernel hash mismatch: expected {EXPECTED_BASELINE_BLOB_SHA1}, got {baseline_sha1}"
        )
    if numerics_sha1 != EXPECTED_NUMERICS_BLOB_SHA1:
        raise RuntimeError(
            f"Frozen P1 kernel hash mismatch: expected {EXPECTED_NUMERICS_BLOB_SHA1}, got {numerics_sha1}"
        )
    return {
        "electrostatics_baseline": baseline_sha1,
        "electrostatics_numerics": numerics_sha1,
    }


@lru_cache(maxsize=1)
def resolve_source_head_sha() -> str:
    """Return current repository HEAD commit SHA (or env override) with safe fallback."""
    env_sha = os.environ.get("V1_SOURCE_HEAD_SHA")
    if env_sha:
        return env_sha.strip()
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(REPO_ROOT),
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2.0,
        )
        return out.strip() or "unknown"
    except Exception:  # noqa: BLE001
        return "unknown"


def verify_worker_startup_invariants() -> None:
    """Called by isolated V1-B worker prior to publishing READY handshake."""
    verify_frozen_kernel_hashes()
    resolve_source_head_sha()


def strict_rfc8259_dumps(obj: Any) -> str:
    """Serialize strictly to RFC 8259 JSON, forbidding NaN/Infinity."""
    return json.dumps(obj, allow_nan=False, separators=(",", ":"))


def _parse_json_int(value: Any, *, field: str, request_id: int | None) -> int:
    """Accept finite integer-valued JSON numbers; reject bool, non-int floats, and non-numbers."""
    if isinstance(value, bool):
        raise SchemaValidationError(400, "INVALID_SCHEMA", f"Field {field!r} must be integer, got bool", field=field, request_id=request_id)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            raise SchemaValidationError(
                400,
                "INVALID_SCHEMA",
                f"Field {field!r} must be a finite integer value",
                field=field,
                request_id=request_id,
            )
        return int(value)
    raise SchemaValidationError(
        400,
        "INVALID_SCHEMA",
        f"Field {field!r} must be an integer",
        field=field,
        request_id=request_id,
    )


def _parse_json_float(
    value: Any,
    *,
    field: str,
    request_id: int | None,
    min_val: float | None = None,
    max_val: float | None = None,
) -> float:
    """Accept finite JSON numbers (`int` or `float`, rejecting `bool`) normalized `-0.0 -> +0.0`."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SchemaValidationError(
            400,
            "INVALID_SCHEMA",
            f"Field {field!r} must be a finite number",
            field=field,
            request_id=request_id,
        )
    try:
        fval = float(value)
    except (OverflowError, TypeError, ValueError) as exc:
        raise SchemaValidationError(
            400,
            "INVALID_SCHEMA",
            f"Field {field!r} exceeds IEEE-754 finite float64 range",
            field=field,
            request_id=request_id,
        ) from exc
    if not math.isfinite(fval):
        raise SchemaValidationError(
            400,
            "INVALID_SCHEMA",
            f"Field {field!r} must be finite",
            field=field,
            request_id=request_id,
        )
    if fval == 0.0:
        fval = 0.0
    if min_val is not None and fval < min_val:
        raise SchemaValidationError(
            400,
            "INVALID_SCHEMA",
            f"Field {field!r} ({fval}) below minimum {min_val}",
            field=field,
            request_id=request_id,
        )
    if max_val is not None and fval > max_val:
        raise SchemaValidationError(
            400,
            "INVALID_SCHEMA",
            f"Field {field!r} ({fval}) above maximum {max_val}",
            field=field,
            request_id=request_id,
        )
    return fval


def _extract_valid_request_id(payload: Any) -> int | None:
    if not isinstance(payload, dict):
        return None
    raw = payload.get("request_id")
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int) and 1 <= raw <= MAX_SAFE_INTEGER:
        return raw
    if isinstance(raw, float) and math.isfinite(raw) and raw.is_integer():
        ival = int(raw)
        if 1 <= ival <= MAX_SAFE_INTEGER:
            return ival
    return None


def _reject_extra_keys(obj: dict[str, Any], allowed: set[str], *, context: str, request_id: int | None) -> None:
    for key in obj:
        if key not in allowed:
            raise SchemaValidationError(
                400,
                "INVALID_SCHEMA",
                f"Unknown field {key!r} in {context}",
                field=key,
                request_id=request_id,
            )


def _normalize_electrode(raw: Any, *, field_prefix: str, request_id: int | None) -> dict[str, float]:
    if not isinstance(raw, dict):
        raise SchemaValidationError(
            400,
            "INVALID_SCHEMA",
            f"Field {field_prefix!r} must be a JSON object",
            field=field_prefix,
            request_id=request_id,
        )
    required = {"center_x_m", "center_y_m", "radius_m", "voltage_v"}
    _reject_extra_keys(raw, required, context=field_prefix, request_id=request_id)
    for k in required:
        if k not in raw:
            raise SchemaValidationError(
                400,
                "INVALID_SCHEMA",
                f"Missing required field {field_prefix}.{k}",
                field=f"{field_prefix}.{k}",
                request_id=request_id,
            )
    return {
        "center_x_m": _parse_json_float(raw["center_x_m"], field=f"{field_prefix}.center_x_m", request_id=request_id),
        "center_y_m": _parse_json_float(raw["center_y_m"], field=f"{field_prefix}.center_y_m", request_id=request_id),
        "radius_m": _parse_json_float(
            raw["radius_m"],
            field=f"{field_prefix}.radius_m",
            request_id=request_id,
            min_val=0.0015,
            max_val=0.015,
        ),
        "voltage_v": _parse_json_float(
            raw["voltage_v"],
            field=f"{field_prefix}.voltage_v",
            request_id=request_id,
            min_val=-50000.0,
            max_val=50000.0,
        ),
    }


def check_presolve_domain_eligibility(
    params: dict[str, Any],
    *,
    n_override: int | None = None,
    request_id: int | None = None,
) -> tuple[bool, str | None]:
    """Enforce Section 3.1 pre-solve grid-resolved domain eligibility for `grounded_box_2d`."""
    n_val = n_override if n_override is not None else int(params["n"])
    if n_val not in ALLOWED_GRID_SIZES:
        return False, f"Unsupported resolution n={n_val}; expected one of {ALLOWED_GRID_SIZES}"

    w = float(params["box_width_m"])
    half_w = w / 2.0
    h = w / (n_val - 1)
    le = params["left_electrode"]
    re = params["right_electrode"]

    le_cx, le_cy, le_r = float(le["center_x_m"]), float(le["center_y_m"]), float(le["radius_m"])
    re_cx, re_cy, re_r = float(re["center_x_m"]), float(re["center_y_m"]), float(re["radius_m"])

    # Verify continuous box bounds & off-axis UI bound
    if abs(le_cy) > w / 4.0 or abs(re_cy) > w / 4.0:
        return False, f"Electrode |center_y_m| exceeds bounded off-axis limit W/4={w / 4.0:.6g} m"
    if min(le_r, re_r) < 3.0 * h:
        return False, f"Electrode radius min({le_r:.6g}, {re_r:.6g}) < 3h ({3.0 * h:.6g} m) at n={n_val}"

    # Canonical left-to-right x-projected separation >= 6h (prevents swapped/diagonal contour failure)
    x_gap = (re_cx - re_r) - (le_cx + le_r)
    if x_gap < 6.0 * h:
        return (
            False,
            f"Canonical x-projected separation ({x_gap:.6g} m) < 6h ({6.0 * h:.6g} m) at n={n_val}",
        )

    for label, cx, cy, rad in (("left_electrode", le_cx, le_cy, le_r), ("right_electrode", re_cx, re_cy, re_r)):
        wx = half_w - (abs(cx) + rad)
        wy = half_w - (abs(cy) + rad)
        if wx < 6.0 * h or wy < 6.0 * h:
            return (
                False,
                f"{label} wall clearance (x={wx:.6g} m, y={wy:.6g} m) < 6h ({6.0 * h:.6g} m) at n={n_val}",
            )

    # Verify continuous GroundedBoxConfig preconditions cleanly
    try:
        GroundedBoxConfig(
            n=n_val,
            box_width_m=w,
            left_electrode=ElectrodeConfig(le_cx, le_cy, le_r, float(le["voltage_v"])),
            right_electrode=ElectrodeConfig(re_cx, re_cy, re_r, float(re["voltage_v"])),
        )
    except ValueError as exc:
        return False, str(exc)

    return True, None


def validate_and_normalize_request(endpoint: str | None, payload: Any) -> dict[str, Any]:
    """Strictly validate request payload and return normalized canonical parameters."""
    if endpoint not in ("/api/v1/solve", "/api/v1/study"):
        raise SchemaValidationError(404, "NOT_FOUND", f"Unknown API endpoint: {endpoint}", field="endpoint")

    if not isinstance(payload, dict):
        raise SchemaValidationError(400, "INVALID_SCHEMA", "Request body must be a JSON object")

    req_id = _extract_valid_request_id(payload)
    if "request_id" not in payload:
        raise SchemaValidationError(400, "INVALID_SCHEMA", "Missing required field 'request_id'", field="request_id")
    parsed_req_id = _parse_json_int(payload["request_id"], field="request_id", request_id=req_id)
    if parsed_req_id < 1 or parsed_req_id > MAX_SAFE_INTEGER:
        raise SchemaValidationError(
            400,
            "INVALID_SCHEMA",
            f"'request_id' must be in [1, {MAX_SAFE_INTEGER}]",
            field="request_id",
            request_id=None,
        )
    req_id = parsed_req_id

    if endpoint == "/api/v1/solve" and "study_n_list" in payload:
        raise SchemaValidationError(
            400,
            "UNSUPPORTED_FIELD_FOR_ENDPOINT",
            "'study_n_list' is only permitted on /api/v1/study",
            field="study_n_list",
            request_id=req_id,
        )
    if endpoint == "/api/v1/study" and "include_convergence_study" in payload:
        raise SchemaValidationError(
            400,
            "UNSUPPORTED_FIELD_FOR_ENDPOINT",
            "'include_convergence_study' is rejected on /api/v1/study",
            field="include_convergence_study",
            request_id=req_id,
        )

    mode = payload.get("mode")
    if mode not in ("parallel_plate_1d", "grounded_box_2d"):
        raise SchemaValidationError(
            400,
            "INVALID_SCHEMA",
            "Field 'mode' must be 'parallel_plate_1d' or 'grounded_box_2d'",
            field="mode",
            request_id=req_id,
        )
    if endpoint == "/api/v1/study" and mode != "grounded_box_2d":
        raise SchemaValidationError(
            400,
            "INVALID_SCHEMA",
            "/api/v1/study requires mode='grounded_box_2d'",
            field="mode",
            request_id=req_id,
        )

    raw_params = payload.get("parameters")
    if not isinstance(raw_params, dict):
        raise SchemaValidationError(
            400,
            "INVALID_SCHEMA",
            "Field 'parameters' must be a JSON object",
            field="parameters",
            request_id=req_id,
        )

    if mode == "parallel_plate_1d":
        allowed_top = {"request_id", "mode", "parameters"}
        for extra in ("probe_xy_m", "include_convergence_study"):
            if extra in payload:
                raise SchemaValidationError(
                    400,
                    "UNSUPPORTED_FIELD_FOR_MODE",
                    f"Field {extra!r} is not supported in parallel_plate_1d mode",
                    field=extra,
                    request_id=req_id,
                )
        _reject_extra_keys(payload, allowed_top, context="solve request", request_id=req_id)

        req_1d = {"voltage_v", "gap_m", "area_m2"}
        _reject_extra_keys(raw_params, req_1d, context="parameters", request_id=req_id)
        for k in req_1d:
            if k not in raw_params:
                raise SchemaValidationError(
                    400,
                    "INVALID_SCHEMA",
                    f"Missing required field parameters.{k}",
                    field=f"parameters.{k}",
                    request_id=req_id,
                )
        norm_params = {
            "voltage_v": _parse_json_float(
                raw_params["voltage_v"], field="parameters.voltage_v", request_id=req_id, min_val=0.0, max_val=50000.0
            ),
            "gap_m": _parse_json_float(
                raw_params["gap_m"], field="parameters.gap_m", request_id=req_id, min_val=0.005, max_val=0.200
            ),
            "area_m2": _parse_json_float(
                raw_params["area_m2"], field="parameters.area_m2", request_id=req_id, min_val=1e-4, max_val=0.05
            ),
        }
        return {
            "endpoint": "solve",
            "request_id": req_id,
            "mode": mode,
            "parameters": norm_params,
        }

    # grounded_box_2d (/api/v1/solve or /api/v1/study)
    allowed_top = (
        {"request_id", "mode", "parameters", "probe_xy_m", "include_convergence_study"}
        if endpoint == "/api/v1/solve"
        else {"request_id", "mode", "parameters", "probe_xy_m", "study_n_list"}
    )
    _reject_extra_keys(payload, allowed_top, context=f"{endpoint} request", request_id=req_id)

    req_2d = {"n", "box_width_m", "left_electrode", "right_electrode"}
    _reject_extra_keys(raw_params, req_2d, context="parameters", request_id=req_id)
    for k in req_2d:
        if k not in raw_params:
            raise SchemaValidationError(
                400,
                "INVALID_SCHEMA",
                f"Missing required field parameters.{k}",
                field=f"parameters.{k}",
                request_id=req_id,
            )

    n_val = _parse_json_int(raw_params["n"], field="parameters.n", request_id=req_id)
    if n_val not in ALLOWED_GRID_SIZES:
        raise SchemaValidationError(
            400,
            "INVALID_SCHEMA",
            f"Field 'parameters.n' must be one of {ALLOWED_GRID_SIZES}, got {n_val}",
            field="parameters.n",
            request_id=req_id,
        )
    box_width_m = _parse_json_float(
        raw_params["box_width_m"],
        field="parameters.box_width_m",
        request_id=req_id,
        min_val=0.04,
        max_val=0.20,
    )
    norm_params = {
        "n": n_val,
        "box_width_m": box_width_m,
        "left_electrode": _normalize_electrode(
            raw_params["left_electrode"], field_prefix="parameters.left_electrode", request_id=req_id
        ),
        "right_electrode": _normalize_electrode(
            raw_params["right_electrode"], field_prefix="parameters.right_electrode", request_id=req_id
        ),
    }

    probe_raw = payload.get("probe_xy_m", [0.0, 0.0])
    if not isinstance(probe_raw, list) or len(probe_raw) != 2:
        raise SchemaValidationError(
            400,
            "INVALID_PROBE_COORDS",
            "Field 'probe_xy_m' must be a 2-element array [x_m, y_m]",
            field="probe_xy_m",
            request_id=req_id,
        )
    px = _parse_json_float(probe_raw[0], field="probe_xy_m[0]", request_id=req_id)
    py = _parse_json_float(probe_raw[1], field="probe_xy_m[1]", request_id=req_id)
    half_w = box_width_m / 2.0
    if abs(px) > half_w or abs(py) > half_w:
        raise SchemaValidationError(
            400,
            "INVALID_PROBE_COORDS",
            f"Probe coordinates [{px}, {py}] lie outside [-{half_w}, {half_w}]^2",
            field="probe_xy_m",
            request_id=req_id,
        )

    if endpoint == "/api/v1/solve":
        inc_study = payload.get("include_convergence_study", False)
        if not isinstance(inc_study, bool):
            raise SchemaValidationError(
                400,
                "INVALID_SCHEMA",
                "Field 'include_convergence_study' must be boolean",
                field="include_convergence_study",
                request_id=req_id,
            )
        eligible, reason = check_presolve_domain_eligibility(norm_params)
        if not eligible:
            raise SchemaValidationError(
                400,
                "INVALID_FORCE_DOMAIN",
                reason or "Configuration violates pre-solve domain eligibility",
                field="parameters",
                request_id=req_id,
            )
        return {
            "endpoint": "solve",
            "request_id": req_id,
            "mode": mode,
            "parameters": norm_params,
            "probe_xy_m": [px, py],
            "include_convergence_study": inc_study,
        }

    # /api/v1/study
    study_n_raw = payload.get("study_n_list", list(REQUIRED_STUDY_N_LIST))
    if not isinstance(study_n_raw, list) or len(study_n_raw) != len(REQUIRED_STUDY_N_LIST):
        raise SchemaValidationError(
            400,
            "INVALID_SCHEMA",
            f"Field 'study_n_list' must equal {list(REQUIRED_STUDY_N_LIST)}",
            field="study_n_list",
            request_id=req_id,
        )
    study_n_list = [
        _parse_json_int(item, field=f"study_n_list[{idx}]", request_id=req_id)
        for idx, item in enumerate(study_n_raw)
    ]
    if tuple(study_n_list) != REQUIRED_STUDY_N_LIST:
        raise SchemaValidationError(
            400,
            "INVALID_SCHEMA",
            f"Field 'study_n_list' must equal {list(REQUIRED_STUDY_N_LIST)}, got {study_n_list}",
            field="study_n_list",
            request_id=req_id,
        )

    # Check continuous / canonical domain invariants BEFORE execution on /study
    # (coarse mesh-level 3h/6h checks happen per-level inside study gating returning 200 WITHHELD_*)
    le = norm_params["left_electrode"]
    re = norm_params["right_electrode"]
    if abs(le["center_y_m"]) > box_width_m / 4.0 or abs(re["center_y_m"]) > box_width_m / 4.0:
        raise SchemaValidationError(
            400,
            "INVALID_FORCE_DOMAIN",
            f"Electrode |center_y_m| exceeds bounded off-axis limit W/4={box_width_m / 4.0:.6g} m",
            field="parameters",
            request_id=req_id,
        )
    if (re["center_x_m"] - re["radius_m"]) <= (le["center_x_m"] + le["radius_m"]):
        raise SchemaValidationError(
            400,
            "INVALID_FORCE_DOMAIN",
            "Electrodes must satisfy non-overlapping left-to-right x-ordering",
            field="parameters",
            request_id=req_id,
        )
    try:
        GroundedBoxConfig(
            n=n_val,
            box_width_m=box_width_m,
            left_electrode=ElectrodeConfig(**le),
            right_electrode=ElectrodeConfig(**re),
        )
    except ValueError as exc:
        raise SchemaValidationError(
            400,
            "INVALID_FORCE_DOMAIN",
            str(exc),
            field="parameters",
            request_id=req_id,
        ) from exc

    return {
        "endpoint": "study",
        "request_id": req_id,
        "mode": mode,
        "parameters": norm_params,
        "probe_xy_m": [px, py],
        "study_n_list": study_n_list,
    }


def _encode_f64(value: float) -> str:
    norm = 0.0 if value == 0.0 else float(value)
    return f"f64:{struct.pack('>d', norm).hex()}"


def _encode_i(value: int) -> str:
    return f"i:{int(value)}"


def _encode_b(value: bool) -> str:
    return "b:true" if value else "b:false"


def _encode_s(value: str) -> str:
    return f"s:{value}"


def build_canonical_fingerprint_ascii(normalized_req: dict[str, Any]) -> str:
    """Build exact canonical ASCII line serialization specified in V1 Spec Section 4.1."""
    ep = normalized_req["endpoint"]
    mode = normalized_req["mode"]
    p = normalized_req["parameters"]

    if ep == "solve" and mode == "parallel_plate_1d":
        lines = (
            "v=1",
            f"endpoint={_encode_s('solve')}",
            f"mode={_encode_s('parallel_plate_1d')}",
            f"parameters.area_m2={_encode_f64(p['area_m2'])}",
            f"parameters.gap_m={_encode_f64(p['gap_m'])}",
            f"parameters.voltage_v={_encode_f64(p['voltage_v'])}",
        )
        return "\n".join(lines)

    le = p["left_electrode"]
    re = p["right_electrode"]
    probe = normalized_req["probe_xy_m"]

    if ep == "solve" and mode == "grounded_box_2d":
        lines = (
            "v=1",
            f"endpoint={_encode_s('solve')}",
            f"mode={_encode_s('grounded_box_2d')}",
            f"include_convergence_study={_encode_b(normalized_req['include_convergence_study'])}",
            f"parameters.box_width_m={_encode_f64(p['box_width_m'])}",
            f"parameters.left_electrode.center_x_m={_encode_f64(le['center_x_m'])}",
            f"parameters.left_electrode.center_y_m={_encode_f64(le['center_y_m'])}",
            f"parameters.left_electrode.radius_m={_encode_f64(le['radius_m'])}",
            f"parameters.left_electrode.voltage_v={_encode_f64(le['voltage_v'])}",
            f"parameters.n={_encode_i(p['n'])}",
            f"parameters.right_electrode.center_x_m={_encode_f64(re['center_x_m'])}",
            f"parameters.right_electrode.center_y_m={_encode_f64(re['center_y_m'])}",
            f"parameters.right_electrode.radius_m={_encode_f64(re['radius_m'])}",
            f"parameters.right_electrode.voltage_v={_encode_f64(re['voltage_v'])}",
            f"probe_xy_m=[{_encode_f64(probe[0])},{_encode_f64(probe[1])}]",
        )
        return "\n".join(lines)

    if ep == "study" and mode == "grounded_box_2d":
        study_items = ",".join(_encode_i(val) for val in normalized_req["study_n_list"])
        lines = (
            "v=1",
            f"endpoint={_encode_s('study')}",
            f"mode={_encode_s('grounded_box_2d')}",
            f"parameters.box_width_m={_encode_f64(p['box_width_m'])}",
            f"parameters.left_electrode.center_x_m={_encode_f64(le['center_x_m'])}",
            f"parameters.left_electrode.center_y_m={_encode_f64(le['center_y_m'])}",
            f"parameters.left_electrode.radius_m={_encode_f64(le['radius_m'])}",
            f"parameters.left_electrode.voltage_v={_encode_f64(le['voltage_v'])}",
            f"parameters.n={_encode_i(p['n'])}",
            f"parameters.right_electrode.center_x_m={_encode_f64(re['center_x_m'])}",
            f"parameters.right_electrode.center_y_m={_encode_f64(re['center_y_m'])}",
            f"parameters.right_electrode.radius_m={_encode_f64(re['radius_m'])}",
            f"parameters.right_electrode.voltage_v={_encode_f64(re['voltage_v'])}",
            f"probe_xy_m=[{_encode_f64(probe[0])},{_encode_f64(probe[1])}]",
            f"study_n_list=[{study_items}]",
        )
        return "\n".join(lines)

    raise ValueError(f"Unsupported normalized request combination: ({ep}, {mode})")


def compute_input_fingerprint(normalized_req: dict[str, Any]) -> str:
    """Compute exact UTF-8 SHA-256 canonical input_fingerprint excluding request_id."""
    ascii_repr = build_canonical_fingerprint_ascii(normalized_req)
    return hashlib.sha256(ascii_repr.encode("utf-8")).hexdigest()


def validate_snapped_contour_topology(
    sol: FieldSolution,
    cfg: GroundedBoxConfig,
) -> tuple[bool, str | None]:
    """Post-solve kernel-matched snapped-contour topology gate (explicit runtime checks, never assert).

    Recomputes `coords_mask` independently from `coords_contour = linspace(-w_contour/2, w_contour/2, n)`
    with `w_contour = (n - 1) * sol.grid_spacing_m` so IEEE-754 half-cell rounding ties match
    `compute_maxwell_stress_contour` identically.
    """
    n = int(cfg.n)
    w = float(cfg.box_width_m)
    le = cfg.left_electrode
    re = cfg.right_electrode

    if sol.potential_v.shape != (n, n) or sol.vacuum_mask.shape != (n, n):
        return False, "FieldSolution array shapes do not match GroundedBoxConfig"

    # Mask coordinates matching electrostatics_baseline.py L488-491
    coords_mask = np.linspace(-w / 2.0, w / 2.0, n)
    gx, gy = np.meshgrid(coords_mask, coords_mask, indexing="ij")
    left_mask = (gx - le.center_x_m) ** 2 + (gy - le.center_y_m) ** 2 <= le.radius_m**2
    right_mask = (gx - re.center_x_m) ** 2 + (gy - re.center_y_m) ** 2 <= re.radius_m**2

    if not bool(np.any(left_mask)):
        return False, "left_mask contains zero conductor nodes"
    if not bool(np.any(right_mask)):
        return False, "right_mask contains zero conductor nodes"
    if bool(np.any(left_mask & right_mask)):
        return False, "left_mask and right_mask overlap on discrete grid"
    if not bool(np.array_equal(left_mask | right_mask, sol.conductor_mask)):
        return False, "Discrete union left_mask | right_mask does not match sol.conductor_mask"
    if bool(np.any(sol.conductor_mask & sol.boundary_mask)):
        return False, "sol.conductor_mask overlaps sol.boundary_mask"

    # Contour coordinates matching electrostatics_numerics.py L293-301
    h_sol = float(sol.grid_spacing_m)
    w_contour = (n - 1) * h_sol
    coords_contour = np.linspace(-w_contour / 2.0, w_contour / 2.0, n)

    sep = abs(re.center_x_m - le.center_x_m)
    d_inter = sep - (le.radius_m + re.radius_m)
    d_left_wall = (le.center_x_m - le.radius_m) - (-w / 2.0)
    d_right_wall = (w / 2.0) - (re.center_x_m + re.radius_m)
    d_vert = (w / 2.0) - max(abs(le.center_y_m) + le.radius_m, abs(re.center_y_m) + re.radius_m)

    margin_x = max(min(d_inter * 0.35, d_left_wall * 0.35, d_right_wall * 0.35, 0.003), 1.5 * h_sol)
    margin_y = max(min(d_vert * 0.35, 0.003), 1.5 * h_sol)
    wall_margin = 2.5 * h_sol

    def _snap(x_lo: float, x_hi: float, y_lo: float, y_hi: float) -> tuple[int, int, int, int]:
        ix0 = int(np.clip(np.argmin(np.abs(coords_contour - x_lo)), 1, n - 2))
        ix1 = int(np.clip(np.argmin(np.abs(coords_contour - x_hi)), 1, n - 2))
        iy0 = int(np.clip(np.argmin(np.abs(coords_contour - y_lo)), 1, n - 2))
        iy1 = int(np.clip(np.argmin(np.abs(coords_contour - y_hi)), 1, n - 2))
        return ix0, ix1, iy0, iy1

    c_left = _snap(
        le.center_x_m - le.radius_m - margin_x,
        le.center_x_m + le.radius_m + margin_x,
        le.center_y_m - le.radius_m - margin_y,
        le.center_y_m + le.radius_m + margin_y,
    )
    c_right = _snap(
        re.center_x_m - re.radius_m - margin_x,
        re.center_x_m + re.radius_m + margin_x,
        re.center_y_m - re.radius_m - margin_y,
        re.center_y_m + re.radius_m + margin_y,
    )
    c_enc = _snap(
        -w / 2.0 + wall_margin,
        w / 2.0 - wall_margin,
        -w / 2.0 + wall_margin,
        w / 2.0 - wall_margin,
    )

    interiors: dict[str, np.ndarray] = {}
    for cname, box in (("c_left", c_left), ("c_right", c_right), ("c_enclosure_inner", c_enc)):
        x0, x1, y0, y1 = box
        if x0 >= x1 or y0 >= y1:
            return False, f"Snapped contour {cname} has empty interior {box}"
        if not bool(
            np.all(sol.vacuum_mask[x1, y0 : y1 + 1])
            and np.all(sol.vacuum_mask[x0, y0 : y1 + 1])
            and np.all(sol.vacuum_mask[x0 : x1 + 1, y1])
            and np.all(sol.vacuum_mask[x0 : x1 + 1, y0])
        ):
            return False, f"Snapped contour {cname} perimeter intersects non-vacuum node"
        inside = np.zeros((n, n), dtype=bool)
        inside[x0 + 1 : x1, y0 + 1 : y1] = True
        interiors[cname] = inside

    in_l = interiors["c_left"]
    in_r = interiors["c_right"]
    in_e = interiors["c_enclosure_inner"]

    if int(np.sum(left_mask & ~in_l)) != 0:
        return False, "c_left fails to enclose all left_mask nodes"
    if int(np.sum((right_mask | sol.boundary_mask) & in_l)) != 0:
        return False, "c_left interior captures right_mask or boundary_mask nodes"
    if int(np.sum(right_mask & ~in_r)) != 0:
        return False, "c_right fails to enclose all right_mask nodes"
    if int(np.sum((left_mask | sol.boundary_mask) & in_r)) != 0:
        return False, "c_right interior captures left_mask or boundary_mask nodes"
    if int(np.sum(sol.conductor_mask & ~in_e)) != 0:
        return False, "c_enclosure_inner fails to enclose all conductor_mask nodes"
    if int(np.sum(sol.boundary_mask & in_e)) != 0:
        return False, "c_enclosure_inner interior captures boundary_mask nodes"

    x0_l, x1_l, y0_l, y1_l = c_left
    x0_r, x1_r, y0_r, y1_r = c_right
    x0_e, x1_e, y0_e, y1_e = c_enc

    disjoint = (x1_l < x0_r) or (x1_r < x0_l) or (y1_l < y0_r) or (y1_r < y0_l)
    if not disjoint:
        return False, f"c_left {c_left} and c_right {c_right} contours are not strictly disjoint"
    if not (x0_e < x0_l and x1_l < x1_e and y0_e < y0_l and y1_l < y1_e):
        return False, f"c_left {c_left} is not strictly inside c_enclosure_inner {c_enc}"
    if not (x0_e < x0_r and x1_r < x1_e and y0_e < y0_r and y1_r < y1_e):
        return False, f"c_right {c_right} is not strictly inside c_enclosure_inner {c_enc}"

    return True, None


def _build_provenance(module: str, function: str) -> dict[str, Any]:
    kernel_hashes = verify_frozen_kernel_hashes()
    return {
        "module": module,
        "function": function,
        "source_head_sha": resolve_source_head_sha(),
        "kernel_blob_sha1": kernel_hashes,
        "whole_body_thrust_status": WHOLE_BODY_THRUST_STATUS,
    }


def _run_parallel_plate_1d(norm_req: dict[str, Any], input_fp: str) -> dict[str, Any]:
    p = norm_req["parameters"]
    v = p["voltage_v"]
    d = p["gap_m"]
    area = p["area_m2"]

    bench = parallel_plate_benchmark(voltage_v=v, gap_m=d, area_m2=area)
    vw = verify_plate_force_virtual_work(voltage_v=v, gap_m=d, area_m2=area)
    aspect_ratio = math.sqrt(area) / d
    fringing_warning = bool(aspect_ratio < 5.0)

    return {
        "request_id": norm_req["request_id"],
        "input_fingerprint": input_fp,
        "model_id": "parallel_plate_1d",
        "epistemic_label": "ESTABLISHED MODEL",
        "parameters": p,
        "constants": {"epsilon_0_f_per_m": EPSILON_0_F_PER_M},
        "provenance": _build_provenance(
            "electrostatics_baseline",
            "parallel_plate_benchmark + verify_plate_force_virtual_work",
        ),
        "uncertainty_and_limits": {
            "geometry_family": "ideal_infinite_parallel_plate_1d",
            "assumptions": [
                "Infinite planar ideal conductors separated by vacuum gap d (epsilon_r = 1.0).",
                "Zero edge fringing fields; uniform normal field E = V / d.",
                "Equal and opposite internal electrostatic attraction sums strictly to net_pair_force_n = 0.0 N.",
            ],
            "validity_notes": [
                "Not a 3D Exodus knife-edge blade or finite dielectric solver.",
                "Valid approximation only when plate lateral extent sqrt(A) >> gap d."
                + (
                    f" WARNING: sqrt(A)/d = {aspect_ratio:.3f} < 5.0 indicates significant edge fringing is neglected."
                    if fringing_warning
                    else ""
                ),
            ],
        },
        "electric_field_v_per_m": float(bench.electric_field_v_per_m),
        "pressure_pa": float(bench.pressure_pa),
        "force_on_positive_plate_n": float(bench.force_on_positive_plate_n),
        "force_on_negative_plate_n": float(bench.force_on_negative_plate_n),
        "net_pair_force_n": float(bench.net_pair_force_n),
        "stored_energy_j": float(bench.stored_energy_j),
        "virtual_work": {key: float(val) for key, val in vw.items()},
        "fringing_aspect_ratio": float(aspect_ratio),
        "fringing_warning": fringing_warning,
        "force_mesh_sensitivity_status": "NOT_APPLICABLE_ANALYTIC_1D",
        "probe_stability_status": "NOT_APPLICABLE_ANALYTIC_1D",
    }


def _evaluate_dual_probe(sol: FieldSolution, cfg: GroundedBoxConfig, probe_xy: list[float]) -> dict[str, Any]:
    px, py = float(probe_xy[0]), float(probe_xy[1])
    coords_mask = np.linspace(-cfg.box_width_m / 2.0, cfg.box_width_m / 2.0, cfg.n)
    ix = int(np.argmin(np.abs(coords_mask - px)))
    iy = int(np.argmin(np.abs(coords_mask - py)))

    half_w = cfg.box_width_m / 2.0
    le = cfg.left_electrode
    re = cfg.right_electrode

    d_left_sq = (px - le.center_x_m) ** 2 + (py - le.center_y_m) ** 2
    d_right_sq = (px - re.center_x_m) ** 2 + (py - re.center_y_m) ** 2
    in_left = bool(d_left_sq <= le.radius_m**2)
    in_right = bool(d_right_sq <= re.radius_m**2)
    in_boundary = bool(abs(px) >= half_w or abs(py) >= half_w)
    requested_in_vac = bool(not (in_left or in_right or in_boundary))
    sampled_in_vac = bool(sol.vacuum_mask[ix, iy])
    probe_in_vac = bool(requested_in_vac and sampled_in_vac)

    sampled_potential = float(sol.potential_v[ix, iy])
    if probe_in_vac:
        ex_val: float | None = float(sol.ex_v_per_m[ix, iy])
        ey_val: float | None = float(sol.ey_v_per_m[ix, iy])
        status = "VALID_VACUUM"
        detail = "Both requested probe coordinates and nearest lattice node lie strictly in vacuum."
    else:
        ex_val = None
        ey_val = None
        status = "NON_VACUUM"
        if not requested_in_vac:
            region = "left_electrode" if in_left else ("right_electrode" if in_right else "grounded_boundary")
            detail = f"Requested probe [{px:.6g}, {py:.6g}] lies inside {region}; vacuum E-field undefined (null)."
        else:
            detail = (
                f"Requested probe [{px:.6g}, {py:.6g}] snapped to non-vacuum lattice node "
                f"[{float(coords_mask[ix]):.6g}, {float(coords_mask[iy]):.6g}]; vacuum E-field undefined (null)."
            )

    return {
        "requested_probe_xy_m": [px, py],
        "sampled_probe_xy_m": [float(coords_mask[ix]), float(coords_mask[iy])],
        "requested_probe_in_vacuum": requested_in_vac,
        "sampled_node_in_vacuum": sampled_in_vac,
        "probe_in_vacuum": probe_in_vac,
        "probe_status": status,
        "probe_status_detail": detail,
        "probe_ex_v_per_m": ex_val,
        "probe_ey_v_per_m": ey_val,
        "sampled_node_potential_v": sampled_potential,
        "sampled_node_potential_note": (
            "Sampled potential at nearest discrete lattice node (equals Dirichlet conductor/wall value when snapped outside vacuum)."
        ),
    }


def _serialize_field_solution(sol: FieldSolution, cfg: GroundedBoxConfig) -> dict[str, Any]:
    if not bool(np.all(np.isfinite(sol.potential_v))):
        raise ValueError("Non-finite entries encountered in FieldSolution.potential_v")
    vac = sol.vacuum_mask
    if not bool(np.all(np.isfinite(sol.ex_v_per_m[vac]))) or not bool(np.all(np.isfinite(sol.ey_v_per_m[vac]))):
        raise ValueError("Non-finite vacuum E-field entries encountered")

    vac_list = vac.tolist()
    ex_json = [
        [float(v) if is_vac else None for v, is_vac in zip(row, vrow)]
        for row, vrow in zip(sol.ex_v_per_m.tolist(), vac_list)
    ]
    ey_json = [
        [float(v) if is_vac else None for v, is_vac in zip(row, vrow)]
        for row, vrow in zip(sol.ey_v_per_m.tolist(), vac_list)
    ]
    coords = np.linspace(-cfg.box_width_m / 2.0, cfg.box_width_m / 2.0, cfg.n)
    return {
        "n": int(cfg.n),
        "grid_spacing_m": float(sol.grid_spacing_m),
        "grid_axes": {
            "coords_m": [float(c) for c in coords.tolist()],
            "shape": [int(cfg.n), int(cfg.n)],
            "axis_0": "x_m",
            "axis_1": "y_m",
            "indexing": "ij",
        },
        "potential_v": [[float(v) for v in row] for row in sol.potential_v.tolist()],
        "ex_v_per_m": ex_json,
        "ey_v_per_m": ey_json,
        "vacuum_mask": vac_list,
        "conductor_mask": sol.conductor_mask.tolist(),
        "boundary_mask": sol.boundary_mask.tolist(),
        "max_discrete_stencil_defect_v": float(sol.max_discrete_residual_v),
        "max_discrete_stencil_defect_note": (
            "Post-solve 5-point Laplace discrete stencil residual from direct sparse spsolve (not an iterative tolerance)."
        ),
    }


def build_force_budget_payload(sol: FieldSolution, cfg: GroundedBoxConfig) -> dict[str, Any]:
    """Build full 6-component N/m force budget with strict `<` tolerance check and separated verdict."""
    budget = evaluate_whole_apparatus_force_budget(sol, tolerance_n_per_m=SINGLE_SOLVE_FORCE_TOLERANCE_N_PER_M)
    fx_l = float(budget.left_electrode_fx_n_per_m)
    fy_l = float(budget.left_electrode_fy_n_per_m)
    fx_r = float(budget.right_electrode_fx_n_per_m)
    fy_r = float(budget.right_electrode_fy_n_per_m)
    fx_e = float(budget.enclosure_reaction_fx_n_per_m)
    fy_e = float(budget.enclosure_reaction_fy_n_per_m)
    net_fx = float(budget.net_electrostatic_force_fx_n_per_m)
    net_fy = float(budget.net_electrostatic_force_fy_n_per_m)
    net_norm = float(math.hypot(net_fx, net_fy))

    total_scale = math.hypot(fx_l, fy_l) + math.hypot(fx_r, fy_r) + math.hypot(fx_e, fy_e)
    rel_residual = float(net_norm / total_scale) if total_scale > 0.0 else 0.0

    # Spec Section 3.3(1): strict `<` match (norm == tolerance yields False)
    balanced = bool(net_norm < SINGLE_SOLVE_FORCE_TOLERANCE_N_PER_M)
    closure_status = "BALANCED_WITHIN_TOLERANCE" if balanced else "UNBALANCED_EXCEEDS_TOLERANCE"

    continuum_note = (
        "Continuum Maxwell stress momentum conservation implies F_left + F_right + F_enclosure -> 0 as mesh spacing h -> 0 "
        "over the modeled 2D vacuum domain. Unmodeled rigid mechanical supports/standoffs and high-voltage feedthroughs "
        "balance electrode electrostatic forces on a physical bench."
    )
    discrete_verdict = (
        f"Measured discrete single-grid closure residual |F_net| = {net_norm:.3e} N/m "
        + ("<" if balanced else ">=")
        + f" {SINGLE_SOLVE_FORCE_TOLERANCE_N_PER_M:.1e} N/m ({closure_status}) on n={cfg.n}; "
        + "discretization residuals scale quadratically with voltage magnitude (proportional to V^2) and are NOT physical net thrust."
    )

    return {
        "units": "N/m",
        "left_electrode_fx_n_per_m": fx_l,
        "left_electrode_fy_n_per_m": fy_l,
        "right_electrode_fx_n_per_m": fx_r,
        "right_electrode_fy_n_per_m": fy_r,
        "enclosure_reaction_fx_n_per_m": fx_e,
        "enclosure_reaction_fy_n_per_m": fy_e,
        "net_electrostatic_force_fx_n_per_m": net_fx,
        "net_electrostatic_force_fy_n_per_m": net_fy,
        "net_electrostatic_force_norm_n_per_m": net_norm,
        "relative_closure_residual": rel_residual,
        "tolerance_n_per_m": SINGLE_SOLVE_FORCE_TOLERANCE_N_PER_M,
        "tolerance_scope": "single_solve_1e-4",
        "is_force_balanced_to_tolerance": balanced,
        "force_closure_status": closure_status,
        "continuum_and_unmodeled_supports_note": continuum_note,
        "discrete_closure_verdict": discrete_verdict,
    }


def _evaluate_2d_single(
    sol: FieldSolution,
    cfg: GroundedBoxConfig,
    probe_xy: list[float],
    *,
    params: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None, str, str | None]:
    sol_payload = _serialize_field_solution(sol, cfg)
    probe_payload = _evaluate_dual_probe(sol, cfg, probe_xy)
    if params is not None:
        primary_ok, primary_reason = check_presolve_domain_eligibility(params, n_override=int(cfg.n))
        if not primary_ok:
            return (
                sol_payload,
                probe_payload,
                None,
                "WITHHELD_INELIGIBLE_PRIMARY_GRID",
                primary_reason or f"Primary grid n={cfg.n} violates Section 3.1 pre-solve domain eligibility",
            )
    topo_ok, topo_diag = validate_snapped_contour_topology(sol, cfg)
    if topo_ok:
        fb_payload = build_force_budget_payload(sol, cfg)
        fb_status = "COMPUTED"
        fb_diag = None
    else:
        fb_payload = None
        fb_status = "WITHHELD_INVALID_CONTOUR_TOPOLOGY"
        fb_diag = topo_diag
    return sol_payload, probe_payload, fb_payload, fb_status, fb_diag


def evaluate_post_solve_force_budget_only(
    sol: FieldSolution,
    cfg: GroundedBoxConfig,
) -> tuple[dict[str, Any] | None, str, str | None]:
    """Direct adapter hook testing post-solve topology withholding (independent of Python -O)."""
    topo_ok, topo_diag = validate_snapped_contour_topology(sol, cfg)
    if not topo_ok:
        return None, "WITHHELD_INVALID_CONTOUR_TOPOLOGY", topo_diag
    return build_force_budget_payload(sol, cfg), "COMPUTED", None


def _run_gated_studies(
    norm_req: dict[str, Any],
    study_levels: tuple[int, ...] = REQUIRED_STUDY_N_LIST,
) -> tuple[dict[str, Any], dict[str, Any], str, str]:
    p = norm_req["parameters"]
    probe_xy = norm_req["probe_xy_m"]

    presolve_failures: list[dict[str, Any]] = []
    for lvl in study_levels:
        ok, reason = check_presolve_domain_eligibility(p, n_override=lvl)
        if not ok:
            presolve_failures.append({"n": lvl, "reason": reason})

    if presolve_failures:
        status = "WITHHELD_INELIGIBLE_MESH_LEVEL"
        return (
            {
                "status": status,
                "study_n_list": list(study_levels),
                "failed_levels": presolve_failures,
                "rows": [],
                "derived_sensitivity": None,
            },
            {
                "status": status,
                "study_n_list": list(study_levels),
                "failed_levels": presolve_failures,
                "rows": [],
                "assessment": None,
            },
            status,
            status,
        )

    le_cfg = ElectrodeConfig(**p["left_electrode"])
    re_cfg = ElectrodeConfig(**p["right_electrode"])
    topo_failures: list[dict[str, Any]] = []
    for lvl in study_levels:
        cfg_lvl = GroundedBoxConfig(
            n=lvl,
            box_width_m=float(p["box_width_m"]),
            left_electrode=le_cfg,
            right_electrode=re_cfg,
        )
        sol_lvl = electrode_pair_in_grounded_box(config=cfg_lvl)
        topo_ok, topo_diag = validate_snapped_contour_topology(sol_lvl, cfg_lvl)
        if not topo_ok:
            topo_failures.append({"n": lvl, "reason": topo_diag})

    if topo_failures:
        status = "WITHHELD_INVALID_CONTOUR_TOPOLOGY"
        return (
            {
                "status": status,
                "study_n_list": list(study_levels),
                "failed_levels": topo_failures,
                "rows": [],
                "derived_sensitivity": None,
            },
            {
                "status": status,
                "study_n_list": list(study_levels),
                "failed_levels": topo_failures,
                "rows": [],
                "assessment": None,
            },
            status,
            status,
        )

    base_cfg = GroundedBoxConfig(
        n=int(p["n"]),
        box_width_m=float(p["box_width_m"]),
        left_electrode=le_cfg,
        right_electrode=re_cfg,
    )
    force_study = force_mesh_convergence_study(n_list=study_levels, config=base_cfg)
    probe_rows = electrode_pair_mesh_study(
        n_list=study_levels,
        box_width_m=float(p["box_width_m"]),
        probe_xy_m=(float(probe_xy[0]), float(probe_xy[1])),
        config=base_cfg,
        require_vacuum_probe=False,
    )
    probe_assess = assess_probe_convergence(
        probe_rows,
        requested_probe_xy_m=(float(probe_xy[0]), float(probe_xy[1])),
    )

    serialized_rows = [
        {
            "n": int(r.n),
            "grid_spacing_m": float(r.grid_spacing_m),
            "left_electrode_fx_n_per_m": float(r.left_electrode_fx_n_per_m),
            "left_electrode_fy_n_per_m": float(r.left_electrode_fy_n_per_m),
            "right_electrode_fx_n_per_m": float(r.right_electrode_fx_n_per_m),
            "right_electrode_fy_n_per_m": float(r.right_electrode_fy_n_per_m),
            "enclosure_reaction_fx_n_per_m": float(r.enclosure_reaction_fx_n_per_m),
            "enclosure_reaction_fy_n_per_m": float(r.enclosure_reaction_fy_n_per_m),
            "net_residual_fx_n_per_m": float(r.net_residual_fx_n_per_m),
            "net_residual_fy_n_per_m": float(r.net_residual_fy_n_per_m),
            "net_residual_magnitude_n_per_m": float(r.net_residual_magnitude_n_per_m),
            "max_abs_change_to_prev": float(r.max_abs_change_to_prev) if r.max_abs_change_to_prev is not None else None,
            "max_relative_change_to_prev": float(r.max_relative_change_to_prev)
            if r.max_relative_change_to_prev is not None
            else None,
            "row_tolerance_n_per_m": 1e-3,
            "row_tolerance_scope": "study_row_1e-3",
        }
        for r in force_study.rows
    ]

    # Spec Section 3.3(3): suppress observed orders for non-uniform h-ratio triplet (41, 81, 101)
    suppressed_comp_assessments = {
        cname: {
            "component_name": ca.component_name,
            "finest_value_n_per_m": float(ca.finest_value_n_per_m),
            "penultimate_value_n_per_m": float(ca.penultimate_value_n_per_m),
            "last_step_abs_diff_n_per_m": float(ca.last_step_abs_diff_n_per_m),
            "last_step_relative_change": float(ca.last_step_relative_change)
            if ca.last_step_relative_change is not None
            else None,
            "observed_order": None,
            "regime": ca.regime,
            "is_converged": bool(ca.is_converged),
        }
        for cname, ca in force_study.component_assessments.items()
    }

    force_status = "STABLE_WITHIN_STUDY_TOLERANCE" if force_study.is_converged_to_tolerance else "SENSITIVE_OR_UNBALANCED"
    force_payload = {
        "status": force_status,
        "study_n_list": list(study_levels),
        "failed_levels": [],
        "rows": serialized_rows,
        "observed_order_status": "NOT_COMPUTED_NONUNIFORM_H_RATIO",
        "observed_order_left_electrode": None,
        "observed_order_right_electrode": None,
        "observed_order_enclosure": None,
        "observed_orders_by_component": None,
        "component_assessments": suppressed_comp_assessments,
        "derived_sensitivity": {
            "units": "N/m",
            "per_component_last_step_diff_n_per_m": {
                k: float(v) for k, v in force_study.per_component_last_step_diff_n_per_m.items()
            },
            "max_component_last_step_diff_n_per_m": float(force_study.max_component_last_step_diff_n_per_m),
            "max_vector_last_step_diff_n_per_m": float(force_study.max_vector_last_step_diff_n_per_m),
            "max_component_relative_change": float(force_study.max_component_relative_change),
            "finest_net_residual_magnitude_n_per_m": float(force_study.finest_net_residual_magnitude_n_per_m),
            "is_converged_to_tolerance": bool(force_study.is_converged_to_tolerance),
            "thresholds": {
                "study_row_1e-3": 1e-3,
                "study_convergence_1e-6": 1e-6,
                "study_relative_change": 0.05,
                "study_abs_change_n_per_m": 5e-4,
                "study_near_zero_abs_n_per_m": 1e-6,
                "significant_force_threshold_n_per_m": 1e-6,
            },
        },
        "discretization_error_note": force_study.discretization_error_note,
        "diagnostic_note": force_study.diagnostic_note,
    }

    probe_payload = {
        "status": probe_assess.convergence_status,
        "study_n_list": list(study_levels),
        "failed_levels": [],
        "rows": [
            {
                "n": int(pr.n),
                "grid_spacing_m": float(pr.grid_spacing_m),
                "probe_x_m": float(pr.probe_x_m),
                "probe_y_m": float(pr.probe_y_m),
                "probe_potential_v": float(pr.probe_potential_v),
                "probe_ex_v_per_m": float(pr.probe_ex_v_per_m) if pr.probe_ex_v_per_m is not None else None,
                "probe_ey_v_per_m": float(pr.probe_ey_v_per_m) if pr.probe_ey_v_per_m is not None else None,
                "max_vacuum_e_v_per_m": float(pr.max_vacuum_e_v_per_m),
                "max_discrete_stencil_defect_v": float(pr.max_discrete_residual_v),
                "probe_in_vacuum": bool(pr.probe_in_vacuum),
                "requested_probe_in_vacuum": bool(pr.requested_probe_in_vacuum),
                "sampled_node_in_vacuum": bool(pr.sampled_node_in_vacuum),
                "probe_status": pr.probe_status,
            }
            for pr in probe_rows
        ],
        "assessment": {
            "vacuum_status": probe_assess.vacuum_status,
            "convergence_status": probe_assess.convergence_status,
            "assessment_summary": probe_assess.assessment_summary,
            "requested_probe_xy_m": [float(v) for v in probe_assess.requested_probe_xy_m],
            "sampled_probe_coords": [[float(x), float(y)] for x, y in probe_assess.sampled_probe_coords],
            "coords_stable": bool(probe_assess.coords_stable),
            "relative_field_drift": float(probe_assess.relative_field_drift)
            if probe_assess.relative_field_drift is not None
            else None,
            "is_stable": bool(probe_assess.is_stable),
            "is_converged": False,
        },
    }

    return force_payload, probe_payload, force_status, probe_assess.convergence_status


def _run_grounded_box_2d(norm_req: dict[str, Any], input_fp: str) -> dict[str, Any]:
    p = norm_req["parameters"]
    probe_xy = norm_req["probe_xy_m"]
    ep = norm_req["endpoint"]

    cfg = GroundedBoxConfig(
        n=int(p["n"]),
        box_width_m=float(p["box_width_m"]),
        left_electrode=ElectrodeConfig(**p["left_electrode"]),
        right_electrode=ElectrodeConfig(**p["right_electrode"]),
    )
    sol = electrode_pair_in_grounded_box(config=cfg)
    sol_payload, probe_payload, fb_payload, fb_status, fb_diag = _evaluate_2d_single(
        sol,
        cfg,
        probe_xy,
        params=p,
    )

    run_study = (ep == "study") or bool(norm_req.get("include_convergence_study", False))
    if run_study:
        study_levels = tuple(norm_req.get("study_n_list", REQUIRED_STUDY_N_LIST))
        force_study_payload, probe_study_payload, force_sens_status, probe_stab_status = _run_gated_studies(
            norm_req, study_levels=study_levels
        )
        provenance_fn = (
            "electrode_pair_in_grounded_box + evaluate_whole_apparatus_force_budget + "
            "force_mesh_convergence_study + electrode_pair_mesh_study + assess_probe_convergence"
        )
        provenance_mod = "electrostatics_baseline + electrostatics_numerics"
    else:
        force_study_payload = None
        probe_study_payload = None
        force_sens_status = "NOT_ASSESSED"
        probe_stab_status = "NOT_ASSESSED"
        provenance_fn = "electrode_pair_in_grounded_box + evaluate_whole_apparatus_force_budget"
        provenance_mod = "electrostatics_baseline + electrostatics_numerics"

    return {
        "request_id": norm_req["request_id"],
        "input_fingerprint": input_fp,
        "model_id": "grounded_box_2d",
        "epistemic_label": "ESTABLISHED MODEL",
        "parameters": p,
        "constants": {"epsilon_0_f_per_m": EPSILON_0_F_PER_M},
        "provenance": _build_provenance(provenance_mod, provenance_fn),
        "uncertainty_and_limits": {
            "geometry_family": "grounded_box_2d_cylinders",
            "assumptions": [
                "2D Cartesian cross-section (infinite out-of-plane depth; forces strictly in N/m, NOT 3D N).",
                "Circular conductors with fixed Dirichlet potentials inside a grounded 0 V square enclosure.",
                "Homogeneous vacuum permittivity epsilon_0; O(h) staircase conductor boundary discretization.",
                "Mechanical standoffs/feedthroughs are unmodeled; peak |E| is grid-sensitive.",
            ],
            "validity_notes": [
                "NOT a 3D Exodus knife-edge blade or finite dielectric potting model.",
                "Non-uniform triplet (41, 81, 101) suppresses observed convergence order by contract.",
            ],
        },
        "solution": sol_payload,
        "probe": probe_payload,
        "force_budget": fb_payload,
        "force_budget_status": fb_status,
        "force_budget_diagnostic": fb_diag,
        "force_mesh_sensitivity_status": force_sens_status,
        "probe_stability_status": probe_stab_status,
        "force_study": force_study_payload,
        "probe_study": probe_study_payload,
    }


def solve_normalized_request(norm_req: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """Execute normalized V1 request synchronously against verified P0/P1 kernels."""
    verify_frozen_kernel_hashes()
    input_fp = compute_input_fingerprint(norm_req)
    if norm_req["mode"] == "parallel_plate_1d":
        payload = _run_parallel_plate_1d(norm_req, input_fp)
    else:
        payload = _run_grounded_box_2d(norm_req, input_fp)
    # Verify strict RFC 8259 JSON Compliance prior to returning
    strict_rfc8259_dumps(payload)
    return 200, payload


def execute_ipc_request(
    endpoint: str | None,
    request_payload: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    """Worker IPC entrypoint invoked by `v1_worker_bridge._run_worker_loop` under `--handler-module`."""
    try:
        norm = validate_and_normalize_request(endpoint, request_payload)
    except SchemaValidationError as exc:
        return exc.status_code, exc.to_error_payload()
    except Exception as exc:  # noqa: BLE001 - fail closed into structured HTTP 400 INVALID_SCHEMA
        req_id = _extract_valid_request_id(request_payload)
        return (
            400,
            {
                "error": {
                    "code": "INVALID_SCHEMA",
                    "message": f"Request validation failed: {exc}",
                    "field": None,
                },
                "request_id": req_id,
            },
        )

    try:
        return solve_normalized_request(norm)
    except Exception as exc:  # noqa: BLE001 - fail closed inside structured response
        return (
            500,
            {
                "error": {
                    "code": "SOLVER_EXECUTION_ERROR",
                    "message": f"Solver execution failed cleanly: {exc}",
                    "field": None,
                },
                "request_id": norm.get("request_id"),
            },
        )


def validate_v1_request_for_manager(endpoint: str, request_payload: dict[str, Any]) -> Any:
    """Pre-admission validator returning `BridgeResult` on schema/domain error, else `None`."""
    from v1_worker_bridge import BridgeResult

    try:
        validate_and_normalize_request(endpoint, request_payload)
        return None
    except SchemaValidationError as exc:
        return BridgeResult(exc.status_code, exc.to_error_payload())
    except Exception as exc:  # noqa: BLE001 - fail closed into structured HTTP 400 INVALID_SCHEMA
        req_id = _extract_valid_request_id(request_payload)
        return BridgeResult(
            400,
            {
                "error": {
                    "code": "INVALID_SCHEMA",
                    "message": f"Request validation failed: {exc}",
                    "field": None,
                },
                "request_id": req_id,
            },
        )


def create_solver_worker_manager(**kwargs: Any) -> Any:
    """Create a V1-A `WorkerManager` wired strictly to the V1-B `v1_solver_adapter` worker."""
    from v1_worker_bridge import WorkerManager

    kwargs.setdefault("request_validator", validate_v1_request_for_manager)
    kwargs.setdefault("handler_module", "v1_solver_adapter")
    return WorkerManager(**kwargs)


def create_solver_server(host: str, port: int, **kwargs: Any) -> Any:
    """Create hardened IPv4-loopback HTTP server wired to the isolated V1-B solver worker."""
    from run_explorer import create_server

    if "worker_manager" not in kwargs or kwargs["worker_manager"] is None:
        mgr_keys = ("response_deadline_s", "worker_reap_timeout_s")
        mgr_kwargs = {k: kwargs[k] for k in mgr_keys if k in kwargs}
        kwargs["worker_manager"] = create_solver_worker_manager(**mgr_kwargs)
    return create_server(host, port, **kwargs)
