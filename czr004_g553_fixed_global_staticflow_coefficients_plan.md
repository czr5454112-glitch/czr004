# Repair5G.5.53 Plan — Fixed Global StaticFlow Coefficient Optimization

Project: `czr004`
Branch: `codex/g531-slice-pilot`
Start point: after G5.52 commit `679e763` (`repair5g: finish g552 label-v2 safegate`)
Round name: `Repair5G.5.53 fixed-global static_flow coefficient optimization`

## 0. Executive decision

Pause the dynamic learned UpdateParams policy line for now.

Do **not** continue the following as the main route in this round:

```text
contextual selector
checkpoint-level abstention policy
dynamic learned UpdateParams policy
per-context theta generator
policy-as-executed learned action log
Label-v2 policy training
```

G5.50–G5.52 produced valuable diagnostics, but they repeatedly failed to produce a safe non-static learned policy. G5.52 in particular showed that the stricter Label-v2 / policy-as-executed interpretation correctly forbids the unsafe G5.51 actions, but it collapses to all-abstain and does not provide a usable learned policy.

Therefore G5.53 changes the immediate objective to a simpler and more verifiable one:

```text
Search / learn one fixed global set of static_flow_shield coefficients
that can replace the current hand-designed static_flow_shield coefficients
under the same paired evaluation protocol.
```

This fixed coefficient vector is **not** a contextual policy. It is a static global baseline candidate.

It must be:

```text
global/shared across all maps, agent counts, seeds, budgets, and checkpoints
deterministic
context-independent
not selected by a model at runtime
not a selector
not an abstention policy
not a per-context theta generator
not a dynamic UpdateParams policy
```

It is evaluated as:

```text
optimized_static_flow_shield_fixed_v1
  vs
current hand static_flow_shield
```

using paired replay with identical:

```text
map
agents
seed
budget
horizon
solver settings
scenario
binary / commit
```

If the fixed learned coefficients do not beat the current hand static_flow_shield with zero success regression under fresh evaluation, keep the hand static_flow_shield as the primary baseline.

## 1. Why this pivot is scientifically reasonable

The project’s long-term goal remains:

```text
Use learning-enhanced / optimized UpdateLTM to replace the LTM paper’s crude additive update
and exceed LTM under solver-facing MAPF metrics.
```

However, the dynamic policy path is currently blocked by several hard facts:

```text
G5.50:
  offline generator passed,
  but fresh targeted replay failed with 216 success regressions vs static_flow_shield.

G5.51:
  iteration labels passed,
  checkpoint policy offline passed,
  but targeted replay failed with 352 success regressions vs static_flow_shield,
  300 regressions vs additive_ltm,
  and positive/worse quality delta.

G5.52:
  Label-v2 correctly forbade all 27 G5.51 ALLOW_THETA actions,
  built 25 safe theta and 1213 forbidden theta entries,
  but policy-as-executed offline gate failed with zero non-static usage.
```

These results suggest that the current dynamic policy problem is too hard or too underspecified.

A fixed global coefficient search is a lower-dimensional and cleaner question:

```text
Can we improve the hand-designed static_flow_shield coefficients themselves?
```

This has several advantages:

1. It removes policy-distribution shift.
2. It removes abstention semantics.
3. It removes per-context theta selection.
4. It removes generated-theta slate confusion.
5. It keeps all evaluation paired and deterministic.
6. It creates a stronger baseline for future dynamic methods.
7. It gives a clear answer: one fixed vector is better, or the hand static vector remains best.

This is similar in spirit to guidance-parameter optimization work such as Guidance Graph Optimization: optimize guidance parameters through solver-facing outcomes before claiming learned dynamic policy. For `czr004`, the object is not a guidance graph, but a global static-flow UpdateParams coefficient vector.

## 2. Non-negotiable constraints

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

Do not train or evaluate:

```text
contextual selector
per-context theta policy
checkpoint policy
abstention gate
runtime learned policy
dynamic neural UpdateParams model
```

