# Phase5.5 Repair5G Learning Insertion Strategy

Decision: `learning_update_ltm_dynamics_not_actions`

This report records the governance addendum insertion and supporting route artifacts for the Repair5G learning-insertion strategy. It does not modify solver semantics, run fresh IDs, or claim Phase5.5, Phase6, or AAAI readiness.

## Inserted grand-plan addendum

The exact verbatim addendum block titled `2026-06 Repair5G learning-insertion strategy for top-tier AI / MAPF venues` was inserted into:

- `deep-research-report.md`
- `phase4_6_laur_ltm_codex_execution_plan.md`
- `docs/aaai_quality_requirements.md`

## Strategic decision

The only valid learning insertion point remains `UpdateLTM` dynamics. Learned components may output bounded C/F-channel update parameters, safe expert mixtures, bounded residuals, and abstention/fallback signals. They must not output MAPF actions, PIBT priorities, restart nodes, heuristic values, candidate deletions, collision outcomes, or LaCAM*/PIBT control decisions.

The runtime selector is retained as a safety bridge and fallback layer. It is not the final paper method unless it evolves into a safe learned-abstention or safe mixture policy that validates against static/map-agent flow-shield under closed-loop heldout gates.

## Preferred route

The preferred top-venue route is a safe learned bounded dual-channel UpdateLTM policy: first safe learned abstention and mixture over validated experts, then bounded residual parameters once counterfactual UpdateLTM labels exist. Advanced graph/trace neural models remain blocked until the runtime bridge and counterfactual labels are reliable.

## Current gates

- `phase5p5_allowed=false`
- `phase6_allowed=false`
- `aaai_ready=false`
- No fresh learned-runtime IDs were run by this documentation task.
- Solver semantics, LaCAM*/PIBT behavior, candidate generation, conflict handling, pruning, restarts, and action policies were not changed.

## Supporting artifacts

- `outputs/reports/phase5p5_repair5g_learning_insertion_strategy_summary.json`
- `outputs/tables/phase5p5_repair5g_learning_route_comparison.csv`
- `outputs/tables/phase5p5_repair5g_learning_stage_ladder.csv`
