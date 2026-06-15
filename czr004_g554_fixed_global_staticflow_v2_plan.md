# Repair5G.5.54 Plan — Fixed Global StaticFlow Coefficients v2: Fresh Paired Optimization, Near-Miss Expansion, and Trust-Region Search

Project: `czr004`  
Branch: `codex/g531-slice-pilot`  
Start point: after G5.53 commit `f9fd4dd` (`repair5g: finish g553 fixed staticflow search`)  
Round name: `Repair5G.5.54 fixed-global static_flow coefficient optimization v2`

---

## 0. Executive interpretation

G5.53 should **not** be interpreted as a final proof that hand-designed `static_flow_shield` cannot be improved.

G5.53 was useful and conservative, but it was a first fixed-global search pass with several limitations:

```text
G5.53 decision:
  g553_no_fixed_coeff_candidate_beats_hand_staticflow_keep_baseline

Stage0 smoke:
  solver_rows = 5075
  candidate_vectors = 200
  fulltheta_fingerprint_match_rate = 1
  materialization_failure_rows = 0
  stage0_surviving_candidates = 200

Stage1:
  solver_facing_rows_evaluated = 128000
  stage1_source = outputs/logs/phase5p5_repair5g552_label_expansion/label_v2_dataset.csv
  stage1_source_reused_solver_rows = 128000
  local_new_stage1_solver_rows = 0
  candidate_vectors = 2195
  stage1_validation_ready_candidates = 0
  zero_regression_low_support_candidates = 1470
  global_support_with_regression_candidates = 27

Validation:
  validation_run = false
  new_solver_rows = 0
```

The important nuance:

```text
G5.53 did not run a large fresh paired fixed-coefficient optimization/validation sweep.
It screened fixed candidates against a reused Label-v2 evidence pool.
Many zero-regression candidates existed, but they were rejected for insufficient global support.
High-support candidates had success regressions.
```

Therefore the scientific conclusion is:

```text
G5.53 did not promote a fixed global coefficient replacement.
It did not close the fixed-global coefficient optimization question.
```

G5.54 continues the simplified fixed-coefficient route, but with a better experimental design:

```text
1. keep dynamic learned policy paused;
2. keep exactly one global fixed coefficient vector as the candidate object;
3. run fresh paired solver replay, not only reused Label-v2 screening;
4. expand low-support zero-regression near-misses instead of discarding them;
5. optimize in a trust region around current hand static_flow and near-miss candidates;
6. validate top candidates with fresh heldout seeds / maps / horizons;
7. promote nothing unless zero-regression validation and blind gates pass.
```

---

## 1. Scientific motivation

The user's intuition is scientifically reasonable:

```text
The current static_flow_shield coefficients were hand-designed and not heavily optimized.
A fixed global coefficient vector may still be improvable.
```

G5.52 already showed that current hand `static_flow_shield` is a strong quality baseline versus additive LTM:

```text
mean_ratio_additive = 1.28936118566
mean_ratio_static_flow = 1.19350570633
relative_improvement_pct = 7.43433883353
```

But the current hand vector is not a perfect universal solution:

```text
static_flow_success_rate = 0.753984962406
additive_success_rate = 0.785363408521
success_regression_count_static_vs_additive = 465
```

Thus there are two distinct optimization goals:

```text
Primary G5.54 goal:
  fixed global coefficients that beat current hand static_flow_shield with zero success regression.

Diagnostic secondary goal:
  understand whether current hand static_flow trades success for quality,
  and whether any coefficient adjustment improves that frontier.
```

G5.54 is not a dynamic learned policy round. It is a fixed global coefficient optimization round.

---

## 2. Non-negotiable scope

Do **not** resume:

```text
dynamic learned UpdateParams policy
contextual selector
checkpoint policy
abstention policy
per-context theta generator
policy-as-executed learned action log
Label-v2 policy training
runtime learned policy
```

A candidate is exactly:

```text
one deterministic global fixed static_flow_shield coefficient vector
```

It must be shared across:

```text
all maps
all agent counts
all seeds
all budgets
all horizons
all checkpoints
all runtime states
```

It must not depend on:

```text
map_family
agents
seed
budget
horizon
traffic state
trace features
checkpoint features
success/failure outcome
selector decisions
runtime context
```

It is evaluated as:

```text
optimized_fixed_static_flow_coefficients_v2
  vs
current hand static_flow_shield
```

