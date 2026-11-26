/**
 * Propulsion Explorer V2-A — Force Story UI, Boundary A/B/C Ledgers & V1 State Synchronization
 *
 * Implements Slice V2-A of frozen V2 Design Specification R4 (docs/V2_FORCE_STORY_SPEC.md, §7.1, §7.3, §7.4):
 * - Pull-on-mount + synchronous subscribe() consumption of window.__v1SolverUI
 * - 8-predicate atomic identity & transport-epoch clearing barrier (V2-SPEC-R1-M3, R2-M1, R3-M2)
 * - Strictly segregated Surface A (qualitative 3D DUT H0/H1/H2) vs Surface B (separate 1D/2D P0/P1 analogues)
 * - Synchronized Boundary A/B/C signed ledgers (1D N, 2D signed (Fx, Fy) N/m, 3D PENDING_SCIENTIFIC_ACCEPTANCE)
 * - Independent ConvergenceStudyStatusRecord rendering preserving native { n, reason }[] verbatim (V2-SPEC-R2-L1, R3-M1)
 * - Non-conflating 3D Boundary A/B shell highlight & 2D P1 Boundary A/B/C contour overlay
 * - Full Chapter 5 scalar-wave isolation (V1-B3-POLISH-R1-M1 parity)
 * - Keyboard-accessible tablist & ARIA live regions
 *
 * Slice V2-B (H2 comparators, live clearance sweep, Null-Control Lab) is NOT implemented here.
 */