A candidate is a single global fixed coefficient vector.

It may only change bounded static_flow_shield coefficients such as:

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
theta_goal_projection_mode_*
```

If a field is not actually used by static_flow_shield materialization, audit and report it separately.

No candidate may depend on:

```text
map family
agent count
seed
budget
horizon
checkpoint
traffic state
trace features
success/failure outcome
runtime context
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

Even if the fixed coefficient vector wins, it is not a dynamic learned policy claim. At most it becomes a stronger fixed baseline:

```text
optimized_static_flow_shield_fixed_v1
```

## 3. Baseline interpretation

Primary baseline for this round:

```text
current hand-designed static_flow_shield
```

Paper/parity floor:

```text
additive_ltm
```

Diagnostic baselines:

```text
frozen_family_static_goal_aware
best_fixed_static_goal_aware
family_static variants
```

G5.52 found that static_flow_shield has meaningful quality margin over additive_ltm on paired both-success cases:

```text
mean_ratio_additive = 1.28936118566
mean_ratio_static_flow = 1.19350570633
relative_improvement_pct = 7.43433883353
```

But static_flow_shield also has success-regression cases relative to additive_ltm:

```text
static_flow_success_rate = 0.753984962406
additive_success_rate = 0.785363408521
success_regression_count_static_vs_additive = 465
```

Therefore G5.53 should evaluate additive_ltm as a paper floor and diagnostic success-safety floor, but the direct promotion gate is versus current hand static_flow_shield.

If optimized fixed coefficients zero-regress versus static_flow_shield, they inherit static_flow’s success profile. Additional additive diagnostics should still be reported.

## 4. Required worklog entry

Before coding, append to `docs/codex-worklog.md`:

```markdown
## 2026-06-15 - Repair5G.5.53 fixed-global static_flow coefficient optimization

- Request:
  Pause the dynamic learned UpdateParams policy / contextual selector / checkpoint-level abstention direction. Do not train a contextual policy in this round. The new objective is to search or learn one fixed global set of static_flow_shield coefficients that can directly replace the current hand-designed static_flow_shield baseline.

- Interpretation:
  G5.50–G5.52 showed that fulltheta regions and checkpoint labels contain signal, but dynamic policy training repeatedly failed targeted SafeGate. G5.52 Label-v2 forbade all 27 G5.51 ALLOW_THETA actions and collapsed to all-abstain. Therefore this round reduces complexity: optimize a single global deterministic static-flow coefficient vector, not a per-context policy.

- Baseline:
  Primary comparison is optimized_fixed_static_flow_coefficients vs current hand static_flow_shield using paired replay. additive_ltm is the paper/parity floor and a diagnostic safety floor. Strong static/family variants remain diagnostics.

- Success criteria:
  Zero success regression versus current static_flow_shield, non-worse success rate, better paired quality metric on both-success rows, robustness on held-out/fresh seeds/maps/agent counts/budgets, candidate recognized, fingerprint match rate = 1, cost finite, all claim flags closed.

- Constraints:
  No external/lacam2/lacam2 edits, no solver semantic changes, no contextual selector, no checkpoint policy, no dynamic UpdateParams policy, no abstention gate, no IDs 166..205, no runtime/Phase5.5/Phase6/AAAI claims.
```

Also append a short governance update to:

```text
deep-research-report.md
docs/aaai_quality_requirements.md
docs/goal_aware_dual_channel_ltm_research_strategy.md
phase4_6_laur_ltm_codex_execution_plan.md
```

Required statement:

```text
G5.53 pauses the dynamic learned UpdateParams policy direction and evaluates a simpler fixed-global coefficient optimization problem. The candidate is a single deterministic static_flow_shield coefficient vector shared across all maps, agents, seeds, budgets, and checkpoints. It is not a contextual selector, abstention policy, or runtime learned policy. It can only replace the hand-designed static_flow_shield coefficients if it wins paired replay with zero success regression versus the current static_flow_shield. If it fails, current hand static_flow_shield remains the primary baseline.
```