using paired replay with identical:

```text
map
agents
seed
scenario
budget
horizon
base_time_limit_sec
ltm_max_iterations
binary
commit
candidate registry
counterfactual parser
```

---

## 3. Guardrails

Do not modify:

```text
external/lacam2/lacam2/**
PIBT conflict semantics
candidate domain
agent actions
agent priorities
h-values
OPEN / EXPLORED
LaCAM* high-level search
rewrite / incumbent pruning
restart semantics
candidate deletion semantics
```

Do not use reserved IDs:

```text
166..205
```

Keep all claim flags closed:

```json
{
  "phase5p5_allowed": false,
  "phase6_allowed": false,
  "runtime_claim_allowed": false,
  "learned_runtime_policy_validated": false,
  "aaai_ready": false
}
```

Even if G5.54 finds a better fixed vector, it is not a dynamic learned runtime policy. It may only become:

```text
optimized_static_flow_shield_fixed_v2_candidate
```

and all broader paper/runtime claims remain closed until later blind and paper-grade gates.

---

## 4. Baseline interpretation

Primary baseline:

```text
current C++-materialized hand static_flow_shield
candidate_id = repair5g59_static_flow_shield
```

Do not accidentally use the older helper fulltheta reference as the baseline if it differs.

G5.53 found that the current C++ materialized hand static_flow differs from the legacy helper in:

```text
theta_alpha_flow_wait_progress
theta_lambda_flow
```

Current hand values include:

```text
theta_alpha_flow_wait_progress = 0
theta_lambda_flow = 0
theta_flow_shield_beta = 0.35
theta_max_flow_shield = 0.75
theta_min_edge_cost = 1
theta_max_edge_cost = 11
goal_projection_mode = flow_shield
```

This is crucial. G5.54 must audit whether these fields are actually active in the materialized C++ path. In particular:

```text
If theta_lambda_flow is not used under flow_shield mode,
do not waste search budget treating it as a primary active field.

If theta_alpha_flow_wait_progress is zero in the current hand baseline,
test whether small positive wait-progress flow is beneficial or dangerous.

If alpha_flow_commit_progress is active but wait-progress flow is off,
search commit-flow / wait-flow interaction carefully.
```

Paper floor:

```text
additive_ltm
```

Diagnostics:

```text
frozen_family_static_goal_aware
best_fixed_static_goal_aware
family_static variants
```

Promotion is judged versus current hand `static_flow_shield`, not versus additive alone.

Additive remains a diagnostic safety floor. Report additive success regressions, but do not require additive dominance for Stage1 exploration. Require additive diagnostics for validation and blind.

---

## 5. Required worklog entry

Before coding, append to `docs/codex-worklog.md`:

```markdown
## 2026-06-15 - Repair5G.5.54 fixed-global static_flow coefficient optimization v2

- Request:
  Continue the fixed-global coefficient route after G5.53 commit f9fd4dd. Keep dynamic learned UpdateParams policy, contextual selector, checkpoint policy, and abstention policy paused. The objective remains: search one deterministic global static_flow_shield coefficient vector that can directly replace the current hand static_flow_shield baseline.

- Interpretation:
  G5.53 did not find a promotable fixed-global vector, but it was not a final negative result. Stage0 materialization passed with fingerprint=1 and 200 surviving candidates. Stage1 evaluated 128,000 solver-facing rows from the reused G5.52 Label-v2 dataset, not a large fresh fixed-coefficient optimization replay. It found 1,470 zero-regression low-support candidates and 27 high-support candidates with regressions, then skipped validation because no candidate passed the strict support gate.

- G5.54 change:
  Run a fresh paired fixed-coefficient search/validation pipeline. Expand zero-regression near-misses, use trust-region and derivative-free candidate generation around current hand static_flow and near-miss candidates, and validate top candidates on fresh heldout paired replay. Search-phase candidates may have regressions for diagnostic learning, but promotion candidates must have zero success regressions versus current hand static_flow_shield.

- Baseline:
  Primary baseline is the current C++-materialized hand static_flow_shield (`repair5g59_static_flow_shield`), not the older helper fulltheta reference. additive_ltm remains the paper/parity floor and diagnostic success floor.

- Constraints:
  No external/lacam2/lacam2 edits, no solver semantic changes, no dynamic policy, no selector, no checkpoint policy, no abstention gate, no per-context theta, no IDs 166..205, and no runtime/Phase5.5/Phase6/AAAI claims.
```

