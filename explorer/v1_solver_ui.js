/**
 * Propulsion Explorer V1 — Interactive Validated P0/P1 Solver UI (Slice B3)
 *
 * Implements the accepted V1 Solver Integration Specification R5:
 * - Connects 1D parallel-plate and 2D grounded-box interactive controls to
 *   accepted V1-A/B1 POST /api/v1/solve & POST /api/v1/study endpoints.
 * - Enforces synchronous pre-debounce state invalidation (clientStateGeneration,
 *   currentCanonicalFingerprint, activeModelMode, activeViewContext,
 *   latestDispatchedRequestId), 150 ms debounce, AbortController cancellation,
 *   and shared staleness gates on BOTH success and error/abort/parse paths.
 * - Provides truthful offline fallback using accepted B2 V1_REFERENCE_SNAPSHOTS
 *   under file:// and static HTTP servers (locking unsupported 2D parameter
 *   controls offline while preserving closed-form 1D evaluation).
 * - Preserves strict visual separation: dedicated 2D cross-section canvas (N/m)
 *   hides 3D schematic force arrows (forceGroup.visible === false), keeps
 *   #slider-eps labeled VISUAL PROXY ONLY, and preserves WHOLE-BODY THRUST:
 *   NOT MEASURED / NOT ESTABLISHED.
 */