## 5. Required files

Create:

```text
czr004_g553_fixed_global_staticflow_coefficients_plan.md

scripts/repair5g553_common.py
scripts/verify_repair5g553_g552_artifacts.py
scripts/audit_repair5g553_staticflow_current_coefficients.py
scripts/create_repair5g553_global_staticflow_search_space.py
scripts/run_repair5g553_global_staticflow_stage0_smoke.py
scripts/analyze_repair5g553_stage0_smoke.py
scripts/run_repair5g553_global_staticflow_stage1_search.py
scripts/analyze_repair5g553_stage1_search.py
scripts/create_repair5g553_fixed_coeff_validation_plan.py
scripts/run_repair5g553_fixed_coeff_validation.py
scripts/analyze_repair5g553_fixed_coeff_validation.py
scripts/create_repair5g553_fixed_coeff_blind_plan_if_warranted.py
scripts/run_repair5g553_fixed_coeff_blind_if_warranted.py
scripts/analyze_repair5g553_fixed_coeff_blind_if_warranted.py
scripts/write_repair5g553_decision.py
```

Outputs:

```text
outputs/reports/phase5p5_repair5g553_*
outputs/tables/phase5p5_repair5g553_*
outputs/logs/phase5p5_repair5g553_*
```

Large raw plans/results must go under ignored logs. Do not commit raw CSVs >50MB. Commit only compact summaries, previews, manifests, hashes, and exact resume commands.

## 6. Stage A — Verify G5.52 and lock pivot

Inputs:

```text
outputs/reports/phase5p5_repair5g552_decision_summary.json
outputs/reports/phase5p5_repair5g552_label_v2_dataset_summary.json
outputs/reports/phase5p5_repair5g552_policy_as_executed_summary.json
outputs/reports/phase5p5_repair5g552_safe_theta_library_summary.json
outputs/reports/phase5p5_repair5g552_staticflow_vs_additive_margin_summary.json
outputs/reports/phase5p5_repair5g552_g551_targeted_regression_autopsy_v2_summary.json
```

Write:

```text
outputs/reports/phase5p5_repair5g553_g552_verification.md
outputs/reports/phase5p5_repair5g553_g552_verification_summary.json
outputs/tables/phase5p5_repair5g553_g552_artifact_audit.csv
outputs/tables/phase5p5_repair5g553_claim_flag_audit.csv
```

Required checks:

```text
g552_decision = g552_label_v2_offline_policy_not_safe_continue_label_design
label_v2_rows = 128000
g551_allow_theta_candidates_forbidden_under_label_v2 = 27
safe_theta_count = 25
forbidden_theta_count = 1213
targeted_replay_run = false
policy_as_executed_offline_non_static_usage = 0
static_flow_vs_additive_relative_improvement_pct = 7.43433883353
all claim flags closed
external_lacam2_clean = true
```

Write a clear interpretation:

```text
G5.53 does not continue G5.52 policy-as-executed training. It pauses dynamic policy work and evaluates fixed global static-flow coefficient optimization.
```

## 7. Stage B — Audit current static_flow_shield coefficients

Create:

```text
scripts/audit_repair5g553_staticflow_current_coefficients.py
```

Write:

```text
outputs/reports/phase5p5_repair5g553_current_staticflow_coefficients.md
outputs/reports/phase5p5_repair5g553_current_staticflow_coefficients_summary.json
outputs/tables/phase5p5_repair5g553_current_staticflow_theta.csv
outputs/tables/phase5p5_repair5g553_staticflow_field_usage_audit.csv
outputs/tables/phase5p5_repair5g553_staticflow_materialization_audit.csv
```

Required audit questions:

```text
1. What exact theta coefficients define current static_flow_shield?
2. Which fields are actually consumed by C++ UpdateParams materialization?
3. Which fields are aliases or ignored?
4. What are the legal lower/upper bounds for each coefficient?
5. Does current static_flow_shield materialize with fingerprint match = 1?
6. Is goal_projection_mode encoded canonically?
7. Are min_edge_cost / max_edge_cost ordered and bounded?
8. Are all costs finite under current coefficients?
9. Which candidate ID / method string is the current primary static_flow_shield?
```