Also update governance docs if baseline/SafeGate text is modified:

```text
deep-research-report.md
docs/aaai_quality_requirements.md
docs/goal_aware_dual_channel_ltm_research_strategy.md
phase4_6_laur_ltm_codex_execution_plan.md
```

Required governance statement:

```text
G5.54 continues fixed-global static_flow coefficient optimization. The candidate remains one deterministic global coefficient vector shared across all maps, agents, seeds, budgets, and checkpoints. It is not a dynamic learned policy. G5.53 did not promote a replacement because its Stage1 candidates either lacked support or regressed; G5.54 therefore runs fresh paired optimization and near-miss expansion. Current hand static_flow_shield remains the primary baseline unless a fixed global vector passes fresh validation/blind replay with zero success regression.
```

---

## 6. Required files

Create:

```text
czr004_g554_fixed_global_staticflow_v2_plan.md

scripts/repair5g554_common.py
scripts/verify_repair5g554_g553_artifacts.py
scripts/audit_repair5g554_g553_negative_result.py
scripts/audit_repair5g554_active_staticflow_fields.py
scripts/create_repair5g554_nearmiss_candidate_pool.py
scripts/create_repair5g554_trust_region_search_space.py
scripts/run_repair5g554_stage0b_materialization_and_field_smoke.py
scripts/analyze_repair5g554_stage0b_materialization_and_field_smoke.py
scripts/run_repair5g554_stage1_fresh_screening.py
scripts/analyze_repair5g554_stage1_fresh_screening.py
scripts/create_repair5g554_stage2_nearmiss_expansion_plan.py
scripts/run_repair5g554_stage2_nearmiss_expansion.py
scripts/analyze_repair5g554_stage2_nearmiss_expansion.py
scripts/create_repair5g554_validation_plan.py
scripts/run_repair5g554_validation.py
scripts/analyze_repair5g554_validation.py
scripts/create_repair5g554_blind_if_warranted.py
scripts/run_repair5g554_blind_if_warranted.py
scripts/analyze_repair5g554_blind_if_warranted.py
scripts/write_repair5g554_decision.py
```

Outputs:

```text
outputs/reports/phase5p5_repair5g554_*
outputs/tables/phase5p5_repair5g554_*
outputs/logs/phase5p5_repair5g554_*
```

Large raw plans/results must go under ignored logs. Do not commit raw CSVs >50 MB. Commit:

```text
compact summaries
preview CSVs
leaderboards
failure taxonomies
sha256 hashes
exact resume commands
large-artifact manifest
```

---

## 7. Stage A — Verify G5.53 and audit why it is not final

Create:

```text
scripts/verify_repair5g554_g553_artifacts.py
scripts/audit_repair5g554_g553_negative_result.py
```

Inputs:

```text
outputs/reports/phase5p5_repair5g553_decision_summary.json
outputs/reports/phase5p5_repair5g553_stage0_smoke_summary.json
outputs/reports/phase5p5_repair5g553_stage1_search_summary.json
outputs/reports/phase5p5_repair5g553_current_staticflow_coefficients_summary.json
outputs/reports/phase5p5_repair5g553_global_staticflow_search_space_summary.json
outputs/reports/phase5p5_repair5g553_fixed_coeff_validation_summary.json
outputs/tables/phase5p5_repair5g553_stage1_candidate_leaderboard.csv
outputs/tables/phase5p5_repair5g553_stage1_candidate_by_stratum.csv
outputs/tables/phase5p5_repair5g553_current_staticflow_theta.csv
```

Write:

```text
outputs/reports/phase5p5_repair5g554_g553_verification.md
outputs/reports/phase5p5_repair5g554_g553_verification_summary.json
outputs/reports/phase5p5_repair5g554_g553_negative_result_audit.md
outputs/reports/phase5p5_repair5g554_g553_negative_result_audit_summary.json
outputs/tables/phase5p5_repair5g554_g553_artifact_audit.csv
outputs/tables/phase5p5_repair5g554_g553_zero_reg_low_support_candidates.csv
outputs/tables/phase5p5_repair5g554_g553_high_support_regressing_candidates.csv
outputs/tables/phase5p5_repair5g554_g553_nearmiss_by_stratum.csv
outputs/tables/phase5p5_repair5g554_g553_search_limitations.csv
```

Required answers:

