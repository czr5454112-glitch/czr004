# Repair5G.5.41 Balanced Per-Stratum Static-Flow Safe-Region Mining Plan

## Objective

G5.41 follows the G5.40 negative global-candidate result by changing the safe-region unit from a global parameter candidate to:

```text
candidate_id x map_family x agents x budget_ms x iteration_bucket
```

The round asks whether static-flow-relative parameter candidates that are unsafe globally can still be safe and useful in deployable strata after balanced seed-block support. Runtime, Phase5.5, Phase6, learned-runtime, and AAAI claims remain closed.

## Guardrails

- Do not edit `external/lacam2/lacam2/**`.
- Do not change PIBT conflict semantics, candidate domain, agent actions, priorities, h-values, LaCAM* search, OPEN/EXPLORED handling, pruning, restart semantics, or candidate deletion.
- Do not use reserved IDs `166..205`.
- Do not claim `phase5p5_allowed=true`, `phase6_allowed=true`, `runtime_claim_allowed=true`, `learned_runtime_policy_validated=true`, or `aaai_ready=true`.
- Do not train a predictor or create a non-static frozen policy unless supported per-stratum regions pass the stated gates.

## Stages

1. Verify required G5.40 artifacts and audit whether the global candidate conclusion hides per-stratum signal.
2. Re-label G5.40 evidence at `candidate_id,map_family,agents,budget_ms,iteration_bucket` granularity.
3. Build a balanced support-extension plan over fresh seeds `826..905`, prioritizing G5.40 boundary and near-miss candidate-stratum pairs.
4. Run the balanced extension with the real solver and analyze supported safe/useful strata.
5. Only if supported strata exist, create and run local refinement under a hard cap of 64 candidates.
6. Only if final supported strata exist, train/evaluate the diagnostic region predictor.
7. Only if final supported strata exist, create a frozen stratum policy and run blind replay on fresh seeds.
8. Write the final G5.41 decision with all claim flags closed.

## Support Gates

- Diagnostic labels: `support_pairs >= 20`, `seed_block_support >= 1`, `context_support >= 5`.
- Strong labels: `support_pairs >= 60`, `seed_block_support >= 2`, `context_support >= 20`.
- Final deployable labels: `support_pairs >= 80`, `seed_block_support >= 3`, `zero regressions vs static_flow and family static`, `mean_delta <= 0`, and `better >= worse` or `safe_high_margin_count > 0`.
- Local refinement final gate: `support_pairs >= 120`, `seed_block_support >= 3`, zero regressions, `mean_delta < 0`, and `better >= worse`.

## Expected Artifacts

- `scripts/repair5g541_common.py`
- thin wrapper scripts for each G5.41 stage
- `outputs/reports/phase5p5_repair5g541_*`
- `outputs/tables/phase5p5_repair5g541_*`
- `artifacts/models/laur_ltm/repair5g541_*_manifest.json` only when a predictor or policy artifact is warranted

## Validation

Run the prompt-specified G5.41 validation sequence: compile all G5.41 scripts, execute each stage, parse JSON summaries, run `git diff --check`, confirm `external/lacam2/lacam2` is clean, and run the existing focused pytest bundle when practical.