If current static_flow_shield itself cannot be materialized with exact fingerprint 1, stop and repair the staticflow fingerprint path before running search.

## 8. Stage C — Define fixed global search space

Create:

```text
scripts/create_repair5g553_global_staticflow_search_space.py
```

Write:

```text
outputs/reports/phase5p5_repair5g553_global_staticflow_search_space.md
outputs/reports/phase5p5_repair5g553_global_staticflow_search_space_summary.json
outputs/tables/phase5p5_repair5g553_search_space_bounds.csv
outputs/tables/phase5p5_repair5g553_candidate_family_blueprint.csv
outputs/tables/phase5p5_repair5g553_search_plan_preview.csv
```

Search-space principles:

```text
start from current hand static_flow_shield coefficients
use local bounded perturbations first
do not include context-dependent branches
do not include learned policy features
do not include abstention
all candidates are global fixed theta vectors
all candidates must be deterministic and registry-materializable
```

Candidate families:

```text
hand_static_reference
tiny_local_perturbation_2pct
small_local_perturbation_5pct
medium_local_perturbation_10pct
coordinate_sweep_each_field
lambda_flow_lambda_cong_grid
flow_shield_beta_cap_grid
alpha_flow_wait_progress_grid
alpha_cong_commit_nonprogress_grid
edge_cost_clamp_grid
rho_decay_grid
sobol_local_global_static
cma_es_or_ranked_search_candidates
negative_random_wide_control
```

Bounds should be conservative unless existing project bounds are stricter:

```text
theta_alpha_cong_commit_progress: [0.0, 1.5]
theta_alpha_cong_commit_nonprogress: [0.5, 1.75]
theta_alpha_cong_block: [0.5, 2.25]
theta_alpha_cong_wait_progress: [0.0, 1.25]
theta_alpha_cong_wait_nonprogress: [0.0, 1.75]
theta_alpha_flow_commit_progress: [0.0, 1.5]
theta_alpha_flow_wait_progress: [0.0, 1.25]
theta_rho_cong_decay: [0.90, 1.00]
theta_rho_flow_decay: [0.90, 1.00]
theta_lambda_cong: [0.50, 1.50]
theta_lambda_flow: [0.0, 1.50]
theta_flow_shield_beta: [0.0, 0.80]
theta_max_flow_shield: [0.25, 1.50]
theta_min_edge_cost: [0.25, 1.00]
theta_max_edge_cost: [8.0, 12.0]
theta_goal_projection_mode: {flow_shield, agent_progress, none}
```

If the current static_flow_shield uses a narrower known range, use the narrower range and document it.

Hard requirement:

```text
candidate_recognized_all = true
fulltheta_fingerprint_match_rate = 1
cost_finite_all = true
```

No search may proceed if fingerprint match is not 1 in the candidate registry smoke.

## 9. Stage D — Dataset split and paired protocol

Create a fixed evaluation protocol with clean splits:

```text
stage0_smoke:
  small row budget, all candidate materialization and obvious failure check

stage1_search:
  training/tuning search on development seeds

stage2_validation:
  heldout seeds and neighbor strata, no parameter changes after this begins

stage3_blind_if_warranted:
  fresh seeds/maps/agent settings, only if stage2 passes
```

Write:

```text
outputs/tables/phase5p5_repair5g553_split_manifest.csv
outputs/tables/phase5p5_repair5g553_eval_contexts_by_split.csv
outputs/reports/phase5p5_repair5g553_split_manifest_summary.json
```

Core strata:

```text
random, agents 50/100, nominal_budget_ms 2000
maze, agents 50/100, nominal_budget_ms 2000
```

Diagnostic strata:

```text
warehouse, agents 50/100, nominal_budget_ms 500/1000/2000
maze/random, nominal_budget_ms 500/1000 if evaluable
```

