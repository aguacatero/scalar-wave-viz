# Jev Integration Proposal — scalar-wave-viz

## Status

**Proposal only. Do not treat Jev as a physics authority.**

Evaluate Jev only as an epistemic-status and claim-language linter after source provenance and numerical validation are established by deterministic/expert methods.

## Required deep-review skill stack

Sources:
- Matt Pocock: `https://github.com/mattpocock/skills`
- K-Dense Scientific Agent Skills: `https://github.com/K-Dense-AI/scientific-agent-skills`

Use in order:

1. **Matt `research`** — map README/notebook/caption claim surfaces, numerical models, source/provenance metadata, and current validation paths. Output `docs/jev/review/01_REPO_MAP.md`.
2. **K-Dense `scientific-critical-thinking`** — red-team category slippage between measured, established theory, simulation output, prediction, extrapolation, and unsupported claim; inspect bias, causal overreach, and wording that exceeds evidence. Output `02_SCIENTIFIC_CRITIQUE.md`.
3. **K-Dense `peer-review`** — review the proposed claim-status method for claim/evidence alignment, reproducibility, citation/source support, and specialist physics-review needs. Output `03_PEER_REVIEW.md`.
4. **K-Dense `literature-review`** — use for bounded verification of relevant physical/material claims and provenance standards; do not use Jev or the literature-review skill to turn speculation into evidence. Output `04_METHOD_LITERATURE.md` when used.
5. **K-Dense `experimental-design`** — design a benchmark comparing explicit provenance metadata + deterministic lint rules, human/expert labels, and Jev on development and untouched holdout claims. Include clearly established, model-dependent, speculative, and misleadingly phrased examples. Output `05_BENCHMARK_DESIGN.md`.
6. **K-Dense `statistical-power`** — determine enough labeled claims to estimate false-overstatement and false-downgrade rates with useful precision. Output `06_SAMPLE_PRECISION.md`.
7. **K-Dense `statistical-analysis`** — predefine overstatement detection, false downgrades of established facts, calibration, phrasing sensitivity, and added value beyond provenance metadata. Output `07_ANALYSIS_PLAN.md` and reuse after shadow mode.
8. **Matt `domain-modeling`** — define measured, established theory, model output, prediction, speculative extrapolation, unsupported, provenance, qualification, and human review. Output `08_DECISION_MODEL.md`.
9. **Matt `codebase-design`** — design one offline/lint-style Jev seam after provenance and numerical checks, with fake adapter, logs, model/question versioning, and no automatic scientific upgrade. Output `09_ARCHITECTURE.md`.
10. **Matt `grill-with-docs`** — resolve label taxonomy, acceptable false-downgrade/overstatement rates, shadow behavior, and what always requires expert review. Output `10_DECISIONS.md`.
11. Create `docs/jev/DEEP_REVIEW.md` with `GO | MODIFY | NO-GO`, claim-surface inventory, deterministic provenance requirements, scientific critique, benchmark/holdout plan, specialist review needs, shadow-linter design, and implementation plan only if justified.
12. **After GO/MODIFY:** Matt `to-spec`; after implementation Matt `code-review`; then K-Dense `statistical-analysis` on untouched/shadow results.

## Jev constraints

Jev must not validate physics mathematics, verify source values from memory, convert simulation behavior into experimental evidence, establish scalar-wave/exotic-material physics, infer Moscovium properties beyond supplied sources, or replace numerical tests/literature verification/expert review.

## Candidate questions

- `claim_is_supported_as_experimental_fact` → yes/no
- `claim_is_model_dependent` → yes/no
- `claim_contains_speculative_component` → yes/no
- `wording_overstates_available_support` → yes/no
- `recommended_epistemic_label` → `measured | established_theory | model_output | prediction | speculative_extrapolation | unsupported | human_review`
- `qualification_required` → yes/no

## Review instruction

Assume explicit provenance metadata plus deterministic linting may be sufficient. Keep Jev only if repeated semantic wording judgments remain and untouched benchmark evidence shows it catches meaningful epistemic slippage without creating false authority.
