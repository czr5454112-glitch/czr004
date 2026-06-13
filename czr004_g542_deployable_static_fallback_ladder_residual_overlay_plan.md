# Repair5G.5.42 Deployable Static-Fallback Ladder With Residual Overlay

## Objective

G5.42 tests whether the G5.41 family-static regressions were caused by using
`static_flow_shield` as the frozen fallback rather than by the residual
parameter regions themselves. The deployable policy is hierarchical:

1. Select a deployable static baseline for each stratum from:
   `additive_ltm`, `static_flow_shield`, `best_fixed_static_goal_aware`,
   `frozen_family_static_goal_aware`.
2. Apply a residual region only when it has support and zero-regression
   evidence against the selected static ladder baseline, `static_flow_shield`,
   and `frozen_family_static_goal_aware`.
3. Otherwise fall back to the selected deployable static baseline.

The learned residual component is not a replacement for the strongest
deployable static baseline; it is a conditional overlay. The first decision is
which deployable static baseline is safest for the stratum, and the second
decision is whether a supported residual region can safely improve over that
baseline.

## Guardrails

- Do not modify `external/lacam2/lacam2/**`.
- Do not change PIBT conflict semantics, candidate domains, actions,
  priorities, h-values, candidate deletion, LaCAM* search, OPEN/EXPLORED
  semantics, incumbent pruning, or restart semantics.
- Do not use reserved candidate IDs `166..205`.
- Do not use posthoc per-context oracle baselines.
- Keep `phase5p5_allowed`, `phase6_allowed`, `runtime_claim_allowed`,
  `learned_runtime_policy_validated`, and `aaai_ready` false in all summaries.

## Stages

### Stage A: Verify G5.41 and audit failure sources

Verify the committed G5.41 artifacts, materialize alias mappings when names
differ, confirm the positive evidence versus `static_flow_shield`, and
decompose the 15 regressions versus `frozen_family_static_goal_aware` into
residual-caused, static-flow-fallback-caused, other-fallback-caused, and
materialization/role mismatch classes.

### Stage B: Build the deployable static ladder

Train frozen rules from pre-G5.42 evidence only. Rules may choose only
`additive_ltm`, `static_flow_shield`, `best_fixed_static_goal_aware`, and
`frozen_family_static_goal_aware`. Use the coarsest supported stratum among
map-family, map-family by agents, map-family by budget, and map-family by
agents by budget.

### Stage C: Create residual overlay labels

Re-evaluate the G5.41 supported regions relative to the selected static ladder
baseline as well as `static_flow_shield` and `frozen_family_static_goal_aware`.
Classify regions as safe/useful, safe/equal, unsafe, or static-only.

### Stage D: Create policy candidates

Emit static-only and ladder-plus-overlay policy candidates:
`P0_static_flow_only`, `P1_frozen_family_static_only`,
`P2_deployable_static_ladder_only`, `P3_ladder_plus_overlay_high_margin_only`,
`P4_ladder_plus_overlay_nonnegative`, `P5_ultra_conservative_overlay`, and
`P6_staticflow_positive_residual_but_family_guard`.

### Stage E: Targeted ladder-overlay probe

Run fresh-seed solver evidence for the static baselines, static ladder,
G5.41 policy, and distinct ladder-overlay policies. Report regression counts
against static flow, family static, and the selected ladder baseline.

### Stage F: Freeze policy and blind replay

Freeze a non-static overlay only if targeted probe evidence has zero
regression versus static flow, family static, and ladder baseline, non-positive
mean quality delta versus ladder, better-count at least worse-count, and
non-static selection rate greater than zero. Otherwise write a static-ladder
decision and skip blind replay.

### Stage G: Edge-class design if blocked

If ladder-relative residuals do not pass, produce edge-class and
event-conditioned UpdateLTM design targets for the next round.

## Validation

Run the prompt's requested compile, stage, JSON-parse, diff, external-clean,
and targeted pytest checks. Commit only the G5.42 plan, scripts, summaries,
tables, required strategy docs, and manifest files; do not commit raw logs or
large checkpoints.