Horizon families:

```text
short_budget_ms: 1000, 2000, 5000
base_time_limit_sec: 0.5, 1.0
ltm_max_iterations: 2, 4
```

Every candidate comparison must include paired rows against:

```text
current hand static_flow_shield
additive_ltm diagnostic
family_static diagnostic if cheap enough
```

Paired key:

```text
map
agents
seed
nominal_budget_ms
horizon_id
short_budget_ms
base_time_limit_sec
ltm_max_iterations
scenario hash
```

## 10. Stage E — Stage0 smoke

Create:

```text
scripts/run_repair5g553_global_staticflow_stage0_smoke.py
scripts/analyze_repair5g553_stage0_smoke.py
```

Write:

```text
outputs/reports/phase5p5_repair5g553_stage0_smoke.md
outputs/reports/phase5p5_repair5g553_stage0_smoke_summary.json
outputs/tables/phase5p5_repair5g553_stage0_smoke_results_sample.csv
outputs/tables/phase5p5_repair5g553_stage0_materialization_failures.csv
outputs/tables/phase5p5_repair5g553_stage0_obvious_regressions.csv
```

Minimum smoke:

```text
candidate_vectors >= 200
solver_rows >= 5000
baseline_static_flow_rows >= 500
fingerprint_match_rate = 1
candidate_recognized_all = true
cost_finite_all = true
```

Stage0 pass:

```text
no materialization failures
no fingerprint mismatches
no invalid cost candidates
at least 20 candidates survive obvious-regression filter
current hand static_flow reproduced exactly
```

If Stage0 fails due to fingerprint/cost/recognition, stop and report:

```text
g553_fixed_staticflow_materialization_blocked
```

## 11. Stage F — Stage1 fixed coefficient search

Create:

```text
scripts/run_repair5g553_global_staticflow_stage1_search.py
scripts/analyze_repair5g553_stage1_search.py
```

Raw output under ignored logs:

```text
outputs/logs/phase5p5_repair5g553_stage1_search/stage1_search_results.csv
outputs/logs/phase5p5_repair5g553_stage1_search/stage1_search_plan.csv
```

Committed compact outputs:

```text
outputs/reports/phase5p5_repair5g553_stage1_search.md
outputs/reports/phase5p5_repair5g553_stage1_search_summary.json
outputs/tables/phase5p5_repair5g553_stage1_candidate_leaderboard.csv
outputs/tables/phase5p5_repair5g553_stage1_candidate_by_stratum.csv
outputs/tables/phase5p5_repair5g553_stage1_failure_cases.csv
outputs/tables/phase5p5_repair5g553_stage1_parameter_sensitivity.csv
outputs/tables/phase5p5_repair5g553_stage1_top_candidates.csv
```

Minimum local search:

```text
candidate_vectors >= 1000
new_solver_rows >= 60000
baseline_static_flow_rows >= 5000
paired_success_rows_vs_static_flow >= 20000
```

Preferred if PC stable:

```text
candidate_vectors >= 3000
new_solver_rows >= 150000
paired_success_rows_vs_static_flow >= 50000
```

Search objective is lexicographic, not mean-only.

For each candidate:

```text
success_regression_count_vs_static_flow
success_gain_count_vs_static_flow
success_rate_delta_vs_static_flow
both_success_quality_delta_mean_vs_static_flow
both_success_quality_delta_median_vs_static_flow
better_count_vs_static_flow
worse_count_vs_static_flow
paired_rows
support_strata
support_seed_blocks
fingerprint_match_rate
cost_finite_rate
```

Candidate search score:

```text
if fingerprint_match_rate < 1:
  reject
elif candidate_recognized_all != true:
  reject
elif cost_finite_all != true:
  reject
elif success_regression_count_vs_static_flow > 0:
  reject_for_promotion_but_keep_for_sensitivity
else:
  rank by:
    1. mean quality delta vs static_flow (lower is better)
    2. median quality delta vs static_flow
    3. better_count - worse_count
    4. support_strata
    5. simplicity / distance from hand static vector
```