```text
1. Did G5.53 run fresh Stage1 solver rows or reuse G5.52 Label-v2 rows?
2. How many zero-regression candidates were rejected for low support?
3. How much support did the top zero-regression candidates have?
4. Which candidates had strong quality gain but insufficient support?
5. Which candidates had global support but success regressions?
6. Were near-misses concentrated around specific parameter directions?
7. Did validation run? If not, why?
8. Was the current static_flow baseline the C++ materialized alias, not legacy helper?
9. Which current hand fields differ from legacy helper?
10. Is the G5.53 result a final negative or a first-pass screening negative?
```

Expected interpretation:

```text
G5.53 is a conservative no-promotion result.
It is not a final closure of fixed global coefficient search because Stage1 reused a prior label dataset and did not expand low-support zero-regression near-misses with fresh paired replay.
```

---

## 8. Stage B — Active-field audit

Create:

```text
scripts/audit_repair5g554_active_staticflow_fields.py
```

Write:

```text
outputs/reports/phase5p5_repair5g554_active_staticflow_fields.md
outputs/reports/phase5p5_repair5g554_active_staticflow_fields_summary.json
outputs/tables/phase5p5_repair5g554_active_field_materialization_audit.csv
outputs/tables/phase5p5_repair5g554_one_factor_field_smoke_plan.csv
outputs/tables/phase5p5_repair5g554_field_usage_semantic_audit.csv
```

Audit all fields:

```text
theta_alpha_cong_commit_progress
theta_alpha_cong_commit_nonprogress
theta_alpha_cong_block
theta_alpha_cong_wait_progress
theta_alpha_cong_wait_nonprogress
theta_alpha_flow_commit_progress
theta_alpha_flow_wait_progress
theta_rho_cong_decay
theta_rho_flow_decay
theta_lambda_cong
theta_lambda_flow
theta_flow_shield_beta
theta_max_flow_shield
theta_min_edge_cost
theta_max_edge_cost
theta_goal_projection_mode_flow_shield
theta_goal_projection_mode_agent_progress
theta_goal_projection_mode_none
```

For each field, classify:

```text
active_in_materialization
active_in_update
active_in_cost_projection
active_only_under_specific_goal_projection_mode
ignored_or_alias
requires_nonzero_flow_events
requires_nonzero_wait_progress_events
```

Special checks:

```text
1. Does theta_lambda_flow affect traversal cost under FlowShield mode?
2. Does theta_alpha_flow_wait_progress affect any flow_raw_count when wait-progress events exist?
3. Does theta_flow_shield_beta matter if flow raw is mostly from committed progress only?
4. Is theta_alpha_flow_commit_progress active in current hand static_flow?
5. Are min/max edge cost clamps binding in relevant contexts?
6. Is goal_projection_mode_flow_shield always canonical?
```

If a field is inactive, do not spend the main search budget on it except as an ablation diagnostic.

---

## 9. Stage C — Near-miss candidate pool

Create:

```text
scripts/create_repair5g554_nearmiss_candidate_pool.py
```

Write:

```text
outputs/reports/phase5p5_repair5g554_nearmiss_candidate_pool.md
outputs/reports/phase5p5_repair5g554_nearmiss_candidate_pool_summary.json
outputs/tables/phase5p5_repair5g554_nearmiss_candidate_pool.csv
outputs/tables/phase5p5_repair5g554_nearmiss_theta_centroids.csv
outputs/tables/phase5p5_repair5g554_nearmiss_failure_frontier.csv
```

Candidate sources:

```text
1. current hand static_flow_shield
2. legacy helper static_flow reference
3. midpoint between current hand and legacy helper
4. G5.53 zero-regression low-support candidates
5. G5.53 high-quality near-miss candidates
6. G5.53 high-support candidates with few success regressions
7. G5.52 safe theta library candidates
8. G5.49/G5.50 true safe-gain region centroids, converted to fixed-global candidates
9. small perturbations around current hand static_flow
10. shrinkage versions of risky candidates toward current hand static_flow
```

Important:

```text
The candidate is still one fixed global vector.
The near-miss source does not make it contextual.
```

For each near-miss candidate compute:

```text
distance_from_current_static_flow
distance_from_legacy_helper
support_rows_existing
success_regression_count_existing
quality_delta_existing
support_strata_existing
theta_family
active_field_deltas
```

Select seed candidates for search-space construction.

---

