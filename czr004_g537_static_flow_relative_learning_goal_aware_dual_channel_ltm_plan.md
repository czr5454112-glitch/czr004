# Repair5G.5.37 Static-Flow-Relative Learning Plan

G5.37 treats additive LTM as a legacy floor and evaluates learning against the strongest safe static goal-aware dual-channel baselines: `static_flow_shield`, best fixed static, and best family/static-stratum rules. The round is intentionally static-relative: offline training artifacts may use committed G5.33..G5.36 evidence, while blind G5.37 replay outcomes are evaluation-only and must not tune the policy.

## Stages

1. Verify G5.36 artifacts and reinterpret G5.36 under a static-baseline ladder.
2. Build static-relative labels against additive, static_flow, best fixed static, best family static, and the primary static baseline.
3. Analyze where static_flow dominates, where static candidates still have safe gaps, and whether the gap is quality, success, or candidate coverage.
4. Train/evaluate a static-relative selector whose fallback is best static, not additive except where additive is safer.
5. Train/evaluate a bounded static-flow residual diagnostic and propose a small future candidate set.
6. Create and execute a fresh blind replay plan over heldout seeds `286..365`.
7. Analyze selected-vs-additive, selected-vs-static_flow, selected-vs-best-fixed, selected-vs-best-family, and selected-vs-primary-static evidence.
8. Write a decision with all Phase5.5, Phase6, runtime, learned-runtime, and AAAI claims closed.

## Guardrails

- Do not edit `external/lacam2/lacam2/**`.
- Do not change PIBT, candidate domain, h-values, priorities, candidate deletion, LaCAM* high-level search, restart semantics, or solver pruning semantics.
- Do not use reserved IDs `166..205`.
- Do not use G5.37 blind replay outcomes to tune the primary policy.
- Keep `phase5p5_allowed=false`, `phase6_allowed=false`, `runtime_claim_allowed=false`, `learned_runtime_policy_validated=false`, and `aaai_ready=false`.