Do not promote candidates selected only on stage1. Stage1 only nominates candidates for validation.

Stage1 pass to validation:

```text
at least 3 candidate vectors with:
  success_regression_count_vs_static_flow = 0
  both_success_quality_delta_mean_vs_static_flow < 0
  better_count > worse_count
  support_strata >= 3
  fingerprint_match_rate = 1
```

If no candidate passes, write:

```text
g553_no_fixed_coeff_candidate_beats_hand_staticflow_keep_baseline
```

and stop after decision.

## 12. Stage G — Heldout validation

Create:

```text
scripts/create_repair5g553_fixed_coeff_validation_plan.py
scripts/run_repair5g553_fixed_coeff_validation.py
scripts/analyze_repair5g553_fixed_coeff_validation.py
```

Raw output under logs:

```text
outputs/logs/phase5p5_repair5g553_validation/validation_results.csv
```

Committed outputs:

```text
outputs/reports/phase5p5_repair5g553_fixed_coeff_validation.md
outputs/reports/phase5p5_repair5g553_fixed_coeff_validation_summary.json
outputs/tables/phase5p5_repair5g553_validation_candidate_leaderboard.csv
outputs/tables/phase5p5_repair5g553_validation_by_stratum.csv
outputs/tables/phase5p5_repair5g553_validation_failure_cases.csv
outputs/tables/phase5p5_repair5g553_validation_vs_additive_diagnostic.csv
```

Validation minimum:

```text
heldout_candidates <= 10
new_solver_rows >= 50000
paired_success_rows_vs_static_flow >= 15000
fresh seeds not used in stage1
no parameter changes after validation starts
```

Validation pass:

```text
best candidate:
  success_regression_count_vs_static_flow = 0
  success_rate_delta_vs_static_flow >= 0
  both_success_quality_delta_mean_vs_static_flow <= -0.001
  better_count_vs_static_flow > worse_count_vs_static_flow
  support_strata >= 3
  support_seed_blocks >= 3
  fingerprint_match_rate = 1
  cost_finite_all = true
```

Preferred broader claim threshold:

```text
relative quality improvement vs static_flow >= 1%
zero success regressions
```

If candidate improves mean quality by <0.1 absolute ratio point, report as marginal and do not promote beyond diagnostic.

## 13. Stage H — Fresh blind if warranted

Only if validation passes.

Create:

```text
scripts/create_repair5g553_fixed_coeff_blind_plan_if_warranted.py
scripts/run_repair5g553_fixed_coeff_blind_if_warranted.py
scripts/analyze_repair5g553_fixed_coeff_blind_if_warranted.py
```

Committed outputs:

```text
outputs/reports/phase5p5_repair5g553_fixed_coeff_blind_summary.json
outputs/reports/phase5p5_repair5g553_fixed_coeff_blind.md
outputs/tables/phase5p5_repair5g553_blind_candidate_vs_static_flow.csv
outputs/tables/phase5p5_repair5g553_blind_by_stratum.csv
outputs/tables/phase5p5_repair5g553_blind_failure_cases.csv
```

Blind minimum:

```text
new_solver_rows >= 60000
fresh seed blocks
include random/maze core
include warehouse diagnostics if feasible
include additive diagnostic
```

Blind pass:

```text
success_regression_count_vs_static_flow = 0
success_rate_delta_vs_static_flow >= 0
both_success_quality_delta_mean_vs_static_flow <= -0.001
better_count > worse_count
fingerprint_match_rate = 1
cost_finite_all = true
```

If blind passes, decision may be:

```text
g553_fixed_global_staticflow_coefficients_beat_hand_staticflow_continue_as_stronger_baseline
```

But claim flags remain closed:

```text
phase5p5_allowed=false
phase6_allowed=false
runtime_claim_allowed=false
learned_runtime_policy_validated=false
aaai_ready=false
```

This candidate can become a new diagnostic or primary fixed baseline in future rounds only after user review.