(function () {
  "use strict";

  var Data = window.V2ForceStoryData;
  if (!Data) return;

  var activeSurface = "surface_a"; // "surface_a" (3D qualitative) | "surface_b" (1D/2D benchmark)
  var show3DBoundaryOverlay = false;
  var show2DContourOverlay = false;
  var lastRenderedV2Generation = 0;
  var lastSnapshot = null;
  var lastEventType = "init";
  var lastV1State = null;

  function el(id) {
    return document.getElementById(id);
  }

  function setText(id, text) {
    var node = el(id);
    if (node) node.textContent = text;
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function fmtSignedSci(val, unit) {
    if (typeof val !== "number" || !Number.isFinite(val)) return "—";
    if (val === 0) return "0.0" + (unit ? " " + unit : "");
    var sign = val > 0 ? "+" : "";
    return sign + val.toExponential(3) + (unit ? " " + unit : "");
  }

  function fmtSci(val, unit) {
    if (typeof val !== "number" || !Number.isFinite(val)) return "—";
    if (val === 0) return "0.0" + (unit ? " " + unit : "");
    return val.toExponential(3) + (unit ? " " + unit : "");
  }

  function renderStaticSections() {
    // 1. Surface A — Qualitative 3D Exodus DUT Hypotheses (ZERO 1D/2D P0/P1 numbers!)
    var surfA = Data.SURFACE_A_QUALITATIVE_3D_DUT;
    setText("v2-surface-a-banner", surfA.banner);
    setText("v2-surface-a-subtitle", surfA.subtitle);

    var cardsHost = el("v2-surface-a-cards");
    if (cardsHost) {
      cardsHost.innerHTML = surfA.hypotheses.map(function (h) {
        var xw = Data.EPISTEMIC_CROSSWALK[h.epistemic_class];
        var pillCls = xw ? xw.pill_class : "pill-unverified";
        var badgeText = xw ? xw.badge_label : h.epistemic_class;
        return (
          '<article class="v2-hyp-card" data-hypothesis-id="' + escapeHtml(h.id) + '">' +
            '<div class="v2-hyp-head">' +
              '<h4 class="v2-hyp-title">' + escapeHtml(h.title) + "</h4>" +
              '<span class="provenance-pill ' + pillCls + '">' + escapeHtml(badgeText) + "</span>" +
            "</div>" +
            '<p class="v2-hyp-text">' + escapeHtml(h.summary) + "</p>" +
            '<p class="v2-hyp-meta"><strong>Boundary Expectation:</strong> ' + escapeHtml(h.boundary_expectation) + "</p>" +
            '<p class="v2-hyp-meta"><strong>3D Quantitative Slot:</strong> <span class="v2-status-chip v2-chip-pending">' + escapeHtml(h.quantitative_3d_status) + "</span></p>" +
            '<p class="v2-hyp-cite"><strong>Sources:</strong> ' + h.citations_html + "</p>" +
          "</article>"
        );
      }).join("");
    }

    // 2. Surface B static banner/subtitle
    var surfB = Data.SURFACE_B_QUANTITATIVE_ANALOGUES;
    setText("v2-surface-b-banner", surfB.banner);
    setText("v2-surface-b-subtitle", surfB.subtitle);

    // 3. Deeper <details> — US11511891B2 Eq. (4) & Eq. (11) Contested-Derivation Audit
    var auditBody = el("v2-h1-audit-tbody");
    if (auditBody) {
      auditBody.innerHTML = Data.H1_CONTESTED_DERIVATION_AUDIT.map(function (item) {
        return (
          "<tr>" +
            "<th scope='row'>" + escapeHtml(item.equation_ref) + "</th>" +
            "<td>" + item.claimed_statement_html + "</td>" +
            "<td>" + escapeHtml(item.audit_note) + "</td>" +
            "<td><span class='v2-status-chip v2-chip-warn'>" + escapeHtml(item.disposition) + "</span></td>" +
          "</tr>"
        );
      }).join("");
    }

    // 4. Deeper <details> — Boundary A/B/C Definitions & Momentum-Transfer Paths
    var bndHost = el("v2-boundary-defs-list");
    if (bndHost) {
      bndHost.innerHTML = Data.BOUNDARY_DEFINITIONS.map(function (b) {
        var pathsHtml = b.momentum_paths.map(function (p) {
          return "<li>" + escapeHtml(p) + "</li>";
        }).join("");
        return (
          '<div class="v2-bnd-def ' + b.color_class + '">' +
            "<h4>" + escapeHtml(b.title) + "</h4>" +
            "<p><strong>Control Volume:</strong> " + escapeHtml(b.control_volume) + "</p>" +
            "<p><strong>Conservation Law:</strong> " + b.conservation_html + "</p>" +
            "<ul>" + pathsHtml + "</ul>" +
          "</div>"
        );
      }).join("");
    }

    // 5. Deeper <details> — Scientific Charter 5-Category Crosswalk
    var cwBody = el("v2-charter-crosswalk-tbody");
    if (cwBody) {
      cwBody.innerHTML = Data.EPISTEMIC_CLASSES.map(function (cls) {
        var info = Data.EPISTEMIC_CROSSWALK[cls];
        return (
          "<tr>" +
            "<th scope='row'><span class='provenance-pill " + info.pill_class + "'>" + escapeHtml(info.badge_label) + "</span></th>" +
            "<td>" + escapeHtml(info.charter_categories.join(" + ")) + "</td>" +
            "<td>" + escapeHtml(info.what_if_rule) + "</td>" +
          "</tr>"
        );
      }).join("");
    }
  }

  function selectSurface(surfaceId) {
    if (surfaceId !== "surface_a" && surfaceId !== "surface_b") return;
    activeSurface = surfaceId;
    var tabA = el("v2-surface-tab-a");
    var tabB = el("v2-surface-tab-b");
    var panelA = el("v2-surface-panel-a");
    var panelB = el("v2-surface-panel-b");

    var isA = surfaceId === "surface_a";
    if (tabA) {
      tabA.classList.toggle("active", isA);
      tabA.setAttribute("aria-selected", isA ? "true" : "false");
      tabA.tabIndex = isA ? 0 : -1;
    }
    if (tabB) {
      tabB.classList.toggle("active", !isA);
      tabB.setAttribute("aria-selected", !isA ? "true" : "false");
      tabB.tabIndex = !isA ? 0 : -1;
    }
    if (panelA) panelA.classList.toggle("hidden", !isA);
    if (panelB) panelB.classList.toggle("hidden", isA);
  }

  function syncOverlaysWithContext(v1State) {
    var isWave = Boolean(v1State && v1State.activeViewContext === "scalar_wave_contrast");
    var is2D = Boolean(v1State && v1State.activeModelMode === "grounded_box_2d" && v1State.activeViewContext === "v1_2d");
    var is3D = Boolean(!isWave && (!v1State || (v1State.activeModelMode === "schematic_3d" && v1State.activeViewContext === "3d_schematic")));

    // 3D Boundary A/B shells are allowed ONLY in 3D schematic mode (NEVER in 2D or Chapter 5 wave)
    if (window.__explorer && typeof window.__explorer.setBoundaryOverlayVisible === "function") {
      window.__explorer.setBoundaryOverlayVisible(Boolean(show3DBoundaryOverlay && is3D));
    }

    var chk3D = el("v2-toggle-3d-boundaries");
    if (chk3D) {
      chk3D.disabled = !is3D;
      chk3D.checked = Boolean(show3DBoundaryOverlay);
      chk3D.setAttribute("aria-disabled", is3D ? "false" : "true");
    }

    var chk2D = el("v2-toggle-2d-contours");
    if (chk2D) {
      chk2D.disabled = !is2D;
      chk2D.checked = Boolean(show2DContourOverlay);
      chk2D.setAttribute("aria-disabled", is2D ? "false" : "true");
    }

    if (window.__v1SolverUI && typeof window.__v1SolverUI.redraw2DCanvasIfReady === "function" && is2D) {
      window.__v1SolverUI.redraw2DCanvasIfReady();
    }
  }

  /**
   * Optional 2D P1 Boundary A/B/C contour overlay drawn cleanly on #v1-2d-canvas.
   * Mirrors exact accepted P1 contour geometry (c_left, c_right around electrodes; c_enclosure_inner near walls).
   */
  function draw2DBoundaryContours(ctx, resp, bounds) {
    if (!show2DContourOverlay || !resp || !resp.parameters || !bounds) return;
    if (lastV1State && lastV1State.activeViewContext === "scalar_wave_contrast") return;
    var p = resp.parameters;
    var le = p.left_electrode;
    var re = p.right_electrode;
    if (!le || !re) return;

    var halfWMm = bounds.halfWMm;
    var plotX = bounds.plotX;
    var plotY = bounds.plotY;
    var plotSize = bounds.plotSize;

    function worldMmToCanvas(xMm, yMm) {
      var u = (xMm + halfWMm) / (2.0 * halfWMm);
      var v = 1.0 - (yMm + halfWMm) / (2.0 * halfWMm);
      return { cx: plotX + u * plotSize, cy: plotY + v * plotSize };
    }

    var pxPerMm = plotSize / (2.0 * halfWMm);
    var padMm = Math.max(1.5, (p.box_width_m * 1000.0 / Math.max(2, p.n - 1)) * 1.5);
    var halfBoxMm = Math.min(le.radius_m * 1000.0 + padMm, halfWMm * 0.42);
    var rBoxPx = halfBoxMm * pxPerMm;

    ctx.save();
    ctx.setLineDash([6, 4]);
    ctx.lineWidth = 1.8;

    // Boundary A electrode contours (c_left, c_right — cyan)
    ctx.strokeStyle = "#38bdf8";
    var lC = worldMmToCanvas(le.center_x_m * 1000.0, le.center_y_m * 1000.0);
    var rC = worldMmToCanvas(re.center_x_m * 1000.0, re.center_y_m * 1000.0);
    ctx.strokeRect(lC.cx - rBoxPx, lC.cy - rBoxPx, rBoxPx * 2, rBoxPx * 2);
    ctx.strokeRect(rC.cx - rBoxPx, rC.cy - rBoxPx, rBoxPx * 2, rBoxPx * 2);

    // Boundary B inner enclosure contour (c_enclosure_inner — amber)
    ctx.strokeStyle = "#f59e0b";
    var insetPx = Math.max(6, (3.0 / Math.max(10, p.n - 1)) * plotSize);
    ctx.strokeRect(plotX + insetPx, plotY + insetPx, plotSize - insetPx * 2, plotSize - insetPx * 2);

    // Compact corner legend label on canvas
    ctx.setLineDash([]);
    ctx.font = "bold 10px ui-monospace, SFMono-Regular, Menlo, monospace";
    ctx.fillStyle = "#38bdf8";
    ctx.textAlign = "left";
    ctx.fillText("Boundary A (c_left, c_right)", plotX + 6, plotY + plotSize - 20);
    ctx.fillStyle = "#f59e0b";
    ctx.fillText("Boundary B (c_enclosure_inner)", plotX + 6, plotY + plotSize - 7);
    ctx.restore();
  }

  function formatQuantityCellHtml(qty) {
    if (!qty || typeof qty !== "object") {
      return '<span class="v2-null-val">—</span>';
    }
    if (qty.status === "COMPUTED_SCALAR_1D") {
      return '<span class="v2-num-val">' + escapeHtml(fmtSignedSci(qty.value_n, "N")) + "</span>";
    }
    if (qty.status === "COMPUTED_VECTOR_2D") {
      return (
        '<div class="v2-vec-cell">' +
          '<span class="v2-num-val">F<sub>x</sub>: ' + escapeHtml(fmtSignedSci(qty.fx_n_per_m, "N/m")) + "</span>" +
          '<span class="v2-num-val">F<sub>y</sub>: ' + escapeHtml(fmtSignedSci(qty.fy_n_per_m, "N/m")) + "</span>" +
          '<span class="v2-vec-mag">|F|: ' + escapeHtml(fmtSci(qty.magnitude_n_per_m, "N/m")) + "</span>" +
        "</div>"
      );
    }
    if (qty.status === "COMPUTED_RESIDUAL_2D") {
      var chipCls = qty.is_force_balanced_to_tolerance ? "v2-chip-ok" : "v2-chip-warn";
      return (
        '<div class="v2-vec-cell">' +
          '<span class="v2-num-val">F<sub>net,x</sub>: ' + escapeHtml(fmtSignedSci(qty.net_fx_n_per_m, "N/m")) + "</span>" +
          '<span class="v2-num-val">F<sub>net,y</sub>: ' + escapeHtml(fmtSignedSci(qty.net_fy_n_per_m, "N/m")) + "</span>" +
          '<span class="v2-vec-mag">|F<sub>net</sub>|: ' + escapeHtml(fmtSci(qty.norm_n_per_m, "N/m")) + "</span>" +
          '<span class="v2-status-chip ' + chipCls + '">' + escapeHtml(qty.force_closure_status) + "</span>" +
          '<span class="v2-residual-tag">DISCRETIZATION RESIDUAL, NOT THRUST</span>' +
        "</div>"
      );
    }
    if (qty.status === "PENDING_SCIENTIFIC_ACCEPTANCE") {
      return '<span class="v2-null-val">—</span> <span class="v2-status-chip v2-chip-pending">PENDING_SCIENTIFIC_ACCEPTANCE (P2)</span>';
    }
    if (qty.status === "WITHHELD_INVALID_CONTOUR_TOPOLOGY" || qty.status === "WITHHELD_INELIGIBLE_PRIMARY_GRID") {
      return '<span class="v2-null-val">—</span> <span class="v2-status-chip v2-chip-warn">' + escapeHtml(qty.status) + "</span>";
    }
    if (qty.status === "REJECTED_INVALID_FORCE_DOMAIN") {
      return '<span class="v2-null-val">—</span> <span class="v2-status-chip v2-chip-err">REJECTED_INVALID_FORCE_DOMAIN (HTTP 400)</span>';
    }
    if (qty.status === "UNAVAILABLE_SOLVER_ERROR") {
      return '<span class="v2-null-val">—</span> <span class="v2-status-chip v2-chip-err">' + escapeHtml(qty.native_v1_code || "UNAVAILABLE_SOLVER_ERROR") + "</span>";
    }
    if (qty.status === "CLEARED_PENDING_OR_INACTIVE") {
      return '<span class="v2-null-val">—</span> <span class="v2-status-chip v2-chip-muted">' + escapeHtml(qty.reason_code || "CLEARED") + "</span>";
    }
    return '<span class="v2-null-val">—</span> <span class="v2-status-chip v2-chip-muted">' + escapeHtml(qty.status) + "</span>";
  }

  function renderConvergenceStudyCard(studyProv, is2D) {
    var card = el("v2-study-provenance-card");
    if (!card) return;
    if (!is2D || !studyProv) {
      card.classList.add("hidden");
      return;
    }

    card.classList.remove("hidden");
    setText("v2-study-status-badge", studyProv.status);
    setText("v2-study-scope-label", "source_scope: " + studyProv.source_scope);
    setText(
      "v2-study-levels-text",
      Array.isArray(studyProv.study_n_list) ? "Levels: [" + studyProv.study_n_list.join(", ") + "]" : "No multi-grid study run yet (click Run Convergence Study in V1 Solver)."
    );

    var failedHost = el("v2-study-failed-levels");
    if (failedHost) {
      if (studyProv.status === "WITHHELD_INELIGIBLE_MESH_LEVEL" || studyProv.status === "WITHHELD_INVALID_CONTOUR_TOPOLOGY") {
        var itemsHtml = studyProv.failed_levels.map(function (fl) {
          return "<li><code>n=" + escapeHtml(String(fl.n)) + "</code>: " + escapeHtml(fl.reason) + "</li>";
        }).join("");
        failedHost.innerHTML =
          '<div class="v2-study-withheld-note">' +
            "<strong>Multi-Grid Study Withheld (" + escapeHtml(studyProv.native_v1_code) + ") — Primary-Grid Signed Force Vectors Preserved Above</strong>" +
            "<p>Zero study rows synthesized (<code>rows: []</code>, <code>derived_sensitivity: null</code>, <code>value: null</code>). Native adapter diagnostics:</p>" +
            "<ul>" + itemsHtml + "</ul>" +
          "</div>";
        failedHost.classList.remove("hidden");
      } else if (studyProv.status === "STABLE_WITHIN_STUDY_TOLERANCE" || studyProv.status === "SENSITIVE_OR_UNBALANCED") {
        failedHost.innerHTML =
          '<p class="v2-study-ok-note">Observed Order Status: <code>' + escapeHtml(studyProv.observed_order_status) + "</code> (all observed_order values suppressed/null by contract).</p>";
        failedHost.classList.remove("hidden");
      } else {
        failedHost.innerHTML = "";
        failedHost.classList.add("hidden");
      }
    }
  }

  function renderSurfaceBSummary(snap, v1State) {
    var summaryHost = el("v2-surface-b-active-summary");
    if (!summaryHost) return;

    if (snap.context_id === "parallel_plate_1d") {
      var posRow = snap.rows[0];
      var negRow = snap.rows[1];
      var netRow = snap.rows[4];
      var isReady = posRow && posRow.quantity && posRow.quantity.status === "COMPUTED_SCALAR_1D";
      summaryHost.innerHTML =
        '<div class="v2-analogue-card">' +
          '<div class="v2-hyp-head">' +
            "<h4>Active Benchmark: 1D Ideal Parallel Plate (N)</h4>" +
            '<span class="provenance-pill pill-established">ESTABLISHED MODEL</span>' +
          "</div>" +
          "<p>" + escapeHtml(Data.SURFACE_B_QUANTITATIVE_ANALOGUES.analogues.parallel_plate_1d.lesson) + "</p>" +
          (isReady
            ? '<dl class="v1-kv-grid">' +
                "<dt>+ Plate Force</dt><dd>" + escapeHtml(fmtSignedSci(posRow.quantity.value_n, "N")) + "</dd>" +
                "<dt>&minus; Plate Force</dt><dd>" + escapeHtml(fmtSignedSci(negRow.quantity.value_n, "N")) + "</dd>" +
                "<dt>Net Pair Force</dt><dd>" + escapeHtml(fmtSignedSci(netRow.quantity.value_n, "N")) + "</dd>" +
              "</dl>"
            : '<p class="v2-cleared-note">1D quantitative readout currently cleared (' + escapeHtml(posRow.quantity.reason_code || posRow.quantity.status) + ").</p>") +
        "</div>";
      return;
    }

    if (snap.context_id === "grounded_box_2d") {
      var lRow = snap.rows[0];
      var rRow = snap.rows[1];
      var dutRow = snap.rows[4];
      var encRow = snap.rows[5];
      var resRow = snap.rows[7];
      var isComp = lRow && lRow.quantity && lRow.quantity.status === "COMPUTED_VECTOR_2D";
      summaryHost.innerHTML =
        '<div class="v2-analogue-card">' +
          '<div class="v2-hyp-head">' +
            "<h4>Active Benchmark: 2D Grounded Box (N/m)</h4>" +
            '<span class="provenance-pill pill-established">ESTABLISHED MODEL</span>' +
          "</div>" +
          "<p>" + escapeHtml(Data.SURFACE_B_QUANTITATIVE_ANALOGUES.analogues.grounded_box_2d.lesson) + "</p>" +
          (isComp
            ? '<dl class="v1-kv-grid">' +
                "<dt>Left Electrode F<sub>x</sub></dt><dd>" + escapeHtml(fmtSignedSci(lRow.quantity.fx_n_per_m, "N/m")) + "</dd>" +
                "<dt>Right Electrode F<sub>x</sub></dt><dd>" + escapeHtml(fmtSignedSci(rRow.quantity.fx_n_per_m, "N/m")) + "</dd>" +
                "<dt>DUT Flux (F<sub>L</sub>+F<sub>R</sub>)<sub>x</sub></dt><dd>" + escapeHtml(fmtSignedSci(dutRow.quantity.fx_n_per_m, "N/m")) + "</dd>" +
                "<dt>Enclosure Reaction F<sub>enc,x</sub></dt><dd>" + escapeHtml(fmtSignedSci(encRow.quantity.fx_n_per_m, "N/m")) + "</dd>" +
                "<dt>|F<sub>net</sub>| Closure Residual</dt><dd>" + escapeHtml(fmtSci(resRow.quantity.norm_n_per_m, "N/m")) + " (" + escapeHtml(resRow.quantity.force_closure_status) + ")</dd>" +
              "</dl>"
            : '<p class="v2-cleared-note">2D quantitative readout currently unavailable/cleared (' + escapeHtml(lRow.quantity.reason_code || lRow.quantity.native_v1_code || lRow.quantity.status) + ").</p>") +
        "</div>";
      return;
    }

    summaryHost.innerHTML =
      '<div class="v2-analogue-card">' +
        "<h4>No 1D/2D P0/P1 Benchmark Active</h4>" +
        "<p>Currently viewing the provisional 3D Exodus schematic. Select <strong>1D Parallel Plate (N)</strong> or <strong>2D Grounded Box (N/m)</strong> below to inspect a separate quantitative P0/P1 momentum-accounting benchmark.</p>" +
      "</div>";
  }

  function renderSnapshot(v1State, eventType) {
    lastV1State = v1State || null;
    lastEventType = eventType || "sync";

    var isWave = Boolean(v1State && v1State.activeViewContext === "scalar_wave_contrast");
    var wavePanel = el("v2-wave-isolation-panel");
    var mainBody = el("v2-story-main-content");

    if (wavePanel) wavePanel.classList.toggle("hidden", !isWave);
    if (mainBody) mainBody.classList.toggle("hidden", isWave);

    var syncCheck = Data.evaluateV1SyncPredicates(v1State, lastRenderedV2Generation);
    var snap = Data.buildForceLedgerSnapshot(v1State, lastRenderedV2Generation);
    if (syncCheck.ok && v1State && typeof v1State.clientStateGeneration === "number") {
      lastRenderedV2Generation = v1State.clientStateGeneration;
    }
    lastSnapshot = snap;

    // Context & transport pills
    var ctxLabel =
      isWave ? "MATHEMATICAL TOY (ISOLATED)" :
      snap.context_id === "parallel_plate_1d" ? "1D PARALLEL PLATE (N)" :
      snap.context_id === "grounded_box_2d" ? "2D GROUNDED BOX (N/m)" :
      "3D EXODUS SCHEMATIC (P2 PENDING)";
    setText("v2-context-pill", ctxLabel);

    var epBadge = el("v2-epistemic-badge");
    if (epBadge) {
      if (isWave) {
        epBadge.textContent = "MATHEMATICAL TOY (ISOLATED)";
        epBadge.className = "provenance-pill pill-whatif";
      } else if (snap.context_id === "schematic_3d_exodus") {
        epBadge.textContent = "PROVISIONAL ILLUSTRATIVE SCENE";
        epBadge.className = "provenance-pill pill-provisional";
      } else {
        epBadge.textContent = "ESTABLISHED MODEL";
        epBadge.className = "provenance-pill pill-established";
      }
    }

    var tPill = el("v2-transport-pill");
    if (tPill) {
      var tLabel =
        snap.transport_mode === "static_schematic" ? "STATIC 3D SCHEMATIC" :
        snap.transport_mode === "offline" ? "SOLVER BRIDGE OFFLINE" :
        "LIVE P0/P1 BRIDGE";
      tPill.textContent = tLabel;
      tPill.classList.toggle("offline", snap.transport_mode === "offline");
    }

    // Sync identity & status banner
    var idText =
      "Context: " + snap.context_id +
      " | Unit Domain: " + snap.unit_domain +
      " | Gen: " + String(snap.sync_identity.client_state_generation) +
      " | Transport Epoch: " + String(snap.sync_identity.transport_epoch) +
      " | Origin: " + String(snap.sync_identity.response_origin_transport || "none");
    setText("v2-sync-identity-line", idText);

    var statusBanner = el("v2-ledger-status-banner");
    if (statusBanner) {
      if (isWave) {
        statusBanner.className = "v1-banner v1-banner-warn";
        statusBanner.textContent = "Chapter 5 scalar-wave contrast is active. Electrostatic ledgers and solver triggers are isolated.";
      } else if (snap.context_id === "schematic_3d_exodus") {
        statusBanner.className = "v1-banner v1-banner-warn";
        statusBanner.textContent = "3D Exodus quantitative whole-device forces are PENDING_SCIENTIFIC_ACCEPTANCE (Track B P2). Zero 1D N or 2D N/m values are projected onto the 3D blade.";
      } else if (syncCheck.ok) {
        var firstQ = snap.rows[0].quantity;
        if (firstQ.status === "WITHHELD_INVALID_CONTOUR_TOPOLOGY" || firstQ.status === "WITHHELD_INELIGIBLE_PRIMARY_GRID") {
          statusBanner.className = "v1-banner v1-banner-error";
          statusBanner.textContent = "Native V1 status " + firstQ.native_v1_code + " (HTTP 200): " + firstQ.diagnostic;
        } else {
          statusBanner.className = "v1-banner v1-banner-balanced";
          statusBanner.textContent = "Synchronized verified " + snap.unit_domain + " P0/P1 ledger (origin: " + snap.sync_identity.response_origin_transport + ", epoch " + String(snap.sync_identity.transport_epoch) + "). Separate idealized benchmark — NOT 3D Exodus geometry.";
        }
      } else if (v1State && v1State.solveState === "error") {
        var errQ = snap.rows[0].quantity;
        statusBanner.className = "v1-banner v1-banner-error";
        statusBanner.textContent = "Ledger cleared on solver error (" + String(errQ.native_v1_code || errQ.status) + "): " + String(errQ.diagnostic || "");
      } else {
        statusBanner.className = "v1-banner v1-banner-warn";
        var reasonMsg = syncCheck.reasonCode === "TRANSPORT_EPOCH_MISMATCH"
          ? "Transport mode changed (TRANSPORT_EPOCH_MISMATCH) — previous numeric ledger cleared synchronously until a fresh verified response publishes under the new transport epoch."
          : "Numeric ledger cleared (" + String(syncCheck.reasonCode || "PENDING_OR_IDLE") + ") — awaiting verified P0/P1 response.";
        statusBanner.textContent = reasonMsg;
      }
    }

    // Render Three-Boundary Ledger Table
    var tbody = el("v2-ledger-tbody");
    if (tbody) {
      var boundaryLabels = {
        boundary_a_dut: "Boundary A (DUT)",
        boundary_b_environment: "Boundary B (Env)",
        boundary_c_closed: "Boundary C (Closed)"
      };
      tbody.innerHTML = snap.rows.map(function (row) {
        return (
          '<tr data-row-id="' + escapeHtml(row.row_id) + '" data-source-scope="' + escapeHtml(row.source_scope) + '" data-row-status="' + escapeHtml(row.quantity.status) + '">' +
            '<td><span class="v2-bnd-tag v2-tag-' + escapeHtml(row.boundary) + '">' + escapeHtml(boundaryLabels[row.boundary] || row.boundary) + "</span></td>" +
            "<th scope='row'>" + escapeHtml(row.component_label) + "</th>" +
            "<td>" + formatQuantityCellHtml(row.quantity) + "</td>" +
          "</tr>"
        );
      }).join("");
    }

    // Render independent Convergence Study Provenance card (V2-SPEC-R2-L1, V2-SPEC-R3-M1)
    renderConvergenceStudyCard(snap.convergence_study_provenance, snap.context_id === "grounded_box_2d" && !isWave);

    // Render Surface B summary
    renderSurfaceBSummary(snap, v1State);

    // Sync 3D and 2D non-conflating overlays
    syncOverlaysWithContext(v1State);
  }

  function bindEvents() {
    var tabA = el("v2-surface-tab-a");
    var tabB = el("v2-surface-tab-b");
    if (tabA) {
      tabA.addEventListener("click", function () { selectSurface("surface_a"); });
      tabA.addEventListener("keydown", function (ev) {
        if (ev.key === "ArrowRight" || ev.key === "ArrowLeft") {
          ev.preventDefault();
          selectSurface("surface_b");
          if (tabB) tabB.focus();
        }
      });
    }
    if (tabB) {
      tabB.addEventListener("click", function () { selectSurface("surface_b"); });
      tabB.addEventListener("keydown", function (ev) {
        if (ev.key === "ArrowRight" || ev.key === "ArrowLeft") {
          ev.preventDefault();
          selectSurface("surface_a");
          if (tabA) tabA.focus();
        }
      });
    }

    var chk3D = el("v2-toggle-3d-boundaries");
    if (chk3D) {
      chk3D.addEventListener("change", function () {
        show3DBoundaryOverlay = Boolean(chk3D.checked);
        syncOverlaysWithContext(lastV1State);
      });
    }

    var chk2D = el("v2-toggle-2d-contours");
    if (chk2D) {
      chk2D.addEventListener("change", function () {
        show2DContourOverlay = Boolean(chk2D.checked);
        syncOverlaysWithContext(lastV1State);
      });
    }

    // Quick context buttons inside Surface B (delegate strictly to V1 setMode, never bypassing Chapter 5 exit)
    document.querySelectorAll(".v2-context-jump-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var mode = btn.dataset.v2JumpMode;
        if (window.__v1SolverUI && typeof window.__v1SolverUI.setMode === "function") {
          window.__v1SolverUI.setMode(mode);
        }
      });
    });
  }

  function initV2ForceStoryUI() {
    renderStaticSections();
    bindEvents();
    selectSurface("surface_a");

    if (window.__v1SolverUI) {
      if (typeof window.__v1SolverUI.setV2CanvasOverlayRenderer === "function") {
        window.__v1SolverUI.setV2CanvasOverlayRenderer(draw2DBoundaryContours);
      }
      // Pull-on-mount synchronous read (§7.1.1)
      if (typeof window.__v1SolverUI.getState === "function") {
        renderSnapshot(window.__v1SolverUI.getState(), "init");
      }
      // Register synchronous push subscriber (§7.1.1)
      if (typeof window.__v1SolverUI.subscribe === "function") {
        window.__v1SolverUI.subscribe(function (evt) {
          if (evt && evt.state) {
            renderSnapshot(evt.state, evt.eventType);
          }
        });
      }
    } else {
      renderSnapshot(null, "init");
    }

    window.__v2ForceStoryUI = {
      getSnapshot: function () {
        return lastSnapshot;
      },
      getState: function () {
        return {
          activeSurface: activeSurface,
          show3DBoundaryOverlay: show3DBoundaryOverlay,
          show2DContourOverlay: show2DContourOverlay,
          lastRenderedV2Generation: lastRenderedV2Generation,
          lastEventType: lastEventType,
          snapshot: lastSnapshot
        };
      },
      selectSurface: selectSurface,
      set3DBoundaryOverlay: function (visible) {
        show3DBoundaryOverlay = Boolean(visible);
        syncOverlaysWithContext(lastV1State);
      },
      set2DContourOverlay: function (visible) {
        show2DContourOverlay = Boolean(visible);
        syncOverlaysWithContext(lastV1State);
      }
    };
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initV2ForceStoryUI);
  } else {
    initV2ForceStoryUI();
  }
})();
