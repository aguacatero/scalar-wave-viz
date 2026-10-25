# P1 Scientific Baseline — ChatGPT Independent R11 Sign-Off / Acceptance Ledger

**REVIEW DISPOSITION: ACCEPTED (R11 INDEPENDENT REVIEW) — P1 SCIENTIFIC BASELINE SIGNED OFF. PR REMAINS DRAFT; AWAITING OWNER MERGE AUTHORIZATION.**  
Date: 2026-10-25. Persistent handoff and disposition ledger recording independent scientific sign-off for PR #10 P1 baseline.

---

## 1. Immutable Review Baseline (R11)

- **Repository:** https://github.com/aguacatero/scalar-wave-viz
- **Draft PR:** https://github.com/aguacatero/scalar-wave-viz/pull/10 (base `main` at `174c6b895a0c2ec416b6d46ab9e0835b14a8cb49`)
- **Branch:** `p1-numerics-force-accounting-2026-10-18`
- **Accepted Code HEAD SHA:** `2a87abd0f8de873899f541d521d303d0f4462954`
- **Canonical Independent R11 Review URL:** https://github.com/aguacatero/scalar-wave-viz/pull/10#pullrequestreview-5644613779
- **Verified CI Run at Accepted HEAD:** https://github.com/aguacatero/scalar-wave-viz/actions/runs/40198587319
  - Job logs: **Ran 72 tests / OK** (0 failures, 0 errors)
  - Manifest provenance gate passed
  - Artifact upload confirmed
- **Verified Push CI Run:** https://github.com/aguacatero/scalar-wave-viz/actions/runs/40198583733 (72 tests passed)
- **Independently Inspected Artifact Bundle:**
  - Artifact: `conventional-electrostatics-preview` (ID `12601040946`, digest `sha256:5a434d527d52f56c6bab33705ef2ac5d57de6b317092d52c5b7ab02f24c71aa6`)
  - Verified 2480 × 832 PNG (`electrostatics_baseline.png`)
  - Strict RFC 8259 JSON manifest (`electrostatics_manifest.json`, schema 1.2.0)
  - Tested checkout SHA and PR branch source HEAD recorded with exact provenance
- **Accepted P0 Preservation:** Present `electrostatics_baseline.py` and P0 accepted signoff commit `57067164b47d7d374a1d7bb1c8ce00bb79aa07f8` share identical Git blob `97f65dfa25db7730323edd5e52c98b17371fdeaa`.

---

## 2. Review Findings Verified Resolved in R11

### P1-R10-F1 (Configurable local-budget benchmark parameter validation) — CLOSED
- **Resolution:** In `benchmark_interior_control_volume_budget` (`scalar_wave_3d.py`), `interior_sigma` strictly rejects negative, nonfinite, and boolean values ($\sigma_{\text{int}} \ge 0.0$); `source_amplitude` rejects nonfinite and boolean values while genuinely executing signed amplitudes ($A \ne 0.0$); `n_steps` requires a strict positive integer ($N_{\text{steps}} \ge 1$), preventing zero/negative step vacuous passes; grid dimensions, sponge width, spacing, wave speed, and Courant factor have fail-closed parameter validation guards.
- **Regression:** `tests/test_p1_wave_3d.py` includes comprehensive invalid-input adversarial regressions, signed negative-drive execution with non-zero source work, and machine-precision $H + B + D - W$ closure.

### P1-R10-R1 (Nonblocking reproducibility metadata) — IMPLEMENTED
- **Resolution:** In `examples/electrostatics_demo.py`, added `simulation_protocol` metadata under `exact_discrete_interior_control_volume_budget` recording initial Gaussian pulse form $\phi^0 = \exp(-r^2 / (2 (2 \Delta x)^2))$, staggered previous-step prescription $\phi^{-1} = \phi^0 + 0.5 \Delta t^2 c^2 \nabla^2 \phi^0$, time-independent spatial source $S(x) = A \sin(x)$ restricted to the interior, and uniform interior damping conductivity $\sigma(x) = \sigma_{\text{int}}$.

---

## 3. Independent Numerical Cross-Check

The independent review separately reconstructed the 7-point clamped Laplacian and staggered leapfrog $H_{\text{int}} + B + D - W$ budget in NumPy on a $40^3$ grid with $sw=8$, $dx=1.0\text{ m}$, Courant factor $0.85$, $n=25$ steps, $\sigma_{\text{int}}=0.5$, and $A=+0.1$ versus $A=-0.1$:
- Signed positive drive ($A=+0.1$): $W \approx 87.5743653213\text{ E\_arb}$, relative closure error $3.64 \times 10^{-15} < 10^{-12}$.
- Signed negative drive ($A=-0.1$): $W \approx 91.0891120536\text{ E\_arb}$, relative closure error $1.82 \times 10^{-15} < 10^{-12}$.

Both drives genuinely affect evolution and both independently satisfy the exact discrete local conservation identity.

---

## 4. Test Suite & Baseline Health

- **Total unit tests:** **72 passed** (0 failures, 0 errors).
  - 35 P0 baseline regression tests
  - 16 P1 electrostatics & Maxwell stress tests
  - 21 P1 3D scalar wave numerics tests
- **Local test command:** `python3 -m unittest discover -s tests -v`
- **Demo execution:** `MPLBACKEND=Agg python3 examples/electrostatics_demo.py` generates valid 2480 × 832 PNG and RFC 8259 compliant JSON manifest with full provenance.

---

## 5. Epistemic Scope and Explicit Non-Claims

This sign-off applies strictly to the **P1 conventional electrostatics force accounting and mathematical scalar wave numerics baseline**:
1. **No patent geometry reproduction:** Idealized cylindrical electrode disks in a grounded box; does not reproduce Exodus patent US11511891B2 FIGS. 4–8.
2. **No net thrust claim:** All 2D forces in N/m; whole apparatus balances to 0 N/m. No anomalous propulsion or net mechanical thrust is established.
3. **No physical scalar electrodynamics:** Mathematical wave model only; Moscovium preset is severely under-resolved on coarse grids and remains an unverified WHAT-IF parameter.
4. **No independent physical authority:** Discrete Hamiltonian and continuity identities establish numerical consistency of finite-difference approximations, not physical laws of nature.

---

## 6. Governance & Next Steps

1. **P1 Code Frozen:** Code tree at SHA `2a87abd0f8de873899f541d521d303d0f4462954` is scientifically accepted and frozen.
2. **PR #10 Lifecycle:** PR #10 remains **DRAFT, OPEN, UNMERGED** pending explicit repository owner authorization. Agents must not self-approve or merge.
3. **Phase 2 Authorization:** Phase 2 (Issue #7 / Exodus patent geometry reproduction) is **NOT authorized** until the repository owner explicitly authorizes merging PR #10 and kicking off Phase 2.
4. **Pickup Mode:** `PICKUP: MANUAL-ONLY`.