## 14. Reports and decision

Create:

```text
scripts/write_repair5g553_decision.py
```

Write:

```text
outputs/reports/phase5p5_repair5g553_decision.md
outputs/reports/phase5p5_repair5g553_decision_summary.json
outputs/tables/phase5p5_repair5g553_claim_ledger.csv
outputs/tables/phase5p5_repair5g553_final_candidate_theta.csv
outputs/tables/phase5p5_repair5g553_baseline_role_policy.csv
outputs/tables/phase5p5_repair5g553_large_artifact_manifest.csv
```

Possible decisions:

```text
g553_fixed_staticflow_materialization_blocked
g553_no_fixed_coeff_candidate_beats_hand_staticflow_keep_baseline
g553_stage1_candidate_found_continue_validation
g553_validation_failed_keep_hand_staticflow
g553_validation_passed_continue_blind
g553_blind_failed_keep_hand_staticflow
g553_fixed_global_staticflow_coefficients_beat_hand_staticflow_continue_as_stronger_baseline
```

Required final answers:

```text
1. Did one fixed global coefficient vector beat hand static_flow_shield?
2. Did it have zero success regressions vs hand static_flow_shield?
3. Did it improve paired both-success quality?
4. Did it preserve or improve success rate?
5. Did it generalize to heldout seeds / maps / agent counts / budgets?
6. Did it pass fingerprint = 1 and cost finite gates?
7. How large was the gain versus hand static_flow?
8. How does it compare diagnostically to additive_ltm?
9. Should the hand static_flow_shield remain the primary baseline?
10. Should dynamic learned policy remain paused?
```

Final report must explicitly state:

```text
This round does not validate a dynamic learned UpdateParams policy.
This round only evaluates whether a fixed global optimized coefficient vector can replace a hand-designed static baseline.
```

## 15. Quality and safety requirements

Validation commands:

```powershell
python -m py_compile scripts/repair5g553_common.py scripts/verify_repair5g553_g552_artifacts.py scripts/audit_repair5g553_staticflow_current_coefficients.py scripts/create_repair5g553_global_staticflow_search_space.py scripts/run_repair5g553_global_staticflow_stage0_smoke.py scripts/analyze_repair5g553_stage0_smoke.py scripts/run_repair5g553_global_staticflow_stage1_search.py scripts/analyze_repair5g553_stage1_search.py scripts/create_repair5g553_fixed_coeff_validation_plan.py scripts/run_repair5g553_fixed_coeff_validation.py scripts/analyze_repair5g553_fixed_coeff_validation.py scripts/create_repair5g553_fixed_coeff_blind_plan_if_warranted.py scripts/run_repair5g553_fixed_coeff_blind_if_warranted.py scripts/analyze_repair5g553_fixed_coeff_blind_if_warranted.py scripts/write_repair5g553_decision.py

git diff --check

python -m pytest tests -q
```

Known unrelated test failures from missing historical G5/G5.1 artifacts may be reported as pre-existing only if they are unchanged and documented.

Hard stop conditions:

```text
external/lacam2/lacam2 dirty
reserved IDs 166..205 used
fingerprint mismatch in candidate materialization
candidate_recognized_all false
cost non-finite
dynamic policy / selector / abstention code introduced
raw oversized CSV committed
claim flags opened
```

## 16. Short implementation note

This round should run long enough locally to be meaningful. It should not finish by merely writing static tables.

Minimum practical local target:

```text
Stage0: >=5k solver rows
Stage1: >=60k solver rows
Validation if Stage1 passes: >=50k solver rows
Blind if validation passes: >=60k solver rows
```

Preferred if PC remains stable:

```text
Stage1: >=150k solver rows
Validation: >=80k solver rows
Blind: >=80k solver rows
```

Use resumable row limits and exact resume commands.

## 17. One-sentence goal

```text
Stop learning a dynamic policy; learn/search one fixed global coefficient vector for static_flow_shield and test it as a direct deterministic replacement for the hand static_flow baseline.
```
