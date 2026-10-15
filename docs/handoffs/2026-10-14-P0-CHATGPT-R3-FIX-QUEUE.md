# P0 Scientific Baseline — ChatGPT Independent R3 Findings / Antigravity Fix Queue

**REVIEW DISPOSITION: CHANGES REQUESTED (R3) — RESOLVED FOR R4 RE-REVIEW. PR REMAINS DRAFT.**
Date: 2026-10-14. Persistent handoff and fix ledger resolving independent review findings R3-F1 through R3-F3.

## 1. Immutable Review Baseline (R3)

- **Repository:** https://github.com/aguacatero/scalar-wave-viz
- **Draft PR:** https://github.com/aguacatero/scalar-wave-viz/pull/5
- **Branch:** `scientific-baseline-exodus-2026-10-13`
- **Reviewed Code Baseline (R3):** `120f037491469b576a8f56f3e1b496828cc95dce`
- **Updated Agent Contract HEAD:** `393ea5ef8c5ffd07585f3fddd5d861037c5b21f5`
- **Independent R3 Review URL:** https://github.com/aguacatero/scalar-wave-viz/pull/5#pullrequestreview-5520916593
- **Owner R4 Pickup Instructions:** https://github.com/aguacatero/scalar-wave-viz/pull/5#issuecomment-6172694315
- **Verified CI at R3 HEAD:** Run 38500315579 (20 tests passed, artifact bundle downloaded and inspected).

---

## 2. Unresolved R3 Findings & Exact Resolutions

### R3-F1 — MED: Typed electrode y-position ignored by solver; potential manifest misreporting

- **Finding:** `GroundedBoxConfig` stored `left_electrode.center_y_m` and `right_electrode.center_y_m`, and `generate_manifest` recorded them, but `electrode_pair_in_grounded_box` constructed masks using `(x-left_center_x_m)**2 + y**2` and `(x-right_center_x_m)**2 + y**2`. Electrodes were hardcoded to $y=0$ regardless of config.
- **Resolution:**
  - Added `center_y_m` with default `0.0` to `ElectrodeConfig` and `electrode_pair_in_grounded_box` signature.
  - Added `__post_init__` validation in `ElectrodeConfig` and `GroundedBoxConfig` ensuring all coordinates, voltages, radii, and grid parameters are finite and positive.
  - Implemented exact y-offsets in disk mask formulation:
    `left = (x - left_center_x_m)**2 + (y - left_center_y_m)**2 <= left_radius_m**2`
    `right = (x - right_center_x_m)**2 + (y - right_center_y_m)**2 <= right_radius_m**2`
- **Regression:**
  - `test_electrode_y_position_affects_mask_and_manifest`: sets nonzero vertical offsets ($+5\text{ mm}$ left, $-5\text{ mm}$ right), computes actual conductor node centroids $\bar{y} = \frac{1}{N}\sum y_{\text{cond}}$, asserts $|\bar{y} - y_{\text{target}}| < h$, tests rejection of non-finite y values (`np.nan`, `np.inf`), and verifies manifest geometry serialization.

### R3-F2 — MED: Configured run mesh study silently reverted to default geometry

- **Finding:** `render(config_2d=...)` solved the configured electrode pair, then called `electrode_pair_mesh_study(..., box_width_m=cfg.box_width_m)`, silently reverting electrode positions, radii, and voltages to defaults. For a custom case the manifest presented default study data under a custom configuration record.
- **Resolution:**
  - Updated `electrode_pair_mesh_study` signature to accept `config: GroundedBoxConfig | None = None`.
  - When `config` is provided, mesh refinement varies only $n$, strictly preserving `box_width_m`, `left_electrode`, and `right_electrode` geometry and potentials across all refinement levels.
  - Updated `generate_manifest` to accept `study_config` and serialize `mesh_study_geometry` in `case_1_grounded_box_2d` to ensure complete provenance transparency.
  - Updated `render` to pass active `config=cfg` directly into `electrode_pair_mesh_study`.
- **Regression:**
  - `test_mesh_study_uses_custom_configuration`: runs `electrode_pair_mesh_study` with non-default $50\text{ mm}$ width, asymmetric voltages ($\pm 800\text{ V}$), custom radii ($4\text{ mm}$), and vertical offsets; verifies grid spacing scales correctly and manifest serializes `mesh_study_geometry`.

### R3-F3 — MED: Manifest conflated PR source HEAD SHA with GitHub CI synthetic merge commit

- **Finding:** Downloaded artifact `electrostatics_manifest.json` recorded `git_commit=987f473...` (GitHub Actions synthetic PR merge commit `refs/pull/PR/merge`), while the actual PR source branch HEAD was `120f037...`. Claiming artifact matched PR source HEAD was ambiguous.
- **Resolution:**
  - Implemented `get_git_provenance()` in `examples/electrostatics_demo.py` extracting:
    - `pr_source_head_sha`: exact source branch commit SHA (via `PR_SOURCE_HEAD_SHA` env var or local `git rev-parse HEAD`).
    - `tested_checkout_sha`: actual git commit checked out during execution (`git rev-parse HEAD`).
    - `pr_base_sha`: target base branch commit SHA (`PR_BASE_SHA` or `origin/main`).
    - `ci_event_name`: execution trigger event (`pull_request`, `push`, or `local`).
    - `is_synthetic_pr_merge`: boolean flag indicating whether test ran on GitHub's synthetic merge commit.
  - Bumped schema version to `1.1.0`; manifest explicitly records `git_commit` (pointing to `pr_source_head_sha`), `tested_checkout_sha`, and a dedicated `provenance` block with explanatory notes.
  - Updated `.github/workflows/physics-tests.yml` to inject `PR_SOURCE_HEAD_SHA`, `PR_BASE_SHA`, and `GITHUB_EVENT_NAME` into demo execution, followed by a mandatory provenance assertion gate step.
- **Regression:**
  - `test_manifest_provenance_distinguishes_source_head_from_tested_merge`: tests both live git provenance and simulated GitHub Actions PR environment, confirming that `pr_source_head_sha` matches PR HEAD while `tested_checkout_sha` records checkout commit, and `is_synthetic_pr_merge` is flagged.

---

## 3. Test Suite Summary

- Total unit tests: **23 passed** (0 failures, 0 errors).
- All previous regression gates (F1–F6, R2-F1–R2-F5) remain green.
- Local command: `python3 -m unittest discover -s tests -v`