## 10. Stage D — Trust-region search space v2

Create:

```text
scripts/create_repair5g554_trust_region_search_space.py
```

Write:

```text
outputs/reports/phase5p5_repair5g554_trust_region_search_space.md
outputs/reports/phase5p5_repair5g554_trust_region_search_space_summary.json
outputs/tables/phase5p5_repair5g554_search_space_bounds_v2.csv
outputs/tables/phase5p5_repair5g554_candidate_registry_v2_preview.csv
outputs/tables/phase5p5_repair5g554_candidate_family_breakdown.csv
outputs/tables/phase5p5_repair5g554_candidate_generation_metadata.csv
```

Raw full registry:

```text
outputs/logs/phase5p5_repair5g554_candidate_registry_v2.csv
```

Generate at least:

```text
candidate_vectors >= 8000
preferred_candidate_vectors >= 16000 if local PC remains stable
```

Candidate families:

```text
hand_static_reference
legacy_helper_reference
hand_legacy_midpoints
one_factor_small_perturbation
two_factor_interaction
trust_region_sobol_around_hand
trust_region_sobol_around_nearmiss
cma_es_style_offline_candidates
cross_entropy_elite_refits
coordinate_descent_lines
flow_wait_progress_micro_sweep
lambda_cong_micro_sweep
flow_shield_beta_cap_sweep
cost_clamp_micro_sweep
rho_decay_micro_sweep
shrinkage_to_hand_from_risky
negative_controls_wide_random
```

Use staged trust regions:

```text
tiny:
  +/- 2.5% around current hand for active numeric fields

small:
  +/- 5%

medium:
  +/- 10%

near-miss:
  interpolation between current hand and near-miss candidate:
    t in {0.1, 0.2, ..., 0.9}

wide diagnostic:
  bounded Sobol / Latin hypercube, diagnostic only
```

The main search should prioritize active fields and likely useful interactions:

```text
alpha_cong_commit_nonprogress
alpha_flow_commit_progress
alpha_flow_wait_progress
lambda_cong
flow_shield_beta
max_flow_shield
min_edge_cost
max_edge_cost
rho_cong_decay
goal_projection_mode
```

Do not over-index on inactive fields.

---

## 11. Stage E — Stage0B materialization + field smoke

Create:

```text
scripts/run_repair5g554_stage0b_materialization_and_field_smoke.py
scripts/analyze_repair5g554_stage0b_materialization_and_field_smoke.py
```

Run a real cheap smoke:

```text
stage0b_candidate_vectors >= 1000
stage0b_solver_rows >= 10000
stage0b_contexts >= 50
```

Include:

```text
random / maze / warehouse diagnostic
agents 50 / 100
nominal_budget_ms 2000
short_budget_ms 1000 / 2000
base_time_limit_sec 0.5
ltm_max_iterations 2
```

Write:

```text
outputs/reports/phase5p5_repair5g554_stage0b_smoke.md
outputs/reports/phase5p5_repair5g554_stage0b_smoke_summary.json
outputs/tables/phase5p5_repair5g554_stage0b_candidate_survivors.csv
outputs/tables/phase5p5_repair5g554_stage0b_materialization_failures.csv
outputs/tables/phase5p5_repair5g554_stage0b_obvious_regressions.csv
outputs/tables/phase5p5_repair5g554_stage0b_field_response.csv
```

Stage0B pass:

```text
candidate_recognized_all = true
fulltheta_fingerprint_match_rate = 1
cost_finite_all = true
current_hand_static_flow_reproduced = true
materialization_failure_rows = 0
```

If fingerprint is not exactly 1, stop and repair materialization. Do not proceed.

---

## 12. Stage F — Stage1 fresh screening

Create:

```text
scripts/run_repair5g554_stage1_fresh_screening.py
scripts/analyze_repair5g554_stage1_fresh_screening.py
```

This is the main difference from G5.53.

Do not rely only on G5.52 Label-v2 reused rows.

Run fresh paired solver-facing rows:

```text
minimum_new_stage1_solver_rows >= 256000
preferred_new_stage1_solver_rows >= 512000 if local PC remains stable
candidate_vectors_screened >= 3000
contexts >= 1000
baseline_static_flow_reference_rows >= 1000
```

Use paired contexts:

