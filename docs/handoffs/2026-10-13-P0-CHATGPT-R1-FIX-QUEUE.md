# P0 Scientific Baseline — ChatGPT Independent R1 Findings / Antigravity Fix Queue

**REVIEW DISPOSITION: CHANGES REQUESTED — NOT APPROVED FOR MERGE.**
Date: 2026-10-13. This file is a persistent implementation + re-review handoff, not approval or a scientific validation certificate.

## Immutable review baseline

- Repository: https://github.com/aguacatero/scalar-wave-viz
- Draft PR: https://github.com/aguacatero/scalar-wave-viz/pull/5
- Branch: `scientific-baseline-exodus-2026-10-13`
- **Code and documentation HEAD reviewed:** `cee27d1c503ef714b19fb17bb7821ec8c6dcb0fc`
- Base: `edbfeba325eb6c9a76080fea7de94df5f8fd3614`
- **GitHub independent COMMENT review:** https://github.com/aguacatero/scalar-wave-viz/pull/5#pullrequestreview-5508073654
- Inline comments: `electrostatics_baseline.py`, `examples/electrostatics_demo.py`, `docs/EXODUS_MODEL_CONTRACT.md`, and `.github/workflows/physics-tests.yml`.
- At reviewed HEAD, both push/PR CI succeeded; PR run: https://github.com/aguacatero/scalar-wave-viz/actions/runs/38441804640
- 8 unit tests passed; figure generation and artifact upload passed. The latest artifact is called `conventional-electrostatics-preview` (30-day retention).
- Reviewer downloaded and inspected the CI-produced 2240×768 PNG; it contains potential, field and independent analytic force panels.
- **Important:** the software has not reproduced an Exodus patent embodiment, found a measured anomalous force, or modeled physical scalar-wave material properties.

## Scientific checks independently passed (limited)

1. Ideal vacuum parallel-plate pressure `p=0.5*epsilon0*(V/d)**2` and signed opposing local plate-force magnitudes follow standard assumptions.
2. Ideal plate field energy `U=0.5*epsilon0*(V/d)**2*A*d` has correct SI units.
3. Five-point Laplace Dirichlet stencil with 4 on diagonal, -1 at unknown nearest neighbors and fixed neighboring potentials on RHS is correct for a homogeneous vacuum rectangular grid.
4. Electric field sign `E=-grad(V)` and V/m coordinate units are correct where a resolved vacuum gradient exists.
5. The grounded outer boundary is **a real external conductor**, not free space. Figure C is **a distinct analytic plate case** and cannot be used as field-derived force from panels A/B.

These narrow statements do not validate fields at curved conductor surfaces or propulsion claims.

## Actionable fix queue (complete in order, then obtain independent re-review)

### F1 — HIGH / BLOCKER: solver returns nonphysical electric fields in conductors

- Source: `electrostatics_baseline.py` lines 96–98 and `examples/electrostatics_demo.py` lines 18–33.
- The returned public `FieldSolution.ex_v_per_m` / `ey_v_per_m` arrays evaluate `np.gradient` through fixed conducting cells. Even when potentials are constant inside an ideal conductor, grid-gradient samples immediately adjacent to the surface inside that conductor become nonzero.
- Independent numerical reconstruction of the current five-point stencil and default config at `n=101`: max reported |E| on conductor voxels approximately **85.6 kV/m**. The plot masks the cells, but the underlying API still offers those numbers.
- **Fix:** explicitly distinguish vacuum interior, ideal-conductor interior and fixed external boundary in output metadata. Provide masked/undefined field samples for conductor/boundary nodes and a separate clearly documented one-sided interface/Maxwell-stress path. Do not confuse fictitious interface-gradient samples with physical interior conductor E.
- **Regression:** fail if the public 'physical vacuum E' representation includes non-vacuum cells as meaningful finite field values; check known analytic uniform-field signs/units and validation on interfaces; ensure plot uses the same domain mask.

### F2 — HIGH / BLOCKER: plotted quantitative |E| lacks geometry/grid convergence

- Source: `electrostatics_baseline.py` lines 120–138; `examples/electrostatics_demo.py` lines 36–57.
- Circular electrodes are voxelized using a sharp binary test; peak vacuum field and local gradient change as the approximated boundary steps shift.
- Independent stencil reconstruction with fixed 40 mm enclosure, electrode centers ±8 mm, radii 3 mm and potentials ±500 V: maximum vacuum |E| ≈ **126.7, 141.1, 166.8 kV/m** at `n=41,101,161` respectively. These are diagnostic grid sensitivity numbers, **not experimentally measured uncertainties or established continuum limits**.
- **Fix:** implement mesh-refinement studies, compare local field at fixed physical probe points separated from staircase boundaries, track normalized domain/grid error and electric flux/field symmetry; compare an analytic/numerically independent benchmark (e.g., concentric-cylinder Laplace problem or bipolar cylinder solution as applicable). Until results converge, mark figure heatmap `ILLUSTRATIVE / NON-CONVERGED`, avoid displaying unsupported claims based on the maximum.
- **Regression:** automated check that fixed-physical-location field error decreases with refinement for a source-backed benchmark; output convergence table alongside example image or mark explicit nonvalidated status.

### F3 — MED: visually juxtaposed but physically unrelated force panel and circularity in net test