(function () {
  "use strict";

  var DEBOUNCE_MS = 150;
  var DEFAULT_1D_PARAMS = { voltage_v: 1000.0, gap_m: 0.01, area_m2: 0.01 };

  var FALLBACK_PRESETS = {
    p0_p1_canonical_40mm: {
      n: 101,
      box_width_m: 0.04,
      left_electrode: { center_x_m: -0.008, center_y_m: 0.0, radius_m: 0.003, voltage_v: 500.0 },
      right_electrode: { center_x_m: 0.008, center_y_m: 0.0, radius_m: 0.003, voltage_v: -500.0 },
      probe_xy_m: [0.0, 0.0],
      gap_range_mm: [6.0, 16.0],
      off_axis_cy_range_mm: [-10.0, 10.0]
    },
    asymmetric_hv_80mm_bench: {
      n: 101,
      box_width_m: 0.08,
      left_electrode: { center_x_m: -0.015, center_y_m: 0.0, radius_m: 0.007, voltage_v: -20000.0 },
      right_electrode: { center_x_m: 0.015, center_y_m: 0.0, radius_m: 0.007, voltage_v: 0.0 },
      probe_xy_m: [0.0, 0.0],
      gap_range_mm: [12.0, 28.0],
      off_axis_cy_range_mm: [-20.0, 20.0]
    },
    bipolar_hv_80mm_bench: {
      n: 101,
      box_width_m: 0.08,
      left_electrode: { center_x_m: -0.015, center_y_m: 0.0, radius_m: 0.007, voltage_v: -10000.0 },
      right_electrode: { center_x_m: 0.015, center_y_m: 0.0, radius_m: 0.007, voltage_v: 10000.0 },
      probe_xy_m: [0.0, 0.0],
      gap_range_mm: [12.0, 28.0],
      off_axis_cy_range_mm: [-20.0, 20.0]
    }
  };

  // --- Authoritative Section 4.2 Synchronous Client State ---
  var clientStateGeneration = 0;
  var currentCanonicalFingerprint = null;
  var activeModelMode = "schematic_3d"; // "schematic_3d" | "parallel_plate_1d" | "grounded_box_2d"
  var activeViewContext = "3d_schematic"; // "3d_schematic" | "v1_1d" | "v1_2d" | "scalar_wave_contrast"
  var activeEndpoint = null; // null | "/api/v1/solve" | "/api/v1/study"
  var latestDispatchedRequestId = 0;
  var nextRequestId = 1;
  var debounceTimerId = null;
  var activeAbortController = null;
  var solveState = "idle"; // "idle" | "pending" | "ready" | "error"
  var transportMode = (window.location && window.location.protocol === "file:") ? "offline" : "live";
  var lastRenderedResponse = null;
  var active2DPresetId = "p0_p1_canonical_40mm";
  var lastCanvasBounds = null;
  var suppressWaveCallback = false;

  function getSnapshotsBundle() {
    return window.V1_REFERENCE_SNAPSHOTS || null;
  }

  function getHelpers() {
    var b = getSnapshotsBundle();
    return (b && b.helpers) ? b.helpers : null;
  }

  function getPresetDef(presetId) {
    var b = getSnapshotsBundle();
    if (b && b.presets_2d && b.presets_2d[presetId] && b.presets_2d[presetId].metadata) {
      var meta = b.presets_2d[presetId].metadata;
      var cp = meta.canonical_parameters;
      return {
        n: cp.n,
        box_width_m: cp.box_width_m,
        left_electrode: Object.assign({}, cp.left_electrode),
        right_electrode: Object.assign({}, cp.right_electrode),
        probe_xy_m: meta.default_probe_xy_m ? meta.default_probe_xy_m.slice() : [0.0, 0.0],
        gap_range_mm: meta.gap_range_mm ? meta.gap_range_mm.slice() : [6.0, 16.0],
        off_axis_cy_range_mm: meta.off_axis_cy_range_mm ? meta.off_axis_cy_range_mm.slice() : [-10.0, 10.0]
      };
    }
    var fb = FALLBACK_PRESETS[presetId] || FALLBACK_PRESETS.p0_p1_canonical_40mm;
    return {
      n: fb.n,
      box_width_m: fb.box_width_m,
      left_electrode: Object.assign({}, fb.left_electrode),
      right_electrode: Object.assign({}, fb.right_electrode),
      probe_xy_m: fb.probe_xy_m.slice(),
      gap_range_mm: fb.gap_range_mm.slice(),
      off_axis_cy_range_mm: fb.off_axis_cy_range_mm.slice()
    };
  }

  function roundTo(val, decimals) {
    var f = Math.pow(10, decimals);
    var r = Math.round(val * f) / f;
    return r === 0 ? 0.0 : r;
  }

  function fmtSci(val, unit) {
    if (typeof val !== "number" || !Number.isFinite(val)) return "—";
    if (val === 0) return unit ? "0.0 " + unit : "0.0";
    var abs = Math.abs(val);
    var s = (abs >= 1e-3 && abs < 1e4) ? val.toPrecision(6) : val.toExponential(4);
    return unit ? s + " " + unit : s;
  }

  function fmtSignedSci(val, unit) {
    if (typeof val !== "number" || !Number.isFinite(val)) return "—";
    if (val === 0) return unit ? "0.0 " + unit : "0.0";
    var prefix = val > 0 ? "+" : "";
    return prefix + fmtSci(val, unit);
  }

  function el(id) {
    return document.getElementById(id);
  }

  function setText(id, text) {
    var node = el(id);
    if (node) node.textContent = text;
  }

  function isComputed2DActive() {
    return activeModelMode === "grounded_box_2d" && activeViewContext === "v1_2d";
  }

  // --- Read Canonical Request Payloads from Current Controls ---
  function read1DParametersFromUI() {
    var vEl = el("v1-1d-voltage");
    var gEl = el("v1-1d-gap");
    var aEl = el("v1-1d-area");
    var voltageV = vEl ? parseFloat(vEl.value) : DEFAULT_1D_PARAMS.voltage_v;
    var gapMm = gEl ? parseFloat(gEl.value) : DEFAULT_1D_PARAMS.gap_m * 1000.0;
    var areaCm2 = aEl ? parseFloat(aEl.value) : DEFAULT_1D_PARAMS.area_m2 * 10000.0;
    return {
      voltage_v: roundTo(Number.isFinite(voltageV) ? voltageV : 0.0, 6),
      gap_m: roundTo((Number.isFinite(gapMm) ? gapMm : 10.0) / 1000.0, 6),
      area_m2: roundTo((Number.isFinite(areaCm2) ? areaCm2 : 100.0) / 10000.0, 7)
    };
  }

  function read2DRequestFromUI(endpoint) {
    var preset = getPresetDef(active2DPresetId);
    var nEl = el("v1-2d-grid-n");
    var nVal = nEl ? parseInt(nEl.value, 10) : preset.n;
    if (nVal !== 41 && nVal !== 81 && nVal !== 101) nVal = preset.n;

    var wM = preset.box_width_m;
    var rM = preset.left_electrode.radius_m;

    var vLeft, vRight, cxM, cyM, probeX, probeY;
    if (transportMode === "offline") {
      // Offline 2D locks strictly to canonical preset parameters (prevents stale sliders impersonating frozen snapshots)
      vLeft = preset.left_electrode.voltage_v;
      vRight = preset.right_electrode.voltage_v;
      cxM = Math.abs(preset.right_electrode.center_x_m);
      cyM = preset.left_electrode.center_y_m;
      probeX = preset.probe_xy_m[0];
      probeY = preset.probe_xy_m[1];
    } else {
      var vlEl = el("v1-2d-vleft");
      var vrEl = el("v1-2d-vright");
      var gapEl = el("v1-2d-gap");
      var cyEl = el("v1-2d-cy");
      var pxEl = el("v1-2d-probe-x");
      var pyEl = el("v1-2d-probe-y");

      vLeft = roundTo(vlEl ? parseFloat(vlEl.value) : preset.left_electrode.voltage_v, 6);
      vRight = roundTo(vrEl ? parseFloat(vrEl.value) : preset.right_electrode.voltage_v, 6);
      var gapMm = gapEl ? parseFloat(gapEl.value) : ((2.0 * Math.abs(preset.right_electrode.center_x_m) - 2.0 * rM) * 1000.0);
      cxM = roundTo((gapMm / 2.0) / 1000.0 + rM, 6);
      cyM = roundTo((cyEl ? parseFloat(cyEl.value) : 0.0) / 1000.0, 6);

      var halfWMm = (wM * 1000.0) / 2.0;
      var pxMm = pxEl ? parseFloat(pxEl.value) : 0.0;
      var pyMm = pyEl ? parseFloat(pyEl.value) : 0.0;
      if (!Number.isFinite(pxMm)) pxMm = 0.0;
      if (!Number.isFinite(pyMm)) pyMm = 0.0;
      pxMm = Math.max(-halfWMm, Math.min(halfWMm, pxMm));
      pyMm = Math.max(-halfWMm, Math.min(halfWMm, pyMm));
      probeX = roundTo(pxMm / 1000.0, 6);
      probeY = roundTo(pyMm / 1000.0, 6);
    }

    var base = {
      mode: "grounded_box_2d",
      parameters: {
        n: nVal,
        box_width_m: wM,
        left_electrode: {
          center_x_m: roundTo(-cxM, 6),
          center_y_m: cyM,
          radius_m: rM,
          voltage_v: vLeft
        },
        right_electrode: {
          center_x_m: roundTo(cxM, 6),
          center_y_m: cyM,
          radius_m: rM,
          voltage_v: vRight
        }
      },
      probe_xy_m: [probeX, probeY]
    };
    if (endpoint === "/api/v1/study") {
      base.study_n_list = [41, 81, 101];
    } else {
      base.include_convergence_study = false;
    }
    return base;
  }

  function computeCurrentFingerprintSync(mode, view, endpoint) {
    if (view === "scalar_wave_contrast" || mode === "schematic_3d" || !endpoint) {
      return null;
    }
    var h = getHelpers();
    if (!h || typeof h.computeInputFingerprint !== "function") {
      return null;
    }
    try {
      if (mode === "parallel_plate_1d") {
        return h.computeInputFingerprint("/api/v1/solve", {
          mode: "parallel_plate_1d",
          parameters: read1DParametersFromUI()
        });
      }
      if (mode === "grounded_box_2d") {
        var req2d = read2DRequestFromUI(endpoint);
        return h.computeInputFingerprint(endpoint, req2d);
      }
    } catch (_e) {
      return null;
    }
    return null;
  }

  // --- Section 3.2 Dynamic Slider Bounds Enforcement ---
  function sync2DSliderBounds(resetToPresetDefaults) {
    var preset = getPresetDef(active2DPresetId);
    var nEl = el("v1-2d-grid-n");
    var nVal = nEl ? parseInt(nEl.value, 10) : preset.n;
    if (nVal !== 41 && nVal !== 81 && nVal !== 101) nVal = preset.n;

    var wMm = preset.box_width_m * 1000.0;
    var rMm = preset.left_electrode.radius_m * 1000.0;
    var hMm = wMm / (nVal - 1);

    // Spec Section 3.2: intersection of [max(5 mm, 6h), W - 4r - 12h] with preset envelope
    var dynGapMin = Math.max(5.0, 6.0 * hMm, preset.gap_range_mm[0]);
    var dynGapMax = Math.min(wMm - 4.0 * rMm - 12.0 * hMm, preset.gap_range_mm[1]);
    var dynCyMax = Math.max(0.0, Math.min(wMm / 4.0, wMm / 2.0 - rMm - 6.0 * hMm, Math.abs(preset.off_axis_cy_range_mm[1])));

    var gapEl = el("v1-2d-gap");
    var cyEl = el("v1-2d-cy");
    var vlEl = el("v1-2d-vleft");
    var vrEl = el("v1-2d-vright");
    var pxEl = el("v1-2d-probe-x");
    var pyEl = el("v1-2d-probe-y");

    var defaultGapMm = roundTo(2.0 * Math.abs(preset.right_electrode.center_x_m) * 1000.0 - 2.0 * rMm, 3);
    if (gapEl) {
      gapEl.min = String(roundTo(dynGapMin, 3));
      gapEl.max = String(roundTo(dynGapMax, 3));
      if (resetToPresetDefaults) {
        gapEl.value = String(defaultGapMm);
      } else {
        var curGap = parseFloat(gapEl.value);
        if (!Number.isFinite(curGap) || curGap < dynGapMin || curGap > dynGapMax) {
          gapEl.value = String(Math.max(dynGapMin, Math.min(dynGapMax, defaultGapMm)));
        }
      }
    }
    if (cyEl) {
      cyEl.min = String(roundTo(-dynCyMax, 3));
      cyEl.max = String(roundTo(dynCyMax, 3));
      if (resetToPresetDefaults) {
        cyEl.value = String(roundTo(preset.left_electrode.center_y_m * 1000.0, 3));
      } else {
        var curCy = parseFloat(cyEl.value);
        if (!Number.isFinite(curCy) || curCy < -dynCyMax || curCy > dynCyMax) {
          cyEl.value = String(Math.max(-dynCyMax, Math.min(dynCyMax, 0.0)));
        }
      }
    }
    if (resetToPresetDefaults) {
      if (vlEl) vlEl.value = String(preset.left_electrode.voltage_v);
      if (vrEl) vrEl.value = String(preset.right_electrode.voltage_v);
      if (pxEl) pxEl.value = String(roundTo(preset.probe_xy_m[0] * 1000.0, 3));
      if (pyEl) pyEl.value = String(roundTo(preset.probe_xy_m[1] * 1000.0, 3));
    }
    if (pxEl) {
      pxEl.min = String(-wMm / 2.0);
      pxEl.max = String(wMm / 2.0);
    }
    if (pyEl) {
      pyEl.min = String(-wMm / 2.0);
      pyEl.max = String(wMm / 2.0);
    }
    updateSliderReadoutLabels();
  }

  function updateSliderReadoutLabels() {
    var p1d = read1DParametersFromUI();
    setText("v1-1d-voltage-val", p1d.voltage_v.toFixed(0) + " V");
    setText("v1-1d-gap-val", (p1d.gap_m * 1000.0).toFixed(1) + " mm (" + p1d.gap_m.toFixed(4) + " m)");
    setText("v1-1d-area-val", (p1d.area_m2 * 10000.0).toFixed(0) + " cm² (" + p1d.area_m2.toFixed(4) + " m²)");

    var vlEl = el("v1-2d-vleft");
    var vrEl = el("v1-2d-vright");
    var gapEl = el("v1-2d-gap");
    var cyEl = el("v1-2d-cy");
    if (vlEl) {
      var vl = parseFloat(vlEl.value);
      setText("v1-2d-vleft-val", (vl > 0 ? "+" : "") + vl.toFixed(0) + " V");
    }
    if (vrEl) {
      var vr = parseFloat(vrEl.value);
      setText("v1-2d-vright-val", (vr > 0 ? "+" : "") + vr.toFixed(0) + " V");
    }
    if (gapEl) {
      setText("v1-2d-gap-val", parseFloat(gapEl.value).toFixed(1) + " mm");
    }
    if (cyEl) {
      var cy = parseFloat(cyEl.value);
      setText("v1-2d-cy-val", (cy > 0 ? "+" : "") + cy.toFixed(1) + " mm");
    }
  }

  // --- UI Visibility, Transport Lock & Clear/Invalidation Helpers ---
  function setSolveStateUI(newState) {
    solveState = newState;
    var badge = el("v1-solve-state");
    if (badge) {
      badge.dataset.solveState = newState;
      badge.textContent = newState.toUpperCase();
    }
    var canvasStatus = el("v1-2d-canvas-status");
    if (canvasStatus) {
      if (newState === "pending" && isComputed2DActive()) {
        canvasStatus.textContent = "Computing validated 2D P0/P1 solution...";
        canvasStatus.classList.remove("hidden");
      } else if (newState === "error" && isComputed2DActive()) {
        canvasStatus.textContent = "2D solver error — see error banner in V1 Solver panel.";
        canvasStatus.classList.remove("hidden");
      } else {
        canvasStatus.classList.add("hidden");
      }
    }
  }

  function clearErrorBanner() {
    var banner = el("v1-error-banner");
    if (banner) banner.classList.add("hidden");
    setText("v1-error-title", "Solver Request Error");
    setText("v1-error-message", "");
  }

  function showErrorBanner(code, message) {
    var banner = el("v1-error-banner");
    setText("v1-error-title", "Solver Error" + (code ? " (" + code + ")" : ""));
    setText("v1-error-message", message || "Request failed.");
    if (banner) banner.classList.remove("hidden");
  }

  function clearComputedReadouts() {
    lastRenderedResponse = null;
    var ids1d = [
      "v1-1d-e-field", "v1-1d-pressure", "v1-1d-force-pos", "v1-1d-force-neg",
      "v1-1d-net-force", "v1-1d-energy", "v1-1d-vw-fixed-v", "v1-1d-vw-fixed-q",
      "v1-1d-aspect-ratio", "v1-1d-epsilon0"
    ];
    for (var i = 0; i < ids1d.length; i++) setText(ids1d[i], "—");
    var fWarn = el("v1-1d-fringing-warning");
    if (fWarn) fWarn.classList.add("hidden");

    var ids2d = [
      "v1-2d-rendered-params-text", "v1-2d-fx-left", "v1-2d-fy-left",
      "v1-2d-fx-right", "v1-2d-fy-right", "v1-2d-fx-box", "v1-2d-fy-box",
      "v1-2d-fx-net", "v1-2d-fy-net", "v1-2d-fnorm-net", "v1-2d-rel-residual",
      "v1-2d-stencil-defect", "v1-2d-probe-status", "v1-2d-probe-coords",
      "v1-2d-probe-phi", "v1-2d-probe-ex", "v1-2d-probe-ey",
      "v1-2d-mesh-sens-status", "v1-2d-probe-stab-status"
    ];
    for (var j = 0; j < ids2d.length; j++) setText(ids2d[j], "—");

    var closureBanner = el("v1-2d-closure-banner");
    if (closureBanner) {
      closureBanner.className = "v1-banner hidden";
    }
    var studyCard = el("v1-2d-study-card");
    if (studyCard) studyCard.classList.add("hidden");
    var studyRows = el("v1-2d-study-rows");
    if (studyRows) studyRows.innerHTML = "";

    setText("v1-prov-model", "—");
    setText("v1-prov-epistemic", "—");
    setText("v1-prov-fingerprint", "—");
    setText("v1-prov-source-sha", "—");
    setText("v1-prov-kernels", "—");
    setText("v1-prov-thrust", "NOT MEASURED / NOT ESTABLISHED");
    var limitsEl = el("v1-prov-limits");
    if (limitsEl) limitsEl.innerHTML = "";

    clear2DCanvas();
  }

  function syncTransportUI() {
    var isOffline = transportMode === "offline";
    var tBadge = el("v1-transport-badge");
    if (tBadge) {
      tBadge.textContent = isOffline ? "SOLVER BRIDGE OFFLINE" : "LIVE P0/P1 BRIDGE";
      tBadge.classList.toggle("offline", isOffline);
    }
    var offlineBanner = el("v1-offline-banner");
    if (offlineBanner) {
      offlineBanner.classList.toggle("hidden", !isOffline);
    }
    var retryBtn = el("v1-btn-retry-live");
    if (retryBtn) {
      var isFileProto = window.location && window.location.protocol === "file:";
      retryBtn.classList.toggle("hidden", isFileProto);
    }
    var lockNote = el("v1-2d-offline-lock-note");
    if (lockNote) {
      lockNote.classList.toggle("hidden", !isOffline);
    }

    // Lock unsupported arbitrary 2D controls when offline (preset & bundled snapshot n={41,81,101} remain selectable)
    var locked2DIds = ["v1-2d-vleft", "v1-2d-vright", "v1-2d-gap", "v1-2d-cy", "v1-2d-probe-x", "v1-2d-probe-y"];
    for (var i = 0; i < locked2DIds.length; i++) {
      var ctrl = el(locked2DIds[i]);
      if (ctrl) ctrl.disabled = isOffline;
    }
    var gridLabel = el("v1-2d-grid-n-label");
    if (gridLabel) {
      gridLabel.innerHTML = isOffline
        ? "Precomputed Snapshot Grid (<i>n</i> &times; <i>n</i>):"
        : "Grid Resolution (<i>n</i> &times; <i>n</i>):";
    }
    if (isOffline) {
      sync2DSliderBounds(true);
    }
  }

  function syncModePanelsAndViewport() {
    var modeBtns = document.querySelectorAll(".v1-mode-btn");
    modeBtns.forEach(function (btn) {
      var isAct = btn.dataset.v1Mode === activeModelMode;
      btn.classList.toggle("active", isAct);
      btn.setAttribute("aria-checked", isAct ? "true" : "false");
    });

    var pSch = el("v1-panel-schematic");
    var p1d = el("v1-panel-1d");
    var p2d = el("v1-panel-2d");
    var provCard = el("v1-provenance-card");
    if (pSch) pSch.classList.toggle("hidden", activeModelMode !== "schematic_3d");
    if (p1d) p1d.classList.toggle("hidden", activeModelMode !== "parallel_plate_1d");
    if (p2d) p2d.classList.toggle("hidden", activeModelMode !== "grounded_box_2d");
    if (provCard) provCard.classList.toggle("hidden", activeModelMode === "schematic_3d");

    var epBadge = el("v1-mode-epistemic-badge");
    if (epBadge) {
      if (activeModelMode === "schematic_3d") {
        epBadge.textContent = "PROVISIONAL ILLUSTRATIVE SCENE";
        epBadge.className = "provenance-pill pill-provisional";
      } else {
        epBadge.textContent = "ESTABLISHED MODEL";
        epBadge.className = "provenance-pill pill-established";
      }
    }

    // Strict visual separation: dedicated 2D viewport shown ONLY in v1_2d context; 3D forceGroup hidden!
    var show2DViewport = isComputed2DActive();
    var vp2d = el("v1-2d-viewport");
    var vpContainer = el("viewport-container");
    if (vp2d) vp2d.classList.toggle("hidden", !show2DViewport);
    if (vpContainer) vpContainer.classList.toggle("v1-2d-active", show2DViewport);

    if (window.__explorer && typeof window.__explorer.syncAllLayerVisibilities === "function") {
      window.__explorer.syncAllLayerVisibilities();
    }
  }

  // --- Section 4.2 Synchronous Pre-Debounce Invalidation ---
  function invalidatePending(nextMode, nextView, nextEndpoint, nextState) {
    clientStateGeneration += 1;
    activeModelMode = nextMode;
    activeViewContext = nextView;
    activeEndpoint = nextEndpoint;

    if (debounceTimerId !== null) {
      clearTimeout(debounceTimerId);
      debounceTimerId = null;
    }
    if (activeAbortController) {
      try {
        activeAbortController.abort();
      } catch (_err) {
        // ignore
      }
      activeAbortController = null;
    }

    currentCanonicalFingerprint = computeCurrentFingerprintSync(activeModelMode, activeViewContext, activeEndpoint);
    clearErrorBanner();
    clearComputedReadouts();
    syncModePanelsAndViewport();
    setSolveStateUI(nextState || "idle");
  }

  function isCapturedCurrent(captured) {
    return (
      captured.gen === clientStateGeneration &&
      captured.fp === currentCanonicalFingerprint &&
      captured.mode === activeModelMode &&
      captured.view === activeViewContext &&
      captured.reqId === latestDispatchedRequestId
    );
  }

  function enterOfflineModeAndRender(endpointToRun) {
    transportMode = "offline";
    syncTransportUI();
    var targetView = activeModelMode === "grounded_box_2d" ? "v1_2d" : (activeModelMode === "parallel_plate_1d" ? "v1_1d" : "3d_schematic");
    invalidatePending(activeModelMode, targetView, endpointToRun || "/api/v1/solve", "pending");
    dispatchCurrentRequest();
  }

  function scheduleV1Request(endpoint, immediate) {
    var targetView = activeModelMode === "grounded_box_2d" ? "v1_2d" : (activeModelMode === "parallel_plate_1d" ? "v1_1d" : "3d_schematic");
    if (activeModelMode === "schematic_3d") {
      invalidatePending("schematic_3d", "3d_schematic", null, "idle");
      return;
    }
    // Always run synchronous pre-debounce invalidation BEFORE scheduling debounce timer
    invalidatePending(activeModelMode, targetView, endpoint, "pending");

    if (immediate) {
      dispatchCurrentRequest();
    } else {
      debounceTimerId = setTimeout(function () {
        debounceTimerId = null;
        dispatchCurrentRequest();
      }, DEBOUNCE_MS);
    }
  }

  function dispatchCurrentRequest() {
    if (activeModelMode === "schematic_3d" || activeViewContext === "scalar_wave_contrast" || !activeEndpoint) {
      return;
    }
    var reqId = nextRequestId++;
    latestDispatchedRequestId = reqId;

    var captured = {
      gen: clientStateGeneration,
      reqId: reqId,
      fp: currentCanonicalFingerprint,
      mode: activeModelMode,
      view: activeViewContext,
      endpoint: activeEndpoint
    };

    // Offline dispatch path (true serverless file:// or static HTTP fallback)
    if (transportMode === "offline") {
      executeOfflineRequest(captured);
      return;
    }

    var payload;
    if (captured.mode === "parallel_plate_1d") {
      payload = {
        request_id: reqId,
        mode: "parallel_plate_1d",
        parameters: read1DParametersFromUI()
      };
    } else {
      var req2d = read2DRequestFromUI(captured.endpoint);
      payload = Object.assign({ request_id: reqId }, req2d);
    }

    var controller = typeof AbortController !== "undefined" ? new AbortController() : null;
    activeAbortController = controller;

    var fetchOpts = {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    };
    if (controller) {
      fetchOpts.signal = controller.signal;
    }

    fetch(captured.endpoint, fetchOpts).then(
      function (response) {
        if (activeAbortController === controller) {
          activeAbortController = null;
        }
        // Section 4.2: shared staleness gate evaluated FIRST before parsing or error display
        if (!isCapturedCurrent(captured)) {
          return;
        }

        var contentType = (response.headers && response.headers.get("content-type")) || "";
        var isJsonHeader = contentType.toLowerCase().indexOf("application/json") !== -1;

        // Detect static HTTP server (e.g. python -m http.server returning 501/405/404 non-JSON HTML)
        if (!isJsonHeader && (response.status === 501 || response.status === 405 || response.status === 404)) {
          enterOfflineModeAndRender(captured.endpoint);
          return;
        }

        return response.text().then(
          function (rawText) {
            if (!isCapturedCurrent(captured)) {
              return;
            }
            var data = null;
            var parseFailed = false;
            try {
              data = JSON.parse(rawText);
            } catch (_parseErr) {
              parseFailed = true;
            }

            if (response.status !== 200) {
              var errCode = (!parseFailed && data && data.error && data.error.code)
                ? data.error.code
                : ("HTTP_" + String(response.status));
              var errMsg = (!parseFailed && data && data.error && data.error.message)
                ? data.error.message
                : ("Server returned HTTP " + String(response.status) + ".");
              handleCurrentError(captured, errCode, errMsg);
              return;
            }

            if (parseFailed || !data || typeof data !== "object") {
              handleCurrentError(captured, "MALFORMED_JSON", "Received malformed JSON response from solver bridge.");
              return;
            }

            if (data.status === "V1_A_TRANSPORT_ONLY") {
              enterOfflineModeAndRender(captured.endpoint);
              return;
            }

            // Section 4.2 Success identity verification
            if (data.request_id !== captured.reqId || data.input_fingerprint !== captured.fp) {
              handleCurrentError(
                captured,
                "IDENTITY_MISMATCH",
                "Response request_id/input_fingerprint did not match current client request."
              );
              return;
            }

            renderVerifiedResponse(captured, data);
          },
          function () {
            if (!isCapturedCurrent(captured)) return;
            handleCurrentError(captured, "RESPONSE_READ_ERROR", "Failed to read solver response body.");
          }
        );
      },
      function (err) {
        if (activeAbortController === controller) {
          activeAbortController = null;
        }
        // Section 4.2: shared staleness gate evaluated FIRST on network/abort errors
        if (!isCapturedCurrent(captured)) {
          return;
        }
        if (err && err.name === "AbortError") {
          return;
        }
        handleCurrentError(
          captured,
          "NETWORK_ERROR",
          "Could not reach live V1 solver bridge (" + (err && err.message ? err.message : "network error") + ")."
        );
      }
    );
  }

  function executeOfflineRequest(captured) {
    if (!isCapturedCurrent(captured)) return;
    var h = getHelpers();
    if (!h) {
      handleCurrentError(captured, "OFFLINE_BUNDLE_MISSING", "Offline B2 reference snapshot bundle is unavailable.");
      return;
    }
    try {
      if (captured.mode === "parallel_plate_1d") {
        var params1d = read1DParametersFromUI();
        var res1d = h.evaluateParallelPlate1D(params1d, captured.reqId);
        if (!isCapturedCurrent(captured)) return;
        if (res1d.request_id !== captured.reqId || res1d.input_fingerprint !== captured.fp) {
          handleCurrentError(captured, "OFFLINE_IDENTITY_MISMATCH", "Offline 1D fingerprint mismatch.");
          return;
        }
        renderVerifiedResponse(captured, res1d);
        return;
      }

      if (captured.mode === "grounded_box_2d") {
        var snap = h.lookupOfflineSnapshotByFingerprint(captured.fp);
        if (!isCapturedCurrent(captured)) return;
        if (!snap) {
          handleCurrentError(
            captured,
            "OFFLINE_SNAPSHOT_UNAVAILABLE",
            "No precomputed offline snapshot matches this 2D parameter combination. Launch `python run_explorer.py` for live arbitrary 2D solves."
          );
          return;
        }
        snap.request_id = captured.reqId;
        renderVerifiedResponse(captured, snap);
      }
    } catch (err) {
      if (!isCapturedCurrent(captured)) return;
      handleCurrentError(captured, "OFFLINE_VALIDATION_ERROR", err && err.message ? err.message : String(err));
    }
  }

  function handleCurrentError(captured, code, message) {
    if (!isCapturedCurrent(captured)) return;
    clearComputedReadouts();
    setSolveStateUI("error");
    showErrorBanner(code, message);
  }

  // --- Rendering Verified Responses ---
  function renderVerifiedResponse(captured, resp) {
    if (!isCapturedCurrent(captured)) return;
    clearErrorBanner();
    lastRenderedResponse = resp;

    if (captured.mode === "parallel_plate_1d") {
      render1DResponse(resp);
    } else if (captured.mode === "grounded_box_2d") {
      render2DResponse(resp);
    }
    renderProvenanceCard(resp);
    setSolveStateUI("ready");
  }

  function render1DResponse(resp) {
    setText("v1-1d-e-field", fmtSci(resp.electric_field_v_per_m, "V/m"));
    setText("v1-1d-pressure", fmtSci(resp.pressure_pa, "Pa"));
    setText("v1-1d-force-pos", fmtSignedSci(resp.force_on_positive_plate_n, "N"));
    setText("v1-1d-force-neg", fmtSignedSci(resp.force_on_negative_plate_n, "N"));
    setText("v1-1d-net-force", fmtSci(resp.net_pair_force_n, "N") + " (exact cancellation)");
    setText("v1-1d-energy", fmtSci(resp.stored_energy_j, "J"));
    if (resp.virtual_work) {
      setText("v1-1d-vw-fixed-v", fmtSci(resp.virtual_work.virtual_work_fixed_v_n, "N"));
      setText("v1-1d-vw-fixed-q", fmtSci(resp.virtual_work.virtual_work_fixed_q_n, "N"));
    }
    setText("v1-1d-aspect-ratio", typeof resp.fringing_aspect_ratio === "number" ? resp.fringing_aspect_ratio.toFixed(3) : "—");
    if (resp.constants) {
      setText("v1-1d-epsilon0", String(resp.constants.epsilon_0_f_per_m) + " F/m");
    }

    var warnEl = el("v1-1d-fringing-warning");
    if (warnEl) {
      if (resp.fringing_warning) {
        setText(
          "v1-1d-fringing-text",
          "sqrt(A)/d = " + resp.fringing_aspect_ratio.toFixed(3) + " < 5.0 — significant edge fringing is neglected by the ideal 1D infinite-plate model."
        );
        warnEl.classList.remove("hidden");
      } else {
        warnEl.classList.add("hidden");
      }
    }
  }

  function render2DResponse(resp) {
    var p = resp.parameters || {};
    var le = p.left_electrode || {};
    var re = p.right_electrode || {};
    var gapMm = ((re.center_x_m - re.radius_m) - (le.center_x_m + le.radius_m)) * 1000.0;
    setText(
      "v1-2d-rendered-params-text",
      "n=" + String(p.n) +
        ", W=" + (p.box_width_m * 1000.0).toFixed(1) + " mm" +
        ", r=" + (le.radius_m * 1000.0).toFixed(1) + " mm" +
        ", d=" + gapMm.toFixed(1) + " mm" +
        ", cy=" + (le.center_y_m * 1000.0).toFixed(1) + " mm" +
        ", VL=" + le.voltage_v + " V" +
        ", VR=" + re.voltage_v + " V" +
        (transportMode === "offline" ? " [FROZEN SNAPSHOT]" : " [LIVE SOLVE]")
    );

    // Closure verdict banner (V1-SPEC-R2-M1: never claim balance when unbalanced!)
    var closureBanner = el("v1-2d-closure-banner");
    var fb = resp.force_budget;
    if (closureBanner) {
      if (resp.force_budget_status !== "COMPUTED" || !fb) {
        closureBanner.className = "v1-banner v1-banner-unbalanced";
        setText("v1-2d-closure-status-label", "FORCE BUDGET WITHHELD: " + String(resp.force_budget_status));
        setText("v1-2d-closure-verdict", resp.force_budget_diagnostic || "Force budget withheld due to geometry/contour topology gate.");
        setText("v1-2d-continuum-note", "");
      } else if (fb.force_closure_status === "BALANCED_WITHIN_TOLERANCE" && fb.is_force_balanced_to_tolerance === true) {
        closureBanner.className = "v1-banner v1-banner-balanced";
        setText("v1-2d-closure-status-label", "BALANCED_WITHIN_TOLERANCE (< 1e-4 N/m)");
        setText("v1-2d-closure-verdict", fb.discrete_closure_verdict || "");
        setText("v1-2d-continuum-note", fb.continuum_and_unmodeled_supports_note || "");
      } else {
        closureBanner.className = "v1-banner v1-banner-unbalanced";
        setText("v1-2d-closure-status-label", "UNBALANCED_EXCEEDS_TOLERANCE (Discretization Warning)");
        setText("v1-2d-closure-verdict", fb.discrete_closure_verdict || "");
        setText("v1-2d-continuum-note", fb.continuum_and_unmodeled_supports_note || "");
      }
    }

    // 6-component force budget table (N/m)
    if (fb) {
      setText("v1-2d-fx-left", fmtSignedSci(fb.left_electrode_fx_n_per_m));
      setText("v1-2d-fy-left", fmtSignedSci(fb.left_electrode_fy_n_per_m));
      setText("v1-2d-fx-right", fmtSignedSci(fb.right_electrode_fx_n_per_m));
      setText("v1-2d-fy-right", fmtSignedSci(fb.right_electrode_fy_n_per_m));
      setText("v1-2d-fx-box", fmtSignedSci(fb.enclosure_reaction_fx_n_per_m));
      setText("v1-2d-fy-box", fmtSignedSci(fb.enclosure_reaction_fy_n_per_m));
      setText("v1-2d-fx-net", fmtSignedSci(fb.net_electrostatic_force_fx_n_per_m));
      setText("v1-2d-fy-net", fmtSignedSci(fb.net_electrostatic_force_fy_n_per_m));
      setText("v1-2d-fnorm-net", fmtSci(fb.net_electrostatic_force_norm_n_per_m, "N/m"));
      setText("v1-2d-rel-residual", fmtSci(fb.relative_closure_residual));
      setText("v1-2d-tol", fmtSci(fb.tolerance_n_per_m, "N/m") + " (strict <)");
    }

    // Probe & numerical quality diagnostics
    if (resp.solution) {
      setText("v1-2d-stencil-defect", fmtSci(resp.solution.max_discrete_stencil_defect_v, "V") + " (5-pt stencil)");
    }
    var pr = resp.probe;
    if (pr) {
      setText("v1-2d-probe-status", String(pr.probe_status));
      var reqStr = "[" + (pr.requested_probe_xy_m[0] * 1000).toFixed(2) + ", " + (pr.requested_probe_xy_m[1] * 1000).toFixed(2) + "] mm";
      var smpStr = "[" + (pr.sampled_probe_xy_m[0] * 1000).toFixed(2) + ", " + (pr.sampled_probe_xy_m[1] * 1000).toFixed(2) + "] mm";
      setText("v1-2d-probe-coords", reqStr + " -> " + smpStr);
      setText(
        "v1-2d-probe-phi",
        fmtSci(pr.sampled_node_potential_v, "V") + " (sampled lattice node)"
      );
      if (pr.probe_in_vacuum && pr.probe_ex_v_per_m !== null && pr.probe_ey_v_per_m !== null) {
        setText("v1-2d-probe-ex", fmtSignedSci(pr.probe_ex_v_per_m, "V/m"));
        setText("v1-2d-probe-ey", fmtSignedSci(pr.probe_ey_v_per_m, "V/m"));
      } else {
        setText("v1-2d-probe-ex", "N/A (NON_VACUUM)");
        setText("v1-2d-probe-ey", "N/A (NON_VACUUM)");
      }
    }

    setText("v1-2d-mesh-sens-status", String(resp.force_mesh_sensitivity_status || "NOT_ASSESSED"));
    setText("v1-2d-probe-stab-status", String(resp.probe_stability_status || "NOT_ASSESSED"));

    // Multi-grid convergence study card (when present)
    var studyCard = el("v1-2d-study-card");
    var studyRowsEl = el("v1-2d-study-rows");
    if (resp.force_study && studyCard && studyRowsEl) {
      var fs = resp.force_study;
      studyCard.classList.remove("hidden");
      setText(
        "v1-2d-study-order-status",
        "Status: " + String(fs.status) + " | Observed Order: " + String(fs.observed_order_status) + " (all observed_order fields suppressed/null)"
      );
      studyRowsEl.innerHTML = "";
      if (Array.isArray(fs.rows) && fs.rows.length > 0) {
        fs.rows.forEach(function (row) {
          var tr = document.createElement("tr");
          tr.innerHTML =
            "<td>" + String(row.n) + "</td>" +
            "<td>" + (row.grid_spacing_m * 1000.0).toFixed(3) + "</td>" +
            "<td>" + fmtSignedSci(row.left_electrode_fx_n_per_m) + "</td>" +
            "<td>" + fmtSci(row.net_residual_magnitude_n_per_m) + "</td>";
          studyRowsEl.appendChild(tr);
        });
      } else {
        var emptyTr = document.createElement("tr");
        emptyTr.innerHTML = "<td colspan='4'>Study rows withheld (" + String(fs.status) + ")</td>";
        studyRowsEl.appendChild(emptyTr);
      }

      if (fs.derived_sensitivity && fs.derived_sensitivity.per_component_last_step_diff_n_per_m) {
        var diffs = fs.derived_sensitivity.per_component_last_step_diff_n_per_m;
        setText(
          "v1-2d-study-diffs",
          "Last-step |ΔF| (81->101, N/m): left_fx=" + fmtSci(diffs.left_fx) +
            ", right_fx=" + fmtSci(diffs.right_fx) +
            ", box_fx=" + fmtSci(diffs.box_fx) +
            " (max=" + fmtSci(fs.derived_sensitivity.max_component_last_step_diff_n_per_m, "N/m") + ")"
        );
        setText(
          "v1-2d-study-thresholds",
          "Distinct Thresholds: single_solve=1e-4 N/m | study_row=1e-3 N/m | study_convergence=1e-6 N/m."
        );
      } else {
        setText("v1-2d-study-diffs", "");
        setText("v1-2d-study-thresholds", "");
      }
    } else if (studyCard) {
      studyCard.classList.add("hidden");
    }

    render2DCanvas(resp);
  }

  function renderProvenanceCard(resp) {
    setText("v1-prov-model", String(resp.model_id || "—"));
    setText("v1-prov-epistemic", String(resp.epistemic_label || "ESTABLISHED MODEL"));
    setText("v1-prov-fingerprint", String(resp.input_fingerprint || "—"));
    var prov = resp.provenance || {};
    setText("v1-prov-source-sha", String(prov.source_head_sha || "—"));
    if (prov.kernel_blob_sha1) {
      setText(
        "v1-prov-kernels",
        "P0:" + String(prov.kernel_blob_sha1.electrostatics_baseline || "—").slice(0, 12) +
          " / P1:" + String(prov.kernel_blob_sha1.electrostatics_numerics || "—").slice(0, 12)
      );
    }
    setText("v1-prov-thrust", String(prov.whole_body_thrust_status || "NOT MEASURED / NOT ESTABLISHED"));

    var limitsEl = el("v1-prov-limits");
    if (limitsEl && resp.uncertainty_and_limits) {
      var u = resp.uncertainty_and_limits;
      var html = "<strong>Geometry family:</strong> " + escapeHtml(String(u.geometry_family || "—"));
      var notes = [].concat(u.assumptions || [], u.validity_notes || []);
      if (notes.length > 0) {
        html += "<ul>";
        for (var i = 0; i < notes.length; i++) {
          html += "<li>" + escapeHtml(String(notes[i])) + "</li>";
        }
        html += "</ul>";
      }
      limitsEl.innerHTML = html;
    }
  }

  function escapeHtml(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // --- Dedicated 2D Cross-Section Canvas Renderer ---
  function clear2DCanvas() {
    var canvas = el("v1-2d-canvas");
    if (!canvas) return;
    var ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.fillStyle = "#05080d";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    lastCanvasBounds = null;
  }

  function potentialToRGB(val, vMin, vMax) {
    var span = Math.max(Math.abs(vMin), Math.abs(vMax), 1e-12);
    var t = Math.max(-1.0, Math.min(1.0, val / span));
    var r, g, b;
    if (t >= 0) {
      // Dark slate (15,23,42) -> bright red (239,68,68)
      r = Math.round(15 + t * (239 - 15));
      g = Math.round(23 + t * (68 - 23));
      b = Math.round(42 + t * (68 - 42));
    } else {
      // Dark slate (15,23,42) -> electric blue (37,99,235)
      var u = -t;
      r = Math.round(15 + u * (37 - 15));
      g = Math.round(23 + u * (99 - 23));
      b = Math.round(42 + u * (235 - 42));
    }
    return [r, g, b];
  }

  function draw2DArrow(ctx, x0, y0, dx, dy, color, label) {
    var len = Math.hypot(dx, dy);
    if (len < 2) return;
    var ux = dx / len;
    var uy = dy / len;
    var x1 = x0 + dx;
    var y1 = y0 + dy;

    ctx.save();
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.lineWidth = 2.6;
    ctx.beginPath();
    ctx.moveTo(x0, y0);
    ctx.lineTo(x1, y1);
    ctx.stroke();

    var head = 9;
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x1 - head * ux + 4.5 * uy, y1 - head * uy - 4.5 * ux);
    ctx.lineTo(x1 - head * ux - 4.5 * uy, y1 - head * uy + 4.5 * ux);
    ctx.closePath();
    ctx.fill();

    if (label) {
      ctx.font = "bold 11px ui-monospace, SFMono-Regular, Menlo, monospace";
      ctx.fillText(label, x1 + 4, y1 - 4);
    }
    ctx.restore();
  }

  function render2DCanvas(resp) {
    var canvas = el("v1-2d-canvas");
    if (!canvas || !resp || !resp.solution) return;
    var ctx = canvas.getContext("2d");
    if (!ctx) return;

    var sol = resp.solution;
    var phi = sol.potential_v;
    var ex = sol.ex_v_per_m;
    var ey = sol.ey_v_per_m;
    var vac = sol.vacuum_mask;
    var cond = sol.conductor_mask;
    var bnd = sol.boundary_mask;
    var n = Array.isArray(phi) ? phi.length : 0;
    if (n < 2) return;

    var wM = resp.parameters.box_width_m;
    var halfWMm = (wM * 1000.0) / 2.0;

    var vMin = Infinity;
    var vMax = -Infinity;
    for (var ix = 0; ix < n; ix++) {
      for (var iy = 0; iy < n; iy++) {
        var pv = phi[ix][iy];
        if (pv < vMin) vMin = pv;
        if (pv > vMax) vMax = pv;
      }
    }
    setText("v1-2d-cb-min", vMin.toFixed(0) + " V");
    setText("v1-2d-cb-max", (vMax > 0 ? "+" : "") + vMax.toFixed(0) + " V");

    var padLeft = 48;
    var padRight = 20;
    var padTop = 20;
    var padBottom = 42;
    var plotW = canvas.width - padLeft - padRight;
    var plotH = canvas.height - padTop - padBottom;
    var plotSize = Math.min(plotW, plotH);
    var plotX = padLeft + Math.floor((plotW - plotSize) / 2);
    var plotY = padTop + Math.floor((plotH - plotSize) / 2);
    lastCanvasBounds = { plotX: plotX, plotY: plotY, plotSize: plotSize, halfWMm: halfWMm };

    ctx.fillStyle = "#05080d";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // 1. Render [n, n] potential heatmap (axis 0 = x left->right, axis 1 = y bottom->top)
    var off = document.createElement("canvas");
    off.width = n;
    off.height = n;
    var offCtx = off.getContext("2d");
    var img = offCtx.createImageData(n, n);
    var buf = img.data;
    for (var gx = 0; gx < n; gx++) {
      for (var gy = 0; gy < n; gy++) {
        var rowY = (n - 1) - gy; // invert y so +y is upward
        var idx = (rowY * n + gx) * 4;
        if (bnd && bnd[gx][gy]) {
          buf[idx] = 71;
          buf[idx + 1] = 85;
          buf[idx + 2] = 105;
          buf[idx + 3] = 255;
        } else if (cond && cond[gx][gy]) {
          var cv = phi[gx][gy];
          if (cv < 0) {
            buf[idx] = 244; buf[idx + 1] = 63; buf[idx + 2] = 94;
          } else if (cv > 0) {
            buf[idx] = 251; buf[idx + 1] = 146; buf[idx + 2] = 60;
          } else {
            buf[idx] = 16; buf[idx + 1] = 185; buf[idx + 2] = 129;
          }
          buf[idx + 3] = 255;
        } else {
          var rgb = potentialToRGB(phi[gx][gy], vMin, vMax);
          buf[idx] = rgb[0];
          buf[idx + 1] = rgb[1];
          buf[idx + 2] = rgb[2];
          buf[idx + 3] = 255;
        }
      }
    }
    offCtx.putImageData(img, 0, 0);
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(off, plotX, plotY, plotSize, plotSize);

    // 2. Grounded outer box border & x/y (mm) axis ticks
    ctx.strokeStyle = "#94a3b8";
    ctx.lineWidth = 1.5;
    ctx.strokeRect(plotX, plotY, plotSize, plotSize);

    ctx.fillStyle = "#cbd5e1";
    ctx.font = "11px ui-monospace, SFMono-Regular, Menlo, monospace";
    ctx.textAlign = "center";
    ctx.fillText((-halfWMm).toFixed(0), plotX, plotY + plotSize + 15);
    ctx.fillText("0", plotX + plotSize / 2, plotY + plotSize + 15);
    ctx.fillText("+" + halfWMm.toFixed(0), plotX + plotSize, plotY + plotSize + 15);
    ctx.fillText("x (mm)", plotX + plotSize / 2, plotY + plotSize + 32);

    ctx.textAlign = "right";
    ctx.fillText("+" + halfWMm.toFixed(0), plotX - 6, plotY + 8);
    ctx.fillText("0", plotX - 6, plotY + plotSize / 2 + 4);
    ctx.fillText((-halfWMm).toFixed(0), plotX - 6, plotY + plotSize);

    ctx.save();
    ctx.translate(14, plotY + plotSize / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.textAlign = "center";
    ctx.fillText("y (mm)", 0, 0);
    ctx.restore();

    function worldMmToCanvas(xMm, yMm) {
      var u = (xMm + halfWMm) / (2.0 * halfWMm);
      var v = 1.0 - (yMm + halfWMm) / (2.0 * halfWMm);
      return {
        cx: plotX + u * plotSize,
        cy: plotY + v * plotSize
      };
    }

    // 3. Vacuum-only electric-field direction quiver arrows
    var stride = Math.max(3, Math.floor(n / 13));
    ctx.strokeStyle = "rgba(186, 230, 253, 0.55)";
    ctx.lineWidth = 1.1;
    for (var qx = stride; qx < n - stride; qx += stride) {
      for (var qy = stride; qy < n - stride; qy += stride) {
        if (!vac || !vac[qx][qy]) continue;
        var exv = ex[qx][qy];
        var eyv = ey[qx][qy];
        if (exv === null || eyv === null) continue;
        var mag = Math.hypot(exv, eyv);
        if (mag <= 1e-12) continue;
        var pxC = plotX + (qx / (n - 1)) * plotSize;
        var pyC = plotY + (1.0 - qy / (n - 1)) * plotSize;
        var qLen = 10.0;
        var qdx = (exv / mag) * qLen;
        var qdy = -(eyv / mag) * qLen;
        ctx.beginPath();
        ctx.moveTo(pxC - qdx * 0.4, pyC - qdy * 0.4);
        ctx.lineTo(pxC + qdx * 0.6, pyC + qdy * 0.6);
        ctx.stroke();
      }
    }

    // 4. Conductor outlines
    var le = resp.parameters.left_electrode;
    var re = resp.parameters.right_electrode;
    var rPx = (le.radius_m * 1000.0 / (2.0 * halfWMm)) * plotSize;
    var lPos = worldMmToCanvas(le.center_x_m * 1000.0, le.center_y_m * 1000.0);
    var rPos = worldMmToCanvas(re.center_x_m * 1000.0, re.center_y_m * 1000.0);

    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 1.6;
    ctx.beginPath();
    ctx.arc(lPos.cx, lPos.cy, rPx, 0, Math.PI * 2);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(rPos.cx, rPos.cy, rPx, 0, Math.PI * 2);
    ctx.stroke();

    // 5. 2D N/m Force-Budget Arrows (Left, Right, Enclosure)
    var fb = resp.force_budget;
    if (fb && resp.force_budget_status === "COMPUTED") {
      var mL = Math.hypot(fb.left_electrode_fx_n_per_m, fb.left_electrode_fy_n_per_m);
      var mR = Math.hypot(fb.right_electrode_fx_n_per_m, fb.right_electrode_fy_n_per_m);
      var mB = Math.hypot(fb.enclosure_reaction_fx_n_per_m, fb.enclosure_reaction_fy_n_per_m);
      var fMax = Math.max(mL, mR, mB, 1e-18);
      var maxArrowPx = plotSize * 0.22;

      function scaledVec(fx, fy) {
        var mag = Math.hypot(fx, fy);
        if (mag <= 1e-15) return { dx: 0, dy: 0 };
        var len = Math.max(14, (mag / fMax) * maxArrowPx);
        return { dx: (fx / mag) * len, dy: -(fy / mag) * len };
      }

      var vL = scaledVec(fb.left_electrode_fx_n_per_m, fb.left_electrode_fy_n_per_m);
      var vR = scaledVec(fb.right_electrode_fx_n_per_m, fb.right_electrode_fy_n_per_m);
      var vB = scaledVec(fb.enclosure_reaction_fx_n_per_m, fb.enclosure_reaction_fy_n_per_m);

      draw2DArrow(ctx, lPos.cx, lPos.cy, vL.dx, vL.dy, "#f43f5e", "F_L");
      draw2DArrow(ctx, rPos.cx, rPos.cy, vR.dx, vR.dy, "#10b981", "F_R");
      draw2DArrow(ctx, plotX + plotSize * 0.5, plotY + 14, vB.dx, vB.dy, "#f59e0b", "F_enc");
    }

    // 6. Probe crosshair
    if (resp.probe && Array.isArray(resp.probe.requested_probe_xy_m)) {
      var prPt = worldMmToCanvas(
        resp.probe.requested_probe_xy_m[0] * 1000.0,
        resp.probe.requested_probe_xy_m[1] * 1000.0
      );
      ctx.save();
      ctx.strokeStyle = "#38bdf8";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(prPt.cx - 7, prPt.cy);
      ctx.lineTo(prPt.cx + 7, prPt.cy);
      ctx.moveTo(prPt.cx, prPt.cy - 7);
      ctx.lineTo(prPt.cx, prPt.cy + 7);
      ctx.stroke();
      ctx.restore();
    }
  }

  // --- Public Mode & Lifecycle Transitions ---
  function setMode(mode) {
    if (mode !== "schematic_3d" && mode !== "parallel_plate_1d" && mode !== "grounded_box_2d") {
      return;
    }
    if (mode === "schematic_3d") {
      invalidatePending("schematic_3d", "3d_schematic", null, "idle");
      return;
    }
    // If Chapter 5 scalar wave view was active, exit it cleanly when user explicitly enters a computed V1 solver mode
    if (window.__explorer && typeof window.__explorer.isScalarWaveContrastActive === "function" && window.__explorer.isScalarWaveContrastActive()) {
      suppressWaveCallback = true;
      try {
        window.__explorer.toggleScalarWaveContrast(false);
      } finally {
        suppressWaveCallback = false;
      }
    }
    activeModelMode = mode;
    if (mode === "grounded_box_2d") {
      sync2DSliderBounds(false);
    }
    scheduleV1Request("/api/v1/solve", true);
  }

  function onScalarWaveToggle(isWaveActive) {
    if (suppressWaveCallback) return;
    if (isWaveActive) {
      // Section 4.2 & 6.1: Chapter 5 entry while solve/study is in flight immediately aborts & invalidates!
      invalidatePending(activeModelMode, "scalar_wave_contrast", null, "idle");
    } else if (activeModelMode !== "schematic_3d") {
      scheduleV1Request("/api/v1/solve", true);
    }
  }

  function onChapterChange(chapterNum) {
    if (activeModelMode === "schematic_3d") return;
    // Invalidate any in-flight request on chapter transition (Section 4.2)
    if (solveState === "pending") {
      var viewCtx = activeModelMode === "grounded_box_2d" ? "v1_2d" : "v1_1d";
      invalidatePending(activeModelMode, viewCtx, null, "idle");
    }
  }

  function onExploreFreelyToggle(_isFree) {
    if (activeModelMode === "schematic_3d") return;
    if (solveState === "pending") {
      var viewCtx = activeModelMode === "grounded_box_2d" ? "v1_2d" : "v1_1d";
      invalidatePending(activeModelMode, viewCtx, null, "idle");
    }
  }

  // --- Event Binding ---
  function initV1SolverUI() {
    syncTransportUI();
    sync2DSliderBounds(true);
    updateSliderReadoutLabels();
    syncModePanelsAndViewport();

    // Mode buttons
    document.querySelectorAll(".v1-mode-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        setMode(btn.dataset.v1Mode);
      });
    });

    // Retry live bridge button (for HTTP sessions that fell back to offline)
    var retryBtn = el("v1-btn-retry-live");
    if (retryBtn) {
      retryBtn.addEventListener("click", function () {
        if (window.location && window.location.protocol === "file:") return;
        transportMode = "live";
        syncTransportUI();
        if (activeModelMode !== "schematic_3d") {
          scheduleV1Request("/api/v1/solve", true);
        }
      });
    }

    // 1D sliders (150 ms debounced live/offline solve with synchronous pre-debounce invalidation)
    ["v1-1d-voltage", "v1-1d-gap", "v1-1d-area"].forEach(function (id) {
      var input = el(id);
      if (input) {
        input.addEventListener("input", function () {
          updateSliderReadoutLabels();
          if (activeModelMode === "parallel_plate_1d") {
            scheduleV1Request("/api/v1/solve", false);
          }
        });
      }
    });

    // 2D preset & grid resolution selectors
    var presetSel = el("v1-2d-preset");
    if (presetSel) {
      presetSel.addEventListener("change", function () {
        active2DPresetId = presetSel.value;
        sync2DSliderBounds(true);
        if (activeModelMode === "grounded_box_2d") {
          scheduleV1Request("/api/v1/solve", true);
        }
      });
    }

    var gridSel = el("v1-2d-grid-n");
    if (gridSel) {
      gridSel.addEventListener("change", function () {
        sync2DSliderBounds(transportMode === "offline");
        if (activeModelMode === "grounded_box_2d") {
          scheduleV1Request("/api/v1/solve", true);
        }
      });
    }

    // 2D live parameter sliders & probe inputs (150 ms debounced)
    ["v1-2d-vleft", "v1-2d-vright", "v1-2d-gap", "v1-2d-cy", "v1-2d-probe-x", "v1-2d-probe-y"].forEach(function (id) {
      var input = el(id);
      if (input) {
        input.addEventListener("input", function () {
          updateSliderReadoutLabels();
          if (activeModelMode === "grounded_box_2d" && transportMode === "live") {
            scheduleV1Request("/api/v1/solve", false);
          }
        });
      }
    });

    // 2D Convergence Study button
    var studyBtn = el("v1-2d-btn-study");
    if (studyBtn) {
      studyBtn.addEventListener("click", function () {
        if (activeModelMode === "grounded_box_2d") {
          scheduleV1Request("/api/v1/study", true);
        }
      });
    }

    // Click on 2D canvas sets probe [x, y] when live
    var canvas2d = el("v1-2d-canvas");
    if (canvas2d) {
      canvas2d.addEventListener("click", function (ev) {
        if (transportMode !== "live" || !lastCanvasBounds || activeModelMode !== "grounded_box_2d") return;
        var rect = canvas2d.getBoundingClientRect();
        var scaleX = canvas2d.width / Math.max(1, rect.width);
        var scaleY = canvas2d.height / Math.max(1, rect.height);
        var cx = (ev.clientX - rect.left) * scaleX;
        var cy = (ev.clientY - rect.top) * scaleY;
        var b = lastCanvasBounds;
        var u = (cx - b.plotX) / b.plotSize;
        var v = (cy - b.plotY) / b.plotSize;
        if (u < 0 || u > 1 || v < 0 || v > 1) return;
        var xMm = roundTo((u * 2.0 - 1.0) * b.halfWMm, 2);
        var yMm = roundTo(((1.0 - v) * 2.0 - 1.0) * b.halfWMm, 2);
        var pxEl = el("v1-2d-probe-x");
        var pyEl = el("v1-2d-probe-y");
        if (pxEl) pxEl.value = String(xMm);
        if (pyEl) pyEl.value = String(yMm);
        scheduleV1Request("/api/v1/solve", false);
      });
    }

    // Expose public inspection/integration API for explorer.js and Playwright tests
    window.__v1SolverUI = {
      isComputed2DActive: isComputed2DActive,
      setMode: setMode,
      setTransportMode: function (mode) {
        if (mode === "live" || mode === "offline") {
          transportMode = mode;
          syncTransportUI();
        }
      },
      onChapterChange: onChapterChange,
      onScalarWaveToggle: onScalarWaveToggle,
      onExploreFreelyToggle: onExploreFreelyToggle,
      getState: function () {
        return {
          activeModelMode: activeModelMode,
          activeViewContext: activeViewContext,
          activeEndpoint: activeEndpoint,
          transportMode: transportMode,
          solveState: solveState,
          clientStateGeneration: clientStateGeneration,
          currentCanonicalFingerprint: currentCanonicalFingerprint,
          latestDispatchedRequestId: latestDispatchedRequestId,
          isComputed2DActive: isComputed2DActive(),
          lastRenderedResponse: lastRenderedResponse
        };
      }
    };
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initV1SolverUI);
  } else {
    initV1SolverUI();
  }
})();