```text
map_family: random, maze, warehouse diagnostic
agents: 50, 100
nominal_budget_ms: 2000 primary, 1000/500 diagnostic
short_budget_ms: 1000, 2000, 5000
base_time_limit_sec: 0.5, 1.0
ltm_max_iterations: 2, 4
fresh seeds outside G5.53 where practical
no IDs 166..205
```

Important search-phase rule:

```text
Search-phase candidates may have success regressions.
Do not promote them.
Use their regressions to learn the frontier.
Promotion candidates must have zero regressions later.
```

Write:

```text
outputs/reports/phase5p5_repair5g554_stage1_fresh_screening.md
outputs/reports/phase5p5_repair5g554_stage1_fresh_screening_summary.json
outputs/tables/phase5p5_repair5g554_stage1_candidate_leaderboard.csv
outputs/tables/phase5p5_repair5g554_stage1_candidate_by_stratum.csv
outputs/tables/phase5p5_repair5g554_stage1_success_quality_frontier.csv
outputs/tables/phase5p5_repair5g554_stage1_zero_regression_candidates.csv
outputs/tables/phase5p5_repair5g554_stage1_low_regression_high_gain_candidates.csv
outputs/tables/phase5p5_repair5g554_stage1_failure_cases.csv
outputs/tables/phase5p5_repair5g554_stage1_parameter_sensitivity.csv
```

Stage1 ranking objective:

```text
primary:
  minimize success_regression_count_vs_static_flow

secondary:
  among zero or low regression candidates, maximize both-success quality improvement

tertiary:
  prefer broad support across strata and seed blocks
```

Candidate classes:

```text
validation_ready:
  success_regression_count_vs_static_flow = 0
  candidate_rows >= 1000
  support_strata >= 4
  support_seed_blocks >= 8
  both_success_quality_delta_mean_vs_static_flow <= -0.001
  better_count > worse_count
  fingerprint = 1
  cost_finite_all = true

near_miss_expand:
  success_regression_count_vs_static_flow <= 2
  or zero-regression but support < 1000
  or quality_delta <= -0.01 but support narrow

reject:
  repeated regressions across multiple strata
  fingerprint mismatch
  nonfinite cost
  worse quality and no success gain
```

Do not require global support during the first few hundred rows. Instead, expand promising candidates.

---

## 13. Stage G — Stage2 near-miss expansion

Create:

```text
scripts/create_repair5g554_stage2_nearmiss_expansion_plan.py
scripts/run_repair5g554_stage2_nearmiss_expansion.py
scripts/analyze_repair5g554_stage2_nearmiss_expansion.py
```

Select:

```text
top_zero_regression_low_support_candidates >= 50
top_low_regression_high_gain_candidates >= 50
top_hand_trust_region_candidates >= 50
negative_controls >= 20
```

Run:

```text
minimum_stage2_new_solver_rows >= 256000
preferred_stage2_new_solver_rows >= 512000
candidate_rows_per_candidate_target >= 2000
support_strata_target >= 6
support_seed_blocks_target >= 12
```

Write:

```text
outputs/reports/phase5p5_repair5g554_stage2_nearmiss_expansion.md
outputs/reports/phase5p5_repair5g554_stage2_nearmiss_expansion_summary.json
outputs/tables/phase5p5_repair5g554_stage2_candidate_leaderboard.csv
outputs/tables/phase5p5_repair5g554_stage2_candidate_by_stratum.csv
outputs/tables/phase5p5_repair5g554_stage2_candidate_confidence_intervals.csv
outputs/tables/phase5p5_repair5g554_stage2_validation_shortlist.csv
outputs/tables/phase5p5_repair5g554_stage2_failure_cases.csv
```

Stage2 validation shortlist gate:

```text
success_regression_count_vs_static_flow = 0
candidate_rows >= 2000
support_strata >= 6
support_seed_blocks >= 12
mean_quality_delta_vs_static_flow <= -0.001
bootstrap CI upper <= 0
better_count > worse_count
fingerprint_match_rate = 1
candidate_recognized_all = true
cost_finite_all = true
```

If no candidate reaches this, still write the frontier and explain whether:

```text
1. fixed global space appears too constrained;
2. support is still insufficient;
3. gains are narrow to random/maze;
4. success regressions are unavoidable for quality gains;
5. search budget needs continuation;
6. hand static_flow is genuinely close to Pareto frontier.
```

---

## 14. Stage H — Fresh validation

Create:

```text
scripts/create_repair5g554_validation_plan.py
scripts/run_repair5g554_validation.py
scripts/analyze_repair5g554_validation.py
```