- Source: `examples/electrostatics_demo.py` lines 37–69; `electrostatics_baseline.py` lines 31–42; corresponding tests.
- A/B use two circular electrode cross-sections at **+500/-500 V**, 3 mm radius in a **40 mm** grounded box; C uses separate **1,000 V**, **1 mm gap**, **1 cm²** analytic ideal parallel plates. The latter gives `p≈4.427 Pa`, `|F|≈442.7 µN`; it is **NOT** force from A/B.
- Even though the global title uses “separate”, viewers can visually associate the force bars with A/B; force-sign convention (+x for left plate's attraction to right, for example) is not explicit.
- `net_pair_force_n=0.0` is hardcoded and its test merely verifies the constant. No numerical force balance is validated.
- **Fix:** annotate explicit geometry/voltage/dimensions and provenance **per panel** or export two visibly separate figures; explicitly define signed +x and opposite reactions; compute analytic net as sum of two signed terms; verify with independent force/energy relation including voltage-source-work bookkeeping.
- **Regression:** test the output config labels and net computation; compare numeric ideal plate force scaling and independent formula.

### F4 — MED: patent H1 claim should explicitly flag a contested derivation

- Source: `docs/EXODUS_MODEL_CONTRACT.md` lines 15–25.
- In US11511891B2 (https://patents.google.com/patent/US11511891B2/en), the inventor posits `d(Ut)=0` at Eq.(4) by analogy with stationary action before deriving a nonzero Eq.(11) `epsilon0*(E2²*A2 − E1²*A1)`. The stationarity of action `δS=0` does not imply the pointwise identity `d(Ut)=0`; patent issuance does not validate the step.
- Standard vacuum electrostatic traction uses the Maxwell stress tensor, with local flat conducting surface pressure `epsilon0*E²/2` (when applicable). Do **not** silently blend this with the patent's claimed expression.
- **Fix:** maintain a citation-bound proof-obligation/derivation ledger for patent equations (especially Eq.(4)–(11)), define whole-system momentum balance and any environment momentum exchange, and explicitly document unverified steps. Assign this as a mandatory gate for P2, not as a completed validation claim in P0.
- **Regression:** documents/tests validate that H0 and H1 outputs remain separate, units checked and claims visibly labeled.

### F5 — MED: no pinned computational environment / machine-readable run provenance

- Source: `.github/workflows/physics-tests.yml` lines 9–19 and `requirements.txt`.
- CI directly installs floating `numpy scipy matplotlib`, while requirements are also unpinned. PNG does not record validated status, fixed-potential shapes, boundary, selected physical parameters, code SHA or package versions as a paired artifact.
- **Fix:** lock tested dependency versions, have CI install from the same lock, export JSON run manifest with full geometry, voltages, grid, equations/units/boundaries, SHA, package versions and validation status; upload alongside PNG.
- **Regression:** CI verifies manifest schema and config values correspond exactly to the simulation run.

### F6 — LOW: stale roadmap checkbox

- Source: `docs/ROADMAP.md` line 11.
- CI confirmation checkbox is unchecked despite confirmed runs. Update after inspecting the new HEAD; do not conflate “CI passed” with physical validation.

## Ordering and gate

1. F1 + F2: essential for the credibility of numerical field results. Smallest safe P0 fallback is to label fields explicitly illustrative/unvalidated, mask nonphysical conductor fields in API, and defer full force analysis/convergence to P1 with a clear bounded acceptance statement. A quantitative publication claim must still be blocked.
2. F3: correct both visual presentation and test semantics.
3. F4/F5: record scientific and reproducibility gates, ensure no misleading current claims; may stage additional work for P1/P2 if honest scope is maintained.
4. F6 housekeeping.
5. Run entire test suite, generate/inspect **new** CI PNG, inspect artifacts. Do not claim an independent signoff from passing CI.

## Instructions to Antigravity / Hermes

- Read `AGENTS.md` and this entire report before changing physics code.
- Work on the existing PR #5 **draft branch**; no merge, no self-approval, no bypassing adversarial review.
- Use tests-first changes where practicable; implement each fix with a regression case and explicit comments closing F1–F6.
- Avoid installing unnecessary skills or changing the primary physics theory.
- Push an updated **code SHA**, verify GitHub checks at exact SHA, and update the canonical handoff with tests, residual issues, and revision.
- Then write on the PR: **READY FOR CHATGPT INDEPENDENT RE-REVIEW** with links to this report, changed diff, current SHA, test commands, and output artifacts. Do not mark this review accepted without external examination.

## Instructions to next independent reviewer (new ChatGPT session)

1. Retrieve exact current PR head before starting; compare against original `cee27d1...` and this report.
2. Reproduce F1 interior conductor test and F2 mesh study at explicitly specified same physical configurations; independently confirm fixes, not only new test expectations.
3. Open new CI generated field figure and paired manifest; validate chart labels and geometry consistency.
4. Recheck patent H0/H1 physical distinction and whether derivation Eq.(4)–(11) is explicitly qualified.
5. Evaluate unresolved items, assign HIGH/MED/LOW and write review directly on PR. Approve no speculative physics from aesthetic results.
6. Leave PR draft until acceptance and **user-authorized** merge.

**Current R1 outcome: CHANGES REQUESTED, no merge, no independent signoff.**
