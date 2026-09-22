# Jev Integration Proposal — scalar-wave-viz

## Status

**Proposal only. Do not treat Jev as a physics authority.**

This proposal asks for a deep review of Jev as an epistemic-status and claim-language gate. The repository deliberately mixes established equations/data, numerical models, predictions, and speculative extrapolations; Jev may be useful for consistently flagging when prose crosses those boundaries.

## Why this repo may benefit

The primary risk is not arithmetic—it is category slippage: a visualization assumption or speculative material property can be phrased as if it were measured physics. A constrained judge operating on structured claim provenance may improve labeling consistency and reviewer trust.

**Working benefit hypothesis:** reduce overstatement and improve separation of measured, established, modeled, predicted, extrapolated, and unsupported claims.

## Candidate decision boundaries

1. Scientific sentence/claim → epistemic category.
2. Notebook output → simulation result versus physical inference.
3. Measured isotope/material property versus theoretical prediction versus speculative parameter.
4. README/caption wording → appropriately qualified versus overstated.
5. Claim with mixed provenance → human/scientific review.

## What Jev must not do

- calculate or validate FDTD/nuclear-physics mathematics;
- determine whether a cited scientific value is correct without verified source data;
- turn simulation behavior into experimental evidence;
- establish scalar-wave or exotic-material physics;
- infer properties of Moscovium beyond supplied sources/models;
- replace unit tests, numerical validation, literature verification, or expert review.

## Proposed record

```json
{
  "claim": "A stable Moscovium isotope would nearly trap the modeled wave.",
  "claim_context": "README description of simulation preset",
  "provenance": [
    {"component": "isotope stability", "status": "model_prediction", "source": "..."},
    {"component": "wave speed preset", "status": "speculative_parameter", "source": "project assumption"}
  ],
  "simulation_support": true,
  "experimental_support": false
}
```

Source/provenance status must be determined by verified metadata, not guessed by Jev.

## Candidate questions

- `claim_is_supported_as_experimental_fact` → yes/no
- `claim_is_model_dependent` → yes/no
- `claim_contains_speculative_component` → yes/no
- `wording_overstates_available_support` → yes/no
- `recommended_epistemic_label` → choice: `measured`, `established_theory`, `model_output`, `prediction`, `speculative_extrapolation`, `unsupported`, `human_review`
- `qualification_required` → yes/no

## Benchmark requirement

Build a gold set from README/notebook claims and label them independently using source provenance. Include clearly established statements, model results, predictions, deliberate speculation, and misleadingly phrased examples.

Compare Jev to deterministic provenance labels and simple keyword rules. Measure overstatement detection, false downgrades of established facts, calibration, consistency across equivalent phrasing, and whether the system adds value beyond explicit metadata.

## Shadow mode

Run Jev as a linter that emits review findings only. It should not rewrite notebooks/README automatically. Human review decides whether wording changes are appropriate.

## Architecture requirements

- Provenance/source verification precedes Jev.
- Mathematical/numerical validation remains deterministic.
- One Jev adapter or offline lint command.
- `OPENROUTER_API_KEY` via secret store only.
- Pin/log model version during benchmark.
- Version question sets.
- API failure produces no claim-status upgrade.

## Required deep-review deliverable

Create `docs/jev/DEEP_REVIEW.md` with:

1. `GO`, `MODIFY`, or `NO-GO`.
2. Inventory of claim-generation surfaces (README/notebooks/captions).
3. Deterministic provenance labeling that should be implemented first.
4. Minimal record/question set.
5. Gold-set benchmark design.
6. False-overstatement and false-downgrade analysis.
7. Shadow-linter design.
8. Expected scientific-communication benefit.
9. Implementation plan only if justified.

## Review instruction for Claude/Codex

Assume explicit provenance metadata plus deterministic linting may be sufficient. Recommend Jev only if repeated semantic wording judgments remain and benchmark evidence shows it catches meaningful epistemic slippage without creating false authority.