Only run if Stage2 shortlist exists.

Validation candidate count:

```text
top_candidates_to_validate <= 10
```

Fresh validation rows:

```text
minimum_validation_solver_rows >= 120000
preferred_validation_solver_rows >= 240000
candidate_rows_per_candidate >= 10000
```

Use fresh heldout:

```text
seeds unseen in Stage1/Stage2
maps/agent/horizons held out where possible
random / maze primary
warehouse diagnostic
nominal_budget_ms: 2000 primary, 500/1000 diagnostic
short_budget_ms: 1000/2000/5000
base_time_limit_sec: 0.5/1.0
ltm_max_iterations: 2/4
```

Validation pass:

```text
success_regression_count_vs_static_flow = 0
success_rate_delta_vs_static_flow >= 0
both_success_quality_delta_mean_vs_static_flow <= -0.001
bootstrap CI upper <= 0
better_count > worse_count
candidate_recognized_all = true
fulltheta_fingerprint_match_rate = 1
cost_finite_all = true
theta_in_bounds_all = true
```

Additive diagnostics:

```text
success_regression_count_vs_additive
quality_delta_vs_additive
whether optimized candidate worsens static_flow's additive regression profile
```

Do not require additive zero-regression for primary validation unless explicitly configured, but report it prominently.

Write:

```text
outputs/reports/phase5p5_repair5g554_validation.md
outputs/reports/phase5p5_repair5g554_validation_summary.json
outputs/tables/phase5p5_repair5g554_validation_candidate_leaderboard.csv
outputs/tables/phase5p5_repair5g554_validation_by_stratum.csv
outputs/tables/phase5p5_repair5g554_validation_vs_additive_diagnostic.csv
outputs/tables/phase5p5_repair5g554_validation_failure_cases.csv
```

---

## 15. Stage I — Blind replay if warranted

Create:

```text
scripts/create_repair5g554_blind_if_warranted.py
scripts/run_repair5g554_blind_if_warranted.py
scripts/analyze_repair5g554_blind_if_warranted.py
```

Only if validation passes.

Blind replay:

```text
minimum_blind_solver_rows >= 120000
preferred_blind_solver_rows >= 240000
blind_candidate_count <= 3
fresh seeds only
no tuning after blind plan is created
```

Blind pass:

```text
success_regression_count_vs_static_flow = 0
success_rate_delta_vs_static_flow >= 0
mean_quality_delta_vs_static_flow <= -0.001
bootstrap CI upper <= 0
better_count > worse_count
fingerprint_match_rate = 1
candidate_recognized_all = true
cost_finite_all = true
```

If blind passes, decision may be:

```text
g554_fixed_global_staticflow_coefficients_candidate_found_keep_claims_closed
```

Even then:

```text
phase5p5_allowed = false
phase6_allowed = false
runtime_claim_allowed = false
learned_runtime_policy_validated = false
aaai_ready = false
```

This is a fixed baseline candidate, not a dynamic learned policy.

---

## 16. Stage J — Decision

Create:

```text
scripts/write_repair5g554_decision.py
```

Write:

```text
outputs/reports/phase5p5_repair5g554_decision.md
outputs/reports/phase5p5_repair5g554_decision_summary.json
outputs/tables/phase5p5_repair5g554_claim_ledger.csv
outputs/tables/phase5p5_repair5g554_final_candidate_theta.csv
outputs/tables/phase5p5_repair5g554_large_artifact_manifest.csv
```

Decision labels:

```text
g554_fingerprint_or_materialization_blocked
g554_stage1_underpowered_continue_fresh_screening
g554_nearmisses_found_continue_expansion
g554_no_fixed_global_candidate_after_fresh_search_keep_hand_baseline
g554_validation_failed_keep_hand_baseline
g554_blind_failed_keep_hand_baseline
g554_fixed_global_staticflow_coefficients_candidate_found_keep_claims_closed
```

Final summary keys:

```json
{
  "decision": "...",
  "primary_baseline": "current hand static_flow_shield",
  "dynamic_learned_policy_paused": true,
  "candidate_object": "one fixed global coefficient vector",
  "stage1_new_solver_rows": 0,
  "stage2_new_solver_rows": 0,
  "validation_new_solver_rows": 0,
  "blind_new_solver_rows": 0,
  "best_candidate_id": "...",
  "best_candidate_success_regressions_vs_static_flow": 0,
  "best_candidate_quality_delta_vs_static_flow": "...",
  "validation_passed": false,
  "blind_passed": false,
  "optimized_fixed_candidate_promoted": false,
  "should_hand_static_flow_remain_primary": true,
  "phase5p5_allowed": false,
  "phase6_allowed": false,
  "runtime_claim_allowed": false,
  "learned_runtime_policy_validated": false,
  "aaai_ready": false
}
```

---

## 17. Local PC runtime guidance

This round is intentionally heavier than G5.53. G5.53 finished quickly because Stage1 reused an existing Label-v2 dataset.

G5.54 should run real fresh solver rows.

Recommended local sequence:

```powershell
python scripts/verify_repair5g554_g553_artifacts.py
python scripts/audit_repair5g554_g553_negative_result.py
python scripts/audit_repair5g554_active_staticflow_fields.py
python scripts/create_repair5g554_nearmiss_candidate_pool.py
python scripts/create_repair5g554_trust_region_search_space.py --candidate-count 16000
python scripts/run_repair5g554_stage0b_materialization_and_field_smoke.py --row-limit 10000 --max-workers 16
python scripts/analyze_repair5g554_stage0b_materialization_and_field_smoke.py
python scripts/run_repair5g554_stage1_fresh_screening.py --row-limit 256000 --max-workers 20
python scripts/analyze_repair5g554_stage1_fresh_screening.py
python scripts/create_repair5g554_stage2_nearmiss_expansion_plan.py
python scripts/run_repair5g554_stage2_nearmiss_expansion.py --row-limit 256000 --max-workers 20
python scripts/analyze_repair5g554_stage2_nearmiss_expansion.py
python scripts/create_repair5g554_validation_plan.py
python scripts/run_repair5g554_validation.py --row-limit 120000 --max-workers 20
python scripts/analyze_repair5g554_validation.py
python scripts/create_repair5g554_blind_if_warranted.py
python scripts/run_repair5g554_blind_if_warranted.py --row-limit 120000 --max-workers 20
python scripts/analyze_repair5g554_blind_if_warranted.py
python scripts/write_repair5g554_decision.py
```

If local runtime is too high, use resumable row limits and exact resume commands. Do not convert fresh Stage1 into reused-row analysis only.

---

## 18. Success and failure interpretation

### Success

A real success is:

```text
one fixed global coefficient vector
fresh validation and ideally blind replay
zero success regression vs current hand static_flow
quality improvement vs hand static_flow
fingerprint = 1
cost finite
not context dependent
all claims closed
```

This would be a stronger fixed baseline, not a dynamic learned policy.

### Failure

A useful failure is:

```text
fresh Stage1 + Stage2 show no fixed global vector can improve hand static_flow
without success regressions.
```

That would support the conclusion:

```text
Current hand static_flow is close to the Pareto frontier for global fixed coefficients.
Future improvement likely requires either:
  1. per-family fixed coefficients as a diagnostic only,
  2. better static-flow feature engineering,
  3. or a dynamic policy later with much stronger safety machinery.
```

### Inconclusive

An inconclusive result is:

```text
only reused data,
no fresh Stage1,
insufficient near-miss expansion,
fingerprint not 1,
or validation skipped.
```

Do not report such a result as evidence that fixed global coefficients cannot improve.

---

## 19. Forbidden shortcuts

Do not do any of the following:

```text
Do not use per-map or per-agent coefficients as the main candidate.
Do not call a per-family diagnostic a global fixed vector.
Do not relax zero-regression validation gate.
Do not promote a candidate based only on additive_ltm improvement.
Do not count context-dependent selection as fixed global coefficients.
Do not train a selector.
Do not restart dynamic policy work inside G5.54.
Do not rely only on G5.52 Label-v2 reused rows for Stage1.
Do not skip validation just because support is initially low.
Do not treat low-support zero-regression candidates as dead; expand them.
Do not commit raw CSV >50 MB.
```

---

## 20. Final scientific target

G5.54 should answer one precise question:

```text
After fresh trust-region optimization and near-miss expansion,
is there a single deterministic global static_flow_shield coefficient vector
that zero-regression improves over the current hand static_flow_shield?
```

If yes, create a stronger fixed baseline candidate.

If no, keep hand static_flow as primary and report a much stronger negative than G5.53.

Either outcome is scientifically useful.
